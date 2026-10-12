"""The fidelity oracle must reject errors even when dimensions stay correct."""

import pytest
from composition_truth import Truth, compare


def test_exact_channels_reject_single_erased_feature() -> None:
    truth = Truth((2, 1), b"\0\0\0\xff\xff\xff", b"\0\0\0\xff\xff\xff")
    assert compare((2, 1), truth.low, truth) == {"exact_pixels": 2, "bounded_pixels": 0}
    with pytest.raises(AssertionError, match="pixel 0 channel 0"):
        compare((2, 1), b"\x01\0\0\xff\xff\xff", truth)


def test_phase_bound_includes_only_local_source_values() -> None:
    truth = Truth((2, 1), b"\x55" * 3 + b"\0" * 3, b"\xaa" * 3 + b"\0" * 3, grey=True)
    assert compare((2, 1), b"\x80" * 3 + b"\0" * 3, truth) == {
        "exact_pixels": 1,
        "bounded_pixels": 1,
    }
    with pytest.raises(AssertionError, match="pixel 0 channel 0"):
        compare((2, 1), b"\xab" * 3 + b"\0" * 3, truth)


def test_phase_bound_cannot_hide_colour_conversion_error() -> None:
    truth = Truth((1, 1), b"\0" * 3, b"\xff" * 3, grey=True)
    with pytest.raises(AssertionError, match="grey neutrality"):
        compare((1, 1), b"\x80\x81\x80", truth)


@pytest.mark.parametrize("size", [(1, 2), (2, 2), (0, 1)])
def test_wrong_physical_raster_extent_is_rejected(size: tuple[int, int]) -> None:
    truth = Truth((2, 1), b"\0" * 6, b"\0" * 6)
    with pytest.raises(AssertionError, match="pixel extent"):
        compare(size, b"\0" * 6, truth)


@pytest.mark.parametrize("data", [b"\0" * 5, b"\0" * 7])
def test_truncated_or_surplus_bytes_are_rejected(data: bytes) -> None:
    truth = Truth((2, 1), b"\0" * 6, b"\0" * 6)
    with pytest.raises(AssertionError, match="RGB length"):
        compare((2, 1), data, truth)


@pytest.mark.parametrize("low,high", [(b"\0", b"\0" * 3), (b"\xff" * 3, b"\0" * 3)])
def test_malformed_or_inverted_truth_is_rejected(low: bytes, high: bytes) -> None:
    truth = Truth((1, 1), low, high)
    with pytest.raises(AssertionError, match="truth"):
        compare((1, 1), b"\0" * 3, truth)
