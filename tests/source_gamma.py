"""Exact rational binary32 truth for the declared gamma-2 finite input domain."""

import hashlib
import re
import struct
from fractions import Fraction
from functools import lru_cache
from typing import cast

from target_observation import Event

BOUND = Fraction(3, 2**25) + Fraction(1, 2**50)


def value32(bits: int) -> Fraction:
    """Decode nonnegative finite binary32 using integer arithmetic only."""
    if not 0 <= bits < 0x7F800000:
        raise ValueError("Unsupported binary32 bits")
    exponent, mantissa = bits >> 23, bits & 0x7FFFFF
    if exponent:
        mantissa += 1 << 23
    shift = exponent - 150 if exponent else -149
    return Fraction(mantissa * 2**shift) if shift >= 0 else Fraction(mantissa, 2**-shift)


def rounded32(value: Fraction) -> int:
    """Round a nonnegative rational to nearest-even binary32 without host floats."""
    if value < 0 or value > 2:
        raise ValueError("Unsupported binary32 rounding domain")
    if value == 0:
        return 0
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    power = Fraction(2**exponent) if exponent >= 0 else Fraction(1, 2**-exponent)
    if value < power:
        exponent -= 1
    shift = 149 if exponent < -126 else 23 - exponent
    scaled = value * 2**shift if shift >= 0 else value / 2**-shift
    whole, remainder = divmod(scaled.numerator, scaled.denominator)
    if 2 * remainder > scaled.denominator or (2 * remainder == scaled.denominator and whole % 2):
        whole += 1
    if exponent < -126:
        return whole
    if whole == 1 << 24:
        whole >>= 1
        exponent += 1
    return ((exponent + 127) << 23) | (whole - (1 << 23))


@lru_cache(maxsize=4)
def truth(denominator: int) -> tuple[tuple[int, int, Fraction], ...]:
    if not 1 <= denominator <= 65535:
        raise ValueError("Unsupported gamma input domain")
    records: list[tuple[int, int, Fraction]] = []
    for code in range(denominator + 1):
        exact = Fraction(code, denominator)
        x = rounded32(exact)
        y = rounded32(value32(x) ** 2)
        error = abs(value32(y) - exact**2)
        if error > BOUND:
            raise ValueError("Independent gamma rounding violates declared bound")
        records.append((x, y, error))
    return tuple(records)


def verify_table(data: bytes, *, denominator: int = 65535) -> dict[str, object]:
    """Check every captured input/output bit against independent rational truth.

    LittleCMS 2.19.1's type-1 parametric curve evaluates pow(R,gamma), with a
    binary32 public result. For gamma=2 this oracle needs no libm/transcendental
    approximation: https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsgamma.c
    The measured claim is exact rounding on these inputs, not all libm inputs.
    """
    expected = truth(denominator)
    if len(data) != len(expected) * 8:
        raise ValueError("Incomplete/extra gamma code table")
    for index, ((x, y), (ex, ey, _)) in enumerate(
        zip(struct.iter_unpack("<II", data), expected, strict=True)
    ):
        if x != ex:
            raise ValueError(f"Wrong gamma input bits at code {index}")
        if y != ey:
            raise ValueError(f"Wrong gamma output bits at code {index}")
    return {
        "codes": len(expected),
        "sha256": hashlib.sha256(data).hexdigest(),
        "maximum_error": str(max(row[2] for row in expected)),
        "declared_bound": str(BOUND),
        "exact_nearest_even_bits": True,
        "complete_cmm_precision_verified": False,
    }


def verify_gamma(
    text: str,
    event: Event,
    pid: int,
    pipeline: dict[str, object],
    tables: dict[int, bytes],
    *,
    denominator: int = 65535,
) -> dict[str, object]:
    """Bind public curve evaluation to the independently checked final pipeline."""
    lines = text.splitlines()
    prefix = (
        f"gamma-v1 {pid} {event.sequence} {event.transform_handle} {event.input_handle} "
        f"{event.input_format} {event.output_format} {event.flags} {event.cmm_version} "
        f"{denominator + 1}"
    )
    if (
        len(lines) != 4
        or lines[0] != prefix
        or pid <= 0
        or event.kind != "transform"
        or event.input_format not in (25, 262169)
        or (event.output_format, event.flags, event.cmm_version, event.intent)
        != (262169, 8448, 2190, 1)
    ):
        raise ValueError("Foreign/incomplete source gamma binding")
    stages = pipeline.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("Missing source gamma pipeline")
    first = cast(list[object], stages)[0]
    expected: list[dict[str, object]] = [
        {"kind": 1, "parameters": ["2"] + ["0"] * 9} for _ in range(3)
    ]
    if not isinstance(first, dict):
        raise ValueError("Invalid source gamma stage")
    stage = cast(dict[str, object], first)
    curves = stage.get("curves")
    if (
        stage.get("kind") != "curves"
        or not isinstance(curves, list)
        or len(cast(list[object], curves)) != 3
    ):
        raise ValueError("Unsupported source gamma stage")
    for channel, curve in enumerate(cast(list[object], curves)):
        if (
            not isinstance(curve, dict)
            or cast(dict[str, object], curve).get("kind") != expected[channel]["kind"]
            or cast(dict[str, object], curve).get("parameters") != expected[channel]["parameters"]
            or re.fullmatch(rf"channel {channel} [1-9][0-9]* 1 0x1p\+1", lines[channel + 1]) is None
        ):
            raise ValueError("Changed/missing source gamma curve/channel")
    if set(tables) != {0, 1, 2}:
        raise ValueError("Missing/extra source gamma channel tables")
    return {
        "channels": {str(c): verify_table(tables[c], denominator=denominator) for c in range(3)},
        "source_curve_evaluation_verified": True,
        "domain": f"all {denominator + 1} normalized word inputs per channel",
        "pipeline_stage_dispatch_verified": False,
        "complete_cmm_precision_verified": False,
    }
