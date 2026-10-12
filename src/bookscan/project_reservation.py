"""Exclusive new-project name reservation; never infer ownership from directory contents.

The import owner publishes/cleans its known source, stores and private names. This
boundary removes a verified empty reservation or one exact owned regular file
or empty child directory selected by the import owner. It never discovers children
to clean, and no reservation is saved state.
"""

import fcntl
import os
import platform
import stat
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Self

from bookscan.ownership import OwnershipError, Writer
from bookscan.project_header import HEADER_NAME, HeaderError


class ReservationError(HeaderError):
    @property
    def remediation(self) -> str:
        if self.code == "OUTPUT_DIRECTORY_INVALID":
            return "Choose an unused project name in an existing readable parent directory."
        if self.code == "DEPENDENCY_UNAVAILABLE":
            return "Use the supported macOS local filesystem and Python 3.12 environment."
        return super().remediation


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _file_stamp(info: os.stat_result) -> tuple[int, ...]:
    # stat_result tuple equality loses sub-float timestamp changes. Compare ns
    # fields explicitly; reading may change atime without changing ownership.
    # https://docs.python.org/3.12/library/os.html#os.stat_result
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _canonical(descriptor: int) -> Path:
    # Python 3.12 provides macOS F_GETPATH; keep case and symlink-parent aliases
    # on the same OS-resolved native identity, as the writer already does.
    # https://docs.python.org/3.12/library/fcntl.html
    raw = fcntl.fcntl(descriptor, fcntl.F_GETPATH, bytes(1024))
    path = Path(os.fsdecode(raw.split(b"\0", 1)[0]))
    if not path.is_absolute():
        raise ReservationError("INVALID_PROJECT", "No canonical reservation directory path.")
    return path


def _close(descriptor: int) -> None:
    selected = sys.exception()
    try:
        os.close(descriptor)
    except OSError as failure:
        if selected is None:
            raise ReservationError(
                "WRITE_FAILED", "Cannot close reservation descriptor.", 5
            ) from failure
        selected.add_note("Reservation descriptor cleanup: " + str(failure))


class Reservation:
    """Hold root/parent identities until import completion or owned cleanup.

    Normal context exit keeps the directory and closes only these descriptors.
    Exceptional exit attempts empty-only cleanup, preserving the selected error.
    This carries no checkpoint commitment. File removal requires an explicit
    single name and the operation owner's captured-identity predicate.
    """

    def __init__(self, parent: int, directory: int, path: Path) -> None:
        self.path = path
        self._parent = parent
        self._directory = directory
        self._parent_identity = _identity(os.fstat(parent))
        self._identity = _identity(os.fstat(directory))
        self._pid = os.getpid()

    def verify(self) -> None:
        if self._parent < 0 or self._directory < 0 or self._pid != os.getpid():
            raise ReservationError("INVALID_PROJECT", "Reservation is closed or foreign.")
        try:
            parent = self.path.parent.lstat()
            named = os.stat(self.path.name, dir_fd=self._parent, follow_symlinks=False)
            current = self.path.lstat()
            if (
                not stat.S_ISDIR(parent.st_mode)
                or not stat.S_ISDIR(named.st_mode)
                or not stat.S_ISDIR(current.st_mode)
                or _identity(parent) != self._parent_identity
                or _identity(os.fstat(self._parent)) != self._parent_identity
                or _identity(named) != self._identity
                or _identity(current) != self._identity
                or _identity(os.fstat(self._directory)) != self._identity
            ):
                raise ReservationError("INVALID_PROJECT", "Reservation or its parent was replaced.")
        except OSError as error:
            raise ReservationError(
                "INVALID_PROJECT", "Cannot verify reservation identity."
            ) from error

    def remove_empty(self) -> None:
        """Remove this name only while its native identity still names an empty root.

        No enumeration/recursive deletion: even an unexpected empty child prevents
        removal. The full create owner must first clean its own known entries.
        """
        self.verify()
        try:
            # rmdir refuses nonempty directories; dir_fd binds removal to the held
            # parent. Local concurrent replacement is checked before the syscall;
            # this is not a defense against an adversarial same-user rename race.
            # https://docs.python.org/3.12/library/os.html#os.rmdir
            os.rmdir(self.path.name, dir_fd=self._parent)
        except OSError as error:
            raise ReservationError(
                "WRITE_FAILED", "Reservation retained; cannot safely remove its empty root.", 5
            ) from error

    def remove_file(self, name: str, *, matches: Callable[[os.stat_result], bool]) -> None:
        """Remove one unchanged owned regular file, relative to the held root.

        The caller must compare its captured creation identity, never just a
        filename or content digest. Missing names are already clean. Links,
        nonregular/replaced entries and unknown children are never removed.
        Like remove_empty, this is not an adversarial same-user rename defense.
        """
        self.verify()
        if not name or name in {".", ".."} or "/" in name or "\0" in name:
            raise ReservationError("INVALID_PROJECT", "Cleanup requires one file name, not a path.")
        try:
            try:
                entry = os.stat(name, dir_fd=self._directory, follow_symlinks=False)
            except FileNotFoundError:
                return
            if not stat.S_ISREG(entry.st_mode) or entry.st_nlink != 1 or not matches(entry):
                raise ReservationError(
                    "INVALID_PROJECT", "Owned cleanup file changed or was replaced."
                )
            self.verify()
            # Recheck native metadata after the caller's predicate; bind the
            # unlink to the held directory and never follow a replacement link.
            # https://docs.python.org/3.12/library/os.html#os.stat
            current = os.stat(name, dir_fd=self._directory, follow_symlinks=False)
            if _file_stamp(current) != _file_stamp(entry):
                raise ReservationError(
                    "INVALID_PROJECT", "Owned cleanup file changed before removal."
                )
            # https://docs.python.org/3.12/library/os.html#os.unlink
            os.unlink(name, dir_fd=self._directory)
        except OSError as error:
            raise ReservationError(
                "WRITE_FAILED", "Cannot remove owned cleanup file.", 5
            ) from error

    def remove_directory(self, name: str, *, matches: Callable[[os.stat_result], bool]) -> None:
        """Remove one unchanged owned empty child, relative to the held root.

        The caller supplies its captured native identity. Never infer ownership
        from a name or contents. Missing names are already clean; unknown children
        prevent removal. Like remove_empty, this is not an adversarial same-user
        rename defense. This operation checks no cancellation callback.
        """
        self.verify()
        if not name or name in {".", ".."} or "/" in name or "\0" in name:
            raise ReservationError("INVALID_PROJECT", "Cleanup requires one directory name.")
        try:
            try:
                entry = os.stat(name, dir_fd=self._directory, follow_symlinks=False)
            except FileNotFoundError:
                return
            if not stat.S_ISDIR(entry.st_mode) or not matches(entry):
                raise ReservationError(
                    "INVALID_PROJECT", "Owned cleanup directory changed or was replaced."
                )
            self.verify()
            current = os.stat(name, dir_fd=self._directory, follow_symlinks=False)
            if _file_stamp(current) != _file_stamp(entry):
                raise ReservationError(
                    "INVALID_PROJECT", "Owned cleanup directory changed before removal."
                )
            # The kernel refuses a nonempty child, including one populated after
            # the identity recheck. dir_fd binds this one name to our held root.
            # https://docs.python.org/3.12/library/os.html#os.rmdir
            os.rmdir(name, dir_fd=self._directory)
        except OSError as error:
            raise ReservationError(
                "WRITE_FAILED", "Cannot remove owned empty cleanup directory.", 5
            ) from error

    def close(self) -> None:
        directory, parent = self._directory, self._parent
        self._directory = self._parent = -1
        try:
            if directory >= 0:
                _close(directory)
        finally:
            if parent >= 0:
                _close(parent)

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
        if exc_value is not None:
            try:
                self.remove_empty()
            except HeaderError as failure:
                exc_value.add_note("Reservation retained; cleanup: " + str(failure))
        self.close()


def _rollback_closed_store(
    owner: Writer,
    name: str,
    parent_identity: tuple[int, int],
    captured: os.stat_result,
    error: BaseException,
) -> None:
    """Reopen verified ancestry after original closes; never retry their fd numbers."""
    parent = directory = -1
    try:
        owner.verify()
        # Reopen rather than retry a failed close: its descriptor may be reused.
        # https://docs.python.org/3.12/library/os.html#os.close
        parent = os.open(
            owner.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        if _identity(os.fstat(parent)) != parent_identity:
            raise ReservationError("INVALID_PROJECT", "Store creation parent was replaced.")
        directory = os.open(
            owner.path.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent,
        )
        reservation = Reservation(parent, directory, owner.path)
        reservation.verify()
        owner.verify()
        try:
            os.stat(HEADER_NAME, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            stamp = _file_stamp(captured)

            def matches(entry: os.stat_result) -> bool:
                owner.verify()
                return _file_stamp(entry) == stamp

            reservation.remove_directory(name, matches=matches)
        else:
            error.add_note(f"{name} store retained; project header is occupied.")
    except (OSError, HeaderError, OwnershipError) as failure:
        error.add_note(f"{name} store retained; cleanup: {failure}")
    finally:
        try:
            if directory >= 0:
                _close(directory)
        finally:
            if parent >= 0:
                _close(parent)


@contextmanager
def provision_store(owner: Writer, name: str) -> Iterator[os.stat_result]:
    """Create one store and roll back a failed initialization under held ownership.

    Only the captured unchanged empty name is removable. Unknown capture,
    changed ancestry and an existing header retain it for the import owner.
    No cancellation callback or child discovery runs during cleanup.
    """
    owner.verify()
    if not name or name in {".", ".."} or "/" in name or "\0" in name:
        raise ReservationError("INVALID_PROJECT", "Store creation requires one directory name.")
    parent = directory = -1
    reservation: Reservation | None = None
    created = False
    captured: os.stat_result | None = None
    parent_identity: tuple[int, int] | None = None
    try:
        parent = os.open(
            owner.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        parent_identity = _identity(os.fstat(parent))
        directory = os.open(
            owner.path.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent,
        )
        reservation = Reservation(parent, directory, owner.path)
        reservation.verify()
        owner.verify()
        # Bind creation/capture to the verified root, not a re-resolved path.
        # https://docs.python.org/3.12/library/os.html#os.mkdir
        os.mkdir(name, 0o700, dir_fd=directory)
        created = True
        captured = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISDIR(captured.st_mode):
            raise ReservationError("INVALID_PROJECT", "Created store is not a directory.")
        owner.verify()
        reservation.verify()
        yield captured
    except BaseException as error:
        if created and reservation is not None:
            if captured is None:
                error.add_note(f"{name} store retained; creation identity was not captured.")
            else:
                try:
                    owner.verify()
                    reservation.verify()
                    try:
                        os.stat(HEADER_NAME, dir_fd=directory, follow_symlinks=False)
                    except FileNotFoundError:
                        stamp = _file_stamp(captured)

                        def matches(entry: os.stat_result) -> bool:
                            owner.verify()
                            return _file_stamp(entry) == stamp

                        reservation.remove_directory(name, matches=matches)
                    else:
                        error.add_note(f"{name} store retained; project header is occupied.")
                except (OSError, HeaderError, OwnershipError) as failure:
                    error.add_note(f"{name} store retained; cleanup: {failure}")
        raise
    finally:
        selected = sys.exception()
        try:
            try:
                if directory >= 0:
                    _close(directory)
            finally:
                if parent >= 0:
                    _close(parent)
        except BaseException as error:
            if selected is None and captured is not None and parent_identity is not None:
                _rollback_closed_store(owner, name, parent_identity, captured, error)
            raise


def reserve(project: Path, *, check_cancel: Callable[[], None] = lambda: None) -> Reservation:
    """Exclusively reserve an unused name in an existing canonical parent on macOS.

    A caught error cleans only a verified empty reservation. A kill may leave an
    occupied incomplete name; a subsequent create must choose a new destination.
    """
    check_cancel()
    if platform.system() != "Darwin":
        raise ReservationError(
            "DEPENDENCY_UNAVAILABLE", "Project reservation is verified on macOS only.", 5
        )
    parent = directory = -1
    reservation: Reservation | None = None
    created = False
    try:
        selected = project.expanduser().absolute()
        if not selected.name:
            raise ReservationError("PROJECT_EXISTS", "Filesystem root is already occupied.", 4)
        try:
            parent = os.open(
                selected.parent.resolve(strict=True),
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            path = _canonical(parent) / selected.name
        except (OSError, RuntimeError) as error:
            raise ReservationError(
                "OUTPUT_DIRECTORY_INVALID",
                "Project parent must be an existing readable directory.",
                4,
            ) from error
        check_cancel()
        try:
            # mkdir fails for any occupied name, including a dangling symlink.
            # https://docs.python.org/3.12/library/os.html#os.mkdir
            os.mkdir(path.name, 0o700, dir_fd=parent)
            created = True
        except FileExistsError as error:
            raise ReservationError(
                "PROJECT_EXISTS", "Project destination is already occupied.", 4
            ) from error
        except OSError as error:
            raise ReservationError(
                "WRITE_FAILED", "Cannot create project reservation.", 5
            ) from error
        try:
            directory = os.open(
                path.name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent,
            )
            opened_directory = directory
            reservation = Reservation(parent, directory, path)
            parent = directory = -1  # Transfer ownership before cancellable verification.
            reservation.verify()
            # umask may remove requested bits; make the new private root usable.
            os.fchmod(opened_directory, 0o700)
        except OSError as error:
            raise ReservationError(
                "WRITE_FAILED", "Cannot open private project reservation.", 5
            ) from error
        check_cancel()
        return reservation
    except BaseException as error:
        if reservation is not None:
            reservation.__exit__(type(error), error, error.__traceback__)
        elif created:
            # No captured root identity: the name cannot safely be deleted.
            error.add_note("Reservation retained; root identity was not captured.")
        raise
    finally:
        try:
            if directory >= 0:
                _close(directory)
        finally:
            if parent >= 0:
                _close(parent)
