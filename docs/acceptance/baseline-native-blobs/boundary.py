"""Verify the same live F change, append-only notes and frozen implementation subjects."""

import gzip
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from verify import load

ROOT = Path(__file__).resolve().parents[3]
TASK = ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md"
ACCEPTANCE = "docs/acceptance/baseline-finite.md"
CHANGE = "ryouonnvvlkzyyxmxrpqxnuqrysrqtvy"
PARENT = "03eb30abe1ae485696e5deec25bfb229a42ecf69"
NEW = {
    "src/bookscan/native_blobs.py",
    "tests/test_native_blobs.py",
    "tests/native_blob_worker.py",
    "tests/native_blob_acceptance.py",
    "tests/native_blob_sample_acceptance.py",
}
EVIDENCE = {
    "README.md",
    "verify.py",
    "controls.py",
    "boundary.py",
    "boundary.json",
    "boundary-controls.json",
    "coverage.json",
    "evidence-controls.json",
    "index.json.gz",
    "raw-000.zippart",
    "raw-001.zippart",
    "raw-002.zippart",
}
ALLOWED = (
    {TASK, ACCEPTANCE, "Taskfile.yml"}
    | NEW
    | {"docs/acceptance/baseline-native-blobs/" + name for name in EVIDENCE}
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_change(change: str, parent: str, description: str, conflict: str) -> None:
    if (change, parent, description, conflict) != (CHANGE, PARENT, "", "clear"):
        raise ValueError("Wrong F change, parent, partial description or conflict")


def verify_scope(changed: set[str]) -> None:
    if not changed <= ALLOWED:
        raise ValueError("Foreign changed path")


def prefix(current: bytes, previous: bytes) -> None:
    if not current.startswith(previous):
        raise ValueError("Lost note prefix")


def run() -> dict[str, object]:
    retained = load(Path(__file__).parent)
    starting = json.loads(retained["starting-files.json"])
    paths = subprocess.check_output(["jj", "file", "list"], cwd=ROOT, text=True).splitlines()
    current = {name: sha((ROOT / name).read_bytes()) for name in paths}
    if not set(starting) <= set(current):
        raise ValueError("Starting tracked path removed")
    changed = {name for name, digest in current.items() if starting.get(name) != digest}
    verify_scope(changed)
    prefix((ROOT / TASK).read_bytes(), retained["task-prefix"])
    prefix((ROOT / ACCEPTANCE).read_bytes(), retained["acceptance-prefix"])
    taskfile = (ROOT / "Taskfile.yml").read_bytes()
    original_taskfile = taskfile.split(b"\n  process:native-blob-check:", 1)[0]
    if sha(original_taskfile) != starting["Taskfile.yml"]:
        raise ValueError("Original Taskfile changed")
    subjects: dict[str, Any] = json.loads(
        gzip.decompress(retained["frozen/subjects-before.json.gz"])
    )
    for name, expected in subjects.items():
        path = Path(name)
        if path == ROOT / TASK:
            measured = path.read_bytes().split(b"\nFinal paired native-blob measurement passed", 1)[
                0
            ]
            if sha(measured) != expected["sha256"]:
                raise ValueError("Measured task prefix changed")
            continue
        if path == ROOT / ACCEPTANCE:
            if sha(retained["acceptance-prefix"]) != expected["sha256"]:
                raise ValueError("Measured acceptance prefix changed")
            continue
        info = path.lstat()
        raw = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
        identity = [
            info.st_dev,
            info.st_ino,
            info.st_mode,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        ]
        if sha(raw) != expected["sha256"] or identity != expected["identity"]:
            raise ValueError("Frozen subject changed: " + name)
    facts = subprocess.check_output(
        [
            "jj",
            "log",
            "-r",
            "@",
            "--no-graph",
            "--no-pager",
            "-T",
            'change_id ++ "\\n" ++ '
            'parents.map(|p| p.commit_id()).join(" ") ++ "\\n" ++ '
            'description ++ "\\n" ++ if(conflict, "conflict", "clear")',
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    verify_change(*facts)
    return {
        "starting_paths": len(starting),
        "changed_paths": sorted(changed),
        "frozen_subjects": len(subjects),
        "change": CHANGE,
        "parent": PARENT,
        "description_empty": True,
        "conflicts": False,
        "prefixes_preserved": True,
        "finite_delivery": False,
    }


def controls() -> list[str]:
    outcomes: list[str] = []
    cases = {
        "wrong-change": ("wrong", PARENT, "", "clear"),
        "wrong-parent": (CHANGE, "wrong", "", "clear"),
        "partial-description": (CHANGE, PARENT, "partial", "clear"),
        "conflict": (CHANGE, PARENT, "", "conflict"),
    }
    for label, facts in cases.items():
        try:
            verify_change(*facts)
        except ValueError:
            outcomes.append(label)
        else:
            raise AssertionError(label)
    try:
        verify_scope({"src/bookscan/foreign.py"})
    except ValueError:
        outcomes.append("foreign-path")
    else:
        raise AssertionError("Foreign path passed")
    try:
        prefix(b"changed", b"original")
    except ValueError:
        outcomes.append("lost-prefix")
    else:
        raise AssertionError("Lost prefix passed")
    return outcomes


if __name__ == "__main__":
    print(json.dumps({"boundary": run(), "controls": controls()}, indent=2))
