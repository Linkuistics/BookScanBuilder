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
