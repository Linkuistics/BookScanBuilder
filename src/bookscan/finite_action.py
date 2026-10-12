"""Public ``baseline disposition|inspected|acknowledge``: receipt actions over a saved project.

Two layers, so a second front end shares one state boundary:

* ``apply`` takes a caller-held verified writer ownership and a displayed-identity
  action. It never acquires or reads a file: durable retry lookup precedes
  currency and external file integrity (``baseline_state.act``), and a new action
  commits one checkpoint through the verified predecessor.
* ``run`` is the finite adapter. It checks static arguments before any read,
  reads the receipt file, acquires the project once, authenticates the receipt
  against its saved descriptor, and freezes exactly one outcome before delivery.

The committed fact is authoritative: a signal, cleanup failure or delivery failure
after the checkpoint commit changes the exit code, never ``committed``.

Invocation, receipt-file and receipt-grammar errors precede every project read, so
the PDF/RGB libraries behind saved-state verification are imported only once a
project is actually opened, as for help and the other invocation errors.
"""

import json
import os
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TextIO, cast

from bookscan import packet_receipts, review_facts
from bookscan.finite_command import Control, Interrupted, envelope, signals
from bookscan.finite_protocol import Delivery, Request

if TYPE_CHECKING:
    from bookscan import checkpoints, project_header

MAX_RECEIPT_BYTES = 1 << 20
VERIFY = "Verify the saved project with bookscan baseline status PROJECT before retrying."
IO_REMEDY = "Check project storage and permissions, then verify with bookscan baseline status."
# check_values reads only the reason/decision/scope/note; no receipt is needed for it.
_UNREAD = review_facts.Displayed("", "", "", "", "full")


@dataclass(frozen=True)
class Applied:
    """One action's outcome. ``checkpoint`` is None for a durable identical retry."""

    result: dict[str, object]
    replayed: bool
    checkpoint: "checkpoints.Checkpoint | None"
    project_id: str
    current_review_revision: str
    warnings: tuple[str, ...] = ()


@dataclass
class Progress:
    """Set the moment a checkpoint commit returns, so a later signal cannot hide it."""

    applied: Applied | None = None


def apply(
    stores: "project_header.Stores",
    checkpoint: "checkpoints.Checkpoint",
    action: review_facts.Action,
    *,
    integrity: Callable[[], None] = lambda: None,
    check_cancel: Callable[[], None] = lambda: None,
    progress: Progress | None = None,
) -> Applied:
    """Apply one action under the caller's ownership; commit only a new, verified state.

    ``checkpoint`` must be the current verified checkpoint the caller loaded under
    the same ownership. ``integrity`` is consulted only for a new action.
    """
    from bookscan import baseline_state

    def verifier(value: dict[str, object]) -> None:
        baseline_state.restore(stores, value, check_cancel=check_cancel)

    project_id = cast(str, checkpoint.state["project_id"])
    moved = baseline_state.act(
        stores,
        checkpoint.state,
        action,
        checkpoint_revision=checkpoint.revision + 1,
        integrity=integrity,
        check_cancel=check_cancel,
    )
    if moved.state is None:
        applied = Applied(moved.result, True, None, project_id, moved.facts.review_revision)
    else:
        committed = stores.checkpoints.commit(
            moved.state, expected=checkpoint, verify_state=verifier, check_cancel=check_cancel
        )
        applied = Applied(
            moved.result,
            False,
            committed.checkpoint,
            project_id,
            moved.facts.review_revision,
            committed.warnings,
        )
    if progress is not None:
        progress.applied = applied
    return applied


def read_receipt(path: Path) -> bytes:
    """Bounded read of one regular receipt file; never blocks on a FIFO or device."""
    try:
        # Following a user-supplied link is deliberate: authenticity is the bytes.
        # O_NONBLOCK keeps open() from waiting on a writerless FIFO; the type check
        # below then refuses it, and a regular file is unaffected.
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK)
    except OSError as error:
        raise packet_receipts.ReceiptError(
            f"Receipt file cannot be opened: {error.strerror or error}.", "malformed"
        ) from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise packet_receipts.ReceiptError("Receipt path is not a regular file.", "malformed")
        data = b""
        while len(data) <= MAX_RECEIPT_BYTES:
            chunk = os.read(descriptor, MAX_RECEIPT_BYTES + 1 - len(data))
            if not chunk:
                return data
            data += chunk
        raise packet_receipts.ReceiptError("Receipt file is larger than any receipt.", "malformed")
    except OSError as error:
        raise packet_receipts.ReceiptError(
            f"Receipt file cannot be read: {error.strerror or error}.", "malformed"
        ) from error
    finally:
        os.close(descriptor)


def _packet_integrity(
    descriptor: packet_receipts.Descriptor, receipt: packet_receipts.Receipt, given: Path
) -> Callable[[], None]:
    """Check every listed packet file where the given receipt says the packet lives."""

    def check() -> None:
        parts = receipt.path.split("/")
        names = Path(os.path.abspath(given)).parts
        if len(names) <= len(parts) or list(names[-len(parts) :]) != parts:
            raise packet_receipts.ReceiptError(
                "The receipt file is not at its issued packet location, so the packet's "
                "files cannot be verified; use the receipt inside the unedited packet.",
                "packet-file-changed",
            )
        root = Path(*names[: -len(parts)])
        try:
            directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        except OSError as error:
            raise packet_receipts.ReceiptError(
                f"The issued packet directory cannot be opened: {error.strerror or error}.",
                "packet-file-changed",
            ) from error
        try:
            packet_receipts.verify_files(descriptor, directory)
        finally:
            os.close(directory)

    return check


def _action(request: Request, displayed: review_facts.Displayed) -> review_facts.Action:
    options = request.options
    if request.operation == "baseline.disposition":
        return review_facts.Disposition(
            displayed, options["--reason"][0], options["--decision"][0], options["--note"][0]
        )
    if request.operation == "baseline.inspected":
        return review_facts.Inspection(
            displayed,
            options["--scope"][0],
            options["--viewer"][0],
            options["--scale"][0],
            options["--note"][0],
        )
    return review_facts.Acknowledgement(
        displayed, options["--note"][0], None if "--all" in options else options["--page"]
    )


def perform(request: Request, control: Control, progress: Progress) -> Applied:
    """The finite operation: static checks, receipt, one acquisition, authenticate, apply."""
    review_facts.check_values(_action(request, _UNREAD))
    given = Path(request.options["--receipt"][0])
    raw = read_receipt(given)
    receipt = packet_receipts.Receipt.parse(raw)
    control.check()
    from bookscan import baseline_state, project_header

    def verify(stores: "project_header.Stores", value: dict[str, object]) -> None:
        baseline_state.restore(stores, value, check_cancel=control.check)

    with project_header.resume(
        Path(request.subject), verify_state=verify, check_cancel=control.check
    ) as (stores, checkpoint):
        snapshot = cast(dict[str, object], checkpoint.state["snapshot"])
        descriptor = stores.packets.read(receipt.packet_id, check_cancel=control.check)
        packet_receipts.authenticate(
            descriptor,
            raw,
            project_id=cast(str, checkpoint.state["project_id"]),
            source_sha256=cast(str, snapshot["source_sha256"]),
        )
        action = _action(request, review_facts.Displayed.from_receipt(receipt))
        return apply(
            stores,
            checkpoint,
            action,
            integrity=_packet_integrity(descriptor, receipt, given),
            check_cancel=control.check,
            progress=progress,
        )


def _warning(text: str) -> dict[str, str]:
    code, _, message = text.partition(": ")
    return {
        "code": code if message else "ACTION_WARNING",
        "message": message or text,
        "remediation": VERIFY,
    }


def _remedy(error: BaseException) -> str:
    code = cast(str, getattr(error, "code", ""))
    if isinstance(error, (packet_receipts.ReceiptError, review_facts.ReviewError)):
        return error.remediation
    if code == "INVALID_PROJECT":
        from bookscan import project_header

        return project_header.HeaderError("INVALID_PROJECT", str(error)).remediation
    if code == "WRITE_FAILED" or getattr(error, "exit_code", 0) == 5:
        return IO_REMEDY
    return cast(str, getattr(error, "remediation", IO_REMEDY))


# An error class can be raised only after its module was imported, so the catch
# list is built from loaded modules and never forces the heavy libraries early.
_PROJECT_ERRORS = (
    ("bookscan.project_header", "HeaderError"),
    ("bookscan.ownership", "OwnershipError"),
    ("bookscan.checkpoints", "CheckpointError"),
    ("bookscan.occurrence_record", "OccurrenceRecordError"),
    ("bookscan.assets", "AssetError"),
    ("bookscan.native_blobs", "BlobError"),
    ("bookscan.packet_descriptors", "DescriptorError"),
)


def _known_errors() -> tuple[type[BaseException], ...]:
    from bookscan import records

    found: list[type[BaseException]] = [
        Interrupted,
        OSError,
        packet_receipts.ReceiptError,
        review_facts.ReviewError,
        records.RecordError,
    ]
    for module, name in _PROJECT_ERRORS:
        loaded = sys.modules.get(module)
        if loaded is not None:
            found.append(getattr(loaded, name))
    return tuple(found)


def _failure(operation: str, error: BaseException, progress: Progress) -> dict[str, object]:
    record = envelope(operation)
    applied = progress.applied
    committed = applied is not None or getattr(error, "committed", False) is True
    context: dict[str, object] = {"phase": "after-checkpoint" if committed else "action"}
    if isinstance(error, Interrupted):
        record.update(
            code="INTERRUPTED",
            exit_code=error.exit_code,
            message=(
                "Action interrupted after its checkpoint was committed."
                if committed
                else "Action interrupted before any checkpoint was committed."
            ),
            remediation=VERIFY if committed else "Nothing was saved; retry the same command.",
        )
    elif isinstance(error, OSError):
        record.update(
            code="WRITE_FAILED",
            exit_code=5,
            message=f"Cannot complete the action: {error}",
            remediation=IO_REMEDY,
        )
    else:
        message = cast(str, getattr(error, "message", None) or str(error))
        remedy = _remedy(error)
        record.update(
            code=getattr(error, "code", "WRITE_FAILED"),
            exit_code=getattr(error, "exit_code", 5),
            message=message,
            remediation=f"{remedy} {VERIFY}" if committed else remedy,
        )
        if isinstance(error, packet_receipts.ReceiptError):
            context["receipt"] = error.context
        if isinstance(error, review_facts.ReviewError):
            for key, value in (("command", error.command), ("reason", error.reason)):
                if value is not None:
                    context[key] = value
            if error.allowed:
                context["allowed"] = list(error.allowed)
    record.update(affected_ids=[], context=context, committed=committed)
    if applied is not None:
        _attach(record, applied)
        record["affected_ids"] = applied.result["affected_ids"]
    return record


def _attach(record: dict[str, object], applied: Applied) -> None:
    result = applied.result
    record.update(
        project_id=applied.project_id,
        review_revision=result["review_revision"],
        snapshot_id=result["snapshot_id"],
        current_review_revision=applied.current_review_revision,
        replayed=applied.replayed,
        checkpoint_revision=result["checkpoint_revision"],
    )
    if applied.checkpoint is not None:
        record["checkpoint_sha256"] = applied.checkpoint.sha256


def _success(operation: str, applied: Applied) -> dict[str, object]:
    record = envelope(operation)
    _attach(record, applied)
    record.update(
        status=applied.result["status"],
        exit_code=0,
        committed=True,
        affected_ids=applied.result["affected_ids"],
        detail=applied.result["detail"],
        warnings=[_warning(item) for item in applied.warnings],
    )
    return record


def _human(record: dict[str, object]) -> str:
    if record["status"] == "error":
        return f"{record['code']}: {record['message']}\n{record['remediation']}\n"
    affected = ", ".join(cast(list[str], record["affected_ids"]))
    again = " (replayed original result)" if record["replayed"] else ""
    verb = "Acknowledged" if record["status"] == "acknowledged" else "Recorded"
    return (
        f"{verb} {str(record['operation']).split('.')[-1]} for {affected}: "
        f"checkpoint {record['checkpoint_revision']}, review revision "
        f"{record['current_review_revision']}{again}.\n"
    )


def run(request: Request, stdout: TextIO, stderr: TextIO, *, delivery: Delivery | None) -> int:
    """Freeze one outcome before delivery; a later signal cannot replace it."""
    control = Control()
    progress = Progress()
    with signals(control):
        try:
            applied = perform(request, control, progress)
            record = _success(request.operation, applied)
            text = _serialize(record, request.json)
            control.check()
        except _known_errors() as error:
            record = _failure(request.operation, error, progress)
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
                    "RESULT_DELIVERY_FAILED: Cannot deliver the action result. Check "
                    "stdout/stderr and verify with bookscan baseline status.\n"
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


def _serialize(record: dict[str, object], json_mode: bool) -> str:
    return (
        json.dumps(record, ensure_ascii=True, allow_nan=False) + "\n"
        if json_mode
        else _human(record)
    )
