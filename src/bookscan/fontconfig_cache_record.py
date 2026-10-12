"""Read saved cache-construction consistency without historical native I/O.

This component does not attest initial emptiness, native execution, actual file
use, glyph fidelity or a complete accepted project. Outer discovery and copied
resource-snapshot records require separate readers. Returned facts are detached.
"""

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from bookscan import records
from bookscan.fontconfig_record import restore_guard
from bookscan.resource_record import (
    NamedResources,
    ResourceRecordError,
    restore_named,
)


@dataclass(frozen=True)
class CacheConstruction:
    cache_root: str
    command: tuple[str, ...]
    inputs: NamedResources


def restore_cache(value: object, binding: object) -> CacheConstruction | None:
    """Bind construction inputs to the completed configured named inventory.

    Effective cache aliases are checked against their saved resolved tree roots.
    Logical sysroot routes stay distinct. Construction inputs intentionally omit
    these mutable trees; their guard must equal the complete verified warm guard.
    No historical path resolution, environment reconstruction or execution occurs.
    """
    scope = restore_guard(binding)
    if value is None:
        return None
    try:
        records.decode(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except (ValueError, TypeError, RecursionError, records.RecordError) as error:
        raise ResourceRecordError("Invalid saved cache-construction JSON values.") from error
    if type(value) is not dict or set(cast(dict[str, object], value)) != {
        "method",
        "initially_empty",
        "cache_root",
        "command",
        "inputs",
    }:
        raise ResourceRecordError("Unsupported saved Fontconfig cache-construction fields.")
    data = cast(dict[str, object], value)
    if data["method"] != "FcConfigBuildFonts" or data["initially_empty"] is not True:
        raise ResourceRecordError("Unsupported saved Fontconfig cache-construction claim.")
    if scope is None:
        raise ResourceRecordError("Saved cache construction requires a completed scope guard.")
    root_value = data["cache_root"]
    if (
        type(root_value) is not str
        or "\0" in root_value
        or not Path(root_value).is_absolute()
        or str(Path(root_value)) != root_value
        or ".." in Path(root_value).parts
    ):
        raise ResourceRecordError("Invalid saved canonical cache root.")
    root = root_value
    warm = restore_named(binding)
    inputs = restore_named(data["inputs"])
    warm_data = cast(dict[str, object], binding)
    input_data = cast(dict[str, object], data["inputs"])
    if input_data.get("fontconfig_scope_guard") != warm_data["fontconfig_scope_guard"]:
        raise ResourceRecordError("Cache inputs and completed configured scope disagree.")
    trees = {item.path: item for item in warm.directories}
    mutable: set[str] = set()
    for item in warm.directories:
        if item.entries is not None:
            recorded_root = next(entry for entry in item.entries if entry.path == item.path)
            if recorded_root.resolved == root:
                mutable.add(item.path)
    if not mutable or any(str(Path(name)) not in mutable for name in scope.effective_cache_dirs):
        raise ResourceRecordError("Completed cache scope lacks its confined present tree.")
    for name in (
        *scope.config_files,
        *scope.config_dirs,
        *scope.parsed_files,
        *scope.template_dirs,
        *scope.effective_font_dirs,
    ):
        # Use saved identities only. Absent optional trees carry no resolved target;
        # their logical spelling cannot prove historical alias resolution.
        tree = trees.get(str(Path(name)))
        targets = [name]
        if tree is not None and tree.entries is not None:
            targets.extend(entry.resolved for entry in tree.entries if entry.path == tree.path)
        targets.extend(
            item.resolved
            for item in warm.files
            if item.path == str(Path(name)) and item.resolved is not None
        )
        if any(
            Path(target).is_relative_to(root) or Path(root).is_relative_to(target)
            for target in targets
        ):
            raise ResourceRecordError("Saved cache overlaps a configuration/font/template input.")
    fixed = replace(
        warm, directories=tuple(item for item in warm.directories if item.path not in mutable)
    )
    if inputs != fixed:
        raise ResourceRecordError(
            "Saved fixed cache-construction subjects changed or are incomplete."
        )
    command_value = data["command"]
    if type(command_value) is not list:
        raise ResourceRecordError("Saved Fontconfig construction command requires an array.")
    command_items = cast(list[object], command_value)
    if len(command_items) != 6 or any(type(item) is not str for item in command_items):
        raise ResourceRecordError("Unsupported saved Fontconfig construction command.")
    command = tuple(cast(list[str], command_items))
    if (
        command[1] != "-I"
        or command[4:] != ("--build-cache", root)
        or Path(command[2]).name != "fontconfig_probe.py"
        or re.fullmatch(r"libfontconfig(?:\.[0-9]+)*\.dylib", Path(command[3]).name) is None
    ):
        raise ResourceRecordError("Unsupported saved isolated Fontconfig cache command.")
    files = {item.path: item for item in inputs.files}
    if any(
        name not in files or files[name].resolved is None
        for name in (command[0], command[2], command[3])
    ):
        raise ResourceRecordError(
            "Cache command lacks present bound native/interpreter/probe files."
        )
    return CacheConstruction(root, command, inputs)
