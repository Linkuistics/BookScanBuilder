"""Coherently rehash false evidence; require the independent reader to refuse."""

import copy
import io
import json
import tarfile
import tempfile
from pathlib import Path

import verify


def run(directory: Path) -> list[str]:
    index = json.loads((directory / "index.json").read_bytes())
    original: dict[str, bytes] = {}
    raw = b"".join((directory / item["name"]).read_bytes() for item in index["parts"])
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive:
            stream = archive.extractfile(member)
            assert stream is not None
            original[member.name] = stream.read()
    verify.verify(directory, reconstruct=False)
    refused: list[str] = []
    for kind in (
        "invented-delivery",
        "removed-disproof",
        "wrong-wheel-source",
        "erased-limitations",
    ):
        files = dict(original)
        changed = copy.deepcopy(index)
        if kind == "invented-delivery":
            changed["complete_finite_handoff"] = True
            measurement = json.loads(files["measurement/measurement.json"])
            measurement["complete_finite_handoff"] = True
            files["measurement/measurement.json"] = json.dumps(measurement).encode()
        elif kind == "removed-disproof":
            for name in list(files):
                if name.startswith("controls/"):
                    del files[name]
        elif kind == "wrong-wheel-source":
            files["src/bookscan/finite_protocol.py"] += b"\n# inconsistent copied source\n"
        else:
            measurement = json.loads(files["measurement/measurement.json"])
            for case in measurement["public"]["cases"].values():
                if "stdout" in case:
                    case["stdout"] = case["stdout"].replace(
                        "Fresh import loses old review facts", "Review facts need no attention"
                    )
            files["measurement/measurement.json"] = json.dumps(measurement).encode()
            for family in ("source-public", "wheel-public"):
                for letter in ("a", "b"):
                    name = f"measurement/{family}-{letter}/result.json"
                    report = json.loads(files[name])
                    report.update(measurement["public"])
                    files[name] = json.dumps(report).encode()
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for name, value in sorted(files.items()):
                member = tarfile.TarInfo(name)
                member.size = len(value)
                archive.addfile(member, io.BytesIO(value))
        value = buffer.getvalue()
        changed["archive_sha256"] = verify.sha(value)
        changed["files"] = {name: verify.sha(data) for name, data in files.items()}
        changed["parts"] = [{"name": "corpus.part", "sha256": verify.sha(value)}]
        with tempfile.TemporaryDirectory(prefix="bookscan-protocol-control-") as temp:
            target = Path(temp)
            (target / "corpus.part").write_bytes(value)
            (target / "index.json").write_text(json.dumps(changed))
            try:
                verify.verify(target, reconstruct=False)
            except (AssertionError, KeyError):
                refused.append(kind)
            else:
                raise AssertionError("Reader accepted coherent false corpus: " + kind)
    return refused


if __name__ == "__main__":
    print(json.dumps({"coherent_false_corpora_refused": run(Path(__file__).parent)}))
