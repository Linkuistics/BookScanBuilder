"""Hand-encoded ICC v4 matrix/TRC profiles; no CMM builds the input truth."""

import struct


def profile(gamma: int = 1, *, swapped: bool = False) -> bytes:
    # ICC.1:2010 sections 7, 9.2.30/31/38/39/44/45, 10.16 and 10.28.
    # https://www.color.org/specification/ICC1v43_2010-12.pdf
    # Both profiles share these fixed D50-adapted columns, so their matrix
    # composition cancels. Only the independently declared power curve changes.
    columns = [(28579, 14582, 913), (25236, 46981, 6364), (9377, 3973, 46804)]
    if swapped:
        columns[0], columns[2] = columns[2], columns[0]
    tags = {
        b"wtpt": b"XYZ \0\0\0\0" + struct.pack(">iii", 63190, 65536, 54061),
        b"rXYZ": b"XYZ \0\0\0\0" + struct.pack(">iii", *columns[0]),
        b"gXYZ": b"XYZ \0\0\0\0" + struct.pack(">iii", *columns[1]),
        b"bXYZ": b"XYZ \0\0\0\0" + struct.pack(">iii", *columns[2]),
    }
    curve = b"para\0\0\0\0\0\0\0\0" + struct.pack(">i", gamma * 65536)
    for key in (b"rTRC", b"gTRC", b"bTRC"):
        tags[key] = curve
    for key, text in [
        (b"desc", "Constructed matrix power curve"),
        (b"cprt", "Test-owned construction"),
    ]:
        encoded = text.encode("utf-16-be")
        tags[key] = (
            b"mluc\0\0\0\0"
            + struct.pack(">II", 1, 12)
            + b"enUS"
            + struct.pack(">II", len(encoded), 28)
            + encoded
        )
    header = bytearray(128)
    header[8:12] = b"\x04\x30\0\0"
    header[12:24] = b"mntrRGB XYZ "
    header[24:36] = struct.pack(">6H", 2026, 1, 1, 0, 0, 0)
    header[36:40] = b"acsp"
    header[64:68] = struct.pack(">I", 1)
    header[68:80] = struct.pack(">iii", 63190, 65536, 54061)
    directory = bytearray(struct.pack(">I", len(tags)))
    payload = bytearray()
    offset = 128 + 4 + 12 * len(tags)
    for key, value in tags.items():
        directory.extend(key + struct.pack(">II", offset + len(payload), len(value)))
        payload.extend(value)
        payload.extend(b"\0" * (-len(payload) % 4))
    data = header + directory + payload
    data[:4] = struct.pack(">I", len(data))
    return bytes(data)
