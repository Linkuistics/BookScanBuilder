"""Read final live pipeline data; consistency probes are not a colour oracle."""

import hashlib
import re
from fractions import Fraction
from typing import cast

from icc_matrix_truth import inverse
from profile_memory import Memory, binary
from target_observation import Event


def verify_abi(disassembly: str) -> None:
    """Check this arm64 binary's actual Lut/worker load sites, not header guesses."""
    for function, pattern in [
        ("_cmsDeleteTransform", r"ldr\s+x0, \[x19, #0x70\].*?\n[^\n]*bl\s+_cmsPipelineFree"),
        ("_cmsDoTransform", r"ldr\s+x8, \[x0, #0x8\].*?\n[^\n]*blr\s+x8"),
    ]:
        match = re.search(
            rf"^{function}:\n(.*?)(?=^_[A-Za-z0-9_.]+:|\Z)", disassembly, re.MULTILINE | re.DOTALL
        )
        if match is None or re.search(pattern, match[1], re.DOTALL) is None:
            raise ValueError("Native transform ABI load-site mismatch: " + function)


def parse_pipeline(text: str, event: Event, pid: int) -> dict[str, object]:
    lines = text.splitlines()
    prefix = (
        f"pipeline-v1 {pid} {event.sequence} {event.transform_handle} "
        f"{event.input_format} {event.output_format} {event.flags} {event.cmm_version} "
    )
    if (
        not lines
        or pid <= 0
        or event.kind != "transform"
        or event.input_format not in (262169, 25)
        or (event.output_format, event.intent, event.flags, event.cmm_version)
        != (262169, 1, 8448, 2190)
        or not lines[0].startswith(prefix)
    ):
        raise ValueError("Foreign/unsupported final pipeline binding")
    match = re.fullmatch(r"([1-9][0-9]*) ([1-9][0-9]*)", lines[0][len(prefix) :])
    if match is None or not 1 <= int(match[2]) <= 8:
        raise ValueError("Missing/unsupported pipeline stages")
    if len(lines) < 2 or lines[1].split() != [
        "creation",
        str(event.input_handle),
        str(event.target_handle),
        "1",
        "1",
        "1",
        "1",
        "0x1p+0",
        "0x1p+0",
    ]:
        raise ValueError("Foreign/unsupported actual creation metadata")
    position = 2
    stages: list[dict[str, object]] = []
    for index in range(int(match[2])):
        if position >= len(lines):
            raise ValueError("Incomplete final stages")
        fields = lines[position].split()
        if len(fields) != 5 or fields[:2] != ["stage", str(index)] or fields[3:] != ["3", "3"]:
            raise ValueError("Missing/reordered stage or unsupported channels")
        position += 1
        if fields[2] == "1835103334":  # 'matf', public cmsSigMatrixElemType
            if position >= len(lines):
                raise ValueError("Missing final matrix data")
            values = lines[position].split()
            if len(values) != 14 or values[0] != "matrix" or values[1] not in ("0", "1"):
                raise ValueError("Missing/unsupported final matrix")
            numbers = [binary(v) for v in values[2:]]
            if values[1] == "0" and any(numbers[9:]):
                raise ValueError("Unexpected absent matrix offset")
            stages.append(
                {
                    "kind": "matrix",
                    "matrix": [str(v) for v in numbers[:9]],
                    "offset": [str(v) for v in numbers[9:]] if values[1] == "1" else None,
                }
            )
            position += 1
        elif fields[2] == "1668707188":  # 'cvst', public cmsSigCurveSetElemType
            curves: list[dict[str, object]] = []
            for channel in range(3):
                if position >= len(lines):
                    raise ValueError("Missing final curve data")
                values = lines[position].split()
                if (
                    len(values) != 15
                    or values[:2] != ["curve", str(channel)]
                    or values[2] not in {str(v) for v in (1, 2, 3, 4, 5, -1, -2, -3, -4, -5)}
                ):
                    raise ValueError("Missing/reordered/unsupported final curve")
                domain = [binary(v) for v in values[3:5]]
                if domain[0] >= domain[1]:
                    raise ValueError("Invalid final curve domain")
                curves.append(
                    {
                        "kind": int(values[2]),
                        "domain": [str(v) for v in domain],
                        "parameters": [str(binary(v)) for v in values[5:]],
                    }
                )
                position += 1
            stages.append({"kind": "curves", "curves": curves})
        else:
            raise ValueError("Unsupported final pipeline stage")
    probes = lines[position:]
    if len(probes) != 256:
        raise ValueError("Incomplete/extra native pipeline probes")
    for index, line in enumerate(probes):
        fields = line.split()
        if (
            len(fields) != 8
            or fields[:2] != ["probe", str(index)]
            or any(re.fullmatch(r"[0-9]+", v) is None for v in fields[2:])
        ):
            raise ValueError("Missing/reordered native pipeline probes")
        words = [int(v) for v in fields[2:5]]
        packed = [int(v) for v in fields[5:]]
        if max(words) > 65535 or max(packed) > 255:
            raise ValueError("Invalid native probe range")
        if packed != [(v + 128) // 257 for v in words]:
            raise ValueError("Actual pipeline/transform quantizer mismatch")
    return {
        "stages": stages,
        "probe_count": len(probes),
        "probe_sha256": hashlib.sha256(("\n".join(probes) + "\n").encode()).hexdigest(),
        "creation_intents": [1, 1],
        "bpc_requested": [True, True],
        "adaptation_read_before_after": ["1", "1"],
        "probe_meaning": "Eval16 -> independently verified integer packer equals real transform",
        "independent_fidelity_verified": False,
        "intermediate_precision_verified": False,
    }


def verify_profile_stages(
    record: dict[str, object], source: Memory, target: Memory
) -> dict[str, object]:
    """Compare the constructed RGB pipeline with exact rational profile algebra.

    The 64*u*max(1,||T^-1||*||S||)*max(1,cond(T)) coefficient envelope is declared
    from binary64 roundoff and this well-conditioned 3x3 construction, not pixels.
    It checks the observed matrix only, not arbitrary ICCs, libm or CMM precision.
    """
    stages = record.get("stages")
    if not isinstance(stages, list) or len(cast(list[object], stages)) != 3:
        raise ValueError("Unexpected constructed profile stages")
    typed = cast(list[dict[str, object]], stages)
    if [s.get("kind") for s in typed] != ["curves", "matrix", "curves"]:
        raise ValueError("Unexpected constructed curve/matrix order")
    for stage, memory, sign in [(typed[0], source, 1), (typed[2], target, -1)]:
        expected = [
            {
                "kind": sign * c.kind,
                "domain": [str(v) for v in c.domain],
                "parameters": [str(v) for v in c.parameters],
            }
            for c in memory.curves
        ]
        if stage.get("curves") != expected:
            raise ValueError("Changed source/reversed target curve data")
    ti = inverse(target.matrix)
    norm_t = max(sum(abs(v) for v in row) for row in target.matrix)
    norm_i = max(sum(abs(v) for v in row) for row in ti)
    norm_s = max(sum(abs(v) for v in row) for row in source.matrix)
    condition = norm_t * norm_i
    if condition > 16:
        raise ValueError("Unsupported ill-conditioned matrix construction")
    expected_matrix = [
        sum((ti[r][k] * source.matrix[k][c] for k in range(3)), Fraction())
        for r in range(3)
        for c in range(3)
    ]
    matrix = typed[1].get("matrix")
    if (
        not isinstance(matrix, list)
        or len(cast(list[object], matrix)) != 9
        or typed[1].get("offset") is not None
    ):
        raise ValueError("Unexpected constructed matrix/offset")
    actual = [Fraction(str(v)) for v in cast(list[object], matrix)]
    error = max(abs(a - b) for a, b in zip(actual, expected_matrix, strict=True))
    bound = Fraction(64, 2**53) * max(Fraction(1), norm_i * norm_s) * max(Fraction(1), condition)
    if error > bound:
        raise ValueError("Final matrix differs from independent profile composition")
    return {
        "expected_matrix": [str(v) for v in expected_matrix],
        "maximum_matrix_error": str(error),
        "matrix_envelope": str(bound),
        "target_condition": str(condition),
        "source_curves_exact": True,
        "reversed_target_curve_parameters_exact": True,
        "curve_evaluation_verified": False,
        "complete_cmm_precision_verified": False,
    }
