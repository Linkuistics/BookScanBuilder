"""Immutable packet descriptors under caller-held project ownership.

A receipt carries only its issued packet ID, so the project stores each descriptor
as ``<packet-id>.<sha256>.json``: the content address is the file's own digest and
the packet ID makes lookup exact without a second index to keep in step. A
descriptor is a presentation record outside the review checkpoint; publishing one
never changes review facts, and a descriptor alone is not a published packet.

Damage to a saved descriptor is project damage (INVALID_PROJECT/3). Only an
absent packet is an INVALID_RECEIPT/6 ``unknown-packet``. Resume never enumerates
orphans: lookup lists the directory only to find names carrying one issued ID.
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
from typing import Self

from bookscan import packet_receipts
from bookscan.assets import DirectoryIdentity
from bookscan.ownership import Writer

STORE = "packets"
# A descriptor lists every file of a whole-book packet; this bounds a corrupt size.
MAX_BYTES = 64 * 1024 * 1024
Cancel = Callable[[], None]

_PACKET = re.compile("packet-[0-9a-f]{32}")
_NAME = re.compile(r"(packet-[0-9a-f]{32})\.([0-9a-f]{64})\.json")


@dataclass
class DescriptorError(Exception):
    code: str
    message: str
    exit_code: int = 3

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


def _close(descriptor: int) -> None:
    selected = sys.exception()
    try:
        os.close(descriptor)
    except OSError as error:
        if selected is None:
            raise
        selected.add_note("Packet descriptor close: " + str(error))


def _damaged(message: str) -> DescriptorError:
    return DescriptorError("INVALID_PROJECT", message)


class Descriptors:
    """Exact descriptor store; packet meaning stays with packet_receipts."""

    def __init__(self, owner: Writer, identity: DirectoryIdentity) -> None:
        self.owner = owner
        self.identity = identity

    @classmethod
    def provision(cls, owner: Writer) -> Self:
        from bookscan.project_reservation import provision_store

        owner.verify()
        try:
            with provision_store(owner, STORE) as info:
                result = cls(owner, DirectoryIdentity(info.st_dev, info.st_ino))
                with result._directory():
                    pass
                return result
        except OSError as error:
            raise DescriptorError(
                "WRITE_FAILED", "Cannot reserve unused packet descriptors directory.", 5
            ) from error

    def _verify_directory(self, descriptor: int) -> None:
        self.owner.verify()
        held = os.fstat(descriptor)
        current = (self.owner.path / STORE).lstat()
        expected = (self.identity.device, self.identity.inode)
        if (
            not stat.S_ISDIR(current.st_mode)
            or (held.st_dev, held.st_ino) != expected
            or (current.st_dev, current.st_ino) != expected
        ):
            raise _damaged("Packet descriptors directory was replaced.")

    @contextmanager
    def _directory(self) -> Iterator[int]:
        self.owner.verify()
        descriptor = -1
        try:
            descriptor = os.open(
                self.owner.path / STORE,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            self._verify_directory(descriptor)
            yield descriptor
            self._verify_directory(descriptor)
        except OSError as error:
            raise _damaged("Cannot verify packet descriptors directory.") from error
        finally:
            if descriptor >= 0:
                _close(descriptor)

    def _read(self, directory: int, name: str, digest: str, check_cancel: Cancel) -> bytes:
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
                or before.st_size > MAX_BYTES
            ):
                raise _damaged("Packet descriptor file type/links/size changed.")
            chunks: list[bytes] = []
            remaining = before.st_size
            while remaining:
                check_cancel()
                chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                if not chunk:
                    raise _damaged("Packet descriptor is truncated.")
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            if hashlib.sha256(raw).hexdigest() != digest:
                raise _damaged("Packet descriptor differs from its content address.")
            check_cancel()
            after = os.fstat(descriptor)
            current = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if _identity(before) != _identity(after) or _identity(after) != _identity(current):
                raise _damaged("Packet descriptor changed during verification.")
            self._verify_directory(directory)
            return raw
        except OSError as error:
            raise _damaged("Packet descriptor is missing or unreadable.") from error
        finally:
            if descriptor >= 0:
                _close(descriptor)

    def _parse(self, raw: bytes, digest: str, packet_id: str) -> packet_receipts.Descriptor:
        try:
            descriptor = packet_receipts.Descriptor.parse(raw, digest)
        except packet_receipts.ReceiptError as error:
            raise _damaged("Saved packet descriptor is invalid: " + error.message) from error
        if descriptor.packet_id != packet_id:
            raise _damaged("Saved packet descriptor names a different packet.")
        return descriptor

    def read(
        self, packet_id: str, *, check_cancel: Cancel = lambda: None
    ) -> packet_receipts.Descriptor:
        """The saved descriptor of one issued packet, verified against its address."""
        if type(packet_id) is not str or _PACKET.fullmatch(packet_id) is None:
            raise packet_receipts.ReceiptError(
                "Packet ID is not an issued packet identifier.", "malformed"
            )
        check_cancel()
        with self._directory() as directory:
            try:
                names = os.listdir(directory)
            except OSError as error:
                raise _damaged("Cannot list packet descriptors.") from error
            found = sorted(
                (match.group(2), name)
                for name in names
                if (match := _NAME.fullmatch(name)) is not None and match.group(1) == packet_id
            )
            if not found:
                raise packet_receipts.ReceiptError(
                    "No packet with this identifier was issued by this project.", "unknown-packet"
                )
            if len(found) != 1:
                raise _damaged("Packet identifier names several saved descriptors.")
            digest, name = found[0]
            raw = self._read(directory, name, digest, check_cancel)
            return self._parse(raw, digest, packet_id)

    def publish(
        self, descriptor: packet_receipts.Descriptor, *, check_cancel: Cancel = lambda: None
    ) -> str:
        """Atomically publish one sealed descriptor without replacing any name."""
        check_cancel()
        try:
            sealed = packet_receipts.Descriptor.parse(descriptor.raw, descriptor.id)
        except packet_receipts.ReceiptError as error:
            raise DescriptorError(
                "WRITE_FAILED", "A packet descriptor must be sealed before publication.", 5
            ) from error
        name = f"{sealed.packet_id}.{sealed.id}.json"
        with self._directory() as directory:
            private = ".descriptor-" + uuid.uuid4().hex
            descriptor_fd = -1
            owned = False
            held: os.stat_result | None = None

            def cleanup() -> None:
                if not owned or held is None:
                    return
                try:
                    current = os.stat(private, dir_fd=directory, follow_symlinks=False)
                    if (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino):
                        raise DescriptorError(
                            "WRITE_FAILED", "Private packet descriptor name was replaced.", 5
                        )
                    os.unlink(private, dir_fd=directory)
                except OSError as error:
                    raise DescriptorError(
                        "WRITE_FAILED", "Cannot clean owned private packet descriptor.", 5
                    ) from error

            try:
                descriptor_fd = os.open(
                    private,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                    dir_fd=directory,
                )
                owned = True
                held = os.fstat(descriptor_fd)
                view = memoryview(sealed.raw)
                while view:
                    check_cancel()
                    written = os.write(descriptor_fd, view)
                    if written == 0:
                        raise OSError("Zero-length packet descriptor write.")
                    view = view[written:]
                os.fsync(descriptor_fd)
                check_cancel()
                self._read(directory, private, sealed.id, check_cancel)
                self._verify_directory(directory)
                try:
                    # Atomic no-clobber publication; a descriptor is not a packet.
                    # https://docs.python.org/3.12/library/os.html#os.link
                    os.link(
                        private,
                        name,
                        src_dir_fd=directory,
                        dst_dir_fd=directory,
                        follow_symlinks=False,
                    )
                except FileExistsError:
                    # Same name means same packet and same content address; accept
                    # only an exact verified existing descriptor.
                    self._read(directory, name, sealed.id, check_cancel)
            except BaseException as error:
                try:
                    cleanup()
                except (DescriptorError, OSError) as failure:
                    error.add_note("Packet descriptor cleanup: " + str(failure))
                if isinstance(error, OSError):
                    raise DescriptorError(
                        "WRITE_FAILED", "Cannot publish complete packet descriptor.", 5
                    ) from error
                raise
            else:
                cleanup()
            finally:
                if descriptor_fd >= 0:
                    _close(descriptor_fd)
        return sealed.id
