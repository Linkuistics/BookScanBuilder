"""Reconstruct ordinary reservation evidence without temporary paths or native execution.

Checks consistency of retained records and byte identities, not historical execution
attestation, relocated project validity, public create or source-composition fidelity.
"""

import gzip
import hashlib
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import cast


def obj(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def ledger(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in ET.fromstring(raw).iter("testcase"):
        key = str(item.get("classname")) + "." + str(item.get("name"))
        assert key not in result
        result[key] = [entry.tag for entry in item if entry.tag in {"failure", "error", "skipped"}]
    return result


def process(raw: bytes) -> dict[str, object]:
    report = obj(json.loads(raw))
    observations = cast(list[dict[str, object]], report["observations"])
    for item in observations:
        barrier = obj(item["barrier"])
        assert barrier["pid"] == item["pid"]
        del item["pid"]
        del barrier["pid"]
        barrier["path"] = Path(cast(str, barrier["path"])).name
    return report


def verify(members: dict[str, bytes], root: str) -> dict[str, object]:
    before = obj(json.loads(gzip.decompress(members["run/subjects-before.json.gz"])))
    after = obj(json.loads(gzip.decompress(members["run/subjects-after.json.gz"])))
    assert before == after
    for name, raw in members.items():
        if name.startswith("repo/"):
            assert digest(raw) == obj(before[root + name.removeprefix("repo/")])["sha256"]
    measured = obj(json.loads(members["run/measurement.json"]))
    assert measured["complete_finite_handoff"] is False
    assert measured["subjects"] == len(before)
    units = ledger(members["run/gate-a.xml"])
    assert units == ledger(members["run/gate-b.xml"]) == measured["units"]
    assert not any(units.values())
    previous = ledger(members["prior/gate-a.xml"])
    assert {key: value for key, value in units.items() if key in previous} == previous
    new = {key: value for key, value in units.items() if key not in previous}
    assert new == measured["new_units"] and len(new) == 18
    assert all("test_project_reservation." in key for key in new)
    for suffix in ("a", "b"):
        assert ledger(members[f"run/reservation-{suffix}.xml"]) == new
        assert process(members[f"run/process-{suffix}/report.json"]) == measured["reservation"]
        assert (
            process(members[f"run/wheel-process-{suffix}/report.json"]) == measured["reservation"]
        )
    controls = obj(measured["controls"])
    assert set(controls) == {"omit-identity", "recursive-cleanup"}
    for name, count, tokens in [
        ("omit-identity", 4, ("canonical", "replaced_root", "replaced_parent")),
        ("recursive-cleanup", 2, ("unknown_content", "descriptor_cleanup")),
    ]:
        cases = ledger(members[f"run/{name}.xml"])
        assert controls[name] == cases
        failures = {key: value for key, value in cases.items() if value}
        assert len(failures) == count
        assert all(any(token in key for token in tokens) for key in failures)
        assert set(cases) == set(new)
    native = obj(measured["native"])
    assert (
        native["composition_fidelity_verified"] is False
        and native["public_finite_delivery"] is False
    )
    assert native["limitations"] and native["source_loss_resume"] is True
    assert native["resource_loss_resume"] is True
    for name in ("native-a", "native-b", "wheel-native-a/native", "wheel-native-b/native"):
        actual = obj(json.loads(members[f"run/{name}/report.json"]))
        assert {key: actual[key] for key in native} == native
    previous_native = obj(json.loads(members["prior/native-report.json"]))
    assert {key: previous_native[key] for key in native} == native
    with zipfile.ZipFile(
        io.BytesIO(members["run/wheel/bookscan_builder-0.1.0-py3-none-any.whl"])
    ) as wheel:
        packages = obj(measured["package_members"])
        assert {
            name: digest(wheel.read(name))
            for name in wheel.namelist()
            if name.startswith("bookscan/")
        } == packages
        for name, expected in packages.items():
            assert digest(members["repo/src/" + name]) == expected
    return {
        "units": len(units),
        "new_units": len(new),
        "subjects": len(before),
        "complete_finite_handoff": False,
    }


def read(directory: Path) -> tuple[dict[str, bytes], str]:
    index = obj(json.loads((directory / "index.json").read_bytes()))
    assert index["format"] == "BookScanBuilderReservationEvidence" and index["version"] == 1
    parts = cast(list[dict[str, object]], index["parts"])
    chunks: list[bytes] = []
    for part in parts:
        name = cast(str, part["path"])
        assert Path(name).name == name and name.endswith(".zippart")
        raw = (directory / name).read_bytes()
        assert len(raw) == part["bytes"] and digest(raw) == part["sha256"]
        chunks.append(raw)
    archive = b"".join(chunks)
    assert digest(archive) == index["archive_sha256"]
    with zipfile.ZipFile(io.BytesIO(archive)) as saved:
        assert len(saved.namelist()) == len(set(saved.namelist()))
        members = {name: saved.read(name) for name in saved.namelist()}
    inventory = obj(index["members"])
    assert set(members) == set(inventory)
    for name, raw in members.items():
        fact = obj(inventory[name])
        assert fact["sha256"] == digest(raw) and fact["bytes"] == len(raw)
    return members, cast(str, index["repository_root"])


if __name__ == "__main__":
    payloads, source_root = read(Path(__file__).parent)
    print(json.dumps(verify(payloads, source_root), sort_keys=True))
