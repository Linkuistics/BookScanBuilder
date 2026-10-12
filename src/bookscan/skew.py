"""Advisory native estimates; this module never changes a retained image."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, cast

from PIL import Image

LEPTONICA = "leptonica-1.87.0"
SETTINGS: dict[str, object] = {
    "analysis": "Pillow RGB to L; whole image; no resize",
    "threshold": 160,
    "sweep_range_degrees": 7.0,
    "sweep_delta_degrees": 1.0,
    "sweep_reduction": 4,
    "search_reduction": 2,
    "search_delta_degrees": 0.01,
    "angle_convention": "deskew degrees, clockwise positive; advisory only",
}


class NativeError(RuntimeError):
    code = "DEPENDENCY_UNAVAILABLE"
    exit_code = 5
    remediation = "Run task process:setup; inspect its named native dependency failure."


class AssessmentFailed(NativeError):
    code = "ASSESSMENT_FAILED"
    remediation = "Check the analysis image and native diagnostic; retry with sufficient resources."


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate field {key}")
        result[key] = value
    return result


def json_object(text: str) -> dict[str, object]:
    try:
        data = cast(object, json.loads(text, object_pairs_hook=_unique_object))
    except ValueError as error:
        raise NativeError(f"Invalid native JSON: {error}") from error
    if not isinstance(data, dict):
        raise NativeError("Native JSON must be one object.")
    return cast(dict[str, object], data)


@dataclass(frozen=True)
class Estimate:
    native_status: int
    angle_degrees: float | None
    score_ratio: float | None
    invalid_numeric: tuple[str, ...]
    region: tuple[int, int, int, int]
    diagnostics: str
    available: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "leptonica": LEPTONICA,
            "settings": dict(SETTINGS),
            "native_status": self.native_status,
            "angle_degrees": self.angle_degrees,
            "score_ratio": self.score_ratio,
            "invalid_numeric": list(self.invalid_numeric),
            "regions": [list(self.region)],
            "diagnostics": self.diagnostics,
            "available": self.available,
            "reasons": list(self.reasons),
        }


def parse_estimate(text: str, diagnostics: str, size: tuple[int, int]) -> Estimate:
    data = json_object(text)
    if (
        data.get("schema") != "BookScanBuilderSkew"
        or type(data.get("version")) is not int
        or data["version"] != 1
        or data.get("leptonica") != LEPTONICA
    ):
        raise NativeError("Unsupported native estimator protocol/version/library.")
    for key, expected in zip(("width", "height"), size, strict=True):
        if type(data.get(key)) is not int or data[key] != expected or expected <= 0:
            raise NativeError(f"Native estimator {key} does not match the analysis image.")
    status = data.get("status")
    if type(status) is not int:
        raise NativeError("Native estimator status is not an integer.")
    numbers: list[float | None] = []
    invalid: list[str] = []
    for key in ("angle_degrees", "score_ratio"):
        if key not in data:
            raise NativeError(f"Native estimator omitted {key}.")
        raw = data[key]
        if raw is None:
            invalid.append(f"{key}:nonfinite")
            numbers.append(None)
        elif type(raw) not in (int, float):
            raise NativeError(f"Native estimator {key} is not numeric/null.")
        else:
            try:
                number = float(cast(int | float, raw))
            except OverflowError as error:
                raise NativeError(f"Native estimator {key} overflowed.") from error
            if math.isfinite(number):
                numbers.append(number)
            else:
                invalid.append(f"{key}:nonfinite")
                numbers.append(None)
    angle, ratio = numbers
    if ratio is not None and ratio < 0:
        raise NativeError("Native score ratio cannot be negative.")
    # Leptonica 1.87.0 can return status 0 AND confidence 0: no deadband/probability.
    # https://raw.githubusercontent.com/DanBloomberg/leptonica/1.87.0/src/skew.c
    available = status == 0 and not invalid and ratio != 0
    reasons: list[str] = []
    if not available:
        reasons.append("assessment-unavailable")
    elif angle != 0:
        reasons.append("skew-nonzero")
    if "max found at sweep edge" in diagnostics or (angle is not None and abs(angle) > 6):
        # The library's own confidence-suppression boundary is 7 - sweepdelta.
        reasons.append("skew-range-edge")
    return Estimate(
        status, angle, ratio, tuple(invalid), (0, 0, *size), diagnostics, available, tuple(reasons)
    )


def write_analysis(baseline: Image.Image, destination: Path) -> None:
    if baseline.mode != "RGB":
        raise AssessmentFailed("The retained baseline must be decoded RGB.")
    with destination.open("xb") as stream:
        write_analysis_stream(baseline, stream)


def write_analysis_stream(baseline: Image.Image, stream: BinaryIO) -> None:
    if baseline.mode != "RGB":
        raise AssessmentFailed("The retained baseline must be decoded RGB.")
    # Pillow 12.3 documents RGB -> L luma; conversion allocates a separate image.
    # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.convert
    with baseline.convert("L") as analysis:
        analysis.save(stream, format="PNG")
