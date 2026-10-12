"""Repack coherent evidence mutations, then require independent semantic refusal."""

import copy
import gzip
import io
import json
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import cast

from verify import equal, load, sha, verify


def store(directory: Path, read: dict[str, bytes]) -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(read.items()):
            archive.writestr(name, raw)
    raw = stream.getvalue()
    parts: list[dict[str, object]] = []
    for ordinal, offset in enumerate(range(0, len(raw), 900_000)):
        name = f"raw-{ordinal:03d}.zippart"
        chunk = raw[offset : offset + 900_000]
        (directory / name).write_bytes(chunk)
        parts.append({"name": name, "sha256": sha(chunk), "size": len(chunk)})
    index = {"parts": parts, "entries": {n: sha(v) for n, v in read.items()}}
    (directory / "index.json.gz").write_bytes(gzip.compress(json.dumps(index).encode()))


def control(directory: Path, read: dict[str, bytes], expected: str) -> str:
    store(directory, read)
    restored = load(directory)  # All archive/entry identities are deliberately coherent.
    equal(restored, read, "coherent repack")
    try:
        verify(restored)
    except ValueError as error:
        equal(str(error), expected, "named semantic refusal")
        return str(error)
    raise ValueError("Wrong evidence was accepted")


def run() -> dict[str, object]:
    read = load(Path(__file__).parent)
    result: dict[str, object] = {"baseline": verify(read)}
    wrong = copy.deepcopy(read)
    measured = json.loads(wrong["frozen/measurement.json"])
    prior = json.loads(wrong["prior-measurement.json"])
    for lane in ("source", "wheel"):
        for suffix in ("a", "b"):
            label = f"assessment-{lane}-{suffix}"
            name = f"frozen/{label}/report.json"
            report = json.loads(wrong[name])
            # Change every corresponding ledger so agreement alone cannot reject it.
            for record in (
                report["records"][0],
                measured["native"][label]["records"][0],
                prior["native"][label]["records"][0],
            ):
                record["triage_reasons"] = [
                    reason
                    for reason in record["triage_reasons"]
                    if reason["id"] != "orientation-unverified"
                ]
            wrong[name] = json.dumps(report).encode()
    wrong["frozen/measurement.json"] = json.dumps(measured).encode()
    wrong["prior-measurement.json"] = json.dumps(prior).encode()
    with tempfile.TemporaryDirectory(prefix="triage-evidence-native-") as name:
        result["missing-orientation"] = control(Path(name), wrong, "Missing native limitations")
    wrong = copy.deepcopy(read)
    name = "controls/domain/units.xml"
    document = ET.fromstring(wrong[name])
    removed = False
    for row in document.iter("testcase"):
        if row.attrib["name"].endswith("[fidelity-reject]"):
            row.remove(cast(ET.Element, row.find("failure")))
            removed = True
    equal(removed, True, "fault subject found")
    wrong[name] = ET.tostring(document)
    with tempfile.TemporaryDirectory(prefix="triage-evidence-mutation-") as name:
        result["missing-domain-disproof"] = control(Path(name), wrong, "isolated mutation failures")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
