"""Bind saved Fontconfig discovery and copied-resource consistency without I/O.

These detached facts cannot attest native execution, file use, XML rewrite
correctness, configuration currency, glyph fidelity or an accepted project.
Historical paths are interpreted lexically, never reopened or resolved.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from bookscan import fontconfig, records
from bookscan.fontconfig_cache_record import CacheConstruction, restore_cache
from bookscan.fontconfig_record import restore_guard
from bookscan.linked_record import LinkedDependencies
from bookscan.linked_record import restore as restore_linked
from bookscan.resource_record import NamedResources, ResourceRecordError, restore_named

SNAPSHOT_LIMITATION = (
    "Supported selected configuration/font copy; native libraries/templates stay host-bound. "
    "No independent glyph truth."
)


@dataclass(frozen=True)
class SavedDiscovery:
    scope: fontconfig.ConfiguredScope
    binding: NamedResources
    linked: LinkedDependencies
    cache: CacheConstruction | None
    snapshot: SavedSnapshot | None


@dataclass(frozen=True)
class SavedSnapshot:
    root: str
    configuration_file: str
    selection: str
    original: SavedDiscovery


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(cast(dict[str, object], value)) != fields:
        raise ResourceRecordError("Unsupported saved Fontconfig discovery/snapshot fields.")
    return cast(dict[str, object], value)


def _json(value: object) -> None:
    try:
        records.decode(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"))
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
        raise ResourceRecordError("Invalid saved discovery JSON values.") from error


def _path(value: object) -> str:
    if type(value) is not str or "\0" in value:
        raise ResourceRecordError("Invalid saved snapshot path.")
    path = Path(value)
    if not path.is_absolute() or str(path) != value or ".." in path.parts:
        raise ResourceRecordError("Invalid saved canonical snapshot path.")
    return value


def _snapshot(value: object, warm: SavedDiscovery) -> SavedSnapshot:
    data = _object(
        value,
        {
            "method",
            "configuration_file",
            "selection",
            "root",
            "original",
            "runtime_resources_verified",
            "limitation",
        },
    )
    if (
        data["method"] != "copied-path-cache-redirect"
        or data["selection"] not in ("explicit", "captured-fontconfig")
        or data["runtime_resources_verified"] is not False
        or data["limitation"] != SNAPSHOT_LIMITATION
    ):
        raise ResourceRecordError("Unsupported saved Fontconfig copy claim.")
    root, config = _path(data["root"]), _path(data["configuration_file"])
    original = _restore(data["original"], original=True)
    files = {item.path: item for item in original.binding.files}
    if config not in original.scope.config_files or config not in files:
        raise ResourceRecordError("Saved copied configuration was not a loaded named source.")
    if warm.cache is None or warm.cache.cache_root != root + fontconfig.SNAPSHOT_CACHE:
        raise ResourceRecordError("Saved snapshot lacks its confined completed cache.")
    if original.linked != warm.linked or (
        original.binding.working_directory,
        original.binding.working_directory_identity,
    ) != (warm.binding.working_directory, warm.binding.working_directory_identity):
        raise ResourceRecordError("Saved copy changed its native graph or working context.")
    source, copied = original.scope, warm.scope
    for name in (
        *source.config_files,
        *source.config_dirs,
        *source.parsed_files,
        *source.effective_font_dirs,
        *source.effective_cache_dirs,
        *source.template_dirs,
    ):
        targets = {_path(name)}
        file = files.get(name)
        if file is not None and file.resolved is not None:
            targets.add(file.resolved)
        for tree in original.binding.directories:
            if tree.path == name and tree.entries is not None:
                targets.update(entry.resolved for entry in tree.entries if entry.path == name)
        if any(
            Path(target).is_relative_to(root) or Path(root).is_relative_to(target)
            for target in targets
        ):
            raise ResourceRecordError("Saved snapshot overlaps an original resource.")

    def mapped(name: str) -> str:
        return str(Path(root) / _path(name).lstrip("/"))

    loaded = set(source.config_files) | {
        name
        for name in source.parsed_files
        if not any(Path(name).is_relative_to(tree) for tree in source.template_dirs)
    }
    for field in ("config_files", "config_dirs"):
        if getattr(copied, field) != tuple(sorted(mapped(name) for name in getattr(source, field))):
            raise ResourceRecordError("Saved copied configuration scope contradicts its original.")
    parsed = tuple(sorted(mapped(name) if name in loaded else name for name in source.parsed_files))
    fonts = tuple(sorted(mapped(name) for name in source.effective_font_dirs))
    if (
        copied.parsed_files != parsed
        or copied.template_dirs != source.template_dirs
        or copied.font_dirs != fonts
        or copied.effective_font_dirs != fonts
        or copied.cache_dirs != (warm.cache.cache_root,)
        or copied.effective_cache_dirs != (warm.cache.cache_root,)
    ):
        raise ResourceRecordError("Saved copy has unconfined or contradictory configured routes.")
    warm_files = {item.path: item for item in warm.binding.files}
    for item in original.binding.files:
        if item.path in loaded:
            copied_file = warm_files.get(mapped(item.path))
            if copied_file is None or copied_file.resolved != mapped(item.path):
                raise ResourceRecordError("Saved copied configuration file retains a host route.")
        elif warm_files.get(item.path) != item:
            raise ResourceRecordError("Saved copy changed a host-bound native/template file.")
    warm_trees = {item.path: item for item in warm.binding.directories}
    source_trees = {item.path: item for item in original.binding.directories}
    for name in source.template_dirs:
        if warm_trees.get(name) != source_trees.get(name):
            raise ResourceRecordError("Saved copy changed a host-bound template inventory.")
    input_trees = {
        *source.config_dirs,
        *source.effective_font_dirs,
        *(name for name in source.config_files if name in source_trees),
    }
    for name in input_trees:
        before = source_trees[name]
        after = warm_trees.get(mapped(name))
        if after is None or (before.entries is None) != (after.entries is None):
            raise ResourceRecordError("Saved copied tree has contradictory presence.")
        if before.entries is None or after.entries is None:
            continue
        by_path = {entry.path: entry for entry in after.entries}
        if set(by_path) != {mapped(entry.path) for entry in before.entries}:
            raise ResourceRecordError("Saved copied tree changed its candidate inventory.")
        for entry in before.entries:
            copied_entry = by_path[mapped(entry.path)]
            resolved = mapped(entry.resolved if entry.kind == "dangling-symlink" else entry.path)
            if (
                copied_entry.kind != entry.kind
                or copied_entry.resolved != resolved
                or copied_entry.members != entry.members
                or (entry.kind != "dangling-symlink" and copied_entry.link_target is not None)
                or (entry.kind == "dangling-symlink" and copied_entry.link_target != resolved)
                or (
                    entry.kind == "file"
                    and entry.path not in loaded
                    and (copied_entry.size, copied_entry.sha256) != (entry.size, entry.sha256)
                )
            ):
                raise ResourceRecordError(
                    "Saved copied resource changed bytes or retains a host route."
                )
    return SavedSnapshot(root, config, cast(str, data["selection"]), original)


def _restore(value: object, *, original: bool = False) -> SavedDiscovery:
    if type(value) is not dict:
        raise ResourceRecordError("Saved Fontconfig discovery requires an object.")
    fields = {
        "fontconfig_version",
        "scope",
        "binding",
        "linked",
        "runtime_resources_verified",
        "limitation",
    }
    data = cast(dict[str, object], value)
    optional = set(data) & {"cache_construction", "resource_snapshot"}
    data = _object(data, fields | optional)
    if original and optional:
        raise ResourceRecordError("Saved original discovery cannot itself claim a cache or copy.")
    if (
        data["fontconfig_version"] != "2.18.3"
        or data["runtime_resources_verified"] is not False
        or data["limitation"] != fontconfig.LIMITATION
    ):
        raise ResourceRecordError("Unsupported saved Fontconfig discovery version/use claim.")
    scope = restore_guard(data["binding"])
    binding_data = cast(dict[str, object], data["binding"])
    if (
        scope is None
        or data["scope"] != cast(dict[str, object], binding_data["fontconfig_scope_guard"])["scope"]
    ):
        raise ResourceRecordError("Saved outer scope differs from its required configured guard.")
    binding = restore_named(data["binding"])
    linked = restore_linked(data["linked"], data["binding"])
    libraries = [
        item.path
        for item in linked.files
        if re.fullmatch(r"libfontconfig(?:\.[0-9]+)*\.dylib", Path(item.path).name)
    ]
    if len(libraries) != 1:
        raise ResourceRecordError("Saved discovery requires one linked Fontconfig library.")
    cache = restore_cache(data.get("cache_construction"), data["binding"])
    if "cache_construction" in data and (cache is None or cache.command[3] != libraries[0]):
        raise ResourceRecordError("Saved cache command does not use the discovered native library.")
    result = SavedDiscovery(scope, binding, linked, cache, None)
    if "resource_snapshot" in data:
        return SavedDiscovery(
            scope, binding, linked, cache, _snapshot(data["resource_snapshot"], result)
        )
    return result


def restore(value: object) -> SavedDiscovery:
    """Read a closed saved envelope and retain immutable, non-executable facts.

    The copied record binds its original selection and scope mapping. It cannot
    verify the historical XML transformation or turn matching resources into a
    complete native-use or glyph-fidelity claim. No environment is reconstructed.
    """
    _json(value)
    return _restore(value)
