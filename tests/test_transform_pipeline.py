"""Reject lost stages, foreign live-creation identities and inconsistent native probes."""

from dataclasses import replace
from fractions import Fraction

import pytest
from target_observation import Event


def event() -> Event:
    return Event(7, "transform", 88, 99, 101, 262169, 262169, 1, 8448, 2190)


def record() -> str:
    return (
        "pipeline-v1 42 7 101 262169 262169 8448 2190 123 1\n"
        "creation 88 99 1 1 1 1 0x1p+0 0x1p+0\n"
        "stage 0 1835103334 3 3\n"
        "matrix 0 0x1p+0 0x0p+0 0x0p+0 0x0p+0 0x1p+0 0x0p+0 "
        "0x0p+0 0x0p+0 0x1p+0 0x0p+0 0x0p+0 0x0p+0\n"
        + "".join(
            f"probe {v} {v * 257} {(255 - v) * 257} {((v * 73) % 256) * 257} "
            f"{v} {255 - v} {(v * 73) % 256}\n"
            for v in range(256)
        )
    )


def test_final_matrix_and_complete_probe_binding() -> None:
    from transform_pipeline import parse_pipeline

    result = parse_pipeline(record(), event(), 42)
    assert result["stages"] == [
        {"kind": "matrix", "matrix": ["1", "0", "0", "0", "1", "0", "0", "0", "1"], "offset": None}
    ]
    assert result["probe_count"] == 256
    assert result["independent_fidelity_verified"] is False


@pytest.mark.parametrize(
    "old,new",
    [
        ("pipeline-v1", "pipeline-v2"),
        ("42 7", "43 7"),
        ("42 7", "42 8"),
        ("7 101", "7 102"),
        ("8448", "8192"),
        ("2190", "2180"),
        ("123 1", "0 1"),
        ("123 1", "123 2"),
        ("creation 88", "creation 89"),
        ("88 99", "88 100"),
        ("1 1 1 1 0x", "1 1 0 1 0x"),
        ("0x1p+0\n", "0x0p+0\n"),
        ("stage 0", "stage 1"),
        ("1835103334", "0"),
        ("3 3\n", "4 3\n"),
        ("matrix 0", "matrix 2"),
        ("matrix 0 0x1p+0", "matrix 0 nan"),
        ("probe 0 0", "probe 1 0"),
        ("probe 0 0", "probe 0 257"),
        ("probe 0 0 65535 0 0", "probe 0 0 65535 0 1"),
        ("probe 255 ", "probe 256 "),
    ],
)
def test_rejects_foreign_incomplete_or_inconsistent_pipeline(old: str, new: str) -> None:
    from transform_pipeline import parse_pipeline

    with pytest.raises(ValueError):
        parse_pipeline(record().replace(old, new, 1), event(), 42)


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_rejects_incomplete_or_extra_probe(mutation: str) -> None:
    from transform_pipeline import parse_pipeline

    text = record()
    text = text.rsplit("probe 255", 1)[0] if mutation == "missing" else text + "extra\n"
    with pytest.raises(ValueError):
        parse_pipeline(text, event(), 42)


def test_signed_curve_kind_and_binary_parameters_are_retained() -> None:
    from transform_pipeline import parse_pipeline

    text = record()
    start = text.index("stage 0")
    end = text.index("probe 0")
    text = (
        text[:start]
        + "stage 0 1668707188 3 3\n"
        + "".join(
            f"curve {c} -4 -0x1p+10 0x1p+10 0x1.3333333333333p+1 " + "0x1p+0 " * 9 + "\n"
            for c in range(3)
        )
        + text[end:]
    )
    result = parse_pipeline(text, event(), 42)
    assert isinstance(result["stages"], list)
    assert result["stages"][0]["curves"][0]["kind"] == -4
    assert result["stages"][0]["curves"][0]["parameters"][0] == "5404319552844595/2251799813685248"


def test_independent_profile_composition_rejects_changed_matrix_or_curve() -> None:
    from profile_memory import Curve, Memory
    from transform_pipeline import verify_profile_stages

    one, zero = Fraction(1), Fraction()
    curve = Curve(1, (-one, one), (Fraction(2),) + (zero,) * 9, (0, 65535))
    profile = Memory(
        ((one, zero, zero), (zero, one, zero), (zero, zero, one)), (one, one, one), (curve,) * 3
    )
    curve_record = {"kind": 1, "domain": ["-1", "1"], "parameters": ["2"] + ["0"] * 9}
    result: dict[str, object] = {
        "stages": [
            {"kind": "curves", "curves": [curve_record] * 3},
            {
                "kind": "matrix",
                "matrix": ["1", "0", "0", "0", "1", "0", "0", "0", "1"],
                "offset": None,
            },
            {"kind": "curves", "curves": [{**curve_record, "kind": -1}] * 3},
        ]
    }
    evidence = verify_profile_stages(result, profile, profile)
    assert evidence["maximum_matrix_error"] == "0"
    with pytest.raises(ValueError, match="matrix"):
        changed = replace(
            profile, matrix=((Fraction(2), zero, zero), profile.matrix[1], profile.matrix[2])
        )
        verify_profile_stages(result, changed, profile)

    with pytest.raises(ValueError, match="curve"):
        changed = replace(profile, curves=(replace(curve, parameters=(one,) * 10),) * 3)
        verify_profile_stages(result, changed, profile)


def test_native_disassembly_rejects_wrong_lut_or_worker_offset() -> None:
    from transform_pipeline import verify_abi

    text = (
        "_cmsDeleteTransform:\n0000 ldr x0, [x19, #0x70]\n0004 cbz x0, 0x0010\n"
        "0008 bl _cmsPipelineFree\n_cmsDoTransform:\n0010 ldr x8, [x0, #0x8]\n"
        "0014 mov x5, sp\n0018 blr x8\n_next:\n"
    )
    verify_abi(text)
    for old, new in [("#0x70", "#0x78"), ("#0x8]", "#0x10]")]:
        with pytest.raises(ValueError):
            verify_abi(text.replace(old, new))
