"""Independent final-byte truth and explicit composition-domain counterexamples."""

import importlib
import struct
from fractions import Fraction
from types import ModuleType

import pytest

IDENTITY = ["1", "0", "0", "0", "1", "0", "0", "0", "1"]
ZERO = ["0"] * 9


def module() -> ModuleType:
    return importlib.import_module("composed_envelope")


def vectors() -> bytes:
    data = bytearray()
    for index in range(256):
        codes = (index, 255 - index, index * 73 % 256)
        data.extend(struct.pack("<34I", index, *codes, *(c * 257 for c in codes), *([0] * 27)))
    return bytes(data)


def test_zero_truth_and_negative_clipping_are_exact() -> None:
    assert module().ideal_channels((17, 53, 201), ZERO) == [(Fraction(), Fraction(), "linear")] * 3
    matrix = ["-1", "0", "0", *(["0"] * 6)]
    assert module().ideal_channels((32, 0, 0), matrix)[0] == (Fraction(), Fraction(), "linear")


def test_white_truth_and_above_white_clipping_do_not_come_from_observed_pixels() -> None:
    channels = module().ideal_channels((255, 255, 255), IDENTITY)
    for low, high, branch in channels:
        assert branch == "power"
        assert abs(low - 1) < Fraction(1, 2**48)
        assert abs(high - 1) < Fraction(1, 2**48)
    matrix = ["3/2", "0", "0", *(["0"] * 6)]
    assert module().ideal_channels((255, 0, 0), matrix)[0] == (Fraction(1), Fraction(1), "power")


def test_nonidentity_matrix_row_order_is_observable_in_ideal_channels() -> None:
    matrix = ["0", "1", "0", "0", "0", "1", "1", "0", "0"]
    red, green, blue = module().ideal_channels((255, 0, 128), matrix)
    assert red == (Fraction(), Fraction(), "linear")
    assert Fraction(1, 2) < green[0] <= green[1] < Fraction(3, 5)
    assert abs(blue[0] - 1) < Fraction(1, 2**48)


def test_propagation_and_quantization_ceiling_is_derived_without_native_samples() -> None:
    # Includes normalization before gamma, source output rounding, row L1=2,
    # matrix rounding, slope 13, finite target accuracy and both quantizers.
    expected = (
        13
        * (2 * (Fraction(3, 2**25) + Fraction(1, 2**50)) + Fraction(1, 2**24) + Fraction(1, 2**48))
        + Fraction(1, 2**24)
        + Fraction(1, 2**44)
        + Fraction(129, 65535)
    )
    assert module().BYTE_BOUND == 255 * expected
    assert Fraction(1, 2) < module().BYTE_BOUND < Fraction(63, 125)
    assert module().verify_slope() is True


@pytest.mark.parametrize(
    "codes,matrix",
    [
        ((-1, 0, 0), IDENTITY),
        ((256, 0, 0), IDENTITY),
        ((0, 0), IDENTITY),
        ((0, 0, 0), ["0"] * 8),
        ((0, 0, 0), ["0"] * 10),
        ((0, 0, 0), ["nan", *(["0"] * 8)]),
        ((0, 0, 0), ["3", *(["0"] * 8)]),
        ((255, 0, 0), ["2", *(["0"] * 8)]),
        ((255, 0, 0), ["-1/8", *(["0"] * 8)]),
    ],
)
def test_incomplete_or_unadmitted_composition_domain_is_rejected(
    codes: tuple[int, ...], matrix: list[str]
) -> None:
    with pytest.raises(ValueError):
        module().ideal_channels(codes, matrix)


def test_propagated_interval_near_curve_seam_is_rejected_even_outside_old_seam_margin() -> None:
    # Core input 0.00313081 lies above the previous 2^-40 seam exclusion,
    # but source+matrix uncertainty crosses the seam and cannot use a slope.
    with pytest.raises(ValueError, match="branch"):
        module().ideal_channels((255, 0, 0), ["313081/100000000", *(["0"] * 8)])


def test_zero_matrix_table_has_all_source_identities_and_narrow_claim() -> None:
    result = module().verify_composed(vectors(), ZERO)
    assert result["values"] == 768
    assert len(result["records"]) == 768
    assert result["maximum_byte_error_upper_bound"] == "0"
    assert result["controlled_composed_byte_envelope_verified"] is True
    assert result["renderer_pixel_traversal_observed"] is False
    assert result["arbitrary_icc_verified"] is False
    assert result["page_composition_fidelity_verified"] is False


@pytest.mark.parametrize("change", ["missing", "extra", "order", "code", "word", "byte", "range"])
def test_wrong_final_byte_or_input_association_cannot_be_credited(change: str) -> None:
    data = bytearray(vectors())
    if change == "missing":
        del data[-136:]
    elif change == "extra":
        data.extend(data[:136])
    else:
        column, replacement = {
            "order": (0, 18),
            "code": (1, 19),
            "word": (4, 17),
            "byte": (28, 2),
            "range": (28, 256),
        }[change]
        struct.pack_into("<I", data, 17 * 136 + column * 4, replacement)
    with pytest.raises(ValueError):
        module().verify_composed(bytes(data), ZERO)


def test_even_a_one_byte_error_is_rejected_for_exact_black_truth() -> None:
    data = bytearray(vectors())
    struct.pack_into("<I", data, 17 * 136 + 28 * 4, 1)
    with pytest.raises(ValueError, match="byte"):
        module().verify_composed(bytes(data), ZERO)
