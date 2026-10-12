"""Independent static snapshot/physical mapping constructions; no render/fidelity claim."""

import argparse
import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pikepdf

from bookscan.intake import Frame, Page, snapshot

# Declared independently, before output: a 72 x 36 user-unit rectangle at (10,20),
# UserUnit=2 gives 144 x 72 points and 600 x 300 pixels at 300 dpi. Positive PDF
# /Rotate rotates clockwise. Pixel coordinates below are edges, not pixel centres.
CASES = [
    (0, (600, 300), (144, 72), ((0, 300), (600, 300), (600, 0), (0, 0))),
    (90, (300, 600), (72, 144), ((0, 0), (0, 600), (300, 600), (300, 0))),
    (180, (600, 300), (144, 72), ((600, 0), (0, 0), (0, 300), (600, 300))),
    (270, (300, 600), (72, 144), ((300, 600), (300, 0), (0, 0), (0, 600))),
]
CORNERS = [(10, 20), (82, 20), (82, 56), (10, 56)]
BOXES = [(82, 56, 10, 20), (70, 50, 22, 26), (11, 21, 81, 55), (12, 22, 80, 54), (13, 23, 79, 53)]


def check_frame(frame: Frame, case: int) -> None:
    _, pixels, points, corners = CASES[case]
    assert frame.pixels == pixels, "pixel extent"
    assert frame.points == points, "physical extent"
    assert [frame.map_point(Decimal(x), Decimal(y)) for x, y in CORNERS] == list(corners), (
        "edge map"
    )
    assert frame.extent_changed, "CropBox extent reason"


def check_page(page: Page, case: int) -> None:
    assert page.source_page == case + 1, "occurrence order"
    assert page.geometry.boxes == tuple(tuple(Decimal(v) for v in box) for box in BOXES), "boxes"
    assert page.geometry.rotate == CASES[case][0], "rotation"
    assert page.geometry.user_unit == 2, "UserUnit"
    assert page.hint is None, "unmarked input"
    check_frame(page.frame, case)


def run(artifacts: Path) -> dict[str, object]:
    artifacts.mkdir()  # Unused, explicit external directory; no collection discovery.
    truth = {
        "cases": CASES,
        "original_boxes": BOXES,
        "corners": CORNERS,
        "scope": "static-byte-snapshot and pixel-edge/physical mapping only",
        "fidelity": "unavailable: no rendered image or native-composition oracle yet",
    }
    truth_path = artifacts / "truth.json"
    truth_path.write_text(json.dumps(truth, indent=2) + "\n")
    source = artifacts / "Ordinary unmarked.pdf"
    with pikepdf.Pdf.new() as pdf:
        for rotate, _, _, _ in CASES:
            page = pdf.add_blank_page(page_size=(72, 36))
            for key, value in zip(("MediaBox", "CropBox", "BleedBox", "TrimBox", "ArtBox"), BOXES):
                page.obj["/" + key] = pikepdf.Array(value)
            page.obj.Rotate = rotate
            page.obj.UserUnit = 2
        # Blank/duplicate occurrences are deliberately retained, never deduplicated.
        pdf.pages.append(pdf.pages[0])  # pyright: ignore[reportUnknownMemberType]
        pdf.save(source, min_version="1.7", deterministic_id=True)
    original = source.read_bytes()
    before = hashlib.sha256(original).hexdigest()
    result = snapshot(source, artifacts / "private-source.pdf")
    assert result.sha256 == before
    assert source.read_bytes() == original == result.path.read_bytes()
    assert len(result.pages) == 5
    for case, page in enumerate(result.pages[:4]):
        check_page(page, case)
    assert result.pages[4].source_page == 5
    assert result.pages[4].geometry == result.pages[0].geometry
    records: list[dict[str, object]] = []
    for page in result.pages:
        records.append(
            {
                "source_page": page.source_page,
                "boxes": [[str(v) for v in box] for box in page.geometry.boxes],
                "rotate": page.geometry.rotate,
                "unit": str(page.geometry.user_unit),
                "pixels": page.frame.pixels,
                "points": [str(v) for v in page.frame.points],
                "matrix": [str(v) for v in page.frame.matrix],
                "hint": None,
            }
        )
    good = result.pages[0]
    controls = {
        "wrong-unit": replace(good, geometry=replace(good.geometry, user_unit=Decimal(1))),
        "wrong-box": replace(
            good,
            geometry=replace(
                good.geometry,
                boxes=(tuple(Decimal(v) for v in [0, 0, 72, 36]), *good.geometry.boxes[1:]),
            ),
        ),
        "wrong-order": result.pages[1],
        "wrong-pixel-extent": replace(good, frame=replace(good.frame, pixels=(300, 150))),
        "wrong-physical-extent": replace(
            good, frame=replace(good.frame, points=(Decimal(72), Decimal(36)))
        ),
        "wrong-edge-map": replace(
            good,
            frame=replace(
                good.frame,
                matrix=(
                    Fraction(1),
                    Fraction(0),
                    Fraction(0),
                    Fraction(1),
                    Fraction(0),
                    Fraction(0),
                ),
            ),
        ),
    }
    rejected: dict[str, str] = {}
    for name, wrong in controls.items():
        try:
            check_page(wrong, 0)
        except AssertionError as error:
            rejected[name] = str(error)
        else:
            raise AssertionError(f"Wrong-subject control escaped: {name}")
        # The unrelated occurrence/bytes checks stay green for every control.
        check_page(result.pages[2], 2)
        assert result.path.read_bytes() == original
    assert len(rejected) == 6
    source.unlink()
    result.verify()
    assert not source.exists()
    report: dict[str, object] = {
        "source_sha256": before,
        "truth_sha256": hashlib.sha256(truth_path.read_bytes()).hexdigest(),
        "pages": records,
        "controls": rejected,
        "source_loss_snapshot_verified": True,
        "original_and_snapshot_bytes_equal": True,
        "accepted_project_delivered": False,
        "render_fidelity_claimed": False,
    }
    (artifacts / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.artifacts), indent=2))


if __name__ == "__main__":
    main()
