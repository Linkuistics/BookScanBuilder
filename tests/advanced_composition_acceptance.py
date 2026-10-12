"""Actual Cairo construction controls for embedded text, Matte, Screen and 600 ppi.

No system-font/ICC/real-page truth, saved project or public workflow is supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pikepdf
from advanced_composition_truth import detail_loss, truth
from composition_truth import Truth, compare
from PIL import Image
from render_identity import linked_files

from bookscan.intake import snapshot
from bookscan.render import render_page, renderer_path
from bookscan.samples import collect

SIZE = (64, 32)
NAMES = ("type3-text", "matte-white", "matte-black", "screen-group", "600-ppi-detail")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def native_gray() -> bytes:
    return bytes(
        255 * (x % 2) if x < 64 else (0 if x < 96 else 255) for _ in range(64) for x in range(128)
    )


def image(pdf: pikepdf.Pdf, data: bytes, size: tuple[int, int], rgb: bool) -> pikepdf.Object:
    result = pikepdf.Stream(pdf, data)
    result.Type, result.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
    result.Width, result.Height = size
    result.ColorSpace = pikepdf.Name.DeviceRGB if rgb else pikepdf.Name.DeviceGray
    result.BitsPerComponent, result.Interpolate = 8, False
    return result


def construct(path: Path, native: bytes) -> None:
    # ISO 32000-1 9.6.5, 11.3.5/Table136, 11.6.5.3/Table145 and 11.6.6.
    # https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
    # Independent truth is declared before calling the renderer. Embedded glyph
    # programs avoid using a system font or a second rasterizer as the oracle.
    with pikepdf.Pdf.new() as pdf:
        for name in NAMES:
            page = pdf.add_blank_page(page_size=(15.36, 7.68))
            page.obj.Resources = pikepdf.Dictionary()
            if name == "type3-text":
                font = pdf.make_indirect(
                    pikepdf.Dictionary(
                        Type=pikepdf.Name.Font,
                        Subtype=pikepdf.Name.Type3,
                        FontBBox=pikepdf.Array([0, 0, 1000, 1000]),
                        FontMatrix=pikepdf.Array([Decimal(".001"), 0, 0, Decimal(".001"), 0, 0]),
                        Encoding=pikepdf.Dictionary(
                            Type=pikepdf.Name.Encoding,
                            Differences=pikepdf.Array([65, pikepdf.Name.A, pikepdf.Name.B]),
                        ),
                        FirstChar=65,
                        LastChar=66,
                        Widths=pikepdf.Array([1000, 1000]),
                        Resources=pikepdf.Dictionary(),
                        CharProcs=pikepdf.Dictionary(
                            A=pikepdf.Stream(pdf, b"1000 0 0 0 1000 1000 d1 0 0 1000 1000 re f"),
                            B=pikepdf.Stream(
                                pdf,
                                b"1000 0 0 0 1000 1000 d1 0 0 250 1000 re "
                                b"750 0 250 1000 re 250 0 500 250 re 250 750 500 250 re f",
                            ),
                        ),
                    )
                )
                im = image(pdf, b"\xff\0\xff\0\xff\xff", (2, 1), True)
                page.obj.Resources.Font = pikepdf.Dictionary(F=font)
                page.obj.Resources.XObject = pikepdf.Dictionary(Im=im)
                body = (
                    b"q 7.68 0 0 3.84 0 3.84 cm /Im Do Q "
                    b"0 1 0 rg 7.68 3.84 7.68 3.84 re f "
                    b"0 0 0 rg BT /F 3.84 Tf 0 0 Td (AB) Tj ET"
                )
            elif name in {"matte-white", "matte-black"}:
                alpha = bytes(
                    85 if (x // 8 + y // 8) % 2 == 0 else 170 for y in range(32) for x in range(64)
                )
                raw = bytes(
                    c
                    for a in alpha
                    for c in ((255, 255 - a, 255 - a) if name == "matte-white" else (a, 0, 0))
                )
                im = image(pdf, raw, SIZE, True)
                mask = image(pdf, alpha, SIZE, False)
                mask.Matte = pikepdf.Array([1, 1, 1] if name == "matte-white" else [0, 0, 0])
                im.SMask = mask
                page.obj.Resources.XObject = pikepdf.Dictionary(Im=im)
                body = b"0 0 1 rg 0 0 15.36 7.68 re f q 15.36 0 0 7.68 0 0 cm /Im Do Q"
            elif name == "screen-group":
                form = pikepdf.Stream(
                    pdf,
                    b"0 0 1 rg 0 0 15.36 7.68 re f /Blend gs 1 0 0 rg 0 0 7.68 7.68 re f",
                )
                form.Type, form.Subtype = pikepdf.Name.XObject, pikepdf.Name.Form
                form.BBox = pikepdf.Array([0, 0, 15.36, 7.68])
                form.Group = pikepdf.Dictionary(
                    S=pikepdf.Name.Transparency, I=True, CS=pikepdf.Name.DeviceRGB
                )
                form.Resources = pikepdf.Dictionary(
                    ExtGState=pikepdf.Dictionary(Blend=pikepdf.Dictionary(BM=pikepdf.Name.Screen))
                )
                page.obj.Resources.XObject = pikepdf.Dictionary(Form=form)
                body = b"q /Form Do Q"
            else:
                assert name == "600-ppi-detail"
                page.obj.Resources.XObject = pikepdf.Dictionary(
                    Im=image(pdf, native, (128, 64), False)
                )
                body = b"q 15.36 0 0 7.68 0 0 cm /Im Do Q"
            page.obj.Contents = pikepdf.Stream(pdf, body)
        pdf.add_blank_page(page_size=(15.36, 7.68))
        pdf.pages.append(pdf.pages[0])  # pyright: ignore[reportUnknownMemberType]
        pdf.save(path, min_version="1.7", deterministic_id=True)


def run(artifacts: Path) -> dict[str, object]:
    artifacts.mkdir()
    declared = {name: truth(name) for name in NAMES}
    native = native_gray()
    classification = "failed (signed >300-ppi resolution limitation), synthetic only"
    manifest = {
        "version": 1,
        "size": SIZE,
        "points": ["15.36", "7.68"],
        "bounds": {
            name: {"low_sha256": digest(t.low), "high_sha256": digest(t.high), "grey": t.grey}
            for name, t in declared.items()
        },
        "policy": "Exact embedded glyph/image/vector, primary Matte and isolated Screen channels",
        "matte": "c' = m + alpha*(c-m); red, alpha=1/3 or 2/3, white/black matte; blue backdrop",
        "screen": "B(cb,cs)=1-(1-cb)*(1-cs); opaque red over opaque blue inside isolated RGB group",
        "detail": {
            "native_size": [128, 64],
            "ppi": [600, 600],
            "native_sha256": digest(native),
            "comparison": (
                "Aligned 2:1, constant baseline texel at each native source sample centre"
            ),
            "fine_band": [0, 0, 64, 64],
            "minimum_changed_native_samples": 2048,
            "baseline_bound": (
                "Neutral local 0..255 at fine band/macro transitions; exact macro interiors"
            ),
            "classification": classification,
        },
        "unavailable": (
            "ICC/device calibration/arbitrary fonts/general blend modes/"
            "complex real truth/runtime resources"
        ),
    }
    truth_path = artifacts / "truth.json"
    truth_path.write_text(json.dumps(manifest, indent=2) + "\n")
    for name, wanted in declared.items():
        (artifacts / f"{name}.low.rgb").write_bytes(wanted.low)
        (artifacts / f"{name}.high.rgb").write_bytes(wanted.high)
    (artifacts / "600-ppi.gray").write_bytes(native)
    truth_files = {p.name: digest(p.read_bytes()) for p in artifacts.iterdir() if p.is_file()}
    source = artifacts / "Ordinary text Matte and fine detail.pdf"
    construct(source, native)
    saved = snapshot(source, artifacts / "snapshot.pdf")
    renderer = renderer_path()
    blank = Truth(SIZE, b"\xff" * 6144, b"\xff" * 6144)
    truths = [*declared.values(), blank, declared[NAMES[0]]]
    records: list[dict[str, object]] = []
    rasters: list[bytes] = []
    for page, wanted in zip(saved.pages, truths, strict=True):
        assert page.frame.points == (Decimal("15.36"), Decimal("7.68"))
        assert page.frame.pixels == SIZE
        raster = render_page(saved, page, renderer)
        counts = compare(raster.size, raster.rgb, wanted)
        rasters.append(raster.rgb)
        with Image.frombytes("RGB", raster.size, raster.rgb) as png:
            png.save(artifacts / f"page-{page.source_page}.png")
        records.append(
            {
                "source_page": page.source_page,
                "size": raster.size,
                "points": [str(p) for p in page.frame.points],
                **counts,
                "rgb_sha256": digest(raster.rgb),
                "diagnostics": raster.diagnostics,
                "command": [
                    v.replace(str(artifacts), "<ARTIFACTS>")
                    if v != raster.command[-1]
                    else "<PRIVATE_PREFIX>"
                    for v in raster.command
                ],
            }
        )
    inventory = collect(saved, saved.pages[4])
    assert inventory.resolution.complete and len(inventory.images) == 1
    sample = inventory.images[0]
    assert sample.packed == native and sample.placement.samples == (128, 64)
    assert sample.placement.ppi == (600.0, 600.0)
    assert sample.placement.above_baseline_resolution and not sample.composition_verified
    lost = detail_loss(SIZE, rasters[4], (128, 64), native)
    assert lost["changed_native_pixels"] >= 2048
    controls: dict[str, str] = {}
    wrong_resolution = artifacts / "native-wrong-resolution.pdf"
    with pikepdf.Pdf.open(saved.path) as pdf:
        pdf.pages[4].obj.Contents = pikepdf.Stream(pdf, b"q 7.68 0 0 7.68 0 0 cm /Im Do Q")
        pdf.save(wrong_resolution, min_version="1.7", deterministic_id=True)
    wrong_saved = snapshot(wrong_resolution, artifacts / "native-wrong-resolution-snapshot.pdf")
    wrong_sample = collect(wrong_saved, wrong_saved.pages[4]).images[0]
    assert wrong_sample.packed == native
    try:
        assert wrong_sample.placement.ppi == (600.0, 600.0), "physical source ppi differs"
    except AssertionError as error:
        controls["native-wrong-resolution"] = str(error)
    else:
        raise AssertionError("Wrong resolution subject escaped")
    unaffected = render_page(wrong_saved, wrong_saved.pages[1], renderer)
    compare(unaffected.size, unaffected.rgb, truths[1])
    for name, index in [
        ("native-erased-glyph", 0),
        ("native-missing-white-matte", 1),
        ("native-missing-black-matte", 2),
        ("native-wrong-blend", 3),
        ("native-erased-macro-feature", 4),
    ]:
        wrong_source = artifacts / f"{name}.pdf"
        with pikepdf.Pdf.open(saved.path) as pdf:
            page = pdf.pages[index]
            if index == 0:
                page.obj.Resources.Font.F.CharProcs.B = pikepdf.Stream(
                    pdf, b"1000 0 0 0 1000 1000 d1"
                )
            elif index in {1, 2}:
                del page.obj.Resources.XObject.Im.SMask.Matte
            elif index == 3:
                page.obj.Resources.XObject.Form.Resources.ExtGState.Blend.BM = pikepdf.Name.Multiply
            else:
                page.obj.Resources.XObject.Im.write(b"\xff" * 8192)
            pdf.save(wrong_source, min_version="1.7", deterministic_id=True)
        wrong = snapshot(wrong_source, artifacts / f"{name}-snapshot.pdf")
        assert [p.frame for p in wrong.pages] == [p.frame for p in saved.pages]
        bad = render_page(wrong, wrong.pages[index], renderer)
        try:
            compare(bad.size, bad.rgb, truths[index])
        except AssertionError as error:
            controls[name] = str(error)
        else:
            raise AssertionError(f"Wrong native subject escaped: {name}")
        unaffected_index = 3 if index != 3 else 1
        unaffected = render_page(wrong, wrong.pages[unaffected_index], renderer)
        compare(unaffected.size, unaffected.rgb, truths[unaffected_index])
    for name, index, data in [
        ("wrong-image", 0, rasters[5]),
        ("wrong-order", 0, rasters[1]),
        ("erased-native-detail", 4, b"\xff" * 6144),
        ("wrong-colour", 3, b"\0\xff\0" * 2048),
    ]:
        try:
            compare(SIZE, data, truths[index])
        except AssertionError as error:
            controls[name] = str(error)
        else:
            raise AssertionError(f"Wrong subject escaped: {name}")
        compare(SIZE, rasters[2], truths[2])
    source.unlink()
    for page, wanted in zip(saved.pages, truths, strict=True):
        resumed = render_page(saved, page, renderer)
        compare(resumed.size, resumed.rgb, wanted)
        assert resumed.rgb == rasters[page.source_page - 1]
    assert collect(saved, saved.pages[4]) == inventory
    assert truth_files == {name: digest((artifacts / name).read_bytes()) for name in truth_files}
    report: dict[str, object] = {
        "truth": manifest,
        "truth_sha256": digest(truth_path.read_bytes()),
        "source_sha256": saved.sha256,
        "pre_output_truth_files_sha256": truth_files,
        "native_identity": linked_files(renderer),
        "pages": records,
        "controls": controls,
        "source_loss_verified": True,
        "source_snapshot_bytes_unchanged": True,
        "native_detail": {
            **lost,
            "ppi": sample.placement.ppi,
            "packed_sha256": digest(native),
            "sample_record_sha256": sample.raw_sha256,
            "classification": classification,
        },
        "accepted_project_delivered": False,
        "complete_composition_fidelity_verified": False,
        "runtime_resources_verified": False,
        "real_preservation_loss_inferred": False,
    }
    (artifacts / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.artifacts), indent=2))


if __name__ == "__main__":
    main()
