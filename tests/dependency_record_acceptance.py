"""Read actual native preflight metadata twice; no public saved-project claim."""

import argparse
import copy
import json
from dataclasses import asdict
from pathlib import Path
from typing import cast

from bookscan import dependencies, dependency_record
from bookscan.resources import ResourceBinding


def run(directory: Path, cache: Path) -> dict[str, object]:
    directory.mkdir()
    metadata = dependencies.preflight(cache)
    graphs = cast(dict[str, dict[str, object]], metadata["linked"])
    paths = sorted(
        {path for graph in graphs.values() for path in cast(dict[str, object], graph["files"])}
    )
    resources = ResourceBinding.capture([Path(path) for path in paths])
    binding = resources.record()
    checked = dependency_record.restore(metadata, binding)
    assert checked.renderer == Path(cast(dict[str, str], metadata["renderer"])["path"])
    resources.verify()
    controls: list[dict[str, object]] = []
    for fault in ("renderer", "build", "self-test", "linked-root", "library", "named-digest"):
        wrong, altered = copy.deepcopy(metadata), copy.deepcopy(binding)
        helper = cast(dict[str, object], wrong["helper"])
        if fault == "renderer":
            cast(dict[str, object], wrong["renderer"])["version"] = "future"
        elif fault == "build":
            helper["build_identity"] = "0" * 64
        elif fault == "self-test":
            cast(dict[str, object], helper["controls"]).pop("upright")
        elif fault == "linked-root":
            cast(dict[str, dict[str, object]], wrong["linked"])["pdftocairo"]["root"] = (
                "/foreign/pdftocairo"
            )
        elif fault == "library":
            cast(dict[str, object], cast(dict[str, object], helper["inputs"])["python_libraries"])[
                "Pillow"
            ] = "future"
        else:
            cast(list[dict[str, object]], altered["files"])[0]["sha256"] = "0" * 64
        try:
            dependency_record.restore(wrong, altered)
        except dependency_record.DependencyRecordError as error:
            controls.append({"fault": fault, "code": error.code, "exit_code": error.exit_code})
        else:
            raise AssertionError("Altered actual preflight metadata accepted")
        assert dependency_record.restore(metadata, binding) == checked
    resources.verify()
    report: dict[str, object] = {
        "format": "BookScanBuilderDependencyRecordAcceptance",
        "version": 1,
        "preflight": metadata,
        "binding": binding,
        "checked": asdict(checked),
        "controls": controls,
        "accepted_project_delivered": False,
        "composition_fidelity_verified": False,
        "limitation": (
            "Historical metadata consistency; complete checkpoint association remains live."
        ),
    }
    (directory / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.artifacts, args.cache)
    print(
        json.dumps({"report": str(args.artifacts / "report.json"), "controls": report["controls"]})
    )


if __name__ == "__main__":
    main()
