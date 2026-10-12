"""Transient ownership of exact files created by one initial import.

This journal is attached only to freshly provisioned empty stores. It is never
serialized, reconstructed from content addresses, or attached by resume. Private
files whose creation never reaches capture remain conservatively untouched.
"""

import os
import stat
from collections.abc import Callable


def stamp(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


class Publications:
    def __init__(self, directory_stamp: tuple[int, ...]) -> None:
        self.directory_stamp = directory_stamp
        self._files: dict[str, tuple[int, ...]] = {}

    def _files_match(self, directory: int, files: dict[str, tuple[int, ...]]) -> None:
        # Enumeration checks for foreign entries; it never grants their ownership.
        if set(os.listdir(directory)) != set(files):
            raise OSError("Import store contains uncaptured names; retain it.")
        for name, captured in files.items():
            named = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if not stat.S_ISREG(named.st_mode) or stamp(named) != captured:
                raise OSError("Captured import publication changed; retain it.")

    def verify(self, directory: int) -> None:
        if stamp(os.fstat(directory)) != self.directory_stamp:
            raise OSError("Import store changed outside captured publication; retain it.")
        self._files_match(directory, self._files)

    def aborted(self, directory: int) -> None:
        """Record a verified own private unlink without adopting any new name.

        Called only after the publisher successfully cleans its created private
        file. Between entry verification and this boundary the directory stamp
        changes through our create/unlink; every prior file must remain exact.
        """
        current = stamp(os.fstat(directory))
        if current[:3] != self.directory_stamp[:3]:
            raise OSError("Import store identity/mode changed; retain it.")
        self._files_match(directory, self._files)
        if stamp(os.fstat(directory)) != current:
            raise OSError("Import store changed during aborted publication capture; retain it.")
        self.directory_stamp = current

    def refused(
        self,
        directory: int,
        descriptor: int,
        name: str,
        expected: tuple[int, ...],
        *,
        linked_name: str | None = None,
    ) -> None:
        """Capture a known private name and returned own link after unlink refusal.

        The publisher stamps its returned creation descriptor before cleanup.
        linked_name is supplied only after its no-clobber link returned success;
        both names must still match that exact two-link file. Unknown outcomes,
        changes or additional links never grant ownership. Resume has no journal.
        """
        current = stamp(os.fstat(directory))
        held = os.fstat(descriptor)
        named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if (
            current[:3] != self.directory_stamp[:3]
            or name in self._files
            or not stat.S_ISREG(held.st_mode)
            or held.st_nlink != (1 if linked_name is None else 2)
            or stamp(held) != expected
            or stamp(named) != expected
        ):
            raise OSError("Refused private import ownership changed; retain it.")
        files = self._files | {name: expected}
        if linked_name is not None:
            if linked_name == name or linked_name in self._files:
                raise OSError("Linked private import name is already owned; retain it.")
            files[linked_name] = expected
        self._files_match(directory, files)
        if stamp(os.fstat(directory)) != current:
            raise OSError("Import store changed during private capture; retain it.")
        self._files, self.directory_stamp = files, current

    def completed(self, directory: int, descriptor: int, name: str, *, created: bool) -> None:
        """Capture at the own link/unlink boundary, before close or final read.

        The caller verified the journal before creating its private name. Only
        successful no-clobber link publication grants ownership of a new name.
        Deduplication must already name this invocation's captured file.
        """
        current = os.fstat(directory)
        # APFS directory nlink changes with file entries (observed 2 -> 3 -> 4
        # for empty -> one file -> two names). Only identity/mode are invariant
        # across our publication. Exact names and file stamps are checked below.
        if stamp(current)[:3] != self.directory_stamp[:3]:
            raise OSError("Import store identity/mode changed; retain it.")
        files = self._files.copy()
        if created:
            held = os.fstat(descriptor)
            named = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if (
                name in files
                or not stat.S_ISREG(held.st_mode)
                or held.st_nlink != 1
                or stamp(held) != stamp(named)
            ):
                raise OSError("New import publication ownership is unverifiable; retain it.")
            files[name] = stamp(held)
        elif name not in files:
            raise OSError("Existing asset was not created by this invocation; retain it.")
        self._files_match(directory, files)
        if stamp(os.fstat(directory)) != stamp(current):
            raise OSError("Import store changed during publication capture; retain it.")
        self._files, self.directory_stamp = files, stamp(current)

    def remove(self, directory: int, guard: Callable[[], None]) -> None:
        """Remove exact unchanged names under the importing writer, never sweep."""
        self.verify(directory)
        for name in tuple(self._files):
            guard()
            self.verify(directory)
            # This guards cooperative operations and changed entries, not hostile
            # same-user replacement between the final stat and unlink.
            removed = self._files[name]
            os.unlink(name, dir_fd=directory)
            del self._files[name]
            # A captured own link pair shares nlink/ctime. Only this successful
            # unlink authorizes updating its surviving alias, never its content,
            # mode, mtime or identity, nor any unrelated captured file.
            for alias, before in self._files.items():
                if before[:2] != removed[:2]:
                    continue
                after = stamp(os.stat(alias, dir_fd=directory, follow_symlinks=False))
                if (
                    before != removed
                    or after[:3] != before[:3]
                    or after[3] != before[3] - 1
                    or after[4:6] != before[4:6]
                ):
                    raise OSError("Captured alias changed during own unlink; retain it.")
                self._files[alias] = after
            current = stamp(os.fstat(directory))
            if current[:3] != self.directory_stamp[:3]:
                raise OSError("Import store identity/mode changed during cleanup; retain it.")
            self._files_match(directory, self._files)
            self.directory_stamp = current
        self.verify(directory)
