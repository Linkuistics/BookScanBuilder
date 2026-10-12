"""Reject scaled, clipped and blurred subjects before crediting native display."""

import math
from pathlib import Path

import pytest
from native_view_scale import measure, write_ruler
from PIL import Image, ImageDraw


def constructed_capture(path: Path, scale: int = 1, blur_bands: bool = False) -> None:
    # Independent fixture: literal source frame/sample positions, no ruler builder reuse.
    with Image.new("RGB", (800, 700), "white") as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle((100, 150, 100 + 512 * scale - 1, 150 + 352 * scale - 1), "red")
        draw.rectangle((101, 151, 100 + 512 * scale - 2, 150 + 352 * scale - 2), "white")
        if scale == 1:
            for x in range(132, 580):
                colour = "gray" if blur_bands else "black" if x % 2 == 0 else "white"
                draw.line((x, 182, x, 245), fill=colour)
            for y in range(278, 470):
                draw.line((132, y, 195, y), fill="black" if y % 2 == 0 else "white")
        image.save(path)


def test_native_ruler_requires_unit_frame_and_one_pixel_bands(tmp_path: Path) -> None:
    path = tmp_path / "native.png"
    constructed_capture(path)
    result = measure(path, (0, 100, 800, 700), (800, 700))
    assert result.passed
    assert result.frame == (100, 150, 612, 502)
    assert (result.horizontal_samples, result.vertical_samples) == (28672, 12288)


@pytest.mark.parametrize("kind", ["scaled", "blurred", "resized-capture", "clipped"])
def test_wrong_subject_cannot_supply_native_measurement(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "wrong.png"
    constructed_capture(path, scale=2 if kind == "scaled" else 1, blur_bands=kind == "blurred")
    region = (0, 100, 800, 400) if kind == "clipped" else (0, 100, 800, 700)
    expected = (1600, 1400) if kind == "resized-capture" else (800, 700)
    assert not measure(path, region, expected).passed


def test_ruler_density_does_not_resample_pixels_or_overwrite(tmp_path: Path) -> None:
    first = tmp_path / "one.png"
    second = tmp_path / "two.png"
    write_ruler(first, 1.0)
    write_ruler(second, 2.0)
    with Image.open(first) as one, Image.open(second) as two:
        assert one.size == (640, 480)
        assert one.tobytes() == two.tobytes()
        assert one.getpixel((96, 96)) == (0, 0, 0)
        assert one.getpixel((97, 96)) == (255, 255, 255)
        assert math.isclose(float(two.info["dpi"][0]), 144, abs_tol=0.02)
    before = first.read_bytes()
    with pytest.raises(FileExistsError):
        write_ruler(first, 1.0)
    assert first.read_bytes() == before


@pytest.mark.parametrize("scale", [0.0, -1.0, float("inf"), float("nan")])
def test_ruler_requires_measured_finite_positive_backing_scale(
    tmp_path: Path, scale: float
) -> None:
    path = tmp_path / "bad.png"
    with pytest.raises(ValueError, match="backing scale"):
        write_ruler(path, scale)
    assert not path.exists()
