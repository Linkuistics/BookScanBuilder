"""Contest the independent ICC instrument before crediting profile readings."""

import struct
from fractions import Fraction as F

import pytest
from icc_fixtures import profile
from icc_matrix_truth import MatrixProfile, inverse, read_profile, to_linear


def replace_tag(data: bytes, name: bytes, value: bytes) -> bytes:
    result = bytearray(data)
    count = int.from_bytes(data[128:132], "big")
    for pos in range(132, 132 + 12 * count, 12):
        if data[pos : pos + 4] == name:
            start, size = struct.unpack(">II", data[pos + 4 : pos + 12])
            assert len(value) == size
            result[start : start + size] = value
            return bytes(result)
    raise AssertionError("Fixture tag missing")


def test_matrix_columns_and_power_are_read_from_signed_fixed_bytes() -> None:
    got = read_profile(profile(2))
    assert got.matrix == (
        (F(28579, 65536), F(25236, 65536), F(9377, 65536)),
        (F(14582, 65536), F(46981, 65536), F(3973, 65536)),
        (F(913, 65536), F(6364, 65536), F(46804, 65536)),
    )
    assert got.powers == (2, 2, 2)
    assert got.white == (F(63190, 65536), F(1), F(54061, 65536))


def test_nonsymmetric_inverse_uses_rows_and_exact_rationals() -> None:
    assert inverse(((F(1), F(1, 2), F(0)), (F(0), F(1), F(1, 4)), (F(0), F(0), F(1)))) == (
        (F(1), F(-1, 2), F(1, 8)),
        (F(0), F(1), F(-1, 4)),
        (F(0), F(0), F(1)),
    )


def test_zero_pivot_is_exchanged_instead_of_mistaken_for_singular() -> None:
    assert inverse(((F(0), F(1), F(0)), (F(1), F(0), F(0)), (F(0), F(0), F(1)))) == (
        (F(0), F(1), F(0)),
        (F(1), F(0), F(0)),
        (F(0), F(0), F(1)),
    )


def test_singular_matrix_cannot_supply_a_fidelity_oracle() -> None:
    with pytest.raises(ValueError, match="singular"):
        inverse(((F(1), F(0), F(0)), (F(1), F(0), F(0)), (F(0), F(0), F(1))))


def test_coupled_profile_transform_has_independent_literal_truth() -> None:
    # M_target=I, M_source=[[3/4,1/4,0],[1/4,3/4,0],[0,0,1]], gamma=2.
    # Inputs (1/5,3/5,4/5) yield (3/25,7/25,16/25) before any quantization.
    white = (F(1), F(1), F(1))
    source = MatrixProfile(
        ((F(3, 4), F(1, 4), F(0)), (F(1, 4), F(3, 4), F(0)), (F(0), F(0), F(1))),
        (2, 2, 2),
        white,
    )
    target = MatrixProfile(
        ((F(1), F(0), F(0)), (F(0), F(1), F(0)), (F(0), F(0), F(1))), (1, 1, 1), white
    )
    assert to_linear(source, target, (51, 153, 204)) == (F(3, 25), F(7, 25), F(16, 25))


def test_profile_bytes_swapping_columns_changes_colour_truth() -> None:
    assert to_linear(
        read_profile(profile(2, swapped=True)), read_profile(profile()), (51, 153, 204)
    ) == (F(16, 25), F(9, 25), F(1, 25))


@pytest.mark.parametrize("cut", [0, 127, 131, 180, -1])
def test_truncated_profile_never_becomes_a_partial_matrix(cut: int) -> None:
    data = profile()
    with pytest.raises(ValueError):
        read_profile(data[:cut])


@pytest.mark.parametrize(
    ("offset", "value"),
    [
        (0, b"\0\0\0\x80"),
        (36, b"bad!"),
        (8, b"\x02\x30\0\0"),
        (16, b"CMYK"),
        (20, b"Lab "),
        (12, b"prtr"),
        (132, b"A2B0"),
        (144, b"wtpt"),
        (136, b"\0\0\0\x80"),
        (136, b"\0\0\x01\x01"),
        (140, b"\x7f\xff\xff\xff"),
        (128, b"\xff\xff\xff\xff"),
    ],
)
def test_invalid_or_unsupported_header_and_directory_fail_closed(offset: int, value: bytes) -> None:
    data = bytearray(profile())
    data[offset : offset + len(value)] = value
    with pytest.raises(ValueError):
        read_profile(bytes(data))


@pytest.mark.parametrize(
    "value",
    [
        b"XYZ \0\0\0\0" + struct.pack(">ii", 65536, 0),
        b"para\0\0\0\0\0\x03\0\0" + struct.pack(">i", 65536),
        b"para\0\0\0\0\0\0\0\0" + struct.pack(">i", 98304),
        b"para\0\0\0\x01\0\0\0\0" + struct.pack(">i", 65536),
    ],
)
def test_wrong_curve_type_function_reserved_or_noninteger_power_is_unavailable(
    value: bytes,
) -> None:
    with pytest.raises(ValueError):
        read_profile(replace_tag(profile(), b"rTRC", value))


def test_negative_xyz_and_different_media_white_fail_closed() -> None:
    with pytest.raises(ValueError):
        read_profile(
            replace_tag(profile(), b"rXYZ", b"XYZ \0\0\0\0" + struct.pack(">iii", -1, 2, 3))
        )
    source = read_profile(profile())
    other = MatrixProfile(source.matrix, source.powers, (F(1), F(1), F(1)))
    with pytest.raises(ValueError, match="white"):
        to_linear(source, other, (51, 153, 204))


def test_nonlinear_target_and_out_of_range_input_are_not_guessed() -> None:
    with pytest.raises(ValueError, match="linear"):
        to_linear(read_profile(profile()), read_profile(profile(2)), (51, 153, 204))
    with pytest.raises(ValueError, match="sample"):
        to_linear(read_profile(profile()), read_profile(profile()), (-1, 153, 204))


def test_shared_complete_curve_storage_is_valid_but_partial_overlap_is_rejected() -> None:
    data = bytearray(profile())
    # The first tag is white, three columns follow, then three curves.
    data[132 + 5 * 12 + 4 : 132 + 5 * 12 + 12] = data[132 + 4 * 12 + 4 : 132 + 4 * 12 + 12]
    assert read_profile(bytes(data)).powers == (1, 1, 1)
    start = int.from_bytes(data[132 + 4 * 12 + 4 : 132 + 4 * 12 + 8], "big")
    data[132 + 5 * 12 + 4 : 132 + 5 * 12 + 8] = (start + 4).to_bytes(4, "big")
    with pytest.raises(ValueError, match="overlapping"):
        read_profile(bytes(data))


def test_non_d50_pcs_white_is_not_silently_treated_as_an_icc_pcs() -> None:
    data = bytearray(profile())
    data[68:80] = struct.pack(">iii", 65536, 65536, 65536)
    data = bytearray(replace_tag(bytes(data), b"wtpt", b"XYZ \0\0\0\0" + bytes(data[68:80])))
    with pytest.raises(ValueError, match="white"):
        read_profile(bytes(data))
