"""Source-native packed channels and metadata; no implicit RGB/composition oracle.

Samples retain PDF row order (top to bottom), component order, MSB-first packing
and row padding. Decode, colour conversion, masks, interpolation, placement,
clipping and blending are separate interpretations, never baked into these bytes.
"""

import hashlib
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from fractions import Fraction
from typing import cast

import pikepdf

from bookscan import placement
from bookscan.intake import Page, Snapshot
from bookscan.pdf import get


@dataclass(frozen=True)
class Color:
    kind: str
    components: int
    metadata: bytes
    profile: bytes | None = None
    palette: bytes | None = None
    high: int | None = None
    base: "Color | None" = None
    ranges: tuple[Fraction, ...] = ()


@dataclass(frozen=True)
class Sample:
    placement: placement.Placement
    color: Color | None
    packed: bytes | None
    raw_sha256: str | None
    decode: tuple[Fraction, ...] | None
    interpolate: bool | None
    filters: tuple[str, ...]
    decode_parameters: bytes | None
    matte: tuple[Fraction, ...] | None
    color_key: tuple[int, ...] | None
    unavailable: str | None
    composition_verified: bool = False

    def pixels(
        self, *, check_cancel: Callable[[], None] = lambda: None
    ) -> Iterator[tuple[int, ...]]:
        """Yield raw integer channel values without Decode or colour conversion."""
        if self.packed is None or self.color is None or self.placement.bits_per_component is None:
            raise placement.Unavailable(self.unavailable or "native samples unavailable")
        width, height = self.placement.samples
        bits, components = self.placement.bits_per_component, self.color.components
        stride = (width * components * bits + 7) // 8
        mask = (1 << bits) - 1
        # ISO 32000-1 8.9.3: MSB first, each row begins on a byte boundary.
        # https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
        for y in range(height):
            check_cancel()
            row = int.from_bytes(self.packed[y * stride : (y + 1) * stride], "big")
            for x in range(width):
                yield tuple(
                    (row >> (stride * 8 - ((x * components + c + 1) * bits))) & mask
                    for c in range(components)
                )
        check_cancel()


@dataclass(frozen=True)
class Inventory:
    resolution: placement.Analysis
    images: tuple[Sample, ...]
    concerns: tuple[str, ...]
    composition_unavailable: str = (
        "Independent complete-page colour/vector/text/mask/clipping/blending oracle unavailable."
    )

    @property
    def samples_available(self) -> bool:
        return self.resolution.complete and not self.concerns


def metadata(value: object) -> bytes | None:
    if value is None:
        return None
    if not isinstance(value, pikepdf.Object):
        raise placement.Unavailable("malformed PDF metadata")
    return value.to_json(dereference=True)


def color_space(
    value: object, resources: object, depth: int = 0, use_default: bool = True
) -> Color:
    if depth > 16:
        raise placement.Unavailable("colour resource nesting/cycle")
    if isinstance(value, pikepdf.Name):
        name = str(value)
        components = {"/DeviceGray": 1, "/DeviceRGB": 3, "/DeviceCMYK": 4}.get(name)
        if components is not None:
            spaces = (
                get(resources, "/ColorSpace") if isinstance(resources, pikepdf.Dictionary) else None
            )
            replacement = (
                get(spaces, "/Default" + name[7:])
                if isinstance(spaces, pikepdf.Dictionary)
                else None
            )
            if use_default and replacement is not None:
                resolved = color_space(replacement, resources, depth + 1, False)
                if resolved.components != components:
                    raise placement.Unavailable("default colour component mismatch")
                return resolved
            return Color(name, components, value.to_json())
        return color_space(
            placement.resource(resources, "/ColorSpace", value), resources, depth + 1, use_default
        )
    # Preserve source channels/profile/lookup; never claim an ICC conversion.
    # ISO 32000-1 8.6.5.5 / 8.6.6.3 (primary PDF linked at pixels()).
    if isinstance(value, pikepdf.Array):
        entries = list(cast(Iterable[object], value))
        if len(entries) == 2 and entries[0] == pikepdf.Name.ICCBased:
            profile = entries[1]
            if not isinstance(profile, pikepdf.Stream):
                raise placement.Unavailable("missing ICC profile stream")
            count = get(profile, "/N")
            if type(count) is not int or count not in {1, 3, 4}:
                raise placement.Unavailable("invalid ICC component count")
            ranges = placement.numbers(
                cast(Iterable[object], get(profile, "/Range", pikepdf.Array([0, 1] * count))),
                count * 2,
            )
            if any(ranges[i] >= ranges[i + 1] for i in range(0, len(ranges), 2)):
                raise placement.Unavailable("invalid ICC range")
            return Color(
                "/ICCBased",
                count,
                value.to_json(dereference=True),
                profile.read_bytes(pikepdf.StreamDecodeLevel.generalized),
                ranges=ranges,
            )
        if len(entries) == 4 and entries[0] == pikepdf.Name.Indexed:
            base = color_space(entries[1], resources, depth + 1, use_default)
            high, lookup = entries[2:]
            if type(high) is not int or not 0 <= high <= 255 or base.kind == "/Indexed":
                raise placement.Unavailable("invalid Indexed base/high value")
            if isinstance(lookup, pikepdf.Stream):
                palette = lookup.read_bytes(pikepdf.StreamDecodeLevel.generalized)
            elif isinstance(lookup, pikepdf.String):
                palette = bytes(lookup)
            else:
                raise placement.Unavailable("invalid Indexed lookup")
            if len(palette) != (high + 1) * base.components:
                raise placement.Unavailable("Indexed lookup length mismatch")
            return Color(
                "/Indexed",
                1,
                value.to_json(dereference=True),
                palette=palette,
                high=high,
                base=base,
            )
    raise placement.Unavailable("colour interpretation unavailable")


LOSSLESS = frozenset(
    {"/FlateDecode", "/LZWDecode", "/ASCIIHexDecode", "/ASCII85Decode", "/RunLengthDecode"}
)


def filter_names(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    entries = list(cast(Iterable[object], value)) if isinstance(value, pikepdf.Array) else [value]
    if any(not isinstance(v, pikepdf.Name) for v in entries):
        raise placement.Unavailable("malformed image filters")
    return tuple(str(v) for v in entries)


def codec_samples(
    obj: pikepdf.Object,
    raw: bytes,
    filters: tuple[str, ...],
    color: Color,
    placed: placement.Placement,
    check_cancel: Callable[[], None],
) -> bytes:
    """Decode a detached image's channels, without Decode/masks/ICC conversion."""
    if (
        not filters
        or filters[-1] not in {"/DCTDecode", "/CCITTFaxDecode"}
        or any(f not in LOSSLESS for f in filters[:-1])
    ):
        raise placement.Unavailable(
            "specialized codec has no verified raw-channel decoder: " + ", ".join(filters)
        )
    parameters = get(obj, "/DecodeParms")
    entries = (
        list(cast(Iterable[object], parameters))
        if isinstance(parameters, pikepdf.Array)
        else [parameters]
    )
    if parameters is not None and len(entries) != len(filters):
        raise placement.Unavailable("codec DecodeParms/filter count mismatch")
    terminal = entries[-1]
    if terminal is not None and not isinstance(terminal, pikepdf.Dictionary):
        raise placement.Unavailable("malformed terminal codec parameters")
    bits = placed.bits_per_component
    if filters[-1] == "/DCTDecode":
        if bits != 8 or color.components not in {1, 3} or color.kind == "/Indexed":
            raise placement.Unavailable(
                "DCT raw channels require 8-bit grayscale/RGB; CMYK polarity unverified"
            )
        transform = get(terminal, "/ColorTransform") if terminal is not None else None
        if transform is not None and (type(transform) is not int or transform != 1):
            raise placement.Unavailable(
                "DCT ColorTransform override has no verified raw-channel interpretation"
            )
        mode = "L" if color.components == 1 else "RGB"
    else:
        if bits != 1 or color.components != 1 or color.kind == "/Indexed":
            raise placement.Unavailable(
                "CCITT raw channels require a one-bit grayscale/stencil grid"
            )
        for key in ("/BlackIs1", "/EncodedByteAlign", "/EndOfLine", "/EndOfBlock"):
            value = get(terminal, key) if terminal is not None else None
            if value is not None and type(value) is not bool:
                raise placement.Unavailable("malformed CCITT " + key)
        for key in ("/K", "/Columns", "/Rows", "/DamagedRowsBeforeError"):
            value = get(terminal, key) if terminal is not None else None
            if value is not None and type(value) is not int:
                raise placement.Unavailable("malformed CCITT " + key)
        for key, default in (
            ("/EncodedByteAlign", False),
            ("/EndOfBlock", True),
            ("/DamagedRowsBeforeError", 0),
        ):
            if terminal is not None and get(terminal, key, default) != default:
                raise placement.Unavailable(
                    "CCITT parameter has no verified decoder interpretation: " + key
                )
        columns = get(terminal, "/Columns", 1728) if terminal is not None else 1728
        rows = get(terminal, "/Rows", 0) if terminal is not None else 0
        if columns != placed.samples[0] or rows not in (0, placed.samples[1]):
            raise placement.Unavailable("CCITT decoder grid differs from declared image grid")
        mode = "1"
    check_cancel()
    # Pinned raw-image API leaves Decode/masks separate; CCITT BlackIs1 is part
    # of codec decoding, not /Decode. Normalization avoids inline convenience
    # page limits and resource-name/ICC conversion inside the image adapter.
    # https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/models/image/_classes.py
    # https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/models/image/_extract.py
    with pikepdf.Pdf.new() as temporary:
        stream = temporary.make_stream(raw)  # pyright: ignore[reportUnknownMemberType]
        stream.Type, stream.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
        stream.Width, stream.Height = placed.samples
        stream.BitsPerComponent = bits
        stream.ColorSpace = (
            pikepdf.Name.DeviceRGB if color.components == 3 else pikepdf.Name.DeviceGray
        )
        stream.Filter = clone_value(get(obj, "/Filter"))
        if parameters is not None:
            stream.DecodeParms = clone_value(parameters)
        with pikepdf.PdfImage(stream).as_pil_image(
            apply_decode_array=False, apply_mask=False
        ) as decoded:
            check_cancel()
            if decoded.size != placed.samples or decoded.mode != mode:
                raise placement.Unavailable(
                    "decoded codec dimensions/channels differ from declared grid"
                )
            packed = decoded.tobytes()
            check_cancel()
            return packed


def decode(
    image: pikepdf.Object | pikepdf.PdfInlineImage,
    resources: object,
    placed: placement.Placement,
    check_cancel: Callable[[], None],
) -> Sample:
    obj = image.obj if isinstance(image, pikepdf.PdfInlineImage) else image
    color: Color | None = None
    raw_digest: str | None = None
    values: tuple[Fraction, ...] | None = None
    interpolate: bool | None = None
    filters: tuple[str, ...] = ()
    params: bytes | None = None
    matte: tuple[Fraction, ...] | None = None
    key: tuple[int, ...] | None = None
    owner_errors: list[BaseException] = []

    def checked() -> None:
        try:
            check_cancel()
        except BaseException as error:
            owner_errors.append(error)
            raise

    try:
        checked()
        raw = image.read_raw_bytes()
        raw_digest = hashlib.sha256(raw).hexdigest()
        filters = filter_names(get(obj, "/Filter"))
        params = metadata(get(obj, "/DecodeParms"))
        stencil = get(obj, "/ImageMask", False)
        color = (
            Color("stencil", 1, b"null")
            if stencil
            else color_space(get(obj, "/ColorSpace"), resources)
        )
        bits = placed.bits_per_component
        if bits is None or (stencil and bits != 1):
            raise placement.Unavailable("missing/invalid sample bit depth")
        default = list(color.ranges) if color.ranges else [0, 1] * color.components
        if color.kind == "/Indexed":
            default = [0, (1 << bits) - 1]
        # Fraction defaults are converted to exact PDF decimal/integer values by
        # retaining the already parsed ICC Range rather than creating a PDF array.
        provided = get(obj, "/Decode")
        values = (
            placement.numbers(cast(Iterable[object], provided), color.components * 2)
            if provided is not None
            else tuple(Fraction(v) for v in default)
        )
        interpolation = get(obj, "/Interpolate", False)
        if type(interpolation) is not bool:
            raise placement.Unavailable("malformed Interpolate")
        interpolate = interpolation
        matte_value = get(obj, "/Matte")
        if isinstance(matte_value, pikepdf.Array):
            matte = placement.numbers(cast(Iterable[object], matte_value), len(matte_value))
        elif matte_value is not None:
            raise placement.Unavailable("malformed Matte")
        mask = get(obj, "/Mask")
        if isinstance(mask, pikepdf.Array):
            numbers = list(cast(Iterable[object], mask))
            if len(numbers) != color.components * 2 or any(type(v) is not int for v in numbers):
                raise placement.Unavailable("malformed colour-key mask")
            key = tuple(cast(int, v) for v in numbers)
            if any(not 0 <= key[i] <= key[i + 1] < 1 << bits for i in range(0, len(key), 2)):
                raise placement.Unavailable("invalid colour-key mask range")
        checked()
        # Exact pinned stream API; generalized decoding does not rasterize a page.
        # https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/_core/_object.pyi
        # Inline raw spans include the EI delimiter whitespace; use a disposable
        # stream to avoid the convenience decoder's minimum-page-size constraint:
        # https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/models/image/_classes.py
        if any(f not in LOSSLESS for f in filters):
            packed = codec_samples(obj, raw, filters, color, placed, checked)
        elif isinstance(image, pikepdf.PdfInlineImage):
            if filters:
                with pikepdf.Pdf.new() as temporary:
                    stream = temporary.make_stream(raw)  # pyright: ignore[reportUnknownMemberType]
                    stream.Filter = clone_value(get(obj, "/Filter"))
                    parameters = get(obj, "/DecodeParms")
                    if parameters is not None:
                        stream.DecodeParms = clone_value(parameters)
                    packed = stream.read_bytes(pikepdf.StreamDecodeLevel.generalized)
            else:
                packed = raw
        else:
            packed = image.read_bytes(pikepdf.StreamDecodeLevel.generalized)
        checked()
        width, height = placed.samples
        expected = ((width * color.components * bits + 7) // 8) * height
        if isinstance(image, pikepdf.PdfInlineImage) and not filters:
            # qpdf includes whitespace before EI in the raw span. Only bytes
            # beyond the declared grid may be treated as its delimiter.
            if len(packed) > expected and all(v in b"\x00\t\n\x0c\r " for v in packed[expected:]):
                packed = packed[:expected]
        if len(packed) != expected:
            raise placement.Unavailable(
                f"decoded sample length {len(packed)} != declared grid {expected}"
            )
        return Sample(
            placed,
            color,
            packed,
            raw_digest,
            values,
            interpolate,
            filters,
            params,
            matte,
            key,
            None,
        )
    except (
        placement.Unavailable,
        pikepdf.PikepdfError,
        TypeError,
        ValueError,
        RuntimeError,
        OSError,
    ) as error:
        if owner_errors and error is owner_errors[-1]:
            raise
        return Sample(
            placed,
            color,
            None,
            raw_digest,
            values,
            interpolate,
            filters,
            params,
            matte,
            key,
            str(error),
        )


def clone_value(value: object, depth: int = 0) -> object:
    """Copy lossless filter parameters without borrowing foreign PDF references."""
    if depth > 16:
        raise placement.Unavailable("decoder-parameter nesting/cycle")
    if isinstance(value, pikepdf.Stream):
        raise placement.Unavailable("stream-valued generalized decoder parameter")
    if isinstance(value, pikepdf.Dictionary):
        result = pikepdf.Dictionary()
        for key in sorted(value.keys()):
            child = clone_value(get(value, key), depth + 1)
            if child is not None:
                result[key] = child
        return result
    if isinstance(value, pikepdf.Array):
        return pikepdf.Array([clone_value(v, depth + 1) for v in cast(Iterable[object], value)])
    if isinstance(value, (pikepdf.Name, pikepdf.String)):
        return pikepdf.Object.parse(value.unparse())
    return value


def collect(
    saved: Snapshot, page: Page, *, check_cancel: Callable[[], None] = lambda: None
) -> Inventory:
    images: list[Sample] = []

    def observe(
        image: pikepdf.Object | pikepdf.PdfInlineImage,
        resources: object,
        placed: placement.Placement,
        checked: Callable[[], None],
    ) -> None:
        images.append(decode(image, resources, placed, checked))

    resolution = placement.analyze(saved, page, check_cancel=check_cancel, image_observer=observe)
    concerns = tuple(
        "/".join(s.placement.path) + ": " + s.unavailable for s in images if s.unavailable
    )
    return Inventory(resolution, tuple(images), concerns)
