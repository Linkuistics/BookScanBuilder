"""Actual native assessments/storage/restart; no complete checkpoint/public claim."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import cast

import assessment_acceptance

from bookscan import (
    assessed_record,
    assessment,
    intake,
    native_setup,
    ownership,
    project_header,
    render,
    source_record,
)


def run(directory: Path, cache: Path) -> dict[str, object]:
    directory.mkdir()
    # Existing independently declared construction truth precedes every comparison.
    prior = assessment_acceptance.run(directory / "construction", cache)
    wanted = cast(list[dict[str, object]], cast(dict[str, object], prior["truth"])["pages"])
    renderer, helper = render.renderer_path(), native_setup.load_cache(cache).binary
    project = directory / "project"
    project.mkdir()
    original = directory / "construction" / "snapshot.pdf"
    subjects: list[assessment.AssessedPage] = []
    payloads: dict[str, bytes] = {}

    def verify(stores: project_header.Stores, state: dict[str, object]) -> None:
        assessed_record.restore(
            stores,
            state["source"],
            state["occurrences"],
            state["baselines"],
            state["native_blobs"],
            renderer,
        )

    with ownership.Writer.acquire(project, ownership.provision(project)) as owner:
        stores = project_header.Stores.provision(owner)
        saved = intake.snapshot(original, owner.path / "source.pdf")
        values: list[dict[str, object]] = []
        baselines: list[dict[str, object]] = []
        for subject, expected in zip(
            assessment.assess_pages(saved, renderer, helper, directory),
            wanted,
            strict=True,
        ):
            value = subject.to_dict()
            assessment_acceptance.verify_record(value, expected)
            values.append(value)
            subjects.append(subject)
            baselines.append(
                stores.images.publish(subject.raster.rgb, subject.raster.size).record()
            )
            for sample in subject.native.images:
                if sample.packed is not None:
                    payloads[hashlib.sha256(sample.packed).hexdigest()] = sample.packed
                pending = [sample.color]
                while pending:
                    color = pending.pop()
                    if color is not None:
                        for raw in (color.profile, color.palette):
                            if raw is not None:
                                payloads[hashlib.sha256(raw).hexdigest()] = raw
                        pending.append(color.base)
        state: dict[str, object] = {
            "source": source_record.record(owner, saved),
            "occurrences": values,
            "baselines": baselines,
            "native_blobs": [
                stores.native.publish(raw).record() for _, raw in sorted(payloads.items())
            ],
        }
        previous = stores.checkpoints.commit(
            state,
            expected=None,
            verify_state=lambda value: verify(stores, value),
        ).checkpoint
        stores.checkpoints.commit(
            state, expected=previous, verify_state=lambda value: verify(stores, value)
        )
    original.unlink()
    controls: list[dict[str, object]] = []
    with project_header.resume(project, verify_state=verify) as (stores, current):
        assert current.revision == 2
        restored = assessed_record.restore(
            stores,
            current.state["source"],
            current.state["occurrences"],
            current.state["baselines"],
            current.state["native_blobs"],
            renderer,
        )
        for subject, actual in zip(subjects, restored, strict=True):
            assert actual.core.page == subject.page and actual.core.analysis == subject.estimate
            assert actual.native == subject.native and actual.reasons == subject.reasons
            assert stores.images.read(actual.core.baseline) == subject.raster.rgb
        before = {p.name: p.read_bytes() for p in (project / "checkpoints").iterdir()}
        for ordinal in range(len(subjects)):
            for fault in ("render", "triage", "native", "core"):
                wrong = copy.deepcopy(current.state)
                row = cast(list[dict[str, object]], wrong["occurrences"])[ordinal]
                if fault == "render":
                    cast(list[str], cast(dict[str, object], row["render"])["command"])[7] = "150"
                elif fault == "triage":
                    row["triage_reasons"] = []
                elif fault == "native":
                    row["composition_fidelity_verified"] = True
                else:
                    row["rgb_sha256"] = "0" * 64
                try:
                    verify(stores, wrong)
                except assessed_record.AssessedRecordError as error:
                    controls.append({"id": row["id"], "fault": fault, "code": error.code})
                else:
                    raise AssertionError("Wrong assessed payload accepted")
                verify(stores, current.state)
        assert {p.name: p.read_bytes() for p in (project / "checkpoints").iterdir()} == before
    report: dict[str, object] = {
        "format": "BookScanBuilderAssessedRecordAcceptance",
        "version": 1,
        "truth_sha256": prior["truth_sha256"],
        "records": [assessment_acceptance.normalized(value, directory) for value in values],
        "baseline_references": baselines,
        "native_blobs": {digest: len(raw) for digest, raw in sorted(payloads.items())},
        "controls": controls,
        "source_loss_resume": True,
        "checkpoint_revision": 2,
        "accepted_project_delivered": False,
        "composition_fidelity_verified": False,
        "limitation": (
            "Initial occurrence component; full checkpoint/public/review semantics remain live."
        ),
    }
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.artifacts, args.cache), indent=2))


if __name__ == "__main__":
    main()
