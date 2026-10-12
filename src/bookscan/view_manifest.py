"""Presentation-neutral matched-view manifest for one baseline occurrence.

Packets, previews and a browser surface all consume this one description of
*what* is shown: the whole-page comparison frame and a gap-free partition of the
baseline pixel rectangle into native regions, each with its three panels and the
exact PDF user-space rectangle its pixels cover. Nothing here chooses fonts,
page sizes or file layout, so no presentation can disagree about a region's
identity or coverage.

Coordinates: project pixels are top-left-origin edges of the immutable 300-dpi
baseline; user space is the source PDF's own, before Rotate. Mappings are exact
``Fraction`` values, never a guessed raster bounding box.
"""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Literal

from bookscan.intake import Frame, effective_crop
from bookscan.pdf import Geometry

# Specified maximum native tile edge; edge tiles are smaller, never padded.
MAX_TILE = 768

type PanelKind = Literal["source", "baseline", "current"]
PANELS: tuple[PanelKind, PanelKind, PanelKind] = ("source", "baseline", "current")
# The unedited finite workflow has no separate current image: both are the baseline.
IDENTICAL: tuple[PanelKind, PanelKind] = ("baseline", "current")

# One PDF point is 1/72 inch and a baseline pixel is 1/300 inch.
FULL_POINTS_PER_PIXEL = Fraction(72, 300)
# At 100% packet view scale each project pixel occupies one PDF display point.
NATIVE_POINTS_PER_PIXEL = Fraction(1)


@dataclass(frozen=True)
class Region:
    """One native tile: a pixel rectangle ``[x, x+width) x [y, y+height)``."""

    index: int  # one-based, row-major
    row: int
    column: int
    x: int
    y: int
    width: int
    height: int

    @property
    def id(self) -> str:
        return f"native-{self.index:03d}"


def _spans(length: int) -> tuple[tuple[int, int], ...]:
    return tuple((start, min(MAX_TILE, length - start)) for start in range(0, length, MAX_TILE))


def partition(size: tuple[int, int]) -> tuple[Region, ...]:
    """Row-major, gap-free, non-overlapping cover of the whole pixel rectangle."""
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError(f"baseline size must be positive, got {width}x{height}")
    columns = _spans(width)
    regions: list[Region] = []
    for row, (y, tile_height) in enumerate(_spans(height)):
        for column, (x, tile_width) in enumerate(columns):
            regions.append(Region(len(regions) + 1, row, column, x, y, tile_width, tile_height))
    return tuple(regions)


type Rect = tuple[Fraction, Fraction, Fraction, Fraction]
"""``(x0, y0, x1, y1)`` with ``x0 <= x1`` and ``y0 <= y1``."""


@dataclass(frozen=True)
class FullView:
    """Whole-page comparison: source MediaBox, baseline and current in one frame."""

    points: tuple[Decimal, Decimal]  # original physical MediaBox extent, 1/72 inch
    points_per_pixel: Fraction
    crop_guide: Rect  # effective original CropBox, in baseline pixels
    crop_differs: bool
    panels: tuple[PanelKind, ...] = PANELS


@dataclass(frozen=True)
class Tile:
    region: Region
    user_rect: Rect  # the PDF user-space rectangle these pixels physically cover
    panels: tuple[PanelKind, ...] = PANELS


@dataclass(frozen=True)
class ViewManifest:
    occurrence_id: str
    pixels: tuple[int, int]
    full: FullView
    native_points_per_pixel: Fraction
    tiles: tuple[Tile, ...]
    identical: tuple[PanelKind, PanelKind] = IDENTICAL


def _normalised(first: tuple[Fraction, Fraction], second: tuple[Fraction, Fraction]) -> Rect:
    (ax, ay), (bx, by) = first, second
    return min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)


def _user_point(frame: Frame, px: Fraction, py: Fraction) -> tuple[Fraction, Fraction]:
    a, b, c, d, e, f = frame.matrix
    determinant = a * d - b * c
    if determinant == 0:
        raise ValueError("degenerate page mapping")
    qx, qy = px - e, py - f
    return (d * qx - c * qy) / determinant, (-b * qx + a * qy) / determinant


def view_manifest(occurrence_id: str, frame: Frame, geometry: Geometry) -> ViewManifest:
    """Describe every matched view of one occurrence from its frame and boxes."""
    crop = effective_crop(geometry)
    guide = _normalised(
        frame.map_point(crop[0], crop[1]),
        frame.map_point(crop[2], crop[3]),
    )
    tiles = tuple(
        Tile(
            region,
            _normalised(
                _user_point(frame, Fraction(region.x), Fraction(region.y)),
                _user_point(
                    frame, Fraction(region.x + region.width), Fraction(region.y + region.height)
                ),
            ),
        )
        for region in partition(frame.pixels)
    )
    return ViewManifest(
        occurrence_id,
        frame.pixels,
        FullView(frame.points, FULL_POINTS_PER_PIXEL, guide, frame.extent_changed),
        NATIVE_POINTS_PER_PIXEL,
        tiles,
    )
