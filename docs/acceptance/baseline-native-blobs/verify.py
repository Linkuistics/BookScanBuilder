"""Reconstruct exact native-blob evidence; never infer public delivery or fidelity."""

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


def equal(left: object, right: object, message: str) -> None:
    if left != right:
        raise ValueError(message)


def units(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for row in ET.fromstring(raw).iter("testcase"):
        name = row.attrib["classname"] + "." + row.attrib["name"]
        if name in result:
            raise ValueError("Duplicate construction identity")
        result[name] = [c.tag for c in row if c.tag in {"error", "failure", "skipped"}]
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


def load(directory: Path) -> dict[str, bytes]:
    index = json.loads(gzip.decompress((directory / "index.json.gz").read_bytes()))
    equal(set(index), {"format", "version", "parts", "entries"}, "Archive fields")
    equal(index["format"], "BookScanBuilderNativeBlobEvidence", "Archive format")
    equal(index["version"], 1, "Archive version")
    chunks: list[bytes] = []
    for part in index["parts"]:
        name = part["name"]
        if Path(name).name != name:
            raise ValueError("Nonlocal archive part")
        raw = (directory / name).read_bytes()
        equal(len(raw), part["size"], "Part size")
        equal(sha(raw), part["sha256"], "Part digest")
        if len(raw) > 900_000:
            raise ValueError("Oversized part")
        chunks.append(raw)
    with zipfile.ZipFile(io.BytesIO(b"".join(chunks))) as archive:
        names = archive.namelist()
        expected = {"blobs/" + row["sha256"] for row in index["entries"].values()}
        equal(set(names), expected, "Complete archive inventory")
        equal(len(names), len(expected), "Unique archive members")
        result: dict[str, bytes] = {}
        for name, row in index["entries"].items():
            raw = archive.read("blobs/" + row["sha256"])
            equal(len(raw), row["size"], "Entry size")
            equal(sha(raw), row["sha256"], "Entry digest")
            result[name] = raw
    return result


def verify(read: dict[str, bytes]) -> dict[str, object]:
    def data(name: str) -> Any:
        return json.loads(read[name])

    measured = data("frozen/measurement.json")
    prior = data("prior-measurement.json")
    equal(measured["public_finite_delivery"], False, "No finite delivery")
    equal(read["frozen/subjects-before.json.gz"], read["frozen/subjects-after.json.gz"], "Freeze")
    subjects = json.loads(gzip.decompress(read["frozen/subjects-before.json.gz"]))
    equal(len(subjects), measured["subjects"], "Subject roster")
    equal(
        data("frozen/frozen-status.json"),
        {"completed": True, "unchanged": True, "subjects": len(subjects)},
        "Completed measurement",
    )
    a = units(read["frozen/gate-a.xml"])
    equal(a, units(read["frozen/gate-b.xml"]), "Full itemwise rerun")
    equal(a, measured["units"], "Full ledger")
    if any(a.values()):
        raise ValueError("Failed full construction")
    equal(prior["units"], {key: a[key] for key in prior["units"]}, "Predecessor retention")
    new = sorted(set(a) - set(prior["units"]))
    equal(new, measured["new_units"], "New constructions")
    equal(len(new), 50, "Blob construction inventory")
    if not all("test_native_blobs." in name for name in new):
        raise ValueError("Unexpected new construction")
    selected = {
        k: v for k, v in a.items() if "test_native_blobs." in k or "test_native_sample_record." in k
    }
    for suffix in ("a", "b"):
        equal(units(read[f"frozen/wheel-units-{suffix}.xml"]), selected, "Installed constructions")
    equal(units(read["frozen/staff-a.xml"]), units(read["frozen/staff-b.xml"]), "Staff rerun")
    red = units(read["red.xml"])
    equal(len(red), 40, "Initial red inventory")
    if (
        any(value != ["failure"] for value in red.values())
        or b"cannot import name 'native_blobs'" not in read["red.log"]
    ):
        raise ValueError("Missing absent-module disproof")
    expected_omissions = {
        "digest": [
            "test_changed_missing_or_aliased_blob_refused_without_repair[bytes]",
            "test_wrong_staged_disk_bytes_never_publish",
            "test_saved_sample_and_every_history_reference_require_exact_blobs",
        ],
        "length": ["test_changed_missing_or_aliased_blob_refused_without_repair[length]"],
        "directory": ["test_saved_directory_identity_prevents_redirected_read_or_write[directory]"],
        "cleanup": ["test_replaced_private_cleanup_name_is_never_deleted"],
    }
    controls = data("omission-controls.json")
    equal({r["omission"] for r in controls}, set(expected_omissions), "Omission inventory")
    for row in controls:
        label = row["omission"]
        ledger = units(read[f"omission-{label}.xml"])
        failed = [k.split(".test_native_blobs.", 1)[1] for k, v in ledger.items() if v]
        passed = [k.split(".test_native_blobs.", 1)[1] for k, v in ledger.items() if not v]
        equal(failed, row["failures"], "Observed omission ledger")
        equal(failed, expected_omissions[label], "Required independent disproof")
        equal(passed, row["passed"], "Unrelated constructions")
        equal(len(ledger), 50, "Complete omission suite")
    package = measured["package_members"]
    with zipfile.ZipFile(
        io.BytesIO(read["wheel/bookscan_builder-0.1.0-py3-none-any.whl"])
    ) as wheel:
        equal(
            set(package),
            {n for n in wheel.namelist() if n.startswith("bookscan/")},
            "Wheel inventory",
        )
        for name, digest in package.items():
            equal(sha(wheel.read(name)), digest, "Wheel bytes")
            equal(sha(read["src/" + name]), digest, "Source bytes")
    for label, facts in measured["sample"].items():
        raw = data(f"frozen/{label}/report.json")
        equal({k: v for k, v in raw.items() if k != "native_identity"}, facts, "Sample ledger")
        equal(facts["all_pdf_paths_removed"], True, "Actual source loss")
        equal(facts["reopened_checkpoint_revision"], 2, "Reopened history")
        equal(facts["composition_verified"], False, "No composition claim")
        equal(facts["accepted_project_delivered"], False, "No accepted project claim")
        original = {
            k: v
            for k, v in facts.items()
            if k not in ("references", "reopened_checkpoint_revision")
        }
        original["format"] = "BookScanBuilderNativeSampleRecordAcceptance"
        equal(original, next(iter(prior["sample"].values())), "Predecessor sample meanings")
        for reference in facts["references"]:
            digest = reference["sha256"]
            blob = read[f"frozen/{label}/project/native-blobs/{digest}.bin"]
            equal(sha(blob), digest, "Native retained bytes")
            equal(len(blob), reference["byte_size"], "Native retained length")
    for label, facts in measured["native"].items():
        raw = data(f"frozen/{label}/report.json")
        equal({k: raw[k] for k in facts}, facts, "Assessment capture")
        equal(facts, next(iter(prior["native"].values())), "Predecessor assessment meaning")
    equal(measured["processes"]["a"], measured["processes"]["b"], "Process itemwise rerun")
    for suffix in ("a", "b"):
        raw = data(f"frozen/process-{suffix}/result.json")
        equal(len(raw["records"]), 8, "Process inventory")
        for row in raw["records"]:
            phase, number = row["case"].rsplit("-", 1)
            number = int(number)
            equal(
                row["exit"],
                0 if number == 0 else -9 if number == 9 else 128 + number,
                "Signal exit",
            )
            equal(bool(row["visible_before"]), phase == "post-link", "Pre-action visibility")
            equal(
                bool(row["visible_after"]),
                number == 0 or phase == "post-link",
                "Publication visibility",
            )
            equal(bool(row["private_names"]), number == 9, "Private kill outcome")
            equal(row["checkpoint"], False, "No saved review state")
            equal(row["immediate_reacquisition"], True, "Reaped ownership")
            if type(row["barrier"]["writer_pid"]) is not int or row["barrier"]["writer_pid"] <= 0:
                raise ValueError("Missing observed writer PID")
        equal(
            raw["product_sha256"], package["bookscan/native_blobs.py"], "Installed process product"
        )
    for suffix in ("a", "b"):
        report = data(f"frozen/preparation-{suffix}/report.json")
        directory = report["artifacts"]
        faults: list[dict[str, object]] = []
        for row in report["fault_checks"]["observed_signal_and_kill_cases"]:
            equal(row["pid"], row["observed_barrier"]["pid"], "Observed preparation writer")
            equal(row["writer_reaped"], True, "Preparation writer reaped")
            equal(row["source_unchanged"], True, "Preparation source unchanged")
            entry = {k: v for k, v in row.items() if k != "pid"}
            entry["observed_barrier"] = {
                k: v for k, v in row["observed_barrier"].items() if k != "pid"
            }
            faults.append(normalize(entry, directory))
        facts = {"cases": normalize(report["cases"], directory), "faults": faults}
        equal(facts, measured["preparation"], "Preparation capture")
        equal(facts, prior["preparation"], "Preparation predecessor meanings")
    for name, raw in read.items():
        if name.startswith(("src/", "tests/")):
            path = "/Users/antony/Development/BookScanBuilder/" + name
            equal(sha(raw), subjects[path]["sha256"], "Retained frozen source")
    return {
        "units": len(a),
        "new_units": len(new),
        "subjects": len(subjects),
        "entries": len(read),
        "public_finite_delivery": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(load(Path(__file__).parent)), sort_keys=True))
