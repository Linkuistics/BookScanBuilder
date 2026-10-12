"""Reconstruct native captured font-path and font-copy evidence on the original Mac."""

from __future__ import annotations

import hashlib
import io
import json
import runpy
import stat
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import cast

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BOOKKEEPING = {
    str(ROOT / ".grove/40-k47/01-k53/11-impl--baseline-finite-k63.md"),
    str(ROOT / "docs/acceptance/baseline-finite.md"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> bytes:
    """Mode000 fault artifacts need temporary owner-read, immediately restored."""
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


def equal(left: object, right: object) -> None:
    if left != right:
        raise ValueError("Per-item retained evidence disagreement")


class Evidence:
    """Address logical records through deduplicated, digest-bound archive blobs."""

    def __init__(self, archive: zipfile.ZipFile, entries: dict[str, dict[str, object]]) -> None:
        self.archive = archive
        self.entries = entries

    def read(self, name: str) -> bytes:
        return self.archive.read("blobs/" + str(self.entries[name]["sha256"]))

    def namelist(self) -> list[str]:
        return list(self.entries)


def main() -> int:
    checker = Path(__file__).read_bytes()
    index_bytes = (HERE / "index.json").read_bytes()
    index = json.loads(index_bytes)
    parts: list[bytes] = []
    for item in index["parts"]:
        data = (HERE / item["name"]).read_bytes()
        equal((len(data), sha(data)), (item["size"], item["sha256"]))
        parts.append(data)
    raw = b"".join(parts)
    equal((len(raw), sha(raw)), (index["archive_size"], index["archive_sha256"]))
    with zipfile.ZipFile(io.BytesIO(raw)) as raw_archive:
        blob_names = raw_archive.namelist()
        equal(len(blob_names), len(set(blob_names)))
        equal(set(blob_names), {"blobs/" + item["sha256"] for item in index["entries"].values()})
        archive = Evidence(raw_archive, index["entries"])
        names = archive.namelist()
        equal(len(names), len(set(names)))
        equal(set(names), set(index["entries"]))
        for name, item in index["entries"].items():
            data = archive.read(name)
            equal((len(data), sha(data)), (item["size"], item["sha256"]))
            path = Path(item["path"])
            equal(stat.S_IMODE(path.stat().st_mode), item["mode"])
            equal(read(path), data)
        before = json.loads(archive.read("frozen/subjects-before.json"))
        equal(before, json.loads(archive.read("frozen/subjects-after.json")))
        host_before = {name: current(Path(name)) for name in before}
        for name, expected in before.items():
            actual = dict(host_before[name])
            if name in BOOKKEEPING:
                equal(sha(read(Path(name))[: expected["size"]]), expected["sha256"])
                actual.update(size=expected["size"], sha256=expected["sha256"])
            equal(actual, expected)
        measured = json.loads(archive.read("frozen/measurement.json"))
        regression = json.loads(archive.read("instruments/regression-verification.json"))
        equal(regression["subjects_before"], regression["subjects_after"])
        equal(measured["preserved_units"], 1141)
        equal(len(measured["units"]), 1153)
        equal(len(regression["new_units"]), 12)
        if any(measured["units"].values()):
            raise ValueError("Unsuccessful unit record")
        prior = json.loads(archive.read("prior/measurement.json"))
        for name, outcome in prior["units"].items():
            equal(measured["units"][name], outcome)
        wheels = [name for name in names if name.startswith("wheel/") and name.endswith(".whl")]
        equal(len(wheels), 1)
        with zipfile.ZipFile(io.BytesIO(archive.read(wheels[0]))) as wheel:
            product = {
                name.removeprefix("product/"): archive.read(name)
                for name in names
                if name.startswith("product/")
            }
            equal(set(product), set(measured["wheel_product_members"]))
            equal(set(product), {name for name in wheel.namelist() if name.startswith("bookscan/")})
            for name, data in product.items():
                equal(data, wheel.read(name))
                equal(data, read(ROOT / "src" / name))
        # The current helper's bytes already match the archived frozen instrument.
        bind = cast(
            Callable[[list[dict[str, object]], int, Path], dict[str, object]],
            runpy.run_path(str(ROOT / "tests/font_loading.py"))["bind_loading"],
        )
        reference = measured["native"]["source-a"]
        for run in ("source-a", "source-b", "wheel-a", "wheel-b"):
            equal(measured["native"][run], reference)
            records = json.loads(archive.read(f"frozen/{run}/result.json"))
            for case in ("a", "b"):
                record = records[case]
                equal(record["cold_outcome"], ["DEPENDENCY_UNAVAILABLE", 5])
                equal(record["warm_outcome"], {"returncode": 0, "stderr": ""})
                equal(record["frozen_before"], record["frozen_after"])
                for key in (
                    "managed_cache_initially_empty",
                    "managed_cache_populated_before_binding",
                    "private_resources_unchanged",
                ):
                    equal(record[key], True)
                equal(record["runtime_resources_verified"], False)
                observed = record["observations"]["observed"]
                equal(observed["child"]["returncode"], 0)
                equal(observed["child"]["reaped"], True)
                equal(record["observations"]["disabled"]["rejected"], True)
                equal(
                    set(observed["controls"]),
                    {
                        "foreign-pid",
                        "wrong-font",
                        "wrong-inode",
                        "wrong-index",
                    },
                )
                equal(set(observed["controls"].values()), {True})
                prefix = f"frozen/{run}/{case}/observed/events/"
                events = [
                    json.loads(archive.read(name))
                    for name in sorted(names)
                    if name.startswith(prefix)
                ]
                font = Path(observed["bound"]["font"])
                equal(bind(events, observed["child"]["pid"], font), observed["bound"])
                for panel in ("observed", "disabled"):
                    png = archive.read(f"frozen/{run}/{case}/{panel}/page.png")
                    with Image.open(io.BytesIO(png)) as image:
                        equal(image.mode, "RGB")
                        equal(list(image.size), record["size"])
                        equal(sha(image.tobytes()), record["rgb_sha256"])
                bad = json.loads(json.dumps(events))
                bad[0]["pid"] += 1
                invalid_records: tuple[list[dict[str, object]], ...] = ([], bad)
                for invalid in invalid_records:
                    try:
                        bind(invalid, observed["child"]["pid"], font)
                    except ValueError:
                        pass
                    else:
                        raise ValueError("Disabled/foreign native control accepted")
        cache_reference = measured["cache"]["source-a"]
        for run in ("source-a", "source-b", "wheel-a", "wheel-b"):
            equal(measured["cache"][run], cache_reference)
            records = json.loads(archive.read(f"frozen/cache-{run}/result.json"))
            for case in ("a", "b"):
                record = records[case]
                equal(record["size"], [600, 150])
                for field in ("mutation_outcome", "foreign_cache_outcome"):
                    equal(record[field], ["DEPENDENCY_UNAVAILABLE", 5])
                equal(record["cache_removed_after_context"], True)
                equal(record["immutable_render_repeat"], True)
                equal(record["runtime_resources_verified"], False)
                equal(record["direct_child"]["exit_code"], 5)
                equal(record["direct_child"]["stdout"], "")
                if not record["direct_child"]["stderr"]:
                    raise ValueError("Missing refused-child diagnostic")
                construction = record["binding"]["cache_construction"]
                equal(construction["method"], "FcConfigBuildFonts")
                equal(construction["initially_empty"], True)
                root = Path(construction["cache_root"])
                if root.exists() or root.is_symlink():
                    raise ValueError("Cache owner left its reservation")
                equal(record["rgb_sha256"], measured["native"][run][case]["rgb_sha256"])
                equal(record["font_sha256"], measured["native"][run][case]["font_sha256"])
                with Image.open(
                    io.BytesIO(archive.read(f"frozen/cache-{run}/{case}/baseline.png"))
                ) as image:
                    equal(image.mode, "RGB")
                    equal(list(image.size), record["size"])
                    equal(sha(image.tobytes()), record["rgb_sha256"])
                trees = record["binding"]["binding"]["directories"]
                cache = [item for item in trees if Path(item["path"]).resolve() == root]
                equal(len(cache), 1)
                cached = {
                    str(Path(item["path"]).relative_to(root)): item["sha256"]
                    for item in cache[0]["entries"]
                    if item["kind"] == "file"
                }
                prefix = f"frozen/cache-{run}/{case}/completed-cache-copy/"
                copied = {
                    name.removeprefix(prefix): sha(archive.read(name))
                    for name in names
                    if name.startswith(prefix)
                }
                equal(copied, cached)
                if not cached:
                    raise ValueError("No native completed cache retained")
        for kind in (
            "snapshot",
            "default",
            "environment",
            "xdg",
            "relative",
            "relative-alias",
            "cwd",
            "home",
        ):
            readings = (
                measured["snapshot"]
                if kind == "snapshot"
                else measured["selection"][kind]
                if kind in {"default", "environment"}
                else measured["path_forms"][kind]
            )
            snapshot_reference = readings["source-a"]
            for run in ("source-a", "source-b", "wheel-a", "wheel-b"):
                equal(readings[run], snapshot_reference)
                records = json.loads(archive.read(f"frozen/{kind}-{run}/result.json"))
                for case in ("a", "b"):
                    record = records[case]
                    truth = json.loads(archive.read(f"frozen/{kind}-{run}/{case}/truth.json"))
                    equal(record["size"], [600, 150])
                    for key in (
                        "before_after_rgb_exact",
                        "host_loss_rgb_exact",
                        "snapshot_removed",
                    ):
                        equal(record[key], True)
                    equal(record["mutation_outcome"], ["DEPENDENCY_UNAVAILABLE", 5])
                    equal(record["runtime_resources_verified"], False)
                    provenance = record["binding"]["resource_snapshot"]
                    equal(provenance["method"], "copied-path-cache-redirect")
                    equal(
                        provenance["selection"],
                        "captured-fontconfig" if kind in {"default", "environment"} else "explicit",
                    )
                    if not str(provenance["configuration_file"]).endswith("/config/fonts.conf"):
                        raise ValueError("Wrong selected entry point")
                    root = Path(provenance["root"])
                    if kind in {"xdg", "relative", "relative-alias", "cwd", "home"}:
                        equal(record["path_form"], kind)
                        expected_roots = {
                            str(root / name.lstrip("/")) for name in record["font_roots"]
                        }
                        equal(
                            set(record["binding"]["scope"]["effective_font_dirs"]), expected_roots
                        )
                        equal(len(expected_roots), 3 if kind == "xdg" else 1)
                        equal(record["rgb_sha256"], measured["snapshot"][run][case]["rgb_sha256"])
                    if root.exists() or root.is_symlink():
                        raise ValueError("Font snapshot owner left its reservation")
                    row = readings[run][case]
                    for key in row:
                        equal(row[key], record[key])
                    for panel in (
                        "baseline",
                        "original-resource",
                        "before-host-loss",
                        "after-host-loss",
                    ):
                        with Image.open(
                            io.BytesIO(archive.read(f"frozen/{kind}-{run}/{case}/{panel}.png"))
                        ) as image:
                            equal(image.mode, "RGB")
                            equal(list(image.size), record["size"])
                            equal(sha(image.tobytes()), record["rgb_sha256"])
                    expected_files: dict[str, str] = {}
                    binding = record["binding"]["binding"]
                    for item in binding["files"]:
                        path = Path(item["path"])
                        if path.is_relative_to(root) and item["sha256"] is not None:
                            expected_files[str(path.relative_to(root))] = item["sha256"]
                    for tree in binding["directories"]:
                        if tree["entries"] is None:
                            continue
                        for item in tree["entries"]:
                            path = Path(item["path"])
                            if path.is_relative_to(root) and item["kind"] == "file":
                                expected_files[str(path.relative_to(root))] = item["sha256"]
                    prefix = f"frozen/{kind}-{run}/{case}/private-copy/"
                    copied = {
                        name.removeprefix(prefix): sha(archive.read(name))
                        for name in names
                        if name.startswith(prefix)
                    }
                    equal(expected_files, copied)
                    if not copied or truth["font_sha256"] not in copied.values():
                        raise ValueError("No exact private font copy retained")
                    if truth["copied_font_rule_sha256"] not in copied.values():
                        raise ValueError("No exact remapped rule construction retained")
        equal(measured["native"]["source-a"], prior["native"]["source-a"])
        equal(measured["cache"]["source-a"], prior["cache"]["source-a"])
        for wrong in ({}, {"wrong-case": True}):
            try:
                equal(cache_reference, wrong)
            except ValueError:
                pass
            else:
                raise ValueError("Wrong cache per-item reading accepted")
        for wrong in ({}, {"wrong-case": True}):
            try:
                equal(reference, wrong)
            except ValueError:
                pass
            else:
                raise ValueError("Wrong per-item reading accepted")
    equal(host_before, {name: current(Path(name)) for name in host_before})
    equal(checker, Path(__file__).read_bytes())
    equal(index_bytes, (HERE / "index.json").read_bytes())
    print(
        json.dumps(
            {
                "entries": len(index["entries"]),
                "parts": len(parts),
                "subjects": len(host_before),
                "units": len(measured["units"]),
                "preserved_units": measured["preserved_units"],
                "native_readings": 4,
                "controlled_fonts": 2,
                "cache_readings": 4,
                "snapshot_readings": 12,
                "path_readings": 20,
                "selection_modes": ["explicit", "default", "environment"],
                "preparation_cases": len(regression["preparation"]["cases"]),
                "writer_outcomes": len(regression["preparation"]["faults"]),
                "source_wheel_equal": True,
                "runtime_resources_verified": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
