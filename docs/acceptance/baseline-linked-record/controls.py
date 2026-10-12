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
    for fault in ("native-use", "header-disproof"):
        altered = dict(entries)
        if fault == "native-use":
            name = "frozen/cache-source-a/result.json"
            data = json.loads(altered[name])
            data["a"]["binding"]["linked"]["runtime_resources_verified"] = True
            altered[name] = json.dumps(data).encode()
            expected = "No native-use truth"
        else:
            altered["header-red.txt"] = altered["header-red.txt"].replace(
                b"3 failed, 60 deselected", b"3 passed, 60 deselected"
            )
            expected = "Missing header disproof"
        with tempfile.TemporaryDirectory(prefix="bookscan-linked-evidence-control-") as name:
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
    return observed


if __name__ == "__main__":
    print(json.dumps(controls(), sort_keys=True))
