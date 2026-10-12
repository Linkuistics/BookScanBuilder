"""Repack coherent wrong observations; semantic checks must refuse each corpus."""

import gzip
import io
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import cast

from verify import equal, run, sha

HERE = Path(__file__).resolve().parent


def main() -> dict[str, object]:
    index = cast(
        dict[str, object], json.loads(gzip.decompress((HERE / "index.json.gz").read_bytes()))
    )
    subjects = [Path(__file__), HERE / "verify.py", HERE / "index.json.gz"]
    subjects.extend(HERE / str(p["name"]) for p in cast(list[dict[str, object]], index["parts"]))
    before = {str(p): sha(p.read_bytes()) for p in subjects}
    run(HERE)
    encoded = b"".join(
        (HERE / str(p["name"])).read_bytes() for p in cast(list[dict[str, object]], index["parts"])
    )
    with zipfile.ZipFile(io.BytesIO(encoded)) as archive:
        entries = cast(dict[str, dict[str, object]], index["entries"])
        good = {
            name: archive.read("blobs/" + str(item["sha256"])) for name, item in entries.items()
        }
    root = Path(tempfile.mkdtemp(prefix="bookscan-analysis-controls-"))
    results: dict[str, object] = {}
    for fault in ("wrong-unit", "wrong-region", "wrong-availability"):
        wrong = dict(good)
        measured = cast(dict[str, object], json.loads(wrong["frozen/measurement.json"]))
        if fault == "wrong-unit":
            unit = next(
                k for k in cast(list[str], measured["new_units"]) if "test_analysis_record" in k
            )
            cast(dict[str, object], measured["units"])[unit] = ["failure"]
            for name in ("gate-a", "gate-b", "wheel-units-a", "wheel-units-b"):
                key = "frozen/" + name + ".xml"
                tree = ET.fromstring(wrong[key])
                row = next(
                    item
                    for item in tree.iter("testcase")
                    if item.attrib["classname"] + "." + item.attrib["name"] == unit
                )
                ET.SubElement(row, "failure").text = "coherent deliberate failure"
                wrong[key] = ET.tostring(tree)
        else:
            for lane in ("source", "wheel"):
                for suffix in ("a", "b"):
                    label = "assessment-" + lane + "-" + suffix
                    key = "frozen/" + label + "/report.json"
                    report = cast(dict[str, object], json.loads(wrong[key]))
                    rows = cast(list[dict[str, object]], report["records"])
                    if fault == "wrong-region":
                        cast(dict[str, object], rows[0]["analysis"])["regions"] = [
                            [0, 0, 1199, 900]
                        ]
                    else:
                        cast(dict[str, object], rows[4]["analysis"])["available"] = True
                    wrong[key] = json.dumps(report).encode()
                    native = cast(dict[str, dict[str, object]], measured["native"])
                    native[label]["records"] = rows
        wrong["frozen/measurement.json"] = json.dumps(measured).encode()
        target = root / fault
        target.mkdir()
        (target / "verify.py").write_bytes((HERE / "verify.py").read_bytes())
        buffer = io.BytesIO()
        blobs = {sha(raw): raw for raw in wrong.values()}
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for digest, raw in sorted(blobs.items()):
                archive.writestr("blobs/" + digest, raw)
        raw = buffer.getvalue()
        parts: list[dict[str, object]] = []
        for offset in range(0, len(raw), 900_000):
            chunk = raw[offset : offset + 900_000]
            name = f"raw-{offset // 900_000:03d}.zippart"
            (target / name).write_bytes(chunk)
            parts.append({"name": name, "size": len(chunk), "sha256": sha(chunk)})
        changed = {
            **index,
            "parts": parts,
            "archive_size": len(raw),
            "archive_sha256": sha(raw),
            "entries": {n: {"size": len(v), "sha256": sha(v)} for n, v in wrong.items()},
        }
        (target / "index.json.gz").write_bytes(gzip.compress(json.dumps(changed).encode(), mtime=0))
        reading = subprocess.run(
            [sys.executable, str(target / "verify.py")], capture_output=True, text=True, check=False
        )
        equal(reading.returncode, 1)
        if "ValueError:" not in reading.stderr or "BadZipFile" in reading.stderr:
            raise ValueError("Control failed archive transport rather than semantic verification")
        results[fault] = {
            "exit_code": reading.returncode,
            "stdout": reading.stdout,
            "stderr": reading.stderr,
            "archive_sha256": sha(raw),
        }
    equal(before, {str(p): sha(p.read_bytes()) for p in subjects})
    return {"refused": results, "subjects_unchanged": True}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
