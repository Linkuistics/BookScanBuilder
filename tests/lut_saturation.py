"""Independent rational oracle for one bound arm64 LUT's finite word saturation."""

import hashlib
import re
import struct
from fractions import Fraction

from stage_evaluation import signed32

# This test-only binder deliberately supports the exact retained native function,
# not another architecture/build with an assumed instruction or rounding policy.
NATIVE_LUT_SHA256 = "f3c274e473750db5e728802c5a0abd1ef3fc99debfbb54d4e64db9038a052c57"


def round64(value: Fraction) -> Fraction:
    """Round a bounded rational to binary64 nearest-even using integers only."""
    if abs(value) > 2**38:
        raise ValueError("Unsupported binary64 oracle domain")
    if value == 0:
        return value
    sign = -1 if value < 0 else 1
    value = abs(value)
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    power = Fraction(2) ** exponent
    if value < power:
        exponent -= 1
    step = Fraction(2) ** max(-1074, exponent - 52)
    scaled = value / step
    whole, remainder = divmod(scaled.numerator, scaled.denominator)
    if 2 * remainder > scaled.denominator or (2 * remainder == scaled.denominator and whole % 2):
        whole += 1
    return sign * whole * step


def native_word(bits: int) -> int:
    """Compute this native fast-floor word with exact rational operations.

    The source specifies scale/add/clamp/fast floor; the native binder fixes its
    actual operation order and constants. The magic addition rounds to 16
    fractional bits before flooring; it is not ideal mathematical floor.
    https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmslut.c
    https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/lcms2_internal.h
    """
    if not 0 <= bits < 2**32:
        raise ValueError("Unsupported saturation bit domain")
    try:
        value = signed32(bits)
    except ValueError as error:
        raise ValueError("Unsupported saturation float domain") from error
    if not -2 <= value <= 2:
        raise ValueError("Unsupported saturation value domain")
    shifted = round64(round64(value * 65535) + Fraction(1, 2))
    if shifted <= 0:
        return 0
    if shifted >= 65535:
        return 65535
    magic = Fraction(3 * 2**35)
    quantized = round64(round64(shifted - 32767) + magic) - magic
    # On this bounded range the magic addition quantizes to exactly 2^-16;
    # the native arithmetic shift takes mathematical floor of that value.
    return quantized.numerator // quantized.denominator + 32767


def verify_native(disassembly: str, constants: str) -> dict[str, object]:
    """Bind complete actual function instructions and both referenced literals."""
    match = re.search(r"^__LUTeval16:\n(.*?)(?=^_[A-Za-z0-9_.]+:|\Z)", disassembly, re.M | re.S)
    if match is None or hashlib.sha256(match[1].encode()).hexdigest() != NATIVE_LUT_SHA256:
        raise ValueError("Unsupported native saturation instructions")
    memory: dict[int, bytes] = {}
    for line in constants.splitlines():
        row = re.fullmatch(r"([0-9a-f]{16})\s+((?:[0-9a-f]{8}\s+)+)", line)
        if row is not None:
            address = int(row[1], 16)
            for offset, word in enumerate(row[2].split()):
                current = address + 4 * offset
                if current in memory:
                    raise ValueError("Duplicate native saturation literal address")
                memory[current] = struct.pack("<I", int(word, 16))
    for address, expected in [(0x33878, 0x40EFFFE000000000), (0x33880, 0xC0DFFFC000000000)]:
        data = memory.get(address, b"") + memory.get(address + 4, b"")
        if data != struct.pack("<Q", expected):
            raise ValueError("Wrong/missing native saturation literal")
    return {
        "function_offset": 0xF7E8,
        "function_body_sha256": NATIVE_LUT_SHA256,
        "scale": 65535,
        "floor_offset": -32767,
        "magic": 3 * 2**35,
        "test_abi_portable": False,
    }


def verify_words(data: bytes) -> dict[str, object]:
    """Check all words against observed target floats; caller binds full traversal.

    Float-to-word agreement supplies no truth for the preceding target curve.
    """
    if len(data) != 256 * 136:
        raise ValueError("Missing/extra saturation vectors")
    ideal_differences: list[list[int]] = []
    for index, row in enumerate(struct.iter_unpack("<34I", data)):
        if row[0] != index:
            raise ValueError("Wrong saturation vector order")
        for channel, bits in enumerate(row[22:25]):
            expected = native_word(bits)
            if row[25 + channel] != expected:
                raise ValueError(f"Wrong saturation word at vector {index}, channel {channel}")
            shifted = signed32(bits) * 65535 + Fraction(1, 2)
            ideal = max(0, min(65535, shifted.numerator // shifted.denominator))
            if ideal != expected:
                ideal_differences.append([index, channel, ideal, expected])
    return {
        "words": 768,
        "sha256": hashlib.sha256(data).hexdigest(),
        "domain": "finite binary32 [-2,2]; 256 controlled RGB probe triples",
        "saturation_arithmetic_verified": True,
        "ideal_floor_differences": ideal_differences,
        "target_precision_verified": False,
        "renderer_pixel_traversal_observed": False,
        "complete_cmm_precision_verified": False,
    }
