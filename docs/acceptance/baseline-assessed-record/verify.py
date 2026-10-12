"""Reconstruct frozen occurrence-reader evidence without native tools or product imports.

This checks archive bytes, itemwise ledgers, package identity and saved byte
closure. It does not replay historical execution or establish source fidelity.
"""

import argparse
import gzip
import hashlib
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify(directory: Path) -> dict[str, int]:
    index: dict[str, Any] = json.loads(gzip.decompress((directory / "index.json.gz").read_bytes()))
    assert index["format"] == "BookScanBuilderAssessedEvidence" and index["version"] == 1
    parts: list[bytes] = []
    for item in index["parts"]:
        assert Path(item["name"]).name == item["name"]
        raw = (directory / item["name"]).read_bytes()
        assert len(raw) == item["size"] and sha(raw) == item["sha256"]
        parts.append(raw)
    archive = b"".join(parts)
    assert sha(archive) == index["archive_sha256"]
    entries = index["entries"]
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        expected = {"blobs/" + item["sha256"] for item in entries.values()}
        assert len(zipped.namelist()) == len(expected) == index["payload_count"]
        assert set(zipped.namelist()) == expected
        payloads = {name.removeprefix("blobs/"): zipped.read(name) for name in expected}
    assert all(sha(raw) == digest for digest, raw in payloads.items())
    for item in entries.values():
        assert len(payloads[item["sha256"]]) == item["size"]

    def read(name: str) -> bytes:
        return payloads[entries[name]["sha256"]]

    def data(name: str) -> Any:
        return json.loads(read(name))

    def units(name: str) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for test in ET.fromstring(read(name)).iter("testcase"):
            key = test.attrib["classname"] + "." + test.attrib["name"]
            assert key not in result
            result[key] = [c.tag for c in test if c.tag in {"failure", "error", "skipped"}]
        return result

    measurement = data("final/measurement.json")
    before = json.loads(gzip.decompress(read("final/subjects-before.json.gz")))
    after = json.loads(gzip.decompress(read("final/subjects-after.json.gz")))
    assert before == after and len(before) == measurement["subjects"]
    assert data("final/frozen-status.json") == {
        "unchanged": True,
        "completed": True,
        "subjects": len(before),
    }
    assert measurement["public_finite_delivery"] is False
    a, b = units("final/gate-a.xml"), units("final/gate-b.xml")
    assert a == b == measurement["units"] and len(a) == 2351 and not any(a.values())
    prior = data("prior/measurement.json")
    assert {key: a[key] for key in prior["units"]} == prior["units"]
    assert len(prior["units"]) == 2284
    new = sorted(set(a) - set(prior["units"]))
    assert new == measurement["new_units"] and len(new) == 67
    selected = {key: value for key, value in a.items() if "test_assessed_record." in key}
    assert units("final/wheel-units-a.xml") == units("final/wheel-units-b.xml") == selected
    assert units("final/staff-a.xml") == units("final/staff-b.xml")
    assert not any(units("final/staff-a.xml").values())
    red = units("instrument/red.xml")
    assert len(red) == 35 and all(value == ["failure"] for value in red.values())
    omissions = data("instrument/omissions.json")
    for name, count in (("placement", 4), ("triage", 8)):
        ledger = units("instrument/" + name + "-omission.xml")
        failed = [key.rsplit(".", 1)[-1] for key, value in ledger.items() if value]
        assert sorted(failed) == sorted(omissions[name]["failed"]) and len(failed) == count
        assert len(ledger) == 67 and sum(not value for value in ledger.values()) == 67 - count
    with zipfile.ZipFile(
        io.BytesIO(read("wheel/bookscan_builder-0.1.0-py3-none-any.whl"))
    ) as wheel:
        package = measurement["package_members"]
        assert set(package) == {name for name in wheel.namelist() if name.startswith("bookscan/")}
        for name, digest in package.items():
            assert digest == sha(wheel.read(name)) == sha(read("repo/src/" + name))
            assert digest == sha(read("installed/" + name))
    for lane in ("source", "wheel"):
        for suffix in ("a", "b"):
            label = "assessed-" + lane + "-" + suffix
            report = data("final/" + label + "/report.json")
            assert report == measurement["assessed"][label]
            assert report == next(iter(measurement["assessed"].values()))
            assert len(report["records"]) == 7 and len(report["controls"]) == 28
            assert report["source_loss_resume"] is True and report["checkpoint_revision"] == 2
            assert report["accepted_project_delivered"] is False
            assert report["composition_fidelity_verified"] is False
            prefix = "final/" + label + "/project/"
            source = sha(read(prefix + "source.pdf"))
            for record, reference in zip(
                report["records"], report["baseline_references"], strict=True
            ):
                assert record["source_sha256"] == source
                assert record["inspected"] is False and record["estimate_applied"] is False
                assert record["composition_fidelity_verified"] is False
                assert record["composition_unavailable"]
                png = read(prefix + "assets/" + reference["id"] + ".png")
                assert sha(png) == reference["png_sha256"] and len(png) == reference["png_size"]
                assert reference["rgb_sha256"] == record["rgb_sha256"]
            for digest, size in report["native_blobs"].items():
                raw = read(prefix + "native-blobs/" + digest + ".bin")
                assert sha(raw) == digest and len(raw) == size
    for suffix in ("a", "b"):
        report = data("final/writer-" + suffix + "/report.json")
        assert len(report["cases"]) == 40
        for row in report["cases"]:
            event = data("final/writer-" + suffix + "/" + row["id"] + ".json")["event"]
            assert row["writer_pid"] == event["writer_pid"]
            assert event["native_directory"] == event["header"]["native_blobs"]
    return {
        "entries": len(entries),
        "payloads": len(payloads),
        "subjects": len(before),
        "unit_outcomes": len(a),
        "new_outcomes": len(new),
        "native_pages": 7,
        "native_controls": 28,
        "omission_failures": 12,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory), sort_keys=True))


if __name__ == "__main__":
    main()
