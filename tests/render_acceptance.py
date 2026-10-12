"""Renderer-independent aligned RGB/physical construction, exercised with actual Poppler."""

import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pikepdf
from PIL import Image
from render_identity import linked_files

from bookscan.intake import snapshot
from bookscan.native_setup import execute, tool
from bookscan.render import render_page, renderer_path

# Pre-output truth: 72 x 36 user-unit MediaBox, lower-left (10,20).
# At UserUnit 1 and 300 dpi that is 300 x 150 pixels, with each source RGB sample
# exactly one output pixel. Scaled cases supply proportionally more samples.
# Vector and static-appearance rectangles align with pixel edges; exact channels
# and full-buffer equality are required, with no output-derived tolerance.
CASES = [
    (rotate, unit, decimal)
    for decimal in (False, True)
    for rotate, unit in [(0, 1), (90, 1), (180, 1), (270, 1), (0, 2), (90, 2)]
]


def pattern(unit: int, decimal: bool = False) -> tuple[tuple[int, int], bytes]:
    width, height = (60, 40) if decimal else (300, 150)
    width, height = width * unit, height * unit
    rgb = bytearray()
    for y in range(height):
        for x in range(width):
            pixel = (17 + x % 43, 23 + y % 71, 91 + (x + y) % 97)
            rgb.extend(pixel)
    return (width, height), bytes(rgb)


def expected(unit: int, rotate: int, decimal: bool = False) -> tuple[tuple[int, int], bytes]:
    (width, height), original = pattern(unit, decimal)
    block = (10 if decimal else 50) * unit
    data = bytearray(original)
    for y in range(height):
        for x in range(width):
            # Green lower-left vector; magenta upper-right static stamp appearance.
            if x < block and y >= height - block:
                data[(y * width + x) * 3 : (y * width + x + 1) * 3] = b"\0\xff\0"
            if x >= width - block and y < block:
                data[(y * width + x) * 3 : (y * width + x + 1) * 3] = b"\xff\0\xff"
    out_size = (height, width) if rotate in (90, 270) else (width, height)
    rotated = bytearray(len(data))
    for y in range(height):
        for x in range(width):
            if rotate == 0:
                xx, yy = x, y
            elif rotate == 90:
                xx, yy = height - 1 - y, x
            elif rotate == 180:
                xx, yy = width - 1 - x, height - 1 - y
            else:
                xx, yy = y, width - 1 - x
            start, target = (y * width + x) * 3, (yy * out_size[0] + xx) * 3
            rotated[target : target + 3] = data[start : start + 3]
    return out_size, bytes(rotated)


def construct(path: Path) -> None:
    with pikepdf.Pdf.new() as pdf:
        for rotate, unit, decimal in CASES:
            w, h = (14.4, 9.6) if decimal else (72, 36)
            block = 2.4 if decimal else 12
            media = [24.4, 29.6, 10, 20] if decimal else [82, 56, 10, 20]
            crop = [20.8, 27.2, 13.6, 22.4] if decimal else [70, 44, 22, 32]
            rect = [22, 27.2, 24.4, 29.6] if decimal else [70, 44, 82, 56]
            page = pdf.add_blank_page(page_size=(72, 36))
            # Reversed diagonal corners deliberately exercise source normalization.
            page.obj.MediaBox = pikepdf.Array(media)
            page.obj.CropBox = pikepdf.Array(crop)
            page.obj.Rotate = rotate
            page.obj.UserUnit = unit
            size, data = pattern(unit, decimal)
            image = pikepdf.Stream(pdf, data)
            image.Type = pikepdf.Name.XObject
            image.Subtype = pikepdf.Name.Image
            image.Width, image.Height = size
            image.BitsPerComponent = 8
            image.ColorSpace = pikepdf.Name.DeviceRGB
            image.Interpolate = False
            inner = pikepdf.Stream(pdf, f"q {w} 0 0 {h} 0 0 cm /Im Do Q".encode())
            inner.Type, inner.Subtype = pikepdf.Name.XObject, pikepdf.Name.Form
            inner.BBox = pikepdf.Array([0, 0, w, h])
            inner.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=image))
            outer = pikepdf.Stream(pdf, b"q 1 0 0 1 0 0 cm /Inner Do Q")
            outer.Type, outer.Subtype = pikepdf.Name.XObject, pikepdf.Name.Form
            outer.BBox = pikepdf.Array([0, 0, w, h])
            outer.Matrix = pikepdf.Array([1, 0, 0, 1, 10, 20])
            outer.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Inner=inner))
            page.obj.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Outer=outer))
            page.obj.Contents = pikepdf.Stream(
                pdf, f"q /Outer Do Q q 0 1 0 rg 10 20 {block} {block} re f Q".encode()
            )
            appearance = pikepdf.Stream(pdf, f"1 0 1 rg 0 0 {block} {block} re f".encode())
            appearance.Type, appearance.Subtype = pikepdf.Name.XObject, pikepdf.Name.Form
            appearance.BBox = pikepdf.Array([0, 0, block, block])
            appearance.Resources = pikepdf.Dictionary()
            annotation = pdf.make_indirect(
                pikepdf.Dictionary(
                    Type=pikepdf.Name.Annot,
                    Subtype=pikepdf.Name.Stamp,
                    Rect=pikepdf.Array(rect),
                    AP=pikepdf.Dictionary(N=appearance),
                    F=4,
                )
            )
            page.obj.Annots = pikepdf.Array([annotation])
        # Blank and duplicate input occurrences are distinct preserved pages.
        blank = pdf.add_blank_page(page_size=(72, 36))
        blank.obj.CropBox = blank.obj.MediaBox
        pdf.pages.append(pdf.pages[0])  # pyright: ignore[reportUnknownMemberType]
        pdf.save(path, min_version="1.7", deterministic_id=True)


def compare(size: tuple[int, int], rgb: bytes, wanted: tuple[tuple[int, int], bytes]) -> None:
    assert size == wanted[0], "pixel extent"
    assert rgb == wanted[1], "independent decoded RGB"


def run(artifacts: Path) -> dict[str, object]:
    artifacts.mkdir()
    truth = {
        "cases": CASES,
        "media_boxes": [[82, 56, 10, 20], [24.4, 29.6, 10, 20]],
        "crop_boxes": [[70, 44, 22, 32], [20.8, 27.2, 13.6, 22.4]],
        "exact_truth": [
            {
                "size": expected(unit, rotate, decimal)[0],
                "rgb_sha256": hashlib.sha256(expected(unit, rotate, decimal)[1]).hexdigest(),
            }
            for rotate, unit, decimal in CASES
        ],
        "bound": "Exact full RGB, grid-aligned unfiltered DeviceRGB; analytic integer permutation",
        "scope": "nested Forms/RGB/vector/static stamp; boxes/Rotate/UserUnit/blank/duplicate",
        "unverified": (
            "font/masks/stencils/grayscale/unaligned/ICC/real composition; "
            "full analyzer; accepted project"
        ),
    }
    truth_path = artifacts / "truth.json"
    truth_path.write_text(json.dumps(truth, indent=2) + "\n")
    input_path = artifacts / "Ordinary composition.pdf"
    construct(input_path)
    saved = snapshot(input_path, artifacts / "snapshot.pdf")
    original_digest = saved.sha256
    renderer = renderer_path()
    records: list[dict[str, object]] = []
    actual: list[tuple[tuple[int, int], bytes]] = []
    for ordinal, page in enumerate(saved.pages):
        raster = render_page(saved, page, renderer)
        if ordinal < len(CASES):
            rotate, unit, decimal = CASES[ordinal]
            wanted = expected(unit, rotate, decimal)
            width, height = ("14.4", "9.6") if decimal else ("72", "36")
            points = (Decimal(width) * unit, Decimal(height) * unit)
            if rotate in (90, 270):
                points = points[::-1]
            assert page.frame.points == points
        elif ordinal == len(CASES):
            wanted = ((300, 150), b"\xff" * (300 * 150 * 3))
        else:
            wanted = expected(1, 0)
        compare(raster.size, raster.rgb, wanted)
        actual.append((raster.size, raster.rgb))
        image_path = artifacts / f"page-{ordinal + 1}.png"
        with Image.frombytes("RGB", raster.size, raster.rgb) as image:
            image.save(image_path)
        records.append(
            {
                "source_page": page.source_page,
                "size": raster.size,
                "points": [str(value) for value in page.frame.points],
                "rgb_sha256": hashlib.sha256(raster.rgb).hexdigest(),
                "diagnostics": raster.diagnostics,
                "command": [
                    value.replace(str(artifacts), "<ARTIFACTS>")
                    if value != raster.command[-1]
                    else "<PRIVATE_PREFIX>"
                    for value in raster.command
                ],
            }
        )
    good = actual[0]
    wrong_pixels = bytearray(good[1])
    wrong_pixels[0] ^= 1
    no_vector = bytearray(good[1])
    no_stamp = bytearray(good[1])
    raw = pattern(1)[1]
    for y in range(150):
        for x in range(300):
            i = (y * 300 + x) * 3
            if x < 50 and y >= 100:
                no_vector[i : i + 3] = raw[i : i + 3]
            if x >= 250 and y < 50:
                no_stamp[i : i + 3] = raw[i : i + 3]
    # Actual wrong CropBox path, with unchanged source bytes and declared RGB oracle.
    prefix = artifacts / "wrong-cropbox"
    command = [
        str(renderer),
        "-f",
        "1",
        "-l",
        "1",
        "-singlefile",
        "-png",
        "-r",
        "300",
        "-cropbox",
        str(saved.path),
        str(prefix),
    ]
    wrong_box = execute(command)
    assert wrong_box.returncode == 0
    with Image.open(prefix.with_suffix(".png")) as image:
        box_record = (image.size, image.tobytes())
    # Independently change only the nested Form translation; physical frame stays green.
    wrong_path = artifacts / "wrong-ctm.pdf"
    with pikepdf.Pdf.open(saved.path) as pdf:
        pdf.pages[0].obj.Resources.XObject.Outer.Matrix = pikepdf.Array([1, 0, 0, 1, 34, 20])
        pdf.save(wrong_path, min_version="1.7", deterministic_id=True)
    wrong_saved = snapshot(wrong_path, artifacts / "wrong-ctm-snapshot.pdf")
    ctm = render_page(wrong_saved, wrong_saved.pages[0], renderer)
    assert wrong_saved.pages[0].frame == saved.pages[0].frame
    controls = {
        "wrong-image": actual[len(CASES)],
        "wrong-rotation": actual[1],
        "wrong-unit": actual[4],
        "wrong-channel": (good[0], bytes(wrong_pixels)),
        "erased-hidden-vector": (good[0], bytes(no_vector)),
        "erased-static-appearance": (good[0], bytes(no_stamp)),
        "wrong-box": box_record,
        "wrong-nested-ctm": (ctm.size, ctm.rgb),
        "wrong-order": actual[2],
    }
    splash_prefix = artifacts / "splash-control"
    splash_command = [
        str(tool("pdftoppm")),
        "-f",
        "1",
        "-l",
        "1",
        "-singlefile",
        "-r",
        "300",
        "-W",
        "300",
        "-H",
        "150",
        str(saved.path),
        str(splash_prefix),
    ]
    splash_result = execute(splash_command)
    assert splash_result.returncode == 0
    with Image.open(splash_prefix.with_suffix(".ppm")) as image:
        controls["splash-unfiltered-preservation"] = (image.size, image.tobytes())
    rejected: dict[str, str] = {}
    for name, bad in controls.items():
        try:
            compare(*bad, expected(1, 0))
        except AssertionError as error:
            rejected[name] = str(error)
        else:
            raise AssertionError(f"Wrong subject escaped: {name}")
        compare(*actual[2], expected(1, 180))
        saved.verify()
    input_path.unlink()
    resumed = render_page(saved, saved.pages[0], renderer)
    compare(resumed.size, resumed.rgb, expected(1, 0))
    assert saved.sha256 == original_digest
    report: dict[str, object] = {
        "native_identity": linked_files(renderer),
        "truth": truth,
        "truth_sha256": hashlib.sha256(truth_path.read_bytes()).hexdigest(),
        "source_sha256": saved.sha256,
        "pages": records,
        "controls": rejected,
        "source_loss_render_passed": True,
        "accepted_project_delivered": False,
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
