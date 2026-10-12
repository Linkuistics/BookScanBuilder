"""Observe coherent false retained corpora fail without changing original evidence."""

import copy
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def encoded(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(domain: str, value: object) -> str:
    return hashlib.sha256(encoded({"domain": domain, "value": value})).hexdigest()


def main() -> None:
    here = Path(__file__).parent
    index = json.loads((here / "index.json").read_bytes())
    raw = b"".join((here / part["name"]).read_bytes() for part in index["parts"])
    originals: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive:
            stream = archive.extractfile(member)
            assert stream is not None
            originals[member.name] = stream.read()
    refused: list[str] = []
    for fault in ("invented-delivery", "removed-disproof", "wrong-build", "erased-limitations"):
        files = dict(originals)
        if fault == "invented-delivery":
            value = json.loads(files["measurement/measurement.json"])
            value["public_finite_delivery"] = True
            # The reader's explicit public boundary lives in the index too.
            name = "measurement/measurement.json"
            files[name] = encoded(value)
        elif fault == "removed-disproof":
            value = json.loads(files["instrument/omissions.json"])
            value["render-context"]["failed"] = []
            files["instrument/omissions.json"] = encoded(value)
        elif fault == "erased-limitations":
            value = json.loads(files["measurement/native-source-a/report.json"])
            value["limitations"] = []
            files["measurement/native-source-a/report.json"] = encoded(value)
        else:
            measured = json.loads(files["measurement/measurement.json"])
            for label in ("native-source-a", "native-source-b", "native-wheel-a", "native-wheel-b"):
                prefix = "measurement/" + label + "/"
                report = json.loads(files[prefix + "report.json"])
                state = report["state"]
                state["dependencies"]["helper"]["build_identity"] = "0" * 64
                state["snapshot"]["toolchain"] = copy.deepcopy(state["dependencies"])
                imported = {
                    key: state[key]
                    for key in (
                        "source",
                        "occurrences",
                        "baselines",
                        "native_blobs",
                        "dependencies",
                        "resource_binding",
                        "fontconfig",
                    )
                }
                state["review_revision"] = digest(
                    "BookScanBuilderReview-v1",
                    {
                        "project_id": state["project_id"],
                        "import": imported,
                        "dispositions": [],
                        "inspections": [],
                    },
                )
                state["snapshot_id"] = digest("BookScanBuilderExportSnapshot-v1", state["snapshot"])
                report["review_revision"], report["snapshot_id"] = (
                    state["review_revision"],
                    state["snapshot_id"],
                )
                old = prefix + "project/checkpoints/" + report["checkpoint_sha256"] + ".json"
                checkpoint = json.loads(files.pop(old))
                checkpoint["state"] = state
                body = encoded(checkpoint)
                report["checkpoint_sha256"] = hashlib.sha256(body).hexdigest()
                files[prefix + "project/checkpoints/" + report["checkpoint_sha256"] + ".json"] = (
                    body
                )
                files[prefix + "project/checkpoints/current.target"] = (
                    report["checkpoint_sha256"] + ".json"
                ).encode()
                measured["native"][label]["helper"] = copy.deepcopy(state["dependencies"]["helper"])
                files[prefix + "report.json"] = encoded(report)
            files["measurement/measurement.json"] = encoded(measured)
        body = io.BytesIO()
        with tarfile.open(fileobj=body, mode="w:gz") as archive:
            for name, data in sorted(files.items()):
                member = tarfile.TarInfo(name)
                member.size, member.mtime = len(data), 0
                archive.addfile(member, io.BytesIO(data))
        packed = body.getvalue()
        changed = copy.deepcopy(index)
        changed["archive_sha256"] = hashlib.sha256(packed).hexdigest()
        changed["files"] = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
        if fault == "invented-delivery":
            changed["public_finite_delivery"] = True
        with tempfile.TemporaryDirectory(prefix="bookscan-initial-evidence-control-") as temp:
            target = Path(temp)
            changed["parts"] = []
            for offset in range(0, len(packed), 850000):
                name = f"corpus-{offset // 850000 + 1:02d}.part"
                part = packed[offset : offset + 850000]
                (target / name).write_bytes(part)
                changed["parts"].append({"name": name, "sha256": hashlib.sha256(part).hexdigest()})
            (target / "index.json").write_text(json.dumps(changed))
            result = subprocess.run(
                [sys.executable, str(here / "verify.py"), "--directory", str(target)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 1 and (
                "AssertionError" in result.stderr or "DependencyRecordError" in result.stderr
            ), (fault, result.stdout, result.stderr)
            refused.append(fault)
    print(json.dumps({"coherent_false_corpora_refused": refused}))


if __name__ == "__main__":
    main()
