"""Repack coherent wrong observations and require the standalone reader to refuse."""

import gzip
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import cast

import verify


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load(directory: Path) -> tuple[dict[str, object], dict[str, bytes]]:
    index = cast(
        dict[str, object], json.loads(gzip.decompress((directory / "index.json.gz").read_bytes()))
    )
    parts = cast(list[dict[str, object]], index["parts"])
    raw = b"".join((directory / str(part["name"])).read_bytes() for part in parts)
    entries = cast(dict[str, dict[str, object]], index["entries"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return index, {
            name: archive.read("blobs/" + str(item["sha256"])) for name, item in entries.items()
        }


def pack(index: dict[str, object], read: dict[str, bytes], directory: Path) -> None:
    stream = io.BytesIO()
    blobs = {sha(raw): raw for raw in read.values()}
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for digest, raw in sorted(blobs.items()):
            archive.writestr("blobs/" + digest, raw)
    raw = stream.getvalue()
    parts: list[dict[str, object]] = []
    for offset in range(0, len(raw), 900_000):
        chunk = raw[offset : offset + 900_000]
        name = f"raw-{len(parts):03d}.zippart"
        (directory / name).write_bytes(chunk)
        parts.append({"name": name, "size": len(chunk), "sha256": sha(chunk)})
    current = {
        **index,
        "archive_size": len(raw),
        "archive_sha256": sha(raw),
        "parts": parts,
        "entries": {name: {"sha256": sha(blob), "size": len(blob)} for name, blob in read.items()},
    }
    (directory / "index.json.gz").write_bytes(gzip.compress(json.dumps(current).encode(), mtime=0))


def change(read: dict[str, bytes], kind: str) -> None:
    if kind == "wrong-unit":
        key = (
            "tests.test_occurrence_record."
            "test_complete_core_roster_binds_every_page_after_original_loss"
        )
        for name in (
            "frozen/gate-a.xml",
            "frozen/gate-b.xml",
            "frozen/wheel-units-a.xml",
            "frozen/wheel-units-b.xml",
        ):
            document = ET.fromstring(read[name])
            row = next(
                node
                for node in document.iter("testcase")
                if node.attrib["classname"] + "." + node.attrib["name"] == key
            )
            ET.SubElement(row, "failure").text = "coherent deliberately wrong result"
            read[name] = ET.tostring(document)
        measured = cast(dict[str, object], json.loads(read["frozen/measurement.json"]))
        cast(dict[str, object], measured["units"])[key] = ["failure"]
        read["frozen/measurement.json"] = json.dumps(measured).encode()
        return
    for suffix in ("a", "b"):
        prefix = (
            f"frozen/wheel-fixtures-{suffix}/test_restart_rejects_hash_vali0/"
            "Saved café project/checkpoints/"
        )
        rows = {
            name: cast(dict[str, object], json.loads(raw))
            for name, raw in read.items()
            if name.startswith(prefix) and name.endswith(".json")
        }
        ordered = sorted(rows, key=lambda name: cast(int, rows[name]["checkpoint_revision"]))
        first, current = ordered
        wanted = first if kind == "missing-bad-predecessor" else current
        record = rows[wanted]
        state = cast(dict[str, object], record["state"])
        page = cast(list[dict[str, object]], state["occurrences"])[0]
        if kind == "missing-bad-predecessor":
            page["source_sha256"] = cast(dict[str, object], state["source"])["source_sha256"]
        else:
            cast(dict[str, object], page["geometry"])["physical_points"] = ["1", "1"]
        raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        del read[wanted]
        read[prefix + sha(raw) + ".json"] = raw
        if kind == "missing-bad-predecessor":
            rows[current]["previous_sha256"] = sha(raw)
            changed = json.dumps(rows[current], sort_keys=True, separators=(",", ":")).encode()
            del read[current]
            read[prefix + sha(changed) + ".json"] = changed


def main() -> None:
    directory = Path(__file__).resolve().parent
    verify.run(directory)
    index, base = load(directory)
    results: list[dict[str, object]] = []
    for kind in ("wrong-unit", "wrong-physical-mapping", "missing-bad-predecessor"):
        read = dict(base)
        change(read, kind)
        with tempfile.TemporaryDirectory(prefix="bookscan-core-control-") as name:
            target = Path(name)
            pack(index, read, target)
            result = subprocess.run(
                [sys.executable, str(directory / "verify.py"), "--directory", name],
                capture_output=True,
                text=True,
                check=False,
            )
            expected = (
                "ValueError: Failed unit construction"
                if kind == "wrong-unit"
                else "ValueError: Occurrence-core evidence disagreement"
            )
            if result.returncode != 1 or expected not in result.stderr:
                raise ValueError(
                    "Wrong coherent evidence did not reach semantic refusal: " + result.stderr
                )
            results.append(
                {
                    "case": kind,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
    print(json.dumps({"verified": True, "controls": results}, indent=2))


if __name__ == "__main__":
    main()
