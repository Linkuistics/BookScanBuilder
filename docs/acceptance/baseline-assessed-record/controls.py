"""Observe the offline reader refusing coherently rehashed false evidence."""

import copy
import gzip
import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from verify import verify


def run(directory: Path) -> list[str]:
    original: dict[str, Any] = json.loads(
        gzip.decompress((directory / "index.json.gz").read_bytes())
    )
    raw = b"".join((directory / p["name"]).read_bytes() for p in original["parts"])
    with zipfile.ZipFile(io.BytesIO(raw)) as zipped:
        payloads = {name.removeprefix("blobs/"): zipped.read(name) for name in zipped.namelist()}
    refused: list[str] = []
    for fault in ("delivery", "removed-disproof", "native-length", "missing-oracle"):
        index, blobs = copy.deepcopy(original), dict(payloads)

        def get(name: str) -> Any:
            return json.loads(blobs[index["entries"][name]["sha256"]])

        def put(name: str, value: object) -> None:
            value_raw = json.dumps(value, sort_keys=True).encode()
            digest = hashlib.sha256(value_raw).hexdigest()
            blobs[digest] = value_raw
            index["entries"][name] = {"sha256": digest, "size": len(value_raw)}

        measurement = get("final/measurement.json")
        if fault == "delivery":
            measurement["public_finite_delivery"] = True
        elif fault == "removed-disproof":
            omissions = get("instrument/omissions.json")
            omissions["placement"]["failed"].pop()
            put("instrument/omissions.json", omissions)
        else:
            for lane in ("source", "wheel"):
                for suffix in ("a", "b"):
                    label = "assessed-" + lane + "-" + suffix
                    report = get("final/" + label + "/report.json")
                    if fault == "native-length":
                        key = next(iter(report["native_blobs"]))
                        report["native_blobs"][key] += 1
                    else:
                        report["records"][0]["composition_unavailable"] = ""
                    measurement["assessed"][label] = report
                    put("final/" + label + "/report.json", report)
        put("final/measurement.json", measurement)
        buffer = io.BytesIO()
        used = {entry["sha256"] for entry in index["entries"].values()}
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
            for digest in sorted(used):
                zipped.writestr("blobs/" + digest, blobs[digest])
        archive = buffer.getvalue()
        index["archive_sha256"] = hashlib.sha256(archive).hexdigest()
        index["payload_count"] = len(used)
        index["parts"] = [
            {
                "name": "changed.zip",
                "size": len(archive),
                "sha256": hashlib.sha256(archive).hexdigest(),
            }
        ]
        with tempfile.TemporaryDirectory(prefix="bookscan-assessed-evidence-") as temporary:
            scratch = Path(temporary)
            (scratch / "changed.zip").write_bytes(archive)
            (scratch / "index.json.gz").write_bytes(gzip.compress(json.dumps(index).encode()))
            try:
                verify(scratch)
            except AssertionError:
                refused.append(fault)
            else:
                raise AssertionError("False evidence accepted: " + fault)
    assert len(refused) == 4
    return refused


if __name__ == "__main__":
    print(json.dumps({"refused": run(Path(__file__).parent)}, sort_keys=True))
