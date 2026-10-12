"""Initial triage meaning, derived from checked occurrence evidence.

The full semantic verifier must supply verified geometry, analysis, native
inventory and decoder diagnostics. This component checks their reason binding;
it does not verify those assets, later review dispositions or source fidelity.
No files, tools, writer acquisitions or mutations are needed here.
"""

from dataclasses import dataclass
from typing import cast

from bookscan.intake import Page
from bookscan.samples import Inventory
from bookscan.skew import AssessmentFailed, Estimate


@dataclass
class TriageRecordError(Exception):
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
class Reason:
    id: str
    details: tuple[str, ...]

    @property
    def allowed_decisions(self) -> tuple[str, ...]:
        return (
            ("reject", "retain-unresolved") if self.id == "skew-nonzero" else ("retain-unresolved",)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "details": list(self.details),
            "allowed_decisions": list(self.allowed_decisions),
            "disposition": "baseline-retained/unresolved",
        }


def derive(
    page: Page, estimate: Estimate, native: Inventory, diagnostics: str
) -> tuple[Reason, ...]:
    """Apply the existing initial-assessment rules without clearing any concern."""
    reasons = [Reason("orientation-unverified", ("No orientation review or edit applied.",))]
    for reason in estimate.reasons:
        if reason not in {"skew-nonzero", "assessment-unavailable", "skew-range-edge"}:
            raise AssessmentFailed(f"Unknown advisory reason: {reason}.")
        reasons.append(Reason(reason, (estimate.diagnostics,) if estimate.diagnostics else ()))
    fidelity = [*native.resolution.concerns, *native.concerns]
    for placed in native.resolution.placements:
        if placed.above_baseline_resolution:
            fidelity.append("Above-300-ppi contributing placement: " + "/".join(placed.path))
    if native.composition_unavailable:
        fidelity.append(native.composition_unavailable)
    if fidelity:
        reasons.append(Reason("import-fidelity", tuple(fidelity)))
    if page.frame.extent_changed:
        reasons.append(
            Reason("extent-change", ("Effective MediaBox and CropBox display regions differ.",))
        )
    if diagnostics:
        reasons.append(Reason("decoder-warning", (diagnostics,)))
    return tuple(reasons)


def _strings(value: object) -> tuple[str, ...]:
    if type(value) is not list or any(type(v) is not str for v in cast(list[object], value)):
        raise TriageRecordError("Saved reason details/domains must be text arrays.")
    result = tuple(cast(list[str], value))
    try:
        for text in result:
            text.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise TriageRecordError("Saved reason text is not UTF-8.") from error
    return result


def restore(
    value: object, page: Page, estimate: Estimate, native: Inventory, diagnostics: str
) -> tuple[Reason, ...]:
    """Require exact initial reason order/details/Q1 domains and unresolved state.

    All dependency arguments must already be checked by their owning readers.
    A later reject/retain-unresolved action belongs to separate review records;
    it cannot rewrite this frozen initial assessment or imply human inspection.
    """
    if type(value) is not list:
        raise TriageRecordError("Saved initial reasons must be an array.")
    expected = derive(page, estimate, native, diagnostics)
    values = cast(list[object], value)
    if len(values) != len(expected):
        raise TriageRecordError("Saved initial reason roster differs from occurrence evidence.")
    for item, reason in zip(values, expected, strict=True):
        if type(item) is not dict:
            raise TriageRecordError("Saved initial reason must be an object.")
        data = cast(dict[str, object], item)
        if (
            set(data) != {"id", "details", "allowed_decisions", "disposition"}
            or type(data["id"]) is not str
            or data["id"] != reason.id
            or type(data["disposition"]) is not str
            or data["disposition"] != "baseline-retained/unresolved"
        ):
            raise TriageRecordError("Unsupported initial reason identity/fields/disposition.")
        if (
            _strings(data["details"]) != reason.details
            or _strings(data["allowed_decisions"]) != reason.allowed_decisions
        ):
            raise TriageRecordError("Saved initial reason details/domain contradict evidence.")
    return expected


def record(
    reasons: tuple[Reason, ...],
    page: Page,
    estimate: Estimate,
    native: Inventory,
    diagnostics: str,
) -> list[dict[str, object]]:
    """Refuse inconsistent initial reasons before serializing an assessed page."""
    value = [r.to_dict() for r in reasons]
    restore(value, page, estimate, native, diagnostics)
    return value
