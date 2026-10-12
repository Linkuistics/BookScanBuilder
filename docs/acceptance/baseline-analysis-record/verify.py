"""Reconstruct saved-analysis evidence; host libraries remain digest references."""

import argparse
import gzip
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import cast


def sha(raw: bytes | bytearray) -> str:
    return hashlib.sha256(raw).hexdigest()


def equal(left: object, right: object) -> None:
    if left != right:
        raise ValueError("Saved-analysis evidence disagreement")


def units(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for row in ET.fromstring(raw).iter("testcase"):
        key = row.attrib["classname"] + "." + row.attrib["name"]
        if key in result:
            raise ValueError("Duplicate unit identity")
        result[key] = [c.tag for c in row if c.tag in {"failure", "error", "skipped"}]
    return result


def normalize(value: object, directory: str) -> object:
    if isinstance(value, str):
        return re.sub(
            r"\.bookscan-prepare-[0-9a-f]{32}\.tmp",
            ".bookscan-prepare-OWNED.tmp",
            value.replace(directory, "ARTIFACTS"),
        )
    if isinstance(value, list):
        return [normalize(item, directory) for item in cast(list[object], value)]
    if isinstance(value, dict):
        return {k: normalize(v, directory) for k, v in cast(dict[str, object], value).items()}
    return value


def verify(read: dict[str, bytes]) -> dict[str, object]:
    def data(name: str) -> dict[str, object]:
        return cast(dict[str, object], json.loads(read[name]))

    measured, prior = data("frozen/measurement.json"), data("prior-measurement.json")
    equal(read["frozen/subjects-before.json.gz"], read["frozen/subjects-after.json.gz"])
    subjects = cast(
        dict[str, object], json.loads(gzip.decompress(read["frozen/subjects-before.json.gz"]))
    )
    equal(len(subjects), measured["subjects"])
    equal(
        data("frozen/frozen-status.json"),
        {"completed": True, "unchanged": True, "subjects": len(subjects)},
    )
    a, b = units(read["frozen/gate-a.xml"]), units(read["frozen/gate-b.xml"])
    equal(a, b)
    equal(a, measured["units"])
    if any(a.values()):
        raise ValueError("Failed unit construction")
    previous = cast(dict[str, object], prior["units"])
    equal(previous, {key: a[key] for key in previous})
    added = sorted(set(a) - set(previous))
    equal(added, measured["new_units"])
    equal(len(added), 97)
    if not all(
        "test_analysis_record" in k
        or k.endswith(".test_assessed_serialization_cannot_save_inconsistent_analysis")
        for k in added
    ):
        raise ValueError("Unexpected new unit scope")
    wanted = {k: v for k, v in a.items() if "test_analysis_record" in k or "test_assessment." in k}
    for suffix in ("a", "b"):
        equal(units(read["frozen/wheel-units-" + suffix + ".xml"]), wanted)
    equal(units(read["frozen/staff-a.xml"]), units(read["frozen/staff-b.xml"]))
    equal(len(units(read["red.xml"])), 95)
    if not all(units(read["red.xml"]).values()):
        raise ValueError("Missing first-red observation")
    if b"DID NOT RAISE" not in read["bypass-control.log"]:
        raise ValueError("Missing serializer bypass failure")

    native = cast(dict[str, object], measured["native"])
    expected: dict[str, object] | None = None
    for lane in ("source", "wheel"):
        for suffix in ("a", "b"):
            label = "assessment-" + lane + "-" + suffix
            report = data("frozen/" + label + "/report.json")
            reading = {
                k: report[k]
                for k in (
                    "truth",
                    "truth_sha256",
                    "records",
                    "controls",
                    "source_loss_itemwise_equal",
                    "accepted_project_delivered",
                    "composition_fidelity_verified",
                )
            }
            equal(reading, native[label])
            if expected is None:
                expected = reading
            equal(reading, expected)
            equal(report["source_loss_itemwise_equal"], True)
            equal(report["accepted_project_delivered"], False)
            equal(report["composition_fidelity_verified"], False)
            equal(sha(read["frozen/" + label + "/snapshot.pdf"]), report["source_sha256"])
            rows = cast(list[dict[str, object]], report["records"])
            equal(len(rows), 7)
            equal(len(cast(dict[str, object], report["controls"])), 9)
            for ordinal, row in enumerate(rows, 1):
                equal(row["id"], f"occ-{ordinal:06d}")
                equal(row["source_pdf_page"], ordinal)
                equal(row["source_sha256"], report["source_sha256"])
                equal(row["inspected"], False)
                equal(row["estimate_applied"], False)
                equal(row["composition_fidelity_verified"], False)
                analysis = cast(dict[str, object], row["analysis"])
                equal(analysis["regions"], [[0, 0, 1200, 900]])
                status, angle, ratio = (
                    analysis[k] for k in ("native_status", "angle_degrees", "score_ratio")
                )
                available = status == 0 and angle is not None and ratio is not None and ratio != 0
                equal(analysis["available"], available)
                invalid = [
                    key + ":nonfinite"
                    for key in ("angle_degrees", "score_ratio")
                    if analysis[key] is None
                ]
                equal(analysis["invalid_numeric"], invalid)
                reasons = cast(list[str], analysis["reasons"])
                equal("assessment-unavailable" in reasons, not available)
                equal("skew-nonzero" in reasons, available and angle != 0)
                if ordinal in (1, 2, 3, 7):
                    if (
                        not available
                        or not isinstance(angle, float)
                        or abs(angle - {1: 0.0, 2: -2.0, 3: 2.0, 7: 0.0}[ordinal]) > 0.125
                    ):
                        raise ValueError("Native sign/angle construction failed")
                elif ordinal == 4:
                    equal(available, False)
                    if "skew-range-edge" not in reasons:
                        raise ValueError("Missing native range edge")
                elif ordinal == 5:
                    equal(available, False)
                    equal(ratio, 0.0)

    preparation: object = None
    for suffix in ("a", "b"):
        report = data("frozen/preparation-" + suffix + "/report.json")
        faults = cast(dict[str, object], report["fault_checks"])
        rows = cast(list[dict[str, object]], faults["observed_signal_and_kill_cases"])
        readings: list[object] = []
        for row in rows:
            barrier = cast(dict[str, object], row["observed_barrier"])
            equal(row["pid"], barrier["pid"])
            equal(row["writer_reaped"], True)
            equal(row["source_unchanged"], True)
            item = {k: v for k, v in row.items() if k != "pid"}
            item["observed_barrier"] = {k: v for k, v in barrier.items() if k != "pid"}
            readings.append(normalize(item, cast(str, report["artifacts"])))
        current = {
            "cases": normalize(report["cases"], cast(str, report["artifacts"])),
            "faults": readings,
        }
        if preparation is None:
            preparation = current
        equal(current, preparation)
        equal(current, prior["preparation"])
        equal(current, measured["preparation"])
    package = {k.removeprefix("product/"): v for k, v in read.items() if k.startswith("product/")}
    with zipfile.ZipFile(
        io.BytesIO(read["wheel/bookscan_builder-0.1.0-py3-none-any.whl"])
    ) as wheel:
        equal(set(package), {n for n in wheel.namelist() if n.startswith("bookscan/")})
        equal(sorted(package), measured["wheel_product_members"])
        for name, raw in package.items():
            equal(wheel.read(name), raw)
            equal(read["installed/" + name], raw)
    equal(measured["public_finite_delivery"], False)
    return {
        "verified": True,
        "units": len(a),
        "new_units": len(added),
        "installed_focused": len(wanted),
        "native_occurrences_per_reading": 7,
        "subjects": len(subjects),
        "complete_project_delivered": False,
    }


def run(directory: Path) -> dict[str, object]:
    index = cast(
        dict[str, object], json.loads(gzip.decompress((directory / "index.json.gz").read_bytes()))
    )
    raw = bytearray()
    for part in cast(list[dict[str, object]], index["parts"]):
        name = cast(str, part["name"])
        if re.fullmatch(r"raw-[0-9]{3}\.zippart", name) is None:
            raise ValueError("Invalid evidence part name")
        chunk = (directory / name).read_bytes()
        equal((len(chunk), sha(chunk)), (part["size"], part["sha256"]))
        if len(chunk) > 900_000:
            raise ValueError("Oversized evidence part")
        raw.extend(chunk)
    equal((len(raw), sha(raw)), (index["archive_size"], index["archive_sha256"]))
    entries = cast(dict[str, dict[str, object]], index["entries"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        equal(len(archive.namelist()), len(set(archive.namelist())))
        equal(set(archive.namelist()), {"blobs/" + str(v["sha256"]) for v in entries.values()})
        read: dict[str, bytes] = {}
        for name, item in entries.items():
            blob = archive.read("blobs/" + str(item["sha256"]))
            equal((len(blob), sha(blob)), (item["size"], item["sha256"]))
            read[name] = blob
    equal(read["instrument/verify.py"], Path(__file__).read_bytes())
    return verify(read)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    print(json.dumps(run(parser.parse_args().directory), indent=2))
