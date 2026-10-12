"""Coherent digest-valid repacks must retain disproof and refuse invented native-use truth."""

import gzip
import io
import json
import tempfile
import zipfile
from pathlib import Path

from verify import reconstruct, sha, verify


def repack(directory: Path, entries: dict[str, bytes]) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(entries.items()):
            archive.writestr(name, raw)
    raw = buffer.getvalue()
    (directory / "raw.zippart").write_bytes(raw)
    index = {
        "parts": [{"name": "raw.zippart", "sha256": sha(raw)}],
        "entries": {name: sha(raw) for name, raw in entries.items()},
    }
    (directory / "index.json.gz").write_bytes(gzip.compress(json.dumps(index).encode(), mtime=0))


def controls() -> dict[str, str]:
    entries = reconstruct(Path(__file__).parent)
    verify(entries)
    observed: dict[str, str] = {}
    for fault in ("native-use", "alias-disproof"):
        altered = dict(entries)
        if fault == "native-use":
            name = "frozen/snapshot-explicit-source-a/result.json"
            data = json.loads(altered[name])
            data["a"]["binding"]["resource_snapshot"]["runtime_resources_verified"] = True
            altered[name] = json.dumps(data).encode()
            expected = "No native-use truth"
        else:
            altered["alias-red.txt"] = altered["alias-red.txt"].replace(
                b"2 failed, 58 deselected", b"2 passed, 58 deselected"
            )
            expected = "Missing alias disproof"
        with tempfile.TemporaryDirectory(prefix="bookscan-discovery-evidence-control-") as name:
            directory = Path(name)
            repack(directory, altered)
            restored = reconstruct(directory)  # All replacement digests are valid.
            if restored != altered:
                raise AssertionError("Repack changed the control subject")
            try:
                verify(restored)
            except ValueError as error:
                if str(error) != expected:
                    raise AssertionError("Unrelated control failure") from error
                observed[fault] = str(error)
            else:
                raise AssertionError("Contradictory coherent evidence accepted")
    # Chunk digests can be valid while a shared blob's content address is false.
    blobs = {"blobs/" + sha(raw): raw for raw in entries.values()}
    target = "blobs/" + sha(entries["alias-red.txt"])
    blobs[target] = b"wrong shared subject"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(blobs.items()):
            archive.writestr(name, raw)
    payload = buffer.getvalue()
    with tempfile.TemporaryDirectory(prefix="bookscan-shared-blob-control-") as name:
        directory = Path(name)
        (directory / "raw.zippart").write_bytes(payload)
        index = {
            "storage": "sha256-blobs-v1",
            "parts": [{"name": "raw.zippart", "sha256": sha(payload)}],
            "entries": {name: sha(raw) for name, raw in entries.items()},
        }
        (directory / "index.json.gz").write_bytes(
            gzip.compress(json.dumps(index).encode(), mtime=0)
        )
        try:
            reconstruct(directory)
        except ValueError as error:
            if str(error) != "Shared blob content address":
                raise AssertionError("Unrelated shared-blob control failure") from error
            observed["shared-blob"] = str(error)
        else:
            raise AssertionError("Misaddressed shared evidence accepted")
    return observed


if __name__ == "__main__":
    print(json.dumps(controls(), sort_keys=True))
