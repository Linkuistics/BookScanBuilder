"""Protocol breaks must never turn invalid native estimates into suggestions."""

import json
import math
from pathlib import Path

import pytest
from PIL import Image

from bookscan.skew import NativeError, parse_estimate, write_analysis


def record(status: int = 0, angle: float | None = 0.0, ratio: float | None = 10.0) -> str:
    return json.dumps(
        {
            "schema": "BookScanBuilderSkew",
            "version": 1,
            "leptonica": "leptonica-1.87.0",
            "width": 1200,
            "height": 900,
            "status": status,
            "angle_degrees": angle,
            "score_ratio": ratio,
        }
    )


@pytest.mark.parametrize(
    ("status", "angle", "ratio", "available", "reasons"),
    [
        (0, 0.0, 10.0, True, ()),
        (0, 0.00001, 1.01, True, ("skew-nonzero",)),
        (0, -2.0, 10.0, True, ("skew-nonzero",)),
        (1, 0.0, 10.0, False, ("assessment-unavailable",)),
        (0, 0.0, 0.0, False, ("assessment-unavailable",)),
        (0, None, 10.0, False, ("assessment-unavailable",)),
        (0, 2.0, None, False, ("assessment-unavailable",)),
        (0, math.nan, 10.0, False, ("assessment-unavailable",)),
        (0, 2.0, math.inf, False, ("assessment-unavailable",)),
    ],
)
def test_invalid_results_are_unavailable_without_deadband(
    status: int, angle: float | None, ratio: float | None, available: bool, reasons: tuple[str, ...]
) -> None:
    estimate = parse_estimate(record(status, angle, ratio), "", (1200, 900))
    assert (estimate.available, estimate.reasons) == (available, reasons)
    assert estimate.region == (0, 0, 1200, 900)
    assert estimate.native_status == status
    # Nonfinite outputs must remain inspectable and safe to save as ordinary JSON.
    json.dumps(estimate.to_dict(), allow_nan=False)


def test_sweep_edge_diagnostic_survives_zero_sentinel() -> None:
    estimate = parse_estimate(record(0, 0, 0), "Warning: max found at sweep edge\n", (1200, 900))
    assert estimate.reasons == ("assessment-unavailable", "skew-range-edge")
    assert "sweep edge" in estimate.diagnostics


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", "other"),
        ("version", 2),
        ("version", True),
        ("leptonica", "leptonica-1.86.0"),
        ("width", 1199),
        ("height", 899),
        ("status", False),
        ("status", 1.5),
        ("angle_degrees", "0"),
        ("score_ratio", False),
        ("score_ratio", -1),
    ],
)
def test_malformed_or_wrong_subject_result_fails(field: str, value: object) -> None:
    payload: dict[str, object] = json.loads(record())
    payload[field] = value
    with pytest.raises(NativeError):
        parse_estimate(json.dumps(payload), "", (1200, 900))


@pytest.mark.parametrize("payload", ["{}", "[]", record() + record(), '{"schema":1,"schema":2}'])
def test_incomplete_duplicate_or_multiple_records_fail(payload: str) -> None:
    with pytest.raises(NativeError):
        parse_estimate(payload, "", (1200, 900))


def test_analysis_is_full_size_copy_and_leaves_rgb_intact(tmp_path: Path) -> None:
    baseline = Image.new("RGB", (4, 2))
    baseline = Image.frombytes(
        "RGB", (4, 2), bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 128, 128, 128] * 2)
    )
    before = baseline.tobytes()
    analysis = tmp_path / "analysis.png"
    write_analysis(baseline, analysis)
    with Image.open(analysis) as actual:
        assert (actual.mode, actual.size) == ("L", (4, 2))
        assert actual.tobytes() == bytes([76, 150, 29, 128] * 2)
    assert baseline.mode == "RGB" and baseline.tobytes() == before


def test_analysis_refuses_overwrite(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis.png"
    analysis.write_bytes(b"owned elsewhere")
    with pytest.raises(FileExistsError):
        write_analysis(Image.new("RGB", (4, 2)), analysis)
    assert analysis.read_bytes() == b"owned elsewhere"
