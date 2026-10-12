"""Lossless native PNG tiles and the packet pixel ruler.

A native tile is the exact baseline pixels of one ``view_manifest.Region`` as a PNG
with nothing but 8-bit RGB samples and a physical density. The density is derived
from a *measured* display backing scale supplied by the caller; it is metadata and
never evidence that a viewer shows one device pixel per project pixel. That claim
rests only on the ruler and an observed framebuffer measurement.

Pure bytes in, pure bytes out: no project, packet directory or viewer is touched.
"""

import io
import math

from PIL import Image, ImageDraw, UnidentifiedImageError

from bookscan.view_manifest import Region

_RULER = (640, 480)


class TileError(Exception):
    """A tile cannot be made, or a published tile is not the saved baseline region."""


def _dpi(scale: object) -> float:
    # bool is an int: True would silently mean a 1.0 scale nobody measured.
    if isinstance(scale, bool) or not isinstance(scale, int | float):
        raise TileError("The display backing scale must be a measured finite positive number.")
    if not math.isfinite(scale) or scale <= 0:
        raise TileError("The display backing scale must be a measured finite positive number.")
    return 72.0 * scale


def _encode(image: Image.Image, scale: object) -> bytes:
    dpi = _dpi(scale)
    out = io.BytesIO()
    # Pillow 12.3 PNG dpi becomes a pHYs chunk: metadata, not viewer scale.
    # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#png
    image.save(out, format="PNG", dpi=(dpi, dpi))
    return out.getvalue()


def _check(rgb: bytes, size: tuple[int, int], region: Region) -> None:
    width, height = size
    if width <= 0 or height <= 0 or len(rgb) != width * height * 3:
        raise TileError("The decoded baseline is not one 8-bit RGB sample triple per pixel.")
    if (
        region.width <= 0
        or region.height <= 0
        or region.x < 0
        or region.y < 0
        or region.x + region.width > width
        or region.y + region.height > height
    ):
        raise TileError(f"Region {region.id} lies outside the {width}x{height} baseline.")


def _region_bytes(rgb: bytes, size: tuple[int, int], region: Region) -> bytes:
    width, _ = size
    row = region.width * 3
    return b"".join(
        rgb[((region.y + y) * width + region.x) * 3 :][:row] for y in range(region.height)
    )


def tile_png(rgb: bytes, size: tuple[int, int], region: Region, backing_scale: float) -> bytes:
    """Encode exactly the region's baseline pixels, at the measured display density."""
    _check(rgb, size, region)
    with Image.frombytes(
        "RGB", (region.width, region.height), _region_bytes(rgb, size, region)
    ) as image:
        return _encode(image, backing_scale)


def ruler_png(backing_scale: float) -> bytes:
    """The packet's pixel ruler: the construction the scale measurement was validated on."""
    with Image.new("RGB", _RULER, "white") as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle((64, 64, 575, 415), fill="red")
        draw.rectangle((65, 65, 574, 414), fill="white")
        for x in range(96, 544):
            draw.line((x, 96, x, 159), fill="black" if x % 2 == 0 else "white")
        for y in range(192, 384):
            draw.line((96, y, 159, y), fill="black" if y % 2 == 0 else "white")
        for x in range(192, 545, 32):
            draw.line((x, 240, x, 304), fill="black")
        return _encode(image, backing_scale)


def verify_tile_png(png: bytes, rgb: bytes, size: tuple[int, int], region: Region) -> None:
    """Decode a tile and require it to be exactly the saved baseline region."""
    _check(rgb, size, region)
    try:
        with Image.open(io.BytesIO(png)) as image:
            if image.format != "PNG":
                raise TileError("The tile is not a PNG.")
            if image.mode != "RGB":
                raise TileError(f"The tile is {image.mode}, not 8-bit RGB.")
            if image.size != (region.width, region.height):
                raise TileError(f"The tile is {image.size[0]}x{image.size[1]}, not {region.id}.")
            decoded = image.tobytes()
    except (UnidentifiedImageError, OSError, SyntaxError) as error:
        raise TileError("The tile is not a decodable PNG.") from error
    if decoded != _region_bytes(rgb, size, region):
        raise TileError(f"The tile pixels differ from the saved baseline in {region.id}.")
