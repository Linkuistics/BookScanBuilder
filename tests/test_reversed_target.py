"""Independent root/linear expectations and isolating reversed-curve controls."""

import importlib
import struct
from fractions import Fraction
from types import ModuleType

import pytest


def module() -> ModuleType:
    return importlib.import_module("reversed_target")


@pytest.mark.parametrize("value,degree,root", [(0, 5, 0), (1, 12, 1), (32, 5, 2)])
def test_perfect_integer_roots_are_exact(value: int, degree: int, root: int) -> None:
    assert module().root_interval(Fraction(value), degree) == (Fraction(root), Fraction(root))


def test_fractional_perfect_root_and_irrational_bracket() -> None:
    assert module().root_interval(Fraction(1, 4096), 12) == (Fraction(1, 2), Fraction(1, 2))
    low, high = module().root_interval(Fraction(2), 12)
    assert low**12 < 2 < high**12
    assert high - low == Fraction(1, 2**80)


@pytest.mark.parametrize("value,degree", [(-1, 5), (33, 5), (1, 0), (1, 4), (1, 13)])
def test_unsupported_root_domains_fail(value: int, degree: int) -> None:
    with pytest.raises(ValueError, match="domain"):
        module().root_interval(Fraction(value), degree)


@pytest.mark.parametrize(
    "bits,value",
    [(0, 0), (0x80000000, 0), (0x39800000, Fraction(1, 4096)), (0xBC800000, Fraction(-1, 64))],
)
def test_linear_branch_uses_exact_coefficient_without_clamping(bits: int, value: Fraction) -> None:
    low, high, branch = module().reverse_interval(bits)
    # Exact binary64 c: 0x1.3d0722149b58p-4, not decimal 1/12.92.
    expected = value / Fraction(43571977818987, 562949953421312)
    assert (low, high, branch) == (expected, expected, "linear")


def test_white_and_positive_branch_have_independent_bounded_truth() -> None:
    low, high, branch = module().reverse_interval(0x3F800000)
    assert branch == "power"
    assert abs(low - 1) < Fraction(1, 2**48)
    assert high - low <= Fraction(2, 2**80)
    low, high, branch = module().reverse_interval(0x3F000000)
    assert branch == "power"
    # Inverse sRGB of 1/2 lies between 7/10 and 4/5; the twelfth-power
    # relation supplies a much tighter independent check than this coarse fact.
    assert Fraction(7, 10) < low < high < Fraction(4, 5)
    a = Fraction(266800925792091, 281474976710656)
    b = Fraction(7513114070305283, 144115188075855872)
    assert (a * low + b) ** 12 <= Fraction(1, 32) <= (a * high + b) ** 12


@pytest.mark.parametrize(
    "bits", [-1, 2**32, 0x7F800000, 0xFF800000, 0x7FC00000, 0xBD800001, 0x40000001]
)
def test_nonfinite_and_out_of_range_inputs_fail(bits: int) -> None:
    with pytest.raises(ValueError, match="domain"):
        module().reverse_interval(bits)


def test_threshold_uncertainty_never_selects_a_branch() -> None:
    with pytest.raises(ValueError, match="boundary"):
        module().branch(Fraction(3130807283067683, 10**18))


def vectors() -> bytes:
    result = bytearray()
    for index in range(256):
        row = [0] * 34
        row[0] = index
        result.extend(struct.pack("<34I", *row))
    return bytes(result)


def test_complete_target_table_keeps_its_finite_accuracy_scope() -> None:
    record = module().verify_target(vectors(), module().expected_curves())
    assert record["values"] == 768
    assert record["linear_values"] == 768
    assert record["power_values"] == 0
    assert record["reversed_target_accuracy_verified"] is True
    assert record["correctly_rounded_transcendentals_verified"] is False
    assert record["renderer_pixel_traversal_observed"] is False
    assert record["complete_cmm_precision_verified"] is False


def test_power_accuracy_accounts_for_idealized_exponent() -> None:
    data = bytearray(vectors())
    for index in range(256):
        for column in range(19, 25):
            struct.pack_into("<I", data, index * 136 + column * 4, 0x3F800000)
    record = module().verify_target(bytes(data), module().expected_curves())
    # At white, the ideal root is exactly one; coefficient deviation and the
    # predeclared exponent allowance must both survive in the reported bound.
    deviation = abs(
        Fraction(1)
        - (1 - Fraction(7513114070305283, 144115188075855872))
        / Fraction(266800925792091, 281474976710656)
    )
    assert Fraction(record["maximum_error_upper_bound"]) == deviation + Fraction(1, 2**48)
    assert record["parameter_idealization_bound"] == str(Fraction(1, 2**48))


@pytest.mark.parametrize("change", ["missing", "extra", "order", "float", "output"])
def test_bad_target_table_cannot_receive_precision_claim(change: str) -> None:
    data = bytearray(vectors())
    if change == "missing":
        del data[-136:]
    elif change == "extra":
        data.extend(data[:136])
    else:
        column, value = {"order": (0, 1), "float": (19, 0x7FC00000), "output": (22, 0x3A800000)}[
            change
        ]
        struct.pack_into("<I", data, 17 * 136 + column * 4, value)
    with pytest.raises(ValueError):
        module().verify_target(bytes(data), module().expected_curves())


@pytest.mark.parametrize("change", ["kind", "coefficient", "domain", "missing", "extra"])
def test_foreign_curves_cannot_be_given_srgb_truth(change: str) -> None:
    curves = module().expected_curves()
    if change == "missing":
        curves.pop()
    elif change == "extra":
        curves.append(curves[0])
    elif change == "kind":
        curves[0]["kind"] = 4
    elif change == "coefficient":
        curves[0]["parameters"][3] = "1"
    else:
        curves[0]["domain"][0] = "0"
    with pytest.raises(ValueError, match="curve"):
        module().verify_target(vectors(), curves)
