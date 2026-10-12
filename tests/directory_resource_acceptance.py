"""Actual Fontconfig candidate growth and guarded rendering; no fidelity oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import cast
from xml.sax.saxutils import escape

import resource_acceptance

from bookscan.intake import snapshot
from bookscan.native_setup import digest, execute, tool
from bookscan.render import render_page, renderer_path
from bookscan.resources import ResourceBinding
from bookscan.skew import NativeError


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    truth = json.loads((fixtures / "truth.json").read_text())
    before = resource_acceptance.subjects(fixtures)
    native = resource_acceptance.run(fixtures, output / "file-binding")
    saved = snapshot(fixtures / "source.pdf", output / "snapshot.pdf")
    renderer = renderer_path()
    environment = dict(os.environ)
    environment.update(
        FONTCONFIG_FILE=str(fixtures / "a.conf"), FONTCONFIG_PATH=str(fixtures), FC_DEBUG="1"
    )
    guard = ResourceBinding.capture(
        [fixtures / "a.conf"],
        directories=[fixtures / "fonts-a", fixtures / "cache-a"],
        optional_directories=[output / "absent-optional"],
        environment=environment,
    )
    rendered = render_page(saved, saved.pages[0], renderer, resources=guard)
    rgb = hashlib.sha256(rendered.rgb).hexdigest()
    if (
        rgb != cast(dict[str, str], native["hashes"])["a"]
        or rendered.resource_binding != guard.record()
    ):
        raise ValueError("Directory guard changed pixels/provenance of stable subjects")
    # Output-owned deliberate mutations; the predeclared input fixture stays frozen.
    scope = output / "candidates"
    scope.mkdir()
    fonts = scope / "fonts"
    fonts.mkdir()
    original = fonts / Path(truth["font_files"][0]).name
    original.symlink_to(truth["font_files"][0])
    config = scope / "fonts.conf"
    cache = scope / "cache"
    cache.mkdir()
    config.write_text(
        "<fontconfig><dir>"
        + escape(str(fonts))
        + "</dir><cachedir>"
        + escape(str(cache))
        + "</cachedir></fontconfig>\n"
    )
    changed_environment = dict(environment)
    changed_environment["FONTCONFIG_FILE"] = str(config)
    warmed = execute([str(tool("fc-list")), "-f", "%{file}\\n"], environment=changed_environment)
    if warmed.returncode or str(original) not in warmed.stdout.splitlines():
        raise ValueError("Original actual Fontconfig candidate absent")
    guarded = ResourceBinding.capture(
        [config], directories=[fonts], environment=changed_environment
    )
    file_only = ResourceBinding.capture([config, original], environment=changed_environment)
    added = fonts / Path(truth["font_files"][1]).name
    added.symlink_to(truth["font_files"][1])
    # --force rebuilds even a timestamp-valid cache; needed for same-second additions.
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/fc-cache/fc-cache.c
    rebuilt = execute(
        [str(tool("fc-cache")), "--force", str(fonts)], environment=changed_environment
    )
    if rebuilt.returncode:
        raise ValueError("Test-owned Fontconfig cache rebuild failed")
    listed = execute([str(tool("fc-list")), "-f", "%{file}\\n"], environment=changed_environment)
    if listed.returncode or not {str(original), str(added)} <= set(listed.stdout.splitlines()):
        raise ValueError("Actual Fontconfig did not see added candidate")
    try:
        render_page(saved, saved.pages[0], renderer, resources=guarded)
    except NativeError as error:
        rejected = [error.code, error.exit_code]
    else:
        raise ValueError("Directory-growth control returned usable pixels")
    if rejected != ["DEPENDENCY_UNAVAILABLE", 5]:
        raise ValueError("Wrong directory-growth outcome")
    # Disproof: a file-only guard still returns pixels despite a new actual candidate.
    unguarded = render_page(saved, saved.pages[0], renderer, resources=file_only)
    if list(unguarded.size) != truth["size"]:
        raise ValueError("Wrong file-only control frame")
    after = resource_acceptance.subjects(fixtures)
    if before != after:
        raise ValueError("Frozen construction subjects changed")
    for path, expected_hash in truth["external_fonts"].items():
        if digest(Path(path)) != expected_hash:
            raise ValueError("Frozen external font changed")
    result: dict[str, object] = {
        "module": str(Path(__import__("bookscan.resources", fromlist=["x"]).__file__).resolve()),
        "native_file_binding": native,
        "binding": guard.record(),
        "rgb_sha256": rgb,
        "render_commands": [list(rendered.command), list(unguarded.command)],
        "controls": {
            "stable-directory-rgb": True,
            "actual-candidate-added": True,
            "candidate-growth-rejected": rejected,
            "wrong-file-only-guard-returns-pixels": True,
        },
        "candidate_scope_before": warmed.stdout.splitlines(),
        "candidate_scope_after": listed.stdout.splitlines(),
        "commands": [
            {
                "argv": row.args,
                "returncode": row.returncode,
                "stdout": row.stdout,
                "stderr": row.stderr,
            }
            for row in (warmed, rebuilt, listed)
        ],
        "subjects_before": before,
        "subjects_after": after,
        "runtime_resources_verified": False,
        "fidelity": truth["fidelity"],
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.fixtures, args.artifacts)
    print(json.dumps(result["controls"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
