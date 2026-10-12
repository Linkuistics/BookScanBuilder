"""Catch profile/handle misbinding and lost binary precision in the native reader."""

from fractions import Fraction

import pytest


def record() -> str:
    return (
        "memory-v1 42 7 99 2190\n"
        "xyz 0x1p+0 0x0p+0 0x0p+0 0x0p+0 0x1p+0 0x0p+0 "
        "0x0p+0 0x0p+0 0x1p+0 0x1p+0 0x1p+0 0x1p+0\n"
        + "".join(
            f"curve {channel} 1 -0x1p+1 0x1p+1 0x1.0000000000001p+0 "
            + "0x0p+0 " * 8
            + "0x0p+0\n"
            + f"table {channel} 3 0 32768 65535\n"
            for channel in range(3)
        )
    )


def test_binary_precision_and_complete_table_are_retained() -> None:
    from profile_memory import parse_memory

    value = parse_memory(record(), 42, 7, 99)
    assert value is not None
    assert value.matrix == ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    assert value.white == (1, 1, 1)
    assert value.curves[0].parameters[0] == Fraction(4503599627370497, 4503599627370496)
    assert value.curves[0].domain == (-2, 2)
    assert value.curves[0].table == (0, 32768, 65535)


@pytest.mark.parametrize(
    "old,new",
    [
        ("memory-v1", "memory-v2"),
        ("42 7 99", "43 7 99"),
        ("42 7 99", "42 8 99"),
        ("42 7 99", "42 7 100"),
        ("2190", "2180"),
        ("xyz 0x1p+0", "xyz nan"),
        ("xyz 0x1p+0", "xyz 1"),
        ("xyz 0x1p+0", "xyz 0x1p+2000"),
        ("curve 0 1", "curve 0 0"),
        ("curve 1 1", "curve 0 1"),
        ("-0x1p+1 0x1p+1", "0x1p+1 -0x1p+1"),
        ("table 0 3", "table 0 4"),
        ("table 0 3", "table 1 3"),
        ("32768", "65536"),
        ("32768", "-1"),
    ],
)
def test_rejects_malformed_or_foreign_capture(old: str, new: str) -> None:
    from profile_memory import parse_memory

    with pytest.raises(ValueError):
        parse_memory(record().replace(old, new, 1), 42, 7, 99)


def test_rejects_incomplete_capture() -> None:
    from profile_memory import parse_memory

    with pytest.raises(ValueError):
        parse_memory("\n".join(record().splitlines()[:-1]) + "\n", 42, 7, 99)


def test_unsupported_profile_keeps_named_unavailability() -> None:
    from profile_memory import parse_memory

    assert (
        parse_memory("memory-v1 42 7 99 2190\nunavailable unsupported-profile\n", 42, 7, 99) is None
    )


def test_rejects_extra_unavailable_payload() -> None:
    from profile_memory import parse_memory

    with pytest.raises(ValueError):
        parse_memory("memory-v1 42 7 99 2190\nunavailable unsupported-profile\nextra\n", 42, 7, 99)


@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong-handle", "unavailable-rgb"])
def test_binding_requires_every_actual_handle(mutation: str) -> None:
    from profile_memory import bind_memory
    from target_observation import Event

    events = [Event(7, "transform", 88, 99, 101, 262169, 262169, 1, 8448, 2190)]
    texts = {(7, 88): record().replace("7 99", "7 88"), (7, 99): record()}
    if mutation == "missing":
        del texts[(7, 88)]
    elif mutation == "extra":
        texts[(8, 99)] = record().replace("7 99", "8 99")
    elif mutation == "wrong-handle":
        texts[(7, 88)] = record()
    else:
        texts[(7, 88)] = "memory-v1 42 7 88 2190\nunavailable unsupported-profile\n"
    with pytest.raises(ValueError):
        bind_memory(texts, events, 42)


@pytest.mark.parametrize("mutation", ["changed-target", "missing-creation"])
def test_rgb_target_memory_matches_its_actual_earlier_creation(mutation: str) -> None:
    from profile_memory import bind_memory
    from target_observation import Event

    events = [
        Event(6, "srgb", 0, 99, 0, 0, 0, 0, 0, 2190),
        Event(7, "transform", 88, 99, 101, 262169, 262169, 1, 8448, 2190),
    ]
    texts = {
        (6, 99): record().replace("7 99", "6 99"),
        (7, 88): record().replace("7 99", "7 88"),
        (7, 99): record(),
    }
    if mutation == "changed-target":
        texts[(7, 99)] = record().replace("xyz 0x1p+0", "xyz 0x1.1p+0")
    else:
        events.pop(0)
        del texts[(6, 99)]
    with pytest.raises(ValueError):
        bind_memory(texts, events, 42)
