"""Reconstruct retained evidence and verify its unchanged current-host subjects.

No native run or historical archive is rewritten. Later appends are permitted
only on the two exact digest-bound bookkeeping prefixes.
"""

from __future__ import annotations

import hashlib
import io
import json
import stat
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BOOKKEEPING = {
    str(ROOT / ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md"),
    str(ROOT / "docs/acceptance/baseline-finite.md"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> bytes:
    mode = path.stat().st_mode
    try:
        if not mode & stat.S_IRUSR:
            path.chmod(mode | stat.S_IRUSR)
        return path.read_bytes()
    finally:
        if not mode & stat.S_IRUSR:
            path.chmod(mode)


def current(path: Path) -> dict[str, object]:
    try:
        item = path.lstat()
    except FileNotFoundError:
        return {"absent": True}
    result: dict[str, object] = {
        "mode": stat.S_IMODE(item.st_mode),
        "device": item.st_dev,
        "inode": item.st_ino,
    }
    if path.is_symlink():
        result.update(link=str(path.readlink()), resolved=str(path.resolve()))
    if path.is_dir():
        result["members"] = sorted(child.name for child in path.iterdir())
    elif path.is_file():
        data = read(path)
        result.update(size=len(data), sha256=sha(data))
    elif path.is_symlink():
        result["target_absent"] = True
    else:
        raise ValueError(f"Unsupported frozen subject: {path}")
    return result


def require_equal(left: object, right: object) -> None:
    if left != right:
        raise ValueError("Per-item evidence disagreement")


def require_prefix(actual: bytes, expected: bytes) -> None:
    if not actual.startswith(expected):
        raise ValueError("Altered bookkeeping prefix")


def main() -> int:
    checker_bytes = Path(__file__).read_bytes()
    index_bytes = (HERE / "index.json").read_bytes()
    index = json.loads(index_bytes)
    parts: list[bytes] = []
    for item in index["parts"]:
        data = (HERE / item["name"]).read_bytes()
        require_equal((len(data), sha(data)), (item["size"], item["sha256"]))
        parts.append(data)
    joined = b"".join(parts)
    require_equal((len(joined), sha(joined)), (index["archive_size"], index["archive_sha256"]))
    subjects_before: dict[str, dict[str, object]]
    with zipfile.ZipFile(io.BytesIO(joined)) as archive:
        names = archive.namelist()
        require_equal(len(names), len(set(names)))
        require_equal(set(names), set(index["entries"]))
        for name, item in index["entries"].items():
            raw = archive.read(name)
            require_equal((len(raw), sha(raw)), (item["size"], item["sha256"]))
            path = Path(item["path"])
            require_equal(stat.S_IMODE(path.lstat().st_mode), item["mode"])
            actual = str(path.readlink()).encode() if item["kind"] == "symlink" else read(path)
            if str(path) in BOOKKEEPING:
                require_prefix(actual, raw)
            else:
                require_equal(actual, raw)
        before = json.loads(archive.read("frozen/subjects-before.json"))
        require_equal(before, json.loads(archive.read("frozen/subjects-after.json")))
        measured = json.loads(archive.read("frozen/measurement.json"))
        regression = json.loads(archive.read("instruments/regression-verification.json"))
        require_equal(regression["subjects_before"], regression["subjects_after"])
        subjects_before = {name: current(Path(name)) for name in before}
        for name, expected in before.items():
            actual = dict(subjects_before[name])
            if name in BOOKKEEPING:
                raw = read(Path(name))
                require_equal(sha(raw[: expected["size"]]), expected["sha256"])
                actual.update(size=expected["size"], sha256=expected["sha256"])
            if actual != expected:
                raise ValueError(f"Changed frozen subject: {name}")
        wheels = [name for name in names if name.startswith("wheels/") and name.endswith(".whl")]
        require_equal(len(wheels), 1)
        with zipfile.ZipFile(io.BytesIO(archive.read(wheels[0]))) as wheel:
            product = {
                name.removeprefix("product/"): archive.read(name)
                for name in names
                if name.startswith("product/")
            }
            require_equal(
                set(product), {name for name in wheel.namelist() if name.startswith("bookscan/")}
            )
            for name, raw in product.items():
                require_equal(raw, wheel.read(name))
                require_equal(raw, read(ROOT / "src" / name))
        for bad in (b"origina", b"changed original", b"orXXXiginal"):
            try:
                require_prefix(bad, b"original")
            except ValueError:
                pass
            else:
                raise ValueError("Wrong prefix control accepted")
    require_equal(subjects_before, {name: current(Path(name)) for name in subjects_before})
    require_equal(index_bytes, (HERE / "index.json").read_bytes())
    require_equal(checker_bytes, Path(__file__).read_bytes())
    require_equal(
        sha(joined), sha(b"".join((HERE / item["name"]).read_bytes() for item in index["parts"]))
    )
    print(
        json.dumps(
            {
                "archive_entries": len(index["entries"]),
                "archive_parts": len(parts),
                "frozen_subjects": len(subjects_before),
                "units": len(measured["units"]),
                "preserved_units": regression["preserved_units"],
                "preparation_cases": len(regression["preparation"]["cases"]),
                "writer_outcomes": len(regression["preparation"]["faults"]),
                "source_wheel_equal": True,
                "boundary_unchanged": True,
                "runtime_resources_verified": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
