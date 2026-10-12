"""Reconstruct paired saved-linked-graph readings from ordinary retained evidence.

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
    equal(len(a), 2032, "Full construction roster")
    if any(a.values()):
        raise ValueError("Failed full construction")
    equal(prior["units"], {key: a[key] for key in prior["units"]}, "Predecessor units")
    new = sorted(set(a) - set(prior["units"]))
    equal(new, measured["new_units"], "New unit ledger")
    equal(len(new), 63, "Reader construction roster")
    if not all(key.startswith("tests.test_linked_record.") for key in new):
        raise ValueError("Unexpected construction scope")
    selected = {
        key: value
        for key, value in a.items()
        if any(
            name in key
            for name in ("test_linked_record.", "test_dependencies.", "test_resource_record.")
        )
    }
    for suffix in ("a", "b"):
        equal(
            units(read[f"frozen/wheel-units-{suffix}.xml"]),
            selected,
            "Installed wheel construction",
        )
    staff = units(read["frozen/staff-a.xml"])
    equal(staff, units(read["frozen/staff-b.xml"]), "Staff itemwise rerun")
    equal(len(staff), 4, "Staff roster")
    if any(staff.values()):
        raise ValueError("Failed staff construction")
    if (
        b"59 failed" not in read["red.txt"]
        or b"cannot import name 'linked_record'" not in read["red.txt"]
    ):
        raise ValueError("Missing initial red construction")
    if b"3 failed, 60 deselected" not in read["header-red.txt"]:
        raise ValueError("Missing header disproof")
    expected = data("historical-reader.json")
    equal(expected["runtime_use_verified"], False, "No historical-use claim")
    equal(expected["accepted_project"], False, "No accepted-project claim")
    for lane in ("source", "wheel"):
        for suffix in ("a", "b"):
            label = f"cache-{lane}-{suffix}"
            reading, raw = data(f"frozen/{label}-reader.json"), data(f"frozen/{label}/result.json")
            equal(reading, expected, "Native reader itemwise historical/rerun")
            equal(reading, measured["resource_readings"][label], "Native reader ledger")
            equal([row["id"] for row in reading["facts"]], ["a", "b"], "Native graph roster")
            for row in reading["facts"]:
                found = raw[row["id"]]["binding"]
                linked, named = found["linked"], found["binding"]
                equal(linked["runtime_resources_verified"], False, "No native-use truth")
                expected_graph = {
                    name: linked[name]
                    for name in (
                        "root",
                        "executable_context",
                        "architecture",
                        "os_build",
                        "system_references",
                    )
                }
                files: list[dict[str, Any]] = []
                for path, info in sorted(linked["files"].items()):
                    refs: list[dict[str, Any]] = []
                    for ref in info["references"]:
                        if "identity" in ref:
                            equal(
                                ref["identity"],
                                "OS shared-cache reference; disk bytes not claimed",
                                "System-reference meaning",
                            )
                        refs.append(
                            {
                                "kind": ref["kind"],
                                "reference": ref["reference"],
                                "resolved": ref.get("resolved"),
                            }
                        )
                    bound = next(item for item in named["files"] if item["path"] == path)
                    equal(
                        (bound["resolved"], bound["sha256"]),
                        (path, info["sha256"]),
                        "Bound native digest",
                    )
                    files.append(
                        {
                            "path": path,
                            "sha256": info["sha256"],
                            "load_commands": info["load_commands"],
                            "references": refs,
                        }
                    )
                expected_graph["files"] = files
                equal(row["graph"], expected_graph, "Native graph reconstruction")
                equal(
                    row["controls"],
                    {
                        name: "INVALID_PROJECT"
                        for name in (
                            "runtime",
                            "header",
                            "digest",
                            "references",
                            "systems",
                            "bound",
                            "target",
                        )
                    },
                    "Native refusal controls",
                )
            label = f"assessment-{lane}-{suffix}"
            raw = data(f"frozen/{label}/report.json")
            predecessor = next(iter(prior["native"].values()))
            equal(
                {key: raw[key] for key in predecessor}, predecessor, "Native assessment predecessor"
            )
            equal(measured["native"][label], predecessor, "Native assessment ledger")
    outcome_keys = (
        "size",
        "rgb_sha256",
        "font_sha256",
        "cache_removed_after_context",
        "immutable_render_repeat",
        "mutation_outcome",
        "foreign_cache_outcome",
        "runtime_resources_verified",
    )
    historical = data("historical-cache.json")
    cache_expected = {
        key: {name: row[name] for name in outcome_keys} for key, row in historical.items()
    }
    for lane in ("source", "wheel"):
        for suffix in ("a", "b"):
            label = f"cache-{lane}-{suffix}"
            raw = data(f"frozen/{label}/result.json")
            equal(
                {key: {name: row[name] for name in outcome_keys} for key, row in raw.items()},
                cache_expected,
                "Native cache predecessor outcomes",
            )
            equal(measured["cache_outcomes"][label], cache_expected, "Native cache outcome ledger")
    for suffix in ("a", "b"):
        raw = data(f"frozen/preparation-{suffix}/report.json")
        faults: list[Any] = []
        for row in raw["fault_checks"]["observed_signal_and_kill_cases"]:
            equal(row["pid"], row["observed_barrier"]["pid"], "Actual installed writer PID")
            if not row["writer_reaped"] or not row["source_unchanged"]:
                raise ValueError("Preparation writer ownership/source failure")
            record = {key: value for key, value in row.items() if key != "pid"}
            record["observed_barrier"] = {
                key: value for key, value in row["observed_barrier"].items() if key != "pid"
            }
            faults.append(normalize(record, raw["artifacts"]))
        preparation = {"cases": normalize(raw["cases"], raw["artifacts"]), "faults": faults}
        equal(preparation, measured["preparation"], "Preparation raw ledger/rerun")
        equal(preparation, prior["preparation"], "Preparation predecessor outcomes")
    package = {
        name.removeprefix("measured/src/"): sha(raw)
        for name, raw in read.items()
        if name.startswith("measured/src/bookscan/")
    }
    equal(sorted(package), measured["wheel_product_members"], "Full product member roster")
    with zipfile.ZipFile(
        io.BytesIO(read["wheel/bookscan_builder-0.1.0-py3-none-any.whl"])
    ) as wheel:
        equal(
            set(package),
            {name for name in wheel.namelist() if name.startswith("bookscan/")},
            "Wheel product roster",
        )
        for name, digest in package.items():
            equal(sha(wheel.read(name)), digest, "Wheel/source product bytes")
            installed = [
                info["sha256"]
                for path, info in subjects.items()
                if path.endswith("installed/lib/python3.12/site-packages/" + name)
            ]
            equal(installed, [digest], "Frozen installed product bytes")
    for name, raw in read.items():
        if name.startswith("measured/"):
            subject = "/Users/antony/Development/BookScanBuilder/" + name.removeprefix("measured/")
            equal(sha(raw), subjects[subject]["sha256"], "Retained measured subject bytes")
    # Each isolated omission must fail its exact named cases and leave the rest green.
    mutations = data("mutations/result.json")
    intended = {
        "binding": [
            "absent-file",
            "bad-digest",
            "digest-disagreement",
            "resolved-disagreement",
            "unbound-file",
        ],
        "sequence": [
            "load-missing-command",
            "load-wrong-kind",
            "ref-kind",
            "ref-order",
            "ref-reference",
        ],
        "closure": ["orphan"],
        "header": [
            "/historical/program (architecture x86_64):",
            "/historical/program garbage:",
            "/historical/program-other:",
        ],
    }
    for label, expected_cases in intended.items():
        raw = read[f"mutations/{label}/result.xml"]
        cases = units(raw)
        equal(len(cases), 63, "Mutation construction roster")
        failures = sorted(
            node.attrib["name"].removesuffix("]").split("[")[-1]
            for node in ET.fromstring(raw).iter("testcase")
            if node.find("failure") is not None
        )
        equal(failures, expected_cases, "Isolated omission disproof")
        equal(mutations[label]["failed_cases"], expected_cases, "Mutation ledger")
        if any(values not in ([], ["failure"]) for values in cases.values()):
            raise ValueError("Mutation error or skipped case")
        equal(
            sha(read[f"mutations/{label}/bookscan/linked_record.py"]),
            mutations[label]["mutated_sha256"],
            "Mutation subject",
        )
    return {
        "verified": True,
        "units": len(a),
        "new_units": len(new),
        "frozen_subjects": len(subjects),
        "native_graphs_per_reading": 2,
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
    equal(
        {name: sha(raw) for name, raw in read.items()},
        index["entries"],
        "Complete archive inventory",
    )
    return read


if __name__ == "__main__":
    print(json.dumps(verify(reconstruct(Path(__file__).parent)), sort_keys=True))
