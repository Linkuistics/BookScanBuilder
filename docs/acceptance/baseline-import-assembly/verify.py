"""Verify retained assembly evidence, optionally reconstructing its construction checks.

Consistency does not attest historical execution, source fidelity or completed
finite delivery. External subjects remain identity references; inode-bound saved
projects are not relocated or consumed as compatible completed-project fixtures.
"""

import argparse
import gzip
import hashlib
import io
import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, cast


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def bundle(directory: Path) -> dict[str, bytes]:
    index = json.loads(gzip.decompress((directory / "index.json.gz").read_bytes()))
    assert index["format"] == "BookScanBuilderImportAssemblyEvidence" and index["version"] == 1
    assert index["complete_finite_handoff"] is False
    assert index["composition_fidelity_verified"] is False and len(index["limitations"]) == 4
    parts: list[bytes] = []
    for ordinal, part in enumerate(index["parts"]):
        assert part["name"] == f"raw-{ordinal:03d}.zippart"
        raw = (directory / part["name"]).read_bytes()
        assert len(raw) == part["size"] and digest(raw) == part["sha256"]
        parts.append(raw)
    raw = b"".join(parts)
    assert len(raw) == index["archive_size"] and digest(raw) == index["archive_sha256"]
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) and set(names) == set(index["entries"])
        result: dict[str, bytes] = {}
        for name in names:
            path = PurePosixPath(name)
            assert not path.is_absolute() and ".." not in path.parts
            assert path.parts[0] in {"project", "reading"}
            payload = archive.read(name)
            assert index["entries"][name] == {"sha256": digest(payload), "size": len(payload)}
            result[name] = payload
    return result


def ledger(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for case in ET.fromstring(raw).iter("testcase"):
        module, name = case.get("classname"), case.get("name")
        assert module is not None and name is not None
        key = module + "." + name
        assert key not in result
        result[key] = [child.tag for child in case if child.tag in {"failure", "error", "skipped"}]
    return result


def verify(data: dict[str, bytes]) -> dict[str, object]:
    measured = cast(dict[str, Any], json.loads(data["reading/measurement.json"]))
    assert measured["complete_finite_handoff"] is False
    units = ledger(data["reading/gate-a.xml"])
    assert units == ledger(data["reading/gate-b.xml"]) == measured["units"]
    assert not any(units.values())
    new = {k: v for k, v in units.items() if ".test_import_assembly." in k}
    assert len(new) == 17 and new == measured["new_units"]
    for suffix in ["a", "b"]:
        focused = {
            k: v
            for k, v in units.items()
            if any(
                "." + module + "." in k
                for module in ["test_import_assembly", "test_baseline_state"]
            )
        }
        assert focused == ledger(data[f"reading/assembly-{suffix}.xml"])
        installed = {
            k: v
            for k, v in units.items()
            if any(
                "." + module + "." in k
                for module in [
                    "test_import_assembly",
                    "test_baseline_state",
                    "test_finite_status",
                    "test_finite_protocol",
                ]
            )
        }
        assert installed == ledger(data[f"reading/wheel-units-{suffix}.xml"])
    before = json.loads(gzip.decompress(data["reading/subjects-before.json.gz"]))
    after = json.loads(gzip.decompress(data["reading/subjects-after.json.gz"]))
    assert before == after and len(before) == measured["subjects"]
    for name, count, token in [
        ("omit-palette-profile", 1, "packed_palette"),
        ("omit-final-verification", 2, "asset_corruption"),
    ]:
        found = ledger(data[f"reading/{name}.xml"])
        assert found == measured["controls"][name] and set(found) == set(new)
        failed = [key for key, failures in found.items() if failures]
        assert len(failed) == count and all(token in key for key in failed)
    keys = list(measured["native"])
    for name in [
        "native-a",
        "native-b",
        "pre-native-valid",
        "wheel-native-a/native",
        "wheel-native-b/native",
    ]:
        native = json.loads(data[f"reading/{name}/report.json"])
        assert {k: native[k] for k in keys} == measured["native"]
    assert measured["native"]["composition_fidelity_verified"] is False
    assert measured["native"]["public_finite_delivery"] is False
    for suffix in ["a", "b"]:
        public = json.loads(data[f"reading/wheel-native-{suffix}/result.json"])
        assert public["complete_finite_handoff"] is False
        assert public["composition_fidelity_verified"] is False
        assert public["source_loss_resume"] and public["resource_loss_resume"]
        assert public["denied_collection_control"] and public["epipe_exit"] == 5
        assert [(x["phase"], x["signal"], x["exit"]) for x in public["writer_observations"]] == [
            (phase, signal, code)
            for phase in ["before", "after"]
            for signal, code in [("SIGINT", 130), ("SIGTERM", 143), ("SIGKILL", -9)]
        ]
        assert all(x["owner_pid"] == x["observed_pid"] for x in public["writer_observations"])
    assert ledger(data["reading/staff-a.xml"]) == ledger(data["reading/staff-b.xml"])
    assert (
        ledger(data["reading/prepare-a/fault-checks.xml"])
        == ledger(data["reading/prepare-b/fault-checks.xml"])
        == measured["preparation_writer"]
    )
    with zipfile.ZipFile(io.BytesIO(data["reading/wheel.whl"])) as wheel:
        members = {
            name: digest(wheel.read(name))
            for name in wheel.namelist()
            if name.startswith("bookscan/")
        }
        assert members == measured["package_members"]
        assert all(digest(data["project/src/" + name]) == sha for name, sha in members.items())
    return {
        "checks": len(units),
        "new_checks": len(new),
        "subjects": len(before),
        "complete_finite_handoff": False,
        "composition_fidelity_verified": False,
    }


def reconstruct(data: dict[str, bytes]) -> None:
    expected = ledger(data["reading/gate-a.xml"])
    expected = {k: v for k, v in expected.items() if ".test_import_assembly." in k}
    with tempfile.TemporaryDirectory(prefix="bookscan-assembly-evidence-") as temporary:
        root = Path(temporary).resolve()
        for name, raw in data.items():
            if name.startswith("project/"):
                path = root / name.removeprefix("project/")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
        xml = root / "construction.xml"
        environment = dict(os.environ, PYTEST_ADDOPTS="--junitxml=" + str(xml))
        result = subprocess.run(
            [
                "uv",
                "run",
                "--locked",
                "pytest",
                "--rootdir=" + str(root),
                "-q",
                "tests/test_import_assembly.py",
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert ledger(xml.read_bytes()) == expected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--reconstruct", action="store_true")
    args = parser.parse_args()
    data = bundle(args.directory)
    result = verify(data)
    if args.reconstruct:
        reconstruct(data)
        result["reconstructed_checks"] = 17
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
