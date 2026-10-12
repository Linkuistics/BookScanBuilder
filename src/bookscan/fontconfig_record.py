"""Restore saved configuration-only scope guards without historical native I/O.

Inventory consistency cannot attest renderer file use, configuration currency,
glyph fidelity or an accepted project. Outer discovery/cache/snapshot records
require separate semantic readers. Returned scopes are facts, not live guards.
"""

from pathlib import Path
from typing import cast

from bookscan.fontconfig import FIELDS, LIMITATION, ConfiguredScope
from bookscan.resource_record import ResourceRecordError, restore_named


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(cast(dict[str, object], value)) != fields:
        raise ResourceRecordError("Unsupported saved Fontconfig scope-guard fields.")
    return cast(dict[str, object], value)


def _paths(value: object) -> tuple[str, ...]:
    if type(value) is not list:
        raise ResourceRecordError("Saved Fontconfig paths require arrays.")
    items = cast(list[object], value)
    if any(type(item) is not str or "\0" in item or not Path(item).is_absolute() for item in items):
        raise ResourceRecordError("Invalid saved absolute Fontconfig path.")
    paths = cast(list[str], items)
    if paths != sorted(set(paths)):
        raise ResourceRecordError("Saved Fontconfig paths must be sorted and unique.")
    return tuple(paths)


def restore_guard(value: object) -> ConfiguredScope | None:
    """Read a named binding and its optional version-3 configuration scope.

    Optional absent trees remain valid recorded absences. Logical font/cache
    roots need not equal effective roots (for example under a historical sysroot).
    No environment values or historical files/native execution are reconstructed.
    """
    named = restore_named(value)  # Also checks UTF-8 JSON/exact scalar and inventory meaning.
    data = cast(dict[str, object], value)
    if "fontconfig_scope_guard" not in data:
        return None
    guard = _object(
        data["fontconfig_scope_guard"], {"version", "scope", "verification", "limitation"}
    )
    if (
        type(guard["version"]) is not int
        or guard["version"] != 3
        or guard["verification"] != "fresh-configuration-only-rediscovery"
        or guard["limitation"] != LIMITATION
    ):
        raise ResourceRecordError(
            "Unsupported saved Fontconfig guard version or verification claim."
        )
    scope = _object(guard["scope"], set(FIELDS))
    result = ConfiguredScope(*(_paths(scope[field]) for field in FIELDS))
    if (
        not result.config_files
        or not result.cache_dirs
        or not result.effective_cache_dirs
        or len(result.template_dirs) != 1
        or not result.parsed_files
        or (result.font_dirs and not result.effective_font_dirs)
    ):
        raise ResourceRecordError("Incomplete saved Fontconfig configured scope.")
    files = {item.path: item for item in named.files}
    trees = {item.path: item for item in named.directories}
    for path in result.config_files:
        key = str(Path(path))
        file, tree = files.get(key), trees.get(key)
        if file is not None and tree is not None:
            raise ResourceRecordError("Fontconfig configuration cannot be both file and directory.")
        if not (
            (file is not None and file.resolved is not None)
            or (tree is not None and tree.entries is not None)
        ):
            raise ResourceRecordError("Loaded Fontconfig configuration lacks a present inventory.")
    entries = [item for tree in named.directories for item in (tree.entries or ())]
    for path in result.parsed_files:
        file = files.get(str(Path(path)))
        if file is None or file.resolved is None:
            raise ResourceRecordError(
                "Parsed Fontconfig file lacks a present named-file inventory."
            )
        for entry in entries:
            if entry.path == file.path and (
                entry.kind != "file"
                or (entry.resolved, entry.device, entry.inode, entry.size, entry.sha256)
                != (file.resolved, file.device, file.inode, file.size, file.sha256)
            ):
                raise ResourceRecordError(
                    "Parsed Fontconfig file and directory inventory disagree."
                )
    for path in (
        *result.config_dirs,
        *result.effective_font_dirs,
        *result.effective_cache_dirs,
        *result.template_dirs,
    ):
        if str(Path(path)) not in trees:
            raise ResourceRecordError(
                "Fontconfig configured directory lacks its named tree inventory."
            )
    return result
