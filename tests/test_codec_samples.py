"""Known-channel constructions catch codec polarity, grid and interpretation errors."""

import io
import zlib
from pathlib import Path
from typing import cast

import pikepdf
import pytest
from PIL import Image, TiffImagePlugin

from bookscan import intake, samples


def jpeg(mode: str = "L") -> bytes:
    buffer = io.BytesIO()
    with Image.new(mode, (16, 8), 128 if mode == "L" else (128, 128, 128)) as image:
        image.save(buffer, format="JPEG", quality=100, subsampling=0)
    return buffer.getvalue()


def fax(group: int = 4) -> bytes:
    buffer = io.BytesIO()
    with Image.frombytes("1", (9, 2), b"\xaa\x80\x55\x00") as image:
        image.save(buffer, format="TIFF", compression="group4" if group == 4 else "group3")
    data = buffer.getvalue()
    with Image.open(io.BytesIO(data)) as tif:
        assert isinstance(tif, TiffImagePlugin.TiffImageFile)
        offsets = cast(tuple[int, ...], tif.tag_v2[273])
        lengths = cast(tuple[int, ...], tif.tag_v2[279])
        assert len(offsets) == len(lengths) == 1
        start, size = offsets[0], lengths[0]
    return data[start : start + size]


def fixture(
    tmp_path: Path,
    codec: str,
    data: bytes,
    *,
    size: tuple[int, int] = (16, 8),
    bits: int = 8,
    color: str = "/DeviceGray",
    params: pikepdf.Object | None = None,
    inline: bool = False,
    wrapped: bool = False,
    inverse: bool = False,
    stencil: bool = False,
    masked: bool = False,
) -> intake.Snapshot:
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 72))
        obj = pdf.make_stream(zlib.compress(data) if wrapped else data)  # pyright: ignore[reportUnknownMemberType]
        obj.Type, obj.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
        obj.Width, obj.Height, obj.BitsPerComponent = *size, bits
        obj.ColorSpace = pikepdf.Name(color)
        obj.Filter = (
            pikepdf.Array([pikepdf.Name.FlateDecode, pikepdf.Name(codec)])
            if wrapped
            else pikepdf.Name(codec)
        )
        if params is not None:
            obj.DecodeParms = pikepdf.Array([None, params]) if wrapped else params
        if inverse:
            obj.Decode = pikepdf.Array([1, 0] * (3 if color == "/DeviceRGB" else 1))
        if stencil:
            obj.ImageMask = True
            del obj.ColorSpace
        if masked:
            mask = pdf.make_stream(b"\x00")  # pyright: ignore[reportUnknownMemberType]
            mask.Type, mask.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
            mask.Width, mask.Height, mask.BitsPerComponent = 1, 1, 8
            mask.ColorSpace = pikepdf.Name.DeviceGray
            obj.SMask = mask
        if inline:
            dictionary = obj.stream_dict.unparse()[2:-2]
            page.Contents = pdf.make_stream(  # pyright: ignore[reportUnknownMemberType]
                b"BI " + dictionary + b" ID " + obj.read_raw_bytes() + b" EI"
            )  # pyright: ignore[reportUnknownMemberType]
        else:
            page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
            page.Contents = pdf.make_stream(b"/I Do")  # pyright: ignore[reportUnknownMemberType]
        source = tmp_path / "input.pdf"
        pdf.save(source, min_version="1.7", static_id=True)
    return intake.snapshot(source, tmp_path / "snapshot.pdf")


@pytest.mark.parametrize("mode", ["L", "RGB"])
@pytest.mark.parametrize("inline,wrapped", [(False, False), (False, True), (True, False)])
def test_dct_keeps_declared_channels_without_decode_or_mask(
    tmp_path: Path, mode: str, inline: bool, wrapped: bool
):
    saved = fixture(
        tmp_path,
        "/DCTDecode",
        jpeg(mode),
        color="/DeviceGray" if mode == "L" else "/DeviceRGB",
        inline=inline,
        wrapped=wrapped,
        inverse=True,
        masked=not inline,
    )
    result = samples.collect(saved, saved.pages[0])
    assert result.samples_available, result.concerns
    sample = result.images[0]
    assert sample.packed == bytes([128]) * (128 if mode == "L" else 384)
    assert sample.decode == (1, 0) * (1 if mode == "L" else 3)
    assert not sample.composition_verified
    if not inline:
        assert result.images[1].packed == b"\x00"


@pytest.mark.parametrize("group", [3, 4])
@pytest.mark.parametrize("black_is_one", [False, True])
@pytest.mark.parametrize("inline,wrapped", [(False, False), (False, True), (True, False)])
def test_ccitt_raw_polarity_padding_and_separate_decode(
    tmp_path: Path, group: int, black_is_one: bool, inline: bool, wrapped: bool
):
    saved = fixture(
        tmp_path,
        "/CCITTFaxDecode",
        fax(group),
        size=(9, 2),
        bits=1,
        params=pikepdf.Dictionary(
            K=-1 if group == 4 else 0, Columns=9, Rows=2, BlackIs1=black_is_one
        ),
        inline=inline,
        wrapped=wrapped,
        inverse=True,
        stencil=inline,
    )
    result = samples.collect(saved, saved.pages[0])
    assert result.samples_available, result.concerns
    # TIFF's BlackIsZero photometry reverses its self-photometric fax runs:
    # encoded rows start black/white respectively. PDF default raw black=0.
    want = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    if black_is_one:
        want = [1 - value for value in want]
    sample = result.images[0]
    assert list(sample.pixels()) == [(value,) for value in want]
    assert sample.decode == (1, 0)
    assert not sample.composition_verified


@pytest.mark.parametrize("black_is_one", [False, True])
def test_hand_encoded_ccitt_white_black_runs(tmp_path: Path, black_is_one: bool):
    # TIFF 6 section 10 tables: EOL, white9=10100, white0=00110101,
    # black9=000100, followed only by byte padding. No image encoder oracle.
    # https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf
    saved = fixture(
        tmp_path,
        "/CCITTFaxDecode",
        bytes.fromhex("001a0009a880"),
        size=(9, 2),
        bits=1,
        params=pikepdf.Dictionary(K=0, Columns=9, Rows=2, BlackIs1=black_is_one),
    )
    result = samples.collect(saved, saved.pages[0])
    assert result.samples_available, result.concerns
    assert result.images[0].packed == (
        bytes.fromhex("0000ff80") if black_is_one else bytes.fromhex("ff800000")
    )


@pytest.mark.parametrize(
    "params",
    [
        {"K": -1, "Columns": 10},
        {"K": -1, "Columns": 9, "Rows": 3},
        {"K": -1, "Columns": 9, "EncodedByteAlign": True},
        {"K": -1, "Columns": 9, "BlackIs1": 1},
        {"K": -1, "Columns": 9, "EndOfBlock": False},
        {"K": -1, "Columns": 9, "DamagedRowsBeforeError": 1},
    ],
)
def test_ccitt_unsupported_or_malformed_parameters_are_unavailable(
    tmp_path: Path, params: dict[str, int | bool]
):
    saved = fixture(
        tmp_path,
        "/CCITTFaxDecode",
        fax(),
        size=(9, 2),
        bits=1,
        params=pikepdf.Dictionary({"/" + key: value for key, value in params.items()}),
    )
    result = samples.collect(saved, saved.pages[0])
    assert result.resolution.complete
    assert not result.samples_available and result.images[0].unavailable


@pytest.mark.parametrize("problem", ["dimension", "bits", "channels", "transform", "corrupt"])
def test_dct_invalid_or_unverified_interpretations_are_named_unavailable(
    tmp_path: Path, problem: str
):
    saved = fixture(
        tmp_path,
        "/DCTDecode",
        b"broken JPEG" if problem == "corrupt" else jpeg("RGB"),
        size=(15, 8) if problem == "dimension" else (16, 8),
        bits=16 if problem == "bits" else 8,
        color="/DeviceGray" if problem == "channels" else "/DeviceRGB",
        params=pikepdf.Dictionary(ColorTransform=0) if problem == "transform" else None,
    )
    result = samples.collect(saved, saved.pages[0])
    assert result.resolution.complete
    assert not result.samples_available and result.images[0].packed is None
    assert result.images[0].unavailable


def test_source_loss_and_selected_codec_cancel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    saved = fixture(tmp_path, "/DCTDecode", jpeg())
    (tmp_path / "input.pdf").unlink()
    assert samples.collect(saved, saved.pages[0]).samples_available
    original = pikepdf.PdfImage.as_pil_image
    entered = False
    selected = ValueError("owner selected during actual codec read")

    def observed(self: pikepdf.PdfImage, apply_decode_array: bool = True, apply_mask: bool = True):
        nonlocal entered
        entered = True
        return original(self, apply_decode_array=apply_decode_array, apply_mask=apply_mask)

    def cancelled():
        if entered:
            raise selected

    monkeypatch.setattr(pikepdf.PdfImage, "as_pil_image", observed)
    with pytest.raises(ValueError) as caught:
        samples.collect(saved, saved.pages[0], check_cancel=cancelled)
    assert entered and caught.value is selected


def test_named_library_codec_failure_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    saved = fixture(tmp_path, "/DCTDecode", jpeg())

    def unavailable(
        self: pikepdf.PdfImage, apply_decode_array: bool = True, apply_mask: bool = True
    ):
        raise pikepdf.UnsupportedImageTypeError("specific decoder limitation")

    monkeypatch.setattr(pikepdf.PdfImage, "as_pil_image", unavailable)
    result = samples.collect(saved, saved.pages[0])
    assert not result.samples_available
    assert result.images[0].unavailable == "specific decoder limitation"


def test_constant_rgb_dct_channels_have_independently_bounded_colour(tmp_path: Path):
    buffer = io.BytesIO()
    # Constant 8x8 DCT blocks at Q=100, no chroma subsampling. Rounding Y/Cb/Cr,
    # inverse coefficients <=1.772 and output rounding bound each channel by 2.
    # This bound precedes decoding; it is no real JPEG/composition oracle.
    with Image.new("RGB", (16, 8), (18, 52, 86)) as image:
        image.save(buffer, format="JPEG", quality=100, subsampling=0)
    saved = fixture(tmp_path, "/DCTDecode", buffer.getvalue(), color="/DeviceRGB")
    result = samples.collect(saved, saved.pages[0])
    assert result.samples_available, result.concerns
    assert all(
        abs(channel - want) <= 2
        for pixel in result.images[0].pixels()
        for channel, want in zip(pixel, (18, 52, 86), strict=True)
    )
