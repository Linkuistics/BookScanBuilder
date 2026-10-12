"""Reconstruct retained dependency consistency; historical execution is not attested."""

import argparse
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
from typing import cast


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def ledger(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in ET.fromstring(raw).iter("testcase"):
        key = item.attrib["classname"] + "." + item.attrib["name"]
        assert key not in result
        result[key] = [child.tag for child in item if child.tag in ("failure", "error", "skipped")]
    return result


def verify(directory: Path) -> dict[str, object]:
    index = json.loads((directory / "index.json").read_bytes())
    chunks: list[bytes] = []
    for part in index["parts"]:
        assert Path(part["name"]).name == part["name"]
        data = (directory / part["name"]).read_bytes()
        assert digest(data) == part["sha256"]
        chunks.append(data)
    raw = b"".join(chunks)
    assert index["format"] == "BookScanBuilderDependencyEvidence" and index["version"] == 1
    assert index["public_finite_delivery"] is False
    assert index["external_subject_bytes_retained"] is False
    assert index["limitation"] == (
        "Offline consistency reconstruction does not attest historical execution "
        "or source composition fidelity."
    )
    assert digest(raw) == index["archive_sha256"]
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for entry in archive:
            assert entry.isfile() and entry.name not in files
            assert not Path(entry.name).is_absolute() and ".." not in Path(entry.name).parts
            stream = archive.extractfile(entry)
            assert stream is not None
            files[entry.name] = stream.read()
    assert {name: digest(data) for name, data in files.items()} == index["files"]
    measurement = json.loads(files["measurement/measurement.json"])
    assert measurement["public_finite_delivery"] is False
    a = ledger(files["measurement/gate-a.xml"])
    assert a == ledger(files["measurement/gate-b.xml"]) == measurement["units"]
    assert len(a) == 2413 and not any(a.values())
    selected = {key: value for key, value in a.items() if "test_dependency_record." in key}
    assert len(selected) == 62 and sorted(selected) == measurement["new_units"]
    assert selected == ledger(files["measurement/wheel-units-a.xml"])
    assert selected == ledger(files["measurement/wheel-units-b.xml"])
    assert ledger(files["measurement/staff-a.xml"]) == ledger(files["measurement/staff-b.xml"])
    before = json.loads(gzip.decompress(files["measurement/subjects-before.json.gz"]))
    assert before == json.loads(gzip.decompress(files["measurement/subjects-after.json.gz"]))
    assert len(before) == measurement["subjects"] == 19566
    assert json.loads(files["measurement/frozen-status.json"])["completed"] is True
    for name, data in files.items():
        if name.startswith("subject/"):
            path = "/Users/antony/Development/BookScanBuilder/" + name.removeprefix("subject/")
            assert before[path]["sha256"] == digest(data)
    omissions = json.loads(files["instrument/omissions.json"])
    for kind, expected_count in (("build", 2), ("graph", 6)):
        outcomes = ledger(files["instrument/omission-" + kind + ".xml"])
        failed = sorted(key.rsplit(".", 1)[1] for key, value in outcomes.items() if value)
        assert failed == omissions[kind]["failed"] and len(failed) == expected_count
        assert omissions[kind]["product_unchanged"] is True
        assert omissions[kind]["copied_source_sha256"] == digest(files["omission/" + kind + ".py"])
        assert len(outcomes) == 62
    wheel_bytes = files["instrument/wheel/bookscan_builder-0.1.0-py3-none-any.whl"]
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as wheel:
        members = {
            name: digest(wheel.read(name))
            for name in wheel.namelist()
            if name.startswith("bookscan/")
        }
        assert members == measurement["package_members"]
        assert (
            wheel.read("bookscan/dependency_record.py")
            == files["subject/src/bookscan/dependency_record.py"]
        )
        with tempfile.TemporaryDirectory(prefix="bookscan-retained-dependency-") as temporary:
            target = Path(temporary)
            for name in members:
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(wheel.read(name))
            script = (
                "import json,sys; from dataclasses import asdict; "
                "from bookscan import dependency_record; "
                "d=json.load(sys.stdin); "
                "actual=asdict(dependency_record.restore(d['preflight'],d['binding'])); "
                "assert json.loads(json.dumps(actual,default=str))==d['checked']; "
                "assert d['accepted_project_delivered'] is False; "
                "assert d['composition_fidelity_verified'] is False; "
                "assert d['limitation']=='Historical metadata consistency; "
                "complete checkpoint association remains live.'; "
                "assert len(d['controls'])==6"
            )
            for label in ("native-source-a", "native-source-b", "native-wheel-a", "native-wheel-b"):
                subprocess.run(
                    [sys.executable, "-c", script],
                    input=files["measurement/" + label + "/report.json"],
                    cwd=target,
                    env=dict(os.environ, PYTHONPATH=str(target), PYTHONDONTWRITEBYTECODE="1"),
                    check=True,
                )
    native = cast(dict[str, object], measurement["native"])
    assert all(item == next(iter(native.values())) for item in native.values())
    return {
        "entries": len(files),
        "tests": len(a),
        "new_tests": len(selected),
        "subjects": len(before),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).parent)
    print(json.dumps(verify(parser.parse_args().directory)))


if __name__ == "__main__":
    main()
