"""Reconstruct saved native channel/colour record evidence; no full project or fidelity claim."""

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
    equal(a, units(read["frozen/gate-b.xml"]), "Itemwise full rerun")
    equal(a, measured["units"], "Full ledger")
    if any(a.values()):
        raise ValueError("Failed full construction")
    equal(prior["units"], {key: a[key] for key in prior["units"]}, "Predecessor units")
    new = sorted(set(a) - set(prior["units"]))
    equal(new, measured["new_units"], "New unit ledger")
    equal(len(new), 54, "Native reader constructions")
    if not all("test_native_sample_record." in key for key in new):
        raise ValueError("Unexpected new construction")
    selected = {
        key: value
        for key, value in a.items()
        if any(
            name in key
            for name in (
                "test_native_sample_record.",
                "test_samples.",
                "test_profiles.",
                "test_assessment.",
            )
        )
    }
    for suffix in ("a", "b"):
        equal(units(read[f"frozen/wheel-units-{suffix}.xml"]), selected, "Installed constructions")
    equal(units(read["frozen/staff-a.xml"]), units(read["frozen/staff-b.xml"]), "Staff rerun")
    if (
        b"46 failed" not in read["red.txt"]
        or b"cannot import name 'native_sample_record'" not in read["red.txt"]
    ):
        raise ValueError("Missing absent-reader disproof")
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
        equal(facts, expected, "Native ledger")
        equal(facts, next(iter(measured["native"].values())), "Native rerun")
        equal(facts["accepted_project_delivered"], False, "No accepted project")
        equal(facts["composition_fidelity_verified"], False, "No composition truth")
        legacy = json.loads(json.dumps(facts))
        for row in legacy["records"]:
            for entry in row["native_samples"]:
                entry.pop("resolved_color")
        equal(legacy, next(iter(prior["native"].values())), "Native predecessor facts")
    for label, expected in measured["sample"].items():
        raw = data(f"frozen/{label}/report.json")
        equal(raw, expected, "Native sample ledger")
        equal(raw, next(iter(measured["sample"].values())), "Sample source/wheel rerun")
        equal(
            [
                raw[key]
                for key in (
                    "all_pdf_paths_removed",
                    "composition_verified",
                    "accepted_project_delivered",
                )
            ],
            [True, False, False],
            "Source loss, no invented fidelity/project",
        )
        blobs = {name: read[f"frozen/{label}/blobs/{name}"] for name in raw["blobs"]}
        equal(
            {sha(blob): len(blob) for blob in blobs.values()}, raw["blobs"], "Retained blob bytes"
        )
        used: set[str] = set()
        for row in raw["rows"]:
            equal(len(row["records"]), row["sample_count"], "Sample roster")
            for entry in row["records"]:
                equal(entry["composition_verified"], False, "No sample composition truth")
                pending = [entry["resolved_color"]]
                digest = entry["packed_sha256"]
                used.add(digest)
                colour = entry["resolved_color"]
                width, height = entry["placement"]["samples"]
                bits = entry["placement"]["bits_per_component"]
                equal(
                    len(blobs[digest]),
                    ((width * colour["components"] * bits + 7) // 8) * height,
                    "Full native channel grid",
                )
                while pending:
                    current = pending.pop()
                    if current is not None:
                        for field in ("profile_sha256", "palette_sha256"):
                            if current[field] is not None:
                                used.add(current[field])
                                equal(
                                    sha(blobs[current[field]]),
                                    current[field],
                                    "Native colour bytes",
                                )
                        pending.append(current["base"])
        equal(used, set(blobs), "Complete retained blob inventory")
        for control in raw["controls"]:
            equal(control["refused"], raw["truth"]["controls"], "Required wrong-subject refusals")
        equal(len(raw["rows"]), 16, "All constructed pages including blank/duplicates")
        equal(len(raw["controls"]), 14, "Every contributing sample controlled")
    for suffix in ("a", "b"):
        raw = data(f"frozen/preparation-{suffix}/report.json")
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
            faults.append(normalize(entry, raw["artifacts"]))
        facts = {"cases": normalize(raw["cases"], raw["artifacts"]), "faults": faults}
        equal(facts, measured["preparation"], "Preparation ledger")
        equal(facts, prior["preparation"], "Preparation predecessor")
        equal(len(faults), 38, "Actual writer fault roster")
    package = {
        name.removeprefix("measured/src/"): sha(raw)
        for name, raw in read.items()
        if name.startswith("measured/src/bookscan/")
    }
    equal(package, measured["package_members"], "Source package ledger")
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
            equal(installed, [digest], "Installed bytes")
    for name, raw in read.items():
        if name.startswith("measured/"):
            subject = "/Users/antony/Development/BookScanBuilder/" + name.removeprefix("measured/")
            equal(sha(raw), subjects[subject]["sha256"], "Retained measured bytes")
    omissions = data("omission-controls.json")
    equal(
        set(omissions),
        {"blob-digest", "placement", "grid", "colour-binding"},
        "Complete omission disproof",
    )
    for label, expected in omissions.items():
        outcomes = units(read[f"omissions/{label}/outcomes.xml"])
        if any(value not in ([], ["failure"]) for value in outcomes.values()):
            raise ValueError("Omission error or skipped case")
        equal(
            sorted(key.split(".")[-1] for key, value in outcomes.items() if value),
            sorted(expected["failed"]),
            "Omission failures",
        )
        equal(
            sorted(key.split(".")[-1] for key, value in outcomes.items() if not value),
            sorted(expected["passed"]),
            "Omission unrelated passes",
        )
        if not expected["failed"] or not expected["passed"]:
            raise ValueError("Omission without positive and negative controls")
    return {
        "verified": True,
        "units": len(a),
        "new_units": len(new),
        "frozen_subjects": len(subjects),
        "public_finite_delivery": False,
    }


def reconstruct(directory: Path) -> dict[str, bytes]:
    index = json.loads(gzip.decompress((directory / "index.json.gz").read_bytes()))
    equal(index["format"], "BookScanBuilderNativeSampleEvidence", "Evidence format")
    equal(index["version"], 1, "Evidence version")
    chunks: list[bytes] = []
    for ordinal, part in enumerate(index["parts"]):
        equal(part["name"], f"raw-{ordinal:03d}.zippart", "Safe ordered part names")
        raw = (directory / part["name"]).read_bytes()
        equal(len(raw), part["size"], "Archive part size")
        if not 0 < len(raw) <= 900000:
            raise ValueError("Invalid archive part extent")
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
