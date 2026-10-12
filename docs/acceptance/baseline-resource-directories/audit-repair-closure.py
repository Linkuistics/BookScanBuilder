"""Read-only closure of historical evidence after named bookkeeping appends.

Run with an unused output file outside the repository and historical inputs.
The original boundary instrument, input map, report and archives stay intact.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path("/Users/antony/Development/BookScanBuilder")
DEST = Path(__file__).parent
BOOKKEEPING = {
    ROOT / ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md",
    ROOT / "docs/acceptance/baseline-finite.md",
}
FIXTURE_SCOPES = [
    Path("/private/tmp/bookscan-k63-directory-work") / name for name in ("prepare-a", "prepare-b")
] + [
    Path("/private/tmp/bookscan-k63-audit-repair") / name
    for name in ("preparation-final", "preparation-credited")
]


def read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except PermissionError:
        assert any(path.is_relative_to(scope) for scope in FIXTURE_SCOPES)
        mode = path.stat().st_mode & 0o7777
        try:
            path.chmod(mode | 0o400)
            return path.read_bytes()
        finally:
            path.chmod(mode)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "sha256": sha(read(path)),
        "mode": stat.st_mode & 0o7777,
        "device": stat.st_dev,
        "inode": stat.st_ino,
        "symlink": str(path.readlink()) if path.is_symlink() else None,
    }


def check_identity(
    actual: dict[str, object],
    expected: dict[str, object],
    content: bytes,
    prefix: bytes | None = None,
) -> None:
    checked = dict(actual)
    if prefix is not None:
        assert sha(prefix) == expected["sha256"], "Archived prefix identity differs"
        assert content.startswith(prefix), "Historical prefix changed or truncated"
        checked["sha256"] = sha(prefix)
    assert checked == expected, "Subject bytes or metadata changed"


def main(output: Path) -> None:
    output = output.resolve()
    assert not output.is_relative_to(ROOT) and not output.is_relative_to(
        Path("/private/tmp/bookscan-k63-audit-repair")
    ), "Write closure output in a separate generation"
    assert not output.exists() and not output.is_symlink(), "Output must be unused"
    boundary_path = DEST / "audit-repair-boundary.json"
    boundary = json.loads(read(boundary_path))
    compressed = read(DEST / boundary["input_map"]["file"])
    assert sha(compressed) == boundary["input_map"]["compressed_sha256"]
    assert len(compressed) == boundary["input_map"]["compressed_bytes"]
    raw = gzip.decompress(compressed)
    assert sha(raw) == boundary["input_map"]["sha256"]
    assert len(raw) == boundary["input_map"]["bytes"]
    records = json.loads(raw)
    paths = {Path(path) for path in records}
    tracked = subprocess.check_output(["jj", "file", "list"], cwd=ROOT, text=True).splitlines()
    paths.update(ROOT / path for path in tracked)
    paths.update({boundary_path, DEST / boundary["input_map"]["file"]})
    before = {str(path): identity(path) for path in sorted(paths)}

    # The digest-bound historical index supplies complete original prefixes.
    index_path = DEST / "audit-repair-index.json"
    assert identity(index_path) == records[str(index_path)]
    index = json.loads(read(index_path))
    blobs: dict[str, bytes] = {}
    for key, item in index["blobs"].items():
        archive_path = DEST / item["archive"]
        assert identity(archive_path) == records[str(archive_path)]
        with zipfile.ZipFile(archive_path) as archive:
            data = archive.read(item["member"])
        assert sha(data) == key, "Archive chunk changed"
        blobs[key] = data
    prefixes: dict[Path, bytes] = {}
    for path, item in index["files"].items():
        data = b"".join(blobs[key] for key in item["parts"])
        assert sha(data) == item["sha256"] and len(data) == item["bytes"]
        if Path(path) in BOOKKEEPING:
            prefixes[Path(path)] = data
    assert set(prefixes) == BOOKKEEPING, "Missing exact bookkeeping prefixes"
    for name, expected in records.items():
        path = Path(name)
        try:
            check_identity(identity(path), expected, read(path), prefixes.get(path))
        except AssertionError as error:
            raise AssertionError(f"Historical input differs: {path}: {error}") from error
    assert sha(read(DEST / "audit-repair-boundary.py")) == boundary["boundary_instrument_sha256"]
    assert boundary["exact_reconstruction"] and boundary["itemwise_outcomes_equal"]
    assert boundary["leaf_live_unsealed"] and not boundary["product_handoff_complete"]
    change = subprocess.check_output(
        ["jj", "log", "--no-pager", "--no-graph", "-r", "@", "-T", "change_id"],
        cwd=ROOT,
        text=True,
    )
    parent = subprocess.check_output(
        ["jj", "log", "--no-pager", "--no-graph", "-r", "@-", "-T", "commit_id"],
        cwd=ROOT,
        text=True,
    )
    assert change == boundary["f_change_id"] and parent == boundary["parent"]
    after = {str(path): identity(path) for path in sorted(paths)}
    assert before == after, "An input changed during closure"
    result = {
        "version": 1,
        "historical_input_subjects": len(records),
        "current_input_subjects": len(before),
        "historical_boundary_sha256": sha(read(boundary_path)),
        "historical_exact_inputs": len(records) - len(prefixes),
        "bookkeeping_prefixes": {
            str(path): {
                "historical_bytes": len(prefix),
                "historical_sha256": sha(prefix),
                "current_sha256": before[str(path)]["sha256"],
                "appended_bytes": len(read(path)) - len(prefix),
            }
            for path, prefix in sorted(prefixes.items())
        },
        "inputs_before": before,
        "inputs_after": after,
        "f_change_id": change,
        "parent": parent,
        "leaf_live_unsealed": True,
        "product_handoff_complete": False,
        "temporary_test_fixture_permission_changes": True,
    }
    with output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(
        f"Closure verified: {len(records)} historical subjects; exact named prefixes; "
        f"{len(before)} entire current subjects unchanged; same live F"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    main(parser.parse_args().output)
