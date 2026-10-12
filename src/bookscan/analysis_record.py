"""Read frozen advisory analysis without invoking tools or changing retained pixels.

This validates the existing assessment-v1 analysis object, not a complete saved
occurrence. Its caller must verify the source, occurrence and RGB reference and
supply the verified baseline size. A coherent record is not estimator accuracy,
source fidelity, human inspection or geometry acceptance.
"""

import json
import math
from dataclasses import dataclass
from typing import cast

from bookscan import records, skew


@dataclass
class AnalysisRecordError(Exception):
    message: str
    code: str = "INVALID_PROJECT"
    exit_code: int = 3

    @property
    def remediation(self) -> str:
        return (
            "Use the compatible BookScanBuilder assessment-v1 reader with baseline status "
            "PROJECT; for damaged saved content use bookscan baseline create PDF --workdir NEW "
            "with an intact supported input. Fresh import loses review facts. Without intact "
            "input or a verifiable saved state no recovery is available."
        )

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def _object(value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise AnalysisRecordError("Saved analysis field is not an object.")
    return cast(dict[str, object], value)


def _strings(value: object) -> list[str]:
    if type(value) is not list or not all(type(item) is str for item in cast(list[object], value)):
        raise AnalysisRecordError("Saved analysis reasons/invalid numerics must be string arrays.")
    return cast(list[str], value)


def restore(value: object, size: tuple[int, int]) -> skew.Estimate:
    """Check closed saved meaning against the caller's independently verified size.

    Nested saved inputs must come from records.decode. Direct callers receive the
    same type checks; no booleans, coerced tuples or raw nonfinite values qualify.
    """
    if (
        type(size) is not tuple
        or len(size) != 2
        or any(type(number) is not int or number <= 0 for number in size)
    ):
        raise AnalysisRecordError("Analysis requires a verified positive baseline size.")
    data = _object(value)
    if (
        set(data)
        != {
            "leptonica",
            "settings",
            "native_status",
            "angle_degrees",
            "score_ratio",
            "invalid_numeric",
            "regions",
            "diagnostics",
            "available",
            "reasons",
        }
        or data["leptonica"] != skew.LEPTONICA
    ):
        raise AnalysisRecordError("Unsupported saved analysis fields/library.")
    settings = _object(data["settings"])
    if set(settings) != set(skew.SETTINGS) or any(
        type(settings[key]) is not type(expected) or settings[key] != expected
        for key, expected in skew.SETTINGS.items()
    ):
        raise AnalysisRecordError("Unsupported saved analysis settings.")
    regions = data["regions"]
    if type(regions) is not list or len(cast(list[object], regions)) != 1:
        raise AnalysisRecordError("Saved analysis requires exactly one whole-baseline region.")
    region = cast(list[object], regions)[0]
    if (
        type(region) is not list
        or any(type(number) is not int for number in cast(list[object], region))
        or region != [0, 0, *size]
    ):
        raise AnalysisRecordError("Saved analysis region differs from the whole baseline.")
    if type(data["native_status"]) is not int or type(data["available"]) is not bool:
        raise AnalysisRecordError("Saved native status/availability has the wrong JSON type.")
    for key in ("angle_degrees", "score_ratio"):
        number = data[key]
        if number is not None and (type(number) is not float or not math.isfinite(number)):
            raise AnalysisRecordError("Saved analysis measurements must be finite floats/null.")
    diagnostics = data["diagnostics"]
    if type(diagnostics) is not str:
        raise AnalysisRecordError("Saved analysis diagnostics must be text.")
    try:
        diagnostics.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise AnalysisRecordError("Saved analysis diagnostics are not UTF-8 text.") from error
    invalid, reasons = _strings(data["invalid_numeric"]), _strings(data["reasons"])
    try:
        # Reapply only the pure native-protocol interpretation. No helper, renderer
        # or dependency preflight runs on resume. JSON null preserves nonfinite
        # measurements; the matching explicit markers are checked below.
        # https://docs.python.org/3.12/library/json.html#json.dumps
        native = json.dumps(
            {
                "schema": "BookScanBuilderSkew",
                "version": 1,
                "leptonica": data["leptonica"],
                "width": size[0],
                "height": size[1],
                "status": data["native_status"],
                "angle_degrees": data["angle_degrees"],
                "score_ratio": data["score_ratio"],
            },
            allow_nan=False,
        )
        result = skew.parse_estimate(native, diagnostics, size)
    except (skew.NativeError, ValueError) as error:
        raise AnalysisRecordError("Invalid saved advisory measurements.") from error
    if (
        list(result.invalid_numeric) != invalid
        or result.available is not data["available"]
        or list(result.reasons) != reasons
    ):
        raise AnalysisRecordError("Saved derived analysis facts contradict their measurements.")
    return result


def restore_json(raw: bytes, size: tuple[int, int]) -> skew.Estimate:
    try:
        value = records.decode(raw)
    except records.RecordError as error:
        raise AnalysisRecordError("Invalid saved analysis JSON.") from error
    return restore(value, size)


def record(estimate: skew.Estimate, size: tuple[int, int]) -> dict[str, object]:
    """Refuse inconsistent in-memory analysis before writing an assessed occurrence."""
    value = estimate.to_dict()
    restore(value, size)
    return value
