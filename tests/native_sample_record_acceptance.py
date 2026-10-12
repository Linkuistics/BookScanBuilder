"""Retain/restore actual native channels after PDF loss; no composition truth."""

import argparse
import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import cast

from profile_acceptance import NAMES, construct
from sample_acceptance import TRUTH, make_fixture

from bookscan import intake, native_sample_record, samples


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def run(directory: Path) -> dict[str, object]:
    directory.mkdir()
    # Existing independently constructed channel/profile inputs precede decoding.
    truth = {
        "packed_cases": TRUTH,
        "profile_cases": NAMES,
        "controls": ["changed-blob", "missing-blob", "wrong-placement", "false-composition"],
        "claim": "Exact retained channel/colour/Decode facts, including malformed profiles.",
        "limitation": "No transform execution, complete-page fidelity or accepted project claim.",
    }
    (directory / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    blobs: dict[str, bytes] = {}
    rows: list[dict[str, object]] = []
    subjects: list[samples.Sample] = []
    for label, build in (("packed", make_fixture), ("profile", construct)):
        original = directory / (label + ".pdf")
        build(original)
        saved = intake.snapshot(original, directory / (label + "-snapshot.pdf"))
        for page in saved.pages:
            inventory = samples.collect(saved, page)
            row: dict[str, object] = {
                "case": label,
                "source_pdf_page": page.source_page,
                "source_sha256": saved.sha256,
                "sample_count": len(inventory.images),
                "records": [],
            }
            entries: list[dict[str, object]] = []
            for subject in inventory.images:
                if subject.packed is not None:
                    blobs[sha(subject.packed)] = subject.packed
                pending = [subject.color]
                while pending:
                    color = pending.pop()
                    if color is not None:
                        for raw in (color.profile, color.palette):
                            if raw is not None:
                                blobs[sha(raw)] = raw
                        pending.append(color.base)
                entries.append(native_sample_record.record(subject))
                subjects.append(subject)
            row["records"] = entries
            rows.append(row)
        original.unlink()
        saved.path.unlink()
    retained = directory / "blobs"
    retained.mkdir()
    for digest, raw in blobs.items():
        (retained / digest).write_bytes(raw)

    def read(digest: str) -> bytes:
        return (retained / digest).read_bytes()

    controls: list[dict[str, object]] = []
    ordinal = 0
    for row in rows:
        for entry in cast(list[dict[str, object]], row["records"]):
            subject = subjects[ordinal]
            result = native_sample_record.restore(entry, subject.placement, read_blob=read)
            assert result == subject
            assert list(result.pixels()) == list(subject.pixels())
            failures: list[str] = []
            for name in truth["controls"]:
                assert isinstance(name, str)
                value = copy.deepcopy(entry)
                position = subject.placement
                read_control = read
                if name == "changed-blob":

                    def changed(digest: str) -> bytes:
                        return read(digest) + b"changed"

                    read_control = changed
                elif name == "missing-blob":

                    def absent(digest: str) -> bytes:
                        raise FileNotFoundError(digest)

                    read_control = absent
                elif name == "wrong-placement":
                    position = replace(position, path=(*position.path, "wrong"))
                else:
                    value["composition_verified"] = True
                try:
                    native_sample_record.restore(value, position, read_blob=read_control)
                except native_sample_record.NativeSampleRecordError as error:
                    assert error.exit_code == 3 and error.code == "INVALID_PROJECT"
                    failures.append(name)
                else:
                    raise AssertionError("Wrong subject passed: " + name)
            controls.append({"ordinal": ordinal, "refused": failures})
            ordinal += 1
    assert not list(directory.glob("*.pdf"))
    report: dict[str, object] = {
        "format": "BookScanBuilderNativeSampleRecordAcceptance",
        "version": 1,
        "truth": truth,
        "rows": rows,
        "controls": controls,
        "blobs": {digest: len(raw) for digest, raw in sorted(blobs.items())},
        "all_pdf_paths_removed": True,
        "composition_verified": False,
        "accepted_project_delivered": False,
    }
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.artifacts), indent=2))


if __name__ == "__main__":
    main()
