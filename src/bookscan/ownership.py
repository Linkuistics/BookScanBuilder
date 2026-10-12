"""Stable kernel writer ownership for local saved projects."""

import errno
import fcntl
import os
import platform
import re
import stat
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Self

LOCK_NAME = "writer.lock"


@dataclass
class OwnershipError(Exception):
    code: str
    message: str
    exit_code: int = 3

    @property
    def remediation(self) -> str:
        if self.code == "PROJECT_BUSY":
            return "Finish the current finite operation or Stop browser review, then retry."
        if self.code == "PROJECT_EXISTS":
            return "Choose a new unused project directory; do not replace its writer lock."
        if self.code == "DEPENDENCY_UNAVAILABLE":
            return "Use the verified macOS local filesystem and Python environment."
        return "Use an intact supported input with bookscan baseline create PDF --workdir NEW."

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True)
class LockIdentity:
    """Native local identity to save in the project header, never reconstruct on resume."""

    project_device: int
    project_inode: int
    lock_device: int
    lock_inode: int
    token: str

    @property
    def content(self) -> bytes:
        return f"BookScanBuilderWriterLock:1\n{self.token}\n".encode("ascii")


def _directory(project: Path) -> tuple[Path, int]:
    if platform.system() != "Darwin":
        raise OwnershipError(
            "DEPENDENCY_UNAVAILABLE", "Project ownership is verified on macOS only.", 5
        )
    descriptor = os.open(
        project.resolve(strict=True), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        # Python 3.12 exposes macOS F_GETPATH; the OS supplies canonical case/parent names.
        # https://docs.python.org/3.12/library/fcntl.html
        raw = fcntl.fcntl(descriptor, fcntl.F_GETPATH, bytes(1024))
        path = Path(os.fsdecode(raw.split(b"\0", 1)[0]))
        if not path.is_absolute():
            raise OwnershipError("INVALID_PROJECT", "No canonical project directory path.")
        return path, descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _stamp(entry: os.stat_result) -> tuple[int, ...]:
    return (
        entry.st_dev,
        entry.st_ino,
        entry.st_mode,
        entry.st_nlink,
        entry.st_size,
        entry.st_mtime_ns,
        entry.st_ctime_ns,
    )


def _remove_failed_lock(
    path: Path,
    directory: int,
    lock: int,
    parent: os.stat_result,
    captured: os.stat_result,
) -> None:
    """Remove only a failed provision's captured entry, never a saved project's lock.

    Held descriptors bind the root and newly created file. Recheck ancestry and
    integer-nanosecond metadata; this is not an adversarial rename-race defense.
    No cancellation callback or directory-content ownership inference occurs.
    """

    def verify_root() -> None:
        current_parent = path.parent.lstat()
        root, named = os.fstat(directory), path.lstat()
        if (
            not stat.S_ISDIR(current_parent.st_mode)
            or (current_parent.st_dev, current_parent.st_ino) != (parent.st_dev, parent.st_ino)
            or not stat.S_ISDIR(named.st_mode)
            or (root.st_dev, root.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise OwnershipError("INVALID_PROJECT", "Bootstrap root or parent was replaced.")

    verify_root()
    try:
        named = os.stat(LOCK_NAME, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return
    if (
        not stat.S_ISREG(named.st_mode)
        or named.st_nlink != 1
        or _stamp(named) != _stamp(captured)
        or _stamp(os.fstat(lock)) != _stamp(captured)
    ):
        raise OwnershipError("INVALID_PROJECT", "Partial bootstrap lock changed or was replaced.")
    verify_root()
    if _stamp(os.stat(LOCK_NAME, dir_fd=directory, follow_symlinks=False)) != _stamp(captured):
        raise OwnershipError("INVALID_PROJECT", "Partial bootstrap lock changed before removal.")
    # https://docs.python.org/3.12/library/os.html#os.unlink
    os.unlink(LOCK_NAME, dir_fd=directory)


def _close_bootstrap(descriptor: int) -> None:
    selected = sys.exception()
    try:
        os.close(descriptor)
    except OSError as error:
        if selected is None:
            raise OwnershipError("INVALID_PROJECT", "Cannot close bootstrap descriptor.") from error
        selected.add_note("Bootstrap descriptor cleanup: " + str(error))


def provision(project: Path) -> LockIdentity:
    """Provision in a new reservation; failed writes clean only their unchanged own file."""
    directory = lock = -1
    captured: os.stat_result | None = None
    path: Path | None = None
    parent: os.stat_result | None = None
    try:
        path, directory = _directory(project)
        parent = path.parent.lstat()
        lock = os.open(
            LOCK_NAME,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        captured = os.fstat(lock)
        root = os.fstat(directory)
        identity = LockIdentity(
            root.st_dev, root.st_ino, captured.st_dev, captured.st_ino, uuid.uuid4().hex
        )
        os.fchmod(lock, 0o600)
        captured = os.fstat(lock)
        data = identity.content
        while data:
            written = os.write(lock, data)
            if written == 0:
                raise OSError("Zero-length writer lock write.")
            captured = os.fstat(lock)
            data = data[written:]
        os.fsync(lock)
        return identity
    except BaseException as error:
        selected = error
        if isinstance(error, OSError):
            selected = (
                OwnershipError("PROJECT_EXISTS", "Project writer lock already exists.", 4)
                if lock < 0 and isinstance(error, FileExistsError)
                else OwnershipError(
                    "INVALID_PROJECT", f"Cannot provision project ownership: {error}"
                )
            )
        if captured is not None and path is not None and parent is not None:
            try:
                _remove_failed_lock(path, directory, lock, parent, captured)
            except (OSError, OwnershipError) as failure:
                selected.add_note(
                    "Partial writer lock retained; bootstrap cleanup: " + str(failure)
                )
        elif lock >= 0:
            selected.add_note("Partial writer lock retained; cleanup identity unavailable.")
        if selected is error:
            raise
        raise selected from error
    finally:
        try:
            if lock >= 0:
                _close_bootstrap(lock)
        finally:
            if directory >= 0:
                _close_bootstrap(directory)


class Writer:
    """Caller-held ownership; shared operations verify it without reacquiring the lock.

    Context exit closes only owned descriptors and keeps the lock inode in place.
    Never use lockf/process locks, or expose descriptors for children to inherit.
    """

    def __init__(self, path: Path, directory: int, lock: int, identity: LockIdentity) -> None:
        self.path = path
        self.identity = identity
        self._directory = directory
        self._lock = lock
        self._pid = os.getpid()

    @classmethod
    def acquire(cls, project: Path, identity: LockIdentity) -> Self:
        directory = lock = -1
        try:
            path, directory = _directory(project)
            # Nonblocking open also prevents corrupt FIFOs from hanging verification.
            lock = os.open(
                LOCK_NAME,
                os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                dir_fd=directory,
            )
            owner = cls(path, directory, lock, identity)
            owner.verify()
            try:
                # macOS flock has open-file-description lifetime, unlike POSIX lockf.
                # Verify actual close/exec/kill behavior in ownership_processes.py.
                # https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/flock.2.html
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                if error.errno in {errno.EAGAIN, errno.EACCES}:
                    raise OwnershipError(
                        "PROJECT_BUSY", "Project already has a writer.", 4
                    ) from error
                raise OwnershipError(
                    "DEPENDENCY_UNAVAILABLE", f"Cannot obtain native writer ownership: {error}", 5
                ) from error
            owner.verify()
            directory = lock = -1  # Transfer both descriptors to the returned owner.
            return owner
        except OSError as error:
            raise OwnershipError(
                "INVALID_PROJECT", f"Cannot open project ownership: {error}"
            ) from error
        finally:
            if lock >= 0:
                os.close(lock)
            if directory >= 0:
                os.close(directory)

    def verify(self) -> None:
        """Check native identity/content before each operation and again before its commit."""
        if self._lock < 0 or self._directory < 0 or os.getpid() != self._pid:
            raise OwnershipError("INVALID_PROJECT", "Writer ownership is closed or foreign.")
        identity = self.identity
        try:
            root = os.fstat(self._directory)
            current_root = self.path.stat(follow_symlinks=False)
            held = os.fstat(self._lock)
            current = os.stat(LOCK_NAME, dir_fd=self._directory, follow_symlinks=False)
            if (
                not stat.S_ISDIR(current_root.st_mode)
                or (root.st_dev, root.st_ino) != (identity.project_device, identity.project_inode)
                or (current_root.st_dev, current_root.st_ino) != (root.st_dev, root.st_ino)
                or not stat.S_ISREG(held.st_mode)
                or not stat.S_ISREG(current.st_mode)
                or held.st_nlink != 1
                or (held.st_dev, held.st_ino) != (identity.lock_device, identity.lock_inode)
                or (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino)
                or re.fullmatch("[0-9a-f]{32}", identity.token) is None
                or held.st_size != len(identity.content)
                or os.pread(self._lock, 256, 0) != identity.content
            ):
                raise OwnershipError(
                    "INVALID_PROJECT", "Project directory/writer lock was replaced or changed."
                )
        except OSError as error:
            raise OwnershipError(
                "INVALID_PROJECT", f"Cannot verify project ownership: {error}"
            ) from error

    def close(self) -> None:
        # Closing an inherited reference must never issue LOCK_UN on a parent's lock.
        lock, directory = self._lock, self._directory
        self._lock = self._directory = -1
        try:
            if lock >= 0:
                os.close(lock)
        finally:
            if directory >= 0:
                os.close(directory)

    def __enter__(self) -> Self:
        try:
            self.verify()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self.close()
        except OSError as error:
            if exc_value is None:
                raise
            exc_value.add_note("Writer descriptor cleanup: " + str(error))
