"""Reconstruct saved-cache-construction-reader measurements; host dependencies remain references."""

import gzip
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, cast


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def equal(left: object, right: object, context: str) -> None:
    if left != right:
        raise ValueError(context)


def units(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for row in ET.fromstring(raw).iter("testcase"):
        key = row.attrib["classname"] + "." + row.attrib["name"]
        if key in result:
            raise ValueError("Duplicate unit identity")
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


def verify(read: dict[str, bytes]) -> dict[str, object]:
    def data(name: str) -> Any:
        return json.loads(read[name])

    measured, prior = data("frozen/measurement.json"), data("prior-measurement.json")
    equal(measured["public_finite_delivery"], False, "no finite delivery")
    equal(read["frozen/subjects-before.json.gz"], read["frozen/subjects-after.json.gz"], "freeze")
    subjects = json.loads(gzip.decompress(read["frozen/subjects-before.json.gz"]))
    equal(len(subjects), measured["subjects"], "subject roster")
    equal(
        data("frozen/frozen-status.json"),
        {"completed": True, "unchanged": True, "subjects": len(subjects)},
        "completed freeze",
    )
    a = units(read["frozen/gate-a.xml"])
    equal(a, units(read["frozen/gate-b.xml"]), "full rerun")
    equal(a, measured["units"], "unit ledger")
    equal(len(a), 1969, "unit roster")
    if any(a.values()):
        raise ValueError("Failed construction")
    equal(prior["units"], {key: a[key] for key in prior["units"]}, "predecessor units")
    new = sorted(set(a) - set(prior["units"]))
    equal(new, measured["new_units"], "new unit ledger")
    equal(len(new), 53, "new units")
    if not all(key.startswith("tests.test_fontconfig_cache_record.") for key in new):
        raise ValueError("Unexpected new scope")
    selected = {
        key: value
        for key, value in a.items()
        if any(
            name in key
            for name in (
                "test_fontconfig_cache_record.",
                "test_fontconfig_record.",
                "test_fontconfig_cache.",
            )
        )
    }
    for suffix in ("a", "b"):
        equal(units(read[f"frozen/wheel-units-{suffix}.xml"]), selected, "wheel units")
    staff = units(read["frozen/staff-a.xml"])
    equal(staff, units(read["frozen/staff-b.xml"]), "staff rerun")
    equal(len(staff), 4, "staff roster")
    if any(staff.values()):
        raise ValueError("Failed staff construction")
    if (
        b"49 failed" not in read["red.txt"]
        or b"cannot import name 'fontconfig_cache_record'" not in read["red.txt"]
    ):
        raise ValueError("Missing initial failing construction")
    if b"1 failed, 52 passed" not in read["alias-red.txt"]:
        raise ValueError("Missing alias-only disproof")
    prior_native = next(iter(prior["native"].values()))
    expected_cache = None
    historical = data("historical-cache.json")
    keys = (
        "size",
        "rgb_sha256",
        "font_sha256",
        "cache_removed_after_context",
        "immutable_render_repeat",
        "mutation_outcome",
        "foreign_cache_outcome",
        "runtime_resources_verified",
    )
    historical_outcomes = {
        key: {name: row[name] for name in keys} for key, row in historical.items()
    }
    for lane in ("source", "wheel"):
        for suffix in ("a", "b"):
            label = f"assessment-{lane}-{suffix}"
            native = data(f"frozen/{label}/report.json")
            reading = {key: native[key] for key in prior_native}
            equal(reading, prior_native, "native assessment predecessor")
            equal(reading, measured["native"][label], "native assessment ledger")
            equal(
                sha(read[f"frozen/{label}/snapshot.pdf"]), native["source_sha256"], "native source"
            )
            label = f"cache-{lane}-{suffix}"
            raw = data(f"frozen/{label}/result.json")
            outcomes = {key: {name: row[name] for name in keys} for key, row in raw.items()}
            equal(outcomes, historical_outcomes, "native cache predecessor")
            equal(outcomes, measured["cache_outcomes"][label], "native cache ledger")
            reading = data(f"frozen/{label}-reader.json")
            equal(reading, measured["resource_readings"][label], "raw cache reader ledger")
            equal(reading["runtime_use_verified"], False, "no reader-use claim")
            equal(reading["accepted_project"], False, "no accepted project")
            equal([row["id"] for row in reading["facts"]], ["a", "b"], "native construction roster")
            for row in reading["facts"]:
                saved = raw[row["id"]]["binding"]
                construction, warm = saved["cache_construction"], saved["binding"]
                equal(
                    set(construction),
                    {"method", "initially_empty", "cache_root", "command", "inputs"},
                    "cache fields",
                )
                equal(construction["method"], "FcConfigBuildFonts", "cache method")
                if construction["initially_empty"] is not True:
                    raise ValueError("cache initial-empty claim")
                root = construction["cache_root"]
                equal(row["cache_root"], root, "reader cache root")
                equal(row["command"], construction["command"], "reader command")
                equal(row["scope"], saved["scope"], "reader scope")
                equal(saved["scope"], warm["fontconfig_scope_guard"]["scope"], "warm scope")
                equal(
                    construction["inputs"]["fontconfig_scope_guard"],
                    warm["fontconfig_scope_guard"],
                    "input guard",
                )
                equal(warm["runtime_resources_verified"], False, "no named-use claim")
                equal(
                    row["inputs_environment_sha256"],
                    construction["inputs"]["environment_sha256"],
                    "opaque environment fact",
                )
                equal(len(construction["command"]), 6, "command length")
                equal(construction["command"][1], "-I", "isolated command")
                equal(
                    construction["command"][4:],
                    ["--build-cache", root],
                    "cache confinement command",
                )
                fixed = dict(warm)
                fixed["directories"] = [
                    tree for tree in warm["directories"] if tree["path"] != root
                ]
                equal(construction["inputs"], fixed, "fixed construction subjects")
                cache_tree = next(tree for tree in warm["directories"] if tree["path"] == root)
                if not cache_tree["entries"]:
                    raise ValueError("Missing completed native cache inventory")
                equal(row["input_files"], len(fixed["files"]), "input file count")
                equal(row["input_trees"], len(fixed["directories"]), "input tree count")
                equal(
                    row["controls"],
                    {
                        name: ["INVALID_PROJECT", 3]
                        for name in (
                            "method",
                            "empty",
                            "fixed-subject",
                            "guard",
                            "absent-cache",
                            "mutable-input",
                            "command",
                        )
                    },
                    "cache refusal controls",
                )
            normalized = normalize(
                reading,
                str(Path(raw["a"]["binding"]["cache_construction"]["cache_root"]).parent.parent),
            )
            for row in normalized["facts"]:
                del row["inputs_environment_sha256"]
                row["command"][0] = "INTERPRETER"
                row["command"][2] = "BOUND-fontconfig_probe.py"
            if expected_cache is None:
                expected_cache = normalized
            equal(normalized, expected_cache, "native cache reader itemwise rerun")
    preparations: list[dict[str, Any]] = []
    for suffix in ("a", "b"):
        raw = data(f"frozen/preparation-{suffix}/report.json")
        directory = raw["artifacts"]
        faults: list[Any] = []
        for row in raw["fault_checks"]["observed_signal_and_kill_cases"]:
            equal(row["pid"], row["observed_barrier"]["pid"], "actual writer PID")
            equal(row["writer_reaped"], True, "writer reaped")
            equal(row["source_unchanged"], True, "source preserved")
            fact = {key: value for key, value in row.items() if key != "pid"}
            fact["observed_barrier"] = {
                key: value for key, value in row["observed_barrier"].items() if key != "pid"
            }
            faults.append(normalize(fact, directory))
        preparations.append({"cases": normalize(raw["cases"], directory), "faults": faults})
    equal(preparations[0], preparations[1], "preparation rerun")
    equal(preparations[0], prior["preparation"], "preparation predecessor")
    equal(preparations[0], measured["preparation"], "preparation ledger")
    mutations = data("mutations/result.json")
    expected_failures = {
        "initial-empty": [
            "test_contradictory_construction_is_refused[empty-false]",
            "test_contradictory_construction_is_refused[empty-int]",
            "test_restart_checks_cache_meaning_in_hash_valid_predecessors[True]",
        ],
        "guard-equality": [
            "test_contradictory_construction_is_refused[changed-guard]",
            "test_contradictory_construction_is_refused[missing-guard]",
        ],
        "fixed-subjects": [
            "test_contradictory_construction_is_refused[changed-cwd-identity]",
            "test_contradictory_construction_is_refused[changed-cwd]",
            "test_contradictory_construction_is_refused[changed-environment]",
            "test_contradictory_construction_is_refused[changed-file]",
            "test_contradictory_construction_is_refused[extra-file]",
            "test_contradictory_construction_is_refused[missing-file]",
            "test_contradictory_construction_is_refused[missing-tree]",
            "test_contradictory_construction_is_refused[mutable-cache-input]",
        ],
    }
    equal(set(mutations), set(expected_failures), "mutation roster")
    for name, wanted in expected_failures.items():
        rows = units(read[f"mutations/{name}/result.xml"])
        failed = sorted(
            key.split("test_fontconfig_cache_record.", 1)[1] for key, tags in rows.items() if tags
        )
        equal(failed, wanted, "isolated mutation failures")
        equal(failed, mutations[name]["failed"], "mutation ledger")
        equal(len(rows), 53, "mutation unit roster")
        freeze = data(f"mutations/{name}/subjects.json")
        equal(freeze["before"], freeze["after"], "mutation freeze")
    with zipfile.ZipFile(
        io.BytesIO(read["wheel/bookscan_builder-0.1.0-py3-none-any.whl"])
    ) as archive:
        equal(
            sorted(name for name in archive.namelist() if name.startswith("bookscan/")),
            measured["wheel_product_members"],
            "wheel roster",
        )
        for name in measured["wheel_product_members"]:
            equal(archive.read(name), read["measured/src/" + name], "wheel/source member")
    return {
        "passed": True,
        "units": len(a),
        "new_units": len(new),
        "subjects": len(subjects),
        "native_cache_records_per_reading": 2,
        "native_controls_per_reading": 14,
        "public_finite_delivery": False,
        "runtime_use_verified": False,
    }


def load(directory: Path) -> dict[str, bytes]:
    index = json.loads(gzip.decompress((directory / "index.json.gz").read_bytes()))
    chunks: list[bytes] = []
    for part in index["parts"]:
        raw = (directory / part["name"]).read_bytes()
        equal(sha(raw), part["sha256"], "archive part digest")
        chunks.append(raw)
    with zipfile.ZipFile(io.BytesIO(b"".join(chunks))) as archive:
        equal(len(archive.namelist()), len(set(archive.namelist())), "duplicate archive member")
        equal(set(archive.namelist()), set(index["entries"]), "archive roster")
        result = {name: archive.read(name) for name in archive.namelist()}
    for name, digest in index["entries"].items():
        equal(sha(result[name]), digest, "archive entry digest")
    return result


if __name__ == "__main__":
    print(json.dumps(verify(load(Path(__file__).parent)), sort_keys=True))
