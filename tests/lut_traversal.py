"""Verify ordered native LUT probe dispatch, with bounded source/matrix arithmetic."""

import hashlib
import re
import struct

from stage_evaluation import signed32, verify_dispatch_abi, verify_stages
from target_observation import Event


def verify_abi(disassembly: str) -> dict[str, int]:
    """Check this arm64 binary's pipeline access and actual transform dispatch."""
    offsets = verify_dispatch_abi(disassembly)
    for name, pattern in [
        ("_cmsPipelineEval16", r"ldp\s+x2, x3, \[x2, #0x10\].*br\s+x3"),
        ("_CachedXFORM", r"ldr\s+x8, \[x23, #0x70\].*ldp\s+x2, x9, \[x8, #0x10\].*blr\s+x9"),
    ]:
        match = re.search(rf"^{name}:\n(.*?)(?=^_[A-Za-z0-9_.]+:|\Z)", disassembly, re.M | re.S)
        if match is None or re.search(pattern, match[1], re.S) is None:
            raise ValueError("Native traversal ABI mismatch: " + name)
        address = re.match(r"([0-9a-f]+)\s", match[1])
        if address is None:
            raise ValueError("Native traversal ABI missing offset: " + name)
        offsets[name] = int(address[1], 16)
    return offsets


def verify_transform_dispatch(
    text: str, event: Event, pid: int, offsets: dict[str, int], module: str
) -> int:
    """Bind the actual cached worker; original flags alone cannot identify it."""
    lines = text.splitlines()
    if (
        len(lines) != 2
        or lines[1] != module
        or re.fullmatch(
            rf"module-v1 {pid} {event.sequence} evaluator [1-9][0-9]* [1-9][0-9]*", lines[0]
        )
        is None
    ):
        raise ValueError("Wrong native transform dispatcher identity")
    fields = lines[0].split()
    offset = int(fields[4]) - int(fields[5])
    if offset != offsets.get("_CachedXFORM"):
        raise ValueError("Wrong native transform dispatcher offset")
    return offset


def verify_binding(
    text: str, event: Event, pid: int, lut: int, offsets: dict[str, int], module: str
) -> dict[str, object]:
    """Bind recorded original evaluator addresses and the complete three-stage chain."""
    lines = text.splitlines()
    if (
        len(lines) != 10
        or pid <= 0
        or lut <= 0
        or event.transform_handle <= 0
        or event.kind != "transform"
        or event.input_format not in (25, 262169)
        or (event.output_format, event.intent, event.flags, event.cmm_version)
        != (262169, 1, 8448, 2190)
        or lines[0] != f"traversal-v1 {pid} {event.sequence} {event.transform_handle} {lut} 256"
        or lines[-1] != "calls 256 768 restored 1 abi 16 24"
        or lines[2] != module
    ):
        raise ValueError("Foreign/incomplete traversal binding")
    fields = lines[1].split()
    if (
        len(fields) != 4
        or fields[0] != "lut16"
        or any(re.fullmatch(r"[1-9][0-9]*", v) is None for v in fields[1:])
    ):
        raise ValueError("Wrong LUT evaluator identity")
    evaluator, base, data = map(int, fields[1:])
    if data != lut or evaluator - base != offsets.get("__LUTeval16"):
        raise ValueError("Wrong LUT evaluator offset/data")
    pointers: list[int] = []
    nexts: list[int] = []
    for index, (signature, symbol) in enumerate(
        [
            (1668707188, "_EvaluateCurves"),
            (1835103334, "_EvaluateMatrix"),
            (1668707188, "_EvaluateCurves"),
        ]
    ):
        row = lines[3 + 2 * index].split()
        if (
            len(row) != 10
            or row[:2] != ["stage", str(index)]
            or row[3:6] != [str(signature), "3", "3"]
            or any(re.fullmatch(r"[1-9][0-9]*", row[c]) is None for c in [2, 6, 7, 8])
            or re.fullmatch(r"0|[1-9][0-9]*", row[9]) is None
            or lines[4 + 2 * index] != module
        ):
            raise ValueError("Wrong traversal stage identity")
        if int(row[7]) != base or int(row[6]) - base != offsets.get(symbol):
            raise ValueError("Wrong traversal stage module/offset")
        pointers.append(int(row[2]))
        nexts.append(int(row[9]))
    if len(set(pointers)) != 3 or nexts != [*pointers[1:], 0]:
        raise ValueError("Wrong traversal stage chain")
    return {
        "pipeline_probe_traversal_observed": True,
        "vectors": 256,
        "stage_calls": 768,
        "native_symbol_offsets": {
            s: offsets[s] for s in ["__LUTeval16", "_EvaluateCurves", "_EvaluateMatrix"]
        },
        "test_abi_portable": False,
        "renderer_pixel_traversal_observed": False,
    }


def verify_vectors(data: bytes, coefficients: list[str]) -> dict[str, object]:
    """Require complete linked values, exact byte formatting and restored output.

    Target floats and saturated words are observed, not independent target truth.
    Source/matrix arithmetic uses the independently declared rational oracle.
    """
    if len(data) != 256 * 136:
        raise ValueError("Missing/extra traversal vectors")
    stage_data = bytearray()
    for index, row in enumerate(struct.iter_unpack("<34I", data)):
        codes = (index, 255 - index, index * 73 % 256)
        if row[0] != index or row[1:4] != codes or row[4:7] != tuple(c * 257 for c in codes):
            raise ValueError("Wrong traversal input/order/formatter")
        if row[10:13] != row[13:16] or row[16:19] != row[19:22]:
            raise ValueError("Broken traversal stage linkage")
        # Decode every stage component to reject NaN/Inf even at the last stage.
        for bits in row[7:25]:
            signed32(bits)
        if any(v > 65535 for v in row[25:28]) or any(v > 255 for v in row[28:34]):
            raise ValueError("Out-of-domain traversal output")
        if row[28:31] != tuple((v + 128) // 257 for v in row[25:28]):
            raise ValueError("Wrong traversal output formatter")
        if row[28:31] != row[31:34]:
            raise ValueError("Changed output after observer restoration")
        stage_data.extend(struct.pack("<9I", *row[7:13], *row[16:19]))
    arithmetic = verify_stages(bytes(stage_data), coefficients, denominator=255)
    return {
        "vectors": 256,
        "sha256": hashlib.sha256(data).hexdigest(),
        "arithmetic": arithmetic,
        "stage_links_bit_exact": True,
        "restored_outputs_bit_exact": True,
        "target_precision_verified": False,
        "saturation_arithmetic_verified": False,
        "renderer_pixel_traversal_observed": False,
        "complete_cmm_precision_verified": False,
    }
