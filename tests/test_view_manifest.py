"""Presentation-neutral matched-view manifest: native partition and physical mapping.

Expected values are derived by hand from the PDF Rotate/UserUnit definitions and
from independent pixel-coverage counting, not from the product's own matrix.
"""

from decimal import Decimal
from fractions import Fraction

import pytest

from bookscan.intake import frame_for
from bookscan.pdf import Geometry
from bookscan.view_manifest import MAX_TILE, partition, view_manifest

SCALE = Fraction(300, 72)  # project pixels per PDF point at UserUnit 1


def geometry(
    media: tuple[str, str, str, str] = ("0", "0", "612", "792"),
    crop: tuple[str, str, str, str] | None = None,
    rotate: int = 0,
    unit: str = "1",
) -> Geometry:
    media_box = tuple(Decimal(value) for value in media)
    crop_box = tuple(Decimal(value) for value in crop) if crop else media_box
    return Geometry((media_box, crop_box, media_box, media_box, media_box), rotate, Decimal(unit))


def covered(size: tuple[int, int]) -> list[int]:
    """Independent coverage count: how many regions claim each pixel (row-major)."""
    width, height = size
    counts = [0] * (width * height)
    for region in partition(size):
        assert 0 <= region.x and 0 <= region.y
        assert region.x + region.width <= width and region.y + region.height <= height
        assert 0 < region.width <= MAX_TILE and 0 < region.height <= MAX_TILE
        for row in range(region.y, region.y + region.height):
            base = row * width + region.x
            for column in range(region.width):
                counts[base + column] += 1
    return counts


def test_norwegian_baseline_partitions_into_the_signed_twenty_regions() -> None:
    regions = partition((3591, 2695))
    assert len(regions) == 20
    assert {(region.width, region.height) for region in regions} == {
        (768, 768),
        (519, 768),
        (768, 391),
        (519, 391),
    }
    first, last = regions[0], regions[-1]
    assert (first.index, first.id, first.row, first.column) == (1, "native-001", 0, 0)
    assert (last.id, last.row, last.column) == ("native-020", 3, 4)
    assert (last.x, last.y, last.width, last.height) == (3072, 2304, 519, 391)


@pytest.mark.parametrize(
    "size",
    [(1, 1), (768, 768), (769, 768), (768, 769), (1536, 768), (1537, 1), (100, 50), (1700, 1541)],
)
def test_every_pixel_is_covered_exactly_once_with_no_oversize_tile(size: tuple[int, int]) -> None:
    assert set(covered(size)) == {1}


def test_regions_are_row_major_with_unique_stable_identities() -> None:
    regions = partition((2000, 1600))
    assert [region.index for region in regions] == list(range(1, len(regions) + 1))
    assert len({region.id for region in regions}) == len(regions)
    order = [(region.row, region.column) for region in regions]
    assert order == sorted(order)
    assert partition((2000, 1600)) == regions


@pytest.mark.parametrize("size", [(0, 10), (10, 0), (-1, 5)])
def test_a_degenerate_baseline_is_refused(size: tuple[int, int]) -> None:
    with pytest.raises(ValueError):
        partition(size)


def test_unrotated_region_maps_to_the_top_left_of_the_user_space_page() -> None:
    page = geometry()
    manifest = view_manifest("occ-000001", frame_for(page), page)
    tile = manifest.tiles[0]
    edge = Fraction(768) / SCALE  # 184.32 points
    assert tile.user_rect == (Fraction(0), Fraction(792) - edge, edge, Fraction(792))


def test_rotation_moves_the_first_region_to_the_documented_corner() -> None:
    edge = Fraction(768) / SCALE
    expected = {
        90: (Fraction(0), Fraction(0), edge, edge),
        180: (Fraction(612) - edge, Fraction(0), Fraction(612), edge),
        270: (Fraction(612) - edge, Fraction(792) - edge, Fraction(612), Fraction(792)),
    }
    for rotate, rect in expected.items():
        page = geometry(rotate=rotate)
        manifest = view_manifest("occ-000001", frame_for(page), page)
        assert manifest.tiles[0].user_rect == rect, rotate


def test_reversed_media_box_and_user_unit_apply_to_the_mapping() -> None:
    page = geometry(media=("612", "792", "0", "0"), unit="2")
    frame = frame_for(page)
    # 612x792 user units at UserUnit 2 are 1224x1584 points -> ceil(5100 x 6600) pixels.
    assert frame.pixels == (5100, 6600)
    tile = view_manifest("occ-000001", frame, page).tiles[0]
    edge = Fraction(768) / (SCALE * 2)  # points of user space per 768 pixels
    assert tile.user_rect == (Fraction(0), Fraction(792) - edge, edge, Fraction(792))


def test_final_partial_pixel_region_extends_past_the_media_box_exactly() -> None:
    # 100.1 pt -> 417.0833 px -> 418 pixels, so the last column covers 0.9166 px beyond the page.
    page = geometry(media=("0", "0", "100.1", "100"))
    frame = frame_for(page)
    assert frame.pixels == (418, 417)
    tile = view_manifest("occ-000001", frame, page).tiles[0]
    assert tile.user_rect[2] == Fraction(418) / SCALE
    assert tile.user_rect[2] > Fraction("100.1")


def test_crop_guide_is_the_cropbox_intersection_in_baseline_pixels() -> None:
    page = geometry(crop=("36", "36", "576", "756"))
    manifest = view_manifest("occ-000001", frame_for(page), page)
    assert manifest.full.crop_guide == (
        Fraction(36) * SCALE,
        Fraction(792 - 756) * SCALE,
        Fraction(576) * SCALE,
        Fraction(792 - 36) * SCALE,
    )
    assert manifest.full.crop_differs


def test_cropbox_larger_than_media_box_guides_the_whole_page() -> None:
    page = geometry(crop=("-50", "-50", "700", "900"))
    frame = frame_for(page)
    manifest = view_manifest("occ-000001", frame, page)
    assert manifest.full.crop_guide == (
        Fraction(0),
        Fraction(0),
        Fraction(612) * SCALE,
        Fraction(792) * SCALE,
    )
    assert not manifest.full.crop_differs


def test_full_view_shares_one_physical_frame_and_declares_its_display_scale() -> None:
    page = geometry()
    frame = frame_for(page)
    manifest = view_manifest("occ-000042", frame, page)
    assert manifest.occurrence_id == "occ-000042"
    assert manifest.pixels == frame.pixels
    assert manifest.full.points == frame.points
    assert manifest.full.points_per_pixel == Fraction(72, 300)
    assert manifest.full.panels == ("source", "baseline", "current")
    assert manifest.identical == ("baseline", "current")


def test_native_tiles_carry_three_panels_at_one_point_per_pixel() -> None:
    page = geometry()
    manifest = view_manifest("occ-000001", frame_for(page), page)
    assert manifest.native_points_per_pixel == Fraction(1)
    assert {tile.panels for tile in manifest.tiles} == {("source", "baseline", "current")}
    # 612x792 pt at 300 dpi is 2550x3300 pixels: ceil(2550/768)=4 columns, ceil(3300/768)=5 rows.
    assert [tile.region for tile in manifest.tiles] == list(partition((2550, 3300)))
    assert len(manifest.tiles) == 20
