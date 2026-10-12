"""Predeclared analytic placements and actual Cairo annotation-visibility controls.

This is an internal analyzer check, not independent composition fidelity, a
saved-project/public workflow or source-native sample decoding acceptance.
"""

import argparse
import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pikepdf

from bookscan import placement, render
from bookscan.intake import Page, Snapshot, snapshot

# Literal edge transforms derived from physical construction, not an analyzer.
# Four half-UserUnit pages: 72x36 units at (10,20) occupy 150x75 pixels.
ROTATIONS = [
    (0, (150, 0, 0, -75, 0, 75)),
    (90, (0, 150, 75, 0, 0, 0)),
    (180, (-150, 0, 0, 75, 150, 0)),
    (270, (0, -150, -75, 0, 75, 150)),
]


def stream(pdf: pikepdf.Pdf, data: bytes) -> pikepdf.Object:
    return pdf.make_stream(data)  # pyright: ignore[reportUnknownMemberType]


def image(pdf: pikepdf.Pdf, width: int, height: int) -> pikepdf.Object:
    obj = stream(pdf, b"\x80" * (width * height))
    obj.Type, obj.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
    obj.Width, obj.Height, obj.BitsPerComponent = width, height, 8
    obj.ColorSpace = pikepdf.Name.DeviceGray
    return obj


def form(pdf: pikepdf.Pdf, content: bytes, resources: pikepdf.Object) -> pikepdf.Object:
    obj = stream(pdf, content)
    obj.Type, obj.Subtype = pikepdf.Name.XObject, pikepdf.Name.Form
    obj.BBox = pikepdf.Array([0, 0, 1, 1])
    obj.Resources = resources
    return obj


def expected(
    kind: str, size: tuple[int, int], ppi: tuple[int, int], matrix: tuple[int | str, ...]
) -> dict[str, object]:
    return {
        "kind": kind,
        "samples": list(size),
        "ppi": list(ppi),
        "matrix": [str(v) for v in matrix],
    }


def truth() -> list[list[dict[str, object]]]:
    pages = [[expected("image", (300, 150), (600, 600), m)] for _, m in ROTATIONS]
    pages.append(
        [
            expected("image", (600, 300), (300, 300), (600, 0, 0, -300, 0, 300)),
            expected("image", (600, 300), (600, 600), (300, 0, 0, -150, 150, 225)),
            expected("image", (600, 300), (300, 300), (600, 0, 0, -300, 0, 300)),
        ]
    )
    full = (300, 0, 0, -300, 0, 300)
    pages.append(
        [
            expected("image", (300, 300), (300, 300), full),
            expected("soft-mask", (900, 600), (900, 600), full),
            expected("stencil", (600, 600), (600, 600), full),
            expected("inline", (2, 1), (2, 1), full),
        ]
    )
    pages.append(
        [
            expected("image", (600, 300), (300, 300), (600, 0, 0, -300, 900, -900)),
            expected("image", (1, 1), (72, 72), ("25/6", 0, 0, "-25/6", 0, 300)),
        ]
    )
    pages.append([expected("image", (300, 600), (600, 600), (0, -150, -300, 0, 600, 300))])
    for flags in [0, 1, 2, 4, 32]:
        pages.append([] if flags in {2, 32} else [expected("image", (300, 300), (300, 300), full)])
    pages.append([])
    pages.append(pages[0])  # Deliberate duplicate occurrence remains ordered.
    return pages


def construct(path: Path) -> None:
    with pikepdf.Pdf.new() as pdf:
        for rotation, _ in ROTATIONS:
            page = pdf.add_blank_page(page_size=(72, 36))
            page.MediaBox = pikepdf.Array([82, 56, 10, 20])
            page.CropBox = pikepdf.Array([20, 30, 60, 50])
            page.UserUnit, page.Rotate = 0.5, rotation
            page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 300, 150)))
            page.Contents = stream(pdf, b"72 0 0 36 10 20 cm /I Do")
        page = pdf.add_blank_page(page_size=(144, 72))
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 600, 300)))
        page.Contents = pikepdf.Array(
            [
                stream(pdf, b"144 0 0 72 0 0 cm /I Do q"),
                stream(pdf, b"0.5 0 0 0.5 0.25 0.25 cm /I Do Q /I Do"),
            ]
        )
        page = pdf.add_blank_page(page_size=(72, 72))
        im = image(pdf, 300, 300)
        im.SMask = image(pdf, 900, 600)
        stencil = stream(pdf, b"\x00" * (75 * 600))
        stencil.Type, stencil.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
        stencil.Width, stencil.Height, stencil.BitsPerComponent, stencil.ImageMask = (
            600,
            600,
            1,
            True,
        )
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=im, M=stencil))
        page.Contents = stream(
            pdf,
            b"72 0 0 72 0 0 cm /I Do /M Do BI /W 2 /H 1 /BPC 8 /CS /RGB ID "
            b"\xff\x00\x00\x00\xff\x00 EI",
        )
        page = pdf.add_blank_page(page_size=(144, 72))
        child = form(
            pdf, b"/I Do", pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 600, 300)))
        )
        child.Matrix = pikepdf.Array([2, 0, 0, 1, 3, 4])
        outer = form(
            pdf,
            b"q 72 0 0 72 0 0 cm /F Do Q /I Do",
            pikepdf.Dictionary(XObject=pikepdf.Dictionary(F=child, I=image(pdf, 1, 1))),
        )
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(F=outer, I=image(pdf, 7, 7)))
        page.Contents = stream(pdf, b"/F Do")
        page = pdf.add_blank_page(page_size=(144, 72))
        ap = form(
            pdf,
            b"10 0 0 20 2 3 cm /I Do",
            pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 300, 600))),
        )
        ap.BBox, ap.Matrix = pikepdf.Array([2, 3, 12, 23]), pikepdf.Array([0, 1, -1, 0, 7, 8])
        page.Annots = pikepdf.Array(
            [
                pdf.make_indirect(
                    pikepdf.Dictionary(
                        Type=pikepdf.Name.Annot,
                        Subtype=pikepdf.Name.Stamp,
                        Rect=pikepdf.Array([72, 0, 144, 36]),
                        AP=pikepdf.Dictionary(N=ap),
                        F=4,
                    )
                )
            ]
        )
        for flags in [0, 1, 2, 4, 32]:
            page = pdf.add_blank_page(page_size=(72, 72))
            ap = form(
                pdf,
                b"/I Do",
                pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 300, 300))),
            )
            page.Annots = pikepdf.Array(
                [
                    pdf.make_indirect(
                        pikepdf.Dictionary(
                            Type=pikepdf.Name.Annot,
                            Subtype=pikepdf.Name.Stamp,
                            Rect=pikepdf.Array([0, 0, 72, 72]),
                            AP=pikepdf.Dictionary(N=ap),
                            F=flags,
                        )
                    )
                ]
            )
        pdf.add_blank_page(page_size=(72, 72))
        pdf.pages.append(pdf.pages[0])  # pyright: ignore[reportUnknownMemberType]
        pdf.save(path, min_version="1.7", deterministic_id=True)


def shape(result: placement.Analysis) -> list[dict[str, object]]:
    return [
        {
            "kind": p.kind,
            "samples": list(p.samples),
            "ppi": list(p.ppi),
            "matrix": [str(v) for v in p.matrix],
        }
        for p in result.placements
    ]


def check(result: placement.Analysis, expected_rows: list[dict[str, object]]) -> None:
    assert result.complete and not result.concerns, "complete inventory"
    rows = shape(result)
    assert len(rows) == len(expected_rows), "placement count"
    for row, wanted in zip(rows, expected_rows, strict=True):
        for field in wanted:
            assert row[field] == wanted[field], field


def run(
    artifacts: Path, analyzer: Callable[[Snapshot, Page], placement.Analysis] = placement.analyze
) -> dict[str, object]:
    artifacts.mkdir()
    declared = truth()
    truth_path = artifacts / "truth.json"
    truth_path.write_text(
        json.dumps(
            {
                "pages": declared,
                "scope": __doc__,
                "annotation_visibility_pixels": {"0": 128, "1": 128, "2": 255, "4": 128, "32": 255},
                "bound": "exact matrix/sample inventory; exact aligned constant-gray visibility; "
                "no composition-fidelity claim",
            },
            indent=2,
        )
        + "\n"
    )
    truth_sha = hashlib.sha256(truth_path.read_bytes()).hexdigest()
    source = artifacts / "ordinary.pdf"
    construct(source)
    original = source.read_bytes()
    saved = snapshot(source, artifacts / "private.pdf")
    results = [analyzer(saved, page) for page in saved.pages]
    assert len(results) == len(declared) == 15
    # Controls are observed rejecting wrong subjects BEFORE outputs are credited.
    good = results[4]
    first = good.placements[0]
    wrong = {
        "wrong-ctm": replace(
            good,
            placements=(
                replace(first, matrix=results[0].placements[0].matrix),
                *good.placements[1:],
            ),
        ),
        "wrong-unit-resolution": replace(
            good, placements=(replace(first, ppi=(150, 150)), *good.placements[1:])
        ),
        "wrong-resource": replace(
            good, placements=(replace(first, samples=(7, 7)), *good.placements[1:])
        ),
        "wrong-order": replace(
            good, placements=(good.placements[1], good.placements[0], good.placements[2])
        ),
        "missing-mask": replace(
            results[5], placements=results[5].placements[:1] + results[5].placements[2:]
        ),
        "partial-complete-claim": replace(good, concerns=("unaccounted image-bearing path",)),
    }
    rejected: dict[str, str] = {}
    for name, result in wrong.items():
        target = 5 if name == "missing-mask" else 4
        try:
            check(result, declared[target])
        except AssertionError as error:
            rejected[name] = str(error)
        else:
            raise AssertionError(f"Wrong subject escaped: {name}")
        check(results[2], declared[2])
        assert source.read_bytes() == saved.path.read_bytes() == original
    for result, want in zip(results, declared, strict=True):
        check(result, want)
    renderer = render.renderer_path()
    visible: dict[str, object] = {}
    for index, flags in enumerate([0, 1, 2, 4, 32], 8):
        raster = render.render_page(saved, saved.pages[index], renderer)
        value = 255 if flags in {2, 32} else 128
        assert raster.size == (300, 300) and raster.rgb == bytes([value]) * (300 * 300 * 3), (
            "annotation visibility"
        )
        visible[str(flags)] = {
            "size": raster.size,
            "rgb_sha256": hashlib.sha256(raster.rgb).hexdigest(),
            "diagnostics": raster.diagnostics,
        }
    source.unlink()
    assert [shape(analyzer(saved, p)) for p in saved.pages] == [shape(r) for r in results]
    assert saved.path.read_bytes() == original
    assert hashlib.sha256(truth_path.read_bytes()).hexdigest() == truth_sha
    report: dict[str, object] = {
        "format": "BookScanBuilderPlacementAcceptance",
        "version": 1,
        "source_sha256": saved.sha256,
        "truth_sha256": truth_sha,
        "pages": [
            {
                "source_page": p.source_page,
                "placements": shape(r),
                "paths": [list(i.path) for i in r.placements],
                "maximum_ppi": r.maximum_ppi,
                "import_fidelity": r.import_fidelity,
            }
            for p, r in zip(saved.pages, results, strict=True)
        ],
        "controls": rejected,
        "actual_cairo_annotation_visibility": visible,
        "source_loss_verified": True,
        "snapshot_bytes_unchanged": True,
        "composition_fidelity_verified": False,
        "source_native_decoding_verified": False,
        "accepted_project_delivered": False,
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
