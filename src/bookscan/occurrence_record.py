"""Bind initial occurrence cores to verified source pages, RGB and saved analysis.

This is deliberately a component of the full checkpoint semantic verifier. It
does not verify render resources, native sample/profile assets, triage, review
actions or acknowledgement. The returned objects contain none of those unchecked
payloads. A core roster alone cannot qualify as a complete accepted project.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from bookscan import analysis_record, records, source_record
from bookscan.assessment import LIMITATION
from bookscan.assets import AssetError, Assets, RGBAsset
from bookscan.intake import Page
from bookscan.skew import Estimate


@dataclass
class OccurrenceRecordError(Exception):
    message: str
    code: str = "INVALID_PROJECT"
    exit_code: int = 3

    @property
    def remediation(self) -> str:
        return (
            "Use the compatible BookScanBuilder assessment-v1 reader with bookscan baseline "
            "status PROJECT; for damaged saved content use bookscan baseline create PDF "
            "--workdir NEW with an intact supported input. Fresh import loses review facts. "
            "Without intact input or a verifiable saved state no recovery is available."
        )

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True)
class CoreOccurrence:
    id: str
    source_sha256: str
    page: Page
    baseline: RGBAsset
    analysis: Estimate


def _json(value: object) -> bytes:
    """Reject Python coercions as well as ambiguous/non-UTF-8 saved JSON."""
    try:
        # Serialize first to reject circular containers before walking their types.
        # Canonical JSON distinguishes true/1 and 10/10.0 in source-page meaning.
        # https://docs.python.org/3.12/library/json.html#json.dumps
        raw = json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        pending = [value]
        while pending:
            item = pending.pop()
            if type(item) is dict:
                data = cast(dict[object, object], item)
                if any(type(key) is not str for key in data):
                    raise ValueError("Non-string saved key.")
                pending.extend(data.values())
            elif type(item) is list:
                pending.extend(cast(list[object], item))
            elif item is not None and type(item) not in (str, bool, int, float):
                raise ValueError("Non-JSON saved value.")
        # Enclosing arrays use a private object wrapper for the strict decoder.
        records.decode(b'{"value":' + raw + b"}")
        return raw
    except (ValueError, TypeError, RecursionError, records.RecordError) as error:
        raise OccurrenceRecordError("Invalid occurrence JSON values.") from error


def _array(value: object) -> list[object]:
    if type(value) is not list:
        raise OccurrenceRecordError("Saved occurrence/baseline roster must be an array.")
    return cast(list[object], value)


def _occurrence(value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise OccurrenceRecordError("Saved occurrence must be an object.")
    data = cast(dict[str, object], value)
    if set(data) != {
        "id",
        "source_pdf_page",
        "source_sha256",
        "geometry",
        "advisory_hint",
        "rgb_sha256",
        "render",
        "resolution",
        "native_samples",
        "native_sample_concerns",
        "composition_unavailable",
        "composition_fidelity_verified",
        "analysis",
        "triage_reasons",
        "limitation",
        "retention",
        "estimate_applied",
        "inspected",
    }:
        raise OccurrenceRecordError("Unsupported initial occurrence fields.")
    if (
        data["limitation"] != LIMITATION
        or data["retention"] != "baseline-retained/unresolved"
        or any(
            data[key] is not False
            for key in ("inspected", "estimate_applied", "composition_fidelity_verified")
        )
    ):
        raise OccurrenceRecordError(
            "Initial occurrence claims inspection/edit/fidelity acceptance."
        )
    return data


def verify_cores(
    images: Assets,
    source_value: object,
    occurrences: object,
    baselines: object,
    *,
    check_cancel: Callable[[], None] = lambda: None,
) -> tuple[CoreOccurrence, ...]:
    """Read all cores in exact source order under the caller's verified ownership.

    Nested inputs must come from records.decode; direct inputs get the same JSON
    type checks. No original read, native launch, build, reacquisition or mutation.
    The full semantic verifier must additionally verify every omitted payload.
    """
    images.owner.verify()
    check_cancel()
    _json({"occurrences": occurrences, "baselines": baselines})
    pages, references = _array(occurrences), _array(baselines)
    try:
        saved = source_record.restore(images.owner, source_value, check_cancel=check_cancel)
        if len(pages) != len(saved.pages) or len(references) != len(saved.pages):
            raise OccurrenceRecordError("Occurrence/baseline roster differs from complete source.")
        result: list[CoreOccurrence] = []
        for page, value, reference in zip(saved.pages, pages, references, strict=True):
            check_cancel()
            data = _occurrence(value)
            expected = source_record.page_record(page)
            actual = {key: data[key] for key in expected}
            if _json(actual) != _json(expected) or data["source_sha256"] != saved.sha256:
                raise OccurrenceRecordError(
                    "Occurrence identity/geometry/provenance differs from source."
                )
            baseline = RGBAsset.from_record(reference)
            if baseline.size != page.frame.pixels or data["rgb_sha256"] != baseline.rgb_sha256:
                raise OccurrenceRecordError(
                    "Occurrence RGB identity/dimensions differ from baseline."
                )
            images.read(baseline, check_cancel=check_cancel)
            estimate = analysis_record.restore(data["analysis"], baseline.size)
            result.append(
                CoreOccurrence(cast(str, expected["id"]), saved.sha256, page, baseline, estimate)
            )
        # Recheck the source across the whole asset read, without reopening the original.
        source_record.restore(images.owner, source_value, check_cancel=check_cancel)
        images.owner.verify()
        check_cancel()
        return tuple(result)
    except (
        source_record.SourceRecordError,
        AssetError,
        analysis_record.AnalysisRecordError,
    ) as error:
        raise OccurrenceRecordError(
            "Saved occurrence core could not verify: " + error.message
        ) from error
