"""Reproduce valid repacked disproofs from retained deltas and exact ZIP metadata."""

import gzip
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import cast

HERE = Path(__file__).resolve().parent


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(gzip.decompress(path.read_bytes())))


def main() -> int:
    baseline = load(HERE / "index.json.gz")
    original = b"".join(
        (HERE / cast(str, row["name"])).read_bytes()
        for row in cast(list[dict[str, object]], baseline["parts"])
    )
    if sha(original) != baseline["archive_sha256"]:
        raise ValueError("Original archive mismatch")
    with zipfile.ZipFile(io.BytesIO(original)) as source:
        blobs = {name.removeprefix("blobs/"): source.read(name) for name in source.namelist()}
    controls = cast(list[dict[str, object]], load(HERE / "control-deltas.json.gz")["controls"])
    metadata = load(HERE / "control-zip-metadata.json.gz")
    for control in controls:
        kind = cast(str, control["kind"])
        index_name = cast(str, control["valid_repacked_index"])
        index = load(HERE / index_name)
        entries = cast(dict[str, dict[str, object]], index["entries"])
        altered = dict(blobs)
        for name, value in cast(dict[str, str], control["deltas"]).items():
            raw = value.encode("utf-8")
            row = entries[name]
            if (len(raw), sha(raw)) != (row["size"], row["sha256"]):
                raise ValueError("Control delta mismatch")
            altered[sha(raw)] = raw
        meta = cast(dict[str, dict[str, object]], metadata[kind])
        buffer = io.BytesIO()
        with zipfile.ZipFile(
            buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as output:
            for digest in sorted({cast(str, row["sha256"]) for row in entries.values()}):
                name = "blobs/" + digest
                row = meta[name]
                date = cast(
                    tuple[int, int, int, int, int, int], tuple(cast(list[int], row["date_time"]))
                )
                info = zipfile.ZipInfo(name, date_time=date)
                info.create_system = cast(int, row["create_system"])
                info.external_attr = cast(int, row["external_attr"])
                info.compress_type = cast(int, row["compress_type"])
                output.writestr(info, altered[digest], compresslevel=9)
        encoded = buffer.getvalue()
        if (len(encoded), sha(encoded)) != (index["archive_size"], index["archive_sha256"]):
            raise ValueError("Exact control archive reconstruction mismatch")
        with tempfile.TemporaryDirectory(prefix="bookscan-header-disproof-") as temporary:
            scratch = Path(temporary)
            (scratch / "verify.py").write_bytes((HERE / "verify.py").read_bytes())
            (scratch / "index.json.gz").write_bytes((HERE / index_name).read_bytes())
            offset = 0
            for row in cast(list[dict[str, object]], index["parts"]):
                size = cast(int, row["size"])
                raw = encoded[offset : offset + size]
                if sha(raw) != row["sha256"]:
                    raise ValueError("Control part mismatch")
                (scratch / cast(str, row["name"])).write_bytes(raw)
                offset += size
            result = subprocess.run(
                [sys.executable, str(scratch / "verify.py")],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            last = (HERE / cast(str, control["refusal"])).read_text().splitlines()[-1]
            if result.returncode != control["exit_code"] or result.stderr.splitlines()[-1] != last:
                raise ValueError("Reconstructed control no longer refuses identically")
    print(json.dumps({"exact_repacked_controls_refused": [row["kind"] for row in controls]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
