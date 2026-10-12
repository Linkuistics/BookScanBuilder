"""Test-owned PID-bound dyld observation; no complete runtime-resource claim."""

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

PREFIX = re.compile(r"dyld\[([0-9]+)\]: (.*)")
UUID = r"[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}"
IMAGE = re.compile(rf"<({UUID})> (/.+)")


@dataclass(frozen=True)
class Log:
    images: tuple[tuple[str, str], ...]
    loader_messages: tuple[str, ...]
    diagnostics: str


def parse_log(stderr: str, pid: int) -> Log:
    """Keep events, opaque loader state messages and original application diagnostics.

    This grammar is characterized on the actual host, never a stable dyld ABI.
    Missing/changed UUID event syntax cannot silently become successful evidence.
    https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/LoggingDynamicLoaderEvents.html
    Current Apple logLoad source agrees with the observed UUID/path event form:
    https://github.com/apple-oss-distributions/dyld/blob/main/dyld/Loader.cpp
    """
    if pid <= 0:
        raise ValueError("Invalid observed child PID")
    images: list[tuple[str, str]] = []
    messages: list[str] = []
    diagnostics: list[str] = []
    by_path: dict[str, str] = {}
    for line in stderr.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if not content.startswith("dyld["):
            diagnostics.append(line)
            continue
        prefix = PREFIX.fullmatch(content)
        if prefix is None or int(prefix[1]) != pid:
            raise ValueError("Malformed or foreign-PID dyld event")
        event = prefix[2]
        if not event.startswith("<"):
            messages.append(event)
            continue
        image = IMAGE.fullmatch(event)
        if image is None or ".." in PurePosixPath(image[2]).parts:
            raise ValueError("Malformed dyld image UUID/path event")
        uuid, path = image[1], image[2]
        if path in by_path and by_path[path] != uuid:
            raise ValueError("One image path has conflicting mapped UUIDs")
        by_path[path] = uuid
        images.append((path, uuid))
    if not images:
        raise ValueError("No image events; loader observation unavailable")
    return Log(tuple(images), tuple(messages), "".join(diagnostics))


def verify_uuid(mapped: str, disk: str | None) -> None:
    if disk is None or re.fullmatch(UUID, disk) is None or disk != mapped:
        raise ValueError("Mapped/disk Mach-O UUID mismatch or missing UUID")
