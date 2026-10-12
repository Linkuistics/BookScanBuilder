"""Exact rounding truth must reject wrong native bits, not fit their error."""

import importlib
import struct
from fractions import Fraction
from types import ModuleType

import pytest


def module() -> ModuleType:
    return importlib.import_module("source_gamma")


@pytest.mark.parametrize(
    ("value", "bits"),
    [
        (Fraction(0), 0),
        (Fraction(1), 0x3F800000),
        (Fraction(1, 2), 0x3F000000),
        (Fraction(1, 4), 0x3E800000),
        (Fraction(1, 2**149), 1),
        (Fraction(1, 2**150), 0),
        (Fraction(3, 2**150), 2),
        (Fraction(1) + Fraction(1, 2**24), 0x3F800000),
        (Fraction(1) + Fraction(3, 2**24), 0x3F800002),
        (Fraction(1, 2**126) - Fraction(1, 2**150), 0x00800000),
    ],
)
def test_exact_nearest_even_rounding(value: Fraction, bits: int) -> None:
    assert module().rounded32(value) == bits


@pytest.mark.parametrize("bits", [0x80000000, 0x7F800000, 0x7FC00000])
def test_rejects_signed_or_nonfinite_bits(bits: int) -> None:
    with pytest.raises(ValueError, match="binary32"):
        module().value32(bits)


def test_independent_quarter_grid_has_exact_square_and_bound() -> None:
    # Literal native transcript; a wrong rounding rule changes this verdict.
    data = b"".join(
        struct.pack("<II", x, y)
        for x, y in [
            (0, 0),
            (0x3E800000, 0x3D800000),
            (0x3F000000, 0x3E800000),
            (0x3F400000, 0x3F100000),
            (0x3F800000, 0x3F800000),
        ]
    )
    result = module().verify_table(data, denominator=4)
    assert result["codes"] == 5
    assert result["maximum_error"] == "0"
    assert Fraction(result["declared_bound"]) == Fraction(3, 2**25) + Fraction(1, 2**50)


@pytest.mark.parametrize("changed", ["input", "output", "missing", "extra", "order"])
def test_wrong_code_bits_or_inventory_fail(changed: str) -> None:
    pairs = [(0, 0), (0x3F000000, 0x3E800000), (0x3F800000, 0x3F800000)]
    if changed == "input":
        pairs[1] = (0x3F000001, pairs[1][1])
    elif changed == "output":
        pairs[1] = (pairs[1][0], 0x3E800001)
    elif changed == "missing":
        pairs.pop()
    elif changed == "extra":
        pairs.append(pairs[0])
    else:
        pairs.reverse()
    with pytest.raises(ValueError, match="gamma"):
        module().verify_table(b"".join(struct.pack("<II", *p) for p in pairs), denominator=2)


@pytest.mark.parametrize("denominator", [0, -1, 65536])
def test_invalid_domain_is_rejected(denominator: int) -> None:
    with pytest.raises(ValueError, match="domain"):
        module().verify_table(b"", denominator=denominator)


@pytest.mark.parametrize(
    "old,new",
    [
        ("42 7", "43 7"),
        ("7 101", "7 102"),
        ("101 88", "101 89"),
        ("262169 8448", "262169 8192"),
        ("2190 3", "2180 3"),
        ("channel 0 123", "channel 1 123"),
        ("0x1p+1", "0x1p+0"),
        ("gamma-v1", "gamma-v2"),
        ("channel 2 125 1 0x1p+1\n", ""),
    ],
)
def test_foreign_or_incomplete_gamma_binding_is_rejected(old: str, new: str) -> None:
    from source_gamma import verify_gamma
    from target_observation import Event

    header = (
        "gamma-v1 42 7 101 88 262169 262169 8448 2190 3\n"
        "channel 0 123 1 0x1p+1\nchannel 1 124 1 0x1p+1\nchannel 2 125 1 0x1p+1\n"
    )
    event = Event(7, "transform", 88, 99, 101, 262169, 262169, 1, 8448, 2190)
    curves = [{"kind": 1, "parameters": ["2"] + ["0"] * 9} for _ in range(3)]
    pipeline: dict[str, object] = {"stages": [{"kind": "curves", "curves": curves}]}
    with pytest.raises(ValueError, match="gamma"):
        verify_gamma(header.replace(old, new), event, 42, pipeline, {}, denominator=2)


def test_complete_bound_gamma_binding() -> None:
    from source_gamma import verify_gamma
    from target_observation import Event

    header = (
        "gamma-v1 42 7 101 88 262169 262169 8448 2190 3\n"
        "channel 0 123 1 0x1p+1\nchannel 1 124 1 0x1p+1\nchannel 2 125 1 0x1p+1\n"
    )
    event = Event(7, "transform", 88, 99, 101, 262169, 262169, 1, 8448, 2190)
    curves = [{"kind": 1, "parameters": ["2"] + ["0"] * 9} for _ in range(3)]
    pipeline: dict[str, object] = {"stages": [{"kind": "curves", "curves": curves}]}
    data = b"".join(
        struct.pack("<II", *p) for p in [(0, 0), (0x3F000000, 0x3E800000), (0x3F800000, 0x3F800000)]
    )
    result = verify_gamma(header, event, 42, pipeline, {c: data for c in range(3)}, denominator=2)
    assert result["source_curve_evaluation_verified"] is True
    assert result["complete_cmm_precision_verified"] is False
