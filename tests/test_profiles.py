"""Catch ignored ICC curves, mistaken Decode order and profile fallback."""

import hashlib
from dataclasses import replace
from fractions import Fraction as F

import pytest
from icc_fixtures import profile
from test_colour import indexed, sample

from bookscan import samples


def subject(packed: bytes = bytes([64, 128, 192]), *, gamma: int = 2) -> samples.Sample:
    return sample(
        packed,
        color=samples.Color(
            "/ICCBased", 3, b"null", profile=profile(gamma), ranges=(F(0), F(1)) * 3
        ),
        decode=(F(0), F(1)) * 3,
    )


def test_profile_conversion_changes_channels_without_mutating_source():
    from bookscan import profiles

    original = subject()
    result = profiles.display(original, profile(1))
    assert result.view.unavailable is None and result.view.size == (1, 1)
    assert result.view.rgb is not None
    assert all(abs(a - b) <= 1 for a, b in zip(result.view.rgb, [16, 64, 145], strict=True))
    assert result.input_profile_sha256 == hashlib.sha256(profile(2)).hexdigest()
    assert result.output_profile_sha256 == hashlib.sha256(profile(1)).hexdigest()
    assert result.intent == 1 and result.flags == 256 and result.littlecms == "2.19"
    assert result.view.colour_space == "/ICCBased" and "uncombined" in result.view.label
    assert original == subject() and not original.composition_verified


def test_profile_decode_precedes_conversion_and_raw_key_alpha_stays_separate():
    from bookscan import profiles

    original = replace(subject(), decode=(F(1), F(0)) * 3, color_key=(64, 64, 128, 128, 192, 192))
    result = profiles.display(original, profile(1))
    assert result.view.rgb is not None
    assert all(abs(a - b) <= 1 for a, b in zip(result.view.rgb, [143, 63, 16], strict=True))
    assert result.view.colour_key_alpha == b"\0"


def test_indexed_icc_palette_is_converted_at_its_original_grid():
    from bookscan import profiles

    base = subject().color
    assert base is not None
    original = sample(
        b"\x10",
        width=2,
        bits=2,
        color=indexed(base, bytes([0, 0, 0, 64, 128, 192]), 1),
        decode=(F(0), F(3)),
    )
    result = profiles.display(original, profile(1))
    assert result.view.size == (2, 1) and result.view.rgb is not None
    assert all(
        abs(a - b) <= 1 for a, b in zip(result.view.rgb, [0, 0, 0, 16, 64, 145], strict=True)
    )


@pytest.mark.parametrize("data", [b"", b"invalid", profile()[:-1], profile() + b"trailing"])
def test_invalid_input_profile_is_unavailable_without_device_fallback(data: bytes):
    from bookscan import profiles

    color = samples.Color("/ICCBased", 3, b"null", profile=data, ranges=(F(0), F(1)) * 3)
    result = profiles.display(replace(subject(), color=color), profile())
    assert result.view.rgb is None and result.view.unavailable


@pytest.mark.parametrize(
    "offset,value", [(16, b"GRAY"), (12, b"link"), (36, b"oops"), (8, b"\x05\0\0\0")]
)
def test_incompatible_target_profile_fails_explicitly(offset: int, value: bytes):
    from bookscan import profiles

    target = bytearray(profile())
    target[offset : offset + 4] = value
    result = profiles.display(subject(), bytes(target))
    assert result.view.rgb is None and result.view.unavailable


def test_nonunit_ranges_and_unprofiled_device_cmyk_never_guess_conversion():
    from bookscan import profiles

    for color in [
        samples.Color("/ICCBased", 3, b"null", profile=profile(), ranges=(F(-1), F(1)) * 3),
        samples.Color("/DeviceCMYK", 4, b"null"),
    ]:
        result = profiles.display(replace(subject(), color=color), profile())
        assert result.view.rgb is None and result.view.unavailable


def test_native_failure_does_not_swallow_owner_cancel_between_rows():
    from bookscan import profiles

    original = replace(
        subject(bytes([64, 128, 192]) * 2), placement=replace(subject().placement, samples=(1, 2))
    )
    selected = ValueError("selected owner cancellation")
    calls = 0

    def cancelled() -> None:
        nonlocal calls
        calls += 1
        if calls == 7:
            raise selected

    with pytest.raises(ValueError) as caught:
        profiles.display(original, profile(), check_cancel=cancelled)
    assert caught.value is selected


def test_unavailable_codec_retains_its_reason_before_profile_work():
    from bookscan import profiles

    original = replace(subject(), packed=None, unavailable="native codec missing truth")
    result = profiles.display(original, b"invalid")
    assert result.view.rgb is None and result.view.unavailable == original.unavailable


@pytest.mark.parametrize("packed", [b"\x40\x80", b"\x40\x80\xc0\x00"])
def test_incomplete_or_extra_source_channels_are_not_silently_converted(packed: bytes):
    from bookscan import profiles

    result = profiles.display(subject(packed), profile())
    assert result.view.rgb is None and result.view.unavailable


def test_missing_profile_transform_tables_are_unavailable():
    from bookscan import profiles

    target = bytearray(profile())
    target[128:132] = b"\0\0\0\0"
    result = profiles.display(subject(), bytes(target))
    assert result.view.rgb is None and result.view.unavailable
