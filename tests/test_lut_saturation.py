"""Independent literal expectations for finite native word saturation."""

import importlib
import struct
from fractions import Fraction
from types import ModuleType

import pytest


def module() -> ModuleType:
    return importlib.import_module("lut_saturation")


@pytest.mark.parametrize(
    "bits,expected",
    [
        (0, 0),
        (0x80000000, 0),
        (1, 0),
        (0x80000001, 0),
        (0xBF800000, 0),
        (0xC0000000, 0),
        (0x3EFFFFFF, 32767),
        (0x3700007F, 1),
        (0x3F000000, 32768),
        (0x3F000001, 32768),
        (0x3F7FFFFF, 65535),
        (0x3F800000, 65535),
        (0x40000000, 65535),
    ],
)
def test_zero_subnormal_half_and_clamps_have_independent_word_truth(
    bits: int, expected: int
) -> None:
    assert module().native_word(bits) == expected


@pytest.mark.parametrize("bits", [-1, 2**32, 0x7F800000, 0xFF800000, 0x7FC00000, 0x40000001])
def test_unsupported_bits_and_domain_never_gain_arithmetic_claim(bits: int) -> None:
    with pytest.raises(ValueError, match="domain"):
        module().native_word(bits)


@pytest.mark.parametrize(
    "value,expected",
    [
        (Fraction(1) + Fraction(1, 2**53), Fraction(1)),
        (Fraction(1) + Fraction(3, 2**53), Fraction(1) + Fraction(1, 2**51)),
        (Fraction(-1) - Fraction(1, 2**53), Fraction(-1)),
        (Fraction(1, 2**149), Fraction(1, 2**149)),
    ],
)
def test_binary64_operations_use_integer_nearest_even_truth(
    value: Fraction, expected: Fraction
) -> None:
    assert module().round64(value) == expected


def vectors() -> bytes:
    rows: list[bytes] = []
    for index in range(256):
        row = [0] * 34
        row[0] = index
        row[22:25] = [0, 0x3F000000, 0x3F800000]
        row[25:28] = [0, 32768, 65535]
        rows.append(struct.pack("<34I", *row))
    return b"".join(rows)


def test_every_captured_word_is_checked_without_promoting_target_precision() -> None:
    result = module().verify_words(vectors())
    assert result["words"] == 768
    assert result["saturation_arithmetic_verified"] is True
    assert result["target_precision_verified"] is False
    assert result["complete_cmm_precision_verified"] is False


def test_wrong_word_with_identical_formatted_byte_is_rejected() -> None:
    data = bytearray(vectors())
    struct.pack_into("<I", data, 17 * 136 + 26 * 4, 32769)
    assert (32769 + 128) // 257 == (32768 + 128) // 257
    with pytest.raises(ValueError, match="word.*17.*1"):
        module().verify_words(bytes(data))


@pytest.mark.parametrize("change", ["missing", "extra", "word", "order", "float"])
def test_incomplete_order_and_domain_controls_fail(change: str) -> None:
    data = bytearray(vectors())
    if change == "missing":
        del data[-136:]
    elif change == "extra":
        data.extend(data[:136])
    else:
        column, value = {"word": (25, 65536), "order": (0, 1), "float": (22, 0x7FC00000)}[change]
        struct.pack_into("<I", data, column * 4, value)
    with pytest.raises(ValueError):
        module().verify_words(bytes(data))


def native_fixture() -> dict[str, str]:
    import json
    from pathlib import Path

    return json.loads((Path(__file__).parent / "fixtures/lut-saturation-native.json").read_text())


def test_saturation_instruction_and_literal_pool_identity_are_bound() -> None:
    data = native_fixture()
    assert (
        module().verify_native(data["disassembly"], data["constants"])["function_offset"] == 0xF7E8
    )


@pytest.mark.parametrize(
    "surface,old,new",
    [
        ("disassembly", "fmul", "fadd"),
        ("disassembly", "#0.50000000", "#0.25000000"),
        ("disassembly", "#16", "#15"),
        ("constants", "40efffe0", "40efffc0"),
        ("constants", "c0dfffc0", "c0dfffa0"),
        ("constants", "0000000000033880", "0000000000033888"),
    ],
)
def test_changed_instructions_and_constants_never_credit_arithmetic(
    surface: str, old: str, new: str
) -> None:
    data = native_fixture()
    assert old in data[surface]
    data[surface] = data[surface].replace(old, new)
    with pytest.raises(ValueError, match="native"):
        module().verify_native(data["disassembly"], data["constants"])
