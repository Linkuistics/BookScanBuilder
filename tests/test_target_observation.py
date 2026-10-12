"""Reject missing/foreign/misbound native target evidence, not just plausible profiles."""

import struct
from fractions import Fraction

import pytest
from icc_fixtures import profile


def test_actual_event_binds_process_formats_and_handles() -> None:
    from target_observation import parse_event

    event = parse_event("v1 81 2 transform 12 13 14 262169 262169 0 0 2190\n", 81)
    assert (event.sequence, event.kind, event.input_handle, event.target_handle) == (
        2,
        "transform",
        12,
        13,
    )
    assert (event.transform_handle, event.input_format, event.output_format) == (14, 262169, 262169)
    assert (event.intent, event.flags, event.cmm_version) == (0, 0, 2190)


@pytest.mark.parametrize(
    "line",
    [
        "",
        "v2 81 2 transform 12 13 14 262169 262169 0 0 2190\n",
        "v1 82 2 transform 12 13 14 262169 262169 0 0 2190\n",
        "v1 81 0 transform 12 13 14 262169 262169 0 0 2190\n",
        "v1 81 2 unknown 12 13 14 262169 262169 0 0 2190\n",
        "v1 81 2 transform 0 13 14 262169 262169 0 0 2190\n",
        "v1 81 2 transform 12 0 14 262169 262169 0 0 2190\n",
        "v1 81 2 transform 12 13 0 262169 262169 0 0 2190\n",
        "v1 81 2 transform 12 13 14 262169 262169 0 0 2170\n",
        "v1 81 2 transform 12 13 14 262169 262169 0 0 2190\nextra\n",
    ],
)
def test_wrong_event_is_unavailable(line: str) -> None:
    from target_observation import parse_event

    with pytest.raises(ValueError):
        parse_event(line, 81)


def test_serialized_matrix_coefficients_have_exact_column_order_and_inverse() -> None:
    from target_observation import read_target

    result = read_target(profile(1))
    assert result.matrix[0] == (
        Fraction(28579, 65536),
        Fraction(25236, 65536),
        Fraction(9377, 65536),
    )
    assert result.matrix[2] == (Fraction(913, 65536), Fraction(6364, 65536), Fraction(46804, 65536))
    assert result.curves == ((0, (Fraction(1),)),) * 3
    assert result.inverse[0][0] == Fraction(142450003279872, 45455773212479)


@pytest.mark.parametrize(
    "mutation", ["length", "magic", "duplicate", "overlap", "transform", "curve"]
)
def test_unsupported_target_cannot_supply_matrix_evidence(mutation: str) -> None:
    from target_observation import read_target

    data = bytearray(profile(1))
    if mutation == "length":
        data.pop()
    elif mutation == "magic":
        data[36:40] = b"wrong"
    elif mutation == "duplicate":
        data[144:148] = data[132:136]
    elif mutation == "overlap":
        data[148:152] = (int.from_bytes(data[136:140], "big") + 4).to_bytes(4, "big")
    elif mutation == "transform":
        data[132:136] = b"A2B0"
    else:
        for pos in range(132, 240, 12):
            if bytes(data[pos : pos + 4]) == b"rTRC":
                start = int.from_bytes(data[pos + 4 : pos + 8], "big")
                data[start + 8 : start + 10] = struct.pack(">H", 9)
                break
    with pytest.raises(ValueError):
        read_target(bytes(data))


def test_capture_rejects_unrelated_target_handle() -> None:
    from target_observation import bind_capture

    # The profiles are plausible and identical, but no observed creation owns 14.
    with pytest.raises(ValueError, match="target handle"):
        bind_capture(
            [
                "v1 81 1 srgb 0 13 0 0 0 0 0 2190\n",
                "v1 81 2 transform 12 14 15 262169 262169 1 8448 2190\n",
            ],
            {1: profile(1), 2: profile(1)},
            {2: profile(2)},
            81,
            profile(2),
        )


@pytest.mark.parametrize(
    "lines",
    [
        [],
        ["v1 81 2 srgb 0 13 0 0 0 0 0 2190\n"],
        ["v1 81 1 srgb 0 13 0 0 0 0 0 2190\n"],
    ],
)
def test_missing_sequence_or_input_transform_is_unavailable(lines: list[str]) -> None:
    from target_observation import bind_capture

    with pytest.raises(ValueError):
        bind_capture(lines, {1: profile(1)}, {}, 81, profile(2))


def test_rgb_transform_can_use_second_observed_srgb_object() -> None:
    from target_observation import bind_capture

    events, target = bind_capture(
        [
            "v1 81 1 srgb 0 13 0 0 0 0 0 2190\n",
            "v1 81 2 srgb 0 14 0 0 0 0 0 2190\n",
            "v1 81 3 transform 12 14 15 262169 262169 1 8448 2190\n",
            "v1 81 4 transform 12 14 16 25 262169 1 8448 2190\n",
        ],
        {1: profile(1), 2: profile(1), 3: profile(1), 4: profile(1)},
        {3: profile(2), 4: profile(2)},
        81,
        profile(2),
    )
    assert events[2].target_handle == events[1].target_handle
    assert target.curves == ((0, (Fraction(1),)),) * 3
