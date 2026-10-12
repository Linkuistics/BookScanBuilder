"""Bind caller-discovered resource files/trees and the native-child environment.

This checks supplied subjects, not completeness of runtime resource discovery.
No environment values are serialized into project or acceptance provenance.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from bookscan.native_setup import digest
from bookscan.skew import NativeError

LIMITATION = (
    "Only caller-named resource files/directories are bound; complete runtime font/profile/config "
    "discovery and actual-use identity remain unverified. Before/after checks do not "
    "exclude transient changes restored during a native read."
)


@dataclass(frozen=True)
class FileIdentity:
    path: str
    resolved: str | None
    device: int | None
    inode: int | None
    size: int | None
    sha256: str | None


@dataclass(frozen=True)
class DirectoryEntry:
    path: str
    resolved: str
    device: int | None
    inode: int | None
    entry_device: int
    entry_inode: int
    kind: str
    link_target: str | None
    size: int | None
    sha256: str | None
    members: tuple[str, ...] | None


@dataclass(frozen=True)
class DirectoryIdentity:
    path: str
    entries: tuple[DirectoryEntry, ...] | None


def _resolved(path: Path, *, strict: bool = True) -> Path:
    try:
        return path.resolve(strict=strict)
    except RuntimeError as error:
        raise NativeError(f"Cyclic resource path: {path}.") from error


def _metadata(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    # Access time may change because of this very read; it is not resource identity.
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _directory_identity(
    path: Path, optional: bool, check_cancel: Callable[[], None]
) -> DirectoryIdentity:
    """Bind every name, including absent alias targets; fail cycles/unreadable entries."""
    entries: list[DirectoryEntry] = []

    def walk(current: Path, ancestors: frozenset[tuple[int, int]]) -> None:
        check_cancel()
        spelling = current.lstat()
        link = str(current.readlink()) if stat.S_ISLNK(spelling.st_mode) else None
        try:
            before = current.stat()
        except FileNotFoundError:
            if link is None:
                raise
            # Preserve the entry and resolved missing destination, never omit it.
            # Fontconfig 2.18.3 scans hidden names too (except . and ..):
            # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcdir.c
            resolved = _resolved(current, strict=False)
            if (
                _metadata(current.lstat()) != _metadata(spelling)
                or str(current.readlink()) != link
                or _resolved(current, strict=False) != resolved
            ):
                raise NativeError(f"Resource directory entry changed while binding: {current}.")
            # Absence is rechecked after resolving aliases and checking the entry.
            try:
                current.stat()
            except FileNotFoundError:
                pass
            else:
                raise NativeError(f"Resource directory entry changed while binding: {current}.")
            entries.append(
                DirectoryEntry(
                    str(current),
                    str(resolved),
                    None,
                    None,
                    spelling.st_dev,
                    spelling.st_ino,
                    "dangling-symlink",
                    link,
                    None,
                    None,
                    None,
                )
            )
            return
        resolved = _resolved(current)
        members: tuple[str, ...] | None = None
        size: int | None = None
        value: str | None = None
        if stat.S_ISDIR(before.st_mode):
            native = (before.st_dev, before.st_ino)
            if native in ancestors:
                raise NativeError(f"Cyclic resource directory: {current}.")
            # Python 3.12 iterdir includes dotfiles; additions during iteration are
            # unspecified. Recheck names and native metadata after walking children.
            # https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.iterdir
            members = tuple(sorted(child.name for child in current.iterdir()))
            for member in members:
                walk(current / member, ancestors | {native})
            if tuple(sorted(child.name for child in current.iterdir())) != members:
                raise NativeError(f"Resource directory changed while binding: {current}.")
            kind = "directory"
        elif stat.S_ISREG(before.st_mode):
            file = _identity(current, False, check_cancel)
            size, value = file.size, file.sha256
            kind = "file"
        else:
            raise NativeError(f"Unsupported resource directory entry: {current}.")
        after = current.stat()
        if (
            _metadata(before) != _metadata(after)
            or _metadata(current.lstat()) != _metadata(spelling)
            or _resolved(current) != resolved
        ):
            raise NativeError(f"Resource directory entry changed while binding: {current}.")
        entries.append(
            DirectoryEntry(
                str(current),
                str(resolved),
                before.st_dev,
                before.st_ino,
                spelling.st_dev,
                spelling.st_ino,
                kind,
                link,
                size,
                value,
                members,
            )
        )

    check_cancel()
    try:
        try:
            path.lstat()
        except FileNotFoundError:
            if optional:
                return DirectoryIdentity(str(path), None)
            raise
        if not stat.S_ISDIR(path.stat().st_mode):
            raise NativeError(f"Named resource directory is not a directory: {path}.")
        walk(path, frozenset())
    except OSError as error:
        raise NativeError(f"Cannot verify resource directory {path}: {error}") from error
    check_cancel()
    return DirectoryIdentity(str(path), tuple(sorted(entries, key=lambda item: item.path)))


def _identity(path: Path, optional: bool, check_cancel: Callable[[], None]) -> FileIdentity:
    check_cancel()
    try:
        # lstat distinguishes absent optional inputs from dangling entries.
        try:
            path.lstat()
        except FileNotFoundError:
            if optional:
                return FileIdentity(str(path), None, None, None, None, None)
            raise
        resolved = _resolved(path)
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise NativeError(f"Named resource is not a regular file: {path}.")
        value = digest(path, check_cancel=check_cancel)
        after = path.stat()
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) or _resolved(path) != resolved:
            raise NativeError(f"Named resource changed while binding: {path}.")
        return FileIdentity(
            str(path), str(resolved), before.st_dev, before.st_ino, before.st_size, value
        )
    except OSError as error:
        raise NativeError(f"Cannot verify named resource {path}: {error}") from error


@dataclass(frozen=True)
class ResourceBinding:
    files: tuple[FileIdentity, ...]
    _environment: tuple[tuple[str, str], ...]
    directory: Path
    _directory_identity: tuple[int, int]
    directories: tuple[DirectoryIdentity, ...] = ()

    @classmethod
    def capture(
        cls,
        files: Sequence[Path],
        *,
        optional_files: Sequence[Path] = (),
        directories: Sequence[Path] = (),
        optional_directories: Sequence[Path] = (),
        environment: Mapping[str, str] | None = None,
        check_cancel: Callable[[], None] = lambda: None,
    ) -> ResourceBinding:
        """Caller supplies the discovery scope; values stay immutable in memory."""
        check_cancel()
        captured = tuple(sorted((os.environ if environment is None else environment).items()))
        try:
            directory = Path.cwd().resolve(strict=True)
            directory_stat = directory.stat()
        except OSError as error:
            raise NativeError(f"Cannot bind child working directory: {error}") from error
        # Keep logical spellings: resolving only would miss retargeted aliases.
        required = {path.absolute() for path in files}
        optional = {path.absolute() for path in optional_files} - required
        subjects = tuple(
            _identity(path, path in optional, check_cancel) for path in sorted(required | optional)
        )
        required_dirs = {path.absolute() for path in directories}
        optional_dirs = {path.absolute() for path in optional_directories} - required_dirs
        trees = tuple(
            _directory_identity(path, path in optional_dirs, check_cancel)
            for path in sorted(required_dirs | optional_dirs)
        )
        check_cancel()
        return cls(
            subjects, captured, directory, (directory_stat.st_dev, directory_stat.st_ino), trees
        )

    def environment(self) -> dict[str, str]:
        """A fresh copy prevents callers changing the captured child environment."""
        return dict(self._environment)

    def verify(self, *, check_cancel: Callable[[], None] = lambda: None) -> None:
        check_cancel()
        try:
            directory_stat = self.directory.stat()
            if (
                not stat.S_ISDIR(directory_stat.st_mode)
                or (directory_stat.st_dev, directory_stat.st_ino) != self._directory_identity
            ):
                raise NativeError(f"Bound child working directory changed: {self.directory}.")
        except OSError as error:
            raise NativeError(f"Cannot verify child working directory: {error}") from error
        for expected in self.files:
            actual = _identity(Path(expected.path), expected.resolved is None, check_cancel)
            if actual != expected:
                raise NativeError(f"Named resource identity changed: {expected.path}.")
        for expected in self.directories:
            actual = _directory_identity(
                Path(expected.path), expected.entries is None, check_cancel
            )
            if actual != expected:
                raise NativeError(f"Named resource directory identity changed: {expected.path}.")
        check_cancel()

    def record(self) -> dict[str, object]:
        # Encode the entire environment, including unanticipated native options.
        # Never emit values (which may contain secrets); this is an opaque binding.
        encoded = json.dumps(self._environment, ensure_ascii=True, separators=(",", ":")).encode()
        return {
            "environment_sha256": hashlib.sha256(encoded).hexdigest(),
            "working_directory": str(self.directory),
            "working_directory_identity": list(self._directory_identity),
            "files": [asdict(item) for item in self.files],
            "directories": [
                {
                    "path": item.path,
                    "entries": None
                    if item.entries is None
                    else [asdict(entry) for entry in item.entries],
                }
                for item in self.directories
            ],
            "runtime_resources_verified": False,
            "limitation": LIMITATION,
        }
