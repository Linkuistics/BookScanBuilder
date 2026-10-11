"""Frozen per-page public-command acceptance: synthetic, explicit real, or all."""

import argparse
import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import cast

import pikepdf
from pdf_fixtures import raw_pdf, rich_pdf
from PIL import Image
from test_preview import labels

from bookscan.results import Json


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inherited(page: pikepdf.Object, key: str, default: object = None) -> object:
    current = page
    seen: set[tuple[int, int]] = set()
    while True:
        if key in current:
            return cast(object, current[key])
        if "/Parent" not in current:
            return default
        current = current["/Parent"]
        assert current.objgen not in seen
        seen.add(current.objgen)


def geometry(page: pikepdf.Object) -> dict[str, Json]:
    media = inherited(page, "/MediaBox")
    crop = inherited(page, "/CropBox", media)
    record: dict[str, Json] = {}
    for key in ("MediaBox", "CropBox", "BleedBox", "TrimBox", "ArtBox"):
        value = (
            media if key == "MediaBox" else crop if key == "CropBox" else page.get("/" + key, crop)
        )
        assert isinstance(value, pikepdf.Array)
        record[key] = [str(Decimal(str(v))) for v in value]
    record["Rotate"] = str(inherited(page, "/Rotate", 0))
    record["UserUnit"] = str(page.get("/UserUnit", 1))
    return record


def streams(page: pikepdf.Object) -> list[Json]:
    records: list[Json] = []
    ancestors: set[tuple[int, int]] = set()

    def visit(value: object, path: str) -> None:
        if not isinstance(value, (pikepdf.Dictionary, pikepdf.Array, pikepdf.Stream)):
            return
        if value.is_indirect and value.objgen in ancestors:
            return
        if value.is_indirect:
            ancestors.add(value.objgen)
        if isinstance(value, pikepdf.Stream):
            records.append(
                {
                    "path": path,
                    "raw_sha256": hashlib.sha256(value.read_raw_bytes()).hexdigest(),
                    "filter": str(value.get("/Filter", "none")),
                    "subtype": str(value.get("/Subtype", "none")),
                    "width": str(value.get("/Width", "none")),
                    "height": str(value.get("/Height", "none")),
                }
            )
        if isinstance(value, pikepdf.Array):
            for n, child in enumerate(value):
                visit(child, path + f"[{n}]")
        else:
            for key in sorted(value.keys()):
                if key not in {"/P", "/Parent", "/Length", "/StructParent"}:
                    visit(value[key], path + key)
        if value.is_indirect:
            ancestors.remove(value.objgen)

    for key in ("/Resources", "/Contents", "/Group", "/BoxColorInfo", "/Annots"):
        visit(inherited(page, key) if key == "/Resources" else page.get(key), key)
    return records


def render(pdf: Path, page: int, target: Path, cropbox: bool) -> tuple[dict[str, Json], list[str]]:
    command = [
        "pdftoppm",
        "-f",
        str(page),
        "-l",
        str(page),
        "-r",
        "300",
        "-singlefile",
        "-png",
        *(["-cropbox"] if cropbox else []),
        str(pdf),
        str(target),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    path = target.with_suffix(".png")
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        record: dict[str, Json] = {
            "path": str(path),
            "dimensions": [width, height],
            "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(),
            "diagnostics": result.stderr,
        }
        # Fixed pixel crops retain native 300-dpi detail, never resampled.
        areas = {
            "centre": (
                width // 3,
                height // 3,
                min(width, width // 3 + 900),
                min(height, height // 3 + 900),
            ),
            "margin": (0, 0, min(width, 600), min(height, 1000)),
            "detail": (
                width // 4,
                height // 2,
                min(width, width // 4 + 1200),
                min(height, height // 2 + 900),
            ),
        }
        crops: dict[str, Json] = {}
        for name, box in areas.items():
            destination = target.parent / (target.name + "-" + name + ".png")
            detail = rgb.crop(box)
            detail.save(destination)
            crops[name] = {
                "path": str(destination),
                "box": list(box),
                "rgb_sha256": hashlib.sha256(detail.tobytes()).hexdigest(),
            }
        record["crops"] = crops
    return record, command


def cases(
    artifacts: Path, mode: str, collection: Path | None
) -> list[tuple[str, list[str], list[tuple[Path, int, str]]]]:
    covers = labels(artifacts / "Labelled covers.pdf", 4, "K")
    content = labels(artifacts / "Labelled content.pdf", 2, "C")
    six = labels(artifacts / "Six pages.pdf", 6)
    rich = rich_pdf(artifacts / "Nested Form and static appearance.pdf")
    defaults = rich_pdf(artifacts / "Nested default boxes.pdf", defaults=True, annotated=False)
    blank = raw_pdf(artifacts / "Empty encoded stream.pdf", stream_dict=b"/Filter /FlateDecode")
    synthetic = [
        (
            "interleaved",
            [
                "--back",
                str(covers),
                "4",
                "--content",
                str(content),
                "2",
                "--front",
                str(covers),
                "1",
                "--content",
                str(covers),
                "3",
                "--content",
                str(content),
                "1",
            ],
            [
                (covers, 1, "front"),
                (content, 2, "content"),
                (covers, 3, "content"),
                (content, 1, "content"),
                (covers, 4, "back"),
            ],
        ),
        (
            "repeat-roles",
            ["--back", str(covers), "1", "--content", str(content), "--front", str(covers), "1"],
            [
                (covers, 1, "front"),
                (content, 1, "content"),
                (content, 2, "content"),
                (covers, 1, "back"),
            ],
        ),
        (
            "descending",
            ["--content", str(six), "6-4,1,4,!5"],
            [(six, n, "content") for n in (6, 4, 1, 4)],
        ),
        (
            "exclusions",
            ["--content", str(six), "!2,!5-6"],
            [(six, n, "content") for n in (1, 3, 4)],
        ),
        ("assembled", ["--content", str(content)], [(content, n, "content") for n in (1, 2)]),
        ("nested-static", ["--content", str(rich)], [(rich, 1, "content")]),
        ("nested-defaults", ["--content", str(defaults)], [(defaults, 1, "content")]),
        ("encoded-empty", ["--content", str(blank)], [(blank, 1, "content")]),
    ]
    real: list[tuple[str, list[str], list[tuple[Path, int, str]]]] = []
    if mode != "synthetic":
        assert collection is not None
        fundamental = collection / "Raw Scans/Fundamentals of Musical Composition.pdf"
        schoenberg = collection / "Covers/SchoenbergComposition.pdf"
        norwegian = (
            collection
            / "Processed Books/Norwegian - An Essential Grammar (Routledge)"
            / "Norwegian - An Essential Grammar (Routledge).pdf"
        )
        counterpoint = collection / "Needing Cleanup/Counterpoint in Composition.pdf"
        algorithm = collection / "Processed Books/Algorithm Design/Algorithm Design.pdf"
        strings = collection / "Covers/Algorithms on Strings, Trees, and Sequence.pdf"
        real = [
            (
                "music",
                ["--front", str(schoenberg), "1", "--content", str(fundamental), "40,140"],
                [
                    (schoenberg, 1, "front"),
                    (fundamental, 40, "content"),
                    (fundamental, 140, "content"),
                ],
            ),
            ("norwegian", ["--content", str(norwegian), "20"], [(norwegian, 20, "content")]),
            (
                "counterpoint",
                ["--content", str(counterpoint), "20"],
                [(counterpoint, 20, "content")],
            ),
            ("algorithm", ["--content", str(algorithm), "20"], [(algorithm, 20, "content")]),
            (
                "strings",
                [
                    "--front",
                    str(strings),
                    "1",
                    "--content",
                    str(content),
                    "--back",
                    str(strings),
                    "2",
                ],
                [
                    (strings, 1, "front"),
                    (content, 1, "content"),
                    (content, 2, "content"),
                    (strings, 2, "back"),
                ],
            ),
        ]
    return synthetic if mode == "synthetic" else real if mode == "real" else synthetic + real


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("synthetic", "real", "all"), default="all")
    parser.add_argument("--collection", type=Path)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    mode = cast(str, args.mode)
    collection: Path | None = None
    if mode != "synthetic":
        if args.collection is None:
            parser.error("real/all requires an explicit collection root")
        collection = cast(Path, args.collection).resolve()
    artifacts = cast(Path, args.artifacts).resolve()
    if artifacts.exists() or (collection is not None and artifacts.is_relative_to(collection)):
        parser.error("Artifacts must be unused and outside the explicit collection.")
    # Synthetic never resolves or opens the supplied collection; it has no collection dependency.
    if mode == "synthetic" and args.collection is not None:
        parser.error("synthetic mode takes no collection argument")
    artifacts.mkdir(parents=True)
    requests = cases(artifacts, mode, collection)
    root = Path(__file__).resolve().parents[1]
    subjects = sorted(
        set(
            [
                *root.glob("src/bookscan/*.py"),
                *root.glob("tests/*.py"),
                root / "Taskfile.yml",
                root / "pyproject.toml",
                root / "uv.lock",
                root / "docs/specs/prepared-pdf.md",
                root / "docs/adr/prepared-page-hints.md",
                *(p for _, _, items in requests for p, _, _ in items),
            ]
        )
    )
    before = {str(p): digest(p) for p in subjects}
    checks_command = [
        "uv",
        "run",
        "--locked",
        "pytest",
        "-q",
        "tests/test_publication.py",
        "tests/test_validation.py",
        "--basetemp",
        str(artifacts / "fault-checks"),
        "--junitxml",
        str(artifacts / "fault-checks.xml"),
    ]
    checks = subprocess.run(checks_command, capture_output=True, text=True, check=False)
    assert checks.returncode == 0, checks.stdout + checks.stderr
    evidence: list[Json] = [
        cast(dict[str, Json], json.loads(p.read_text()))
        for p in sorted((artifacts / "fault-checks").rglob("evidence.json"))
    ]
    assert len(evidence) == 18
    records: list[Json] = []
    for name, selection_args, expected in requests:
        output = artifacts / (name + "-prepared.pdf")
        command = [
            "uv",
            "run",
            "--locked",
            "bookscan",
            "prepare",
            *selection_args,
            "--output",
            str(output),
            "--json",
        ]
        listing = sorted(p.name for p in artifacts.iterdir())
        preview = subprocess.run(
            [*command, "--dry-run"], capture_output=True, text=True, check=False
        )
        assert preview.returncode == 0, preview.stdout + preview.stderr
        planned = json.loads(preview.stdout)
        assert planned["pages"] == [
            dict(output_page=n, source=str(p), source_page=page, role=role)
            for n, (p, page, role) in enumerate(expected, 1)
        ]
        assert listing == sorted(p.name for p in artifacts.iterdir())
        written = subprocess.run(command, capture_output=True, text=True, check=False)
        assert written.returncode == 0, written.stdout + written.stderr
        result = json.loads(written.stdout)
        assert (
            result["status"] == "written"
            and result["page_count"] == len(expected)
            and result["warnings"] == []
        )
        pages: list[Json] = []
        with pikepdf.Pdf.open(output, attempt_recovery=False) as destination:
            assert len(destination.pages) == len(expected)
            markers: set[tuple[int, int]] = set()
            if name == "algorithm":
                assert destination.pdf_version == "1.7"
                assert destination.Root["/Extensions"]["/ADBE"]["/BaseVersion"] == pikepdf.Name(
                    "/1.7"
                )
                assert destination.Root["/Extensions"]["/ADBE"]["/ExtensionLevel"] == 3
            for n, (source, number, role) in enumerate(expected, 1):
                with pikepdf.Pdf.open(source, attempt_recovery=False) as original:
                    a, b = original.pages[number - 1].obj, destination.pages[n - 1].obj
                    ga, gb = geometry(a), geometry(b)
                    assert ga == gb
                    ra, rb = streams(a), streams(b)
                    assert ra == rb
                    marker = b["/BookScanBuilder"]
                    assert marker.is_indirect and marker.objgen not in markers
                    markers.add(marker.objgen)
                    assert str(marker["/Role"]) == role and marker["/SourcePage"] == number
                    assert (
                        str(marker["/SourceSHA256"]) == before[str(source)]
                        and marker["/Version"] == 1
                    )
                    page_record: dict[str, Json] = {
                        "output_page": n,
                        "source": str(source),
                        "source_page": number,
                        "role": role,
                        "geometry": ga,
                        "raw_streams": ra,
                        "renders": [],
                    }
                    renders: list[Json] = []
                    for view in (
                        ["cropbox", "mediabox"] if ga["MediaBox"] != ga["CropBox"] else ["cropbox"]
                    ):
                        folder = artifacts / f"{name}-page-{n}-{view}"
                        folder.mkdir()
                        old, old_command = render(
                            source, number, folder / "before", view == "cropbox"
                        )
                        new, new_command = render(output, n, folder / "after", view == "cropbox")
                        assert (
                            old["dimensions"] == new["dimensions"]
                            and old["rgb_sha256"] == new["rgb_sha256"]
                        )
                        renders.append(
                            {
                                "view": view,
                                "before": old,
                                "after": new,
                                "commands": cast(list[Json], [old_command, new_command]),
                                "exact_rgb_equal": True,
                            }
                        )
                    page_record["renders"] = renders
                    pages.append(page_record)
        # Text fixtures must remain searchable as well as visibly identical.
        text_command = ["pdftotext", str(output), "-"]
        text = subprocess.check_output(text_command, text=True)
        if name in {"interleaved", "repeat-roles", "descending", "exclusions", "assembled"}:
            extracted = text.split()
            wanted = [
                (("K" if "covers" in p.name else "C" if "content" in p.name else "P") + str(n))
                for p, n, _ in expected
            ]
            assert extracted == wanted, (extracted, wanted)
        records.append(
            {
                "case": name,
                "command": cast(list[Json], command),
                "planned": cast(dict[str, Json], planned),
                "written": cast(dict[str, Json], result),
                "pages": pages,
                "text_command": cast(list[Json], text_command),
                "extracted_text": text,
            }
        )
        print(
            f"{name}: {len(expected)} pages, geometry/resources/300-dpi RGB matched",
            file=sys.stderr,
        )
    after = {str(p): digest(p) for p in subjects}
    assert before == after
    versions: dict[str, Json] = {
        "python": sys.version,
        "pikepdf": pikepdf.__version__,
        "qpdf": pikepdf.__libqpdf_version__,
    }
    for name, command in {
        "uv": ["uv", "--version"],
        "task": ["task", "--version"],
        "poppler": ["pdftoppm", "-v"],
    }.items():
        version = subprocess.run(command, capture_output=True, text=True, check=True)
        versions[name] = (version.stdout + version.stderr).strip()
    report = {
        "schema_version": 1,
        "mode": mode,
        "artifacts": str(artifacts),
        "versions": versions,
        "digests_before": before,
        "digests_after": after,
        "cases": records,
        "fault_checks": {
            "command": checks_command,
            "stdout": checks.stdout,
            "stderr": checks.stderr,
            "junit": str(artifacts / "fault-checks.xml"),
            "observed_signal_and_kill_cases": evidence,
        },
        "human_visual_approval": "pending: page-geometry-k4 owns the separate preparation response",
    }
    (artifacts / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(artifacts / "report.json")


if __name__ == "__main__":
    main()
