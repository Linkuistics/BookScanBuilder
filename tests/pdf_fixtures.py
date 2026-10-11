"""Independent byte-level specimens; writer repair cannot erase intended faults."""

from pathlib import Path


def raw_pdf(
    path: Path,
    catalog: bytes = b"",
    page: bytes = b"",
    stream_dict: bytes = b"",
    stream: bytes = b"",
) -> Path:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R " + catalog + b" >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 240 320] /Resources << >> "
        b"/Contents 4 0 R " + page + b" >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" "
        + stream_dict
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.7\n")
    offsets: list[int] = []
    for n, value in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{n} 0 obj\n".encode() + value + b"\nendobj\n")
    xref = len(data)
    data.extend(b"xref\n0 5\n0000000000 65535 f \n")
    for offset in offsets:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"
    )
    path.write_bytes(data)
    return path


def rich_pdf(path: Path, *, defaults: bool = False, annotated: bool = True) -> Path:
    """Visible nested Form/image, stencil, soft mask, metadata cycles and geometry."""
    import zlib

    import pikepdf

    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(240, 320))
        image = pdf.make_stream(zlib.compress(bytes([190, 30, 70, 30, 120, 220] * 8)))  # pyright: ignore[reportUnknownMemberType]
        image.stream_dict.update(
            pikepdf.Dictionary(
                Type=pikepdf.Name.XObject,
                Subtype=pikepdf.Name.Image,
                Width=4,
                Height=4,
                BitsPerComponent=8,
                ColorSpace=pikepdf.Name.DeviceRGB,
                Filter=pikepdf.Name.FlateDecode,
            )
        )
        globals_stream = pdf.make_stream(b"decoder-globals-kept-raw")  # pyright: ignore[reportUnknownMemberType]
        image["/DecodeParms"] = pikepdf.Dictionary(Predictor=1, JBIG2Globals=globals_stream)
        soft = pdf.make_stream(bytes([255, 210, 170, 130] * 4))  # pyright: ignore[reportUnknownMemberType]
        soft.stream_dict.update(
            pikepdf.Dictionary(
                Type=pikepdf.Name.XObject,
                Subtype=pikepdf.Name.Image,
                Width=4,
                Height=4,
                BitsPerComponent=8,
                ColorSpace=pikepdf.Name.DeviceGray,
            )
        )
        image["/SMask"] = soft
        stencil = pdf.make_stream(b"\xaa\x55\xaa\x55")  # pyright: ignore[reportUnknownMemberType]
        stencil.stream_dict.update(
            pikepdf.Dictionary(
                Type=pikepdf.Name.XObject,
                Subtype=pikepdf.Name.Image,
                Width=8,
                Height=4,
                ImageMask=True,
                BitsPerComponent=1,
            )
        )
        form = pdf.make_stream(  # pyright: ignore[reportUnknownMemberType]
            b"q 120 0 0 120 40 80 cm /Im Do Q\nq 0 0 0 rg 100 0 0 30 50 30 cm /Mask Do Q\n"
        )  # pyright: ignore[reportUnknownMemberType]
        form.stream_dict.update(
            pikepdf.Dictionary(
                Type=pikepdf.Name.XObject,
                Subtype=pikepdf.Name.Form,
                BBox=pikepdf.Array([0, 0, 240, 320]),
                Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=image, Mask=stencil)),
                StructParent=7,
            )
        )
        resources = pdf.make_indirect(pikepdf.Dictionary(XObject=pikepdf.Dictionary(Form=form)))
        resources["/Cycle"] = resources
        resources["/RetainedName"] = pikepdf.Name.Test
        resources["/RetainedString"] = pikepdf.String(b"raw\x00bytes\xff")
        resources["/RetainedBoolean"] = True
        page.obj["/Resources"] = resources
        page.obj["/Contents"] = pdf.make_stream(b"q /Form Do Q\n")  # pyright: ignore[reportUnknownMemberType]
        if not defaults:
            page.obj["/CropBox"] = pikepdf.Array([10, 20, 230, 310])
            page.obj["/BleedBox"] = pikepdf.Array([8, 18, 232, 312])
            page.obj["/TrimBox"] = pikepdf.Array([12, 22, 228, 308])
            page.obj["/ArtBox"] = pikepdf.Array([15, 25, 225, 305])
            page.obj["/Rotate"] = 90
            page.obj["/UserUnit"] = 2
        # Inherited attributes; page-local optional boxes/UserUnit remain local.
        for key in ("/Resources", "/MediaBox", "/CropBox", "/Rotate"):
            if key in page.obj:
                page.obj["/Parent"][key] = page.obj[key]
                del page.obj[key]
        if annotated:
            appearance = pdf.make_stream(b"0 0 1 rg 0 0 30 20 re f\n")  # pyright: ignore[reportUnknownMemberType]
            appearance.stream_dict.update(
                pikepdf.Dictionary(
                    Type=pikepdf.Name.XObject,
                    Subtype=pikepdf.Name.Form,
                    BBox=pikepdf.Array([0, 0, 30, 20]),
                    Resources=pikepdf.Dictionary(),
                    Matrix=pikepdf.Array([1, 0, 0, 1, 0, 0]),
                )
            )
            page.obj["/Annots"] = pikepdf.Array(
                [
                    pikepdf.Dictionary(
                        Subtype=pikepdf.Name.Stamp,
                        Rect=pikepdf.Array([20, 250, 50, 270]),
                        AP=pikepdf.Dictionary(N=appearance),
                        P=page.obj,
                        F=4,
                    )
                ]
            )
        pdf.Root["/Version"] = pikepdf.Name("/1.7")
        pdf.save(path, compress_streams=False, stream_decode_level=pikepdf.StreamDecodeLevel.none)
    return path
