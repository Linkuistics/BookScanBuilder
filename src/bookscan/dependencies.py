"""Read-only native dependency characterization before uncommitted import work.

Static linked identities do not establish runtime font/ICC/config/dlopen inputs.
Keep that limitation in the returned record until those mechanisms are verified.
"""

import argparse
import importlib
import json
import platform
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

from PIL import features

from bookscan.native_setup import checked, default_cache, digest, tool
from bookscan.native_setup import preflight as helper_preflight
from bookscan.render import renderer_path
from bookscan.skew import NativeError

# LC_ID_DYLIB describes this file; it is not an incoming dependency.
# https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/EXTERNAL_HEADERS/mach-o/loader.h
LOADS = frozenset(
    {
        "LC_LOAD_DYLIB",
        "LC_LOAD_WEAK_DYLIB",
        "LC_REEXPORT_DYLIB",
        "LC_LOAD_UPWARD_DYLIB",
        "LC_LAZY_LOAD_DYLIB",
    }
)
LIMITATION = (
    "Static load-command identities only; runtime dlopen/font/ICC/config inputs remain unverified."
)


def load_commands(text: str, path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """Parse captured otool commands without native execution or path resolution."""
    blocks = re.split(r"(?m)^Load command ([0-9]+)\s*$", text)
    if len(blocks) < 3 or not blocks[0].startswith(str(path)):
        raise NativeError(f"Cannot read Mach-O load commands: {path}.")
    rpaths: list[str] = []
    loads: list[tuple[str, str]] = []
    for index in range(1, len(blocks), 2):
        if int(blocks[index]) != (index - 1) // 2:
            raise NativeError(f"Incomplete Mach-O command sequence: {path}.")
        lines = [line.strip() for line in blocks[index + 1].splitlines()]
        kinds = [line.removeprefix("cmd ") for line in lines if line.startswith("cmd ")]
        if len(kinds) != 1:
            raise NativeError(f"Malformed Mach-O command: {path}.")
        kind = kinds[0]
        if kind not in LOADS | {"LC_RPATH", "LC_ID_DYLIB"}:
            if "DYLIB" in kind or "RPATH" in kind:
                raise NativeError(f"Unverified Mach-O command {kind}: {path}.")
            continue
        field = "path" if kind == "LC_RPATH" else "name"
        values = [
            match[1]
            for line in lines
            if (match := re.fullmatch(rf"{field}\s+(.+) \(offset [0-9]+\)", line))
        ]
        if len(values) != 1:
            raise NativeError(f"Malformed {kind} {field}: {path}.")
        if kind == "LC_RPATH":
            rpaths.append(values[0])
        elif kind in LOADS:
            loads.append((kind, values[0]))
    return rpaths, loads


def _expand(value: str, loader: Path, executable: Path) -> Path:
    if value.startswith("@loader_path/"):
        return loader.parent / value.removeprefix("@loader_path/")
    if value == "@loader_path":
        return loader.parent
    if value.startswith("@executable_path/"):
        return executable.parent / value.removeprefix("@executable_path/")
    if value == "@executable_path":
        return executable.parent
    if value.startswith("/"):
        return Path(value)
    raise NativeError(f"Unverified relative/load reference {value}: {loader}.")


def linked_identity(
    executable: Path,
    *,
    executable_context: Path | None = None,
    check_cancel: Callable[[], None] = lambda: None,
) -> dict[str, object]:
    """Characterize one native-architecture static graph, without guessing dyld state.

    Ambiguous rpaths fail instead of claiming which candidate runtime dyld loaded.
    Weak loads are required here too: unsupported absence must not look complete.
    """
    check_cancel()
    if platform.system() != "Darwin" or platform.machine() not in {"arm64", "x86_64"}:
        raise NativeError("Static native dependency checks require a supported macOS architecture.")
    try:
        root = executable.resolve(strict=True)
        context_root = (executable_context or root).resolve(strict=True)
        inspector = tool("otool")
        os_build = checked(["/usr/bin/sw_vers", "-buildVersion"], check_cancel=check_cancel)
        if not os_build:
            raise NativeError("Missing actual macOS build identity.")
        records: dict[str, dict[str, object]] = {}
        systems: set[str] = set()
        seen: set[tuple[Path, tuple[Path, ...]]] = set()
        queue: list[tuple[Path, tuple[Path, ...]]] = [(root, ())]
        identities: dict[Path, str] = {}
        while queue:
            check_cancel()
            path, inherited = queue.pop()
            context = path, inherited
            if context in seen:
                continue
            seen.add(context)
            before = digest(path, check_cancel=check_cancel)
            raw = checked(
                [str(inspector), "-arch", platform.machine(), "-l", str(path)],
                check_cancel=check_cancel,
            )
            rpaths, loads = load_commands(raw, path)
            # The load chain contributes inherited runpaths. This is static
            # characterization; actual runtime selection still needs observation.
            # https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/RunpathDependentLibraries.html
            search = tuple(
                dict.fromkeys(
                    [_expand(value, path, context_root).resolve() for value in rpaths]
                    + list(inherited)
                )
            )
            refs: list[dict[str, str]] = []
            for kind, name in loads:
                check_cancel()
                if name.startswith(("/usr/lib/", "/System/Library/")):
                    if ".." in Path(name).parts:
                        raise NativeError(f"Unverified system reference {name}: {path}.")
                    systems.add(name)
                    refs.append(
                        {
                            "kind": kind,
                            "reference": name,
                            "identity": "OS shared-cache reference; disk bytes not claimed",
                        }
                    )
                    continue
                candidates = (
                    [directory / name.removeprefix("@rpath/") for directory in search]
                    if name.startswith("@rpath/")
                    else [_expand(name, path, context_root)]
                )
                matches = set(
                    candidate.resolve(strict=True)
                    for candidate in candidates
                    if candidate.is_file()
                )
                if not matches:
                    raise NativeError(f"Unresolved linked-file reference {name}: {path}.")
                if len(matches) != 1:
                    raise NativeError(f"Ambiguous linked-file reference {name}: {path}.")
                target = matches.pop()
                refs.append({"kind": kind, "reference": name, "resolved": str(target)})
                queue.append((target, search))
            if digest(path, check_cancel=check_cancel) != before:
                raise NativeError(f"Native dependency changed during characterization: {path}.")
            record: dict[str, object] = {"sha256": before, "load_commands": raw, "references": refs}
            if str(path) in records and records[str(path)] != record:
                raise NativeError(f"Context-dependent native dependency resolution: {path}.")
            records[str(path)] = record
            identities[path] = before
        for path, expected in identities.items():
            if digest(path, check_cancel=check_cancel) != expected:
                raise NativeError(f"Native dependency changed during characterization: {path}.")
        check_cancel()
        return {
            "root": str(root),
            "executable_context": str(context_root),
            "architecture": platform.machine(),
            "files": records,
            "os_build": os_build,
            "system_references": sorted(systems),
            "runtime_resources_verified": False,
            "limitation": LIMITATION,
        }
    except OSError as error:
        raise NativeError(
            f"Cannot characterize native dependencies for {executable}: {error}"
        ) from error


def extension_roots() -> dict[str, Path]:
    """Use imported extensions, including uv's real overlay rather than sysconfig's base."""
    result: dict[str, Path] = {}
    for name in ("PIL._imaging", "pikepdf._core"):
        module = importlib.import_module(name)
        value = cast(str | None, getattr(module, "__file__", None))
        if value is None:
            raise NativeError(f"No loaded extension identity for {name}.")
        result[name] = Path(value).resolve(strict=True)
    return result


def preflight(cache: Path, *, check_cancel: Callable[[], None] = lambda: None) -> dict[str, object]:
    """Combine unchanged helper verification with the chosen renderer/codec identities.

    No accepted pixels, project writes, cache changes or runtime resource credit.
    """
    helper = helper_preflight(cache, check_cancel=check_cancel)
    renderer = renderer_path(check_cancel=check_cancel)
    try:
        roots = {"pdftocairo": renderer, **extension_roots()}
        linked = {
            name: linked_identity(
                path,
                executable_context=renderer if name == "pdftocairo" else Path(sys.executable),
                check_cancel=check_cancel,
            )
            for name, path in roots.items()
        }
        # Exact installed Pillow 12.3.0 supported feature/codec versions.
        # https://pillow.readthedocs.io/en/stable/reference/features.html
        codecs = {name: features.version(name) for name in sorted(features.get_supported())}
        check_cancel()
        return {
            "helper": helper,
            "renderer": {"path": str(renderer), "version": "26.10.0"},
            "linked": linked,
            "pillow_features": codecs,
            "runtime_resources_verified": False,
            "limitation": LIMITATION,
        }
    except (OSError, ImportError) as error:
        raise NativeError(f"Cannot verify renderer/codec identities: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only helper/Cairo/static codec identities; runtime resources unverified."
    )
    parser.add_argument("--cache", type=Path, default=default_cache())
    args = parser.parse_args()
    try:
        record = preflight(args.cache)
    except NativeError as error:
        record = {
            "code": error.code,
            "exit_code": error.exit_code,
            "message": str(error),
            "remediation": error.remediation,
        }
        print(json.dumps(record, allow_nan=False))
        return error.exit_code
    print(json.dumps(record, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
