"""Check saved static native graphs against saved named files without historical I/O.

Closure and matching digests are consistency facts, not evidence of historical
dyld selection, native file use, configuration currency or glyph/source fidelity.
System references retain the saved OS build without claiming shared-cache bytes.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from bookscan import dependencies, records
from bookscan.resource_record import ResourceRecordError, restore_named
from bookscan.skew import NativeError

SYSTEM_IDENTITY = "OS shared-cache reference; disk bytes not claimed"


@dataclass(frozen=True)
class Reference:
    kind: str
    reference: str
    resolved: str | None


@dataclass(frozen=True)
class LinkedFile:
    path: str
    sha256: str
    load_commands: str
    references: tuple[Reference, ...]


@dataclass(frozen=True)
class LinkedDependencies:
    root: str
    executable_context: str
    architecture: str
    os_build: str
    files: tuple[LinkedFile, ...]
    system_references: tuple[str, ...]


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(cast(dict[str, object], value)) != fields:
        raise ResourceRecordError("Unsupported saved linked-dependency fields.")
    return cast(dict[str, object], value)


def _text(value: object) -> str:
    if type(value) is not str or not value or "\0" in value:
        raise ResourceRecordError("Invalid saved native-dependency text.")
    return value


def _path(value: object) -> str:
    text = _text(value)
    path = Path(text)
    if not path.is_absolute() or str(path) != text or ".." in path.parts:
        raise ResourceRecordError("Invalid saved canonical native-dependency path.")
    return text


def _system(name: str) -> bool:
    return name.startswith(("/usr/lib/", "/System/Library/"))


def _reference(value: object) -> Reference:
    if type(value) is not dict:
        raise ResourceRecordError("Saved linked reference requires an object.")
    fields = cast(dict[str, object], value)
    name = _text(fields.get("reference"))
    system = _system(name)
    data = _object(fields, {"kind", "reference", "identity" if system else "resolved"})
    kind = _text(data["kind"])
    if kind not in dependencies.LOADS:
        raise ResourceRecordError("Unsupported saved native load kind.")
    if system:
        _path(name)
        if data["identity"] != SYSTEM_IDENTITY:
            raise ResourceRecordError("OS shared-cache reference cannot claim disk bytes.")
        return Reference(kind, name, None)
    if not (
        name.startswith(("/", "@rpath/", "@loader_path/", "@executable_path/"))
        or name in {"@loader_path", "@executable_path"}
    ):
        raise ResourceRecordError("Unrecognized saved native load reference.")
    return Reference(kind, name, _path(data["resolved"]))


def restore(value: object, binding: object) -> LinkedDependencies:
    """Return immutable saved graph facts bound to a verified named inventory.

    Captured load commands and saved reference ordering must agree, every target
    must be in the graph, every graph file must be reachable from the root, and
    all digests must match the saved named files. Historical symlink/runpath
    resolution is not replayed or certified. No current tool or OS is consulted.
    """
    named = restore_named(binding)
    try:
        records.decode(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except (ValueError, TypeError, RecursionError, records.RecordError) as error:
        raise ResourceRecordError("Invalid saved linked-dependency JSON values.") from error
    data = _object(
        value,
        {
            "root",
            "executable_context",
            "architecture",
            "os_build",
            "files",
            "system_references",
            "runtime_resources_verified",
            "limitation",
        },
    )
    if (
        data["runtime_resources_verified"] is not False
        or data["limitation"] != dependencies.LIMITATION
    ):
        raise ResourceRecordError("Static linked identities cannot grant runtime verification.")
    root, context = _path(data["root"]), _path(data["executable_context"])
    architecture, build = _text(data["architecture"]), _text(data["os_build"])
    if architecture not in {"arm64", "x86_64"}:
        raise ResourceRecordError("Unsupported saved native architecture.")
    if type(data["files"]) is not dict:
        raise ResourceRecordError("Saved linked-file inventory requires an object.")
    saved_files = cast(dict[str, object], data["files"])
    bound = {item.path: item for item in named.files}
    files: dict[str, LinkedFile] = {}
    systems: set[str] = set()
    for name, value in saved_files.items():
        path = _path(name)
        item = _object(value, {"sha256", "load_commands", "references"})
        digest = _text(item["sha256"])
        subject = bound.get(path)
        if (
            re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or subject is None
            or subject.resolved != path
            or subject.sha256 != digest
        ):
            raise ResourceRecordError("Linked file lacks a matching present named identity.")
        raw = _text(item["load_commands"])
        if raw.splitlines()[0] not in {
            path + ":",
            path + f" (architecture {architecture}):",
        }:
            raise ResourceRecordError("Saved Mach-O header names a different file or architecture.")
        try:
            _, loads = dependencies.load_commands(raw, Path(path))
        except NativeError as error:
            raise ResourceRecordError("Invalid saved Mach-O load-command record.") from error
        if type(item["references"]) is not list:
            raise ResourceRecordError("Saved native references require an array.")
        references = tuple(_reference(ref) for ref in cast(list[object], item["references"]))
        if [(ref.kind, ref.reference) for ref in references] != loads:
            raise ResourceRecordError("Saved load commands and native references disagree.")
        systems.update(ref.reference for ref in references if ref.resolved is None)
        files[path] = LinkedFile(path, digest, raw, references)
    if type(data["system_references"]) is not list or data["system_references"] != sorted(systems):
        raise ResourceRecordError("Saved OS shared-cache reference roster disagrees.")
    seen: set[str] = set()
    pending = [root]
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        if path not in files:
            raise ResourceRecordError("Saved linked graph has a missing root or target.")
        seen.add(path)
        pending.extend(ref.resolved for ref in files[path].references if ref.resolved is not None)
    if seen != set(files):
        raise ResourceRecordError("Saved linked graph contains unreachable native files.")
    return LinkedDependencies(
        root,
        context,
        architecture,
        build,
        tuple(files[path] for path in sorted(files)),
        tuple(sorted(systems)),
    )
