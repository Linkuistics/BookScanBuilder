"""Test-owned macOS linked-file characterization; not a runtime loader/preflight claim."""

import hashlib
import platform
from pathlib import Path

from bookscan.native_setup import checked, tool


def linked_files(executable: Path) -> dict[str, object]:
    """Record every reachable non-system LC_LOAD reference plus OS cache references.

    This follows static Mach-O load commands, not runtime dlopen/font/config
    access. Apple shared-cache files are named with the actual OS build, never
    falsely credited with an on-disk library hash. Runtime integration is pending.
    """
    otool = tool("otool")
    root = executable.resolve(strict=True)
    records: dict[str, object] = {}
    system: set[str] = set()
    queue: list[tuple[Path, tuple[Path, ...]]] = [(root, ())]
    while queue:
        path, inherited = queue.pop()
        if str(path) in records:
            continue
        loads = checked([str(otool), "-L", str(path)])
        commands = checked([str(otool), "-l", str(path)])
        lines = commands.splitlines()
        rpaths: list[Path] = []
        for index, line in enumerate(lines):
            if line.strip() == "cmd LC_RPATH":
                value = lines[index + 2].strip().removeprefix("path ").split(" (offset ")[0]
                expanded = value.replace("@loader_path", str(path.parent)).replace(
                    "@executable_path", str(root.parent)
                )
                rpaths.append(Path(expanded))
        search = tuple(rpaths) + inherited
        references: list[dict[str, str]] = []
        for line in loads.splitlines()[1:]:
            name = line.strip().split(" (compatibility version ")[0]
            if name.startswith(("/usr/lib/", "/System/Library/")):
                system.add(line.strip())
                references.append({"reference": name, "identity": "OS shared-cache reference"})
                continue
            if name.startswith("@rpath/"):
                candidates = [directory / name.removeprefix("@rpath/") for directory in search]
            else:
                candidates = [
                    Path(
                        name.replace("@loader_path", str(path.parent)).replace(
                            "@executable_path", str(root.parent)
                        )
                    )
                ]
            matching = [candidate.resolve() for candidate in candidates if candidate.is_file()]
            assert matching, f"Unresolved linked-file reference: {path}: {name}"
            target = matching[0]
            references.append({"reference": name, "resolved": str(target)})
            queue.append((target, search))
        records[str(path)] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "load_commands": commands,
            "libraries": loads,
            "references": references,
        }
    return {
        "files": records,
        "os_build": checked(["/usr/bin/sw_vers", "-buildVersion"]),
        "platform": platform.platform(),
        "system_references": sorted(system),
        "limitation": (
            "Static load-command closure only; dlopen/fonts/ICC/config "
            "and runtime preflight integration pending."
        ),
    }
