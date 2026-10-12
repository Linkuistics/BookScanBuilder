"""Coherent evidence repacks must still refuse invented claims and lost disproof."""

import copy
import gzip
import hashlib
import io
import json
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from verify import load, verify


def pack(read: dict[str, bytes], destination: Path) -> None:
    blobs = {hashlib.sha256(raw).hexdigest(): raw for raw in read.values()}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for digest, raw in sorted(blobs.items()):
            archive.writestr("blobs/" + digest, raw)
    raw = buffer.getvalue()
    parts: list[dict[str, object]] = []
    for ordinal, start in enumerate(range(0, len(raw), 900_000)):
        chunk = raw[start : start + 900_000]
        name = f"raw-{ordinal:03}.zippart"
        (destination / name).write_bytes(chunk)
        parts.append(
            {"name": name, "size": len(chunk), "sha256": hashlib.sha256(chunk).hexdigest()}
        )
    index = {
        "format": "BookScanBuilderNativeBlobEvidence",
        "version": 1,
        "parts": parts,
        "entries": {
            name: {"sha256": hashlib.sha256(value).hexdigest(), "size": len(value)}
            for name, value in sorted(read.items())
        },
    }
    (destination / "index.json.gz").write_bytes(
        gzip.compress(json.dumps(index, sort_keys=True).encode(), mtime=0)
    )


def main() -> None:
    directory = Path(__file__).parent
    original = load(directory)
    outcomes: list[dict[str, object]] = []
    for label in ("false-delivery", "removed-disproof", "wrong-blob-length"):
        read = copy.deepcopy(original)
        if label == "false-delivery":
            measured = json.loads(read["frozen/measurement.json"])
            measured["public_finite_delivery"] = True
            read["frozen/measurement.json"] = json.dumps(measured).encode()
        elif label == "removed-disproof":
            rows = json.loads(read["omission-controls.json"])
            row = next(row for row in rows if row["omission"] == "cleanup")
            row["passed"].extend(row["failures"])
            row["failures"] = []
            read["omission-controls.json"] = json.dumps(rows).encode()
            tree = ET.fromstring(read["omission-cleanup.xml"])
            for test in tree.iter("testcase"):
                for child in list(test):
                    if child.tag == "failure":
                        test.remove(child)
            read["omission-cleanup.xml"] = ET.tostring(tree)
        else:
            measured = json.loads(read["frozen/measurement.json"])
            for name, facts in measured["sample"].items():
                facts["references"][0]["byte_size"] += 1
                captured = json.loads(read[f"frozen/{name}/report.json"])
                captured["references"] = facts["references"]
                read[f"frozen/{name}/report.json"] = json.dumps(captured).encode()
            read["frozen/measurement.json"] = json.dumps(measured).encode()
        with tempfile.TemporaryDirectory(prefix="bookscan-blob-evidence-control-") as temporary:
            destination = Path(temporary)
            pack(read, destination)
            try:
                verify(load(destination))
            except ValueError as error:
                outcomes.append({"control": label, "refused": str(error), "coherent_archive": True})
            else:
                raise AssertionError("Corrupted evidence passed: " + label)
    print(json.dumps(outcomes, indent=2))


if __name__ == "__main__":
    main()
