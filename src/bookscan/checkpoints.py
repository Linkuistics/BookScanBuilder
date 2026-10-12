"""Immutable checkpoint envelopes and atomic current pointers under caller-held ownership.

The required state verifier owns payload meaning and every referenced asset. This
storage boundary is private; an envelope alone is not a complete saved project.
Caught signal handlers must record cancellation, never raise asynchronously.
"""

import hashlib
import json
import os
import re
import signal
import stat
import sys
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Self, cast

from bookscan import records
from bookscan.assets import DirectoryIdentity
from bookscan.ownership import OwnershipError, Writer

CAPABILITIES = ("baseline-rgb-v1", "assessment-v1", "review-records-v1", "snapshot-ack-v1")
Verifier = Callable[[dict[str, object]], None]
Cancel = Callable[[], None]


@dataclass
class CheckpointError(Exception):
    code: str
    message: str
    exit_code: int = 3
    committed: bool = False

    @property
    def remediation(self) -> str:
        if self.code == "STALE_ACTION":
            return "Verify current status and obtain a newly issued view or summary."
        if "capabilit" in self.message or "version" in self.message:
            return (
                "Use a compatible BookScanBuilder reader and its baseline status PROJECT command."
            )
        return (
            "Use an intact supported input with bookscan baseline create PDF --workdir NEW; "
            "fresh import loses review facts. Missing bytes cannot be recovered from a checkpoint."
        )

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _digest(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def _close(descriptor: int) -> None:
    # Preserve a selected failure through cleanup; report a new close failure otherwise.
    # https://docs.python.org/3.12/library/sys.html#sys.exception
    selected = sys.exception()
    try:
        os.close(descriptor)
    except OSError as error:
        if selected is None:
            raise
        selected.add_note("Checkpoint descriptor close: " + str(error))


def _encode(value: dict[str, object]) -> bytes:
    try:
        raw = json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        records.decode(raw)
        return raw
    except (TypeError, ValueError, RecursionError, records.RecordError) as error:
        raise CheckpointError("INVALID_PROJECT", "Invalid checkpoint JSON state.") from error


@dataclass(frozen=True)
class Checkpoint:
    sha256: str
    raw: bytes
    revision: int
    previous: str | None

    @property
    def state(self) -> dict[str, object]:
        # Return a fresh object so verifier/caller mutation cannot change saved bytes.
        return cast(dict[str, object], records.decode(self.raw)["state"])


@dataclass(frozen=True)
class CommitResult:
    checkpoint: Checkpoint
    committed: bool = True
    warnings: tuple[str, ...] = ()


class Checkpoints:
    """Keep all predecessors; never enumerate private files as recoverable state.

    Provision is only for a new create reservation. Resume consumes its saved
    directory identity, not a fresh stat. The current pointer is a digest-only
    relative symlink, deliberately read without following filesystem links.
    """

    def __init__(self, owner: Writer, identity: DirectoryIdentity) -> None:
        self.owner = owner
        self.identity = identity

    @classmethod
    def provision(cls, owner: Writer) -> Self:
        from bookscan.project_reservation import provision_store

        owner.verify()
        try:
            with provision_store(owner, "checkpoints") as info:
                result = cls(owner, DirectoryIdentity(info.st_dev, info.st_ino))
                with result._directory():
                    pass
                return result
        except OSError as error:
            raise CheckpointError(
                "WRITE_FAILED", "Cannot reserve checkpoint directory.", 5
            ) from error

    def _verify(self, directory: int) -> None:
        self.owner.verify()
        try:
            held = os.fstat(directory)
            current = (self.owner.path / "checkpoints").lstat()
        except OSError as error:
            raise CheckpointError(
                "INVALID_PROJECT", "Checkpoint directory is missing/unreadable."
            ) from error
        expected = (self.identity.device, self.identity.inode)
        if (
            not stat.S_ISDIR(current.st_mode)
            or (held.st_dev, held.st_ino) != expected
            or (current.st_dev, current.st_ino) != expected
        ):
            raise CheckpointError("INVALID_PROJECT", "Checkpoint directory was replaced.")

    @contextmanager
    def _directory(self) -> Iterator[int]:
        self.owner.verify()
        descriptor = -1
        try:
            try:
                descriptor = os.open(
                    self.owner.path / "checkpoints",
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                )
                self._verify(descriptor)
            except OSError as error:
                raise CheckpointError(
                    "INVALID_PROJECT", "Cannot verify checkpoint directory."
                ) from error
            yield descriptor
            self._verify(descriptor)
        finally:
            if descriptor >= 0:
                _close(descriptor)

    def _pointer(self, directory: int, name: str = "current") -> tuple[str, tuple[int, ...]] | None:
        try:
            return self._pointer_value(directory, name)
        except OSError as error:
            raise CheckpointError(
                "INVALID_PROJECT", "Current checkpoint pointer is unreadable."
            ) from error

    def _pointer_value(self, directory: int, name: str) -> tuple[str, tuple[int, ...]] | None:
        try:
            before = os.stat(name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if not stat.S_ISLNK(before.st_mode) or before.st_nlink != 1:
            raise CheckpointError("INVALID_PROJECT", "Invalid current checkpoint pointer type.")
        target = os.readlink(name, dir_fd=directory)
        if re.fullmatch("[0-9a-f]{64}\\.json", target) is None:
            raise CheckpointError("INVALID_PROJECT", "Invalid current checkpoint pointer target.")
        after = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if _identity(before) != _identity(after):
            raise CheckpointError(
                "INVALID_PROJECT", "Current checkpoint pointer changed during read."
            )
        return target[:-5], _identity(after)

    def _parse(self, raw: bytes) -> Checkpoint:
        try:
            data = records.decode(raw)
        except records.RecordError as error:
            raise CheckpointError("INVALID_PROJECT", "Invalid checkpoint JSON.") from error
        fields = {
            "format",
            "version",
            "project_id",
            "required_capabilities",
            "checkpoint_revision",
            "previous_sha256",
            "state",
        }
        if (
            set(data) != fields
            or data["format"] != "BookScanBuilderProject"
            or type(data["version"]) is not int
            or data["version"] != 1
        ):
            raise CheckpointError(
                "INVALID_PROJECT", "Unsupported checkpoint fields/format/version."
            )
        capabilities = data["required_capabilities"]
        if (
            not isinstance(capabilities, list)
            or len(cast(list[object], capabilities)) != len(CAPABILITIES)
            or not all(isinstance(v, str) for v in cast(list[object], capabilities))
            or set(cast(list[str], capabilities)) != set(CAPABILITIES)
        ):
            raise CheckpointError(
                "INVALID_PROJECT", "Unsupported required checkpoint capabilities."
            )
        revision, previous = data["checkpoint_revision"], data["previous_sha256"]
        if (
            data["project_id"] != "project-" + self.owner.identity.token
            or type(revision) is not int
            or revision < 1
            or (previous is not None and not _digest(previous))
            or (revision == 1) != (previous is None)
            or not isinstance(data["state"], dict)
        ):
            raise CheckpointError("INVALID_PROJECT", "Invalid checkpoint project/revision/state.")
        return Checkpoint(
            hashlib.sha256(raw).hexdigest(), raw, revision, cast(str | None, previous)
        )

    def _read(self, directory: int, digest: str, check_cancel: Cancel) -> Checkpoint:
        descriptor = -1
        try:
            name = digest + ".json"
            descriptor = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory
            )
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise CheckpointError("INVALID_PROJECT", "Invalid checkpoint file type/link count.")
            chunks: list[bytes] = []
            remaining = before.st_size
            while remaining:
                check_cancel()
                chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                if not chunk:
                    raise CheckpointError("INVALID_PROJECT", "Truncated checkpoint file.")
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            after = os.fstat(descriptor)
            current = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if (
                _identity(before) != _identity(after)
                or _identity(after) != _identity(current)
                or hashlib.sha256(raw).hexdigest() != digest
            ):
                raise CheckpointError(
                    "INVALID_PROJECT", "Checkpoint file changed or digest mismatched."
                )
            return self._parse(raw)
        except OSError as error:
            raise CheckpointError(
                "INVALID_PROJECT", "Checkpoint file missing/unreadable."
            ) from error
        finally:
            if descriptor >= 0:
                _close(descriptor)

    def _load(self, directory: int, verify_state: Verifier, check_cancel: Cancel) -> Checkpoint:
        pointer = self._pointer(directory)
        if pointer is None:
            raise CheckpointError("INVALID_PROJECT", "No committed checkpoint; incomplete create.")
        checkpoint = self._read(directory, pointer[0], check_cancel)
        current = checkpoint
        while True:
            check_cancel()
            verify_state(current.state)
            if current.previous is None:
                break
            previous = self._read(directory, current.previous, check_cancel)
            if previous.revision != current.revision - 1:
                raise CheckpointError(
                    "INVALID_PROJECT", "Nonmonotonic checkpoint predecessor chain."
                )
            current = previous
        if self._pointer(directory) != pointer:
            raise CheckpointError(
                "INVALID_PROJECT", "Current checkpoint changed during verification."
            )
        self._verify(directory)
        return checkpoint

    def load(self, *, verify_state: Verifier, check_cancel: Cancel = lambda: None) -> Checkpoint:
        check_cancel()
        with self._directory() as directory:
            return self._load(directory, verify_state, check_cancel)

    def _publish(self, directory: int, checkpoint: Checkpoint, check_cancel: Cancel) -> None:
        private = ".checkpoint-" + uuid.uuid4().hex
        descriptor = -1
        owned: tuple[int, int] | None = None
        try:
            descriptor = os.open(
                private,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
                dir_fd=directory,
            )
            info = os.fstat(descriptor)
            owned = (info.st_dev, info.st_ino)
            data = memoryview(checkpoint.raw)
            while data:
                check_cancel()
                written = os.write(descriptor, data)
                if written == 0:
                    raise OSError("Zero-length checkpoint write")
                data = data[written:]
            os.fsync(descriptor)
            check_cancel()
            self._verify(directory)
            try:
                # Publish a complete immutable record; not yet a saved current state.
                # https://docs.python.org/3.12/library/os.html#os.link
                os.link(
                    private,
                    checkpoint.sha256 + ".json",
                    src_dir_fd=directory,
                    dst_dir_fd=directory,
                    follow_symlinks=False,
                )
            except FileExistsError:
                existing = self._read(directory, checkpoint.sha256, check_cancel)
                if existing != checkpoint:
                    raise CheckpointError("INVALID_PROJECT", "Occupied checkpoint differs.")
        except BaseException as error:
            try:
                if owned is not None:
                    self._unlink(directory, private, owned)
                    owned = None
            except (OSError, CheckpointError) as failure:
                error.add_note("Checkpoint cleanup: " + str(failure))
            raise
        else:
            self._unlink(directory, private, owned)
            owned = None
        finally:
            if descriptor >= 0:
                _close(descriptor)
        if self._read(directory, checkpoint.sha256, check_cancel) != checkpoint:
            raise CheckpointError("INVALID_PROJECT", "Published checkpoint bytes differ.")

    def _unlink(self, directory: int, name: str, owned: tuple[int, int]) -> None:
        current = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != owned:
            raise CheckpointError("INVALID_PROJECT", "Private checkpoint cleanup name replaced.")
        os.unlink(name, dir_fd=directory)

    def commit(
        self,
        state: dict[str, object],
        *,
        expected: Checkpoint | None,
        verify_state: Verifier,
        check_cancel: Cancel = lambda: None,
    ) -> CommitResult:
        """Verify predecessor/assets, publish bytes, then atomically choose that record.

        A return fixes commitment; caller checks recorded signals afterward and
        returns 130/143 with committed true. No export-style successful signal exit.
        """
        committed = False
        checkpoint: Checkpoint | None = None
        private: str | None = None
        private_identity: tuple[int, int] | None = None
        try:
            with self._directory() as directory:
                check_cancel()
                pointer = self._pointer(directory)
                current = self._load(directory, verify_state, check_cancel) if pointer else None
                if current != expected:
                    raise CheckpointError(
                        "STALE_ACTION", "Expected checkpoint is no longer current.", 6
                    )
                checkpoint = self._parse(
                    _encode(
                        {
                            "format": "BookScanBuilderProject",
                            "version": 1,
                            "project_id": "project-" + self.owner.identity.token,
                            "required_capabilities": list(CAPABILITIES),
                            "checkpoint_revision": 1 if current is None else current.revision + 1,
                            "previous_sha256": None if current is None else current.sha256,
                            "state": state,
                        }
                    )
                )
                verify_state(checkpoint.state)
                check_cancel()
                self._publish(directory, checkpoint, check_cancel)
                target = checkpoint.sha256 + ".json"
                if pointer is not None:
                    private = ".current-" + uuid.uuid4().hex
                    os.symlink(target, private, dir_fd=directory)
                    staged = self._pointer(directory, private)
                    if staged is None or staged[0] != checkpoint.sha256:
                        raise CheckpointError(
                            "INVALID_PROJECT", "Private checkpoint pointer was replaced."
                        )
                    private_identity = (staged[1][0], staged[1][1])
                self._verify(directory)
                if self._pointer(directory) != pointer:
                    raise CheckpointError(
                        "INVALID_PROJECT", "Current pointer was replaced before commit."
                    )
                check_cancel()
                # Only the pointer syscall and outcome assignment are deferred.
                # https://docs.python.org/3.12/library/signal.html#signal.pthread_sigmask
                mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
                try:
                    check_cancel()
                    if signal.sigpending() & {signal.SIGINT, signal.SIGTERM}:
                        raise CheckpointError(
                            "INTERRUPTED",
                            "Pending signal before checkpoint commit.",
                            128 + min(signal.sigpending() & {signal.SIGINT, signal.SIGTERM}),
                        )
                    if pointer is None:
                        # Creation is atomic and refuses an occupied/dangling name.
                        # https://docs.python.org/3.12/library/os.html#os.symlink
                        try:
                            os.symlink(target, "current", dir_fd=directory)
                        except FileExistsError as error:
                            raise CheckpointError(
                                "INVALID_PROJECT",
                                "Current pointer became occupied before create commit.",
                            ) from error
                    else:
                        # Only the verified current pointer is replaceable, not records.
                        # https://docs.python.org/3.12/library/os.html#os.replace
                        os.replace(
                            cast(str, private),
                            "current",
                            src_dir_fd=directory,
                            dst_dir_fd=directory,
                        )
                        private = None
                    committed = True
                finally:
                    signal.pthread_sigmask(signal.SIG_SETMASK, mask)
                return CommitResult(checkpoint)
        except BaseException as error:
            if private is not None and private_identity is not None:
                try:
                    with self._directory() as directory:
                        self._unlink(directory, private, private_identity)
                except (OSError, CheckpointError, OwnershipError) as failure:
                    error.add_note("Checkpoint pointer cleanup: " + str(failure))
            if isinstance(error, CheckpointError):
                error.committed = committed
            elif isinstance(error, OwnershipError) and committed:
                raise CheckpointError(error.code, error.message, error.exit_code, True) from error
            elif isinstance(error, OSError):
                if committed and checkpoint is not None:
                    return CommitResult(
                        checkpoint, warnings=("CHECKPOINT_CLEANUP_FAILED: " + str(error),)
                    )
                raise CheckpointError(
                    "WRITE_FAILED", "Cannot commit checkpoint.", 5, committed
                ) from error
            raise
