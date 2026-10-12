"""Observe refusal of coherently rehashed false retained evidence, without edits."""

import copy
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def main() -> None:
    here = Path(__file__).parent
    index = json.loads((here / "index.json").read_bytes())
    body = b"".join((here / item["name"]).read_bytes() for item in index["parts"])
    originals: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as archive:
        for entry in archive:
            stream = archive.extractfile(entry)
            assert stream is not None
            originals[entry.name] = stream.read()
    outcomes: list[str] = []
    for fault in ("invented-delivery", "removed-disproof", "wrong-build", "erased-limitation"):
        files = dict(originals)
        name = {
            "invented-delivery": "measurement/measurement.json",
            "removed-disproof": "instrument/omissions.json",
            "wrong-build": "measurement/native-source-a/report.json",
            "erased-limitation": "measurement/native-source-a/report.json",
        }[fault]
        data = json.loads(files[name])
        if fault == "invented-delivery":
            data["public_finite_delivery"] = True
        elif fault == "removed-disproof":
            data["build"]["failed"] = []
        elif fault == "wrong-build":
            data["preflight"]["helper"]["build_identity"] = "0" * 64
        else:
            data["limitation"] = "Accepted source fidelity"
        files[name] = json.dumps(data).encode()
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w:gz") as archive:
            for key, value in sorted(files.items()):
                entry = tarfile.TarInfo(key)
                entry.size, entry.mtime = len(value), 0
                archive.addfile(entry, io.BytesIO(value))
        packed = raw.getvalue()
        altered = copy.deepcopy(index)
        altered["archive_sha256"] = hashlib.sha256(packed).hexdigest()
        altered["files"] = {key: hashlib.sha256(value).hexdigest() for key, value in files.items()}
        with tempfile.TemporaryDirectory(prefix="bookscan-dependency-evidence-control-") as temp:
            target = Path(temp)
            altered["parts"] = []
            for offset in range(0, len(packed), 850000):
                part = packed[offset : offset + 850000]
                part_name = f"corpus-{offset // 850000 + 1:02d}.part"
                (target / part_name).write_bytes(part)
                altered["parts"].append(
                    {"name": part_name, "sha256": hashlib.sha256(part).hexdigest()}
                )
            (target / "index.json").write_text(json.dumps(altered))
            result = subprocess.run(
                [sys.executable, str(here / "verify.py"), "--directory", str(target)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 1 and (
                "AssertionError" in result.stderr or "DependencyRecordError" in result.stderr
            ), (fault, result.stdout, result.stderr)
            outcomes.append(fault)
    print(json.dumps({"coherent_false_corpora_refused": outcomes}))


if __name__ == "__main__":
    main()
