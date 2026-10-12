"""Independent matrix/power/Decode/Indexed ICC channels and actual Cairo controls."""

import argparse
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path

import pikepdf
from composition_truth import Truth, compare
from icc_fixtures import profile
from PIL import Image

from bookscan import intake, profiles, render, samples

SIZE = (300, 150)
RAW = bytes([0, 0, 0, 64, 64, 64, 128, 128, 128, 192, 192, 192, 255, 255, 255])
COLOR = bytes([64, 128, 192]) * 5
NAMES = (
    "power-ramp",
    "reverse-decode",
    "indexed",
    "swapped-primaries",
    "default-rgb",
    "invalid-profile",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def declaration() -> tuple[list[bytes], list[Truth]]:
    # Power curves are exactly x**2. Matrix cancels for the explicit linear
    # target. For Cairo's sRGB output use ICC's independent transfer equation.
    # https://registry.color.org/rgb-registry/srgb
    # The two-code Cairo envelope is a DIAGNOSTIC hypothesis only. The actual
    # output-profile matrix/quantization bound has not been independently bound;
    # therefore these comparisons never supply source-fidelity acceptance.
    decoded = [RAW, bytes(255 - v for v in COLOR), COLOR, bytes([192, 128, 64]) * 5, COLOR]
    native = [bytes(math.floor(v * v / 255 + 0.5) for v in row) for row in decoded]
    wanted: list[Truth] = []
    for row in decoded:
        rgb = bytearray()
        for _ in range(SIZE[1]):
            for x in range(SIZE[0]):
                for v in row[(x // 60) * 3 : (x // 60 + 1) * 3]:
                    linear = (v / 255) ** 2
                    encoded = (
                        12.92 * linear
                        if linear <= 0.0031308
                        else 1.055 * linear ** (1 / 2.4) - 0.055
                    )
                    rgb.append(math.floor(encoded * 255 + 0.5))
        wanted.append(
            Truth(SIZE, bytes(max(0, v - 2) for v in rgb), bytes(min(255, v + 2) for v in rgb))
        )
    return native, wanted


def construct(path: Path) -> None:
    with pikepdf.Pdf.new() as pdf:
        for index, name in enumerate(NAMES):
            page = pdf.add_blank_page(page_size=(72, 36))
            icc = pikepdf.Stream(
                pdf,
                b"unverified profile"
                if name == "invalid-profile"
                else profile(2, swapped=name == "swapped-primaries"),
            )
            icc.N, icc.Alternate = 3, pikepdf.Name.DeviceRGB
            space = pikepdf.Array([pikepdf.Name.ICCBased, icc])
            obj = pikepdf.Stream(pdf, RAW if index == 0 else (b"\0" * 5 if index == 2 else COLOR))
            obj.Type, obj.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
            obj.Width, obj.Height, obj.BitsPerComponent, obj.Interpolate = 5, 1, 8, False
            obj.ColorSpace = space
            if name == "reverse-decode":
                obj.Decode = pikepdf.Array([1, 0] * 3)
            if name == "indexed":
                obj.ColorSpace = pikepdf.Array(
                    [pikepdf.Name.Indexed, space, 0, pikepdf.String(bytes([64, 128, 192]))]
                )
            page.obj.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
            if name == "default-rgb":
                obj.ColorSpace = pikepdf.Name.DeviceRGB
                page.obj.Resources.ColorSpace = pikepdf.Dictionary(DefaultRGB=space)
            page.obj.Contents = pikepdf.Stream(
                pdf, b"/RelativeColorimetric ri q 72 0 0 36 0 0 cm /I Do Q"
            )
        pdf.add_blank_page(page_size=(72, 36))
        pdf.pages.append(pdf.pages[0])  # pyright: ignore[reportUnknownMemberType]
        pdf.save(path, deterministic_id=True)


def run(artifacts: Path) -> dict[str, object]:
    artifacts.mkdir()
    native, truths = declaration()
    for index, truth in enumerate(truths):
        (artifacts / f"truth-{index}.low.rgb").write_bytes(truth.low)
        (artifacts / f"truth-{index}.high.rgb").write_bytes(truth.high)
        (artifacts / f"native-{index}.rgb").write_bytes(native[index])
    target = profile(1)
    (artifacts / "linear-target.icc").write_bytes(target)
    (artifacts / "power-input.icc").write_bytes(profile(2))
    manifest = {
        "format": "BookScanBuilderProfileTruth",
        "version": 1,
        "source": "https://www.color.org/specification/ICC1v43_2010-12.pdf",
        "transfer": "https://registry.color.org/rgb-registry/srgb",
        "size": SIZE,
        "native_size": [5, 1],
        "points": [72, 36],
        "native_bound": "1 code: identical matrices cancel; exact x**2 followed by nearest 8-bit",
        "cairo_bound": (
            "Provisional two-code diagnostic envelope; independent target-profile matrix/precision "
            "proof unavailable; no Cairo fidelity pass"
        ),
        "mechanisms": NAMES,
        "native_expected": [v.hex() for v in native],
        "input_profile_sha256": sha(profile(2)),
        "target_profile_sha256": sha(target),
        "limitations": (
            "Constructed RGB profiles only; no real/device calibration, masks, "
            "arbitrary fonts or complete resource provenance"
        ),
    }
    (artifacts / "truth.json").write_text(json.dumps(manifest, indent=2) + "\n")
    truth_subjects = {p.name: sha(p.read_bytes()) for p in artifacts.iterdir()}
    source = artifacts / "Ordinary ICC RGB.pdf"
    construct(source)
    saved = intake.snapshot(source, artifacts / "snapshot.pdf")
    source_bytes = source.read_bytes()
    renderer = render.renderer_path()
    rows: list[dict[str, object]] = []
    images: list[samples.Sample] = []
    for page, name in zip(saved.pages[:6], NAMES, strict=True):
        sample = samples.collect(saved, page).images[0]
        images.append(sample)
        converted = profiles.display(sample, target)
        view = converted.view
        record: dict[str, object] = asdict(converted)
        record["view"] = {
            **asdict(view),
            "rgb": view.rgb.hex() if view.rgb is not None else None,
            "colour_key_alpha": view.colour_key_alpha.hex()
            if view.colour_key_alpha is not None
            else None,
        }
        record.update(name=name, source_page=page.source_page, raw_sha256=sample.raw_sha256)
        if name == "invalid-profile":
            assert view.rgb is None and view.unavailable
        else:
            index = page.source_page - 1
            assert view.rgb is not None and len(view.rgb) == 15
            assert all(abs(a - b) <= 1 for a, b in zip(view.rgb, native[index], strict=True))
            raster = render.render_page(saved, page, renderer)
            record["cairo"] = {
                **compare(raster.size, raster.rgb, truths[index]),
                "rgb_sha256": sha(raster.rgb),
                "fidelity_status": "unavailable: independent target-profile matrix/precision proof",
                "diagnostics": raster.diagnostics,
            }
            with Image.frombytes("RGB", raster.size, raster.rgb) as png:
                png.save(artifacts / f"page-{page.source_page}.png")
        rows.append(record)
    controls: dict[str, str] = {}
    for label, index in [
        ("ignored-input-curve", 4),
        ("wrong-primary-matrix", 4),
        ("ignored-decode", 1),
        ("wrong-indexed-palette", 2),
        ("dropped-default-profile", 4),
        ("erased-source-colour", 3),
    ]:
        wrong = artifacts / f"{label}.pdf"
        with pikepdf.Pdf.open(saved.path) as pdf:
            page = pdf.pages[index]
            if label in {"ignored-input-curve", "wrong-primary-matrix"}:
                replacement = (
                    profile(1) if label == "ignored-input-curve" else profile(2, swapped=True)
                )
                icc = pikepdf.Stream(pdf, replacement)
                icc.N = 3
                page.obj.Resources.ColorSpace.DefaultRGB = pikepdf.Array(
                    [pikepdf.Name.ICCBased, icc]
                )
            elif label == "ignored-decode":
                del page.obj.Resources.XObject.I.Decode
            elif label == "wrong-indexed-palette":
                page.obj.Resources.XObject.I.ColorSpace[3] = pikepdf.String(b"\0\0\0")
            elif label == "dropped-default-profile":
                del page.obj.Resources.ColorSpace.DefaultRGB
            else:
                page.obj.Resources.XObject.I.write(b"\0" * 15)
            pdf.save(wrong, deterministic_id=True)
        ws = intake.snapshot(wrong, artifacts / f"{label}-snapshot.pdf")
        raster = render.render_page(ws, ws.pages[index], renderer)
        try:
            compare(raster.size, raster.rgb, truths[index])
        except AssertionError as error:
            controls[label] = str(error)
        else:
            raise AssertionError("Wrong native profile escaped colour oracle")
        unaffected = render.render_page(ws, ws.pages[0], renderer)
        compare(unaffected.size, unaffected.rgb, truths[0])
        original_sample = images[index]
        wrong_sample = samples.collect(ws, ws.pages[index]).images[0]
        assert wrong_sample.placement.samples == original_sample.placement.samples
        if label != "erased-source-colour":
            assert wrong_sample.packed == original_sample.packed
    source.unlink()
    assert saved.path.read_bytes() == source_bytes
    assert [samples.collect(saved, page).images[0] for page in saved.pages[:6]] == images
    assert not samples.collect(saved, saved.pages[6]).images
    duplicate = samples.collect(saved, saved.pages[7]).images[0]
    assert (
        profiles.display(duplicate, target).view.rgb == profiles.display(images[0], target).view.rgb
    )
    assert all(
        sha((artifacts / name).read_bytes()) == digest for name, digest in truth_subjects.items()
    )
    report: dict[str, object] = {
        "format": "BookScanBuilderProfileConstruction",
        "version": 1,
        "cases": rows,
        "controls": controls,
        "source_sha256": saved.sha256,
        "truth_sha256": sha((artifacts / "truth.json").read_bytes()),
        "source_positions": list(range(1, 9)),
        "source_loss_verified": True,
        "source_bytes_unchanged": True,
        "cairo_fidelity_verified": False,
        "runtime_resources_verified": False,
        "accepted_project_delivered": False,
    }
    (artifacts / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.artifacts), indent=2))
