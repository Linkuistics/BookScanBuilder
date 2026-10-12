"""Explicit-profile, uncombined native RGB views; never modify accepted pixels.

The caller supplies the exact target profile bytes and must retain them with the
view. Successful conversion is not a monitor calibration or composition oracle.
"""

import hashlib
import io
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

from PIL import Image, ImageCms, features

from bookscan import colour, samples


@dataclass(frozen=True)
class Conversion:
    view: colour.Display
    input_profile_sha256: str | None
    output_profile_sha256: str
    pillow: str
    littlecms: str | None
    intent: int = 1
    flags: int = 256


def rgb_profile(data: bytes) -> bool:
    # ICC.1:2010 section 7.2: size, version, class, data colour space, PCS,
    # signature. LittleCMS subsequently checks the actual transform tables.
    # https://www.color.org/specification/ICC1v43_2010-12.pdf
    return (
        len(data) >= 132
        and int.from_bytes(data[:4], "big") == len(data)
        and data[8] in {2, 4}
        and data[12:16] in {b"scnr", b"mntr", b"prtr", b"spac"}
        and data[16:20] == b"RGB "
        and data[20:24] in {b"XYZ ", b"Lab "}
        and data[36:40] == b"acsp"
    )


def display(
    subject: samples.Sample,
    target_profile: bytes,
    *,
    check_cancel: Callable[[], None] = lambda: None,
) -> Conversion:
    """Convert unit-range ICC RGB channels at their unchanged native sample grid.

    Indexed palettes and PDF Decode precede 8-bit quantization/conversion. Raw
    colour-key alpha remains separate; no external/soft mask or Matte is applied.
    Cancellation is checked outside native-error handlers, including between rows.
    """
    check_cancel()
    color = subject.color
    base = color.base if color is not None and color.kind == "/Indexed" else color
    source_profile = base.profile if base is not None else None
    source_digest = (
        hashlib.sha256(source_profile).hexdigest() if source_profile is not None else None
    )
    target_digest = hashlib.sha256(target_profile).hexdigest()
    lcms = features.version_module("littlecms2")
    limitations = (
        "Explicit target-profile RGB; no calibrated monitor or complete-page fidelity claim.",
        "Uncombined samples: no page clipping, blending, interpolation or mask composition.",
        "Soft-mask Matte unpremultiplication and stencil paint colour are not applied.",
        "PDF decoded channels are quantized to 8 bits before ICC conversion; originals retained.",
    )

    def result(rgb: bytes | None, alpha: bytes | None, unavailable: str | None) -> Conversion:
        return Conversion(
            colour.Display(
                subject.placement.samples,
                base.kind if base is not None else None,
                rgb,
                alpha,
                "Explicit-profile uncombined native samples",
                unavailable,
                limitations,
            ),
            source_digest,
            target_digest,
            Image.__version__,
            lcms,
        )

    if subject.unavailable is not None:
        return result(None, None, subject.unavailable)
    if subject.packed is None or subject.decode is None:
        return result(None, None, "Native samples/Decode unavailable")
    width, height = subject.placement.samples
    bits = subject.placement.bits_per_component
    if (
        color is None
        or width <= 0
        or height <= 0
        or bits not in {1, 2, 4, 8, 16}
        or len(subject.decode) != 2 * color.components
        or len(subject.packed) != ((width * color.components * bits + 7) // 8) * height
        or (subject.color_key is not None and len(subject.color_key) != 2 * color.components)
    ):
        return result(None, None, "Native grid/channel/Decode/mask length mismatch")
    if (
        base is None
        or base.kind != "/ICCBased"
        or base.components != 3
        or base.ranges != (Fraction(0), Fraction(1)) * 3
    ):
        return result(None, None, "Only unit-range ICC RGB has a supported native conversion")
    if source_profile is None or not rgb_profile(source_profile):
        return result(None, None, "Missing, malformed or incompatible input RGB ICC profile")
    if not rgb_profile(target_profile):
        return result(None, None, "Malformed or incompatible explicit target RGB ICC profile")
    if Image.__version__ != "12.3.0" or lcms != "2.19":
        return result(
            None, None, "Supported profile conversion requires Pillow 12.3.0/LittleCMS 2.19"
        )
    check_cancel()
    try:
        # Pillow 12.3.0 accepts byte-stream profiles, explicit intent/flags and
        # a reusable RGB transform; apply returns a new image, never in-place.
        # https://raw.githubusercontent.com/python-pillow/Pillow/12.3.0/src/PIL/ImageCms.py
        transform = ImageCms.buildTransformFromOpenProfiles(
            ImageCms.ImageCmsProfile(io.BytesIO(source_profile)),
            ImageCms.ImageCmsProfile(io.BytesIO(target_profile)),
            "RGB",
            "RGB",
            renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
            flags=ImageCms.Flags.NOOPTIMIZE,
        )
    except (ImageCms.PyCMSError, OSError, ValueError) as error:
        return result(None, None, f"ICC transform unavailable: {error}")
    check_cancel()
    pixels = subject.pixels(check_cancel=check_cancel)
    output = bytearray()
    alpha = bytearray() if subject.color_key is not None else None
    for _ in range(height):
        row = bytearray()
        for _ in range(width):
            raw = next(pixels)
            row.extend(colour.nearest(v * 255) for v in colour.interpreted(raw, subject))
            if alpha is not None:
                key = subject.color_key
                assert key is not None
                alpha.append(
                    0 if all(key[2 * c] <= v <= key[2 * c + 1] for c, v in enumerate(raw)) else 255
                )
        check_cancel()
        try:
            with Image.frombytes("RGB", (width, 1), bytes(row)) as image:
                with transform.apply(image) as converted:
                    output.extend(converted.tobytes())
        except (ImageCms.PyCMSError, OSError, ValueError) as error:
            return result(None, None, f"ICC row conversion unavailable: {error}")
        check_cancel()
    return result(bytes(output), bytes(alpha) if alpha is not None else None, None)
