"""Breaks caught: wrong glyph grid, prematted colour, blend or native detail claim."""

import pytest
from advanced_composition_truth import detail_loss, truth
from composition_truth import compare


def pixel(data: bytes, x: int, y: int) -> bytes:
    start = (y * 64 + x) * 3
    return data[start : start + 3]


def test_embedded_text_geometry_includes_holes_and_image() -> None:
    wanted = truth("type3-text")
    assert pixel(wanted.low, 0, 16) == b"\0" * 3
    assert pixel(wanted.low, 16, 16) == b"\0" * 3
    assert pixel(wanted.low, 20, 20) == b"\xff" * 3
    assert pixel(wanted.low, 28, 20) == b"\0" * 3
    assert pixel(wanted.low, 0, 0) == b"\xff\0\xff"
    assert pixel(wanted.low, 16, 0) == b"\0\xff\xff"
    assert pixel(wanted.low, 40, 0) == b"\0\xff\0"
    assert wanted.low == wanted.high
    erased = bytearray(wanted.low)
    erased[(20 * 64 + 28) * 3 : (20 * 64 + 29) * 3] = b"\xff" * 3
    with pytest.raises(AssertionError, match="channel"):
        compare((64, 32), bytes(erased), wanted)


@pytest.mark.parametrize("name", ["matte-white", "matte-black"])
def test_matte_removal_recovers_unassociated_red_before_alpha(name: str) -> None:
    wanted = truth(name)
    assert pixel(wanted.low, 0, 0) == b"\x55\0\xaa"
    assert pixel(wanted.low, 8, 0) == b"\xaa\0\x55"
    assert wanted.low == wanted.high
    wrong = bytearray(wanted.low)
    wrong[1] = 85  # retaining the white matte contaminates green
    with pytest.raises(AssertionError, match="channel 1"):
        compare((64, 32), bytes(wrong), wanted)


def test_isolated_screen_blend_keeps_both_primary_channels() -> None:
    wanted = truth("screen-group")
    assert pixel(wanted.low, 0, 0) == b"\xff\0\xff"
    assert pixel(wanted.low, 32, 0) == b"\0\0\xff"
    with pytest.raises(AssertionError, match="channel 0"):
        compare((64, 32), b"\0\0\xff" * 2048, wanted)


def test_high_resolution_bound_still_rejects_erased_macro_feature() -> None:
    wanted = truth("600-ppi-detail")
    assert pixel(wanted.low, 0, 0) == b"\0" * 3
    assert pixel(wanted.high, 0, 0) == b"\xff" * 3
    assert pixel(wanted.low, 40, 0) == pixel(wanted.high, 40, 0) == b"\0" * 3
    assert pixel(wanted.low, 56, 0) == pixel(wanted.high, 56, 0) == b"\xff" * 3
    with pytest.raises(AssertionError, match="channel"):
        compare((64, 32), b"\xff" * 6144, wanted)


def test_native_detail_witness_reports_actual_missing_source_samples() -> None:
    native = b"\0\xff\0\xff\0\xff\0\xff"  # 4x2 source, 2x1 baseline
    result = detail_loss((2, 1), b"\0" * 3 + b"\xff" * 3, (4, 2), native)
    assert result == {"native_pixels": 8, "changed_native_pixels": 4}
    assert detail_loss((2, 1), b"\x80" * 6, (4, 2), native) == {
        "native_pixels": 8,
        "changed_native_pixels": 8,
    }
    assert detail_loss((2, 1), b"\0" * 6, (4, 2), b"\0" * 8) == {
        "native_pixels": 8,
        "changed_native_pixels": 0,
    }


@pytest.mark.parametrize("size", [(3, 1), (2, 2)])
def test_native_detail_witness_rejects_wrong_mapping(size: tuple[int, int]) -> None:
    with pytest.raises(AssertionError, match="2:1"):
        detail_loss(size, b"\0" * (size[0] * size[1] * 3), (4, 2), b"\0" * 8)


@pytest.mark.parametrize("rgb,native", [(b"\0" * 5, b"\0" * 8), (b"\0" * 6, b"\0" * 7)])
def test_native_detail_witness_rejects_missing_channel_bytes(rgb: bytes, native: bytes) -> None:
    with pytest.raises(AssertionError, match="length"):
        detail_loss((2, 1), rgb, (4, 2), native)
