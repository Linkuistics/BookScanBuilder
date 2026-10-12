"""Bind actual native imports to initial checkpoint meaning and source-loss resume.

This private runner exercises no public finite route, review action or exporter.
Its independent construction truth is inherited unchanged from assessment_acceptance.
"""

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import cast
from unittest.mock import patch

import assessment_acceptance

from bookscan import baseline_state, initial_import, project_header


def run(directory: Path, cache: Path) -> dict[str, object]:
    directory.mkdir()
    prior = assessment_acceptance.run(directory / "construction", cache)
    wanted = cast(list[dict[str, object]], cast(dict[str, object], prior["truth"])["pages"])
    config = directory / "fonts.conf"
    config.write_text(
        '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">'
        "<fontconfig><cachedir>/historical/unused-cache</cachedir></fontconfig>"
    )
    project = directory / "project"
    original = directory / "construction" / "snapshot.pdf"

    def verify(stores: project_header.Stores, value: dict[str, object]) -> None:
        baseline_state.restore(stores, value)

    progress = initial_import.Progress()
    result = initial_import.create(
        original, project, cache=cache, configuration_file=config, progress=progress
    )
    assert progress.committed and progress.result == result
    state = result.checkpoint.state
    values = cast(list[dict[str, object]], state["occurrences"])
    expected_pixels: list[str] = []
    prior_values = cast(list[dict[str, object]], prior["records"])
    for value, expected, before in zip(values, wanted, prior_values, strict=True):
        assessment_acceptance.verify_record(value, expected)
        assert value["rgb_sha256"] == before["rgb_sha256"]
        expected_pixels.append(cast(str, value["rgb_sha256"]))
    checkpoint_sha256 = result.checkpoint.sha256
    # Both original source and the actual copied Fontconfig/cache tree are gone.
    original.unlink()
    assert not (project / ".import-resources").exists()
    controls: list[dict[str, object]] = []

    def denied(*args: object, **kwargs: object) -> object:
        raise PermissionError("Historical native launch denied")

    with patch.object(subprocess, "Popen", denied):
        try:
            subprocess.Popen(["denied-control"])
        except PermissionError:
            pass
        else:
            raise AssertionError("Denied native control failed")
        with project_header.resume(project, verify_state=verify) as (stores, current):
            assert current.sha256 == checkpoint_sha256
            restored = baseline_state.restore(stores, current.state)
            assert [
                item.core.baseline.rgb_sha256 for item in restored.occurrences
            ] == expected_pixels
            for occurrence, expected in zip(restored.occurrences, expected_pixels, strict=True):
                assert (
                    hashlib.sha256(stores.images.read(occurrence.core.baseline)).hexdigest()
                    == expected
                )
            before = {path.name: path.read_bytes() for path in (project / "checkpoints").iterdir()}
            for ordinal in range(len(values)):
                wrong = copy.deepcopy(current.state)
                occurrence = cast(list[dict[str, object]], wrong["occurrences"])[ordinal]
                binding = cast(
                    dict[str, object],
                    cast(dict[str, object], occurrence["render"])["resource_binding"],
                )
                binding["environment_sha256"] = "0" * 64
                # Coherently hash all altered import facts to isolate association checks.
                changed = {key: wrong[key] for key in baseline_state.IMPORT_FIELDS}
                import_digest = hashlib.sha256(
                    json.dumps(
                        {
                            "domain": "BookScanBuilderReview-v1",
                            "value": {
                                "project_id": wrong["project_id"],
                                "import": changed,
                                "dispositions": [],
                                "inspections": [],
                            },
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()
                wrong["review_revision"] = import_digest
                try:
                    baseline_state.restore(stores, wrong)
                except baseline_state.BaselineStateError as error:
                    controls.append(
                        {
                            "id": occurrence["id"],
                            "fault": "mixed-render-context",
                            "code": error.code,
                            "exit_code": error.exit_code,
                        }
                    )
                else:
                    raise AssertionError("Mixed-context native record accepted")
                verify(stores, current.state)
            assert before == {
                path.name: path.read_bytes() for path in (project / "checkpoints").iterdir()
            }
    report: dict[str, object] = {
        "format": "BookScanBuilderInitialStateAcceptance",
        "version": 1,
        "truth_sha256": prior["truth_sha256"],
        "state": state,
        "baseline_sha256": expected_pixels,
        "controls": controls,
        "source_loss_resume": True,
        "resource_loss_resume": True,
        "native_resume_launch_denied": True,
        "checkpoint_sha256": checkpoint_sha256,
        "snapshot_id": state["snapshot_id"],
        "review_revision": state["review_revision"],
        "public_finite_delivery": False,
        "composition_fidelity_verified": False,
        "limitations": list(baseline_state.LIMITATIONS),
    }
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.artifacts, args.cache)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "truth_sha256",
                    "baseline_sha256",
                    "controls",
                    "source_loss_resume",
                    "resource_loss_resume",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
