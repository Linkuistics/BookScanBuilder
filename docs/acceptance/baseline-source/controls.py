"""Rebuild valid, deliberately wrong evidence and observe the retained reader refuse it."""

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

HERE = Path(__file__).resolve().parent


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    index = cast(
        dict[str, object], json.loads(gzip.decompress((HERE / "index.json.gz").read_bytes()))
    )
    names = ["verify.py", "controls.py", "index.json.gz"] + [
        cast(str, row["name"]) for row in cast(list[dict[str, object]], index["parts"])
    ]
    subjects = {name: sha((HERE / name).read_bytes()) for name in names}
    original_entries = cast(dict[str, dict[str, object]], index["entries"])
    encoded = b"".join(
        (HERE / cast(str, row["name"])).read_bytes()
        for row in cast(list[dict[str, object]], index["parts"])
    )
    with zipfile.ZipFile(io.BytesIO(encoded)) as archive:
        blobs = {name.removeprefix("blobs/"): archive.read(name) for name in archive.namelist()}
    results: list[dict[str, object]] = []
    for control, name in (
        ("unit", "frozen/gate-a.xml"),
        ("source", "frozen/source-source-a/initial-assets-complete-0.json"),
        ("commit", "frozen/source-wheel-b/report.json"),
    ):
        entries = {key: dict(value) for key, value in original_entries.items()}
        original = blobs[cast(str, entries[name]["sha256"])]
        if control == "unit":
            tree = ET.fromstring(original)
            first = next(tree.iter("testcase"))
            first.attrib["name"] += "-wrong-subject"
            changed = ET.tostring(tree)
        else:
            data = cast(dict[str, object], json.loads(original))
            if control == "source":
                event = cast(dict[str, object], data["event"])
                source = cast(dict[str, object], event["source"])
                pages = cast(list[dict[str, object]], source["pages"])
                geometry = cast(dict[str, object], pages[0]["geometry"])
                cast(list[int], geometry["pixels"])[0] += 1
            else:
                cases = cast(list[dict[str, object]], data["cases"])
                cases[0]["committed"] = False
            changed = json.dumps(data, sort_keys=True).encode()
        entries[name].update(sha256=sha(changed), size=len(changed))
        available = {**blobs, sha(changed): changed}
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for digest in sorted({cast(str, row["sha256"]) for row in entries.values()}):
                info = zipfile.ZipInfo("blobs/" + digest, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, available[digest], compresslevel=9)
        wrong = stream.getvalue()
        with tempfile.TemporaryDirectory(prefix="bookscan-source-control-") as temporary:
            target = Path(temporary)
            (target / "verify.py").write_bytes((HERE / "verify.py").read_bytes())
            parts: list[dict[str, object]] = []
            for number, offset in enumerate(range(0, len(wrong), 900_000)):
                part = wrong[offset : offset + 900_000]
                part_name = f"raw-{number:03}.zippart"
                (target / part_name).write_bytes(part)
                parts.append({"name": part_name, "size": len(part), "sha256": sha(part)})
            wrong_index = {
                **index,
                "entries": entries,
                "parts": parts,
                "archive_size": len(wrong),
                "archive_sha256": sha(wrong),
            }
            (target / "index.json.gz").write_bytes(gzip.compress(json.dumps(wrong_index).encode()))
            result = subprocess.run(
                [sys.executable, str(target / "verify.py")],
                capture_output=True,
                text=True,
                check=False,
            )
            if (
                result.returncode != 1
                or "Retained saved-source evidence disagreement" not in result.stderr
            ):
                raise ValueError("Wrong evidence was not refused: " + result.stderr)
            results.append(
                {
                    "control": control,
                    "entry": name,
                    "before_sha256": sha(original),
                    "wrong_sha256": sha(changed),
                    "archive_sha256": sha(wrong),
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr.replace(temporary, "CONTROL"),
                    "refused": True,
                }
            )
    after = {name: sha((HERE / name).read_bytes()) for name in names}
    if subjects != after:
        raise ValueError("Control input changed during measurement")
    print(
        json.dumps({"subjects": subjects, "controls": results, "unchanged": True}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
