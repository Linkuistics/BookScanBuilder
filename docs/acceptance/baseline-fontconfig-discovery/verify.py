"""Read-only reconstruction/current-host boundary check; no archival writes."""

import hashlib
import io
import json
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BOOKKEEPING = {
    str(ROOT / ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md"),
    str(ROOT / "docs/acceptance/baseline-finite.md"),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bytes_preserving_mode(path):
    mode = path.stat().st_mode
    try:
        if not mode & stat.S_IRUSR:
            path.chmod(mode | stat.S_IRUSR)
        return path.read_bytes()
    finally:
        if not mode & stat.S_IRUSR:
            path.chmod(mode)


def current(path):
    try:
        item = path.lstat()
    except FileNotFoundError:
        return {"absent": True}
    row = {"mode": stat.S_IMODE(item.st_mode), "device": item.st_dev, "inode": item.st_ino}
    if path.is_symlink():
        row["link"] = str(path.readlink())
        row["resolved"] = str(path.resolve())
    if path.is_dir():
        row["members"] = sorted(p.name for p in path.iterdir())
    elif path.is_file():
        data = bytes_preserving_mode(path)
        row.update(size=len(data), sha256=digest(data))
    elif path.is_symlink():
        row["target_absent"] = True
    else:
        raise ValueError(f"Unsupported input entry {path}")
    return row


def require_prefix(actual, prefix):
    if not actual.startswith(prefix):
        raise ValueError("Altered archived bookkeeping prefix")


def main():
    index = json.loads((HERE / "index.json").read_text())
    parts = []
    for item in index["parts"]:
        data = (HERE / item["name"]).read_bytes()
        if len(data) != item["size"] or digest(data) != item["sha256"]:
            raise ValueError("Changed archive part")
        parts.append(data)
    data = b"".join(parts)
    if len(data) != index["archive_size"] or digest(data) != index["archive_sha256"]:
        raise ValueError("Wrong archive reconstruction")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Duplicate archive entries")
        if set(archive.namelist()) != set(index["entries"]):
            raise ValueError("Wrong archive entry set")
        for name, item in index["entries"].items():
            raw = archive.read(name)
            if len(raw) != item["size"] or digest(raw) != item["sha256"]:
                raise ValueError(f"Changed retained entry {name}")
            path = Path(item["path"])
            if stat.S_IMODE(path.lstat().st_mode) != item["mode"]:
                raise ValueError(f"Changed raw mode {path}")
            actual = str(path.readlink()).encode() if item["kind"] == "symlink" else bytes_preserving_mode(path)
            if str(path) in BOOKKEEPING:
                require_prefix(actual, raw)
            elif actual != raw:
                raise ValueError(f"Changed retained raw subject {path}")
        subjects = json.loads(archive.read("frozen/subjects-before.json"))
        if subjects != json.loads(archive.read("frozen/subjects-after.json")):
            raise ValueError("Credited frozen input disagreement")
        measured = json.loads(archive.read("frozen/measurement.json"))
        report = json.loads(archive.read("regression-verification.json"))
        for prefix in (b"abcdef", b"complete original bookkeeping"):
            for wrong in (prefix[:-1], b"changed" + prefix, prefix[:2] + b"changed" + prefix[2:]):
                try:
                    require_prefix(wrong, prefix)
                except ValueError:
                    pass
                else:
                    raise ValueError("Wrong prefix control accepted")
        wheel_entries = [name for name in archive.namelist() if name.startswith("wheel/") and name.endswith(".whl")]
        if len(wheel_entries) != 1:
            raise ValueError("Expected one retained wheel")
        with zipfile.ZipFile(io.BytesIO(archive.read(wheel_entries[0]))) as wheel:
            product = {name.removeprefix("product/"): archive.read(name) for name in archive.namelist() if name.startswith("product/")}
            if set(product) != {name for name in wheel.namelist() if name.startswith("bookscan/")}:
                raise ValueError("Wrong wheel product members")
            for name, raw in product.items():
                if raw != wheel.read(name) or raw != (ROOT / "src" / name).read_bytes():
                    raise ValueError("Wrong source/wheel product bytes")
    initial = {name: current(Path(name)) for name in subjects}
    for name, expected in subjects.items():
        actual = dict(initial[name])
        if name in BOOKKEEPING:
            raw = bytes_preserving_mode(Path(name))
            if digest(raw[:expected["size"]]) != expected["sha256"]:
                raise ValueError("Changed measured bookkeeping prefix")
            actual.update(size=expected["size"], sha256=expected["sha256"])
        if actual != expected:
            raise ValueError(f"Changed measured input {name}")
    final = {name: current(Path(name)) for name in subjects}
    if initial != final:
        raise ValueError("Input changed during boundary reading")
    print(json.dumps({"archive_entries": len(index["entries"]), "archive_parts": len(parts),
                      "frozen_subjects": len(subjects), "units": len(measured["units"]),
                      "preserved_units": report["preserved_units"],
                      "preparation_cases": len(report["preparation"]["cases"]),
                      "writer_outcomes": len(report["preparation"]["faults"]),
                      "source_wheel_equal": True, "boundary_unchanged": True}))


if __name__ == "__main__":
    main()
