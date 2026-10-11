"""Freeze/digest explicit preview cases. This runner never renders or writes a PDF output."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import cast

from test_preview import labels

from bookscan.prepare import plan
from bookscan.results import Json
from bookscan.selections import parse


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    collection = cast(Path, args.collection).resolve()
    artifacts = cast(Path, args.artifacts).resolve()
    if artifacts.is_relative_to(collection) or artifacts.exists():
        parser.error("Artifacts must be unused and outside the explicit collection.")
    artifacts.mkdir(parents=True)
    covers = labels(artifacts / "Labelled covers.pdf", 4, "K")
    content = labels(artifacts / "Labelled content.pdf", 2, "C")
    six = labels(artifacts / "Six pages.pdf", 6)
    fundamental = collection / "Raw Scans/Fundamentals of Musical Composition.pdf"
    schoenberg = collection / "Covers/SchoenbergComposition.pdf"
    norwegian = collection / (
        "Processed Books/Norwegian - An Essential Grammar (Routledge)/"
        "Norwegian - An Essential Grammar (Routledge).pdf"
    )
    counterpoint = collection / "Needing Cleanup/Counterpoint in Composition.pdf"
    algorithm = collection / "Processed Books/Algorithm Design/Algorithm Design.pdf"
    strings = collection / "Covers/Algorithms on Strings, Trees, and Sequence.pdf"
    cases: list[tuple[str, list[str], list[tuple[Path, int, str]]]] = [
        (
            "interleaved",
            [
                "--back",
                str(covers),
                "4",
                "--content",
                str(content),
                "2",
                "--front",
                str(covers),
                "1",
                "--content",
                str(covers),
                "3",
                "--content",
                str(content),
                "1",
            ],
            [
                (covers, 1, "front"),
                (content, 2, "content"),
                (covers, 3, "content"),
                (content, 1, "content"),
                (covers, 4, "back"),
            ],
        ),
        (
            "repeat-roles",
            ["--back", str(covers), "1", "--content", str(content), "--front", str(covers), "1"],
            [
                (covers, 1, "front"),
                (content, 1, "content"),
                (content, 2, "content"),
                (covers, 1, "back"),
            ],
        ),
        (
            "descending",
            ["--content", str(six), "6-4,1,4,!5"],
            [(six, n, "content") for n in (6, 4, 1, 4)],
        ),
        (
            "exclusions",
            ["--content", str(six), "!2,!5-6"],
            [(six, n, "content") for n in (1, 3, 4)],
        ),
        (
            "assembled",
            ["--content", str(content)],
            [(content, 1, "content"), (content, 2, "content")],
        ),
        (
            "music",
            ["--front", str(schoenberg), "1", "--content", str(fundamental), "40,140"],
            [(schoenberg, 1, "front"), (fundamental, 40, "content"), (fundamental, 140, "content")],
        ),
        ("norwegian", ["--content", str(norwegian), "20"], [(norwegian, 20, "content")]),
        ("counterpoint", ["--content", str(counterpoint), "20"], [(counterpoint, 20, "content")]),
        ("algorithm", ["--content", str(algorithm), "20"], [(algorithm, 20, "content")]),
        (
            "strings",
            ["--front", str(strings), "1", "--content", str(content), "--back", str(strings), "2"],
            [
                (strings, 1, "front"),
                (content, 1, "content"),
                (content, 2, "content"),
                (strings, 2, "back"),
            ],
        ),
    ]
    root = Path(__file__).resolve().parents[1]
    subjects = sorted(
        set(
            [
                *root.glob("src/bookscan/*.py"),
                *root.glob("tests/*.py"),
                root / "pyproject.toml",
                root / "uv.lock",
                root / "Taskfile.yml",
                root / "docs/specs/prepared-pdf.md",
                root / "docs/adr/prepared-page-hints.md",
                *(p for _, _, expected in cases for p, _, _ in expected),
            ]
        )
    )
    before = {str(path): digest(path) for path in subjects}
    records: list[Json] = []
    for name, selection_args, expected in cases:
        output = artifacts / f"{name}-planned.pdf"
        argv = [*selection_args, "--output", str(output), "--dry-run", "--json"]
        command = ["uv", "run", "--locked", "python", "-m", "bookscan.preview", *argv]
        listing = sorted(p.name for p in artifacts.iterdir())
        process = subprocess.run(command, capture_output=True, text=True, check=False)
        assert process.returncode == 0, process.stdout + process.stderr
        result = cast(dict[str, Json], json.loads(process.stdout))
        wanted: list[Json] = [
            dict(output_page=n, source=str(p), source_page=number, role=role)
            for n, (p, number, role) in enumerate(expected, 1)
        ]
        assert result["status"] == "planned" and result["pages"] == wanted
        assert not output.exists() and listing == sorted(p.name for p in artifacts.iterdir())
        projection = plan(parse(argv))
        if name == "algorithm":
            assert projection.version == (1, 7) and projection.extension_level == 3
        item: dict[str, Json] = {
            "case": name,
            "command": cast(list[Json], command),
            "result": result,
            "directory_unchanged": True,
            "geometry": [
                {
                    "boxes": [[str(v) for v in box] for box in p.geometry.boxes],
                    "rotate": p.geometry.rotate,
                    "user_unit": str(p.geometry.user_unit),
                    "raw_stream_sha256": [
                        hashlib.sha256(n.raw).hexdigest() for n in p.nodes if n.raw is not None
                    ],
                }
                for p in projection.projections
            ],
            "effective_version": ".".join(map(str, projection.version)),
            "adbe_extension_level": projection.extension_level,
        }
        records.append(item)
    after = {str(path): digest(path) for path in subjects}
    assert before == after
    versions: dict[str, Json] = {}
    for name, command in {
        "uv": ["uv", "--version"],
        "task": ["task", "--version"],
        "runtime": [
            "uv",
            "run",
            "--locked",
            "python",
            "-c",
            "import sys,pikepdf;print(sys.version);"
            "print(pikepdf.__version__);print(pikepdf.__libqpdf_version__)",
        ],
    }.items():
        versions[name] = subprocess.check_output(command, text=True).strip()
    report: dict[str, Json] = {
        "schema_version": 1,
        "scope": "preview only; no PDF/render acceptance",
        "artifacts": str(artifacts),
        "versions": versions,
        "digests_before": cast(dict[str, Json], before),
        "digests_after": cast(dict[str, Json], after),
        "cases": records,
    }
    (artifacts / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(artifacts / "report.json")


if __name__ == "__main__":
    main()
