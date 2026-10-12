"""Read bound binary profile observations; no CMM evaluation/precision oracle."""

import math
import re
from dataclasses import dataclass
from fractions import Fraction

from icc_matrix_truth import Matrix, Vector
from target_observation import Event


@dataclass(frozen=True)
class Curve:
    kind: int
    domain: tuple[Fraction, Fraction]
    parameters: tuple[Fraction, ...]
    table: tuple[int, ...]


@dataclass(frozen=True)
class Memory:
    matrix: Matrix
    white: Vector
    curves: tuple[Curve, ...]


def binary(value: str) -> Fraction:
    if re.fullmatch(r"-?0x[0-9a-f]+(?:\.[0-9a-f]+)?p[+-][0-9]+", value) is None:
        raise ValueError("Missing binary floating observation")
    try:
        number = float.fromhex(value)
    except (ValueError, OverflowError) as error:
        raise ValueError("Invalid binary floating observation") from error
    if not math.isfinite(number):
        raise ValueError("Nonfinite profile observation")
    return Fraction(number)


def parse_memory(text: str, pid: int, sequence: int, handle: int) -> Memory | None:
    lines = text.splitlines()
    if (
        not lines
        or min(pid, sequence, handle) <= 0
        or lines[0] != f"memory-v1 {pid} {sequence} {handle} 2190"
    ):
        raise ValueError("Missing/malformed/foreign memory identity")
    if lines[1:] == ["unavailable unsupported-profile"]:
        return None
    if len(lines) != 8:
        raise ValueError("Incomplete/extra memory capture")
    xyz = lines[1].split()
    if len(xyz) != 13 or xyz[0] != "xyz":
        raise ValueError("Missing profile XYZ values")
    values = [binary(v) for v in xyz[1:]]
    curves: list[Curve] = []
    for channel in range(3):
        parts = lines[2 + 2 * channel].split()
        if len(parts) != 15 or parts[:2] != ["curve", str(channel)]:
            raise ValueError("Missing/reordered profile curve")
        if parts[2] not in {"1", "2", "3", "4", "5"}:
            raise ValueError("Unsupported memory curve")
        low, high = binary(parts[3]), binary(parts[4])
        if low >= high:
            raise ValueError("Invalid curve domain")
        parameters = tuple(binary(v) for v in parts[5:])
        table = lines[3 + 2 * channel].split()
        if (
            len(table) < 5
            or table[:2] != ["table", str(channel)]
            or any(re.fullmatch(r"[0-9]+", v) is None for v in table[2:])
        ):
            raise ValueError("Missing/malformed estimated curve table")
        count = int(table[2])
        entries = tuple(int(v) for v in table[3:])
        if not 2 <= count <= 65536 or len(entries) != count or max(entries) > 65535:
            raise ValueError("Incomplete/invalid estimated curve table")
        curves.append(Curve(int(parts[2]), (low, high), parameters, entries))
    return Memory(
        (
            (values[0], values[3], values[6]),
            (values[1], values[4], values[7]),
            (values[2], values[5], values[8]),
        ),
        (values[9], values[10], values[11]),
        tuple(curves),
    )


def bind_memory(
    texts: dict[tuple[int, int], str], events: list[Event], pid: int
) -> dict[str, Memory | None]:
    expected = {
        (event.sequence, handle)
        for event in events
        for handle in (event.input_handle, event.target_handle)
        if handle
    }
    if not expected or set(texts) != expected:
        raise ValueError("Missing/extra in-memory profile binding")
    result: dict[str, Memory | None] = {}
    for event in events:
        for role, handle in [("input", event.input_handle), ("target", event.target_handle)]:
            if not handle:
                continue
            memory = parse_memory(texts[(event.sequence, handle)], pid, event.sequence, handle)
            if memory is None and (role == "target" or event.input_format in (262169, 25)):
                raise ValueError("Required RGB memory data unavailable")
            result[f"{event.sequence}-{role}"] = memory
    for event in events:
        if event.input_format not in (262169, 25):
            continue
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
        if (
            creation is None
            or result[f"{creation.sequence}-target"] != result[f"{event.sequence}-target"]
        ):
            raise ValueError("Missing/changed in-memory target creation binding")
    return result
