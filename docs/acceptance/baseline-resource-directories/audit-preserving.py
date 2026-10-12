import copy
import gzip
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path("/Users/antony/Development/BookScanBuilder")
WORK = Path("/private/tmp/bookscan-k63-directory-work")
DEST = ROOT / "docs/acceptance/baseline-resource-directories"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(path):
    try:
        return path.read_bytes()
    except PermissionError:
        assert path.is_relative_to(WORK / "prepare-a") or path.is_relative_to(WORK / "prepare-b")
        mode = path.stat().st_mode & 0o7777
        try:
            path.chmod(mode | 0o400)
            return path.read_bytes()
        finally:
            path.chmod(mode)


def equal(a, b):
    assert a == b, "Wrong bytes/identity/outcome"


TASKFILE_ADDITION = (
    b"\n  process:directory-evidence-check:\n"
    b"    desc: Audit the retained directory measurement against this Mac's "
    b"original host subjects\n"
    b"    cmds:\n"
    b"      - uv run --locked python "
    b"docs/acceptance/baseline-resource-directories/audit-preserving.py\n"
)


def check_taskfile(archived: bytes, actual: bytes) -> None:
    equal(archived + TASKFILE_ADDITION, actual)


try:
    equal("correct", "wrong")
except AssertionError:
    pass
else:
    raise AssertionError("Wrong byte control credited")
paths = subprocess.check_output(["jj", "file", "list"], cwd=ROOT, text=True).splitlines()
current = {p: sha(read(ROOT / p)) for p in paths}
before = json.loads((WORK / "before.json").read_text())
assert set(before) <= set(current)
allowed = {
    ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md",
    "docs/acceptance/baseline-finite.md",
    "Taskfile.yml",
    "src/bookscan/resources.py",
}
changed = {p for p in before if before[p] != current[p]}
assert changed == allowed
for p, name in [
    (
        ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md",
        "starting/.grove/40-k47/01-k53/11-impl--baseline-finite-k63.md",
    ),
    ("docs/acceptance/baseline-finite.md", "starting/docs/acceptance/baseline-finite.md"),
]:
    old = read(WORK / name)
    equal(sha(old), before[p])
    assert read(ROOT / p).startswith(old)
old = read(WORK / "starting/Taskfile.yml")
equal(sha(old), before["Taskfile.yml"])
assert read(ROOT / "Taskfile.yml").startswith(old)
new = {"tests/test_resource_directories.py", "tests/directory_resource_acceptance.py"}
assert new <= set(current) - set(before)
assert all(
    p in new or p.startswith("docs/acceptance/baseline-resource-directories/")
    for p in set(current) - set(before)
)
index = json.loads(gzip.decompress(read(DEST / "file-index.json.gz")))
blobs = {}
for key, item in index["blobs"].items():
    with zipfile.ZipFile(DEST / item["archive"]) as z:
        b = z.read(item["member"])
    equal(sha(b), key)
    blobs[key] = b
taskfile_bytes = None
for path, item in index["files"].items():
    b = b"".join(blobs[key] for key in item["parts"])
    equal(sha(b), item["sha256"])
    equal(len(b), item["bytes"])
    if path == str(ROOT / "Taskfile.yml"):
        taskfile_bytes = b
        check_taskfile(b, read(Path(path)))
        try:
            check_taskfile(b, b + TASKFILE_ADDITION.replace(b"uv run", b"uv execute"))
        except AssertionError:
            pass
        else:
            raise AssertionError("Wrong additive recipe credited")
    else:
        equal(b, read(Path(path)))
    equal(Path(path).stat().st_mode & 0o7777, item["mode"])
    equal(str(Path(path).readlink()) if Path(path).is_symlink() else None, item.get("symlink"))
for item in index["prior_unchanged_archives"]:
    equal(sha(read(DEST / item["path"])), item["sha256"])
assert isinstance(taskfile_bytes, bytes)
m = json.loads(read(DEST / "measurement-index.json"))
parts = []
for item in m["parts"]:
    b = read(DEST / item["file"])
    equal(sha(b), item["sha256"])
    equal(len(b), item["bytes"])
    parts.append(b)
b = b"".join(parts)
equal(sha(b), m["compressed_sha256"])
raw = gzip.decompress(b)
equal(sha(raw), m["sha256"])
equal(len(raw), m["bytes"])
equal(raw, read(WORK / "measurement.json"))
r = json.loads(raw)
equal(r["read_subjects_before"], r["read_subjects_after"])
append = {
    str(ROOT / ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md"): WORK / "measured-task.md",
    str(ROOT / "docs/acceptance/baseline-finite.md"): WORK / "measured-acceptance.md",
}
for path, h in r["read_subjects_before"].items():
    if path == str(ROOT / "Taskfile.yml"):
        equal(sha(taskfile_bytes), h)
        check_taskfile(taskfile_bytes, read(Path(path)))
    elif path in append:
        old = read(append[path])
        equal(sha(old), h)
        assert read(Path(path)).startswith(old)
    else:
        equal(sha(read(Path(path))), h)
with zipfile.ZipFile(next((WORK / "wheel").glob("*.whl"))) as z:
    for member in z.namelist():
        if member.startswith("bookscan/") and not member.endswith("/"):
            equal(z.read(member), read(ROOT / "src" / member))
            equal(z.read(member), read(WORK / "installed/lib/python3.12/site-packages" / member))
truth = json.loads(read(WORK / "fixtures/truth.json"))


def resources(record):
    equal(record["runtime_resources_verified"], False)
    equal(
        record["controls"],
        {
            "stable-directory-rgb": True,
            "actual-candidate-added": True,
            "candidate-growth-rejected": ["DEPENDENCY_UNAVAILABLE", 5],
            "wrong-file-only-guard-returns-pixels": True,
        },
    )
    equal({Path(p).name for p in record["candidate_scope_before"]}, {"Helvetica.ttc"})
    equal({Path(p).name for p in record["candidate_scope_after"]}, {"Helvetica.ttc", "Courier.ttc"})
    equal(record["subjects_before"], record["subjects_after"])
    for row in record["commands"]:
        equal(row["returncode"], 0)
    native = record["native_file_binding"]
    equal(native["runtime_resources_verified"], False)
    equal(native["hashes"]["a"], native["hashes"]["guarded"])
    assert native["hashes"]["a"] != native["hashes"]["b"]
    equal(record["rgb_sha256"], native["hashes"]["a"])
    equal(
        native["controls"],
        {
            "different-font-is-distinct": True,
            "ambient-environment-cannot-change-bound-render": True,
            "changed-resource-rejected": ["DEPENDENCY_UNAVAILABLE", 5],
            "literal-child-environment": "captured\n",
        },
    )
    for i, row in enumerate(native["raw"]):
        equal(row["returncode"], 0)
        equal(row["reaped"], True)
        assert type(row["pid"]) is int and row["pid"] > 0
        assert (
            '\tfile: "'
            + str(
                WORK
                / "fixtures"
                / ("fonts-a" if i == 0 else "fonts-b")
                / Path(truth["font_files"][i]).name
            )
            + '"(w)'
            in row["stdout"]
        )
    for item in record["binding"]["files"]:
        path = Path(item["path"])
        equal(sha(read(path)), item["sha256"])
        equal(str(path.resolve()), item["resolved"])
        equal((path.stat().st_dev, path.stat().st_ino), (item["device"], item["inode"]))
    for directory in record["binding"]["directories"]:
        if directory["entries"] is None:
            assert not Path(directory["path"]).exists()
            continue
        for item in directory["entries"]:
            path = Path(item["path"])
            equal(str(path.resolve()), item["resolved"])
            equal((path.stat().st_dev, path.stat().st_ino), (item["device"], item["inode"]))
            equal(
                (path.lstat().st_dev, path.lstat().st_ino),
                (item["entry_device"], item["entry_inode"]),
            )
            equal(str(path.readlink()) if path.is_symlink() else None, item["link_target"])
            if item["kind"] == "file":
                equal(sha(read(path)), item["sha256"])
            else:
                equal(sorted(p.name for p in path.iterdir()), item["members"])
    return {
        "rgb_sha256": record["rgb_sha256"],
        "controls": record["controls"],
        "hashes": native["hashes"],
        "fidelity": record["fidelity"],
        "renderer_sha256": native["renderer_sha256"],
    }


equal(len(r["resources"]), 4)
equal(r["itemwise_native_equal"], True)
assert all(resources(v) == resources(r["resources"][0]) for v in r["resources"])
for v in [r["resources"][1], r["resources"][3]]:
    assert Path(v["module"]).is_relative_to(WORK / "installed")
wrong = copy.deepcopy(r["resources"][0])
wrong["rgb_sha256"] = "wrong"
try:
    resources(wrong)
except AssertionError:
    pass
else:
    raise AssertionError("Wrong native result credited")
equal(len(r["units"]), 1024)
assert all(not children for _, children in r["units"])
equal(r["unit_rerun_itemwise_equal"], True)
equal(len(r["preparation"]["cases"]), 9)
equal(len(r["preparation"]["faults"]), 38)
equal(r["preparation"]["itemwise_equal"], True)
expected = [
    ("hold", None, 0, True, False, True),
    ("process-lock", None, 0, False, False, True),
    ("native", 2, 130, True, False, True),
    ("native", 15, 143, True, False, True),
    ("native", 9, -9, True, True, True),
    ("exec-open", 9, -9, True, True, True),
]
for v in r["ownership"]:
    equal(
        [
            (
                x["mode"],
                x["signal"],
                x["writer_reaped"],
                x["busy_before_death"],
                x["native_alive_at_reacquisition"],
                x["immediate_reacquisition"],
            )
            for x in v["records"]
        ],
        expected,
    )
equal(r["renders"][0]["pages"], r["renders"][1]["pages"])
equal(len(r["renders"][0]["pages"]), 14)
equal(len(r["renders"][0]["controls"]), 10)
assert all(item["exit"] == 0 for item in r["commands"])
coverage = set()
generations = set()
fallback = {}
for p in (WORK / "graph").glob("coverage-*.json"):
    data = json.loads(read(p))
    generations.add(data["metadata"]["generation"])
    for row in data["paths"]:
        coverage.add(row["path"])
        if row["status"] != "no_recorded_issue" or row["freshness"] != "metadata_match":
            source = ROOT / row["path"]
            fallback[row["path"]] = {
                "sha256": sha(read(source)),
                "status": row["status"],
                "freshness": row["freshness"],
            }
            for gap in row["coverage"]:
                for span in gap.get("ranges", []):
                    fallback[row["path"]].setdefault("ranges", []).append(
                        {
                            "start": span["start"],
                            "end": span["end"],
                            "text": source.read_text().splitlines()[
                                span["start"] - 1 : span["end"]
                            ],
                        }
                    )
# Derived coverage is emitted only in the result, never into a retained input.
# Later archive bookkeeping is direct byte fallback, not structural evidence.
for path in set(paths) - coverage:
    assert path.startswith("docs/acceptance/baseline-resource-directories/")
    fallback[path] = {"sha256": current[path], "status": "later archival bookkeeping; direct bytes"}
for p in (WORK / "graph").glob("snippet-*.json"):
    data = json.loads(read(p))["structuredContent"]
    lines = Path(data["file_path"]).read_text().splitlines()
    equal("\n".join(lines[data["start_line"] - 1 : data["end_line"]]) + "\n", data["source"])
for p in (WORK / "graph").glob("trace-*.json"):
    data = json.loads(read(p))["structuredContent"]
    assert not data.get("truncated") and not data.get("next")
protected = []
for p in subprocess.check_output(
    ["jj", "file", "list", "-r", "@-"], cwd=ROOT, text=True
).splitlines():
    if p not in {
        ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md",
        "Taskfile.yml",
        "pyproject.toml",
        "uv.lock",
    }:
        equal(
            read(ROOT / p), subprocess.check_output(["jj", "file", "show", "-r", "@-", p], cwd=ROOT)
        )
        protected.append(p)
equal(len(protected), 166)
change = subprocess.check_output(
    ["jj", "log", "--no-pager", "--no-graph", "-r", "@", "-T", "change_id"], cwd=ROOT, text=True
)
equal(change, "ryouonnvvlkzyyxmxrpqxnuqrysrqtvy")
parent = subprocess.check_output(
    ["jj", "log", "--no-pager", "--no-graph", "-r", "@-", "-T", "commit_id"], cwd=ROOT, text=True
)
assert parent.startswith("03eb30ab")
assert all(p.stat().st_size < 1048576 for p in DEST.iterdir())
equal(current, {p: sha(read(ROOT / p)) for p in paths})
result = {
    "tracked_paths": len(paths),
    "earlier_paths_preserved": len(before),
    "protected_originals": len(protected),
    "changed_existing_paths": sorted(changed),
    "new_paths": sorted(set(current) - set(before)),
    "exact_raw_files": len(index["files"]),
    "live_raw_files_exact": len(index["files"]) - 1,
    "taskfile_addition": {
        "archived_sha256": sha(taskfile_bytes),
        "current_sha256": sha(read(ROOT / "Taskfile.yml")),
        "exact_addition_sha256": sha(TASKFILE_ADDITION),
        "wrong_recipe_rejected": True,
    },
    "exact_raw_chunks": len(blobs),
    "frozen_subjects": len(r["read_subjects_before"]),
    "native_resource_readings": 4,
    "units_per_rerun": 1024,
    "coverage_paths": len(coverage),
    "coverage_generations": sorted(generations),
    "coverage_fallback": fallback,
    "f_change_id": change,
    "parent": parent,
    "tracked_digests": current,
    "exact_measurement_reconstruction": True,
    "wrong_native_hash_rejected": True,
}
(Path("/private/tmp/bookscan-k63-audit-repair") / "preserving-audit.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(
    "Audited",
    len(paths),
    "paths;",
    len(before),
    "preserved;",
    len(index["files"]),
    "exact raw files;",
    len(r["read_subjects_before"]),
    "frozen subjects; same live F",
)
