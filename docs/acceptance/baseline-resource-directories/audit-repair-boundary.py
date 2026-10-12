from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path("/Users/antony/Development/BookScanBuilder")
WORK = Path("/private/tmp/bookscan-k63-audit-repair")
PREVIOUS = Path("/private/tmp/bookscan-k63-directory-work")
DEST = Path(__file__).parent
OUTPUT = DEST / "audit-repair-boundary.json"


def read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except PermissionError:
        scopes = [PREVIOUS / name for name in ("prepare-a", "prepare-b")]
        scopes += [WORK / name for name in ("preparation-final", "preparation-credited")]
        assert any(path.is_relative_to(scope) for scope in scopes)
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


def main() -> None:
    index = json.loads(read(DEST / "audit-repair-index.json"))
    frozen = json.loads(read(WORK / "verification.json"))
    assert frozen["subjects_before"] == frozen["subjects_after"]
    assert frozen["comparison_inputs_before"] == frozen["comparison_inputs_after"]
    assert frozen["unit_outcomes_itemwise_equal"]
    assert frozen["preparation_outcomes_itemwise_equal"]
    assert frozen["itemwise_reports_equal"] and not frozen["persistent_subject_mutations"]
    assert len(frozen["units"]) == 1024 and all(not children for _, children in frozen["units"])
    assert len(frozen["preparation"]["cases"]) == 9
    assert len(frozen["preparation"]["faults"]) == 38
    assert all(command["exit"] == 0 for command in frozen["checks"] + frozen["runs"])
    a = json.loads(read(WORK / "preserving-a.json"))
    assert a == json.loads(read(WORK / "preserving-b.json"))
    assert a["protected_originals"] == 166
    assert a["taskfile_addition"]["wrong_recipe_rejected"]
    paths = {Path(path) for path in frozen["subjects_before"]}
    paths.update(Path(path) for path in frozen["comparison_inputs_before"])
    paths.update(Path(path) for path in index["files"])
    paths.update(DEST / item["archive"] for item in index["blobs"].values())
    paths.update(DEST / name for name in index["dependencies"])
    paths.add(DEST / "audit-repair-index.json")
    paths.add(Path(__file__))
    before = {str(path): identity(path) for path in sorted(paths)}
    for path, expected in frozen["subjects_before"].items():
        assert identity(Path(path)) == expected, f"Frozen input moved: {path}"
    for path, expected in frozen["comparison_inputs_before"].items():
        assert identity(Path(path)) == expected, f"Comparison input moved: {path}"
    blobs = {}
    for key, item in index["blobs"].items():
        with zipfile.ZipFile(DEST / item["archive"]) as archive:
            data = archive.read(item["member"])
        assert sha(data) == key
        blobs[key] = data
    for path, item in index["files"].items():
        data = b"".join(blobs[key] for key in item["parts"])
        assert sha(data) == item["sha256"] and len(data) == item["bytes"]
        assert read(Path(path)) == data
        actual = identity(Path(path))
        assert all(actual[key] == item[key] for key in ("sha256", "mode", "symlink"))
    for name, expected in index["dependencies"].items():
        actual = identity(DEST / name)
        assert all(actual[key] == expected[key] for key in ("sha256", "mode", "symlink"))
    tracked = subprocess.check_output(["jj", "file", "list"], cwd=ROOT, text=True).splitlines()
    assert set(a["tracked_digests"]) <= set(tracked)
    for path, expected in a["tracked_digests"].items():
        assert sha(read(ROOT / path)) == expected
    added = set(tracked) - set(a["tracked_digests"])
    assert all(
        path.startswith("docs/acceptance/baseline-resource-directories/audit-repair-")
        for path in added
    )
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
    assert change == "ryouonnvvlkzyyxmxrpqxnuqrysrqtvy" and parent.startswith("03eb30ab")
    leaf = ROOT / ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md"
    assert leaf.is_file()
    assert before == {str(path): identity(path) for path in sorted(paths)}
    assert all(path.stat().st_size < 1048576 for path in DEST.iterdir())
    raw_inputs = (json.dumps(before, indent=2) + "\n").encode()
    compressed_inputs = gzip.compress(raw_inputs, mtime=0)
    assert len(compressed_inputs) < 1048576
    input_output = DEST / "audit-repair-boundary-inputs.json.gz"
    result = {
        "version": 1,
        "input_subjects": len(before),
        "frozen_subjects_preserved": 11445,
        "repair_raw_files": len(index["files"]),
        "repair_raw_chunks": len(blobs),
        "exact_reconstruction": True,
        "prior_archives_preserved": True,
        "units": 1024,
        "synthetic_preparation_cases": 9,
        "actual_writer_cases": 38,
        "itemwise_outcomes_equal": True,
        "f_change_id": change,
        "parent": parent,
        "leaf_live_unsealed": True,
        "product_handoff_complete": False,
        "graph_coverage": "Best effort; current code/contracts match metadata; "
        "full-byte/range fallback is retained.",
        "boundary_instrument_sha256": sha(read(Path(__file__))),
        "input_map": {
            "file": input_output.name,
            "sha256": sha(raw_inputs),
            "bytes": len(raw_inputs),
            "compressed_sha256": sha(compressed_inputs),
            "compressed_bytes": len(compressed_inputs),
        },
    }
    # The output is separate from the inputs and never carries its own digest.
    encoded = (json.dumps(result, indent=2) + "\n").encode()
    assert len(encoded) < 1048576
    input_output.write_bytes(compressed_inputs)
    OUTPUT.write_bytes(encoded)
    print(
        f"Boundary verified: {len(before)} inputs preserved; {len(index['files'])} repair files "
        "reconstruct exactly; same live/unsealed F; no complete handoff"
    )


if __name__ == "__main__":
    main()
