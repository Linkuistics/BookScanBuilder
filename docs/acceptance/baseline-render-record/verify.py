"""Reconstruct saved-render-policy evidence; host/tool dependencies remain digest references."""

import gzip
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import cast


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
        return [normalize(v, directory) for v in cast(list[object], value)]
    if isinstance(value, dict):
        return {k: normalize(v, directory) for k, v in cast(dict[str, object], value).items()}
    return value


def verify(read: dict[str, bytes]) -> dict[str, object]:
    def data(name: str) -> dict[str, object]:
        return cast(dict[str, object], json.loads(read[name]))

    measured, prior = data("frozen/measurement.json"), data("prior-measurement.json")
    equal(read["frozen/subjects-before.json.gz"], read["frozen/subjects-after.json.gz"], "freeze")
    subjects = cast(
        dict[str, dict[str, object]],
        json.loads(gzip.decompress(read["frozen/subjects-before.json.gz"])),
    )
    equal(len(subjects), measured["subjects"], "subject roster")
    equal(
        data("frozen/frozen-status.json"),
        {
            "completed": True,
            "unchanged": True,
            "subjects": len(subjects),
        },
        "completed freeze",
    )
    a = units(read["frozen/gate-a.xml"])
    equal(a, units(read["frozen/gate-b.xml"]), "full rerun")
    equal(a, measured["units"], "unit ledger")
    equal(len(a), 1798, "complete units")
    if any(a.values()):
        raise ValueError("Failed unit construction")
    previous = cast(dict[str, object], prior["units"])
    equal(previous, {k: a[k] for k in previous}, "predecessor units")
    added = sorted(set(a) - set(previous))
    equal(added, measured["new_units"], "new unit ledger")
    equal(len(added), 38, "new unit roster")
    if not all(k.startswith("tests.test_render_record.") for k in added):
        raise ValueError("Unexpected unit scope")
    selected = {
        k: v
        for k, v in a.items()
        if any(name in k for name in ("test_render_record.", "test_assessment.", "test_render."))
    }
    equal(len(selected), 74, "wheel unit roster")
    for suffix in ("a", "b"):
        equal(units(read[f"frozen/wheel-units-{suffix}.xml"]), selected, "wheel rerun")
    staff = units(read["frozen/staff-a.xml"])
    equal(staff, units(read["frozen/staff-b.xml"]), "staff rerun")
    equal(len(staff), 4, "staff roster")
    if any(staff.values()):
        raise ValueError("Failed staff construction")
    red = units(read["red-final.xml"])
    equal(len(red), 38, "red roster")
    if any(v != ["failure"] for v in red.values()):
        raise ValueError("Missing first-red failure")

    native = cast(dict[str, object], measured["native"])
    prior_native = next(iter(cast(dict[str, object], prior["native"]).values()))
    for lane in ("source", "wheel"):
        for suffix in ("a", "b"):
            label = f"assessment-{lane}-{suffix}"
            report = data(f"frozen/{label}/report.json")
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
                    "render_policy_controls",
                )
            }
            equal(reading, native[label], "native ledger")
            equal(
                {k: v for k, v in reading.items() if k != "render_policy_controls"},
                prior_native,
                "native predecessor",
            )
            equal(
                set(cast(dict[str, object], report["render_policy_controls"])),
                {"wrong-page", "wrong-density", "wrong-width", "cropbox", "wrong-source"},
                "native policy controls",
            )
            equal(sha(read[f"frozen/{label}/snapshot.pdf"]), report["source_sha256"], "source")
            equal(report["accepted_project_delivered"], False, "no full project")
            equal(report["composition_fidelity_verified"], False, "no fidelity verdict")
            rows = cast(list[dict[str, object]], report["records"])
            equal(len(rows), 7, "native roster")
            for ordinal, row in enumerate(rows, 1):
                equal(row["id"], f"occ-{ordinal:06d}", "native occurrence")
                rendered = cast(dict[str, object], row["render"])
                command = cast(list[str], rendered["command"])
                equal(Path(command[0]).name, "pdftocairo", "native renderer")
                equal(
                    command[1:],
                    [
                        "-f",
                        str(ordinal),
                        "-l",
                        str(ordinal),
                        "-singlefile",
                        "-r",
                        "300",
                        "-W",
                        "1200",
                        "-H",
                        "900",
                        "-png",
                        "-antialias",
                        "default",
                        "<ARTIFACTS>/snapshot.pdf",
                        "<PRIVATE_PREFIX>",
                    ],
                    "native MediaBox policy",
                )
                reasons = cast(list[dict[str, object]], row["triage_reasons"])
                ids = [r["id"] for r in reasons]
                if not {"orientation-unverified", "import-fidelity"} <= set(ids):
                    raise ValueError("Missing native limitations")
                equal(len(set(ids)), len(ids), "unique native reasons")
                for reason in reasons:
                    equal(
                        reason["allowed_decisions"],
                        ["reject", "retain-unresolved"]
                        if reason["id"] == "skew-nonzero"
                        else ["retain-unresolved"],
                        "native Q1 domain",
                    )
                    equal(reason["disposition"], "baseline-retained/unresolved", "initial state")
                for field in ("inspected", "estimate_applied", "composition_fidelity_verified"):
                    equal(row[field], False, "no acceptance")

    for suffix in ("a", "b"):
        report = data(f"frozen/preparation-{suffix}/report.json")
        directory = cast(str, report["artifacts"])
        faults: list[object] = []
        observed = cast(dict[str, object], report["fault_checks"])
        for row in cast(list[dict[str, object]], observed["observed_signal_and_kill_cases"]):
            barrier = cast(dict[str, object], row["observed_barrier"])
            equal(row["pid"], barrier["pid"], "actual writer PID")
            equal(row["writer_reaped"], True, "writer reaped")
            equal(row["source_unchanged"], True, "source preserved")
            entry = {k: v for k, v in row.items() if k != "pid"}
            entry["observed_barrier"] = {k: v for k, v in barrier.items() if k != "pid"}
            faults.append(normalize(entry, directory))
        prepared = {"cases": normalize(report["cases"], directory), "faults": faults}
        equal(prepared, measured["preparation"], "preparation ledger")
        equal(prepared, prior["preparation"], "preparation predecessor")

    for name, raw in read.items():
        if name.startswith("measured/"):
            path = "/Users/antony/Development/BookScanBuilder/" + name.removeprefix("measured/")
            equal(sha(raw), subjects[path]["sha256"], "retained measured bytes")
    with zipfile.ZipFile(
        io.BytesIO(read["wheel/bookscan_builder-0.1.0-py3-none-any.whl"])
    ) as wheel:
        names = [n for n in wheel.namelist() if n.startswith("bookscan/")]
        equal(sorted(names), measured["wheel_product_members"], "wheel roster")
        for name in names:
            equal(wheel.read(name), read["measured/src/" + name], "wheel product bytes")
    mutation = units(read["controls/policy/units.xml"])
    equal(len(mutation), 38, "mutation roster")
    failed = {k for k, tags in mutation.items() if tags == ["failure"]}
    equal(sorted(failed), data("controls/result.json")["failed"], "mutation ledger")
    suffixes = {k.split("[")[-1].rstrip("]") for k in failed}
    equal(
        suffixes,
        {
            "renderer",
            "first-page",
            "last-page",
            "density",
            "crop-width",
            "height",
            "crop-option",
            "hide-annotations",
            "scale-to",
            "antialias",
            "format",
            "source",
            "float-page",
            "True",
        },
        "isolated policy failures",
    )
    if any(tags not in ([], ["failure"]) for tags in mutation.values()):
        raise ValueError("Unexpected mutation outcome")
    return {
        "verified": True,
        "units": len(a),
        "new_units": len(added),
        "subjects": len(subjects),
        "entries": len(read),
        "public_delivery": False,
    }


def load(directory: Path) -> dict[str, bytes]:
    index = json.loads(gzip.decompress((directory / "index.json.gz").read_bytes()))
    pieces: list[bytes] = []
    for item in index["parts"]:
        raw = (directory / item["name"]).read_bytes()
        equal(sha(raw), item["sha256"], "archive part")
        pieces.append(raw)
    with zipfile.ZipFile(io.BytesIO(b"".join(pieces))) as archive:
        equal(sorted(archive.namelist()), sorted(index["entries"]), "archive roster")
        result = {name: archive.read(name) for name in archive.namelist()}
    for name, raw in result.items():
        equal(sha(raw), index["entries"][name], "archive entry")
    return result


if __name__ == "__main__":
    print(json.dumps(verify(load(Path(__file__).parent)), sort_keys=True))
