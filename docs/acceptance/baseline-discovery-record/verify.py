"""Reconstruct paired saved Fontconfig discovery/copy readings from ordinary retained evidence.

Host dependencies remain digest references. This checks recorded constructions,
not native file-use truth, an accepted project or complete finite delivery.
"""

import gzip
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, cast


def equal(left: object, right: object, context: str) -> None:
    if left != right:
        raise ValueError(context)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def units(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for row in ET.fromstring(raw).iter("testcase"):
        key = row.attrib["classname"] + "." + row.attrib["name"]
        if key in result:
            raise ValueError("Duplicate construction identity")
        result[key] = [child.tag for child in row if child.tag in {"failure", "error", "skipped"}]
    return result


def normalize(value: Any, directory: str) -> Any:
    if isinstance(value, str):
        return re.sub(
            r"\.bookscan-prepare-[0-9a-f]{32}\.tmp",
            ".bookscan-prepare-OWNED.tmp",
            value.replace(directory, "ARTIFACTS"),
        )
    if isinstance(value, list):
        return [normalize(item, directory) for item in cast(list[Any], value)]
    if isinstance(value, dict):
        return {
            key: normalize(item, directory) for key, item in cast(dict[str, Any], value).items()
        }
    return value


def discovery(value: Any) -> dict[str, Any]:
    """Independently recover the raw fields represented by the detached reading."""

    def named(binding: Any) -> dict[str, Any]:
        if binding["runtime_resources_verified"] is not False:
            raise ValueError("No native-use truth")
        return {
            key: binding[key]
            for key in (
                "environment_sha256",
                "working_directory",
                "working_directory_identity",
                "files",
                "directories",
            )
        }

    if value["runtime_resources_verified"] is not False:
        raise ValueError("No native-use truth")
    native = value["linked"]
    if native["runtime_resources_verified"] is not False:
        raise ValueError("No native-use truth")
    graph = {
        key: native[key]
        for key in (
            "root",
            "executable_context",
            "architecture",
            "os_build",
            "system_references",
        )
    }
    files: list[dict[str, Any]] = []
    for path, item in sorted(native["files"].items()):
        refs: list[dict[str, Any]] = []
        for reference in item["references"]:
            if "identity" in reference:
                equal(
                    reference["identity"],
                    "OS shared-cache reference; disk bytes not claimed",
                    "No invented system bytes",
                )
            refs.append(
                {
                    "kind": reference["kind"],
                    "reference": reference["reference"],
                    "resolved": reference.get("resolved"),
                }
            )
        files.append(
            {
                "path": path,
                "sha256": item["sha256"],
                "load_commands": item["load_commands"],
                "references": refs,
            }
        )
    graph["files"] = files
    construction = value.get("cache_construction")
    cache = None
    if construction is not None:
        equal(construction["method"], "FcConfigBuildFonts", "Recorded construction method")
        if construction["initially_empty"] is not True:
            raise ValueError("Recorded initial-empty fact")
        cache = {
            "cache_root": construction["cache_root"],
            "command": construction["command"],
            "inputs": named(construction["inputs"]),
        }
    saved = value.get("resource_snapshot")
    snapshot = None
    if saved is not None:
        if saved["runtime_resources_verified"] is not False:
            raise ValueError("No native-use truth")
        equal(saved["method"], "copied-path-cache-redirect", "Recorded copy method")
        if saved["selection"] not in {"explicit", "captured-fontconfig"}:
            raise ValueError("Unsupported recorded selection")
        snapshot = {
            **{key: saved[key] for key in ("root", "configuration_file", "selection")},
            "original": discovery(saved["original"]),
        }
    return {
        "scope": value["scope"],
        "binding": named(value["binding"]),
        "linked": graph,
        "cache": cache,
        "snapshot": snapshot,
    }


def verify(read: dict[str, bytes]) -> dict[str, object]:
    def data(name: str) -> Any:
        return json.loads(read[name])

    measured, prior = data("frozen/measurement.json"), data("prior-measurement.json")
    equal(measured["public_finite_delivery"], False, "No finite delivery")
    equal(
        read["frozen/subjects-before.json.gz"],
        read["frozen/subjects-after.json.gz"],
        "Frozen subjects",
    )
    subjects = json.loads(gzip.decompress(read["frozen/subjects-before.json.gz"]))
    equal(len(subjects), measured["subjects"], "Subject roster")
    equal(
        data("frozen/frozen-status.json"),
        {"completed": True, "unchanged": True, "subjects": len(subjects)},
        "Completed freeze",
    )
    a = units(read["frozen/gate-a.xml"])
    equal(a, units(read["frozen/gate-b.xml"]), "Full itemwise rerun")
    equal(a, measured["units"], "Full ledger")
    equal(len(a), 2092, "Full construction roster")
    if any(a.values()):
        raise ValueError("Failed full construction")
    equal(prior["units"], {key: a[key] for key in prior["units"]}, "Predecessor units")
    new = sorted(set(a) - set(prior["units"]))
    equal(new, measured["new_units"], "New unit ledger")
    equal(len(new), 60, "Reader construction roster")
    if not all(key.startswith("tests.test_fontconfig_discovery_record.") for key in new):
        raise ValueError("Unexpected construction scope")
    selected = {
        key: value
        for key, value in a.items()
        if any(
            name in key
            for name in (
                "test_fontconfig_discovery_record.",
                "test_fontconfig_record.",
                "test_fontconfig_cache_record.",
                "test_linked_record.",
            )
        )
    }
    for suffix in ("a", "b"):
        equal(units(read[f"frozen/wheel-units-{suffix}.xml"]), selected, "Installed wheel units")
    staff = units(read["frozen/staff-a.xml"])
    equal(staff, units(read["frozen/staff-b.xml"]), "Staff itemwise rerun")
    equal(len(staff), 4, "Staff roster")
    if any(staff.values()):
        raise ValueError("Failed staff construction")
    if (
        b"52 failed" not in read["red.txt"]
        or b"cannot import name 'fontconfig_discovery_record'" not in read["red.txt"]
    ):
        raise ValueError("Missing absent-reader disproof")
    if b"5 failed, 1 passed, 52 deselected" not in read["font-red.txt"]:
        raise ValueError("Missing font disproof")
    if b"2 failed, 58 deselected" not in read["alias-red.txt"]:
        raise ValueError("Missing alias disproof")
    for label, expected in measured["native"].items():
        raw = data(f"frozen/{label}/report.json")
        facts = {
            key: raw[key]
            for key in (
                "truth",
                "truth_sha256",
                "records",
                "controls",
                "source_loss_itemwise_equal",
                "accepted_project_delivered",
                "composition_fidelity_verified",
                "render_policy_controls",
            )
        }
        equal(facts, expected, "Native assessment ledger")
        equal(facts, next(iter(prior["native"].values())), "Native assessment predecessor")
        equal(len(facts["records"]), 7, "Native assessed occurrence roster")
    for label, reading in measured["resource_readings"].items():
        raw = data(f"frozen/{label}/result.json")
        equal(reading, data(f"frozen/{label}-reader.json"), "Native cache reading ledger")
        equal([row["id"] for row in reading["facts"]], ["a", "b"], "Cache roster")
        for row in reading["facts"]:
            equal(row["facts"], discovery(raw[row["id"]]["binding"]), "Native cache facts")
            equal(
                row["controls"],
                {
                    key: "INVALID_PROJECT"
                    for key in (
                        "scope",
                        "runtime",
                        "linked-digest",
                        "cache-command",
                    )
                },
                "Native cache controls",
            )
        outcomes = {
            key: {
                field: item[field]
                for field in (
                    "size",
                    "rgb_sha256",
                    "font_sha256",
                    "cache_removed_after_context",
                    "immutable_render_repeat",
                    "mutation_outcome",
                    "foreign_cache_outcome",
                    "runtime_resources_verified",
                )
            }
            for key, item in raw.items()
        }
        equal(outcomes, measured["cache_outcomes"][label], "Cache outcomes ledger")
        equal(outcomes, next(iter(prior["cache_outcomes"].values())), "Cache predecessor outcomes")
    by_mode: dict[str, Any] = {}
    for label, reading in measured["snapshot_readings"].items():
        raw = data(f"frozen/{label}/result.json")
        equal(reading, data(f"frozen/{label}-reader.json"), "Copied-resource reading ledger")
        equal([row["id"] for row in reading["facts"]], ["a", "b"], "Snapshot roster")
        for row in reading["facts"]:
            equal(row["facts"], discovery(raw[row["id"]]["binding"]), "Native copy facts")
            equal(
                row["controls"],
                {
                    key: "INVALID_PROJECT"
                    for key in (
                        "scope",
                        "runtime",
                        "linked-digest",
                        "cache-command",
                        "selection",
                        "copy-root",
                        "font-digest",
                    )
                },
                "Native copy controls",
            )
        outcomes = {
            key: {
                field: item[field]
                for field in (
                    "size",
                    "rgb_sha256",
                    "font_sha256",
                    "snapshot_removed",
                    "mutation_outcome",
                )
            }
            for key, item in raw.items()
        }
        equal(outcomes, measured["snapshot_outcomes"][label], "Snapshot outcomes ledger")
        for item in raw.values():
            if any(
                item[key] is not True
                for key in ("before_after_rgb_exact", "host_loss_rgb_exact", "snapshot_removed")
            ):
                raise ValueError("Missing snapshot source-loss/lifetime fact")
        mode = label.split("-")[1]
        if mode in by_mode:
            equal(outcomes, by_mode[mode], "Source/wheel snapshot itemwise rerun")
        by_mode[mode] = outcomes
    for label, reading in measured["historical_readings"].items():
        kind = label.split("-")[0]
        raw = data("ordinary-binding.json" if kind == "ordinary" else "historical-selection.json")
        originals = (
            {"default": raw}
            if kind == "ordinary"
            else {key: row["binding"] for key, row in raw.items()}
        )
        equal(reading, data(f"frozen/{label}.json"), "Historical reading ledger")
        for row in reading["facts"]:
            equal(row["facts"], discovery(originals[row["id"]]), "Historical native facts")
            equal(
                row["controls"],
                {
                    key: "INVALID_PROJECT"
                    for key in (
                        "scope",
                        "runtime",
                        "linked-digest",
                        "cache-command",
                        "selection",
                        "copy-root",
                        "font-digest",
                    )
                },
                "Historical native controls",
            )
    for reading in [
        *measured["resource_readings"].values(),
        *measured["snapshot_readings"].values(),
        *measured["historical_readings"].values(),
    ]:
        equal(
            [
                reading[key]
                for key in ("runtime_use_verified", "glyph_fidelity_verified", "accepted_project")
            ],
            [False, False, False],
            "No invented fidelity or project",
        )
    for suffix in ("a", "b"):
        raw = data(f"frozen/preparation-{suffix}/report.json")
        directory = raw["artifacts"]
        faults: list[object] = []
        for row in raw["fault_checks"]["observed_signal_and_kill_cases"]:
            equal(row["pid"], row["observed_barrier"]["pid"], "Actual writer PID")
            equal(
                [row[key] for key in ("writer_reaped", "source_unchanged")],
                [True, True],
                "Writer safety",
            )
            entry = {key: value for key, value in row.items() if key != "pid"}
            entry["observed_barrier"] = {
                key: value for key, value in row["observed_barrier"].items() if key != "pid"
            }
            faults.append(normalize(entry, directory))
        reading = {"cases": normalize(raw["cases"], directory), "faults": faults}
        equal(reading, measured["preparation"], "Preparation ledger")
        equal(reading, prior["preparation"], "Preparation predecessor")
        equal(len(faults), 38, "Actual writer fault roster")
    package = {
        name.removeprefix("measured/src/"): sha(raw)
        for name, raw in read.items()
        if name.startswith("measured/src/bookscan/")
    }
    with zipfile.ZipFile(
        io.BytesIO(read["wheel/bookscan_builder-0.1.0-py3-none-any.whl"])
    ) as wheel:
        equal(
            set(package),
            {name for name in wheel.namelist() if name.startswith("bookscan/")},
            "Wheel roster",
        )
        for name, digest in package.items():
            equal(sha(wheel.read(name)), digest, "Source/wheel bytes")
            installed = [
                info["sha256"]
                for path, info in subjects.items()
                if path.endswith("installed/lib/python3.12/site-packages/" + name)
            ]
            equal(installed, [digest], "Installed product bytes")
    for name, raw in read.items():
        if name.startswith("measured/"):
            subject = "/Users/antony/Development/BookScanBuilder/" + name.removeprefix("measured/")
            equal(sha(raw), subjects[subject]["sha256"], "Retained measured bytes")
    mutations = data("mutations/result.json")
    intended = {
        "scope": ["True", "scope"],
        "library": ["cache-foreign-library"],
        "font": ["digest", "size"],
        "alias": ["test_mapped_configuration_file_cannot_keep_a_route_back_to_the_host"],
    }
    for label, cases in intended.items():
        raw = read[f"mutations/{label}/result.xml"]
        equal(len(units(raw)), 60, "Mutation construction roster")
        if any(values not in ([], ["failure"]) for values in units(raw).values()):
            raise ValueError("Mutation error or skipped case")
        failures = sorted(
            row.attrib["name"].removesuffix("]").split("[")[-1]
            for row in ET.fromstring(raw).iter("testcase")
            if row.find("failure") is not None
        )
        equal(failures, cases, "Isolated omission disproof")
        equal(mutations[label]["failed_cases"], cases, "Mutation ledger")
        equal(
            sha(read[f"mutations/{label}/bookscan/fontconfig_discovery_record.py"]),
            mutations[label]["mutated_sha256"],
            "Mutation subject",
        )
    return {
        "verified": True,
        "units": len(a),
        "new_units": len(new),
        "frozen_subjects": len(subjects),
        "public_finite_delivery": False,
    }


def reconstruct(directory: Path) -> dict[str, bytes]:
    index = json.loads(gzip.decompress((directory / "index.json.gz").read_bytes()))
    chunks: list[bytes] = []
    for part in index["parts"]:
        raw = (directory / part["name"]).read_bytes()
        equal(sha(raw), part["sha256"], "Archive part digest")
        chunks.append(raw)
    with zipfile.ZipFile(io.BytesIO(b"".join(chunks))) as archive:
        read = {name: archive.read(name) for name in archive.namelist()}
        equal(len(read), len(archive.namelist()), "Unique archive entries")
    if index.get("storage") == "sha256-blobs-v1":
        equal(
            set(read),
            {"blobs/" + digest for digest in index["entries"].values()},
            "Complete shared blob inventory",
        )
        for name, raw in read.items():
            equal(name, "blobs/" + sha(raw), "Shared blob content address")
        read = {name: read["blobs/" + digest] for name, digest in index["entries"].items()}
    elif index.get("storage") is not None:
        raise ValueError("Unsupported evidence storage")
    equal(
        {name: sha(raw) for name, raw in read.items()},
        index["entries"],
        "Complete archive inventory",
    )
    return read


if __name__ == "__main__":
    print(json.dumps(verify(reconstruct(Path(__file__).parent)), sort_keys=True))
