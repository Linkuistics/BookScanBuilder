"""Public ``baseline create``: signal lifetime, error mapping and one frozen result.

The import itself is ``initial_import.create``; this module owns what surrounds
it. It records caught signals without raising from the handler, selects exactly
one outcome before the first output byte, and reports the checkpoint-commit fact
the import's progress latch observed. A committed checkpoint is authoritative
even when a later signal, cleanup failure or delivery failure changes the exit.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import TextIO, cast

from bookscan import checkpoints, initial_import
from bookscan.finite_command import Control, Interrupted, envelope, signals
from bookscan.finite_protocol import Delivery, Request

OPERATION = "baseline.create"
VERIFY = "Verify the saved project with bookscan baseline status PROJECT before retrying."
RETRY = (
    "Nothing was saved. Retry into a new unused project directory; a killed run may have "
    "left an incomplete directory, which create never reuses."
)
SOURCE_REMEDY = "Supply a stable, supported static PDF and retry into a new unused project."
IO_REMEDY = "Check source and project storage and permissions, then retry into a new project."


def _classify(error: BaseException) -> tuple[str, str, int, str, dict[str, object]]:
    """Return code, message, exit code, remedy and context for a known failure.

    Classes are duck-typed on the code/exit_code every import-owned error carries,
    so each domain keeps its own wording; only an unlisted OSError is invented here.
    """
    from bookscan import intake

    if isinstance(error, intake.ImportFailure):
        return error.code, error.message, error.exit_code, SOURCE_REMEDY, dict(error.context)
    code = cast(str | None, getattr(error, "code", None))
    exit_code = cast(int | None, getattr(error, "exit_code", None))
    if code is not None and exit_code is not None:
        message = cast(str, getattr(error, "message", None) or str(error))
        remedy = cast(str, getattr(error, "remediation", IO_REMEDY))
        return code, message, exit_code, remedy, {}
    return "WRITE_FAILED", f"Cannot complete create: {error}", 5, IO_REMEDY, {}


def _warning(text: str) -> dict[str, str]:
    code, _, message = text.partition(": ")
    return {
        "code": code if message else "CREATE_WARNING",
        "message": message or text,
        "remediation": "Verify the saved project with bookscan baseline status PROJECT.",
    }


def _committed(record: dict[str, object], progress: initial_import.Progress) -> None:
    """Attach the saved identity the command can still name after a late failure."""
    record["committed"] = True
    record["output"] = str(progress.path)
    record["project_id"] = progress.project_id
    result = progress.result
    if result is not None:
        state = result.checkpoint.state
        record.update(
            review_revision=state["review_revision"],
            snapshot_id=state["snapshot_id"],
            current_review_revision=state["review_revision"],
            checkpoint_revision=result.checkpoint.revision,
            checkpoint_sha256=result.checkpoint.sha256,
        )


def _failure(error: BaseException, progress: initial_import.Progress) -> dict[str, object]:
    record = envelope(OPERATION)
    committed = progress.committed or (
        isinstance(error, checkpoints.CheckpointError) and error.committed
    )
    if isinstance(error, Interrupted):
        record.update(
            code="INTERRUPTED",
            exit_code=error.exit_code,
            message=(
                "Create interrupted after its checkpoint was committed."
                if committed
                else "Create interrupted before any checkpoint was committed."
            ),
            remediation=VERIFY if committed else RETRY,
            context={"phase": "after-checkpoint" if committed else "before-checkpoint"},
        )
    else:
        code, message, exit_code, remedy, context = _classify(error)
        if committed:
            remedy = f"{remedy} {VERIFY}"
        record.update(
            code=code,
            exit_code=exit_code,
            message=message,
            remediation=remedy,
            context={**context, "phase": "after-checkpoint" if committed else "create"},
        )
    record["affected_ids"] = []
    if committed:
        _committed(record, progress)
    return record


def _created(progress: initial_import.Progress) -> dict[str, object]:
    record = envelope(OPERATION)
    _committed(record, progress)
    result = progress.result
    assert result is not None
    record.update(
        status="created",
        exit_code=0,
        warnings=[_warning(item) for item in result.warnings],
    )
    return record


def _serialize(record: Mapping[str, object], json_mode: bool) -> str:
    if json_mode:
        return json.dumps(record, ensure_ascii=True, allow_nan=False) + "\n"
    if record["status"] == "error":
        return f"{record['code']}: {record['message']}\n{record['remediation']}\n"
    return str(record["output"]) + "\n"


def run(request: Request, stdout: TextIO, stderr: TextIO, *, delivery: Delivery | None) -> int:
    """Freeze one outcome before delivery; a later signal cannot replace it."""
    from bookscan import native_setup

    control = Control()
    progress = initial_import.Progress()
    known: tuple[type[BaseException], ...] = _known_errors()
    with signals(control):
        try:
            initial_import.create(
                Path(request.subject),
                Path(request.options["--workdir"][0]),
                cache=native_setup.default_cache(),
                progress=progress,
                check_cancel=control.check,
            )
            if not progress.committed or progress.result is None:
                raise checkpoints.CheckpointError(
                    "WRITE_FAILED", "Create returned without a committed checkpoint.", 5
                )
            record = _created(progress)
            text = _serialize(record, request.json)
            control.check()
        except (Interrupted, OSError, *known) as error:
            record = _failure(error, progress)
            text = _serialize(record, request.json)
        result = cast(int, record["exit_code"])
        target = stdout if request.json or result == 0 else stderr
        try:
            target.write(text)
            target.flush()
        except OSError:
            if delivery is not None:
                delivery.failed = True
            try:
                stderr.write(
                    "RESULT_DELIVERY_FAILED: Cannot deliver create result. "
                    "Check stdout/stderr and verify the project with bookscan baseline status.\n"
                )
                stderr.flush()
            except OSError:
                pass
            return result or 5
        if record["status"] != "error":
            for warning in cast(list[dict[str, str]], record["warnings"]):
                try:
                    stderr.write(f"{warning['code']}: {warning['message']}\n")
                    stderr.flush()
                except OSError:
                    break
        return result


def _known_errors() -> tuple[type[BaseException], ...]:
    """Every domain error import can select, loaded only on the create route."""
    from bookscan import (
        analysis_record,
        assets,
        intake,
        native_blobs,
        occurrence_record,
        ownership,
        project_header,
        records,
        render,
        render_record,
        render_workspace,
        resource_record,
        skew,
        source_record,
        triage_record,
    )

    return (
        intake.ImportFailure,
        project_header.HeaderError,
        ownership.OwnershipError,
        checkpoints.CheckpointError,
        skew.NativeError,
        render.RenderFailed,
        render_workspace.WorkspaceError,
        assets.AssetError,
        native_blobs.BlobError,
        occurrence_record.OccurrenceRecordError,
        analysis_record.AnalysisRecordError,
        source_record.SourceRecordError,
        resource_record.ResourceRecordError,
        triage_record.TriageRecordError,
        render_record.RenderRecordError,
        records.RecordError,
    )
