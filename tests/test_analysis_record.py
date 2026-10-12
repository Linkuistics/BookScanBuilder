"""Saved advisory measurements cannot acquire availability or scope by corruption."""

import copy
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from bookscan.skew import Estimate


def literal() -> dict[str, object]:
    # Literal saved meaning, independent of both the native parser and serializer.
    return {
        "leptonica": "leptonica-1.87.0",
        "settings": {
            "analysis": "Pillow RGB to L; whole image; no resize",
            "threshold": 160,
            "sweep_range_degrees": 7.0,
            "sweep_delta_degrees": 1.0,
            "sweep_reduction": 4,
            "search_reduction": 2,
            "search_delta_degrees": 0.01,
            "angle_convention": "deskew degrees, clockwise positive; advisory only",
        },
        "native_status": 0,
        "angle_degrees": -0.00001,
        "score_ratio": 1.01,
        "invalid_numeric": [],
        "regions": [[0, 0, 1200, 900]],
        "diagnostics": "café\n",
        "available": True,
        "reasons": ["skew-nonzero"],
    }


@pytest.mark.parametrize(
    ("status", "angle", "ratio", "diagnostics", "invalid", "available", "reasons"),
    [
        (0, 0.0, 10.0, "", [], True, []),
        (0, -0.0, 10.0, "", [], True, []),
        (0, 0.00001, 1.01, "", [], True, ["skew-nonzero"]),
        (0, -0.00001, 1.01, "café\n", [], True, ["skew-nonzero"]),
        (1, -2.0, 10.0, "", [], False, ["assessment-unavailable"]),
        (0, 0.0, 0.0, "", [], False, ["assessment-unavailable"]),
        (0, None, 10.0, "", ["angle_degrees:nonfinite"], False, ["assessment-unavailable"]),
        (0, 2.0, None, "", ["score_ratio:nonfinite"], False, ["assessment-unavailable"]),
        (
            0,
            None,
            None,
            "",
            ["angle_degrees:nonfinite", "score_ratio:nonfinite"],
            False,
            ["assessment-unavailable"],
        ),
        (0, 6.0, 10.0, "", [], True, ["skew-nonzero"]),
        (0, -6.00001, 10.0, "", [], True, ["skew-nonzero", "skew-range-edge"]),
        (0, 6.5, 0.0, "", [], False, ["assessment-unavailable", "skew-range-edge"]),
        (
            0,
            0.0,
            0.0,
            "Warning: max found at sweep edge\n",
            [],
            False,
            ["assessment-unavailable", "skew-range-edge"],
        ),
    ],
)
def test_literal_saved_meaning_without_reassessment(
    status: int,
    angle: float | None,
    ratio: float | None,
    diagnostics: str,
    invalid: list[str],
    available: bool,
    reasons: list[str],
) -> None:
    from bookscan import analysis_record

    data = literal()
    data.update(
        native_status=status,
        angle_degrees=angle,
        score_ratio=ratio,
        diagnostics=diagnostics,
        invalid_numeric=invalid,
        available=available,
        reasons=reasons,
    )
    loaded = analysis_record.restore_json(json.dumps(data).encode(), (1200, 900))
    assert loaded == Estimate(
        status,
        angle,
        ratio,
        tuple(invalid),
        (0, 0, 1200, 900),
        diagnostics,
        available,
        tuple(reasons),
    )
    assert analysis_record.record(loaded, (1200, 900)) == data


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("leptonica", "leptonica-1.86.0"),
        ("leptonica", None),
        ("settings", {}),
        ("settings", []),
        ("native_status", False),
        ("native_status", 0.0),
        ("native_status", "0"),
        ("angle_degrees", False),
        ("angle_degrees", "-0.00001"),
        ("angle_degrees", 0),
        ("angle_degrees", None),
        ("angle_degrees", float("nan")),
        ("angle_degrees", float("inf")),
        ("score_ratio", False),
        ("score_ratio", -1.0),
        ("score_ratio", 1),
        ("score_ratio", 0.0),
        ("score_ratio", None),
        ("score_ratio", float("-inf")),
        ("available", False),
        ("available", 1),
        ("available", "true"),
        ("invalid_numeric", ["angle_degrees:nonfinite"]),
        ("invalid_numeric", None),
        ("invalid_numeric", ()),
        ("invalid_numeric", [False]),
        ("reasons", []),
        ("reasons", ["assessment-unavailable"]),
        ("reasons", ["skew-nonzero", "skew-nonzero"]),
        ("reasons", ["skew-nonzero", "orientation-unverified"]),
        ("reasons", ("skew-nonzero",)),
        ("reasons", "skew-nonzero"),
        ("diagnostics", None),
        ("diagnostics", ["warning"]),
        ("diagnostics", "\ud800"),
        ("regions", [[0, 0, 1199, 900]]),
        ("regions", [[1, 0, 1200, 900]]),
        ("regions", [[0, 0, True, 900]]),
        ("regions", [[0, 0, 1200.0, 900]]),
        ("regions", [[0, 0, 1200, 900], [0, 0, 1200, 900]]),
        ("regions", [[0, 0, 1200, 900, 1]]),
        ("regions", []),
        ("regions", [(0, 0, 1200, 900)]),
        ("regions", None),
        ("future_acceptance", True),
    ],
)
def test_corruption_cannot_change_saved_advisory_meaning(field: str, value: object) -> None:
    from bookscan import analysis_record

    data = literal()
    data[field] = value
    with pytest.raises(analysis_record.AnalysisRecordError) as caught:
        analysis_record.restore(data, (1200, 900))
    assert (caught.value.code, caught.value.exit_code) == ("INVALID_PROJECT", 3)
    assert "baseline status" in caught.value.remediation
    assert "Fresh import loses review facts" in caught.value.remediation


@pytest.mark.parametrize("field", list(literal()))
def test_omitted_measurement_or_derived_fact_is_not_inferred(field: str) -> None:
    from bookscan import analysis_record

    data = literal()
    del data[field]
    with pytest.raises(analysis_record.AnalysisRecordError):
        analysis_record.restore(data, (1200, 900))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("threshold", 160.0),
        ("sweep_reduction", True),
        ("sweep_range_degrees", 7),
        ("search_delta_degrees", 0.1),
        ("analysis", "RGB analysis"),
        ("future", "ignored"),
    ],
)
def test_different_or_unknown_settings_refuse(field: str, value: object) -> None:
    from bookscan import analysis_record

    data = literal()
    cast(dict[str, object], data["settings"])[field] = value
    with pytest.raises(analysis_record.AnalysisRecordError):
        analysis_record.restore(data, (1200, 900))


@pytest.mark.parametrize(
    "size",
    [
        (1199, 900),
        (1200, 899),
        (0, 900),
        (-1, 900),
        (True, 900),
        (1200.0, 900),
        (1200,),
        [1200, 900],
        None,
    ],
)
def test_scope_is_supplied_by_verified_baseline_not_saved_analysis(size: object) -> None:
    from bookscan import analysis_record

    with pytest.raises(analysis_record.AnalysisRecordError):
        analysis_record.restore(literal(), cast(tuple[int, int], size))


@pytest.mark.parametrize(
    "raw",
    [
        b"{}",
        b"[]",
        b'{"a":1,"a":2}',
        b'{"x":NaN}',
        b'{"x":1e999}',
        b'{"x":"\\ud800"}',
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"{}{}",
    ],
)
def test_saved_json_grammar_never_uses_native_protocol_leniency(raw: bytes) -> None:
    from bookscan import analysis_record

    with pytest.raises(analysis_record.AnalysisRecordError):
        analysis_record.restore_json(raw, (1200, 900))


def test_restored_and_serialized_records_are_detached() -> None:
    from bookscan import analysis_record

    data = literal()
    expected = copy.deepcopy(data)
    loaded = analysis_record.restore(data, (1200, 900))
    cast(list[str], data["reasons"]).clear()
    cast(list[list[int]], data["regions"])[0][2] = 1
    cast(dict[str, object], data["settings"])["threshold"] = 0
    returned = analysis_record.record(loaded, (1200, 900))
    assert returned == expected
    cast(list[str], returned["reasons"]).clear()
    cast(dict[str, object], returned["settings"])["threshold"] = 0
    assert analysis_record.record(loaded, (1200, 900)) == expected


def test_in_memory_forgery_cannot_be_written_as_saved_analysis() -> None:
    from bookscan import analysis_record

    correct = Estimate(0, 0.0, 0.0, (), (0, 0, 1200, 900), "", False, ("assessment-unavailable",))
    with pytest.raises(analysis_record.AnalysisRecordError):
        analysis_record.record(replace(correct, available=True, reasons=()), (1200, 900))


def test_invalid_predecessor_analysis_is_not_saved_or_resumed(tmp_path: Path) -> None:
    from bookscan import analysis_record, assets, ownership, project_header

    path = tmp_path / "Book project"
    path.mkdir()
    identity = ownership.provision(path)
    seen: list[str] = []

    def verify(images: assets.Assets, state: dict[str, object]) -> None:
        reference = assets.RGBAsset.from_record(state["rgb"])
        assert images.read(reference) == b"\x11\x7f\xfe" * 2
        estimate = analysis_record.restore(state["analysis"], reference.size)
        assert estimate.available is False and estimate.reasons == ("assessment-unavailable",)
        seen.append(cast(str, state["note"]))

    with ownership.Writer.acquire(path, identity) as owner:
        stores = project_header.Stores.provision(owner)
        reference = stores.images.publish(b"\x11\x7f\xfe" * 2, (2, 1))
        data = literal()
        data.update(
            angle_degrees=0.0,
            score_ratio=0.0,
            available=False,
            reasons=["assessment-unavailable"],
            regions=[[0, 0, 2, 1]],
        )
        state: dict[str, object] = {"rgb": reference.record(), "analysis": data, "note": "first"}
        first = stores.checkpoints.commit(
            state, expected=None, verify_state=lambda v: verify(stores.images, v)
        ).checkpoint
        wrong = copy.deepcopy(state)
        cast(dict[str, object], wrong["analysis"])["available"] = True
        with pytest.raises(analysis_record.AnalysisRecordError):
            stores.checkpoints.commit(
                wrong, expected=first, verify_state=lambda v: verify(stores.images, v)
            )
        current = stores.checkpoints.load(verify_state=lambda v: verify(stores.images, v))
        assert current is not None and current.revision == 1
        state["note"] = "second"
        stores.checkpoints.commit(
            state, expected=current, verify_state=lambda v: verify(stores.images, v)
        )
    seen.clear()
    with project_header.resume(
        path, verify_state=lambda stores, state: verify(stores.images, state)
    ) as (_, current):
        assert current.revision == 2
    assert seen == ["second", "first"]
    # An older hash-valid checkpoint cannot bypass semantic verification. The
    # controlled writer here deliberately supplies no semantic verifier.
    with project_header.resume(
        path, verify_state=lambda stores, state: verify(stores.images, state)
    ) as (stores, prior):
        bad = stores.checkpoints.commit(wrong, expected=prior, verify_state=lambda _: None)
        stores.checkpoints.commit(state, expected=bad.checkpoint, verify_state=lambda _: None)
    with pytest.raises(analysis_record.AnalysisRecordError):
        with project_header.resume(
            path, verify_state=lambda stores, state: verify(stores.images, state)
        ):
            pytest.fail("hash-valid invalid analysis predecessor was accepted")


def test_saved_analysis_read_requires_no_tool_or_filesystem_access(tmp_path: Path) -> None:
    # Deny actual reads/launches after import, rather than replacing native calls.
    script = f"""
import json, sys
from bookscan import analysis_record
raw = {json.dumps(literal()).encode()!r}
def denied(event, args):
    blocked = ("open", "os.listdir", "os.scandir", "os.system", "os.exec")
    if event in blocked or event.startswith("subprocess."):
        raise PermissionError("analysis boundary read/launch denied: " + event)
sys.addaudithook(denied)
try:
    open("deliberate-denied-read", "rb")
except PermissionError:
    print("control denied")
else:
    raise AssertionError("read denial instrument did not work")
loaded = analysis_record.restore_json(raw, (1200, 900))
assert loaded.available and loaded.angle_degrees == -0.00001
value = json.loads(raw)
value["available"] = False
try:
    analysis_record.restore(value, (1200, 900))
except analysis_record.AnalysisRecordError:
    print("analysis verified; inconsistent record refused")
else:
    raise AssertionError("wrong analysis escaped")
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "control denied",
        "analysis verified; inconsistent record refused",
    ]
