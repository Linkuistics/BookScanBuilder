"""Verified finite read of an initial baseline, with its own signal lifetime.

Status does not publish a checkpoint, preflight historical executables or rebuild
pixels. Every predecessor and referenced asset must pass the complete reader.
Later review state and summary packets belong with their working operations.
"""

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import TextIO, cast

from bookscan import baseline_state, checkpoints, project_header, review_facts
from bookscan.assessment import LIMITATION
from bookscan.assets import AssetError
from bookscan.finite_command import Control, Interrupted, envelope, signals
from bookscan.finite_protocol import Delivery, Request
from bookscan.native_blobs import BlobError
from bookscan.occurrence_record import OccurrenceRecordError
from bookscan.ownership import OwnershipError


def status(project: Path, *, check_cancel: Callable[[], None] = lambda: None) -> dict[str, object]:
    """Acquire once and return only a completely verified, detached current roster.

    The complete reader is also mandatory for every predecessor. A successful
    read changes no review/checkpoint fact and confers no inspection or fidelity.
    Ownership remains held until the result's roster has been assembled/verified.
    """

    def verify(stores: project_header.Stores, value: dict[str, object]) -> None:
        baseline_state.restore(stores, value, check_cancel=check_cancel)

    check_cancel()
    with project_header.resume(project, verify_state=verify, check_cancel=check_cancel) as (
        stores,
        checkpoint,
    ):
        payload = checkpoint.state
        current = baseline_state.restore(stores, payload, check_cancel=check_cancel)
        snapshot = cast(dict[str, object], payload["snapshot"])
        originals = cast(list[dict[str, object]], payload["occurrences"])
        pages = cast(list[dict[str, object]], snapshot["pages"])
        roster: list[dict[str, object]] = []
        for original, page in zip(originals, pages, strict=True):
            check_cancel()
            decided = [
                {"reason": r["id"], **cast(dict[str, object], r["decision"])}
                for r in cast(list[dict[str, object]], page["triage_reasons"])
                if "decision" in r
            ]
            roster.append(copy.deepcopy({**original, **page, "dispositions": decided}))
        record = envelope("baseline.status")
        record.update(
            status="verified",
            project_id=current.project_id,
            review_revision=current.review_revision,
            current_review_revision=current.review_revision,
            snapshot_id=current.snapshot_id,
            checkpoint_revision=checkpoint.revision,
            checkpoint_sha256=checkpoint.sha256,
            pages=roster,
            limitation=LIMITATION,
            limitations=list(current.limitations),
            acknowledgement=review_facts.effective_acknowledgement(current.facts),
        )
        check_cancel()
    check_cancel()
    return record


def _human(record: dict[str, object]) -> str:
    if record["status"] == "error":
        return f"{record['code']}: {record['message']}\n{record['remediation']}\n"
    lines = [
        f"Verified project {record['project_id']}; checkpoint {record['checkpoint_revision']}."
    ]
    for page in cast(list[dict[str, object]], record["pages"]):
        recorded = "inspected" if page["inspections"] else "uninspected"
        lines.append(
            f"{page['id']}: source PDF page {page['source_pdf_page']}; "
            f"baseline retained, {recorded}."
        )
        lines.append("  Geometry: " + json.dumps(page["geometry"], ensure_ascii=True))
        lines.append("  Advisory assessment: " + json.dumps(page["analysis"], ensure_ascii=True))
        for reason in cast(list[dict[str, object]], page["triage_reasons"]):
            lines.append(f"  {reason['id']}: {reason['disposition']}")
            lines.extend("    " + detail for detail in cast(list[str], reason["details"]))
    acknowledgement = cast(dict[str, object] | None, record["acknowledgement"])
    if acknowledgement is None:
        lines.extend([str(record["limitation"]), "No export acknowledgement recorded."])
    else:
        covered = len(cast(list[str], acknowledgement["ids"]))
        lines.extend(
            [
                str(record["limitation"]),
                f"Acknowledgement covers {covered} of {len(cast(list[object], record['pages']))}"
                f" pages; complete: {str(acknowledgement['complete']).lower()}.",
            ]
        )
    lines.extend(cast(list[str], record["limitations"]))
    return "\n".join(lines) + "\n"


def _serialize(record: dict[str, object], json_mode: bool) -> str:
    return (
        json.dumps(record, ensure_ascii=True, allow_nan=False) + "\n"
        if json_mode
        else _human(record)
    )


def run(request: Request, stdout: TextIO, stderr: TextIO, *, delivery: Delivery | None) -> int:
    """Freeze one outcome before delivery; read signals never turn into success."""
    control = Control()
    with signals(control):
        try:
            record = status(Path(request.subject), check_cancel=control.check)
            text = _serialize(record, request.json)
            control.check()
        except (
            Interrupted,
            project_header.HeaderError,
            OwnershipError,
            checkpoints.CheckpointError,
            OccurrenceRecordError,
            AssetError,
            BlobError,
        ) as error:
            record = envelope("baseline.status")
            record.update(
                exit_code=error.exit_code,
                code=error.code,
                message=error.message,
                remediation=(
                    project_header.HeaderError("INVALID_PROJECT", error.message).remediation
                    if error.code == "INVALID_PROJECT"
                    else "Check saved project storage and permissions before retrying."
                    if isinstance(error, (AssetError, BlobError))
                    else error.remediation
                ),
                affected_ids=[],
                context={"phase": "saved-state-verification"},
            )
            text = _serialize(record, request.json)
        result = cast(int, record["exit_code"])
        # Once chosen, a later caught signal cannot replace a domain error or
        # serialized success. No second record, including on a real closed pipe.
        target = stdout if request.json or result == 0 else stderr
        try:
            target.write(text)
            target.flush()
        except OSError:
            if delivery is not None:
                delivery.failed = True
            try:
                stderr.write(
                    "RESULT_DELIVERY_FAILED: Cannot deliver status. Check stdout/stderr.\n"
                )
                stderr.flush()
            except OSError:
                pass
            return result or 5
        return result
