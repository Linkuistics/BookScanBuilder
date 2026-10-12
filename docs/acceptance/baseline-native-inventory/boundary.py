"""Check the same live F change, preserved starting bytes and frozen subject identities."""

import gzip
import json
import os
import subprocess
from pathlib import Path

from verify import load, sha

ROOT = Path(__file__).resolve().parents[3]
TASK = ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md"
ACCEPTANCE = "docs/acceptance/baseline-finite.md"
CHANGE = "ryouonnvvlkzyyxmxrpqxnuqrysrqtvy"
PARENT = "03eb30abe1ae485696e5deec25bfb229a42ecf69"
EVIDENCE = {
    "README.md",
    "verify.py",
    "controls.py",
    "boundary.py",
    "coverage.json",
    "boundary.json",
    "evidence-controls.json",
    "index.json.gz",
    *(f"raw-{number:03}.zippart" for number in range(5)),
}
ALLOWED = {
    TASK,
    ACCEPTANCE,
    "Taskfile.yml",
    "src/bookscan/assessment.py",
    "src/bookscan/native_inventory_record.py",
    "tests/test_native_inventory_record.py",
    "tests/native_inventory_acceptance.py",
} | {"docs/acceptance/baseline-native-inventory/" + name for name in EVIDENCE}


def identity(change: str, parent: str, description: str, conflict: str) -> None:
    if (change, parent, description, conflict) != (CHANGE, PARENT, "", "clear"):
        raise ValueError("Wrong change, parent, partial description or conflict")


def scope(changed: set[str]) -> None:
    if not changed <= ALLOWED:
        raise ValueError("Foreign changed path")


def prefix(current: bytes, previous: bytes) -> None:
    if not current.startswith(previous):
        raise ValueError("Lost note prefix")


def run() -> dict[str, object]:
    retained = load(Path(__file__).parent)
    starting: dict[str, str] = json.loads(retained["starting-files.json"])
    paths = subprocess.check_output(["jj", "file", "list"], cwd=ROOT, text=True).splitlines()
    current = {name: sha((ROOT / name).read_bytes()) for name in paths}
    if not set(starting) <= set(current):
        raise ValueError("Starting tracked path removed")
    changed = {name for name, digest in current.items() if starting.get(name) != digest}
    scope(changed)
    prefix((ROOT / TASK).read_bytes(), retained["task-prefix"])
    prefix((ROOT / ACCEPTANCE).read_bytes(), retained["acceptance-prefix"])
    prefix((ROOT / "Taskfile.yml").read_bytes(), retained["taskfile-prefix"])
    subjects = json.loads(gzip.decompress(retained["final/subjects-before.json.gz"]))
    for name, expected in subjects.items():
        path = Path(name)
        if path == ROOT / TASK:
            prefix(path.read_bytes(), retained["measured-task-prefix"])
            if sha(retained["measured-task-prefix"]) != expected["sha256"]:
                raise ValueError("Measured task prefix changed")
            continue
        if path == ROOT / ACCEPTANCE:
            if sha(retained["acceptance-prefix"]) != expected["sha256"]:
                raise ValueError("Measured acceptance prefix changed")
            continue
        info = path.lstat()
        raw = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
        fields = [
            info.st_dev,
            info.st_ino,
            info.st_mode,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        ]
        if sha(raw) != expected["sha256"] or fields != expected["identity"]:
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
            'change_id ++ "\\n" ++ parents.map(|p| p.commit_id()).join(" ") ++ "\\n" ++ '
            'description ++ "\\n" ++ if(conflict, "conflict", "clear")',
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    identity(*facts)
    return {
        "starting_paths": len(starting),
        "changed_paths": sorted(changed),
        "frozen_subjects": len(subjects),
        "change": CHANGE,
        "parent": PARENT,
        "description_empty": True,
        "conflicts": False,
        "prefixes_preserved": True,
        "public_finite_delivery": False,
    }


def controls() -> list[str]:
    outcomes: list[str] = []
    for label, facts in {
        "wrong-change": ("wrong", PARENT, "", "clear"),
        "wrong-parent": (CHANGE, "wrong", "", "clear"),
        "partial-description": (CHANGE, PARENT, "partial", "clear"),
        "conflict": (CHANGE, PARENT, "", "conflict"),
    }.items():
        try:
            identity(*facts)
        except ValueError:
            outcomes.append(label)
        else:
            raise AssertionError(label)
    try:
        scope({"src/bookscan/foreign.py"})
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
