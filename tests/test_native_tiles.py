"""Lossless native PNG tiles and the packet pixel ruler.

Expected pixels are indexed by hand from an independently constructed image, never
produced by the product's own crop. The PNG chunk list is parsed byte by byte, so the
claim "nothing but lossless RGB samples and a density" does not rest on Pillow's view.
"""

import io
import math
import struct
import zlib
from pathlib import Path

import pytest
from native_view_scale import write_ruler
from PIL import Image

from bookscan.native_tiles import (
    TileError,
    ruler_png,
    tile_png,
    verify_tile_png,
)
from bookscan.view_manifest import Region, partition

SIZE = (1700, 900)  # 768 + 768 + 164 wide, 768 + 132 high: edge tiles of both kinds


def baseline(size: tuple[int, int] = SIZE) -> bytes:
    """Every pixel carries a value no neighbour shares, so any shift is visible."""
    width, height = size
    out = bytearray()
    for y in range(height):
        for x in range(width):
            out += bytes(((x * 7 + y) % 256, (x + y * 13) % 256, (x * 3 + y * 5 + x // 256) % 256))
    return bytes(out)


def chunks(png: bytes) -> list[tuple[bytes, bytes]]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    out: list[tuple[bytes, bytes]] = []
    offset = 8
    while offset < len(png):
        length, kind = struct.unpack(">I4s", png[offset : offset + 8])
        body = png[offset + 8 : offset + 8 + length]
        crc = struct.unpack(">I", png[offset + 8 + length : offset + 12 + length])[0]
        assert crc == zlib.crc32(kind + body)
        out.append((kind, body))
        offset += 12 + length
    return out


def density(png: bytes) -> tuple[int, int, int]:
    (body,) = [body for kind, body in chunks(png) if kind == b"pHYs"]
    return struct.unpack(">IIB", body)


@pytest.fixture(scope="module")
def pixels() -> bytes:
    return baseline()


def test_tile_png_is_exactly_the_region_pixels_for_every_tile_kind(pixels: bytes) -> None:
    width, _ = SIZE
    regions = partition(SIZE)
    assert {(r.width, r.height) for r in regions} == {
        (768, 768),
        (164, 768),
        (768, 132),
        (164, 132),
    }
    for region in regions:
        with Image.open(io.BytesIO(tile_png(pixels, SIZE, region, 1.0))) as image:
            assert image.mode == "RGB"
            assert image.size == (region.width, region.height)
            decoded = image.tobytes()
        expected = b"".join(
            pixels[((region.y + row) * width + region.x) * 3 :][: region.width * 3]
            for row in range(region.height)
        )
        assert decoded == expected


def test_tiles_reassemble_into_the_whole_baseline(pixels: bytes) -> None:
    width, height = SIZE
    whole = Image.new("RGB", SIZE)
    for region in partition(SIZE):
        with Image.open(io.BytesIO(tile_png(pixels, SIZE, region, 1.0))) as tile:
            whole.paste(tile, (region.x, region.y))
    assert whole.size == (width, height)
    assert whole.tobytes() == pixels


def test_png_carries_only_header_density_pixels_and_end(pixels: bytes) -> None:
    png = tile_png(pixels, SIZE, partition(SIZE)[0], 1.0)
    kinds = [kind for kind, _ in chunks(png)]
    assert kinds[0] == b"IHDR" and kinds[-1] == b"IEND"
    assert set(kinds) == {b"IHDR", b"pHYs", b"IDAT", b"IEND"}
    width, height, depth, colour, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", chunks(png)[0][1]
    )
    assert (depth, colour, compression, filtering, interlace) == (8, 2, 0, 0, 0)
    assert (width, height) == (768, 768)


@pytest.mark.parametrize(
    ("scale", "per_metre"),
    [(1.0, 2835), (2.0, 5669), (1.5, 4252), (0.5, 1417)],
)
def test_density_is_the_measured_backing_scale_not_an_assumed_tag(
    pixels: bytes, scale: float, per_metre: int
) -> None:
    # 72 * scale dots per inch over 0.0254 m per inch, rounded to a whole number.
    png = tile_png(pixels, SIZE, partition(SIZE)[0], scale)
    assert density(png) == (per_metre, per_metre, 1)


@pytest.mark.parametrize("scale", [0, -1.0, math.nan, math.inf, True, "1.0"])
def test_unmeasured_or_nonfinite_scale_is_refused(pixels: bytes, scale: object) -> None:
    with pytest.raises(TileError, match="backing scale"):
        tile_png(pixels, SIZE, partition(SIZE)[0], scale)  # type: ignore[arg-type]
    with pytest.raises(TileError, match="backing scale"):
        ruler_png(scale)  # type: ignore[arg-type]


def test_output_is_deterministic_so_it_can_be_content_addressed(pixels: bytes) -> None:
    region = partition(SIZE)[4]
    assert tile_png(pixels, SIZE, region, 1.0) == tile_png(pixels, SIZE, region, 1.0)
    assert ruler_png(1.0) == ruler_png(1.0)


def test_region_outside_the_baseline_or_wrong_buffer_is_refused(pixels: bytes) -> None:
    with pytest.raises(TileError, match="outside"):
        tile_png(pixels, SIZE, Region(1, 0, 0, 1000, 0, 768, 768), 1.0)
    with pytest.raises(TileError, match="outside"):
        tile_png(pixels, SIZE, Region(1, 0, 0, 0, 800, 768, 768), 1.0)
    with pytest.raises(TileError, match="outside"):
        tile_png(pixels, SIZE, Region(1, 0, 0, 0, 0, 0, 10), 1.0)
    with pytest.raises(TileError, match="decoded"):
        tile_png(pixels[:-1], SIZE, partition(SIZE)[0], 1.0)


def test_verify_accepts_the_published_tile_and_rejects_changed_pixels(pixels: bytes) -> None:
    region = partition(SIZE)[5]
    png = tile_png(pixels, SIZE, region, 1.0)
    verify_tile_png(png, pixels, SIZE, region)
    other = bytearray(pixels)
    width, _ = SIZE
    other[((region.y + 3) * width + region.x + 5) * 3] ^= 1
    with pytest.raises(TileError, match="pixels"):
        verify_tile_png(png, bytes(other), SIZE, region)


def test_verify_rejects_a_tile_of_the_wrong_region_or_format(pixels: bytes) -> None:
    regions = partition(SIZE)
    png = tile_png(pixels, SIZE, regions[0], 1.0)
    with pytest.raises(TileError):
        verify_tile_png(png, pixels, SIZE, regions[1])
    edge = next(region for region in regions if region.width != 768)
    with pytest.raises(TileError, match="not native-003"):
        verify_tile_png(png, pixels, SIZE, edge)
    with pytest.raises(TileError, match="PNG"):
        verify_tile_png(b"not a png", pixels, SIZE, regions[0])
    buffer = io.BytesIO()
    with Image.open(io.BytesIO(png)) as image:
        image.convert("RGBA").save(buffer, format="PNG")
    with pytest.raises(TileError, match="RGB"):
        verify_tile_png(buffer.getvalue(), pixels, SIZE, regions[0])


def test_ruler_is_the_construction_the_measurement_instrument_was_validated_against(
    tmp_path: Path,
) -> None:
    for scale in (1.0, 2.0):
        target = tmp_path / f"ruler-{scale}.png"
        write_ruler(target, scale)
        assert ruler_png(scale) == target.read_bytes()


def test_ruler_declares_its_density_and_stays_lossless() -> None:
    png = ruler_png(2.0)
    assert density(png) == (5669, 5669, 1)
    assert {kind for kind, _ in chunks(png)} == {b"IHDR", b"pHYs", b"IDAT", b"IEND"}
    with Image.open(io.BytesIO(png)) as image:
        assert image.mode == "RGB" and image.size == (640, 480)
