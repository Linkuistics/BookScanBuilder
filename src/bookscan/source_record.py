"""Verify saved sole-PDF identity and complete source/page meaning under held ownership.

This record is one input to the complete checkpoint semantic verifier, never a
checkpoint or accepted import by itself. Original identity is descriptive: resume
reads only the fixed project snapshot, with no renderer, estimator or repair.
"""

import json
import os
import re
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from bookscan import intake, records
from bookscan.ownership import Writer

SOURCE_NAME = "source.pdf"
Cancel = Callable[[], None]


@dataclass
class SourceRecordError(Exception):
    message: str
    code: str = "INVALID_PROJECT"
    exit_code: int = 3

    @property
    def remediation(self) -> str:
        return (
            "Use the compatible BookScanBuilder source-record-v1 reader with baseline status "
            "PROJECT; for damaged saved content use bookscan baseline create PDF --workdir NEW "
            "with an intact supported input. Fresh import loses review facts. Without intact "
            "input or a verifiable saved state no recovery is available."
        )

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def _canonical(value: object) -> bytes:
    try:
        # Compare serialized JSON to distinguish true/1 and 300/300.0 in saved meaning.
        # https://docs.python.org/3.12/library/json.html#json.dumps
        raw = json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        records.decode(raw)
        pending = [value]
        while pending:
            item = pending.pop()
            if type(item) is dict:
                mapping = cast(dict[object, object], item)
                if not all(type(key) is str for key in mapping):
                    raise ValueError("Non-string saved key.")
                pending.extend(mapping.values())
            elif type(item) is list:
                pending.extend(cast(list[object], item))
            elif item is not None and type(item) not in (str, bool, int, float):
                raise ValueError("Non-JSON saved value.")
        return raw
    except (ValueError, TypeError, RecursionError, records.RecordError) as error:
        raise SourceRecordError("Invalid source record JSON values.") from error


def _object(value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise SourceRecordError("Saved source field is not an object.")
    return cast(dict[str, object], value)


def _identity(value: object) -> intake.Identity:
    data = _object(value)
    if (
        set(data) != {"device", "inode", "size", "mtime_ns", "ctime_ns"}
        or not all(type(number) is int for number in data.values())
        or cast(int, data["device"]) < 0
        or cast(int, data["inode"]) <= 0
        or cast(int, data["size"]) <= 0
    ):
        raise SourceRecordError("Invalid saved source native identity.")
    return intake.Identity(
        *(cast(int, data[key]) for key in ("device", "inode", "size", "mtime_ns", "ctime_ns"))
    )


def _identity_record(value: intake.Identity) -> dict[str, object]:
    return {
        "device": value.device,
        "inode": value.inode,
        "size": value.size,
        "mtime_ns": value.mtime_ns,
        "ctime_ns": value.ctime_ns,
    }


def page_record(page: intake.Page) -> dict[str, object]:
    """Shared source-page meaning for source and assessed-occurrence verification."""
    geometry, frame, hint = page.geometry, page.frame, page.hint
    return {
        "id": f"occ-{page.source_page:06d}",
        "source_pdf_page": page.source_page,
        "geometry": {
            "boxes": [[str(v) for v in box] for box in geometry.boxes],
            "rotate": geometry.rotate,
            "user_unit": str(geometry.user_unit),
            "physical_points": [str(v) for v in frame.points],
            "pixels": list(frame.pixels),
            "matrix": [str(v) for v in frame.matrix],
            "extent_changed": frame.extent_changed,
        },
        "advisory_hint": (
            {
                "role": hint.role,
                "source_sha256": hint.source_sha256,
                "source_page": hint.source_page,
            }
            if hint
            else None
        ),
    }


def _record(saved: intake.Snapshot) -> dict[str, object]:
    return {
        "format": "BookScanBuilderSource",
        "version": 1,
        "snapshot": SOURCE_NAME,
        "source_sha256": saved.sha256,
        "original_path": str(saved.original_path),
        "original_identity": _identity_record(saved.original_identity),
        "snapshot_identity": _identity_record(saved.private_identity),
        "document": {
            "version": list(saved.document.version),
            "extension_level": saved.document.extension_level,
        },
        "pages": [page_record(page) for page in saved.pages],
    }


def _stamp(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _close(descriptor: int) -> None:
    selected = sys.exception()
    try:
        os.close(descriptor)
    except OSError as error:
        if selected is None:
            raise SourceRecordError("Cannot close saved source descriptor.") from error
        selected.add_note("Saved source descriptor cleanup: " + str(error))


def restore(
    owner: Writer, value: object, *, check_cancel: Cancel = lambda: None
) -> intake.Snapshot:
    """Validate the closed record and rederive every page from exact saved bytes.

    Callers retain their writer and supply records.decode output at nested saved
    inputs. This never acquires ownership again, opens original_path or writes.
    """
    raw = _canonical(value)
    data = _object(value)
    if (
        set(data)
        != {
            "format",
            "version",
            "snapshot",
            "source_sha256",
            "original_path",
            "original_identity",
            "snapshot_identity",
            "document",
            "pages",
        }
        or data["format"] != "BookScanBuilderSource"
        or type(data["version"]) is not int
        or data["version"] != 1
        or data["snapshot"] != SOURCE_NAME
    ):
        raise SourceRecordError("Unsupported saved source fields/format/version.")
    sha, original = data["source_sha256"], data["original_path"]
    if not isinstance(sha, str) or re.fullmatch("[0-9a-f]{64}", sha) is None:
        raise SourceRecordError("Invalid saved source digest.")
    if (
        not isinstance(original, str)
        or "\x00" in original
        or not Path(original).is_absolute()
        or str(Path(original)) != original
    ):
        raise SourceRecordError("Invalid descriptive original source path.")
    identity = _identity(data["snapshot_identity"])
    original_identity = _identity(data["original_identity"])
    if original_identity.size != identity.size or original_identity.file_id == identity.file_id:
        raise SourceRecordError("Original/snapshot source identities conflict.")
    directory = descriptor = -1
    try:
        check_cancel()
        owner.verify()
        # Nonblocking/no-follow open gates FIFOs and symlinks before stream inspection.
        # https://docs.python.org/3.12/library/os.html#os.open
        directory = os.open(owner.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        held = os.fstat(directory)
        if (held.st_dev, held.st_ino) != (
            owner.identity.project_device,
            owner.identity.project_inode,
        ):
            raise SourceRecordError("Project directory was replaced during source read.")
        descriptor = os.open(
            SOURCE_NAME,
            os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=directory,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or intake.Identity.read(before) != identity
        ):
            raise SourceRecordError("Saved source type/links/identity changed.")
        path = owner.path / SOURCE_NAME
        # closefd=False leaves descriptor cleanup with this owner even if inspection fails.
        # https://docs.python.org/3.12/library/functions.html#open
        with open(descriptor, "rb", closefd=False) as stream:
            try:
                document, pages = intake.inspect_saved(
                    stream, path, identity, sha, check_cancel=check_cancel
                )
            except intake.ImportFailure as error:
                raise SourceRecordError("Saved source bytes/support could not verify.") from error
        saved = intake.Snapshot(
            path, sha, Path(original), original_identity, identity, document, pages
        )
        if _canonical(_record(saved)) != raw:
            raise SourceRecordError("Saved source document/occurrence/geometry/provenance changed.")
        check_cancel()
        owner.verify()
        after = os.fstat(descriptor)
        named = os.stat(SOURCE_NAME, dir_fd=directory, follow_symlinks=False)
        if _stamp(before) != _stamp(after) or _stamp(after) != _stamp(named):
            raise SourceRecordError("Saved source changed during verification.")
        return saved
    except OSError as error:
        raise SourceRecordError("Saved source is missing/unreadable.") from error
    finally:
        try:
            if descriptor >= 0:
                _close(descriptor)
        finally:
            if directory >= 0:
                _close(directory)


def restore_json(
    owner: Writer, raw: bytes, *, check_cancel: Cancel = lambda: None
) -> intake.Snapshot:
    try:
        value = records.decode(raw)
    except records.RecordError as error:
        raise SourceRecordError("Invalid saved source JSON.") from error
    return restore(owner, value, check_cancel=check_cancel)


def record(
    owner: Writer, saved: intake.Snapshot, *, check_cancel: Cancel = lambda: None
) -> dict[str, object]:
    """Freeze complete source meaning only after checking it against project bytes."""
    if saved.path != owner.path / SOURCE_NAME:
        raise SourceRecordError("Snapshot is outside the fixed project source path.")
    result = _record(saved)
    restore(owner, result, check_cancel=check_cancel)
    return result
