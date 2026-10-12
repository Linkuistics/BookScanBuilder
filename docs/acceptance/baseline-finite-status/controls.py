"""Rehash four false evidence corpora and require the ordinary reader to refuse.

Run: uv run --locked python docs/acceptance/baseline-finite-status/controls.py
These are consistency controls, not historical-execution or fidelity oracles.
"""

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


def run(base: Path) -> dict[str, object]:
    frozen = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in base.iterdir()
        if path.is_file()
    }
    index: dict[str, Any] = json.loads((base / "index.json").read_bytes())
    raw_archive = b"".join((base / name).read_bytes() for name in index["parts"])
    with zipfile.ZipFile(io.BytesIO(raw_archive)) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="bookscan-status-false-") as temporary:
        for fault in (
            "invented-handoff",
            "removed-disproof",
            "wrong-source",
            "erased-fidelity-limit",
        ):
            changed = dict(entries)
            report: dict[str, Any] = json.loads(changed["reading/measurement.json"])
            if fault == "invented-handoff":
                report["complete_finite_handoff"] = True
            elif fault == "removed-disproof":
                report["controls"]["omit-history"]["failed"] = {}
            elif fault == "erased-fidelity-limit":
                report["native"]["composition_fidelity_verified"] = True
            else:
                changed["source/src/bookscan/finite_status.py"] += b"\n# coherent wrong source\n"
            changed["reading/measurement.json"] = (
                json.dumps(report, sort_keys=True, indent=2) + "\n"
            ).encode()
            target = Path(temporary) / fault
            target.mkdir()
            with zipfile.ZipFile(target / "corpus.zip", "w", compression=zipfile.ZIP_DEFLATED) as z:
                for name, raw in sorted(changed.items()):
                    z.writestr(name, raw)
            current = copy.deepcopy(index)
            current["parts"] = ["corpus.zip"]
            current["sha256"] = hashlib.sha256((target / "corpus.zip").read_bytes()).hexdigest()
            current["entries"] = {
                name: {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                for name, raw in sorted(changed.items())
            }
            (target / "index.json").write_text(json.dumps(current))
            (target / "verification.json.gz").write_bytes(
                gzip.compress(changed["reading/measurement.json"], mtime=0)
            )
            try:
                verify(target)
            except AssertionError:
                results.append({"fault": fault, "coherently_rehashed": True, "refused": True})
            else:
                raise AssertionError("False evidence accepted: " + fault)
    assert frozen == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in base.iterdir()
        if path.is_file()
    }
    return {"original_subjects_unchanged": True, "controls": results}


if __name__ == "__main__":
    print(json.dumps(run(Path(__file__).resolve().parent), indent=2))
