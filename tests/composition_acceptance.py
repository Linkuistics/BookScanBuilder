"""Independent analytic device-colour compositions through the actual Cairo adapter.

Required font/profile/complex-real truth and the complete saved project stay live.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pikepdf
from composition_truth import Truth, compare
from PIL import Image
from render_identity import linked_files

from bookscan.intake import snapshot
from bookscan.render import render_page, renderer_path

SIZE = (64, 32)
NAMES = (
    "gray-8",
    "gray-1-fine",
    "inline-gray",
    "stencil",
    "stencil-reversed",
    "explicit-mask",
    "colour-key-reversed",
    "soft-mask",
    "half-pixel-gray",
)
PHASE_ROW = (255, 255, 0, 255, 85, 170, 85, 255)


def truth(name: str) -> Truth:
    """No product sample decoder, placement walker or renderer computes this truth."""
    low, high = bytearray(), bytearray()
    for y in range(32):
        for x in range(64):
            paint = (x // 8 + y // 8) % 3 == 0
            if name in {"gray-8", "inline-gray"}:
                pixel = bytes([85 * ((x // 8 + 2 * (y // 8)) % 4)]) * 3
            elif name == "gray-1-fine":
                pixel = bytes([255 * (x % 2)]) * 3
            elif name in {"stencil", "stencil-reversed"}:
                if name == "stencil-reversed":
                    paint = not paint
                pixel = b"\0\0\xff" if paint else b"\0\xff\0"
            elif name == "explicit-mask":
                pixel = b"\xff\0\0" if paint else b"\0\xff\0"
            elif name == "colour-key-reversed":
                pixel = b"\0\xff\0" if paint else b"\0\0\0"
            elif name == "soft-mask":
                # ISO 32000-1 11.6.5.3: unpremultiplied pure red over pure blue.
                # Alpha 0,85,170,255 gives exact integer channels without rounding.
                alpha = 85 * ((x // 8 + 2 * (y // 8)) % 4)
                pixel = bytes([alpha, 0, 255 - alpha])
            elif name == "half-pixel-gray":
                # Source cell s covers [0.5+2s, 2.5+2s). A destination pixel
                # covers [x,x+1). Only overlapping cells may contribute. Exact
                # interiors stay exact; boundary mixtures must stay neutral and
                # inside this local convex interval. No fitted colour tolerance.
                candidates = [
                    PHASE_ROW[s % 8]
                    for s in range(32)
                    if 1 + 4 * s < 2 * x + 2 and 5 + 4 * s > 2 * x
                ]
                if x == 0:
                    candidates.append(255)  # exposed white background
                low.extend(bytes([min(candidates)]) * 3)
                high.extend(bytes([max(candidates)]) * 3)
                continue
            else:
                raise ValueError(name)
            low.extend(pixel)
            high.extend(pixel)
    return Truth(SIZE, bytes(low), bytes(high), name == "half-pixel-gray")


def image(
    pdf: pikepdf.Pdf, data: bytes, size: tuple[int, int], bits: int = 8, stencil: bool = False
) -> pikepdf.Object:
    result = pikepdf.Stream(pdf, data)
    result.Type, result.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
    result.Width, result.Height = size
    result.BitsPerComponent = bits
    result.Interpolate = False
    if stencil:
        result.ImageMask = True
    else:
        result.ColorSpace = pikepdf.Name.DeviceGray
    return result


def construct(path: Path) -> None:
    # ISO 32000-1 8.9.4/8.9.6/8.9.7/11.6.5.3 supply sample/paint/alpha semantics.
    # https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
    # Unfiltered aligned 300-ppi samples, or literal 37.5-ppi inline cells.
    with pikepdf.Pdf.new() as pdf:
        for name in NAMES:
            page = pdf.add_blank_page(page_size=(15.36, 7.68))
            page.obj.Resources = pikepdf.Dictionary()
            cell_bits = bytes(
                sum(
                    (int((x // 8 + y // 8) % 3 != 0) << (7 - x % 8))
                    for x in range(start, start + 8)
                )
                for y in range(32)
                for start in range(0, 64, 8)
            )
            gray = bytes(85 * ((x // 8 + 2 * (y // 8)) % 4) for y in range(32) for x in range(64))
            prefix = b""
            if name == "inline-gray":
                raw = bytes(85 * ((x + 2 * y) % 4) for y in range(4) for x in range(8))
                body = (
                    b"q 15.36 0 0 7.68 0 0 cm BI /W 8 /H 4 /BPC 8 "
                    b"/CS /G /I false ID " + raw + b"\nEI Q"
                )
                form = pikepdf.Stream(pdf, body)
                form.Type, form.Subtype = pikepdf.Name.XObject, pikepdf.Name.Form
                form.BBox = pikepdf.Array([0, 0, 15.36, 7.68])
                form.Resources = pikepdf.Dictionary()
                page.obj.Resources.XObject = pikepdf.Dictionary(Form=form)
                page.obj.Contents = pikepdf.Stream(pdf, b"q /Form Do Q")
                continue
            if name == "gray-8":
                im = image(pdf, gray, SIZE)
            elif name == "gray-1-fine":
                im = image(pdf, b"\x55" * 256, SIZE, bits=1)
            elif name in {"stencil", "stencil-reversed"}:
                im = image(pdf, cell_bits, SIZE, bits=1, stencil=True)
                if name == "stencil-reversed":
                    im.Decode = pikepdf.Array([1, 0])
                prefix = b"0 1 0 rg 0 0 15.36 7.68 re f 0 0 1 rg "
            elif name == "explicit-mask":
                im = image(pdf, b"\xff\0\0" * 2048, SIZE)
                im.ColorSpace = pikepdf.Name.DeviceRGB
                im.Mask = image(pdf, cell_bits, SIZE, bits=1, stencil=True)
                prefix = b"0 1 0 rg 0 0 15.36 7.68 re f "
            elif name == "colour-key-reversed":
                raw = bytes(
                    0 if (x // 8 + y // 8) % 3 == 0 else 255 for y in range(32) for x in range(64)
                )
                im = image(pdf, raw, SIZE)
                im.Decode = pikepdf.Array([1, 0])
                im.Mask = pikepdf.Array([0, 0])
                prefix = b"0 1 0 rg 0 0 15.36 7.68 re f "
            elif name == "soft-mask":
                im = image(pdf, b"\xff\0\0" * 2048, SIZE)
                im.ColorSpace = pikepdf.Name.DeviceRGB
                im.SMask = image(pdf, gray, SIZE)
                prefix = b"0 0 1 rg 0 0 15.36 7.68 re f "
            else:
                assert name == "half-pixel-gray"
                raw = bytes(PHASE_ROW[x % 8] for _ in range(16) for x in range(32))
                im = image(pdf, raw, (32, 16))
            page.obj.Resources.XObject = pikepdf.Dictionary(Im=im)
            offset = b"0.12" if name == "half-pixel-gray" else b"0"
            page.obj.Contents = pikepdf.Stream(
                pdf, prefix + b"q 15.36 0 0 7.68 " + offset + b" 0 cm /Im Do Q"
            )
        pdf.add_blank_page(page_size=(15.36, 7.68))
        pdf.pages.append(pdf.pages[0])  # pyright: ignore[reportUnknownMemberType]
        pdf.save(path, min_version="1.7", deterministic_id=True)


def run(artifacts: Path) -> dict[str, object]:
    artifacts.mkdir()
    truths = {name: truth(name) for name in NAMES}
    manifest = {
        "version": 1,
        "size": SIZE,
        "points": ["15.36", "7.68"],
        "bounds": {
            name: {
                "low_sha256": hashlib.sha256(t.low).hexdigest(),
                "high_sha256": hashlib.sha256(t.high).hexdigest(),
                "grey": t.grey,
            }
            for name, t in truths.items()
        },
        "bound_policy": "Exact every channel, except half-pixel local convex bounds/neutral grey",
        "phase": "150-ppi samples translated +0.5 baseline pixel, independent cell intersections",
        "unavailable": "ICC/device calibration/fonts/Matte/general blending/complex real truth",
    }
    truth_path = artifacts / "truth.json"
    truth_path.write_text(json.dumps(manifest, indent=2) + "\n")
    # Keep the complete per-pixel bounds as independent subjects before any render.
    for name, t in truths.items():
        (artifacts / f"{name}.low.rgb").write_bytes(t.low)
        (artifacts / f"{name}.high.rgb").write_bytes(t.high)
    truth_files = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [truth_path, *sorted(artifacts.glob("*.rgb"))]
    }
    source = artifacts / "Ordinary masks and samples.pdf"
    construct(source)
    saved = snapshot(source, artifacts / "snapshot.pdf")
    renderer = renderer_path()
    expected_points = (Decimal("15.36"), Decimal("7.68"))
    blank = Truth(SIZE, b"\xff" * 6144, b"\xff" * 6144)
    all_truth = [*truths.values(), blank, truths[NAMES[0]]]
    records: list[dict[str, object]] = []
    rasters: list[bytes] = []
    for page, wanted in zip(saved.pages, all_truth, strict=True):
        assert page.frame.points == expected_points and page.frame.pixels == SIZE
        raster = render_page(saved, page, renderer)
        counts = compare(raster.size, raster.rgb, wanted)
        rasters.append(raster.rgb)
        with Image.frombytes("RGB", raster.size, raster.rgb) as png:
            png.save(artifacts / f"page-{page.source_page}.png")
        records.append(
            {
                "source_page": page.source_page,
                "size": raster.size,
                "points": [str(v) for v in page.frame.points],
                **counts,
                "rgb_sha256": hashlib.sha256(raster.rgb).hexdigest(),
                "diagnostics": raster.diagnostics,
                "command": [
                    v.replace(str(artifacts), "<ARTIFACTS>")
                    if v != raster.command[-1]
                    else "<PRIVATE_PREFIX>"
                    for v in raster.command
                ],
            }
        )
    controls: dict[str, str] = {}
    wrong_key = bytes(
        channel
        for y in range(32)
        for x in range(64)
        for channel in ((255, 255, 255) if (x // 8 + y // 8) % 3 == 0 else (0, 255, 0))
    )
    subjects = {
        "wrong-image": (0, rasters[9]),
        "wrong-order": (0, rasters[1]),
        "wrong-stencil-polarity": (3, rasters[4]),
        "missing-explicit-mask": (5, b"\xff\0\0" * 2048),
        "key-after-decode": (6, wrong_key),
        "missing-soft-mask": (7, b"\xff\0\0" * 2048),
        "erased-one-pixel-feature": (1, b"\xff" * 6144),
    }
    # Half-pixel sample #2 has guaranteed black interior x=5; replacing just
    # that narrow feature with white must fail while all other pixels stay intact.
    erased = bytearray(rasters[8])
    for y in range(32):
        i = (y * 64 + 5) * 3
        erased[i : i + 3] = b"\xff" * 3
    subjects["erased-misaligned-feature"] = (8, bytes(erased))
    wrong_colour = bytearray(rasters[7])
    wrong_colour[0] ^= 1
    subjects["wrong-colour"] = (7, bytes(wrong_colour))
    # Real native controls alter one source mechanism, with geometry and source
    # positions held constant. The unaffected inline page still passes.
    for name, index in [
        ("native-missing-explicit-mask", 5),
        ("native-missing-soft-mask", 7),
        ("native-wrong-phase", 8),
    ]:
        wrong_path = artifacts / f"{name}.pdf"
        with pikepdf.Pdf.open(saved.path) as pdf:
            page = pdf.pages[index]
            if index == 5:
                del page.obj.Resources.XObject.Im.Mask
            elif index == 7:
                del page.obj.Resources.XObject.Im.SMask
            else:
                page.obj.Contents = pikepdf.Stream(pdf, b"q 15.36 0 0 7.68 0.60 0 cm /Im Do Q")
            pdf.save(wrong_path, min_version="1.7", deterministic_id=True)
        wrong_saved = snapshot(wrong_path, artifacts / f"{name}-snapshot.pdf")
        assert [p.frame for p in wrong_saved.pages] == [p.frame for p in saved.pages]
        bad = render_page(wrong_saved, wrong_saved.pages[index], renderer)
        subjects[name] = (index, bad.rgb)
        unaffected = render_page(wrong_saved, wrong_saved.pages[2], renderer)
        compare(unaffected.size, unaffected.rgb, all_truth[2])
    for name, (index, data) in subjects.items():
        try:
            compare(SIZE, data, all_truth[index])
        except AssertionError as error:
            controls[name] = str(error)
        else:
            raise AssertionError(f"Wrong subject escaped: {name}")
        compare(SIZE, rasters[2], all_truth[2])  # unrelated inline check stays green
        saved.verify()
    source.unlink()
    for page, wanted in zip(saved.pages, all_truth, strict=True):
        resumed = render_page(saved, page, renderer)
        compare(resumed.size, resumed.rgb, wanted)
        assert resumed.rgb == rasters[page.source_page - 1]
    assert truth_path.read_text() == json.dumps(manifest, indent=2) + "\n"
    assert truth_files == {
        name: hashlib.sha256((artifacts / name).read_bytes()).hexdigest() for name in truth_files
    }
    report: dict[str, object] = {
        "truth": manifest,
        "truth_sha256": hashlib.sha256(truth_path.read_bytes()).hexdigest(),
        "source_sha256": saved.sha256,
        "pre_output_truth_files_sha256": truth_files,
        "native_identity": linked_files(renderer),
        "pages": records,
        "controls": controls,
        "source_loss_verified": True,
        "source_snapshot_bytes_unchanged": True,
        "accepted_project_delivered": False,
        "complete_composition_fidelity_verified": False,
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
