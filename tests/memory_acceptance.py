"""Observe actual profile memory, separately from serialized data and fidelity."""

import argparse
import hashlib
import json
import re
import shlex
import shutil
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

import target_acceptance
from PIL import Image
from profile_memory import Memory, bind_memory
from target_observation import parse_event, read_target

from bookscan import intake, render
from bookscan.native_setup import checked, digest, tool


def build(output: Path) -> dict[str, object]:
    output.mkdir()
    target_acceptance.build(output / "base")
    source = Path(__file__).parent / "native/profile_memory_observer.c"
    compiler, pkg = tool("clang"), tool("pkg-config")
    flags = shlex.split(checked([str(pkg), "--cflags", "--libs", "lcms2"]))
    dependencies = checked([str(compiler), "-M", *flags, str(source)])
    subjects = {
        Path(p).resolve(strict=True)
        for p in shlex.split(dependencies.replace("\\\n", " ").split(":", 1)[1])
    }
    subjects |= {
        compiler.resolve(),
        pkg.resolve(),
        Path("/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib").resolve(strict=True),
    }
    before = {str(p): digest(p) for p in sorted(subjects)}
    command = [
        str(compiler),
        "-Wall",
        "-Wextra",
        "-Werror",
        "-dynamiclib",
        *flags,
        str(source),
        "-o",
        str(output / "memory-observer.dylib"),
    ]
    checked(command)
    after = {str(p): digest(p) for p in sorted(subjects)}
    assert before == after
    truth: dict[str, object] = {
        "meaning": "Bound public in-memory profile values; no evaluator/precision/fidelity claim",
        "build_command": command,
        "build_subjects_before": before,
        "build_subjects_after": after,
        "controls": [
            "disabled-observation",
            "foreign-pid",
            "missing-memory",
            "wrong-handle",
            "changed-target",
        ],
        "files": {
            str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*")) if p.is_file()
        },
    }
    (output / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    return truth


def semantic(memory: Memory | None) -> object:
    if memory is None:
        return {"unavailable": "unsupported-profile"}
    return {
        "matrix": [[str(v) for v in row] for row in memory.matrix],
        "white": [str(v) for v in memory.white],
        "curves": [
            {
                "kind": curve.kind,
                "domain": [str(v) for v in curve.domain],
                "parameters": [str(v) for v in curve.parameters],
                "estimated_table": list(curve.table),
            }
            for curve in memory.curves
        ],
    }


def capture(output: Path, pid: int, source: bytes) -> dict[str, object]:
    paths = sorted(output.glob("*-event.txt"), key=lambda p: int(p.name.split("-")[1]))
    events = [parse_event(p.read_text(), pid) for p in paths]
    texts: dict[tuple[int, int], str] = {}
    for path in output.glob("*-memory.txt"):
        match = re.fullmatch(r"([0-9]+)-([0-9]+)-([0-9]+)-memory.txt", path.name)
        if match is None or int(match[1]) != pid:
            raise ValueError("Foreign memory file")
        texts[(int(match[2]), int(match[3]))] = path.read_text()
    memories = bind_memory(texts, events, pid)
    # The original serialized observer validator checks its unchanged subset.
    serialized = output.parent / (output.name + "-serialized")
    serialized.mkdir()
    for path in output.iterdir():
        if path.suffix == ".icc" or path.name.endswith("-event.txt"):
            shutil.copyfile(path, serialized / path.name)
    target_semantic, _ = target_acceptance.capture(serialized, pid, source)
    expected = {p.name for p in serialized.iterdir()} | {
        f"{pid}-{s}-{h}-memory.txt" for s, h in texts
    }
    if {p.name for p in output.iterdir()} != expected:
        raise ValueError("Foreign/extra memory subject")
    deltas: dict[str, object] = {}
    for event in events:
        for role, handle in [("input", event.input_handle), ("target", event.target_handle)]:
            if not handle:
                continue
            key = f"{event.sequence}-{role}"
            memory = memories[key]
            if memory is None:
                continue
            encoded = read_target((output / f"{pid}-{event.sequence}-{role}.icc").read_bytes())
            matrix_difference = [
                [memory.matrix[i][j] - encoded.matrix[i][j] for j in range(3)] for i in range(3)
            ]
            curve_difference: list[list[Fraction]] = []
            for curve, (kind, parameters) in zip(memory.curves, encoded.curves, strict=True):
                if curve.kind != kind + 1:
                    raise ValueError("Memory/ICC curve type mismatch")
                curve_difference.append([a - b for a, b in zip(curve.parameters, parameters)])
            deltas[key] = {
                "matrix": [[str(v) for v in row] for row in matrix_difference],
                "curves": [[str(v) for v in row] for row in curve_difference],
            }
    return {
        "serialized": target_semantic,
        "memory": {key: semantic(value) for key, value in memories.items()},
        "exact_memory_minus_serialized": deltas,
        "raw": {
            "events": [asdict(e) for e in events],
            "files": {p.name: digest(p) for p in sorted(output.iterdir())},
        },
    }


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    truth = json.loads((fixtures / "truth.json").read_text())
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    # Rerun the unchanged observer's complete contract with the same base fixture.
    legacy = target_acceptance.run(fixtures / "base", output / "legacy")
    saved = intake.snapshot(fixtures / "base/source.pdf", output / "snapshot.pdf")
    plain = render.render_page(saved, saved.pages[0], render.renderer_path())
    command = [*plain.command[:-1], str(output / "observed")]
    pid, native = target_acceptance.observe(
        command, fixtures / "memory-observer.dylib", output / "capture"
    )
    captured = capture(output / "capture", pid, (fixtures / "base/input.icc").read_bytes())
    with Image.open(output / "observed.png") as image:
        assert (image.format, image.mode, image.size) == ("PNG", "RGB", plain.size)
        assert image.tobytes() == plain.rgb
    controls: dict[str, str] = {}
    for name in ["foreign-pid", "missing-memory", "wrong-handle", "changed-target"]:
        wrong = output / name
        shutil.copytree(output / "capture", wrong)
        memory_files = sorted(wrong.glob("*-memory.txt"))
        if name == "missing-memory":
            memory_files[0].unlink()
        elif name == "wrong-handle":
            path = memory_files[0]
            fields = path.read_text().splitlines()
            header = fields[0].split()
            header[3] = str(int(header[3]) + 1)
            fields[0] = " ".join(header)
            path.write_text("\n".join(fields) + "\n")
        elif name == "changed-target":
            event = next(
                parse_event(p.read_text(), pid)
                for p in wrong.glob("*-event.txt")
                if parse_event(p.read_text(), pid).input_format == 262169
            )
            path = wrong / f"{pid}-{event.sequence}-{event.target_handle}-memory.txt"
            lines = path.read_text().splitlines()
            fields = lines[1].split()
            fields[1] = (float.fromhex(fields[1]) + 1 / 65536).hex()
            lines[1] = " ".join(fields)
            path.write_text("\n".join(lines) + "\n")
        try:
            capture(
                wrong, pid + (name == "foreign-pid"), (fixtures / "base/input.icc").read_bytes()
            )
        except ValueError as error:
            if name == "changed-target" and str(error) != (
                "Missing/changed in-memory target creation binding"
            ):
                raise
            controls[name] = "rejected; actual profile/render bytes unchanged"
        else:
            raise ValueError(f"Incorrect memory evidence credited: {name}")
    disabled_pid, disabled = target_acceptance.observe(
        [*plain.command[:-1], str(output / "disabled")],
        fixtures / "memory-observer.dylib",
        output / "disabled-capture",
        enabled=False,
    )
    with Image.open(output / "disabled.png") as image:
        assert image.tobytes() == plain.rgb and image.size == plain.size
    try:
        capture(
            output / "disabled-capture", disabled_pid, (fixtures / "base/input.icc").read_bytes()
        )
    except ValueError:
        controls["disabled-observation"] = "rejected; actual uninjected RGB/geometry unchanged"
    else:
        raise ValueError("Disabled memory observation credited")
    assert set(controls) == set(truth["controls"])
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    saved.verify()
    report: dict[str, object] = {
        "format": "BookScanBuilderProfileMemoryObservation",
        "version": 1,
        "source_sha256": saved.sha256,
        "rgb_sha256": hashlib.sha256(plain.rgb).hexdigest(),
        "pixels": list(plain.size),
        "captured": captured,
        "legacy": legacy,
        "native": native,
        "disabled_native": disabled,
        "controls": controls,
        "profile_memory_observed": True,
        "cmm_pipeline_observed": False,
        "cmm_precision_verified": False,
        "cairo_fidelity_verified": False,
        "runtime_resources_verified": False,
        "accepted_project_delivered": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["build", "check"])
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "build":
        build(args.artifacts)
    else:
        if args.fixtures is None:
            parser.error("check requires --fixtures")
        run(args.fixtures, args.artifacts)
    print("Profile memory observation complete; CMM pipeline/precision/fidelity remain unverified")
