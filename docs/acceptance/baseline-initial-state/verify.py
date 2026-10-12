"""Check retained initial-state bytes and meanings without historical host paths.

Copied native inode identities are historical facts, not a relocatable compatible
project. This reader does not attest execution or independent composition fidelity.
"""

import argparse
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from PIL import Image


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest(domain: str, value: object) -> str:
    return sha(
        json.dumps(
            {"domain": domain, "value": value},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )


def ledger(raw: bytes) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for item in ET.fromstring(raw).iter("testcase"):
        key = item.attrib["classname"] + "." + item.attrib["name"]
        assert key not in rows
        rows[key] = [child.tag for child in item if child.tag in ("failure", "error", "skipped")]
    return rows


def verify(directory: Path) -> dict[str, object]:
    index = json.loads((directory / "index.json").read_bytes())
    assert index["format"] == "BookScanBuilderInitialStateEvidence" and index["version"] == 1
    assert (
        index["public_finite_delivery"] is False and index["compatible_completed_project"] is False
    )
    assert index["external_subject_bytes_retained"] is False
    assert (
        index["limitation"] == "Historical consistency and retained bytes do not attest execution "
        "or composition fidelity."
    )
    parts: list[bytes] = []
    for part in index["parts"]:
        assert Path(part["name"]).name == part["name"]
        raw = (directory / part["name"]).read_bytes()
        assert sha(raw) == part["sha256"]
        parts.append(raw)
    raw = b"".join(parts)
    assert sha(raw) == index["archive_sha256"]
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive:
            assert member.isfile() and member.name not in files
            assert not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
            stream = archive.extractfile(member)
            assert stream is not None
            files[member.name] = stream.read()
    assert {name: sha(data) for name, data in files.items()} == index["files"]
    measured = json.loads(files["measurement/measurement.json"])
    assert measured["public_finite_delivery"] is False
    outcomes = ledger(files["measurement/gate-a.xml"])
    assert outcomes == ledger(files["measurement/gate-b.xml"]) == measured["units"]
    assert len(outcomes) == 2464 and not any(outcomes.values())
    new = {key: value for key, value in outcomes.items() if "test_baseline_state." in key}
    assert len(new) == 51 and sorted(new) == measured["new_units"]
    for suffix in ("a", "b"):
        assert new == ledger(files["measurement/wheel-units-" + suffix + ".xml"])
    assert ledger(files["measurement/staff-a.xml"]) == ledger(files["measurement/staff-b.xml"])
    before = json.loads(gzip.decompress(files["measurement/subjects-before.json.gz"]))
    assert before == json.loads(gzip.decompress(files["measurement/subjects-after.json.gz"]))
    assert len(before) == measured["subjects"]
    assert json.loads(files["measurement/frozen-status.json"])["completed"] is True
    omissions = json.loads(files["instrument/omissions.json"])
    for kind, count in (("render-context", 8), ("discovery-inventory", 4)):
        observed = ledger(files["instrument/omission-" + kind + ".xml"])
        assert observed == omissions[kind]["outcomes"]
        assert sorted(key for key, value in observed.items() if value) == sorted(
            omissions[kind]["failed"]
        )
        assert len(omissions[kind]["failed"]) == count and len(observed) == 51
        assert omissions[kind]["product_unchanged"] is True
        assert sha(files["omission/" + kind + ".py"]) == omissions[kind]["copied_source_sha256"]
    with zipfile.ZipFile(io.BytesIO(files["instrument/wheel.whl"])) as wheel:
        package = {
            name: sha(wheel.read(name)) for name in wheel.namelist() if name.startswith("bookscan/")
        }
        assert package == measured["package_members"]
        assert (
            wheel.read("bookscan/baseline_state.py")
            == files["subject/src/bookscan/baseline_state.py"]
        )
        with tempfile.TemporaryDirectory(prefix="bookscan-retained-initial-") as temp:
            target = Path(temp)
            for name in package:
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(wheel.read(name))
            for label in ("native-source-a", "native-source-b", "native-wheel-a", "native-wheel-b"):
                prefix = "measurement/" + label + "/"
                report = json.loads(files[prefix + "report.json"])
                state = report["state"]
                assert (
                    report["public_finite_delivery"] is False
                    and report["composition_fidelity_verified"] is False
                )
                assert (
                    report["source_loss_resume"]
                    and report["resource_loss_resume"]
                    and report["native_resume_launch_denied"]
                )
                assert len(report["limitations"]) == 3 and "Historical" in report["limitations"][0]
                assert state["review"] == {
                    "dispositions": [],
                    "inspections": [],
                    "acknowledgements": [],
                    "retries": [],
                }
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
                assert state["review_revision"] == digest(
                    "BookScanBuilderReview-v1",
                    {
                        "project_id": state["project_id"],
                        "import": imported,
                        "dispositions": [],
                        "inspections": [],
                    },
                )
                assert (
                    state["snapshot_id"]
                    == report["snapshot_id"]
                    == digest("BookScanBuilderExportSnapshot-v1", state["snapshot"])
                )
                assert state["snapshot_id"] != state["review_revision"]
                assert state["snapshot"]["toolchain"] == state["dependencies"]
                assert state["snapshot"]["project_id"] == state["project_id"]
                assert state["snapshot"]["source_sha256"] == state["source"]["source_sha256"]
                assert len(state["occurrences"]) == len(report["controls"]) == 7
                assert report["baseline_sha256"] == [
                    page["rgb_sha256"] for page in state["occurrences"]
                ]
                assert measured["native"][label]["pages"] == [
                    {key: value for key, value in page.items() if key != "render"}
                    for page in state["occurrences"]
                ]
                assert measured["native"][label]["controls"] == report["controls"]
                checkpoint = files[
                    prefix + "project/checkpoints/" + report["checkpoint_sha256"] + ".json"
                ]
                assert (
                    sha(checkpoint) == report["checkpoint_sha256"]
                    and json.loads(checkpoint)["state"] == state
                )
                assert (
                    files[prefix + "project/checkpoints/current.target"]
                    == (report["checkpoint_sha256"] + ".json").encode()
                )
                assert (
                    json.loads(files[prefix + "project/project.json"])["project_id"]
                    == state["project_id"]
                )
                assert sha(files[prefix + "project/source.pdf"]) == state["source"]["source_sha256"]
                for reference, page, revision, shown in zip(
                    state["baselines"],
                    state["occurrences"],
                    state["image_revisions"],
                    state["snapshot"]["pages"],
                    strict=True,
                ):
                    for key in ("id", "source_pdf_page", "geometry", "analysis", "triage_reasons"):
                        assert shown[key] == page[key]
                    assert (
                        shown["image_revision"] == revision
                        and shown["image_sha256"] == page["rgb_sha256"]
                    )
                    assert (
                        shown["side"] == "unknown"
                        and shown["anchors"] == []
                        and shown["inspections"] == []
                    )
                    assert all(shown[key] is None for key in ("half", "group", "run", "placement"))
                    png = files[prefix + "project/assets/" + reference["id"] + ".png"]
                    assert sha(png) == reference["png_sha256"] and len(png) == reference["png_size"]
                    with Image.open(io.BytesIO(png)) as image:
                        assert image.mode == "RGB" and list(image.size) == reference["size"]
                        assert sha(image.tobytes()) == reference["rgb_sha256"] == page["rgb_sha256"]
                    assert revision == digest(
                        "BookScanBuilderImage-v1",
                        {"rgb_sha256": page["rgb_sha256"], "geometry": page["geometry"]},
                    )
                for reference in state["native_blobs"]:
                    blob = files[prefix + "project/native-blobs/" + reference["sha256"] + ".bin"]
                    assert sha(blob) == reference["sha256"] and len(blob) == reference["byte_size"]
                script = (
                    "import json,sys; from pathlib import Path; import subprocess; "
                    "from bookscan import dependency_record,fontconfig_discovery_record; "
                    "s=json.load(sys.stdin)['state']; "
                    "deny=lambda *a,**k: (_ for _ in ()).throw("
                    "PermissionError('historical I/O denied')); "
                    "Path.open=deny; Path.stat=deny; Path.resolve=deny; subprocess.Popen=deny; "
                    "d=dependency_record.restore(s['dependencies'],s['resource_binding']); "
                    "f=fontconfig_discovery_record.restore(s['fontconfig']); "
                    "assert f.linked==dict(d.linked)['pdftocairo']; "
                    "assert f.snapshot is not None and f.cache is not None"
                )
                subprocess.run(
                    [sys.executable, "-c", script],
                    input=files[prefix + "report.json"],
                    cwd=target,
                    env=dict(os.environ, PYTHONPATH=str(target), PYTHONDONTWRITEBYTECODE="1"),
                    check=True,
                )
    natives = measured["native"]
    assert all(value == next(iter(natives.values())) for value in natives.values())
    return {
        "entries": len(files),
        "tests": len(outcomes),
        "new_tests": len(new),
        "subjects": len(before),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).parent)
    print(json.dumps(verify(parser.parse_args().directory)))


if __name__ == "__main__":
    main()
