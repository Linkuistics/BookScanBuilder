"""Remove only a private tree whose exact captured inventory is still present.

Capture happens at boundaries where this process is the only authorized writer:
after its own synchronous writes, or after an owned native child is completed and
reaped. A root this process just created and verified empty is the provenance for
everything captured at those boundaries. Unknown, changed or replaced entries are
retained untouched. These checks detect changes; they do not defend against a
hostile same-user race between a stamp check and an unlink.
"""

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from bookscan.import_publications import stamp
from bookscan.skew import NativeError


@dataclass(frozen=True)
class _Entry:
    kind: str  # "file" | "symlink" | "directory"
    stamp: tuple[int, ...]
    target: str | None = None

    def matches(self, other: "_Entry") -> bool:
        # Directory size/times legitimately move with our own child create/remove;
        # identity and mode still bind them. Files and links match their full stamp.
        if self.kind != other.kind or self.target != other.target:
            return False
        if self.kind == "directory":
            return self.stamp[:3] == other.stamp[:3]
        return self.stamp == other.stamp


def _scan(root: Path) -> dict[str, _Entry]:
    found: dict[str, _Entry] = {}
    pending = [Path()]
    while pending:
        relative = pending.pop()
        for item in os.scandir(root / relative):
            name = relative / item.name
            info = item.stat(follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                found[str(name)] = _Entry("directory", stamp(info))
                pending.append(name)
            elif stat.S_ISLNK(info.st_mode):
                found[str(name)] = _Entry("symlink", stamp(info), os.readlink(item.path))
            elif stat.S_ISREG(info.st_mode):
                found[str(name)] = _Entry("file", stamp(info))
            else:
                raise NativeError("Private tree contains an unsupported entry kind; retaining it.")
    return found


class OwnedTree:
    """One exclusively reserved directory and the entries captured as its own."""

    def __init__(self, root: Path) -> None:
        self.root = root
        try:
            info = root.lstat()
        except OSError as error:
            raise NativeError(f"Cannot capture private tree root: {error}") from error
        if not stat.S_ISDIR(info.st_mode):
            raise NativeError("Private tree root is not a directory; retaining it.")
        self._root = _Entry("directory", stamp(info))
        self._entries: dict[str, _Entry] = {}
        self.capture()

    def capture(self) -> None:
        """Adopt the current contents; call only at an authorized-writer boundary."""
        try:
            self._check_root()
            self._entries = _scan(self.root)
        except OSError as error:
            raise NativeError(f"Cannot capture private tree: {error}") from error

    def _check_root(self) -> None:
        current = _Entry("directory", stamp(self.root.lstat()))
        if not self._root.matches(current):
            raise NativeError("Private tree root was replaced or changed; retaining it.")

    def verify(self) -> None:
        try:
            self._check_root()
            current = _scan(self.root)
        except OSError as error:
            raise NativeError(f"Cannot verify private tree: {error}") from error
        if current.keys() != self._entries.keys():
            raise NativeError("Private tree names changed; retaining it.")
        for name, entry in self._entries.items():
            if not entry.matches(current[name]):
                raise NativeError("Private tree entry changed; retaining it.")

    def remove(self) -> None:
        """Verify the whole inventory first, then remove exactly its captured names."""
        self.verify()
        try:
            for name, entry in sorted(
                self._entries.items(), key=lambda item: (-len(Path(item[0]).parts), item[0])
            ):
                path = self.root / name
                if not entry.matches(
                    _Entry(
                        entry.kind,
                        stamp(path.lstat()),
                        os.readlink(path) if entry.kind == "symlink" else None,
                    )
                ):
                    raise NativeError("Private tree entry changed before removal; retaining it.")
                if entry.kind == "directory":
                    path.rmdir()
                else:
                    path.unlink()
            self._check_root()
            self.root.rmdir()
        except OSError as error:
            raise NativeError(f"Cannot remove owned private tree: {error}") from error
