"""Reconstruct exact native-header evidence; never infer public delivery or fidelity."""

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


def verify(read: dict[str, bytes]) -> dict[str, object]:
    def data(name: str) -> Any:
        return json.loads(read[name])

    measured, prior = data("final/measurement.json"), data("prior-measurement.json")
    equal(measured["public_finite_delivery"], False, "No finite delivery")
    equal(read["final/subjects-before.json.gz"], read["final/subjects-after.json.gz"], "Freeze")
    subjects = json.loads(gzip.decompress(read["final/subjects-before.json.gz"]))
    equal(len(subjects), measured["subjects"], "Complete subject roster")
    equal(
        data("final/frozen-status.json"),
        {"completed": True, "unchanged": True, "subjects": len(subjects)},
        "Completed frozen reading",
    )
    ledger = units(read["final/gate-a.xml"])
    equal(ledger, units(read["final/gate-b.xml"]), "Full itemwise rerun")
    equal(ledger, measured["units"], "Full outcome ledger")
    if any(ledger.values()):
        raise ValueError("Failed full construction")
    equal(prior["units"], {name: ledger[name] for name in prior["units"]}, "Predecessor outcomes")
    new = sorted(set(ledger) - set(prior["units"]))
    equal(new, measured["new_units"], "New constructions")
    equal(len(new), 21, "Native header construction roster")
    if not all("test_native_header." in name for name in new):
        raise ValueError("Unexpected new construction")
    selected = {
        name: value
        for name, value in ledger.items()
        if any(
            part in name
            for part in (
                "test_native_header.",
                "test_project_header.",
                "test_native_blobs.",
                "test_native_inventory_record.",
            )
        )
    }
    for suffix in ("a", "b"):
        equal(units(read[f"final/wheel-units-{suffix}.xml"]), selected, "Installed outcomes")
    equal(
        units(read["final/staff-a.xml"]), units(read["final/staff-b.xml"]), "Staff itemwise rerun"
    )
    if b"13 failed, 8 passed" not in read["red.txt"]:
        raise ValueError("Missing native-header disproof")
    failures = {
        "directory": [
            "test_native_directory_replacement_refuses_before_semantics_and_releases_lock["
            + kind
            + "]"
            for kind in ("copy", "missing", "symlink", "file", "fifo")
        ]
        + ["test_native_replacement_during_semantics_is_checked_after_callback"],
        "semantic-history": [
            "test_native_identity_and_inventory_resume_from_header_only",
            "test_native_replacement_during_semantics_is_checked_after_callback",
            "test_predecessor_only_native_corruption_cannot_hide_behind_empty_current",
            "test_predecessor_inventory_semantics_are_not_replaced_by_blob_digest",
            "test_resume_preserves_selected_owner_error_and_releases_lock[error0]",
            "test_resume_preserves_selected_owner_error_and_releases_lock[error1]",
        ],
    }
    omissions = data("omission-controls.json")
    equal({row["omission"] for row in omissions}, set(failures), "Omission roster")
    for row in omissions:
        label = row["omission"]
        observed = units(read[f"omission-{label}.xml"])
        equal(observed, row["ledger"], "Omission outcome ledger")
        failed = [
            name.split("tests.test_native_header.", 1)[1]
            for name, outcome in observed.items()
            if outcome
        ]
        equal(failed, failures[label], "Isolated omission disproof")
        equal(set(observed), set(new), "Complete omission suite")
        if any(outcome not in ([], ["failure"]) for outcome in observed.values()):
            raise ValueError("Unexpected omission error/skip")
    package = measured["package_members"]
    with zipfile.ZipFile(
        io.BytesIO(read["wheel/bookscan_builder-0.1.0-py3-none-any.whl"])
    ) as wheel:
        equal(
            set(package), {n for n in wheel.namelist() if n.startswith("bookscan/")}, "Wheel roster"
        )
        for name, digest in package.items():
            equal(sha(wheel.read(name)), digest, "Wheel bytes")
            equal(sha(read["src/" + name]), digest, "Product source bytes")
            equal(
                subjects[
                    "/private/tmp/bookscan-k63-native-header.ip551gyh/installed/lib/python3.12/site-packages/"
                    + name
                ]["sha256"],
                digest,
                "Installed product bytes",
            )
    captures = measured["inventories"]
    base = next(iter(captures.values()))
    for label, capture in captures.items():
        raw = data(f"final/{label}/report.json")
        equal(
            {
                key: value
                for key, value in raw.items()
                if key not in ("native_identity", "saved_header")
            },
            capture,
            "Inventory raw capture",
        )
        equal(capture, base, "Inventory itemwise source/wheel rerun")
        equal(
            raw["saved_header"],
            data(f"final/{label}/project/project.json"),
            "Retained project header",
        )
        equal(
            raw["saved_header"]["native_blobs"],
            raw["native_identity"]["blobs"],
            "Saved native identity",
        )
        equal(
            raw["saved_header"]["checkpoints"],
            raw["native_identity"]["checkpoints"],
            "Saved history identity",
        )
        equal(
            capture["restart_identity_source"],
            "project.json; references in each checkpoint",
            "Saved restart context",
        )

        equal(capture["all_pdf_paths_removed"], True, "Observed PDF loss")
        equal(capture["reopened_checkpoint_revision"], 2, "Reopened complete history")
        equal(capture["composition_fidelity_verified"], False, "No composition verdict")
        equal(capture["accepted_project_delivered"], False, "No accepted project")
        equal(
            [(row["case"], row["source_pdf_page"]) for row in capture["rows"]],
            [
                (case, ordinal)
                for case, count in (("packed", 8), ("profile", 8), ("placement", 15))
                for ordinal in range(1, count + 1)
            ],
            "Exact occurrence order",
        )
        references = {row["sha256"]: row for row in capture["references"]}
        equal(len(references), len(capture["references"]), "Unique native reference roster")
        for digest, reference in references.items():
            blob = read[f"final/{label}/project/native-blobs/{digest}.bin"]
            equal(
                reference,
                {
                    "format": "BookScanBuilderNativeBlob",
                    "version": 1,
                    "sha256": sha(blob),
                    "byte_size": len(blob),
                },
                "Exact retained native blob",
            )
        used: set[str] = set()
        for index, row in enumerate(capture["rows"]):
            inventory = row["inventory"]
            resolution = inventory["resolution"]
            equal(inventory["composition_fidelity_verified"], False, "No per-occurrence verdict")
            if not inventory["composition_unavailable"]:
                raise ValueError("Missing independent composition oracle limitation")
            equal(
                [image["placement"] for image in inventory["native_samples"]],
                resolution["placements"],
                "Complete ordered sample/placement binding",
            )
            equal(resolution["complete"], not resolution["concerns"], "Resolution completeness")
            expected_max = max((max(p["ppi"]) for p in resolution["placements"]), default=None)
            equal(
                resolution["maximum_ppi"],
                expected_max if resolution["complete"] else None,
                "Resolution maximum",
            )
            expected_concerns = [
                "/".join(s["placement"]["path"]) + ": " + s["unavailable"]
                for s in inventory["native_samples"]
                if s["unavailable"]
            ]
            equal(
                inventory["native_sample_concerns"],
                expected_concerns,
                "Unavailable sample concerns",
            )
            for sample in inventory["native_samples"]:
                equal(sample["composition_verified"], False, "No sample fidelity claim")
                pending = [sample]
                while pending:
                    item = pending.pop()
                    if not isinstance(item, dict):
                        continue
                    item = cast(dict[str, Any], item)
                    for key in ("packed_sha256", "profile_sha256", "palette_sha256"):
                        if item.get(key) is not None:
                            digest = item[key]
                            if digest not in references:
                                raise ValueError("Unbound retained native bytes")
                            used.add(digest)
                    pending.extend([item.get("resolved_color"), item.get("base")])
            equal(
                capture["controls"][index],
                {
                    "ordinal": index,
                    "refused": [
                        "wrong-maximum",
                        "false-completeness",
                        "false-composition",
                        "lost-sample",
                    ],
                },
                "Required per-occurrence controls",
            )
        equal(used, set(references), "Exact referenced native closure")
        old = next(iter(prior["inventories"].values()))
        equal({key: capture[key] for key in old}, old, "Predecessor inventory meanings")
    for label, capture in measured["native"].items():
        raw = data(f"final/{label}/report.json")
        equal({key: raw[key] for key in capture}, capture, "Assessment raw capture")
        equal(capture, next(iter(prior["native"].values())), "Predecessor assessment meanings")
    for suffix in ("a", "b"):
        report = data(f"final/writer-{suffix}/report.json")
        writer_ledger: dict[str, object] = {}
        for row in report["cases"]:
            label = row["id"]
            raw = data(f"final/writer-{suffix}/{label}.json")
            equal(raw["reading"], row, "Writer reading")
            event = raw["event"]
            equal(event["writer_pid"], row["writer_pid"], "Observed writer PID")
            equal(
                event["native_directory"], event["header"]["native_blobs"], "Writer native identity"
            )
            equal(
                data(f"final/writer-{suffix}/{label}/project.json"),
                event["header"],
                "Saved writer header",
            )
            equal(row["reacquired"], True, "Writer reaped/reacquired")
            expected_exit = (
                0 if row["signal"] == 0 else (-9 if row["signal"] == 9 else 128 + row["signal"])
            )
            equal(row["exit_code"], expected_exit, "Exact writer exit")
            equal(
                row["committed"],
                row["signal"] == 0 or row["phase"] in ("inside-pointer", "post-pointer"),
                "Writer commit fact",
            )
            equal(
                row["revision"],
                int(row["update"]) + int(row["committed"]),
                "Writer checkpoint visibility",
            )
            writer_ledger[label] = {
                k: v
                for k, v in row.items()
                if k not in ("writer_pid", "checkpoint_sha256", "package")
            }
        equal(len(writer_ledger), 40, "Complete writer roster")
        equal(writer_ledger, measured["writers"][suffix], "Writer itemwise record")
    equal(measured["writers"]["a"], measured["writers"]["b"], "Writer itemwise rerun")
    for suffix in ("a", "b"):
        report = data(f"final/preparation-{suffix}/report.json")
        directory = report["artifacts"]
        faults: list[dict[str, object]] = []
        for row in report["fault_checks"]["observed_signal_and_kill_cases"]:
            equal(row["pid"], row["observed_barrier"]["pid"], "Observed preparation owner")
            equal(row["writer_reaped"], True, "Preparation owner reaped")
            equal(row["source_unchanged"], True, "Preparation source unchanged")
            entry = {key: value for key, value in row.items() if key != "pid"}
            entry["observed_barrier"] = {
                key: value for key, value in row["observed_barrier"].items() if key != "pid"
            }
            faults.append(normalize(entry, directory))
        capture = {"cases": normalize(report["cases"], directory), "faults": faults}
        equal(capture, measured["preparation"], "Preparation raw capture")
        equal(capture, prior["preparation"], "Predecessor preparation meanings")
    for name, raw in read.items():
        if name.startswith(("src/", "tests/")):
            equal(
                sha(raw),
                subjects["/Users/antony/Development/BookScanBuilder/" + name]["sha256"],
                "Frozen source identity",
            )
    return {
        "units": len(ledger),
        "new_units": len(new),
        "subjects": len(subjects),
        "entries": len(read),
        "public_finite_delivery": False,
    }


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
    equal(index["format"], "BookScanBuilderNativeHeaderEvidence", "Archive format")
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


if __name__ == "__main__":
    print(json.dumps(verify(load(Path(__file__).parent)), sort_keys=True))
