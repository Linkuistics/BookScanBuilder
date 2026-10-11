"""Bounded dependency experiment; this is not the preparation command."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from contextlib import ExitStack
from decimal import Decimal
from pathlib import Path
from typing import TypedDict

import pikepdf
from PIL import Image


class ExtensionRecord(TypedDict):
    base_version: str
    extension_level: int


def encode_decimal(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"unexpected report value: {type(value).__name__}")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inherited(page: pikepdf.Page, key: str, default: object = None) -> object:
    obj = page.obj
    for _ in range(100):
        if key in obj:
            return obj[key]
        if "/Parent" not in obj:
            return default
        obj = obj.Parent
    raise AssertionError("page tree exceeds experiment depth")


def resource_graph(resources: pikepdf.Object) -> object:
    """Bounded storage fingerprint, including nested streams and decoder resources."""
    visited: dict[tuple[int, int], int] = {}

    def snapshot(value: object) -> object:
        if isinstance(value, pikepdf.Object):
            if value.is_indirect:
                if value.objgen in visited:
                    return {"ref": visited[value.objgen]}
                visited[value.objgen] = len(visited)
            if isinstance(value, pikepdf.Stream | pikepdf.Dictionary):
                result: dict[str, object] = {
                    "dictionary": {
                        key: snapshot(value[key])
                        for key in sorted(value.keys())
                        if key != "/Length"
                    }
                }
                if isinstance(value, pikepdf.Stream):
                    result["raw_sha256"] = hashlib.sha256(
                        value.read_raw_bytes()
                    ).hexdigest()
                return result
            if isinstance(value, pikepdf.Array):
                return [snapshot(item) for item in value]
            if isinstance(value, pikepdf.String):
                return {"string_hex": bytes(value).hex()}
            if isinstance(value, pikepdf.Name):
                return {"name": str(value)}
            raise TypeError(f"unexpected PDF value: {value._type_name}")
        if value is None or isinstance(value, bool | int | float | Decimal | str):
            return value
        raise TypeError(f"unexpected resource value: {type(value).__name__}")

    return snapshot(resources)


def fingerprint(page: pikepdf.Page) -> dict[str, object]:
    resources = inherited(page, "/Resources")
    assert isinstance(resources, pikepdf.Dictionary)
    contents = page.obj.get("/Contents")
    streams = (
        []
        if contents is None
        else ([contents] if isinstance(contents, pikepdf.Stream) else list(contents))
    )
    crop = inherited(page, "/CropBox", inherited(page, "/MediaBox"))
    return {
        "media": list(inherited(page, "/MediaBox")),
        "crop": list(crop),
        "bleed": list(page.obj.get("/BleedBox", crop)),
        "trim": list(page.obj.get("/TrimBox", crop)),
        "art": list(page.obj.get("/ArtBox", crop)),
        "rotate": inherited(page, "/Rotate", 0),
        "unit": page.obj.get("/UserUnit", 1),
        "contents": [hashlib.sha256(s.read_bytes()).hexdigest() for s in streams],
        "images": {
            str(name): {
                "raw": hashlib.sha256(image.read_raw_bytes()).hexdigest(),
                "filter": str(image.get("/Filter", "none")),
                "width": int(image.Width),
                "height": int(image.Height),
                "mask": bool(image.get("/ImageMask", False)),
            }
            for name, image in resources.get("/XObject", {}).items()
            if image.get("/Subtype") == pikepdf.Name.Image
        },
        "annotations": len(page.obj.get("/Annots", [])),
        "resource_graph": resource_graph(resources),
    }


def render(pdf: Path, number: int, target: Path) -> tuple[tuple[int, int], str]:
    subprocess.run(
        [
            "pdftoppm",
            "-f",
            str(number),
            "-l",
            str(number),
            "-r",
            "300",
            "-cropbox",
            "-singlefile",
            "-png",
            str(pdf),
            str(target),
        ],
        check=True,
        capture_output=True,
    )
    with Image.open(target.with_suffix(".png")) as image:
        rgb = image.convert("RGB")
        return rgb.size, hashlib.sha256(rgb.tobytes()).hexdigest()


def make_labels(path: Path, prefix: str, count: int) -> None:
    with pikepdf.Pdf.new() as pdf:
        font = pdf.make_indirect(
            pikepdf.Dictionary(
                Type=pikepdf.Name.Font,
                Subtype=pikepdf.Name.Type1,
                BaseFont=pikepdf.Name.Helvetica,
            )
        )
        for number in range(1, count + 1):
            page = pdf.add_blank_page(page_size=(240, 320))
            page.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
            page.Contents = pdf.make_stream(
                f"BT /F1 28 Tf 25 150 Td ({prefix}{number}) Tj ET".encode("ascii")
            )
        # Make geometry/resources inherited to check page-copy materialization.
        parent = pdf.Root.Pages
        parent.MediaBox = pikepdf.Array([0, 0, 240, 320])
        parent.CropBox = pikepdf.Array([10, 10, 230, 310])
        parent.Rotate = 90
        parent.Resources = pdf.pages[0].Resources
        for page in pdf.pages:
            del page.obj["/MediaBox"]
            del page.obj["/Resources"]
            page.obj["/UserUnit"] = 1.25
            page.obj["/BleedBox"] = pikepdf.Array([12, 12, 228, 308])
            page.obj["/TrimBox"] = pikepdf.Array([15, 15, 225, 305])
            page.obj["/ArtBox"] = pikepdf.Array([20, 20, 220, 300])
        # Header-only inspection would miss this override.
        pdf.Root.Version = pikepdf.Name("/1.7")
        pdf.save(path, compress_streams=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    collection = args.collection.resolve()
    if out == collection or collection in out.parents:
        parser.error("output-dir must be outside the source collection")
    out.mkdir(parents=True, exist_ok=False)
    # Freeze the script and every source before doing any copying/rendering.
    script = Path(__file__).resolve()
    script_before = digest(script)
    recipe = script.parent.parent / "Taskfile.yml"
    recipe_before = digest(recipe)
    specs = [
        ("Covers/SchoenbergComposition.pdf", 1, "front"),
        ("Raw Scans/Fundamentals of Musical Composition.pdf", 40, "content"),
        ("Raw Scans/Fundamentals of Musical Composition.pdf", 140, "content"),
        (
            (
                "Processed Books/Norwegian - An Essential Grammar (Routledge)/"
                "Norwegian - An Essential Grammar (Routledge).pdf"
            ),
            20,
            "content",
        ),
        ("Needing Cleanup/Counterpoint in Composition.pdf", 20, "content"),
        ("Processed Books/Algorithm Design/Algorithm Design.pdf", 20, "content"),
        ("Covers/Algorithms on Strings, Trees, and Sequence.pdf", 1, "front"),
        ("Covers/Algorithms on Strings, Trees, and Sequence.pdf", 2, "back"),
    ]
    sources = {name: collection / name for name, _, _ in specs}
    before = {name: digest(path) for name, path in sources.items()}
    records: list[dict[str, object]] = []
    inventory: dict[str, dict[str, object]] = {}
    expected_extensions: dict[str, ExtensionRecord] = {}
    with ExitStack() as stack:
        opened = {
            name: stack.enter_context(pikepdf.open(path, attempt_recovery=False))
            for name, path in sources.items()
        }
        destination = stack.enter_context(pikepdf.Pdf.new())
        for name, pdf in opened.items():
            page_keys: dict[str, int] = {}
            annotation_pages = 0
            for page in pdf.pages:
                for key in page.obj.keys():
                    page_keys[key] = page_keys.get(key, 0) + 1
                annotation_pages += bool(page.obj.get("/Annots", []))
            form = pdf.Root.get("/AcroForm")
            inventory[name] = {
                "header_version": pdf.pdf_version,
                "catalog_version": str(pdf.Root.get("/Version", "")),
                "page_count": len(pdf.pages),
                "catalog_keys": sorted(pdf.Root.keys()),
                "page_key_counts": page_keys,
                "annotation_pages": annotation_pages,
                "encrypted": pdf.is_encrypted,
                "form_field_count": len(form.get("/Fields", []))
                if form is not None
                else 0,
                "xfa": form is not None and "/XFA" in form,
                "optional_content": "/OCProperties" in pdf.Root,
                "output_intents": "/OutputIntents" in pdf.Root,
            }
            for prefix, definition in pdf.Root.get("/Extensions", {}).items():
                assert prefix == "/ADBE" and str(definition.BaseVersion) == "/1.7"
                assert int(definition.ExtensionLevel) in (1, 2, 3)
                level = int(definition.ExtensionLevel)
                previous = expected_extensions.get(prefix)
                if previous is None or level > previous["extension_level"]:
                    expected_extensions[prefix] = {
                        "base_version": "1.7",
                        "extension_level": level,
                    }
        if expected_extensions:
            destination.Root.Extensions = pikepdf.Dictionary(
                {
                    prefix: pikepdf.Dictionary(
                        BaseVersion=pikepdf.Name("/" + definition["base_version"]),
                        ExtensionLevel=definition["extension_level"],
                    )
                    for prefix, definition in expected_extensions.items()
                }
            )
        for name, number, role in specs:
            source_page = opened[name].pages[number - 1]
            original = fingerprint(source_page)
            destination.pages.append(source_page)
            destination.pages[-1].obj["/BookScanBuilder"] = pikepdf.Dictionary(
                Version=1,
                Role=role,
                SourceSHA256=before[name],
                SourcePage=number,
            )
            assert "/BookScanBuilder" not in source_page.obj
            records.append(
                {
                    "source": name,
                    "source_page": number,
                    "role": role,
                    "fingerprint": original,
                }
            )
        destination.save(
            out / "copied.pdf",
            min_version=(
                max(
                    (
                        version
                        for pdf in opened.values()
                        for version in (
                            pdf.pdf_version,
                            str(pdf.Root.get("/Version", "/0.0"))[1:],
                        )
                    ),
                    key=lambda version: tuple(map(int, version.split("."))),
                ),
                max(
                    (item["extension_level"] for item in expected_extensions.values()),
                    default=0,
                ),
            ),
            compress_streams=False,
            stream_decode_level=pikepdf.StreamDecodeLevel.none,
            recompress_flate=False,
            normalize_content=False,
        )
        for name, pdf in opened.items():
            warnings = pdf.get_warnings()
            assert not warnings, (name, warnings)
            inventory[name]["warnings"] = warnings
    with pikepdf.open(out / "copied.pdf", attempt_recovery=False) as copied:
        assert len(copied.pages) == len(specs)
        assert {
            prefix: {
                "base_version": str(definition.BaseVersion)[1:],
                "extension_level": int(definition.ExtensionLevel),
            }
            for prefix, definition in copied.Root.get("/Extensions", {}).items()
        } == expected_extensions
        for index, record in enumerate(records, 1):
            page = copied.pages[index - 1]
            assert fingerprint(page) == record["fingerprint"]
            assert str(page.obj.BookScanBuilder.Role) == record["role"]
            assert int(page.obj.BookScanBuilder.SourcePage) == record["source_page"]
            src_render = render(
                sources[record["source"]],
                record["source_page"],
                out / f"source-{index}",
            )
            dst_render = render(out / "copied.pdf", index, out / f"copied-{index}")
            assert src_render == dst_render, f"render changed: {record['source']}"
            record["render_size"] = src_render[0]
            record["render_rgb_sha256"] = src_render[1]
            record["exact_render_match"] = True
        assert not copied.get_warnings()
    make_labels(out / "cover-labels.pdf", "K", 4)
    make_labels(out / "content-labels.pdf", "C", 2)
    label_before = {
        name: digest(out / name) for name in ("cover-labels.pdf", "content-labels.pdf")
    }
    label_records: list[dict[str, object]] = []
    labelled = [
        ("cover-labels.pdf", 1, "front"),
        ("content-labels.pdf", 2, "content"),
        ("cover-labels.pdf", 3, "content"),
        ("content-labels.pdf", 1, "content"),
        ("cover-labels.pdf", 4, "back"),
        ("cover-labels.pdf", 1, "back"),
    ]
    with ExitStack() as stack:
        opened_labels = {
            name: stack.enter_context(pikepdf.open(out / name))
            for name in {name for name, _, _ in labelled}
        }
        result = stack.enter_context(pikepdf.Pdf.new())
        snapshots = []
        for name, number, role in labelled:
            page = opened_labels[name].pages[number - 1]
            snapshots.append(fingerprint(page))
            result.pages.append(page)
            result.pages[-1].obj["/BookScanBuilder"] = pikepdf.Dictionary(
                Version=1, Role=role
            )
        assert len({p.objgen for p in result.pages}) == len(labelled)
        assert str(result.pages[0].obj.BookScanBuilder.Role) == "front"
        assert str(result.pages[-1].obj.BookScanBuilder.Role) == "back"
        result.save(
            out / "labelled.pdf",
            compress_streams=False,
            stream_decode_level=pikepdf.StreamDecodeLevel.none,
            min_version=max(
                (
                    version
                    for pdf in opened_labels.values()
                    for version in (
                        pdf.pdf_version,
                        str(pdf.Root.get("/Version", "/0.0"))[1:],
                    )
                ),
                key=lambda version: tuple(map(int, version.split("."))),
            ),
        )
    with pikepdf.open(out / "labelled.pdf") as result:
        assert tuple(map(int, result.pdf_version.split("."))) >= (1, 7)
        for index, (name, number, role) in enumerate(labelled, 1):
            assert fingerprint(result.pages[index - 1]) == snapshots[index - 1]
            assert str(result.pages[index - 1].obj.BookScanBuilder.Role) == role
            assert render(out / name, number, out / f"label-source-{index}") == render(
                out / "labelled.pdf", index, out / f"label-copied-{index}"
            )
            label_records.append(
                {
                    "output_page": index,
                    "source": name,
                    "source_page": number,
                    "role": role,
                    "fingerprint": snapshots[index - 1],
                    "exact_render_match": True,
                }
            )
    text = subprocess.run(
        ["pdftotext", out / "labelled.pdf", "-"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.split()
    assert text == ["K1", "C2", "K3", "C1", "K4", "K1"], text
    after = {name: digest(path) for name, path in sources.items()}
    assert before == after
    assert digest(script) == script_before, "experiment code moved during measurement"
    assert digest(recipe) == recipe_before, "experiment recipe moved during measurement"
    label_after = {name: digest(out / name) for name in label_before}
    assert label_before == label_after
    report = {
        "pikepdf": pikepdf.__version__,
        "qpdf": pikepdf.__libqpdf_version__,
        "poppler": subprocess.run(
            ["pdftoppm", "-v"], capture_output=True, check=True, text=True
        ).stderr.strip(),
        "script_sha256": script_before,
        "taskfile_sha256": recipe_before,
        "sources_before": before,
        "sources_after": after,
        "records": records,
        "source_inventory": inventory,
        "output_extensions": expected_extensions,
        "label_order": text,
        "label_records": label_records,
        "label_sources_before": label_before,
        "label_sources_after": label_after,
        "source_digests_unchanged": True,
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2, default=encode_decimal) + "\n"
    )
    print(
        json.dumps(
            {
                "report": str(out / "report.json"),
                "real_pages": len(records),
                "labelled_pages": len(labelled),
                "exact_render_matches": True,
                "source_digests_unchanged": True,
            }
        )
    )


if __name__ == "__main__":
    main()
