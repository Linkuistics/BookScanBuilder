"""Digest-valid repacks must not invent delivery, omit disproof or alter native meaning."""

import gzip
import io
import json
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from verify import load, sha, verify


def pack(directory: Path, entries: dict[str, bytes]) -> None:
    blobs = {sha(raw): raw for raw in entries.values()}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for digest, raw in sorted(blobs.items()):
            archive.writestr("blobs/" + digest, raw)
    raw = stream.getvalue()
    parts: list[dict[str, object]] = []
    for number, start in enumerate(range(0, len(raw), 900_000)):
        chunk = raw[start : start + 900_000]
        name = f"raw-{number:03}.zippart"
        (directory / name).write_bytes(chunk)
        parts.append({"name": name, "size": len(chunk), "sha256": sha(chunk)})
    index = {
        "format": "BookScanBuilderNativeHeaderEvidence",
        "version": 1,
        "parts": parts,
        "entries": {
            name: {"sha256": sha(value), "size": len(value)} for name, value in entries.items()
        },
    }
    (directory / "index.json.gz").write_bytes(gzip.compress(json.dumps(index).encode()))


def mutate(entries: dict[str, bytes], label: str) -> None:
    def data(name: str) -> Any:
        return json.loads(entries[name])

    def save(name: str, value: object) -> None:
        entries[name] = json.dumps(value).encode()

    measured = data("final/measurement.json")
    if label == "invent-delivery":
        measured["public_finite_delivery"] = True
    elif label == "remove-semantic-disproof":
        rows = data("omission-controls.json")
        row = next(row for row in rows if row["omission"] == "semantic-history")
        for name in row["ledger"]:
            row["ledger"][name] = []
        save("omission-controls.json", rows)
        xml = ET.fromstring(entries["omission-semantic-history.xml"])
        for item in xml.iter("testcase"):
            for child in list(item):
                if child.tag == "failure":
                    item.remove(child)
        entries["omission-semantic-history.xml"] = ET.tostring(xml)
    elif label == "writer-identity":
        path = "final/writer-a/initial-assets-complete-0.json"
        raw = data(path)
        raw["event"]["header"]["native_blobs"]["inode"] += 1
        raw["event"]["native_directory"] = raw["event"]["header"]["native_blobs"]
        save(path, raw)
    else:
        for name, capture in measured["inventories"].items():
            if label == "native-length":
                capture["references"][0]["byte_size"] += 1
            elif label == "missing-oracle":
                capture["rows"][0]["inventory"]["composition_unavailable"] = ""
            else:
                capture["rows"][0]["inventory"]["resolution"]["maximum_ppi"] = 123456.0
            path = f"final/{name}/report.json"
            raw = data(path)
            raw.update(capture)
            save(path, raw)
    save("final/measurement.json", measured)


def run() -> list[dict[str, str]]:
    original = load(Path(__file__).parent)
    outcomes: list[dict[str, str]] = []
    expected = {
        "invent-delivery": "No finite delivery",
        "remove-semantic-disproof": "Isolated omission disproof",
        "native-length": "Exact retained native blob",
        "missing-oracle": "Missing independent composition oracle limitation",
        "wrong-maximum": "Resolution maximum",
        "writer-identity": "Saved writer header",
    }
    for label, message in expected.items():
        entries = dict(original)
        mutate(entries, label)
        with tempfile.TemporaryDirectory(prefix="native-header-control-") as temporary:
            directory = Path(temporary)
            pack(directory, entries)
            # Successful loading establishes that these are coherent digest-valid
            # repacks, rather than accidentally broken ZIP/part integrity controls.
            coherent = load(directory)
            try:
                verify(coherent)
            except ValueError as error:
                if str(error) != message:
                    raise AssertionError((label, str(error), message)) from error
                outcomes.append({"control": label, "refused": message})
            else:
                raise AssertionError("Invalid evidence accepted: " + label)
    verify(original)
    return outcomes


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
