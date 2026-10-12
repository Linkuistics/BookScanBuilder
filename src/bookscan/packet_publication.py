"""Private packet build directory and one no-replace atomic directory publication.

A packet is assembled in a private directory beside its unused destination and
becomes visible only through a single exclusive rename. Python's ``os.rename``
silently replaces an empty directory, so it is never used: macOS provides
``renameatx_np`` with ``RENAME_EXCL``, which refuses every occupied name
including a dangling symlink. The mechanism is verified at stage creation on the
destination's own filesystem rather than assumed.

Cancellation is the caller's: this module raises none and defers none. A stage
that is not published is removed only through an exact captured inventory.
"""

import ctypes
import ctypes.util
import errno
import os
import platform
import secrets
import stat
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from bookscan.owned_tree import OwnedTree
from bookscan.project_header import HeaderError
from bookscan.skew import NativeError

# <sys/stdio.h>: RENAME_SECLUDE 0x1, RENAME_SWAP 0x2, RENAME_EXCL 0x4.
# https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/rename.2.html
RENAME_EXCL = 0x4

_UNSUPPORTED = {errno.ENOTSUP, errno.EOPNOTSUPP, errno.ENOSYS, errno.EINVAL, errno.ENOTTY}


class PacketPublicationError(HeaderError):
    @property
    def remediation(self) -> str:
        if self.code == "OUTPUT_EXISTS":
            return "Inspect the existing destination and choose a new unused packet directory."
        if self.code == "OUTPUT_DIRECTORY_INVALID":
            return "Choose a new packet directory name inside an existing readable directory."
        if self.code == "PUBLISH_FAILED":
            return (
                "Use a local macOS filesystem that supports exclusive directory rename; "
                "no packet was published."
            )
        if self.code == "DEPENDENCY_UNAVAILABLE":
            return "Use the supported macOS local filesystem and Python 3.12 environment."
        return "Check packet destination storage and permissions, then choose a new directory."


type ExclusiveRename = Callable[[int, str, str], None]
"""Rename ``source`` to ``target`` inside one directory, failing if ``target`` exists."""


def native_exclusive_rename(parent: int, source: str, target: str) -> None:
    """Exclusive same-directory rename through the actual macOS libc entry point."""
    library = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    function = library.renameatx_np
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    function.restype = ctypes.c_int
    if function(parent, os.fsencode(source), parent, os.fsencode(target), RENAME_EXCL) != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), target)


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _private_name(suffix: str) -> str:
    return f".bookscan-packet-{secrets.token_hex(16)}.{suffix}"


@dataclass
class Published:
    """The committed packet directory; identity_verified is advisory after commit."""

    path: Path
    identity_verified: bool


class PacketStage:
    """One private build directory that this operation exclusively created."""

    def __init__(
        self,
        parent: int,
        name: str,
        destination: Path,
        stage_name: str,
        identity: tuple[int, int],
        rename: ExclusiveRename,
    ) -> None:
        self._parent = parent
        self._name = name
        self._stage_name = stage_name
        self._identity = identity
        self._rename = rename
        self._tree: OwnedTree | None = None
        self.destination = destination
        self.path = destination.parent / stage_name
        self.published = False

    def capture(self) -> None:
        """Adopt the stage's current contents; call after this process's own writes."""
        if self.published:
            raise PacketPublicationError("WRITE_FAILED", "Packet is already published.", 5)
        try:
            self._tree = OwnedTree(self.path)
        except NativeError as error:
            raise PacketPublicationError(
                "WRITE_FAILED", f"Cannot capture packet stage: {error}", 5
            ) from error

    def publish(self) -> Published:
        """Make the complete stage visible atomically, never replacing a name."""
        if self.published:
            raise PacketPublicationError("WRITE_FAILED", "Packet is already published.", 5)
        self.capture()
        try:
            named = os.stat(self._stage_name, dir_fd=self._parent, follow_symlinks=False)
            if not stat.S_ISDIR(named.st_mode) or _identity(named) != self._identity:
                raise PacketPublicationError(
                    "WRITE_FAILED", "Packet stage was replaced; nothing was published.", 5
                )
            mask = os.umask(0)
            os.umask(mask)
            # A restrictive private stage is made as readable as other output.
            os.chmod(self._stage_name, 0o777 & ~mask, dir_fd=self._parent)
            self.capture()
        except OSError as error:
            raise PacketPublicationError(
                "WRITE_FAILED", "Cannot prepare packet stage for publication.", 5
            ) from error
        try:
            self._rename(self._parent, self._stage_name, self._name)
        except OSError as error:
            if error.errno == errno.EEXIST:
                raise PacketPublicationError(
                    "OUTPUT_EXISTS", "Packet destination is already occupied.", 4
                ) from error
            if error.errno in _UNSUPPORTED:
                raise PacketPublicationError(
                    "PUBLISH_FAILED", "Exclusive directory publication is unsupported here.", 5
                ) from error
            raise PacketPublicationError(
                "PUBLISH_FAILED", "Cannot publish the packet directory.", 5
            ) from error
        self.published = True
        try:
            final = os.stat(self._name, dir_fd=self._parent, follow_symlinks=False)
            verified = stat.S_ISDIR(final.st_mode) and _identity(final) == self._identity
        except OSError:
            verified = False
        return Published(self.destination, verified)

    def discard(self) -> None:
        """Remove an unpublished stage only while its captured inventory is intact."""
        if self.published:
            return
        tree = self._tree
        try:
            if tree is None:
                # No capture: the root may only be removed while still empty.
                named = os.stat(self._stage_name, dir_fd=self._parent, follow_symlinks=False)
                if _identity(named) != self._identity:
                    raise NativeError("Packet stage was replaced; retaining it.")
                os.rmdir(self._stage_name, dir_fd=self._parent)
            else:
                tree.remove()
        except FileNotFoundError:
            return
        except (OSError, NativeError) as error:
            raise PacketPublicationError(
                "WRITE_FAILED", f"Packet stage retained: {error}", 5
            ) from error


def _probe(parent: int, stage_name: str, rename: ExclusiveRename) -> None:
    """Observe exclusive-rename semantics here without publishing or replacing anything."""
    probe_name = _private_name("probe")
    created = False
    try:
        os.mkdir(probe_name, 0o700, dir_fd=parent)
        created = True
        try:
            rename(parent, stage_name, probe_name)
        except OSError as error:
            if error.errno == errno.EEXIST:
                return  # The occupied name was refused: exclusive rename is enforced.
            raise PacketPublicationError(
                "PUBLISH_FAILED", "Exclusive directory publication is unsupported here.", 5
            ) from error
        raise PacketPublicationError(
            "PUBLISH_FAILED", "Directory rename did not refuse an occupied name.", 5
        )
    except OSError as error:
        raise PacketPublicationError(
            "WRITE_FAILED", "Cannot probe packet destination filesystem.", 5
        ) from error
    finally:
        if created:
            try:
                os.rmdir(probe_name, dir_fd=parent)
            except OSError as error:
                selected = sys.exception()
                if selected is not None:
                    selected.add_note(f"Packet probe {probe_name} retained: {error}")


@contextmanager
def stage(
    destination: Path, *, rename: ExclusiveRename = native_exclusive_rename
) -> Iterator[PacketStage]:
    """Reserve a private build directory beside an unused destination.

    The destination name is checked first (an occupied name, including a dangling
    symlink, is refused), then the filesystem's exclusive rename is observed.
    Leaving the block unpublished removes only the captured stage; a published
    packet is never touched.
    """
    if platform.system() != "Darwin":
        raise PacketPublicationError(
            "DEPENDENCY_UNAVAILABLE", "Packet publication is verified on macOS only.", 5
        )
    selected = destination.expanduser().absolute()
    if not selected.name or selected.name in {".", ".."} or "\0" in selected.name:
        raise PacketPublicationError("OUTPUT_EXISTS", "Packet destination is not a new name.", 4)
    parent = -1
    created: str | None = None
    packet: PacketStage | None = None
    try:
        try:
            canonical = selected.parent.resolve(strict=True)
            parent = os.open(canonical, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        except (OSError, RuntimeError) as error:
            raise PacketPublicationError(
                "OUTPUT_DIRECTORY_INVALID",
                "Packet destination parent must be an existing readable directory.",
                4,
            ) from error
        try:
            os.stat(selected.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as error:
            raise PacketPublicationError(
                "OUTPUT_DIRECTORY_INVALID", "Cannot inspect the packet destination.", 4
            ) from error
        else:
            raise PacketPublicationError(
                "OUTPUT_EXISTS", "Packet destination is already occupied.", 4
            )
        name = _private_name("tmp")
        try:
            os.mkdir(name, 0o700, dir_fd=parent)
            created = name
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode):
                raise OSError(errno.ENOTDIR, "Packet stage is not a directory", name)
            # umask may have stripped owner bits from the private stage.
            os.chmod(name, 0o700, dir_fd=parent)
        except OSError as error:
            raise PacketPublicationError(
                "WRITE_FAILED", "Cannot create the private packet directory.", 5
            ) from error
        packet = PacketStage(
            parent, selected.name, canonical / selected.name, name, _identity(info), rename
        )
        _probe(parent, name, rename)
        yield packet
        if not packet.published:
            packet.discard()
    except BaseException as error:
        if packet is not None and not packet.published:
            try:
                packet.discard()
            except PacketPublicationError as failure:
                error.add_note(f"Packet stage {packet.path} retained: {failure}")
        elif created is not None and packet is None:
            try:
                os.rmdir(created, dir_fd=parent)
            except OSError as failure:
                error.add_note(f"Packet stage {created} retained: {failure}")
        raise
    finally:
        if parent >= 0:
            os.close(parent)
