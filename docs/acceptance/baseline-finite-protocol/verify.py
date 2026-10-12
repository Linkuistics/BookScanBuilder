"""Reconstruct retained Q2 evidence; no original input/native/project I/O."""

import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def ledger(raw: bytes) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for item in ET.fromstring(raw).iter("testcase"):
        key = item.attrib["classname"] + "." + item.attrib["name"]
        assert key not in rows
        rows[key] = [child.tag for child in item if child.tag in ("failure", "error", "skipped")]
    return rows


def verify(directory: Path, *, reconstruct: bool = True) -> dict[str, int]:
    index = json.loads((directory / "index.json").read_bytes())
    assert index["format"] == "BookScanBuilderFiniteProtocolEvidence" and index["version"] == 1
    assert index["complete_finite_handoff"] is False
    assert index["external_subject_bytes_retained"] is False
    assert index["limitation"] == (
        "Invocation grammar evidence is not completed finite review/export or source fidelity."
    )
    parts: list[bytes] = []
    for part in index["parts"]:
        assert Path(part["name"]).name == part["name"]
        value = (directory / part["name"]).read_bytes()
        assert sha(value) == part["sha256"]
        parts.append(value)
    raw = b"".join(parts)
    assert sha(raw) == index["archive_sha256"]
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive:
            assert member.isfile() and member.name not in files
            assert not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
            stream = archive.extractfile(member)
            assert stream is not None
            files[member.name] = stream.read()
    assert {name: sha(data) for name, data in files.items()} == index["files"]
    measured = json.loads(files["measurement/measurement.json"])
    assert measured["complete_finite_handoff"] is False
    units = ledger(files["measurement/gate-a.xml"])
    assert units == ledger(files["measurement/gate-b.xml"]) == measured["units"]
    assert len(units) == 2525 and not any(units.values())
    old = json.loads(files["measurement/predecessor-units.json"])
    assert {key: value for key, value in units.items() if key in old} == old and len(old) == 2464
    new = {key: value for key, value in units.items() if ".test_finite_protocol." in key}
    assert new == measured["new_units"] and len(new) == 61
    for kind in ("protocol-units", "wheel-units"):
        for letter in ("a", "b"):
            assert new == ledger(files[f"measurement/{kind}-{letter}.xml"])
    assert ledger(files["measurement/staff-a.xml"]) == ledger(files["measurement/staff-b.xml"])
    assert (
        ledger(files["measurement/prepare-a/fault-checks.xml"])
        == ledger(files["measurement/prepare-b/fault-checks.xml"])
        == measured["preparation_writer"]
    )
    before = json.loads(gzip.decompress(files["measurement/subjects-before.json.gz"]))
    assert before == json.loads(gzip.decompress(files["measurement/subjects-after.json.gz"]))
    assert len(before) == measured["subjects"]
    for kind, failed, passed in (
        ("all-token-flags", 5, 5),
        ("invented-route", 5, 7),
        ("old-entry", 60, 1),
    ):
        rows = ledger(files[f"controls/{kind}.xml"])
        assert sum(bool(value) for value in rows.values()) == failed
        assert sum(not value for value in rows.values()) == passed
    for kind in ("source-public", "wheel-public"):
        for letter in ("a", "b"):
            public = json.loads(files[f"measurement/{kind}-{letter}/result.json"])
            assert {key: value for key, value in public.items() if key != "executable"} == measured[
                "public"
            ]
    assert len(measured["public"]["cases"]) == 22
    assert measured["public"]["epipe"] == {"help": 5, "selected_error": 2}
    assert measured["public"]["denied_read_control"] is True
    assert measured["public"]["complete_finite_handoff"] is False
    for name, case in measured["public"]["cases"].items():
        if name.startswith("help."):
            assert case["exit"] == 0 and case["stderr"] == ""
            assert "not yet available" in case["stdout"]
            assert "one image pixel per framebuffer pixel" in case["stdout"]
            assert "Fresh import loses old review facts" in case["stdout"]
        elif "record" in case:
            assert case["exit"] == case["record"]["exit_code"] == 2
            assert case["record"]["schema"] == "BookScanBuilderCommandResult"
            assert case["record"]["committed"] is False
    with zipfile.ZipFile(io.BytesIO(files["wheel.whl"])) as wheel:
        package = {
            name: sha(wheel.read(name)) for name in wheel.namelist() if name.startswith("bookscan/")
        }
        assert package == measured["package_members"]
        assert all(sha(files["src/" + name]) == digest for name, digest in package.items())
    if reconstruct:
        with tempfile.TemporaryDirectory(prefix="bookscan-retained-protocol-") as temp:
            root = Path(temp)
            for name, data in files.items():
                if name.startswith(("src/", "tests/")):
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
            env = dict(os.environ, PYTHONPATH=str(root / "src"))
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    str(root / "tests/test_finite_protocol.py"),
                    "--rootdir=" + str(root),
                    "--junitxml=" + str(root / "reconstruction.xml"),
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            assert ledger((root / "reconstruction.xml").read_bytes()) == new
    return {
        "entries": len(files),
        "units": len(units),
        "new_units": len(new),
        "subjects": len(before),
    }


if __name__ == "__main__":
    print(json.dumps(verify(Path(__file__).parent), sort_keys=True))
