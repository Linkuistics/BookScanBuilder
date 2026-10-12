"""Read saved caller-named resource facts without historical file access.

This is a component of the future semantic project verifier, not a complete
resource verifier. It proves inventory consistency, not actual historical use,
transient identity, complete discovery or source fidelity. Optional Fontconfig
scope guards require their own reader and are not returned. No secret environment
or executable ResourceBinding can be reconstructed from these opaque facts.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from bookscan import records
from bookscan.resources import LIMITATION, DirectoryEntry, DirectoryIdentity, FileIdentity


@dataclass
class ResourceRecordError(Exception):
    message: str
    code: str = "INVALID_PROJECT"
    exit_code: int = 3

    @property
    def remediation(self) -> str:
        return (
            "Use the compatible BookScanBuilder assessment-v1 reader with bookscan baseline "
            "status PROJECT; for damaged saved content use bookscan baseline create PDF "
            "--workdir NEW with an intact supported input. Fresh import loses review facts. "
            "Without intact input or a verifiable saved state no recovery is available."
        )

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True)
class NamedResources:
    environment_sha256: str
    working_directory: str
    working_directory_identity: tuple[int, int]
    files: tuple[FileIdentity, ...]
    directories: tuple[DirectoryIdentity, ...]


def _json(value: object) -> None:
    try:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        records.decode(raw)
        pending = [value]
        while pending:
            item = pending.pop()
            if type(item) is dict:
                data = cast(dict[object, object], item)
                if any(type(key) is not str for key in data):
                    raise ValueError("Non-string saved key.")
                pending.extend(data.values())
            elif type(item) is list:
                pending.extend(cast(list[object], item))
            elif item is not None and type(item) not in (str, int, float, bool):
                raise ValueError("Non-JSON saved value.")
    except (ValueError, TypeError, RecursionError, records.RecordError) as error:
        raise ResourceRecordError("Invalid saved resource JSON values.") from error


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(cast(dict[str, object], value)) != fields:
        raise ResourceRecordError("Unsupported saved named-resource fields.")
    return cast(dict[str, object], value)


def _array(value: object) -> list[object]:
    if type(value) is not list:
        raise ResourceRecordError("Saved resource inventory must use arrays.")
    return cast(list[object], value)


def _integer(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ResourceRecordError("Invalid saved resource native identity or size.")
    return value


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ResourceRecordError("Invalid saved resource digest.")
    return value


def _path(value: object, *, resolved: bool = False) -> str:
    if type(value) is not str or "\0" in value:
        raise ResourceRecordError("Invalid saved resource path.")
    text = value
    path = Path(text)
    # Logical caller spellings can contain '..'; historical resolved paths cannot.
    if not path.is_absolute() or str(path) != text or (resolved and ".." in path.parts):
        raise ResourceRecordError("Invalid saved absolute resource path.")
    return text


def _ordered(paths: list[str]) -> None:
    if paths != sorted(set(paths)):
        raise ResourceRecordError("Saved resource paths must be sorted and unique.")


def _file(value: object) -> FileIdentity:
    data = _object(value, {"path", "resolved", "device", "inode", "size", "sha256"})
    path = _path(data["path"])
    if data["resolved"] is None:
        if any(data[key] is not None for key in ("device", "inode", "size", "sha256")):
            raise ResourceRecordError("Absent named resource carries present-file facts.")
        return FileIdentity(path, None, None, None, None, None)
    return FileIdentity(
        path,
        _path(data["resolved"], resolved=True),
        _integer(data["device"]),
        _integer(data["inode"]),
        _integer(data["size"]),
        _digest(data["sha256"]),
    )


def _entry(value: object) -> DirectoryEntry:
    data = _object(
        value,
        {
            "path",
            "resolved",
            "device",
            "inode",
            "entry_device",
            "entry_inode",
            "kind",
            "link_target",
            "size",
            "sha256",
            "members",
        },
    )
    path, resolved = _path(data["path"]), _path(data["resolved"], resolved=True)
    entry_device, entry_inode = _integer(data["entry_device"]), _integer(data["entry_inode"])
    link = data["link_target"]
    if link is not None and (type(link) is not str or not link or "\0" in link):
        raise ResourceRecordError("Invalid saved resource symlink target.")
    kind = data["kind"]
    if type(kind) is not str or kind not in ("file", "directory", "dangling-symlink"):
        raise ResourceRecordError("Unsupported saved resource entry kind.")
    if kind == "dangling-symlink":
        if link is None or any(
            data[key] is not None for key in ("device", "inode", "size", "sha256", "members")
        ):
            raise ResourceRecordError("Dangling resource alias has contradictory target facts.")
        return DirectoryEntry(
            path,
            resolved,
            None,
            None,
            entry_device,
            entry_inode,
            kind,
            link,
            None,
            None,
            None,
        )
    device, inode = _integer(data["device"]), _integer(data["inode"])
    if link is None and (device, inode) != (entry_device, entry_inode):
        raise ResourceRecordError("Non-alias entry and target native identities differ.")
    size: int | None = None
    digest: str | None = None
    members: tuple[str, ...] | None = None
    if kind == "file":
        if data["members"] is not None:
            raise ResourceRecordError("File resource has directory membership.")
        size, digest = _integer(data["size"]), _digest(data["sha256"])
    else:
        if data["size"] is not None or data["sha256"] is not None:
            raise ResourceRecordError("Directory resource has file payload facts.")
        names = _array(data["members"])
        if any(
            type(name) is not str or not name or name in (".", "..") or "/" in name or "\0" in name
            for name in names
        ):
            raise ResourceRecordError("Invalid saved directory member name.")
        members = tuple(cast(list[str], names))
        _ordered(list(members))
    return DirectoryEntry(
        path,
        resolved,
        device,
        inode,
        entry_device,
        entry_inode,
        kind,
        link,
        size,
        digest,
        members,
    )


def _tree(value: object) -> DirectoryIdentity:
    data = _object(value, {"path", "entries"})
    root = _path(data["path"])
    if data["entries"] is None:
        return DirectoryIdentity(root, None)
    entries = tuple(_entry(item) for item in _array(data["entries"]))
    _ordered([item.path for item in entries])
    indexed = {item.path: item for item in entries}
    if root not in indexed or indexed[root].kind != "directory":
        raise ResourceRecordError("Present resource tree lacks its directory root.")
    # Exact membership closure excludes foreign/orphan entries and omitted children.
    expected = {root}
    for item in entries:
        if item.members is not None:
            expected.update(str(Path(item.path) / name) for name in item.members)
        if item.path != root:
            parent = indexed.get(str(Path(item.path).parent))
            if (
                parent is None
                or parent.members is None
                or Path(item.path).name not in parent.members
            ):
                raise ResourceRecordError("Resource tree contains an orphan or foreign entry.")
    if set(indexed) != expected:
        raise ResourceRecordError("Resource tree membership is incomplete.")
    for item in entries:
        if item.kind != "directory":
            continue
        native = (item.device, item.inode)
        ancestor = item.path
        while ancestor != root:
            ancestor = str(Path(ancestor).parent)
            parent = indexed[ancestor]
            if (parent.device, parent.inode) == native:
                raise ResourceRecordError("Cyclic saved resource directory traversal.")
    return DirectoryIdentity(root, entries)


def restore_named(value: object) -> NamedResources:
    """Return consistent immutable named facts, without historical I/O or trust upgrades.

    The caller separately verifies optional Fontconfig data and stored referenced
    payloads. The opaque environment digest cannot recreate or verify its values.
    """
    _json(value)
    fields = {
        "environment_sha256",
        "working_directory",
        "working_directory_identity",
        "files",
        "directories",
        "runtime_resources_verified",
        "limitation",
    }
    candidate: object = value
    if type(candidate) is dict and "fontconfig_scope_guard" in cast(dict[str, object], candidate):
        fields.add("fontconfig_scope_guard")
    data = _object(value, fields)
    if "fontconfig_scope_guard" in data and type(data["fontconfig_scope_guard"]) is not dict:
        raise ResourceRecordError("Fontconfig guard requires a separate semantic reader.")
    if data["runtime_resources_verified"] is not False or data["limitation"] != LIMITATION:
        raise ResourceRecordError("Named resource binding cannot grant runtime-use verification.")
    identity = _array(data["working_directory_identity"])
    if len(identity) != 2:
        raise ResourceRecordError("Incomplete saved working-directory identity.")
    files = tuple(_file(item) for item in _array(data["files"]))
    trees = tuple(_tree(item) for item in _array(data["directories"]))
    _ordered([item.path for item in files])
    _ordered([item.path for item in trees])
    return NamedResources(
        _digest(data["environment_sha256"]),
        _path(data["working_directory"], resolved=True),
        (_integer(identity[0]), _integer(identity[1])),
        files,
        trees,
    )
