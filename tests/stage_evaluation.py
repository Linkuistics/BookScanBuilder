"""Independent finite-domain source-stage and matrix arithmetic verification."""

import hashlib
import re
import struct
from fractions import Fraction
from functools import lru_cache

from source_gamma import truth, value32
from target_observation import Event

MATRIX_BOUND = Fraction(1, 2**24) + Fraction(1, 2**48)


def signed32(bits: int) -> Fraction:
    value = value32(bits & 0x7FFFFFFF)
    return -value if bits & 0x80000000 else value


@lru_cache(maxsize=4)
def _verify(data: bytes, matrix: tuple[Fraction, ...], denominator: int) -> dict[str, object]:
    grid = truth(denominator)
    if len(data) != len(grid) * 36:
        raise ValueError("Incomplete/extra stage vectors")
    maximum = Fraction()
    for index, row in enumerate(struct.iter_unpack("<9I", data)):
        codes = (index, denominator - index, (index * 73) % (denominator + 1))
        expected = [grid[c] for c in codes]
        if tuple(row[:3]) != tuple(v[0] for v in expected):
            raise ValueError(f"Wrong stage input bits at vector {index}")
        if tuple(row[3:6]) != tuple(v[1] for v in expected):
            raise ValueError(f"Wrong source-stage output bits at vector {index}")
        inputs = [value32(v) for v in row[3:6]]
        for channel in range(3):
            exact = sum((matrix[3 * channel + c] * inputs[c] for c in range(3)), Fraction())
            actual = signed32(row[6 + channel])
            error = abs(actual - exact)
            if error > MATRIX_BOUND:
                raise ValueError(f"Wrong matrix-stage output at vector {index}, channel {channel}")
            maximum = max(maximum, error)
    return {
        "vectors": len(grid),
        "sha256": hashlib.sha256(data).hexdigest(),
        "source_stage_correctly_rounded": True,
        "matrix_maximum_error": str(maximum),
        "matrix_arithmetic_bound": str(MATRIX_BOUND),
        "complete_cmm_precision_verified": False,
    }


def verify_stages(
    data: bytes, coefficients: list[str], *, denominator: int = 65535
) -> dict[str, object]:
    """Compare actual outputs with exact rational truth, never another CMM.

    For row L1 norm <=2, binary32 inputs in [0,1] and no offset, six binary64
    operations have absolute error <=2*gamma6 plus six underflow units <2^-48.
    Binary32 rounding of a result in [-2,2] adds <=2^-24. This envelope is
    independent of native outputs and includes this binary's fused dot product.
    https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmslut.c
    """
    if len(coefficients) != 9 or not 1 <= denominator <= 65535:
        raise ValueError("Unsupported stage matrix/domain")
    matrix = tuple(Fraction(v) for v in coefficients)
    if any(sum(abs(v) for v in matrix[3 * r : 3 * r + 3]) > 2 for r in range(3)):
        raise ValueError("Matrix outside declared arithmetic domain")
    return dict(_verify(data, matrix, denominator))


def verify_dispatch_abi(disassembly: str) -> dict[str, int]:
    """Bind this exact arm64 stage layout/evaluator to native instructions."""
    bodies: dict[str, str] = {}
    offsets: dict[str, int] = {}
    for name in [
        "_cmsStageData",
        "_cmsStageNext",
        "_cmsStageInputChannels",
        "_cmsStageOutputChannels",
        "_cmsStageType",
        "__cmsStageAllocPlaceholder",
        "_EvaluateCurves",
        "_EvaluateMatrix",
        "__LUTeval16",
        "__LUTevalFloat",
    ]:
        match = re.search(
            rf"^{name}:\n(.*?)(?=^_[A-Za-z0-9_.]+:|\Z)", disassembly, re.MULTILINE | re.DOTALL
        )
        if match is None:
            raise ValueError("Native stage ABI missing function: " + name)
        bodies[name] = match[1]
        first = re.match(r"([0-9a-f]+)\s", match[1])
        if first is None:
            raise ValueError("Native stage ABI missing symbol offset")
        offsets[name] = int(first[1], 16)
    for name, pattern in [
        ("_cmsStageData", r"ldr\s+x0, \[x0, #0x30\]"),
        ("_cmsStageNext", r"ldr\s+x0, \[x0, #0x38\]"),
        ("_cmsStageInputChannels", r"ldr\s+w0, \[x0, #0x10\]"),
        ("_cmsStageOutputChannels", r"ldr\s+w0, \[x0, #0x14\]"),
        ("_cmsStageType", r"ldr\s+w0, \[x0, #0x8\]"),
        ("__cmsStageAllocPlaceholder", r"mov\s+x22, x4.*stp\s+x22, x21, \[x0, #0x18\]"),
        ("_EvaluateCurves", r"ldr\s+x21, \[x2, #0x30\].*bl\s+_cmsEvalToneCurveFloat"),
        (
            "_EvaluateMatrix",
            r"ldr\s+x11, \[x2, #0x30\].*fcvt\s+d1, s1.*fmadd\s+d0, d1, d2, d0.*fcvt\s+s0, d0",
        ),
        ("__LUTeval16", r"ldr\s+x9, \[x21, #0x18\].*blr\s+x9.*ldr\s+x21, \[x21, #0x38\]"),
        ("__LUTevalFloat", r"ldr\s+x9, \[x21, #0x18\].*blr\s+x9.*ldr\s+x21, \[x21, #0x38\]"),
    ]:
        if re.search(pattern, bodies[name], re.DOTALL) is None:
            raise ValueError("Native stage ABI instruction mismatch: " + name)
    return offsets


def verify_binding(
    text: str,
    event: Event,
    pid: int,
    pipeline_handle: int,
    offsets: dict[str, int],
    module_path: str,
    *,
    denominator: int = 65535,
) -> dict[str, object]:
    """Require the actual stage pointer's module-relative native symbol identity."""
    lines = text.splitlines()
    prefix = (
        f"stage-dispatch-v1 {pid} {event.sequence} {event.transform_handle} "
        f"{pipeline_handle} {denominator + 1}"
    )
    if (
        len(lines) != 6
        or pid <= 0
        or pipeline_handle <= 0
        or event.kind != "transform"
        or event.input_format not in (25, 262169)
        or (event.output_format, event.intent, event.flags, event.cmm_version)
        != (262169, 1, 8448, 2190)
        or lines[0] != prefix
        or lines[-1] != "abi 24 48 56 16 20 8 fpcr 0"
    ):
        raise ValueError("Foreign/incomplete stage dispatch binding")
    pointers: set[int] = set()
    bases: set[int] = set()
    for index, (signature, symbol) in enumerate(
        [(1668707188, "_EvaluateCurves"), (1835103334, "_EvaluateMatrix")]
    ):
        fields = lines[1 + index * 2].split()
        if (
            len(fields) != 9
            or fields[:2] != ["stage", str(index)]
            or fields[3:6] != [str(signature), "3", "3"]
            or any(re.fullmatch(r"[1-9][0-9]*", fields[c]) is None for c in [2, 6, 7, 8])
            or lines[2 + index * 2] != module_path
        ):
            raise ValueError("Wrong stage dispatch/module identity")
        pointer, evaluator, base = (int(fields[c]) for c in [2, 6, 7])
        if pointer in pointers or evaluator - base != offsets.get(symbol):
            raise ValueError("Wrong native stage dispatch address/offset")
        pointers.add(pointer)
        bases.add(base)
    if len(bases) != 1:
        raise ValueError("Foreign stage dispatch module base")
    return {
        "source_stage_dispatch_bound": True,
        "matrix_stage_dispatch_bound": True,
        "native_symbol_offsets": {s: offsets[s] for s in ["_EvaluateCurves", "_EvaluateMatrix"]},
        "pipeline_traversal_observed": False,
        "test_abi_portable": False,
    }
