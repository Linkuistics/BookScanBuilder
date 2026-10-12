"""Immutable opaque native channels, profiles and palettes under caller-held ownership.

Directory identity and complete blob references belong to the checkpoint/header
owner. A published blob alone is never saved review state. Resume neither
enumerates private orphans nor repairs damaged entries. Profiles stay uninterpreted.
"""

import hashlib
import os
import re
import stat
import sys
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Self, cast

from bookscan.assets import DirectoryIdentity
from bookscan.import_publications import Publications
from bookscan.ownership import Writer

Cancel = Callable[[], None]


@dataclass
class BlobError(Exception):
    code: str
    message: str
    exit_code: int = 3

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def _identity(info: os.stat_result) -> tuple[int, ...]:
    # atime can advance on an ordinary read; content/entry identities cannot.
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
            raise
        selected.add_note("Native blob descriptor close: " + str(error))


@dataclass(frozen=True)
class Blob:
    sha256: str
    byte_size: int

    def verify(self) -> None:
        if (
            type(self.sha256) is not str
            or re.fullmatch("[0-9a-f]{64}", self.sha256) is None
            or type(self.byte_size) is not int
            or self.byte_size < 0
        ):
            raise BlobError("INVALID_PROJECT", "Invalid native blob reference.")

    def record(self) -> dict[str, object]:
        self.verify()
        return {
            "format": "BookScanBuilderNativeBlob",
            "version": 1,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
        }

    @classmethod
    def from_record(cls, value: object) -> Self:
        if type(value) is not dict:
            raise BlobError("INVALID_PROJECT", "Native blob reference must be an object.")
        data = cast(dict[str, object], value)
        if (
            set(data) != {"format", "version", "sha256", "byte_size"}
            or data["format"] != "BookScanBuilderNativeBlob"
            or type(data["version"]) is not int
            or data["version"] != 1
        ):
            raise BlobError("INVALID_PROJECT", "Unsupported native blob fields/version.")
        result = cls(cast(str, data["sha256"]), cast(int, data["byte_size"]))
        result.verify()
        return result


class Blobs:
    """Exact byte store; acquisition and sample/placement meaning stay with the caller."""

    def __init__(self, owner: Writer, identity: DirectoryIdentity) -> None:
        self.owner = owner
        self.identity = identity
        self.publications: Publications | None = None

    @classmethod
    def provision(cls, owner: Writer) -> Self:
        from bookscan.project_reservation import provision_store

        owner.verify()
        try:
            with provision_store(owner, "native-blobs") as info:
                result = cls(owner, DirectoryIdentity(info.st_dev, info.st_ino))
                with result._directory():
                    pass
                return result
        except OSError as error:
            raise BlobError(
                "WRITE_FAILED", "Cannot reserve unused native blobs directory.", 5
            ) from error

    def _verify_directory(self, descriptor: int) -> None:
        self.owner.verify()
        held = os.fstat(descriptor)
        current = (self.owner.path / "native-blobs").lstat()
        expected = (self.identity.device, self.identity.inode)
        if (
            not stat.S_ISDIR(current.st_mode)
            or (held.st_dev, held.st_ino) != expected
            or (current.st_dev, current.st_ino) != expected
        ):
            raise BlobError("INVALID_PROJECT", "Native blobs directory was replaced.")

    @contextmanager
    def _directory(self) -> Iterator[int]:
        self.owner.verify()
        descriptor = -1
        try:
            descriptor = os.open(
                self.owner.path / "native-blobs",
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            self._verify_directory(descriptor)
            yield descriptor
            self._verify_directory(descriptor)
        except OSError as error:
            raise BlobError("INVALID_PROJECT", "Cannot verify native blobs directory.") from error
        finally:
            if descriptor >= 0:
                _close(descriptor)

    def _read(
        self, directory: int, reference: Blob, check_cancel: Cancel, *, name: str | None = None
    ) -> bytes:
        name = reference.sha256 + ".bin" if name is None else name
        descriptor = -1
        try:
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                dir_fd=directory,
            )
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size != reference.byte_size
            ):
                raise BlobError("INVALID_PROJECT", "Native blob file type/links/size changed.")
            chunks: list[bytes] = []
            remaining = reference.byte_size
            while remaining:
                check_cancel()
                chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                if not chunk:
                    raise BlobError("INVALID_PROJECT", "Native blob is truncated.")
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            if hashlib.sha256(raw).hexdigest() != reference.sha256:
                raise BlobError(
                    "INVALID_PROJECT", "Native blob digest differs from retained bytes."
                )
            check_cancel()
            after = os.fstat(descriptor)
            current = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if _identity(before) != _identity(after) or _identity(after) != _identity(current):
                raise BlobError("INVALID_PROJECT", "Native blob changed during verification.")
            self._verify_directory(directory)
            return raw
        except OSError as error:
            raise BlobError("INVALID_PROJECT", "Native blob is missing or unreadable.") from error
        finally:
            if descriptor >= 0:
                _close(descriptor)

    def read(self, reference: Blob, *, check_cancel: Cancel = lambda: None) -> bytes:
        self.owner.verify()
        reference.verify()
        check_cancel()
        with self._directory() as directory:
            return self._read(directory, reference, check_cancel)

    def publish(self, raw: bytes, *, check_cancel: Cancel = lambda: None) -> Blob:
        self.owner.verify()
        check_cancel()
        if type(raw) is not bytes:
            raise BlobError("WRITE_FAILED", "Native blob requires immutable complete bytes.", 5)
        reference = Blob(hashlib.sha256(raw).hexdigest(), len(raw))
        with self._directory() as directory:
            if self.publications is not None:
                self.publications.verify(directory)
            name = reference.sha256 + ".bin"
            private = ".blob-" + uuid.uuid4().hex
            descriptor = -1
            owned = False
            published = False

            def cleanup() -> None:
                if not owned:
                    return
                try:
                    held = os.fstat(descriptor)
                    current = os.stat(private, dir_fd=directory, follow_symlinks=False)
                    if (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino):
                        raise BlobError(
                            "WRITE_FAILED", "Private native blob cleanup name replaced.", 5
                        )
                    expected = _identity(held)
                    try:
                        os.unlink(private, dir_fd=directory)
                    except OSError as error:
                        if self.publications is not None:
                            try:
                                self.publications.refused(
                                    directory,
                                    descriptor,
                                    private,
                                    expected,
                                    linked_name=name if published else None,
                                )
                            except OSError as failure:
                                error.add_note("Private ownership capture: " + str(failure))
                        raise
                except OSError as error:
                    raise BlobError(
                        "WRITE_FAILED", "Cannot clean owned private native blob.", 5
                    ) from error

            try:
                descriptor = os.open(
                    private,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                    dir_fd=directory,
                )
                owned = True
                view = memoryview(raw)
                while view:
                    check_cancel()
                    written = os.write(descriptor, view)
                    if written == 0:
                        raise OSError("Zero-length native blob write.")
                    view = view[written:]
                os.fsync(descriptor)
                check_cancel()
                self._read(directory, reference, check_cancel, name=private)
                self._verify_directory(directory)
                try:
                    # Atomic no-clobber publication; a blob is not a checkpoint.
                    # https://docs.python.org/3.12/library/os.html#os.link
                    os.link(
                        private,
                        name,
                        src_dir_fd=directory,
                        dst_dir_fd=directory,
                        follow_symlinks=False,
                    )
                    published = True
                except FileExistsError:
                    self._read(directory, reference, check_cancel)
            except BaseException as error:
                try:
                    cleanup()
                    if owned and self.publications is not None:
                        if published:
                            self.publications.completed(directory, descriptor, name, created=True)
                        else:
                            self.publications.aborted(directory)
                except (BlobError, OSError) as failure:
                    error.add_note("Native blob cleanup: " + str(failure))
                if isinstance(error, OSError):
                    raise BlobError(
                        "WRITE_FAILED", "Cannot publish complete native blob.", 5
                    ) from error
                raise
            else:
                cleanup()
                if self.publications is not None:
                    self.publications.completed(directory, descriptor, name, created=published)
            finally:
                if descriptor >= 0:
                    _close(descriptor)
            self._read(directory, reference, check_cancel)
        return reference
