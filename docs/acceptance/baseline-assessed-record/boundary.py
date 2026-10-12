"""Check this continuation's exact change, scope, prefixes and frozen input bytes."""

import base64
import gzip
import hashlib
import io
import json
import os
import subprocess
import zipfile
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from verify import verify

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parents[2]
TASK = ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md"
NOTES = {TASK, "docs/acceptance/baseline-finite.md"}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def run() -> dict[str, object]:
    evidence = verify(HERE)
    starting: dict[str, str] = json.loads(gzip.decompress((HERE / "starting.json.gz").read_bytes()))
    prefixes: dict[str, str] = json.loads(gzip.decompress((HERE / "prefixes.json.gz").read_bytes()))
    current = set(subprocess.check_output(["jj", "file", "list"], cwd=ROOT, text=True).splitlines())
    assert set(starting) <= current
    changed = sorted(
        name for name, digest in starting.items() if sha((ROOT / name).read_bytes()) != digest
    )
    assert set(changed) == set(prefixes)
    for name, encoded in prefixes.items():
        original = base64.b64decode(encoded, validate=True)
        assert sha(original) == starting[name]
        assert (ROOT / name).read_bytes().startswith(original)
    extra = current - set(starting)
    source = {
        "src/bookscan/assessed_record.py",
        "tests/test_assessed_record.py",
        "tests/assessed_record_acceptance.py",
    }
    assert {
        name for name in extra if not name.startswith("docs/acceptance/baseline-assessed-record/")
    } == source
    allowed = {
        "README.md",
        "verify.py",
        "controls.py",
        "boundary.py",
        "index.json.gz",
        "starting.json.gz",
        "prefixes.json.gz",
        "coverage.json.gz",
        "boundary-result.json",
        *(f"raw-{n:03}.zippart" for n in range(4)),
    }
    assert all(Path(name).name in allowed for name in extra - source)
    vcs = subprocess.check_output(
        [
            "jj",
            "log",
            "--no-pager",
            "--no-graph",
            "-r",
            "@",
            "-T",
            'change_id ++ "\\n" ++ description',
        ],
        cwd=ROOT,
        text=True,
    )
    assert vcs == "ryouonnvvlkzyyxmxrpqxnuqrysrqtvy\n"
    parent = subprocess.check_output(
        ["jj", "log", "--no-pager", "--no-graph", "-r", "@-", "-T", "commit_id"],
        cwd=ROOT,
        text=True,
    )
    assert parent == "03eb30abe1ae485696e5deec25bfb229a42ecf69"
    assert not subprocess.check_output(
        ["jj", "log", "--no-pager", "--no-graph", "-r", "conflicts() & @", "-T", "commit_id"],
        cwd=ROOT,
    )
    index: dict[str, Any] = json.loads(gzip.decompress((HERE / "index.json.gz").read_bytes()))
    raw = b"".join((HERE / part["name"]).read_bytes() for part in index["parts"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:

        def read(name: str) -> bytes:
            return archive.read("blobs/" + index["entries"][name]["sha256"])

        subjects = json.loads(gzip.decompress(read("final/subjects-before.json.gz")))
        for name, expected in subjects.items():
            path = Path(name)
            relative = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else None
            if relative in NOTES:
                prefix = (
                    read("repo/" + relative)
                    if relative == TASK
                    else base64.b64decode(prefixes[relative])
                )
                assert path.read_bytes().startswith(prefix)
                continue
            info = path.lstat()
            content = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
            assert sha(content) == expected["sha256"], name
            identity = [
                info.st_dev,
                info.st_ino,
                info.st_mode,
                info.st_size,
                info.st_mtime_ns,
                info.st_ctime_ns,
            ]
            assert identity == expected["identity"], name
    return {
        "starting_files": len(starting),
        "changed_existing": changed,
        "new_files": sorted(extra),
        "frozen_subjects": len(subjects),
        "evidence": evidence,
        "finite_delivered": False,
    }


def disprove() -> list[str]:
    """Change instrument observations only; never edit the working tree."""
    original_output, original_read = subprocess.check_output, Path.read_bytes
    refused: list[str] = []
    for fault in ("wrong-change", "wrong-parent", "foreign-path", "lost-prefix"):

        def output(args: list[str], **kwargs: Any) -> Any:
            value = cast(str | bytes, original_output(args, **kwargs))
            if fault == "wrong-change" and "-r" in args and args[args.index("-r") + 1] == "@":
                return "foreign-change\n"
            if fault == "wrong-parent" and "-r" in args and args[args.index("-r") + 1] == "@-":
                return "a" * 40
            if fault == "foreign-path" and args[:3] == ["jj", "file", "list"]:
                assert isinstance(value, str)
                return value + "foreign-edit.py\n"
            return value

        def read(path: Path) -> bytes:
            value = original_read(path)
            return value[1:] if fault == "lost-prefix" and path == ROOT / TASK else value

        with (
            patch("subprocess.check_output", side_effect=output),
            patch.object(Path, "read_bytes", read),
        ):
            try:
                run()
            except AssertionError:
                refused.append(fault)
            else:
                raise AssertionError("Wrong boundary accepted: " + fault)
    return refused


if __name__ == "__main__":
    result = run()
    result["refused_boundary_controls"] = disprove()
    print(json.dumps(result, sort_keys=True))
