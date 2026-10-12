"""Literal construction truth catches omitted placements and wrong CTM composition."""

from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pikepdf
import pytest

from bookscan import intake


def stream(pdf: pikepdf.Pdf, data: bytes) -> pikepdf.Object:
    return pdf.make_stream(data)  # pyright: ignore[reportUnknownMemberType]


def image(pdf: pikepdf.Pdf, width: int = 600, height: int = 300) -> pikepdf.Object:
    obj = stream(pdf, b"\x80" * (width * height))
    obj.Type = pikepdf.Name.XObject
    obj.Subtype = pikepdf.Name.Image
    obj.Width, obj.Height, obj.BitsPerComponent = width, height, 8
    obj.ColorSpace = pikepdf.Name.DeviceGray
    return obj


def form(pdf: pikepdf.Pdf, content: bytes, resources: pikepdf.Object) -> pikepdf.Object:
    obj = stream(pdf, content)
    obj.Type, obj.Subtype = pikepdf.Name.XObject, pikepdf.Name.Form
    obj.BBox = pikepdf.Array([0, 0, 1, 1])
    obj.Resources = resources
    return obj


def save(pdf: pikepdf.Pdf, tmp_path: Path) -> intake.Snapshot:
    original = tmp_path / "input.pdf"
    pdf.save(original, min_version="1.7")
    return intake.snapshot(original, tmp_path / "snapshot.pdf")


def test_repeated_placements_preserve_order_and_restore_graphics_state(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(144, 72))
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf)))
        # 600x300 samples occupy 2x1 inch, then 1x0.5 inch, then restored 2x1.
        page.Contents = pikepdf.Array(
            [
                stream(pdf, b"144 0 0 72 0 0 cm /I Do q"),
                stream(pdf, b"0.5 0 0 0.5 0.25 0.25 cm /I Do Q /I Do"),
            ]
        )
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete and result.concerns == ()
    assert len(result.placements) == 3
    assert [p.ppi for p in result.placements] == [(300, 300), (600, 600), (300, 300)]
    assert [p.matrix for p in result.placements] == [
        (600, 0, 0, -300, 0, 300),
        (300, 0, 0, -150, 150, 225),
        (600, 0, 0, -300, 0, 300),
    ]
    assert result.maximum_ppi == 600 and result.import_fidelity


@pytest.mark.parametrize(
    "rotation,want",
    [
        (0, (150, 0, 0, -75, 0, 75)),
        (90, (0, 150, 75, 0, 0, 0)),
        (180, (-150, 0, 0, 75, 150, 0)),
        (270, (0, -150, -75, 0, 75, 150)),
    ],
)
def test_page_rotation_and_user_unit_reach_placement(
    tmp_path: Path, rotation: int, want: tuple[int, ...]
):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        page.MediaBox = pikepdf.Array([82, 56, 10, 20])
        page.CropBox = pikepdf.Array([20, 30, 60, 50])
        page.UserUnit, page.Rotate = Decimal("0.5"), rotation
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 300, 150)))
        page.Contents = stream(pdf, b"72 0 0 36 10 20 cm /I Do")
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete
    assert result.placements[0].matrix == want
    assert result.placements[0].ppi == (600, 600)


def test_nested_form_matrices_and_local_resource_shadowing(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(144, 72))
        child = form(pdf, b"/I Do", pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf))))
        child.Matrix = pikepdf.Array([2, 0, 0, 1, 3, 4])
        outer = form(
            pdf,
            b"q 72 0 0 72 0 0 cm /F Do Q /I Do",
            pikepdf.Dictionary(XObject=pikepdf.Dictionary(F=child, I=image(pdf, 1, 1))),
        )
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(F=outer, I=image(pdf, 7, 7)))
        page.Contents = stream(pdf, b"/F Do")
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete
    assert [p.samples for p in result.placements] == [(600, 300), (1, 1)]
    assert result.placements[0].matrix == (600, 0, 0, -300, 900, -900)
    assert result.placements[0].ppi == (300, 300)
    assert result.placements[1].ppi == (72, 72)


def test_inline_image_abbreviations_and_stencil_masks_are_counted(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        base = image(pdf, 300, 300)
        mask = image(pdf, 600, 600)
        mask.ImageMask = True
        mask.BitsPerComponent = 1
        del mask.ColorSpace
        base.Mask = mask
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=base, M=mask))
        page.Contents = stream(
            pdf,
            b"72 0 0 72 0 0 cm /I Do /M Do "
            b"BI /W 2 /H 1 /BPC 8 /CS /RGB ID \xff\x00\x00\x00\xff\x00 EI",
        )
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete
    assert [(p.kind, p.samples, p.ppi) for p in result.placements] == [
        ("image", (300, 300), (300, 300)),
        ("mask", (600, 600), (600, 600)),
        ("stencil", (600, 600), (600, 600)),
        ("inline", (2, 1), (2, 1)),
    ]
    assert result.placements[-1].color_space == "/DeviceRGB"


def test_soft_mask_uses_its_own_sample_grid_and_same_physical_placement(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        base = image(pdf, 300, 300)
        base.SMask = image(pdf, 900, 600)
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=base))
        page.Contents = stream(pdf, b"72 0 0 72 0 0 cm /I Do")
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete and result.maximum_ppi == 900
    assert result.placements[1].kind == "soft-mask"
    assert result.placements[1].ppi == (900, 600)
    assert result.placements[0].matrix == result.placements[1].matrix


def test_static_appearance_bbox_matrix_rect_mapping(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(144, 72))
        appearance = form(
            pdf,
            b"10 0 0 20 2 3 cm /I Do",
            pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 300, 600))),
        )
        appearance.BBox = pikepdf.Array([2, 3, 12, 23])
        appearance.Matrix = pikepdf.Array([0, 1, -1, 0, 7, 8])
        page.Annots = pikepdf.Array(
            [
                pdf.make_indirect(
                    pikepdf.Dictionary(
                        Type=pikepdf.Name.Annot,
                        Subtype=pikepdf.Name.Stamp,
                        Rect=pikepdf.Array([72, 0, 144, 36]),
                        AP=pikepdf.Dictionary(N=appearance),
                        F=4,
                    )
                )
            ]
        )
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete and len(result.placements) == 1
    assert result.placements[0].matrix == (0, -150, -300, 0, 600, 300)
    assert result.placements[0].ppi == (600, 600)


@pytest.mark.parametrize(
    "content",
    [
        b"Q /I Do",
        b"q /I Do",
        b"1 0 0 cm /I Do",
        b"0 0 0 0 0 0 cm /I Do",
        b"/Missing Do /I Do",
        b"/G gs /I Do",
        b"/P scn /I Do",
        b"/Sh sh /I Do",
        b"/F 12 Tf (a) Tj /I Do",
        b"mystery /I Do",
    ],
)
def test_incomplete_paths_never_grant_partial_resolution_pass(tmp_path: Path, content: bytes):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 1, 1)))
        page.Contents = stream(pdf, content)
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert not result.complete and result.concerns
    assert result.maximum_ppi is None and result.import_fidelity


def test_form_cycle_names_unavailable_instead_of_recursing(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        recursive = form(pdf, b"/F Do", pikepdf.Dictionary())
        recursive.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(F=recursive))
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(F=recursive))
        page.Contents = stream(pdf, b"/F Do")
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert not result.complete and result.maximum_ppi is None
    assert any("cycle" in issue for issue in result.concerns)


def test_blank_page_has_complete_empty_inventory(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(72, 72))
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete and result.placements == () and result.maximum_ppi is None
    assert not result.import_fidelity


def test_cancel_and_corruption_propagate_before_analysis(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(72, 72))
        saved = save(pdf, tmp_path)
    selected = RuntimeError("owner cancelled")

    def cancel() -> None:
        raise selected

    with pytest.raises(RuntimeError) as caught:
        placement.analyze(saved, saved.pages[0], check_cancel=cancel)
    assert caught.value is selected
    saved.path.write_bytes(b"wrong source")
    with pytest.raises(intake.ImportFailure, match="INVALID_PROJECT"):
        placement.analyze(saved, saved.pages[0])


def test_shear_ppi_uses_axis_length_not_bounding_box(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(144, 144))
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 500, 300)))
        page.Contents = stream(pdf, b"72 96 0 72 0 0 cm /I Do")
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete and result.placements[0].ppi == (300, 300)
    assert result.placements[0].matrix == (300, -400, 0, -300, 0, 600)
    assert not result.import_fidelity


def test_decimal_ctm_is_exact_before_physical_resolution(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 1, 1)))
        page.Contents = stream(pdf, b"0.24 0 0 0.24 0.1 0.2 cm /I Do")
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete
    assert result.placements[0].matrix == (1, 0, 0, -1, Fraction(5, 12), Fraction(1795, 6))
    assert result.placements[0].ppi == (300, 300)


def test_resolution_boundary_is_exact_even_when_float_ppi_rounds_to_300(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 1, 1)))
        page.Contents = stream(pdf, b"0.23999999999999999999 0 0 0.24 0 0 cm /I Do")
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete and result.import_fidelity


@pytest.mark.parametrize("inherited", [False, True])
def test_page_and_form_inherit_resources_only_when_absent(tmp_path: Path, inherited: bool):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        child = form(pdf, b"/I Do", pikepdf.Dictionary())
        if inherited:
            del child.Resources
        resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(F=child, I=image(pdf, 1, 1)))
        page.obj.Parent.Resources = resources
        del page.Resources
        page.Contents = stream(pdf, b"/F Do")
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete == inherited
    assert len(result.placements) == (1 if inherited else 0)


def test_source_loss_and_foreign_occurrence_check(tmp_path: Path):
    from dataclasses import replace

    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(72, 72))
        saved = save(pdf, tmp_path)
    saved.original_path.unlink()
    assert placement.analyze(saved, saved.pages[0]).complete
    with pytest.raises(intake.ImportFailure, match="INVALID_PROJECT"):
        placement.analyze(saved, replace(saved.pages[0], source_page=2))


@pytest.mark.parametrize(
    "feature", ["Type3", "soft-mask", "bad-image", "mask-cycle", "nested-failure"]
)
def test_unaccounted_image_paths_keep_partial_inventory_explicit(tmp_path: Path, feature: str):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        im = image(pdf, 300, 300)
        resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=im))
        prefix = b""
        if feature == "Type3":
            resources.Font = pikepdf.Dictionary(F=pikepdf.Dictionary(Subtype=pikepdf.Name.Type3))
            prefix = b"/F 12 Tf "
        elif feature == "soft-mask":
            group = form(pdf, b"/I Do", resources)
            resources.ExtGState = pikepdf.Dictionary(
                G=pikepdf.Dictionary(SMask=pikepdf.Dictionary(S=pikepdf.Name.Alpha, G=group))
            )
            prefix = b"/G gs "
        elif feature == "bad-image":
            im.Width = 0
        elif feature == "mask-cycle":
            im.SMask = im
        else:
            resources.XObject.F = form(pdf, b"/Missing Do", pikepdf.Dictionary())
            prefix = b"/F Do "
        page.Resources = resources
        page.Contents = stream(pdf, prefix + b"72 0 0 72 0 0 cm /I Do")
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert not result.complete and result.concerns and result.maximum_ppi is None
    assert result.import_fidelity
    assert len(result.placements) == (0 if feature == "bad-image" else 1)


@pytest.mark.parametrize("nested", [False, True])
def test_cancellation_inside_traversal_is_not_an_unavailable_assessment(
    tmp_path: Path, nested: bool
):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        if nested:
            child = form(pdf, b"q Q " * 10_000, pikepdf.Dictionary())
            page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(F=child))
            page.Contents = stream(pdf, b"/F Do")
        else:
            page.Contents = stream(pdf, b"q Q " * 10_000)
        saved = save(pdf, tmp_path)
    selected = ValueError("selected owner outcome")
    calls = 0

    def cancel() -> None:
        nonlocal calls
        calls += 1
        if calls == 100:
            raise selected

    with pytest.raises(ValueError) as caught:
        placement.analyze(saved, saved.pages[0], check_cancel=cancel)
    assert caught.value is selected


@pytest.mark.parametrize("flags,count", [(0, 1), (1, 1), (2, 0), (4, 1), (32, 0)])
def test_annotation_visibility_matches_selected_cairo_png_renderer(
    tmp_path: Path, flags: int, count: int
):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        appearance = form(
            pdf, b"/I Do", pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image(pdf, 300, 300)))
        )
        page.Annots = pikepdf.Array(
            [
                pdf.make_indirect(
                    pikepdf.Dictionary(
                        Type=pikepdf.Name.Annot,
                        Subtype=pikepdf.Name.Stamp,
                        Rect=pikepdf.Array([0, 0, 72, 72]),
                        AP=pikepdf.Dictionary(N=appearance),
                        F=flags,
                    )
                )
            ]
        )
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete and len(result.placements) == count


def test_mask_nesting_limit_is_explicitly_unavailable(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        im = image(pdf, 1, 1)
        head = im
        for _ in range(70):
            child = image(pdf, 1, 1)
            head.SMask = child
            head = child
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=im))
        page.Contents = stream(pdf, b"72 0 0 72 0 0 cm /I Do")
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert not result.complete and result.import_fidelity
    assert any("depth" in c for c in result.concerns)


def test_gated_invisible_navigation_link_is_not_an_image_path(tmp_path: Path):
    from bookscan import placement

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        page.Annots = pikepdf.Array(
            [
                pdf.make_indirect(
                    pikepdf.Dictionary(
                        Type=pikepdf.Name.Annot,
                        Subtype=pikepdf.Name.Link,
                        Rect=pikepdf.Array([0, 0, 72, 72]),
                        Border=pikepdf.Array([0, 0, 0]),
                    )
                )
            ]
        )
        saved = save(pdf, tmp_path)
    result = placement.analyze(saved, saved.pages[0])
    assert result.complete and not result.placements and not result.import_fidelity
