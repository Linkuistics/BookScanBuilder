"""Exact native sample interpretation and explicitly uncombined diagnostic views.

Device-colour bytes are a display aid, not an sRGB/profile conversion or an
independent oracle for full-page fidelity. These views never change a baseline.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from fractions import Fraction

from bookscan import placement, samples


@dataclass(frozen=True)
class Display:
    size: tuple[int, int]
    colour_space: str | None
    rgb: bytes | None
    colour_key_alpha: bytes | None
    label: str
    unavailable: str | None
    limitations: tuple[str, ...] = (
        "Device colour management and complete-page composition fidelity are unverified.",
        "Uncombined samples: no page clipping, blending, interpolation or mask composition.",
        "Soft-mask Matte unpremultiplication and stencil paint colour are not applied.",
        "RGB display quantizes decoded channels to 8 bits; original channels remain separate.",
    )


def ranges(color: samples.Color) -> tuple[Fraction, ...]:
    if color.kind == "/ICCBased":
        return color.ranges
    return (Fraction(0), Fraction(1)) * color.components


def clip(value: Fraction, low: Fraction, high: Fraction) -> Fraction:
    return min(high, max(low, value))


def nearest(value: Fraction) -> int:
    """Canonical nearest integer with half ties upward (not Python's even tie)."""
    return (value + Fraction(1, 2)).numerator // (value + Fraction(1, 2)).denominator


def interpreted(raw: tuple[int, ...], subject: samples.Sample) -> tuple[Fraction, ...]:
    color, decode, bits = subject.color, subject.decode, subject.placement.bits_per_component
    if color is None or decode is None or bits is None:
        raise placement.Unavailable(subject.unavailable or "native colour metadata unavailable")
    # ISO 32000-1 8.9.5.2/Table 90: map raw values linearly, then clamp to
    # the colour-space range. Indexed Decode is an index, not a 0..1 channel.
    # https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
    values = tuple(
        decode[2 * c] + Fraction(v, (1 << bits) - 1) * (decode[2 * c + 1] - decode[2 * c])
        for c, v in enumerate(raw)
    )
    if color.kind == "/Indexed":
        base, high, palette = color.base, color.high, color.palette
        if base is None or high is None or palette is None:
            raise placement.Unavailable("Indexed base/lookup unavailable")
        # 8.6.6.3: round/clamp index; bytes map to the base colour's full range.
        index = nearest(clip(values[0], Fraction(0), Fraction(high)))
        bounds = ranges(base)
        return tuple(
            bounds[2 * c]
            + Fraction(palette[index * base.components + c], 255)
            * (bounds[2 * c + 1] - bounds[2 * c])
            for c in range(base.components)
        )
    bounds = ranges(color)
    return tuple(clip(v, bounds[2 * c], bounds[2 * c + 1]) for c, v in enumerate(values))


def channels(
    subject: samples.Sample, *, check_cancel: Callable[[], None] = lambda: None
) -> Iterator[tuple[Fraction, ...]]:
    """Yield decoded source-space channels, with Indexed palettes expanded."""
    for raw in subject.pixels(check_cancel=check_cancel):
        yield interpreted(raw, subject)


def display(subject: samples.Sample, *, check_cancel: Callable[[], None] = lambda: None) -> Display:
    """Display Gray/RGB and diagnostic mask planes, without painting/compositing.

    colour_key_alpha is a separate 0/255 plane. None means no colour-key mask,
    never that an external mask or soft mask was applied or that the image is opaque.
    """
    check_cancel()
    color = subject.color
    base = color.base if color is not None and color.kind == "/Indexed" else color
    kind = base.kind if base is not None else None
    label = (
        f"{kind} {subject.placement.kind} uncombined native samples"
        if kind != "stencil" and subject.placement.kind not in {"mask", "soft-mask"}
        else f"{kind} {subject.placement.kind} diagnostic uncombined mask plane"
    )
    unavailable = subject.unavailable
    if unavailable is None and (subject.packed is None or color is None or base is None):
        unavailable = "native samples/colour metadata unavailable"
    if unavailable is None and kind not in {"/DeviceGray", "/DeviceRGB", "stencil"}:
        unavailable = (
            f"{kind} native RGB conversion has no independently verified profile/colour oracle"
        )
    if unavailable is not None:
        return Display(subject.placement.samples, kind, None, None, label, unavailable)
    rgb = bytearray()
    alpha = bytearray() if subject.color_key is not None else None
    for raw in subject.pixels(check_cancel=check_cancel):
        values = interpreted(raw, subject)
        quantized = tuple(nearest(v * 255) for v in values)
        rgb.extend(quantized * 3 if len(quantized) == 1 else quantized)
        if alpha is not None:
            key = subject.color_key
            assert key is not None
            # ISO 32000-1 8.9.6.4: all RAW components must lie inside their
            # inclusive ranges. Decode, palette lookup and RGB do not decide alpha.
            alpha.append(
                0 if all(key[2 * c] <= v <= key[2 * c + 1] for c, v in enumerate(raw)) else 255
            )
    check_cancel()
    return Display(
        subject.placement.samples,
        kind,
        bytes(rgb),
        bytes(alpha) if alpha is not None else None,
        label,
        None,
    )
