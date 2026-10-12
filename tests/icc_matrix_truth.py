"""Test-owned exact matrix/power truth; no CMM, renderer or arbitrary-profile oracle."""

import struct
from dataclasses import dataclass
from fractions import Fraction

type Vector = tuple[Fraction, Fraction, Fraction]
type Matrix = tuple[Vector, Vector, Vector]


@dataclass(frozen=True)
class MatrixProfile:
    matrix: Matrix
    powers: tuple[int, int, int]
    white: Vector


def inverse(matrix: Matrix) -> Matrix:
    rows = [list(row) + [Fraction(int(i == j)) for j in range(3)] for i, row in enumerate(matrix)]
    for col in range(3):
        pivot = next((i for i in range(col, 3) if rows[i][col]), None)
        if pivot is None:
            raise ValueError("singular profile matrix")
        rows[col], rows[pivot] = rows[pivot], rows[col]
        divisor = rows[col][col]
        rows[col] = [v / divisor for v in rows[col]]
        for i in range(3):
            if i != col:
                factor = rows[i][col]
                rows[i] = [v - factor * p for v, p in zip(rows[i], rows[col], strict=True)]
    return (
        (rows[0][3], rows[0][4], rows[0][5]),
        (rows[1][3], rows[1][4], rows[1][5]),
        (rows[2][3], rows[2][4], rows[2][5]),
    )


def read_profile(data: bytes) -> MatrixProfile:
    # ICC.1:2010 §§7.3, 10.16, 10.29, Annex F.3; columns, not rows.
    # https://www.color.org/specification/ICC1v43_2010-12.pdf
    # Deliberately bounded to this test's v4.3 display RGB/XYZ power profiles.
    # Other tags may change transform precedence/adaptation: reject, never ignore.
    if (
        len(data) < 132
        or int.from_bytes(data[:4], "big") != len(data)
        or data[8:12] != b"\x04\x30\0\0"
        or data[12:24] != b"mntrRGB XYZ "
        or data[36:40] != b"acsp"
    ):
        raise ValueError("unsupported or truncated profile header")
    count = int.from_bytes(data[128:132], "big")
    end = 132 + 12 * count
    if end > len(data):
        raise ValueError("truncated tag directory")
    tags: dict[bytes, bytes] = {}
    ranges: list[tuple[int, int]] = []
    allowed = {b"wtpt", b"rXYZ", b"gXYZ", b"bXYZ", b"rTRC", b"gTRC", b"bTRC", b"desc", b"cprt"}
    for pos in range(132, end, 12):
        name = data[pos : pos + 4]
        start, size = struct.unpack(">II", data[pos + 4 : pos + 12])
        stop = start + size
        if (
            name not in allowed
            or name in tags
            or start % 4
            or start < end
            or size < 8
            or stop > len(data)
        ):
            raise ValueError("unsupported or invalid tag directory")
        for left, right in ranges:
            if start < right and stop > left and (start, stop) != (left, right):
                raise ValueError("partially overlapping profile tags")
        tags[name] = data[start:stop]
        ranges.append((start, stop))

    def xyz(name: bytes) -> Vector:
        value = tags.get(name, b"")
        if len(value) != 20 or value[:8] != b"XYZ \0\0\0\0":
            raise ValueError("missing or unsupported XYZ column/white")
        values = tuple(
            Fraction(int.from_bytes(value[p : p + 4], "big", signed=True), 65536)
            for p in (8, 12, 16)
        )
        if any(v < 0 for v in values):
            raise ValueError("negative XYZ")
        return values[0], values[1], values[2]

    def power(name: bytes) -> int:
        value = tags.get(name, b"")
        if len(value) != 16 or value[:12] != b"para\0\0\0\0\0\0\0\0":
            raise ValueError("unsupported curve type/function/reserved bytes")
        exponent = int.from_bytes(value[12:16], "big", signed=True)
        if exponent not in (65536, 131072):
            raise ValueError("unsupported power curve")
        return exponent // 65536

    columns = [xyz(name) for name in (b"rXYZ", b"gXYZ", b"bXYZ")]
    matrix = (
        tuple(columns[j][0] for j in range(3)),
        tuple(columns[j][1] for j in range(3)),
        tuple(columns[j][2] for j in range(3)),
    )
    typed_matrix: Matrix = (
        (matrix[0][0], matrix[0][1], matrix[0][2]),
        (matrix[1][0], matrix[1][1], matrix[1][2]),
        (matrix[2][0], matrix[2][1], matrix[2][2]),
    )
    white = xyz(b"wtpt")
    if struct.unpack(">iii", data[68:80]) != (63190, 65536, 54061) or tuple(
        int(v * 65536) for v in white
    ) != (63190, 65536, 54061):
        raise ValueError("unsupported media/PCS white adaptation")
    inverse(typed_matrix)
    return MatrixProfile(typed_matrix, (power(b"rTRC"), power(b"gTRC"), power(b"bTRC")), white)


def to_linear(source: MatrixProfile, target: MatrixProfile, rgb: tuple[int, int, int]) -> Vector:
    # ICC Annex F.3: M_target^-1 M_source TRC_source(rgb).
    # No clipping, quantization, CMM precision or general device-colour claim.
    if source.white != target.white:
        raise ValueError("unsupported different media white")
    if target.powers != (1, 1, 1):
        raise ValueError("target must be linear")
    if any(v < 0 or v > 255 for v in rgb):
        raise ValueError("invalid 8-bit sample")
    linear = [Fraction(v, 255) ** p for v, p in zip(rgb, source.powers, strict=True)]
    pcs = [
        sum((v * c for v, c in zip(row, linear, strict=True)), Fraction()) for row in source.matrix
    ]
    result = [
        sum((v * c for v, c in zip(row, pcs, strict=True)), Fraction())
        for row in inverse(target.matrix)
    ]
    return result[0], result[1], result[2]
