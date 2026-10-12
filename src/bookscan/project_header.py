"""Immutable native bootstrap identities for caller-owned assets and checkpoint history.

A header is not a committed import. Resume requires a complete current checkpoint
and an operation-owned semantic verifier for every referenced predecessor/asset.
No source collection, renderer, helper build, orphan discovery or repair occurs here.
"""

import json
import os
import re
import stat
import sys
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Self, cast

from bookscan import assets, checkpoints, native_blobs, packet_descriptors, records
from bookscan.import_publications import Publications
from bookscan.ownership import LockIdentity, Writer

HEADER_NAME = "project.json"
MAX_HEADER_BYTES = 16_384
Cancel = Callable[[], None]
Verifier = Callable[["Stores", dict[str, object]], None]


@dataclass
class HeaderError(Exception):
    code: str
    message: str
    exit_code: int = 3

    @property
    def remediation(self) -> str:
        if self.code == "PROJECT_EXISTS":
            return "Choose a new unused project directory; do not replace saved entries."
        if self.code == "WRITE_FAILED":
            return "Check project storage and permissions, then create into a new unused directory."
        return (
            "Use the compatible BookScanBuilder project-format-v1 reader and "
            "bookscan baseline status PROJECT; for damaged or incomplete saved content, "
            "use bookscan baseline create PDF --workdir NEW with an intact supported input. "
            "Fresh import loses review facts; without intact input or verifiable saved state "
            "no recovery is available."
        )

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def _numbers(data: dict[str, object], names: set[str]) -> None:
    if set(data) != names or not all(type(v) is int and v >= 0 for v in data.values()):
        raise HeaderError("INVALID_PROJECT", "Invalid saved native identity fields/types.")
    if any(data[name] == 0 for name in names if "inode" in name):
        raise HeaderError("INVALID_PROJECT", "Invalid saved native inode.")


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise HeaderError("INVALID_PROJECT", "Saved native identity is not an object.")
    return cast(dict[str, object], value)


def _directory_identity(value: object) -> assets.DirectoryIdentity:
    data = _object(value)
    _numbers(data, {"device", "inode"})
    return assets.DirectoryIdentity(cast(int, data["device"]), cast(int, data["inode"]))


def _identity_record(value: assets.DirectoryIdentity) -> dict[str, object]:
    return {"device": value.device, "inode": value.inode}


def _native(info: os.stat_result) -> assets.DirectoryIdentity:
    return assets.DirectoryIdentity(info.st_dev, info.st_ino)


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


@dataclass(frozen=True)
class Header:
    lock: LockIdentity
    file: assets.DirectoryIdentity
    images: assets.DirectoryIdentity
    checkpoints: assets.DirectoryIdentity
    native: assets.DirectoryIdentity
    packets: assets.DirectoryIdentity

    def record(self) -> dict[str, object]:
        return {
            "format": "BookScanBuilderProject",
            "version": 1,
            "project_id": "project-" + self.lock.token,
            "required_capabilities": list(checkpoints.CAPABILITIES),
            "lock": {
                "project_device": self.lock.project_device,
                "project_inode": self.lock.project_inode,
                "lock_device": self.lock.lock_device,
                "lock_inode": self.lock.lock_inode,
                "token": self.lock.token,
            },
            "header": _identity_record(self.file),
            "assets": _identity_record(self.images),
            "checkpoints": _identity_record(self.checkpoints),
            "native_blobs": _identity_record(self.native),
            "packets": _identity_record(self.packets),
        }

    @classmethod
    def from_json(cls, raw: bytes) -> Self:
        try:
            data = records.decode(raw)
        except records.RecordError as error:
            raise HeaderError("INVALID_PROJECT", "Invalid project header JSON.") from error
        if (
            set(data)
            != {
                "format",
                "version",
                "project_id",
                "required_capabilities",
                "lock",
                "header",
                "assets",
                "checkpoints",
                "native_blobs",
                "packets",
            }
            or data["format"] != "BookScanBuilderProject"
            or type(data["version"]) is not int
            or data["version"] != 1
        ):
            raise HeaderError(
                "INVALID_PROJECT", "Unsupported project header fields/format/version."
            )
        capabilities = data["required_capabilities"]
        if (
            not isinstance(capabilities, list)
            or len(cast(list[object], capabilities)) != len(checkpoints.CAPABILITIES)
            or not all(isinstance(v, str) for v in cast(list[object], capabilities))
            or set(cast(list[str], capabilities)) != set(checkpoints.CAPABILITIES)
        ):
            raise HeaderError("INVALID_PROJECT", "Unsupported required project capabilities.")
        lock = _object(data["lock"])
        if set(lock) != {"project_device", "project_inode", "lock_device", "lock_inode", "token"}:
            raise HeaderError("INVALID_PROJECT", "Unsupported saved writer identity fields.")
        numbers = {k: v for k, v in lock.items() if k != "token"}
        _numbers(numbers, {"project_device", "project_inode", "lock_device", "lock_inode"})
        token = lock["token"]
        if (
            not isinstance(token, str)
            or re.fullmatch("[0-9a-f]{32}", token) is None
            or data["project_id"] != "project-" + token
        ):
            raise HeaderError("INVALID_PROJECT", "Invalid saved project/lock token identity.")
        return cls(
            LockIdentity(
                cast(int, lock["project_device"]),
                cast(int, lock["project_inode"]),
                cast(int, lock["lock_device"]),
                cast(int, lock["lock_inode"]),
                token,
            ),
            _directory_identity(data["header"]),
            _directory_identity(data["assets"]),
            _directory_identity(data["checkpoints"]),
            _directory_identity(data["native_blobs"]),
            _directory_identity(data["packets"]),
        )


@dataclass(frozen=True)
class _Saved:
    header: Header
    raw: bytes
    stamp: tuple[int, ...]


@dataclass(frozen=True)
class _Bootstrap:
    """Creation evidence retained only by the provisioning invocation, never resume."""

    parent: assets.DirectoryIdentity
    stores: tuple[tuple[str, tuple[int, ...]], ...]


def _close(descriptor: int, *, writing: bool = False) -> None:
    selected = sys.exception()
    try:
        os.close(descriptor)
    except OSError as failure:
        # Preserve a selected validation/cancellation error over descriptor cleanup.
        # https://docs.python.org/3.12/library/sys.html#sys.exception
        if selected is None:
            raise HeaderError(
                "WRITE_FAILED" if writing else "INVALID_PROJECT",
                "Cannot close project header descriptor.",
                5 if writing else 3,
            ) from failure
        selected.add_note("Header descriptor cleanup: " + str(failure))


def _read(project: Path, check_cancel: Cancel) -> _Saved:
    directory = descriptor = -1
    try:
        check_cancel()
        path = project.resolve(strict=True)
        directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        root = os.fstat(directory)
        descriptor = os.open(
            HEADER_NAME,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
            dir_fd=directory,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or not 0 < before.st_size <= MAX_HEADER_BYTES
        ):
            raise HeaderError("INVALID_PROJECT", "Invalid project header type/link count/size.")
        remaining = before.st_size
        chunks: list[bytes] = []
        while remaining:
            check_cancel()
            chunk = os.read(descriptor, remaining)
            if not chunk:
                raise HeaderError("INVALID_PROJECT", "Truncated project header.")
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        header = Header.from_json(raw)
        after = os.fstat(descriptor)
        named = os.stat(HEADER_NAME, dir_fd=directory, follow_symlinks=False)
        current_root = path.lstat()
        if (
            _stamp(before) != _stamp(after)
            or _stamp(after) != _stamp(named)
            or header.file != _native(after)
            or _native(root)
            != assets.DirectoryIdentity(header.lock.project_device, header.lock.project_inode)
            or not stat.S_ISDIR(current_root.st_mode)
            or _native(current_root) != _native(root)
        ):
            raise HeaderError("INVALID_PROJECT", "Project/header identity changed or was replaced.")
        check_cancel()
        return _Saved(header, raw, _stamp(after))
    except OSError as error:
        raise HeaderError("INVALID_PROJECT", "Project header is missing/unreadable.") from error
    finally:
        try:
            if descriptor >= 0:
                _close(descriptor)
        finally:
            if directory >= 0:
                _close(directory)


def _unlink(directory: int, name: str, identity: assets.DirectoryIdentity) -> None:
    named = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if _native(named) != identity:
        raise HeaderError(
            "INVALID_PROJECT", "Private header name was replaced; leave it untouched."
        )
    os.unlink(name, dir_fd=directory)


def _publish(
    owner: Writer,
    images: assets.Assets,
    history: checkpoints.Checkpoints,
    native: native_blobs.Blobs,
    packets: packet_descriptors.Descriptors,
    check_cancel: Cancel,
    store_stamps: list[tuple[str, tuple[int, ...]]],
) -> _Saved:
    from bookscan.ownership import OwnershipError

    directory = descriptor = -1
    private = ".header-" + uuid.uuid4().hex
    owned: assets.DirectoryIdentity | None = None
    captured: os.stat_result | None = None
    parent: os.stat_result | None = None
    saved: _Saved | None = None
    names = (private,)
    try:
        owner.verify()
        directory = os.open(owner.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        if _native(os.fstat(directory)) != assets.DirectoryIdentity(
            owner.identity.project_device, owner.identity.project_inode
        ):
            raise HeaderError(
                "INVALID_PROJECT", "Project directory was replaced before header write."
            )
        parent = owner.path.parent.lstat()
        _unchanged_stores(directory, store_stamps)
        descriptor = os.open(
            private,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        captured = os.fstat(descriptor)
        owned = _native(captured)
        header = Header(
            owner.identity,
            owned,
            images.identity,
            history.identity,
            native.identity,
            packets.identity,
        )
        raw = json.dumps(
            header.record(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        Header.from_json(raw)
        data = memoryview(raw)
        while data:
            check_cancel()
            written = os.write(descriptor, data)
            if written == 0:
                raise OSError("Zero-length header write.")
            captured = os.fstat(descriptor)
            data = data[written:]
        os.fsync(descriptor)
        captured = os.fstat(descriptor)
        check_cancel()
        owner.verify()
        named = os.stat(private, dir_fd=directory, follow_symlinks=False)
        if _stamp(named) != _stamp(os.fstat(descriptor)) or _native(named) != owned:
            raise HeaderError("INVALID_PROJECT", "Private header was replaced before publication.")
        # The full bootstrap record is visible atomically; no checkpoint is committed.
        # https://docs.python.org/3.12/library/os.html#os.link
        try:
            os.link(
                private,
                HEADER_NAME,
                src_dir_fd=directory,
                dst_dir_fd=directory,
                follow_symlinks=False,
            )
        except FileExistsError as error:
            raise HeaderError("PROJECT_EXISTS", "Project header is already occupied.", 4) from error
        names = (private, HEADER_NAME)
        previous = captured
        captured = None
        captured = _header_link_transition(previous, os.fstat(descriptor), 2)
        _unlink(directory, private, owned)
        names = (HEADER_NAME,)
        previous = captured
        captured = None
        captured = _header_link_transition(previous, os.fstat(descriptor), 1)
        saved = _read(owner.path, check_cancel)
        if saved.header != header or saved.raw != raw:
            raise HeaderError("INVALID_PROJECT", "Published header differs from completed bytes.")
        owner.verify()
        return saved
    except BaseException as error:
        if descriptor >= 0 and owned is not None:
            try:
                if captured is None or parent is None:
                    raise HeaderError(
                        "INVALID_PROJECT", "Private header cleanup identity unavailable."
                    )
                if HEADER_NAME in names:
                    _unchanged_stores(directory, store_stamps)
                    _remove_published_header(owner, directory, descriptor, names, captured, parent)
                else:
                    _remove_failed_header(owner, directory, descriptor, private, captured, parent)
            except (OSError, HeaderError, OwnershipError) as failure:
                error.add_note("Private header cleanup: " + str(failure))
        elif descriptor >= 0 and captured is None:
            error.add_note("Private header retained; cleanup identity unavailable.")
        if isinstance(error, OSError):
            raise HeaderError(
                "WRITE_FAILED", "Cannot publish complete project header.", 5
            ) from error
        raise
    finally:
        selected = sys.exception()
        try:
            try:
                if descriptor >= 0:
                    _close(descriptor, writing=True)
            finally:
                if directory >= 0:
                    _close(directory, writing=True)
        except BaseException as error:
            if selected is None and saved is not None and parent is not None:
                _rollback_closed_bootstrap(owner, _native(parent), saved, store_stamps, error)
            raise


def _remove_failed_header(
    owner: Writer,
    directory: int,
    descriptor: int,
    private: str,
    captured: os.stat_result,
    parent: os.stat_result,
) -> None:
    """Remove only an unchanged prepublication private file under held ownership.

    Unknown/replaced entries and post-link files remain intact. No cancellation
    callback, recursive cleanup or adversarial same-user rename defense occurs.
    """

    def verify_root() -> None:
        owner.verify()
        current_parent = owner.path.parent.lstat()
        if (
            not stat.S_ISDIR(current_parent.st_mode)
            or _native(current_parent) != _native(parent)
            or _native(os.fstat(directory))
            != assets.DirectoryIdentity(owner.identity.project_device, owner.identity.project_inode)
        ):
            raise HeaderError("INVALID_PROJECT", "Private header root or parent was replaced.")

    verify_root()
    try:
        named = os.stat(private, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return
    if (
        not stat.S_ISREG(named.st_mode)
        or named.st_nlink != 1
        or _stamp(named) != _stamp(captured)
        or _stamp(os.fstat(descriptor)) != _stamp(captured)
    ):
        raise HeaderError("INVALID_PROJECT", "Private header changed or was replaced; retain it.")
    verify_root()
    if _stamp(os.stat(private, dir_fd=directory, follow_symlinks=False)) != _stamp(captured):
        raise HeaderError("INVALID_PROJECT", "Private header changed before removal; retain it.")
    # https://docs.python.org/3.12/library/os.html#os.unlink
    os.unlink(private, dir_fd=directory)


def _unchanged_stores(directory: int, captured: list[tuple[str, tuple[int, ...]]]) -> None:
    """Any store activity, including checkpoint publication, prevents header rollback."""
    if {name for name, _ in captured} != {
        "assets",
        "checkpoints",
        "native-blobs",
        "packets",
    }:
        raise HeaderError("INVALID_PROJECT", "Bootstrap store cleanup identities unavailable.")
    for name, stamp in captured:
        named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISDIR(named.st_mode) or _stamp(named) != stamp:
            raise HeaderError(
                "INVALID_PROJECT", "Bootstrap store changed; retain published header."
            )


def _header_link_transition(
    before: os.stat_result, after: os.stat_result, links: int
) -> os.stat_result:
    """Only ctime and the expected link count may change during an owned link/unlink."""
    if (
        _stamp(after)[:3] != _stamp(before)[:3]
        or after.st_nlink != links
        or after.st_size != before.st_size
        or after.st_mtime_ns != before.st_mtime_ns
    ):
        raise HeaderError(
            "INVALID_PROJECT", "Header changed during owned link transition; retain it."
        )
    return after


def _remove_published_header(
    owner: Writer,
    directory: int,
    descriptor: int,
    names: tuple[str, ...],
    captured: os.stat_result,
    parent: os.stat_result,
) -> None:
    """Undo only this failed publication's exact one or two unchanged names.

    The caller first verifies untouched stores. Removing an owned hard link
    changes ctime and link count; capture only that checked transition. Unknown
    transitions retain remaining names. This is not a hostile rename defense.
    """
    remaining: list[str] = []
    for name in names:
        try:
            named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(named.st_mode) or _stamp(named) != _stamp(captured):
            raise HeaderError("INVALID_PROJECT", "Published header changed; retain owned names.")
        remaining.append(name)
    if not remaining:
        return
    if len(remaining) != len(names) or captured.st_nlink != len(names):
        raise HeaderError("INVALID_PROJECT", "Published header links changed; retain owned names.")
    if _stamp(os.fstat(descriptor)) != _stamp(captured):
        raise HeaderError("INVALID_PROJECT", "Held published header changed; retain owned names.")
    if len(names) == 2:
        # Check ancestry through the same held-file safeguard before either unlink.
        # A two-link file cannot use the single-link removal below directly.
        owner.verify()
        if _native(owner.path.parent.lstat()) != _native(parent) or _native(
            os.fstat(directory)
        ) != assets.DirectoryIdentity(owner.identity.project_device, owner.identity.project_inode):
            raise HeaderError("INVALID_PROJECT", "Published header ancestry changed.")
        if _stamp(os.fstat(descriptor)) != _stamp(captured) or any(
            _stamp(os.stat(name, dir_fd=directory, follow_symlinks=False)) != _stamp(captured)
            for name in names
        ):
            raise HeaderError("INVALID_PROJECT", "Published header changed before owned unlink.")
        os.unlink(HEADER_NAME, dir_fd=directory)
        captured = _header_link_transition(captured, os.fstat(descriptor), 1)
    _remove_failed_header(owner, directory, descriptor, names[0], captured, parent)


def _rollback_closed_bootstrap(
    owner: Writer,
    original_parent: assets.DirectoryIdentity,
    saved: _Saved,
    created: list[tuple[str, tuple[int, ...]]],
    selected: BaseException,
) -> bool:
    """Undo an untouched bootstrap after release or importing-operation failure.

    All original closes have been attempted. Never reuse their fd numbers:
    reopen and verify the original ancestry under the still-held writer, then
    compare the original header/store stamps. No discovery or cancellation runs.
    A changed store (including checkpoint activity) retains the entire bootstrap.
    """
    from bookscan import project_reservation
    from bookscan.ownership import OwnershipError

    parent = directory = -1
    try:
        owner.verify()
        # https://docs.python.org/3.12/library/os.html#os.open
        parent = os.open(
            owner.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        if _native(os.fstat(parent)) != original_parent:
            raise HeaderError("INVALID_PROJECT", "Bootstrap parent was replaced before cleanup.")
        directory = os.open(
            owner.path.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent,
        )
        reservation = project_reservation.Reservation(parent, directory, owner.path)
        reservation.verify()
        owner.verify()
        _unchanged_stores(directory, created)

        def matches_header(entry: os.stat_result) -> bool:
            owner.verify()
            return _stamp(entry) == saved.stamp

        reservation.remove_file(HEADER_NAME, matches=matches_header)
        for name, stamp in reversed(created):

            def matches(entry: os.stat_result, stamp: tuple[int, ...] = stamp) -> bool:
                owner.verify()
                return _stamp(entry) == stamp

            reservation.remove_directory(name, matches=matches)
        return True
    except (OSError, HeaderError, OwnershipError) as failure:
        selected.add_note("Closed bootstrap retained; cleanup: " + str(failure))
        return False
    finally:
        try:
            if directory >= 0:
                _close(directory, writing=True)
        finally:
            if parent >= 0:
                _close(parent, writing=True)


class Stores:
    """Bootstrap uses saved identities; shared operations keep caller-held ownership.

    Provision only within an operation's new reservation. It does not claim an
    accepted import. Resume verifies the header before locking, rechecks under
    ownership and requires the caller's semantic verifier on complete history.
    """

    def __init__(self, owner: Writer, saved: _Saved) -> None:
        self.owner, self._saved = owner, saved
        self.header = saved.header
        self.images = assets.Assets(owner, self.header.images)
        self.checkpoints = checkpoints.Checkpoints(owner, self.header.checkpoints)
        self.native = native_blobs.Blobs(owner, self.header.native)
        self.packets = packet_descriptors.Descriptors(owner, self.header.packets)
        self._bootstrap: _Bootstrap | None = None

    @classmethod
    def provision(cls, owner: Writer, *, check_cancel: Cancel = lambda: None) -> Self:
        from bookscan import project_reservation
        from bookscan.ownership import OwnershipError

        check_cancel()
        owner.verify()
        try:
            (owner.path / HEADER_NAME).lstat()
        except FileNotFoundError:
            pass
        except OSError as error:
            raise HeaderError("WRITE_FAILED", "Cannot check header destination.", 5) from error
        else:
            raise HeaderError("PROJECT_EXISTS", "Project header is already occupied.", 4)
        parent = directory = -1
        reservation: project_reservation.Reservation | None = None
        created: list[tuple[str, tuple[int, ...]]] = []
        saved: _Saved | None = None
        parent_identity: assets.DirectoryIdentity | None = None
        try:
            parent = os.open(
                owner.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            )
            parent_identity = _native(os.fstat(parent))
            directory = os.open(
                owner.path.name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent,
            )
            reservation = project_reservation.Reservation(parent, directory, owner.path)
            reservation.verify()
            owner.verify()

            def remember(name: str, identity: assets.DirectoryIdentity) -> None:
                owner.verify()
                captured = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if not stat.S_ISDIR(captured.st_mode) or _native(captured) != identity:
                    raise HeaderError("INVALID_PROJECT", "Provisioned store identity changed.")
                created.append((name, _stamp(captured)))

            images = assets.Assets.provision(owner)
            remember("assets", images.identity)
            history = checkpoints.Checkpoints.provision(owner)
            remember("checkpoints", history.identity)
            check_cancel()
            try:
                native = native_blobs.Blobs.provision(owner)
            except native_blobs.BlobError as error:
                raise HeaderError(error.code, error.message, error.exit_code) from error
            remember("native-blobs", native.identity)
            check_cancel()
            try:
                packets = packet_descriptors.Descriptors.provision(owner)
            except packet_descriptors.DescriptorError as error:
                raise HeaderError(error.code, error.message, error.exit_code) from error
            remember("packets", packets.identity)
            saved = _publish(owner, images, history, native, packets, check_cancel, created)
            result = cls(owner, saved)
            result.verify(check_cancel=check_cancel)
            result._bootstrap = _Bootstrap(parent_identity, tuple(created))
            stamps = dict(created)
            result.images.publications = Publications(stamps["assets"])
            result.native.publications = Publications(stamps["native-blobs"])
            return result
        except BaseException as error:
            if saved is not None and reservation is not None:
                try:
                    owner.verify()
                    reservation.verify()
                    _unchanged_stores(directory, created)

                    def matches_header(entry: os.stat_result) -> bool:
                        owner.verify()
                        return _stamp(entry) == saved.stamp

                    reservation.remove_file(HEADER_NAME, matches=matches_header)
                except (OSError, HeaderError, OwnershipError) as failure:
                    error.add_note("Published header retained; cleanup: " + str(failure))
            if created and reservation is not None:
                # A published (or foreign) header prevents empty-store rollback.
                # Its full lifetime belongs to the importing transaction.
                try:
                    owner.verify()
                    reservation.verify()
                    os.stat(HEADER_NAME, dir_fd=directory, follow_symlinks=False)
                except FileNotFoundError:
                    for name, stamp in reversed(created):
                        try:
                            owner.verify()

                            def matches(
                                entry: os.stat_result, stamp: tuple[int, ...] = stamp
                            ) -> bool:
                                owner.verify()
                                return _stamp(entry) == stamp

                            reservation.remove_directory(
                                name,
                                matches=matches,
                            )
                        except (OSError, HeaderError, OwnershipError) as failure:
                            error.add_note(f"Empty {name} store retained; cleanup: {failure}")
                except (OSError, HeaderError, OwnershipError) as failure:
                    error.add_note("Empty stores retained; cleanup: " + str(failure))
            if isinstance(error, OSError):
                raise HeaderError(
                    "WRITE_FAILED", "Cannot hold project directories for store provision.", 5
                ) from error
            raise
        finally:
            selected = sys.exception()
            try:
                try:
                    if directory >= 0:
                        _close(directory, writing=True)
                finally:
                    if parent >= 0:
                        _close(parent, writing=True)
            except BaseException as error:
                if selected is None and saved is not None and parent_identity is not None:
                    _rollback_closed_bootstrap(owner, parent_identity, saved, created, error)
                raise

    def rollback_empty(self, selected: BaseException) -> bool:
        """Remove only this invocation's original untouched empty bootstrap.

        Call before releasing the importing writer. A changed store, including
        an actual checkpoint, keeps header/source/lock together. Resume has no
        creation evidence and cannot roll back. This consumes the evidence once;
        no names or identities are discovered after failure.
        """
        captured, self._bootstrap = self._bootstrap, None
        if captured is None:
            selected.add_note("Bootstrap retained; original creation evidence unavailable.")
            return False
        return _rollback_closed_bootstrap(
            self.owner, captured.parent, self._saved, list(captured.stores), selected
        )

    def rollback_import(self, selected: BaseException) -> bool:
        """Roll back this import's captured completed publications, then bootstrap.

        Verify both stores and untouched checkpoint history before any removal.
        Unknown private files, changed assets, ancestry or any history activity
        retain the bootstrap/source/lock. No cancellation runs during cleanup.
        """
        from bookscan import project_reservation
        from bookscan.ownership import OwnershipError

        captured, self._bootstrap = self._bootstrap, None
        images, native = self.images.publications, self.native.publications
        if captured is None or images is None or native is None:
            selected.add_note(
                "Import rollback retained; original publication evidence unavailable."
            )
            return False
        original = dict(captured.stores)
        parent = directory = image_directory = native_directory = -1
        try:
            self.owner.verify()
            parent = os.open(
                self.owner.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            )
            if _native(os.fstat(parent)) != captured.parent:
                raise HeaderError("INVALID_PROJECT", "Import rollback parent was replaced.")
            directory = os.open(
                self.owner.path.name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent,
            )
            reservation = project_reservation.Reservation(parent, directory, self.owner.path)

            def guard() -> None:
                reservation.verify()
                self.verify()
                history = os.stat("checkpoints", dir_fd=directory, follow_symlinks=False)
                if _stamp(history) != original["checkpoints"]:
                    raise HeaderError(
                        "INVALID_PROJECT", "Checkpoint activity prevents import rollback."
                    )

            guard()
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            image_directory = os.open("assets", flags, dir_fd=directory)
            native_directory = os.open("native-blobs", flags, dir_fd=directory)
            images.verify(image_directory)
            native.verify(native_directory)
            images.remove(image_directory, guard)
            native.remove(native_directory, guard)
            guard()
            original["assets"] = images.directory_stamp
            original["native-blobs"] = native.directory_stamp
            return _rollback_closed_bootstrap(
                self.owner, captured.parent, self._saved, list(original.items()), selected
            )
        except (
            OSError,
            HeaderError,
            OwnershipError,
            assets.AssetError,
            native_blobs.BlobError,
        ) as failure:
            selected.add_note("Import publications/bootstrap retained; cleanup: " + str(failure))
            return False
        finally:
            try:
                try:
                    if native_directory >= 0:
                        _close(native_directory, writing=True)
                finally:
                    if image_directory >= 0:
                        _close(image_directory, writing=True)
            finally:
                try:
                    if directory >= 0:
                        _close(directory, writing=True)
                finally:
                    if parent >= 0:
                        _close(parent, writing=True)

    def verify(self, *, check_cancel: Cancel = lambda: None) -> None:
        self.owner.verify()
        if (
            self.header.lock != self.owner.identity
            or _read(self.owner.path, check_cancel) != self._saved
        ):
            raise HeaderError("INVALID_PROJECT", "Project header changed under writer ownership.")
        for name, identity in (
            ("assets", self.header.images),
            ("checkpoints", self.header.checkpoints),
            ("native-blobs", self.header.native),
            ("packets", self.header.packets),
        ):
            check_cancel()
            try:
                entry = (self.owner.path / name).lstat()
            except OSError as error:
                raise HeaderError(
                    "INVALID_PROJECT", f"Saved {name} directory is missing/unreadable."
                ) from error
            if not stat.S_ISDIR(entry.st_mode) or _native(entry) != identity:
                raise HeaderError("INVALID_PROJECT", f"Saved {name} directory was replaced.")
        self.owner.verify()


@contextmanager
def resume(
    project: Path, *, verify_state: Verifier, check_cancel: Cancel = lambda: None
) -> Iterator[tuple[Stores, checkpoints.Checkpoint]]:
    """Acquire once, verify complete committed history and close only this acquisition.

    The mandatory verifier receives both saved-identity stores under this single
    acquisition. It must verify all referenced state; header/history grammar is
    insufficient to establish a usable project.
    """
    saved = _read(project, check_cancel)
    owner = Writer.acquire(project, saved.header.lock)
    try:
        stores = Stores(owner, saved)
        stores.verify(check_cancel=check_cancel)

        def verify(state: dict[str, object]) -> None:
            stores.verify(check_cancel=check_cancel)
            verify_state(stores, state)
            stores.verify(check_cancel=check_cancel)

        checkpoint = stores.checkpoints.load(verify_state=verify, check_cancel=check_cancel)
        stores.verify(check_cancel=check_cancel)
        yield stores, checkpoint
        stores.verify(check_cancel=check_cancel)
    finally:
        selected = sys.exception()
        try:
            owner.close()
        except OSError as error:
            if selected is None:
                raise HeaderError(
                    "INVALID_PROJECT", "Cannot close project reader ownership."
                ) from error
            selected.add_note("Project reader ownership cleanup: " + str(error))
