"""Repack coherent evidence mutations, then require independent semantic refusal."""

import copy
import gzip
import io
import json
import tempfile
import zipfile
from pathlib import Path

from verify import equal, load, sha, verify


def store(directory: Path, read: dict[str, bytes]) -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(read.items()):
            archive.writestr(name, raw)
    raw = stream.getvalue()
    parts: list[dict[str, object]] = []
    for ordinal, offset in enumerate(range(0, len(raw), 900_000)):
        name = f"raw-{ordinal:03d}.zippart"
        chunk = raw[offset : offset + 900_000]
        (directory / name).write_bytes(chunk)
        parts.append({"name": name, "sha256": sha(chunk), "size": len(chunk)})
    index = {"parts": parts, "entries": {n: sha(v) for n, v in read.items()}}
    (directory / "index.json.gz").write_bytes(gzip.compress(json.dumps(index).encode()))


def control(directory: Path, read: dict[str, bytes], expected: str) -> str:
    store(directory, read)
    restored = load(directory)  # All archive/entry identities are deliberately coherent.
    equal(restored, read, "coherent repack")
    try:
        verify(restored)
    except ValueError as error:
        equal(str(error), expected, "named semantic refusal")
        return str(error)
    raise ValueError("Wrong evidence was accepted")


def run() -> dict[str, object]:
    read = load(Path(__file__).parent)
    result: dict[str, object] = {"baseline": verify(read)}
    wrong = copy.deepcopy(read)
    measured = json.loads(wrong["frozen/measurement.json"])
    prior = json.loads(wrong["prior-measurement.json"])
    for lane in ("source", "wheel"):
        for suffix in ("a", "b"):
            label = f"assessment-{lane}-{suffix}"
            name = f"frozen/{label}/report.json"
            report = json.loads(wrong[name])
            for record in (
                report["records"][0],
                measured["native"][label]["records"][0],
                prior["native"][label]["records"][0],
            ):
                record["render"]["command"][7] = "150"
            wrong[name] = json.dumps(report).encode()
    wrong["frozen/measurement.json"] = json.dumps(measured).encode()
    wrong["prior-measurement.json"] = json.dumps(prior).encode()
    with tempfile.TemporaryDirectory(prefix="render-evidence-density-") as name:
        result["coherent-wrong-density"] = control(Path(name), wrong, "native MediaBox policy")
    wrong = copy.deepcopy(read)
    measured = json.loads(wrong["frozen/measurement.json"])
    for lane in ("source", "wheel"):
        for suffix in ("a", "b"):
            label = f"assessment-{lane}-{suffix}"
            name = f"frozen/{label}/report.json"
            report = json.loads(wrong[name])
            del report["render_policy_controls"]["wrong-density"]
            del measured["native"][label]["render_policy_controls"]["wrong-density"]
            wrong[name] = json.dumps(report).encode()
    wrong["frozen/measurement.json"] = json.dumps(measured).encode()
    with tempfile.TemporaryDirectory(prefix="render-evidence-control-") as name:
        result["missing-density-control"] = control(Path(name), wrong, "native policy controls")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
