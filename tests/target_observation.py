"""Bounded serialized target metadata and actual child event validation; no CMM oracle."""

import re
import struct
from dataclasses import dataclass
from fractions import Fraction

from icc_matrix_truth import Matrix, Vector, inverse


@dataclass(frozen=True)
class Event:
    sequence: int
    kind: str
    input_handle: int
    target_handle: int
    transform_handle: int
    input_format: int
    output_format: int
    intent: int
    flags: int
    cmm_version: int


def parse_event(line: str, pid: int) -> Event:
    match = re.fullmatch(r"v1 ([0-9]+) ([0-9]+) (srgb|transform)((?: [0-9]+){8})\n", line)
    if match is None or int(match[1]) != pid or pid <= 0 or int(match[2]) <= 0:
        raise ValueError("Missing/malformed/foreign-PID target event")
    values = [int(v) for v in match[4].split()]
    if values[-1] != 2190 or not values[1]:
        raise ValueError("Missing target or unsupported observed CMM version")
    if match[3] == "srgb":
        if any(values[i] for i in range(7) if i != 1):
            raise ValueError("Malformed sRGB creation event")
    elif not all(values[i] for i in (0, 2, 3, 4)):
        raise ValueError("Failed/missing transform evidence")
    return Event(int(match[2]), match[3], *values)


@dataclass(frozen=True)
class Target:
    matrix: Matrix
    inverse: Matrix
    curves: tuple[tuple[int, tuple[Fraction, ...]], ...]
    white: Vector
    tags: tuple[tuple[str, str], ...]


def bind_capture(
    lines: list[str],
    targets: dict[int, bytes],
    inputs: dict[int, bytes],
    pid: int,
    source: bytes,
) -> tuple[list[Event], Target]:
    events = [parse_event(line, pid) for line in lines]
    if not events or [e.sequence for e in events] != list(range(1, len(events) + 1)):
        raise ValueError("Missing/incomplete target event sequence")
    if events[0].kind != "srgb":
        raise ValueError("Missing initial default target creation")
    if set(targets) != {e.sequence for e in events} or set(inputs) != {
        e.sequence for e in events if e.kind == "transform"
    }:
        raise ValueError("Missing/extra captured profile subjects")
    created = events[0]
    target = read_target(targets[created.sequence])
    source_tags = read_target(source).tags
    selected = [e for e in events if e.kind == "transform" and e.input_format in (262169, 25)]
    if not selected:
        raise ValueError("Missing actual RGB input transform")
    for event in selected:
        creation = next(
            (
                e
                for e in events
                if e.kind == "srgb"
                and e.target_handle == event.target_handle
                and e.sequence < event.sequence
            ),
            None,
        )
        if creation is None:
            raise ValueError("Unrelated target handle")
        if read_target(targets[creation.sequence]) != target:
            raise ValueError("Changed sRGB creation target")
        if read_target(targets[event.sequence]) != target:
            raise ValueError("Changed serialized target")
        if read_target(inputs[event.sequence]).tags != source_tags:
            raise ValueError("Unrelated captured input profile")
        if (event.output_format, event.intent, event.flags) != (262169, 1, 8448):
            raise ValueError("Unexpected actual RGB format/intent/flags")
    return events, target


def read_target(data: bytes) -> Target:
    """Read only v4 RGB/XYZ matrix/parametric tags; serialized precision only.

    Known chad/chrm/text tags are retained, never interpreted as arbitrary
    transformation truth. The current target is D50-adapted; this supplies no
    general intent/adaptation or optimized CMM pipeline interpretation.
    """
    # ICC.1:2010 §§7.3, 10.16, 10.29 and Annex F.3.
    # https://www.color.org/specification/ICC1v43_2010-12.pdf
    if (
        len(data) < 132
        or int.from_bytes(data[:4], "big") != len(data)
        or data[8] != 4
        or data[12:24] != b"mntrRGB XYZ "
        or data[36:40] != b"acsp"
    ):
        raise ValueError("Unsupported serialized target header")
    end = 132 + 12 * int.from_bytes(data[128:132], "big")
    if end > len(data):
        raise ValueError("Truncated target directory")
    allowed = {
        b"wtpt",
        b"rXYZ",
        b"gXYZ",
        b"bXYZ",
        b"rTRC",
        b"gTRC",
        b"bTRC",
        b"chad",
        b"chrm",
        b"desc",
        b"cprt",
    }
    tags: dict[bytes, bytes] = {}
    ranges: list[tuple[int, int]] = []
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
            raise ValueError("Unsupported/invalid target tag")
        if any(
            start < right and stop > left and (start, stop) != (left, right)
            for left, right in ranges
        ):
            raise ValueError("Partially overlapping target tags")
        tags[name] = data[start:stop]
        ranges.append((start, stop))

    def xyz(name: bytes) -> Vector:
        value = tags.get(name, b"")
        if len(value) != 20 or value[:8] != b"XYZ \0\0\0\0":
            raise ValueError("Missing/unsupported target XYZ tag")
        a, b, c = struct.unpack(">iii", value[8:])
        return Fraction(a, 65536), Fraction(b, 65536), Fraction(c, 65536)

    curves: list[tuple[int, tuple[Fraction, ...]]] = []
    for name in (b"rTRC", b"gTRC", b"bTRC"):
        value = tags.get(name, b"")
        if len(value) < 12 or value[:8] != b"para\0\0\0\0" or value[10:12] != b"\0\0":
            raise ValueError("Unsupported target curve")
        function = int.from_bytes(value[8:10], "big")
        count = {0: 1, 1: 3, 2: 4, 3: 5, 4: 7}.get(function)
        if count is None or len(value) != 12 + 4 * count:
            raise ValueError("Unsupported/truncated parametric curve")
        parameters = tuple(Fraction(v, 65536) for v in struct.unpack(">" + "i" * count, value[12:]))
        curves.append((function, parameters))
    r, g, b = [xyz(name) for name in (b"rXYZ", b"gXYZ", b"bXYZ")]
    matrix: Matrix = ((r[0], g[0], b[0]), (r[1], g[1], b[1]), (r[2], g[2], b[2]))
    return Target(
        matrix,
        inverse(matrix),
        tuple(curves),
        xyz(b"wtpt"),
        tuple((name.decode("ascii"), value.hex()) for name, value in sorted(tags.items())),
    )
