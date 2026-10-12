"""Check retained status evidence; optionally reconstruct its twenty unit checks.

Byte/outcome consistency is not historical execution attestation or source
fidelity. Inode-bound native projects are evidence, not relocatable resume fixtures.
Usage: uv run --locked python docs/acceptance/baseline-finite-status/verify.py --reconstruct
"""

import argparse
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any


def ledger(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in ET.fromstring(raw).iter("testcase"):
        name = str(item.get("classname")) + "." + str(item.get("name"))
        assert name not in result, name
        result[name] = [child.tag for child in item if child.tag in {"failure", "error", "skipped"}]
    return result


def verify(directory: Path, *, reconstruct: bool = False) -> dict[str, object]:
    index: dict[str, Any] = json.loads((directory / "index.json").read_bytes())
    assert index["format"] == "BookScanBuilderFiniteStatusEvidence" and index["version"] == 1
    assert index["complete_finite_handoff"] is False
    raw = b"".join((directory / name).read_bytes() for name in index["parts"])
    assert hashlib.sha256(raw).hexdigest() == index["sha256"], "Archive digest mismatch"
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert set(archive.namelist()) == set(index["entries"])
        for name, expected in index["entries"].items():
            value = archive.read(name)
            assert len(value) == expected["size"], name
            assert hashlib.sha256(value).hexdigest() == expected["sha256"], name
        measured = archive.read("reading/measurement.json")
        assert gzip.decompress((directory / "verification.json.gz").read_bytes()) == measured
        report: dict[str, Any] = json.loads(measured)
        before = json.loads(gzip.decompress(archive.read("reading/subjects-before.json.gz")))
        after = json.loads(gzip.decompress(archive.read("reading/subjects-after.json.gz")))
        assert before == after and len(before) == report["subjects"]
        assert report["complete_finite_handoff"] is False
        assert report["units"] == ledger(archive.read("reading/gate-a.xml"))
        assert report["units"] == ledger(archive.read("reading/gate-b.xml"))
        assert not any(report["units"].values())
        assert len(report["new_units"]) == 20 and not any(report["new_units"].values())
        assert report["native"]["composition_fidelity_verified"] is False
        assert report["native"]["complete_finite_handoff"] is False
        assert len(report["native"]["writer_observations"]) == 6
        assert len(report["controls"]["omit-history"]["failed"]) == 1
        assert len(report["controls"]["ignore-signal"]["failed"]) == 3
        for name, control in report["controls"].items():
            observed = ledger(archive.read("reading/" + name + ".xml"))
            assert {key: value for key, value in observed.items() if value} == control["failed"]
            assert sorted(key for key, value in observed.items() if not value) == sorted(
                control["passed"]
            )
        with zipfile.ZipFile(
            io.BytesIO(archive.read("wheel/bookscan_builder-0.1.0-py3-none-any.whl"))
        ) as wheel:
            for name, digest in report["package_members"].items():
                assert hashlib.sha256(wheel.read(name)).hexdigest() == digest
                assert hashlib.sha256(archive.read("source/src/" + name)).hexdigest() == digest
        if reconstruct:
            with tempfile.TemporaryDirectory(prefix="bookscan-status-evidence-") as temporary:
                # pytest canonicalizes cwd; rootdir must name that same physical
                # directory when macOS /var is a symlink to /private/var.
                root = Path(temporary).resolve()
                for name in archive.namelist():
                    if not name.startswith("source/"):
                        continue
                    relative = Path(name.removeprefix("source/"))
                    assert not relative.is_absolute() and ".." not in relative.parts
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(archive.read(name))
                environment = dict(os.environ, PYTHONPATH=str(root / "src"))
                xml = root / "reconstruction.xml"
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-q",
                        "--rootdir",
                        str(root),
                        "--junitxml=" + str(xml),
                        "tests/test_finite_status.py",
                    ],
                    cwd=root,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                assert result.returncode == 0, result.stdout + result.stderr
                assert ledger(xml.read_bytes()) == report["new_units"]
    return {
        "entries": len(index["entries"]),
        "unit_outcomes": len(report["units"]),
        "reconstructed": reconstruct,
        "complete_finite_handoff": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--reconstruct", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, reconstruct=args.reconstruct), sort_keys=True))


if __name__ == "__main__":
    main()
