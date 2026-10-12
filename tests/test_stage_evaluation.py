"""Reject wrong arithmetic and foreign native dispatch before crediting stages."""

import importlib
import struct
from fractions import Fraction
from types import ModuleType

import pytest


def module() -> ModuleType:
    return importlib.import_module("stage_evaluation")


def transcript() -> bytes:
    # Independent literal half-grid inputs/squares and identity-matrix outputs.
    return b"".join(
        struct.pack("<9I", *row)
        for row in [
            (0, 0x3F800000, 0, 0, 0x3F800000, 0, 0, 0x3F800000, 0),
            (0x3F000000,) * 3 + (0x3E800000,) * 6,
            (0x3F800000, 0, 0x3F800000) * 3,
        ]
    )


IDENTITY = ["1", "0", "0", "0", "1", "0", "0", "0", "1"]


def test_actual_stages_match_independent_square_and_dot_truth() -> None:
    result = module().verify_stages(transcript(), IDENTITY, denominator=2)
    assert result["vectors"] == 3
    assert result["source_stage_correctly_rounded"] is True
    assert result["matrix_maximum_error"] == "0"
    assert Fraction(result["matrix_arithmetic_bound"]) == Fraction(1, 2**24) + Fraction(1, 2**48)
    assert result["complete_cmm_precision_verified"] is False


def test_nonidentity_matrix_uses_row_major_coefficients() -> None:
    rows = list(struct.iter_unpack("<9I", transcript()))
    data = b"".join(struct.pack("<9I", *r[:6], r[4], r[3], r[5]) for r in rows)
    result = module().verify_stages(
        data, ["0", "1", "0", "1", "0", "0", "0", "0", "1"], denominator=2
    )
    assert result["matrix_maximum_error"] == "0"


@pytest.mark.parametrize(
    "change", ["input", "square", "matrix", "nan", "missing", "extra", "order"]
)
def test_wrong_bits_domain_and_inventory_are_rejected(change: str) -> None:
    data = bytearray(transcript())
    if change == "input":
        data[36] ^= 1
    elif change == "square":
        data[48] ^= 1
    elif change == "matrix":
        data[24:28] = struct.pack("<I", 0x3F000000)
    elif change == "nan":
        data[24:28] = struct.pack("<I", 0x7FC00000)
    elif change == "missing":
        del data[-36:]
    elif change == "extra":
        data.extend(data[:36])
    else:
        data = data[36:] + data[:36]
    with pytest.raises(ValueError):
        module().verify_stages(bytes(data), IDENTITY, denominator=2)


@pytest.mark.parametrize("matrix", [IDENTITY[:-1], ["3"] + IDENTITY[1:], ["NaN"] + IDENTITY[1:]])
def test_unbounded_or_malformed_matrix_is_rejected(matrix: list[str]) -> None:
    with pytest.raises(ValueError):
        module().verify_stages(transcript(), matrix, denominator=2)


@pytest.mark.parametrize("denominator", [0, -1, 65536])
def test_outside_declared_domain_is_rejected(denominator: int) -> None:
    with pytest.raises(ValueError):
        module().verify_stages(b"", IDENTITY, denominator=denominator)


def test_signed_matrix_outputs_are_decoded_exactly() -> None:
    rows = list(struct.iter_unpack("<9I", transcript()))
    data = b"".join(struct.pack("<9I", *r[:6], r[3] | 0x80000000, r[4], r[5]) for r in rows)
    result = module().verify_stages(data, ["-1"] + IDENTITY[1:], denominator=2)
    assert result["matrix_maximum_error"] == "0"


def test_absolute_matrix_envelope_accepts_boundary_and_rejects_just_outside() -> None:
    boundary = Fraction(1, 2**24) + Fraction(1, 2**48)
    matrix = IDENTITY.copy()
    matrix[4] = str(1 + boundary)
    assert module().verify_stages(transcript(), matrix, denominator=2)[
        "matrix_maximum_error"
    ] == str(boundary)
    matrix[4] = str(1 + boundary + Fraction(1, 2**60))
    with pytest.raises(ValueError, match="matrix-stage"):
        module().verify_stages(transcript(), matrix, denominator=2)


def test_wrong_dispatch_abi_cannot_use_arithmetic_as_identity() -> None:
    with pytest.raises(ValueError, match="ABI"):
        module().verify_dispatch_abi("_cmsStageData:\n0000000000000010 ldr x0, [x0, #0x38]\n")


def binding() -> str:
    return (
        "stage-dispatch-v1 42 7 101 555 3\n"
        "stage 0 111 1668707188 3 3 121704 65536 333\n/native/little-cms2.dylib\n"
        "stage 1 222 1835103334 3 3 122624 65536 444\n/native/little-cms2.dylib\n"
        "abi 24 48 56 16 20 8 fpcr 0\n"
    )


def bind(text: str) -> dict[str, object]:
    from target_observation import Event

    event = Event(7, "transform", 88, 99, 101, 262169, 262169, 1, 8448, 2190)
    return module().verify_binding(
        text,
        event,
        42,
        555,
        {"_EvaluateCurves": 56168, "_EvaluateMatrix": 57088},
        "/native/little-cms2.dylib",
        denominator=2,
    )


def test_dispatch_binding_requires_actual_native_symbol_offsets() -> None:
    assert bind(binding())["source_stage_dispatch_bound"] is True


@pytest.mark.parametrize(
    "old,new",
    [
        ("42 7", "43 7"),
        ("7 101", "7 102"),
        ("101 555", "101 556"),
        ("555 3", "555 4"),
        ("stage 0", "stage 1"),
        ("3 3 121704", "4 3 121704"),
        ("121704", "121705"),
        ("122624", "122625"),
        ("65536 333", "65537 333"),
        ("1668707188", "1835103334"),
        ("24 48", "32 48"),
        ("fpcr 0", "fpcr 16777216"),
        ("/native/little-cms2.dylib", "/foreign/little-cms2.dylib"),
        ("stage 1 222", "stage 1 111"),
    ],
)
def test_foreign_wrong_or_incomplete_dispatch_cannot_be_credited(old: str, new: str) -> None:
    with pytest.raises(ValueError, match="dispatch"):
        bind(binding().replace(old, new))
