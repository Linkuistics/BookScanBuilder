"""Run paired native cleanup diagnostics with frozen subjects and itemwise results.

Exit 1 means required preservation tests failed. This is a red diagnostic, not
a product acceptance command. Output directories must be unused.
"""

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import cast

from bookscan.dependencies import linked_identity
from bookscan.render import renderer_path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def subjects(paths: set[Path]) -> dict[str, object]:
    result: dict[str, object] = {}
    for path in sorted(paths):
        info = path.lstat()
        item: dict[str, object] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size": info.st_size,
            "mode": info.st_mode,
            "device": info.st_dev,
            "inode": info.st_ino,
            "mtime_ns": info.st_mtime_ns,
            "ctime_ns": info.st_ctime_ns,
        }
        if stat.S_ISLNK(info.st_mode):
            item["link"] = os.readlink(path)
        result[str(path)] = item
    return result


def outcomes(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for case in ET.parse(path).iter("testcase"):
        name = str(case.get("classname")) + "::" + str(case.get("name"))
        assert name not in result
        outcome = "passed"
        for child in case:
            if child.tag in {"failure", "error", "skipped"}:
                outcome = child.tag
        result[name] = outcome
    assert result
    return result


def run(artifacts: Path) -> int:
    artifacts.mkdir()
    linked = linked_identity(renderer_path())
    write(artifacts / "native-load-identity.json", linked)
    paths = {
        REPO / "Taskfile.yml",
        REPO / "pyproject.toml",
        REPO / "uv.lock",
        REPO / "CONTEXT.md",
        Path(sys.executable),
        Path(sys.executable).resolve(),
        Path("/opt/homebrew/Cellar/fontconfig/2.18.3/include/fontconfig/fontconfig.h"),
    }
    for root in (REPO / "src", HERE, REPO / "docs/specs", REPO / "docs/adr"):
        paths.update(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for root in (REPO / ".venv/lib", Path(sys.base_prefix) / "lib/python3.12"):
        paths.update(
            p
            for p in root.rglob("*")
            if p.is_file() and p.suffix != ".pyc" and "__pycache__" not in p.parts
        )
    paths.update(Path(name) for name in cast(dict[str, object], linked["files"]))
    templates = Path("/opt/homebrew/Cellar/fontconfig/2.18.3/share/fontconfig/conf.avail")
    paths.update(p for p in templates.rglob("*") if p.is_file())
    before = subjects(paths)
    write(artifacts / "subjects-before.json", before)
    per_run: list[dict[str, str]] = []
    exit_codes: list[int] = []
    for name in ("a", "b"):
        output = artifacts / name
        output.mkdir()
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            str(HERE / "preservation_cases.py"),
            "--basetemp=" + str(output / "cases"),
            "--junitxml=" + str(output / "results.xml"),
        ]
        with (
            (output / "stdout.log").open("wb") as stdout,
            (output / "stderr.log").open("wb") as stderr,
        ):
            completed = subprocess.run(command, cwd=REPO, stdout=stdout, stderr=stderr, check=False)
        exit_codes.append(completed.returncode)
        write(output / "command.json", {"argv": command, "exit_code": completed.returncode})
        per_run.append(outcomes(output / "results.xml"))
        write(output / "subjects-after.json", subjects(paths))
        assert subjects(paths) == before, "A diagnostic subject changed during measurement"
    assert per_run[0] == per_run[1], "The two readings disagree item by item"
    controls = {
        name: value
        for name, value in per_run[0].items()
        if "test_clean_controls[" in name or "test_native_cache_replaces_precreated_output" in name
    }
    preservation = {
        name: value
        for name, value in per_run[0].items()
        if "test_changed_entries_survive_cleanup[" in name
    }
    assert len(controls) + len(preservation) == len(per_run[0])
    assert controls and preservation
    report = {
        "paired_outcomes": per_run[0],
        "exit_codes": exit_codes,
        "controls_passed": all(value == "passed" for value in controls.values()),
        "preservation_passed": all(value == "passed" for value in preservation.values()),
        "frozen_subjects": len(before),
        "public_create_delivered": False,
        "limitation": (
            "Empty test-owned font trees; no collection reads, glyph/fidelity or public workflow "
            "claim. OS shared-cache bytes and the complete host runtime/dynamic-open graph "
            "are not frozen. "
            "Generated mutable test subjects are recorded in per-case observations."
        ),
    }
    write(artifacts / "report.json", report)
    print(
        json.dumps(
            {
                key: report[key]
                for key in ("controls_passed", "preservation_passed", "frozen_subjects")
            }
        )
    )
    assert report["controls_passed"], "Diagnostic clean/native controls failed"
    return 0 if report["preservation_passed"] else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.artifacts.absolute()))


if __name__ == "__main__":
    main()
