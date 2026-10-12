"""Independent arithmetic and per-call cache truth for actual RGB8 CMM calls."""

import hashlib
import re
import struct
from fractions import Fraction
from functools import lru_cache

from composed_envelope import BYTE_BOUND, ideal_channels
from lut_saturation import native_word
from reversed_target import ERROR_BOUND, PARAMETER_BOUND, reverse_interval
from source_gamma import truth, value32
from stage_evaluation import MATRIX_BOUND, signed32
from target_observation import Event

NATIVE = {
    "_CachedXFORM": (108824, "b01c0cd4a6c96fe169e06f97104faa520954013e11054c7d89482e2d2cb2dddb"),
    "_Unroll3Bytes": (80344, "b91d74ef380cfc7d3ae4ba50c32ba786f87856ad1b89df7f68c550b33df43d49"),
    "_Pack3Bytes": (87276, "08e21c56ffd3dc83abeb489225f58fd13656640c9ebe51aa4f4cffeb8c6c88d0"),
}


def verify_worker(disassembly: str) -> dict[str, object]:
    """Bind complete installed worker and formatter instructions, including cache copying."""
    for name, (offset, digest) in NATIVE.items():
        match = re.search(rf"^{name}:\n(.*?)(?=^_[A-Za-z0-9_.]+:|\Z)", disassembly, re.M | re.S)
        if (
            match is None
            or int(match[1].split()[0], 16) != offset
            or hashlib.sha256(match[1].encode()).hexdigest() != digest
        ):
            raise ValueError("Unsupported native pixel worker/formatter: " + name)
    return {name: {"offset": offset, "sha256": digest} for name, (offset, digest) in NATIVE.items()}


def verify_header(
    text: str, event: Event, pid: int, call: int, lut: int, module: str, base: int
) -> dict[str, object]:
    """Bind a one-line call's identity, worker, formatters, cache seed and restoration."""
    lines = text.splitlines()
    if len(lines) != 9 or min(pid, call, lut, base) <= 0:
        raise ValueError("Incomplete/foreign pixel call")
    fields = lines[0].split()
    prefix = [
        "pixels-v1",
        str(pid),
        str(event.sequence),
        str(call),
        str(event.transform_handle),
        str(lut),
        str(event.input_format),
        str(event.output_format),
    ]
    if (
        len(fields) != 14
        or fields[:8] != prefix
        or event.kind != "transform"
        or event.input_format not in (25, 262169)
        or (event.output_format, event.intent, event.flags, event.cmm_version)
        != (262169, 1, 8448, 2190)
        or any(re.fullmatch(r"[0-9]+", v) is None for v in fields[8:])
    ):
        raise ValueError("Wrong actual pixel identity/formats")
    width, count, line_in, line_out, plane_in, plane_out = map(int, fields[8:])
    if count != 1 or width <= 0 or (line_in, line_out, plane_in, plane_out) != (0, 0, width, width):
        raise ValueError("Unsupported actual pixel stride/domain")
    for index, (role, name) in enumerate(zip(["worker", "input", "output"], NATIVE, strict=True)):
        offset = NATIVE[name][0]
        if (
            lines[1 + 2 * index] != f"{role} {base + offset} {base}"
            or lines[2 + 2 * index] != module
        ):
            raise ValueError("Wrong actual pixel native address/module")
    if lines[7] != "seed" + " 0" * 32 or lines[8] != f"complete {width} restored 1":
        raise ValueError("Wrong pixel seed/completion/restoration")
    return {"pixels": width, "input_format": event.input_format, "call": call}


def verify_image_binding(
    source: bytes,
    inputs: bytes,
    converted: bytes,
    mode: str,
    size: tuple[int, int],
    rgb: bytes,
    *,
    expected_size: tuple[int, int],
) -> bool:
    """Bind the complete constructed sample roster and converted output to its PNG.

    This seam applies only to the declared opaque, grid-aligned image construction;
    a caller must independently establish its physical placement and CMM truth.
    """
    expected_bytes = expected_size[0] * expected_size[1] * 3
    if (
        min(expected_size) <= 0
        or len(source) != expected_bytes
        or inputs != source
        or len(converted) != expected_bytes
        or mode != "RGB"
        or size != expected_size
        or rgb != converted
    ):
        raise ValueError("Wrong complete constructed source/conversion/framebuffer binding")
    return True


@lru_cache(maxsize=4096)
def _miss(row: tuple[int, ...], coefficients: tuple[str, ...]) -> tuple[str, str, str]:
    """Verify arbitrary admitted RGB8 triples through the bound three-stage LUT."""
    codes = row[1:4]
    expected = [truth(255)[code] for code in codes]
    if row[7:10] != tuple(v[0] for v in expected) or row[10:13] != tuple(v[1] for v in expected):
        raise ValueError("Wrong actual pixel source stage")
    if row[10:13] != row[13:16] or row[16:19] != row[19:22]:
        raise ValueError("Broken actual pixel stage linkage")
    matrix_error = Fraction()
    target_error = Fraction()
    matrix = [Fraction(v) for v in coefficients]
    inputs = [value32(v) for v in row[13:16]]
    for channel in range(3):
        exact = sum((matrix[3 * channel + c] * inputs[c] for c in range(3)), Fraction())
        error = abs(signed32(row[16 + channel]) - exact)
        if error > MATRIX_BOUND:
            raise ValueError("Wrong actual pixel matrix stage")
        matrix_error = max(matrix_error, error)
        low, high, selected = reverse_interval(row[19 + channel])
        actual = signed32(row[22 + channel])
        error = max(abs(actual - low), abs(actual - high))
        error += PARAMETER_BOUND if selected == "power" else Fraction()
        if error > ERROR_BOUND:
            raise ValueError("Wrong actual pixel reversed target")
        target_error = max(target_error, error)
        if row[25 + channel] != native_word(row[22 + channel]):
            raise ValueError("Wrong actual pixel saturation word")
    return str(matrix_error), str(target_error), _bytes(codes, row[28:31], coefficients)


@lru_cache(maxsize=4096)
def _bytes(codes: tuple[int, ...], output: tuple[int, ...], coefficients: tuple[str, ...]) -> str:
    maximum = Fraction()
    for actual, (low, high, _) in zip(
        output, ideal_channels(codes, list(coefficients)), strict=True
    ):
        error = max(abs(actual - 255 * low), abs(actual - 255 * high))
        if error > BYTE_BOUND:
            raise ValueError("Wrong actual pixel ideal byte")
        maximum = max(maximum, error)
    return str(maximum)


def verify_pixels(
    data: bytes,
    coefficients: list[str],
    seed_in: tuple[int, int, int],
    seed_out: tuple[int, int, int],
    pixels: int,
) -> dict[str, object]:
    """Require exactly one input/output record per pixel and the observed cache path.

    The fixed seed domain is all-zero RGB, independently yielding zero words.
    Each actual native call resets its local cache; callers separately bind
    native dispatch, complete seed buffers, strides, formats and restoration.
    https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsxform.c
    This checks conversion calls, not their placement in the page framebuffer.
    """
    if pixels <= 0 or len(data) != pixels * 136:
        raise ValueError("Missing/extra actual pixel records")
    if seed_in != (0, 0, 0) or seed_out != (0, 0, 0):
        raise ValueError("Unsupported/wrong pixel cache seed")
    # Also admit the seed's analytic domain before using it as a cache oracle.
    matrix = tuple(coefficients)
    _bytes((0, 0, 0), (0, 0, 0), matrix)
    cache_in, cache_out = seed_in, seed_out
    misses = 0
    output = bytearray()
    maximum_matrix = maximum_target = maximum_byte = Fraction()
    records: list[list[int]] = []
    for index, row in enumerate(struct.iter_unpack("<34I", data)):
        codes, words, result = row[1:4], row[4:7], row[25:28]
        if row[0] != index or any(c > 255 for c in codes):
            raise ValueError("Wrong pixel order/input domain")
        if words != tuple(c * 257 for c in codes):
            raise ValueError("Wrong actual input formatter")
        hit = words == cache_in
        if row[31:34] != (int(not hit), 3 * int(not hit), int(hit)):
            raise ValueError("Wrong actual cache/stage counters")
        if hit:
            if any(row[7:25]) or result != cache_out:
                raise ValueError("Wrong cache reuse/stage observation")
            error_byte = _bytes(codes, row[28:31], matrix)
        else:
            error_matrix, error_target, error_byte = _miss((0, *row[1:]), matrix)
            maximum_matrix = max(maximum_matrix, Fraction(error_matrix))
            maximum_target = max(maximum_target, Fraction(error_target))
            cache_in, cache_out = words, result
            misses += 1
        if any(v > 65535 for v in result) or row[28:31] != tuple((v + 128) // 257 for v in result):
            raise ValueError("Wrong actual output formatter")
        maximum_byte = max(maximum_byte, Fraction(error_byte))
        output.extend(row[28:31])
        records.append([index, int(hit), *codes, *row[28:31]])
    return {
        "pixels": pixels,
        "misses": misses,
        "hits": pixels - misses,
        "stage_calls": 3 * misses,
        "sha256": hashlib.sha256(data).hexdigest(),
        "rgb_sha256": hashlib.sha256(output).hexdigest(),
        "maximum_matrix_error": str(maximum_matrix),
        "maximum_target_error": str(maximum_target),
        "maximum_byte_error": str(maximum_byte),
        "declared_byte_bound": str(BYTE_BOUND),
        "records": records,
        "conversion_arithmetic_and_cache_verified": True,
        "page_framebuffer_mapping_verified": False,
        "arbitrary_icc_verified": False,
    }
