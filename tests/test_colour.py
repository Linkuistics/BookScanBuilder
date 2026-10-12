"""Hand-derived decoded channels catch inversion, clipping and palette mistakes."""

from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

import pikepdf
import pytest

from bookscan import intake, placement, samples


def sample(
    packed: bytes,
    *,
    bits: int = 8,
    width: int = 1,
    height: int = 1,
    color: samples.Color = samples.Color("/DeviceGray", 1, b"null"),
    decode: tuple[F, ...] = (F(0), F(1)),
    key: tuple[int, ...] | None = None,
) -> samples.Sample:
    placed = placement.Placement(
        ("image",),
        (1, 0),
        "image",
        (width, height),
        bits,
        color.kind,
        (F(1), F(0), F(0), F(1), F(0), F(0)),
        (300, 300),
    )
    return samples.Sample(placed, color, packed, None, decode, False, (), None, None, key, None)


@pytest.mark.parametrize(
    "subject,want,rgb",
    [
        (
            sample(b"\x18\xe4", bits=2, width=3, height=2),
            [(F(0),), (F(1, 3),), (F(2, 3),), (F(1),), (F(2, 3),), (F(1, 3),)],
            b"\x00\x00\x00\x55\x55\x55\xaa\xaa\xaa\xff\xff\xff\xaa\xaa\xaa\x55\x55\x55",
        ),
        (
            sample(b"\x00\x80\xff", width=3, decode=(F(1), F(0))),
            [(F(1),), (F(127, 255),), (F(0),)],
            b"\xff\xff\xff\x7f\x7f\x7f\x00\x00\x00",
        ),
        (
            sample(b"\x00\x80\xff", width=3, decode=(F(-1), F(2))),
            [(F(0),), (F(43, 85),), (F(1),)],
            b"\x00\x00\x00\x81\x81\x81\xff\xff\xff",
        ),
        (
            sample(
                b"\x00\x80\xff",
                color=samples.Color("/DeviceRGB", 3, b"null"),
                decode=(F(1), F(0), F(0), F(1), F(1), F(0)),
            ),
            [(F(1), F(128, 255), F(0))],
            b"\xff\x80\x00",
        ),
        (
            sample(b"\x00\x01\xff\xfe", bits=16, width=2),
            [(F(1, 65535),), (F(65534, 65535),)],
            b"\x00\x00\x00\xff\xff\xff",
        ),
    ],
)
def test_decode_preserves_exact_channels_and_native_grid(
    subject: samples.Sample, want: list[tuple[F, ...]], rgb: bytes
):
    from bookscan import colour

    before = subject.packed
    assert list(colour.channels(subject)) == want
    shown = colour.display(subject)
    assert shown.rgb == rgb and shown.size == subject.placement.samples
    assert shown.colour_space in {"/DeviceGray", "/DeviceRGB"}
    assert shown.unavailable is None and shown.limitations
    assert subject.packed == before and not subject.composition_verified


def indexed(base: samples.Color, palette: bytes, high: int = 2) -> samples.Color:
    return samples.Color("/Indexed", 1, b"null", palette=palette, high=high, base=base)


def test_indexed_decode_rounds_half_up_clips_and_uses_rgb_palette():
    from bookscan import colour

    colors = indexed(
        samples.Color("/DeviceRGB", 3, b"null"), b"\xff\x00\x00\x00\xff\x00\x00\x00\xff"
    )
    subject = sample(b"\x00\x01\x02\xff", width=4, color=colors, decode=(F(1, 2), F(511, 2)))
    assert list(colour.channels(subject)) == [
        (F(0), F(1), F(0)),
        (F(0), F(0), F(1)),
        (F(0), F(0), F(1)),
        (F(0), F(0), F(1)),
    ]
    assert colour.display(subject).rgb == b"\x00\xff\x00" + b"\x00\x00\xff" * 3


def test_indexed_reverse_gray_decode_and_negative_clip():
    from bookscan import colour

    colors = indexed(samples.Color("/DeviceGray", 1, b"null"), b"\x10\x80\xf0")
    subject = sample(b"\x1b", bits=2, width=4, color=colors, decode=(F(2), F(-1)))
    assert list(colour.channels(subject)) == [
        (F(16, 17),),
        (F(128, 255),),
        (F(16, 255),),
        (F(16, 255),),
    ]
    assert colour.display(subject).rgb == b"\xf0" * 3 + b"\x80" * 3 + b"\x10" * 6


def test_colour_key_is_raw_range_before_decode_and_requires_every_component():
    from bookscan import colour

    subject = sample(
        b"\x01\x02\x03\x01\x02\x04",
        width=2,
        color=samples.Color("/DeviceRGB", 3, b"null"),
        decode=(F(1), F(0)) * 3,
        key=(1, 1, 2, 2, 3, 3),
    )
    shown = colour.display(subject)
    assert shown.rgb == b"\xfe\xfd\xfc\xfe\xfd\xfb"
    assert shown.colour_key_alpha == b"\x00\xff"
    assert "uncombined" in shown.label


def test_indexed_colour_key_compares_raw_index_without_palette_clipping():
    from bookscan import colour

    colors = indexed(samples.Color("/DeviceGray", 1, b"null"), b"\x10\xf0", 1)
    subject = sample(b"\x1b", bits=2, width=4, color=colors, decode=(F(0), F(3)), key=(2, 2))
    shown = colour.display(subject)
    assert shown.rgb == b"\x10" * 3 + b"\xf0" * 9
    assert shown.colour_key_alpha == b"\xff\xff\x00\xff"


@pytest.mark.parametrize("kind,components", [("/DeviceCMYK", 4), ("/ICCBased", 3)])
def test_unverified_conversion_keeps_channels_but_does_not_guess_rgb(kind: str, components: int):
    from bookscan import colour

    colors = samples.Color(
        kind,
        components,
        b"null",
        profile=b"not a profile" if kind == "/ICCBased" else None,
        ranges=(F(-1), F(1)) * components if kind == "/ICCBased" else (),
    )
    subject = sample(b"\x00" * components, color=colors, decode=(F(-2), F(2)) * components)
    want = F(-1) if kind == "/ICCBased" else F(0)
    assert list(colour.channels(subject)) == [(want,) * components]
    shown = colour.display(subject)
    assert shown.rgb is None and shown.unavailable and kind in shown.unavailable


def test_indexed_icc_scales_lookup_into_base_ranges_without_fabricating_colour():
    from bookscan import colour

    base = samples.Color(
        "/ICCBased",
        3,
        b"null",
        profile=b"not a profile",
        ranges=(F(-1), F(1), F(2), F(4), F(0), F(1)),
    )
    colors = indexed(base, b"\x00\xff\x80", 0)
    subject = sample(b"\x00", color=colors)
    assert list(colour.channels(subject)) == [(F(-1), F(4), F(128, 255))]
    assert colour.display(subject).rgb is None


def test_stencil_and_soft_mask_are_diagnostic_planes_with_no_paint_or_composition():
    from bookscan import colour

    subject = sample(
        b"\x40", bits=1, width=2, color=samples.Color("stencil", 1, b"null"), decode=(F(1), F(0))
    )
    shown = colour.display(subject)
    assert shown.rgb == b"\xff\xff\xff\x00\x00\x00"
    assert "stencil" in shown.label and "diagnostic" in shown.label
    soft = replace(
        sample(b"\x80"),
        matte=(F(1),),
        placement=replace(
            subject.placement, kind="soft-mask", samples=(1, 1), bits_per_component=8
        ),
    )
    assert "soft-mask" in colour.display(soft).label
    assert any("Matte" in message for message in colour.display(soft).limitations)


def test_unavailable_decode_and_owner_cancel_are_not_relabelled_as_colour():
    from bookscan import colour

    subject = replace(sample(b"\x80"), packed=None, unavailable="codec unavailable")
    shown = colour.display(subject)
    assert shown.rgb is None and shown.unavailable == "codec unavailable"
    selected = ValueError("owner cancellation")

    def cancelled() -> None:
        raise selected

    with pytest.raises(ValueError) as caught:
        colour.display(sample(b"\x80"), check_cancel=cancelled)
    assert caught.value is selected


def test_snapshot_default_indexed_is_interpreted(tmp_path: Path):
    from bookscan import colour

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        obj = pdf.make_stream(b"\x1b")  # pyright: ignore[reportUnknownMemberType]
        obj.Type, obj.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
        obj.Width, obj.Height, obj.BitsPerComponent = 4, 1, 2
        obj.ColorSpace = pikepdf.Array(
            [
                pikepdf.Name.Indexed,
                pikepdf.Name.DeviceRGB,
                1,
                pikepdf.String(b"\x00\x80\xff\xff\x80\x00"),
            ]
        )
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
        page.Contents = pdf.make_stream(b"/I Do")  # pyright: ignore[reportUnknownMemberType]
        source = tmp_path / "input.pdf"
        pdf.save(source)
    saved = intake.snapshot(source, tmp_path / "snapshot.pdf")
    source.unlink()
    original = saved.path.read_bytes()
    inventory = samples.collect(saved, saved.pages[0])
    shown = colour.display(inventory.images[0])
    assert shown.rgb == b"\x00\x80\xff" + b"\xff\x80\x00" * 3
    assert shown.size == (4, 1) and saved.path.read_bytes() == original


def test_constant_decode_and_display_half_tie_quantization():
    from bookscan import colour

    subject = sample(b"\x00\xff", width=2, decode=(F(1, 2), F(1, 2)))
    assert list(colour.channels(subject)) == [(F(1, 2),), (F(1, 2),)]
    assert colour.display(subject).rgb == b"\x80" * 6


def test_display_propagates_selected_cancel_after_first_row():
    from bookscan import colour

    subject = sample(b"\x00\xff", height=2)
    selected = placement.Unavailable("owner cancelled")
    calls = 0

    def checked() -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise selected

    with pytest.raises(placement.Unavailable) as caught:
        colour.display(subject, check_cancel=checked)
    assert caught.value is selected


def test_snapshot_default_rgb_profile_is_never_silently_displayed_as_device_rgb(tmp_path: Path):
    from bookscan import colour

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        obj = pdf.make_stream(b"\x00\x80\xff")  # pyright: ignore[reportUnknownMemberType]
        obj.Type, obj.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
        obj.Width, obj.Height, obj.BitsPerComponent = 1, 1, 8
        obj.ColorSpace = pikepdf.Name.DeviceRGB
        profile = pdf.make_stream(b"unverified profile")  # pyright: ignore[reportUnknownMemberType]
        profile.N = 3
        profile.Range = pikepdf.Array([-1, 1, 0, 1, 2, 4])
        page.Resources = pikepdf.Dictionary(
            XObject=pikepdf.Dictionary(I=obj),
            ColorSpace=pikepdf.Dictionary(
                DefaultRGB=pikepdf.Array([pikepdf.Name.ICCBased, profile])
            ),
        )
        page.Contents = pdf.make_stream(b"/I Do")  # pyright: ignore[reportUnknownMemberType]
        source = tmp_path / "input.pdf"
        pdf.save(source)
    saved = intake.snapshot(source, tmp_path / "snapshot.pdf")
    subject = samples.collect(saved, saved.pages[0]).images[0]
    assert list(colour.channels(subject)) == [(F(-1), F(128, 255), F(4))]
    shown = colour.display(subject)
    assert shown.rgb is None and shown.colour_space == "/ICCBased" and shown.unavailable
