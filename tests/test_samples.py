"""Literal sample grids catch decoding, row-padding and resource-scope mistakes."""

import zlib
from pathlib import Path

import pikepdf
import pytest

from bookscan import intake


def image(pdf: pikepdf.Pdf, data: bytes, width: int, height: int, bpc: int = 8):
    obj = pdf.make_stream(data)  # pyright: ignore[reportUnknownMemberType]
    obj.Type, obj.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
    obj.Width, obj.Height, obj.BitsPerComponent = width, height, bpc
    obj.ColorSpace = pikepdf.Name.DeviceGray
    return obj


def save(pdf: pikepdf.Pdf, tmp_path: Path) -> intake.Snapshot:
    source = tmp_path / "input.pdf"
    pdf.save(source, min_version="1.7")
    return intake.snapshot(source, tmp_path / "snapshot.pdf")


@pytest.mark.parametrize(
    "width,height,bpc,data,want",
    [
        (3, 2, 1, b"\xa0\x40", [(1,), (0,), (1,), (0,), (1,), (0,)]),
        (3, 2, 2, b"\x18\xe4", [(0,), (1,), (2,), (3,), (2,), (1,)]),
        (3, 1, 4, b"\x1f\x70", [(1,), (15,), (7,)]),
        (2, 1, 8, b"\x01\xfe", [(1,), (254,)]),
        (2, 1, 16, b"\x01\x02\xff\xfe", [(258,), (65534,)]),
    ],
)
def test_packed_rows_are_msb_first_and_skip_padding(
    tmp_path: Path, width: int, height: int, bpc: int, data: bytes, want: list[tuple[int]]
):
    from bookscan import samples

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        page.Resources = pikepdf.Dictionary(
            XObject=pikepdf.Dictionary(I=image(pdf, data, width, height, bpc))
        )
        page.Contents = pdf.make_stream(b"72 0 0 72 0 0 cm /I Do")  # pyright: ignore[reportUnknownMemberType]
        saved = save(pdf, tmp_path)
    result = samples.collect(saved, saved.pages[0])
    assert result.resolution.complete and result.samples_available
    sample = result.images[0]
    assert sample.packed == data
    assert list(sample.pixels()) == want
    assert sample.color is not None
    assert sample.decode == (0, 1) and sample.color.kind == "/DeviceGray"
    assert sample.placement.ppi == (width, height)


def test_rgb_decode_metadata_is_not_applied_to_raw_samples(tmp_path: Path):
    from bookscan import samples

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        obj = image(pdf, b"\x00\x80\xff", 1, 1)
        obj.ColorSpace = pikepdf.Name.DeviceRGB
        obj.Decode = pikepdf.Array([1, 0, 0, 1, 1, 0])
        obj.Interpolate = True
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
        page.Contents = pdf.make_stream(b"/I Do")  # pyright: ignore[reportUnknownMemberType]
        saved = save(pdf, tmp_path)
    sample = samples.collect(saved, saved.pages[0]).images[0]
    assert list(sample.pixels()) == [(0, 128, 255)]
    assert sample.decode == (1, 0, 0, 1, 1, 0) and sample.interpolate
    assert not sample.composition_verified


def test_inline_named_colour_and_nested_form_resources(tmp_path: Path):
    from bookscan import samples

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        form = pdf.make_stream(b"BI /W 1 /H 1 /BPC 8 /CS /C ID \x12\x34\x56 EI")  # pyright: ignore[reportUnknownMemberType]
        form.Type, form.Subtype = pikepdf.Name.XObject, pikepdf.Name.Form
        form.BBox = pikepdf.Array([0, 0, 1, 1])
        form.Resources = pikepdf.Dictionary(ColorSpace=pikepdf.Dictionary(C=pikepdf.Name.DeviceRGB))
        page.Resources = pikepdf.Dictionary(
            XObject=pikepdf.Dictionary(F=form),
            ColorSpace=pikepdf.Dictionary(C=pikepdf.Name.DeviceGray),
        )
        page.Contents = pdf.make_stream(b"/F Do /F Do")  # pyright: ignore[reportUnknownMemberType]
        saved = save(pdf, tmp_path)
    result = samples.collect(saved, saved.pages[0])
    assert result.samples_available
    assert [list(s.pixels()) for s in result.images] == [[(18, 52, 86)], [(18, 52, 86)]]
    assert result.images[0].placement.path != result.images[1].placement.path


def test_stencil_and_soft_mask_keep_separate_grids_and_decode(tmp_path: Path):
    from bookscan import samples

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        base = image(pdf, b"\x20\x40", 2, 1)
        mask = image(pdf, b"\xa0", 3, 1, 1)
        mask.ImageMask, mask.Decode = True, pikepdf.Array([1, 0])
        del mask.ColorSpace
        soft = image(pdf, b"\x00\x80\xff", 3, 1)
        soft.Matte = pikepdf.Array([0])
        base.Mask, base.SMask = mask, soft
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=base))
        page.Contents = pdf.make_stream(b"72 0 0 72 0 0 cm /I Do")  # pyright: ignore[reportUnknownMemberType]
        saved = save(pdf, tmp_path)
    result = samples.collect(saved, saved.pages[0])
    assert result.samples_available
    assert [s.placement.kind for s in result.images] == ["image", "mask", "soft-mask"]
    assert [list(s.pixels()) for s in result.images] == [
        [(32,), (64,)],
        [(1,), (0,), (1,)],
        [(0,), (128,), (255,)],
    ]
    assert result.images[1].decode == (1, 0)
    assert result.images[2].matte == (0,)


@pytest.mark.parametrize(
    "corruption", ["short", "extra", "decode", "interpolate", "codec", "color"]
)
def test_unavailable_samples_never_change_complete_resolution(tmp_path: Path, corruption: str):
    from bookscan import samples

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        obj = image(pdf, b"\x80", 1, 1)
        if corruption in {"short", "extra"}:
            obj.write(b"" if corruption == "short" else b"\x80\x80")
        elif corruption == "decode":
            obj.Decode = pikepdf.Array([0])
        elif corruption == "interpolate":
            obj.Interpolate = 7
        elif corruption == "codec":
            obj.Filter = pikepdf.Name.DCTDecode
        elif corruption == "color":
            obj.ColorSpace = pikepdf.Array([pikepdf.Name.Lab, pikepdf.Dictionary()])
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
        page.Contents = pdf.make_stream(b"/I Do")  # pyright: ignore[reportUnknownMemberType]
        saved = save(pdf, tmp_path)
    result = samples.collect(saved, saved.pages[0])
    assert result.resolution.complete
    assert not result.samples_available and result.concerns
    assert result.images[0].packed is None and result.images[0].unavailable


def test_source_loss_cancel_and_snapshot_corruption(tmp_path: Path):
    from bookscan import samples

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        obj = image(pdf, b"\x80", 1, 1)
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
        page.Contents = pdf.make_stream(b"/I Do")  # pyright: ignore[reportUnknownMemberType]
        saved = save(pdf, tmp_path)
    (tmp_path / "input.pdf").unlink()
    assert samples.collect(saved, saved.pages[0]).samples_available
    selected = ValueError("owner cancellation")

    def cancelled():
        raise selected

    with pytest.raises(ValueError) as caught:
        samples.collect(saved, saved.pages[0], check_cancel=cancelled)
    assert caught.value is selected
    saved.path.write_bytes(b"broken")
    with pytest.raises(intake.ImportFailure, match="snapshot"):
        samples.collect(saved, saved.pages[0])


@pytest.mark.parametrize("inline", [False, True])
def test_png_predictor_decodes_channels_without_inventing_rgb(tmp_path: Path, inline: bool):
    from bookscan import samples

    # Independently encoded PNG Up predictor: first row 10,20; second 15,18.
    compressed = zlib.compress(b"\x02\x0a\x14\x02\x05\xfe")
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        if inline:
            page.Contents = pdf.make_stream(  # pyright: ignore[reportUnknownMemberType]
                b"BI /W 2 /H 2 /BPC 8 /CS /G /F /Fl /DP << /Predictor 12 /Columns 2 >> ID "
                + compressed
                + b" EI"
            )
        else:
            obj = image(pdf, compressed, 2, 2)
            obj.Filter = pikepdf.Name.FlateDecode
            obj.DecodeParms = pikepdf.Dictionary(Predictor=12, Columns=2)
            page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
            page.Contents = pdf.make_stream(b"/I Do")  # pyright: ignore[reportUnknownMemberType]
        saved = save(pdf, tmp_path)
    result = samples.collect(saved, saved.pages[0])
    assert result.samples_available
    assert list(result.images[0].pixels()) == [(10,), (20,), (15,), (18,)]
    assert result.images[0].filters == ("/FlateDecode",)
    assert result.images[0].decode_parameters is not None


@pytest.mark.parametrize("use_stream", [False, True])
def test_indexed_palette_and_integer_decode_domain(tmp_path: Path, use_stream: bool):
    from bookscan import samples

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        obj = image(pdf, b"\x12", 2, 1, 4)
        palette = b"\xff\x00\x00\x00\xff\x00\x00\x00\xff"
        lookup = pdf.make_stream(palette) if use_stream else pikepdf.String(palette)  # pyright: ignore[reportUnknownMemberType]
        obj.ColorSpace = pikepdf.Array([pikepdf.Name.Indexed, pikepdf.Name.DeviceRGB, 2, lookup])
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
        page.Contents = pdf.make_stream(b"/I Do")  # pyright: ignore[reportUnknownMemberType]
        saved = save(pdf, tmp_path)
    result = samples.collect(saved, saved.pages[0])
    assert result.samples_available
    sample = result.images[0]
    assert sample.color is not None and sample.color.palette == palette
    assert sample.color.high == 2 and sample.color.base is not None
    assert sample.color.base.kind == "/DeviceRGB"
    assert sample.decode == (0, 15) and list(sample.pixels()) == [(1,), (2,)]
    assert not sample.composition_verified


@pytest.mark.parametrize("default", [False, True])
def test_icc_profile_bytes_range_and_default_colour_substitution(tmp_path: Path, default: bool):
    from bookscan import samples

    profile_bytes = b"literal profile metadata, no conversion oracle"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        obj = image(pdf, b"\x0a\x14\x1e", 1, 1)
        profile = pdf.make_stream(profile_bytes)  # pyright: ignore[reportUnknownMemberType]
        profile.N, profile.Range = 3, pikepdf.Array([-1, 1, 0, 2, 0, 1])
        profile.Alternate = pikepdf.Name.DeviceRGB
        cs = pikepdf.Array([pikepdf.Name.ICCBased, profile])
        obj.ColorSpace = pikepdf.Name.DeviceRGB if default else cs
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
        if default:
            page.Resources.ColorSpace = pikepdf.Dictionary(DefaultRGB=cs)
        page.Contents = pdf.make_stream(b"/I Do")  # pyright: ignore[reportUnknownMemberType]
        saved = save(pdf, tmp_path)
    sample = samples.collect(saved, saved.pages[0]).images[0]
    assert sample.packed == b"\x0a\x14\x1e" and sample.color is not None
    assert sample.color.kind == "/ICCBased" and sample.color.profile == profile_bytes
    assert sample.decode == (-1, 1, 0, 2, 0, 1)
    assert not sample.composition_verified


@pytest.mark.parametrize(
    "kind", ["palette-short", "icc-n", "key-range", "key-reversed", "stencil-bpc"]
)
def test_malformed_colour_and_mask_metadata_is_unavailable(tmp_path: Path, kind: str):
    from bookscan import samples

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        obj = image(pdf, b"\x80", 1, 1)
        if kind == "palette-short":
            obj.ColorSpace = pikepdf.Array(
                [pikepdf.Name.Indexed, pikepdf.Name.DeviceRGB, 2, pikepdf.String(b"x")]
            )
        elif kind == "icc-n":
            profile = pdf.make_stream(b"profile")  # pyright: ignore[reportUnknownMemberType]
            profile.N = 2
            obj.ColorSpace = pikepdf.Array([pikepdf.Name.ICCBased, profile])
        elif kind.startswith("key"):
            obj.Mask = pikepdf.Array([0, 256] if kind == "key-range" else [200, 100])
        else:
            obj.ImageMask = True
            del obj.ColorSpace
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
        page.Contents = pdf.make_stream(b"/I Do")  # pyright: ignore[reportUnknownMemberType]
        saved = save(pdf, tmp_path)
    result = samples.collect(saved, saved.pages[0])
    assert not result.samples_available and result.images[0].unavailable


def test_selected_cancel_inside_decoder_survives_recursive_handlers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from bookscan import samples

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        obj = image(pdf, b"\x80", 1, 1)
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
        page.Contents = pdf.make_stream(b"/I Do")  # pyright: ignore[reportUnknownMemberType]
        saved = save(pdf, tmp_path)
    selected = ValueError("selected inside sample decoding")
    entered = False
    original = samples.decode

    def observed(
        obj: pikepdf.Object | pikepdf.PdfInlineImage,
        resources: object,
        placed: samples.placement.Placement,
        checked: samples.Callable[[], None],
    ) -> samples.Sample:
        nonlocal entered
        entered = True
        return original(obj, resources, placed, checked)

    def cancelled():
        if entered:
            raise selected

    monkeypatch.setattr(samples, "decode", observed)
    with pytest.raises(ValueError) as caught:
        samples.collect(saved, saved.pages[0], check_cancel=cancelled)
    assert entered and caught.value is selected
