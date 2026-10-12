"""Bind actual source/matrix stage pointers and check independent finite arithmetic."""

import argparse
import hashlib
import json
import shlex
import shutil
import struct
from pathlib import Path
from typing import cast

import gamma_acceptance
import target_acceptance
from PIL import Image
from stage_evaluation import MATRIX_BOUND, verify_binding, verify_dispatch_abi, verify_stages
from target_observation import parse_event

from bookscan import intake, render
from bookscan.native_setup import checked, digest, tool


def build(output: Path) -> dict[str, object]:
    output.mkdir()
    gamma_acceptance.build(output / "base")
    source = Path(__file__).parent / "native/stage_evaluation_observer.c"
    compiler, pkg = tool("clang"), tool("pkg-config")
    flags = shlex.split(checked([str(pkg), "--cflags", "--libs", "lcms2"]))
    library = Path("/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib").resolve(strict=True)
    dependencies = checked([str(compiler), "-M", *flags, str(source)])
    subjects = {
        Path(p).resolve(strict=True)
        for p in shlex.split(dependencies.replace("\\\n", " ").split(":", 1)[1])
    } | {compiler.resolve(), pkg.resolve(), library, tool("otool").resolve()}
    before = {str(p): digest(p) for p in sorted(subjects)}
    disassembly = checked([str(tool("otool")), "-tvV", str(library)])
    offsets = verify_dispatch_abi(disassembly)
    (output / "native-disassembly.txt").write_text(disassembly)
    commands: list[list[str]] = []
    for name, defines in [
        ("stage-observer", []),
        ("wrong-stage-abi-observer", ["-DBOOKSCAN_TEST_WRONG_STAGE_ABI"]),
    ]:
        command = [
            str(compiler),
            "-Wall",
            "-Wextra",
            "-Werror",
            "-dynamiclib",
            *defines,
            *flags,
            str(source),
            "-o",
            str(output / (name + ".dylib")),
        ]
        checked(command)
        commands.append(command)
    after = {str(p): digest(p) for p in sorted(subjects)}
    assert before == after
    truth: dict[str, object] = {
        "meaning": "actual retained source/matrix EvalPtr calls, not observed pipeline traversal",
        "vectors": "65536 triples (v,65535-v,73*v%65536); every channel word once, not RGB cube",
        "source_oracle": "rational nearest-even binary32 normalized word, square, binary32 output",
        "matrix_oracle": (
            "exact rational row-major dot of profile-checked coefficients and source outputs"
        ),
        "matrix_arithmetic_bound": str(MATRIX_BOUND),
        "matrix_bound_domain": (
            "row L1<=2, no offset, [0,1] binary32 inputs; <=6 binary64 operations"
        ),
        "native_symbol_offsets": offsets,
        "complete_cmm_precision_verified": False,
        "build_commands": commands,
        "build_subjects_before": before,
        "build_subjects_after": after,
        "controls": [
            "foreign-pid",
            "wrong-handle",
            "wrong-lut",
            "wrong-stage",
            "wrong-symbol",
            "wrong-module",
            "wrong-fpcr",
            "wrong-input-bit",
            "wrong-source-bit",
            "erased-matrix-channel",
            "nonfinite-matrix",
            "missing-vector",
            "wrong-native-abi",
            "wrong-disassembly",
            "disabled-observation",
        ],
        "files": {
            str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*")) if p.is_file()
        },
    }
    (output / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    return truth


def capture(
    output: Path, pid: int, native: dict[str, object], disassembly: str
) -> dict[str, object]:
    offsets = verify_dispatch_abi(disassembly)
    gamma = gamma_acceptance.capture(output, pid, native)
    events = [parse_event(p.read_text(), pid) for p in sorted(output.glob("*-event.txt"))]
    selected = sorted(
        (e for e in events if e.input_format in (25, 262169)), key=lambda e: e.sequence
    )
    expected: set[str] = set()
    records: dict[str, object] = {}
    for event in selected:
        prefix = f"{pid}-{event.sequence}-stage"
        names = [prefix + "-dispatch.txt", prefix + "-vectors.bin"]
        expected.update(names)
        if any(not (output / name).is_file() for name in names):
            raise ValueError("Missing actual stage dispatch subjects")
        preceding = cast(dict[str, object], gamma[str(event.sequence)])
        pipeline = cast(dict[str, object], preceding["pipeline"])
        module = cast(dict[str, object], pipeline["evaluator_module"])
        raw = (output / f"{pid}-{event.sequence}-pipeline.txt").read_text().splitlines()[0].split()
        record = verify_binding(
            (output / names[0]).read_text(),
            event,
            pid,
            int(raw[8]),
            offsets,
            str(module["path"]),
        )
        stages = cast(list[dict[str, object]], pipeline["stages"])
        matrix = cast(list[str], stages[1]["matrix"])
        record["arithmetic"] = verify_stages((output / names[1]).read_bytes(), matrix)
        record["module"] = module
        record["preceding_gamma"] = preceding
        records[str(event.sequence)] = record
    if {p.name for p in output.glob("*-stage*")} != expected:
        raise ValueError("Extra/foreign stage dispatch subjects")
    return records


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    truth = json.loads((fixtures / "truth.json").read_text())
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    assert all(digest(Path(p)) == d for p, d in truth["build_subjects_before"].items())
    disassembly = (fixtures / "native-disassembly.txt").read_text()
    saved = intake.snapshot(
        fixtures / "base/base/base/base/base/source.pdf", output / "snapshot.pdf"
    )
    plain = render.render_page(saved, saved.pages[0], render.renderer_path())
    pid, native = target_acceptance.observe(
        [*plain.command[:-1], str(output / "observed")],
        fixtures / "stage-observer.dylib",
        output / "capture",
    )
    measured = capture(output / "capture", pid, native, disassembly)
    with Image.open(output / "observed.png") as image:
        assert (image.mode, image.size, image.tobytes()) == ("RGB", plain.size, plain.rgb)
    controls: dict[str, str] = {}
    for name in truth["controls"]:
        if name in {"wrong-native-abi", "wrong-disassembly", "disabled-observation"}:
            continue
        wrong = output / name
        shutil.copytree(output / "capture", wrong)
        header = sorted(wrong.glob("*-stage-dispatch.txt"))[0]
        lines = header.read_text().splitlines()
        if name in {"wrong-handle", "wrong-lut"}:
            fields = lines[0].split()
            column = 3 if name == "wrong-handle" else 4
            fields[column] = str(int(fields[column]) + 1)
            lines[0] = " ".join(fields)
        elif name == "wrong-stage":
            lines[1] = lines[1].replace("stage 0", "stage 1")
        elif name == "wrong-symbol":
            fields = lines[1].split()
            fields[6] = str(int(fields[6]) + 4)
            lines[1] = " ".join(fields)
        elif name == "wrong-module":
            lines[2] = "/foreign/little-cms2.dylib"
        elif name == "wrong-fpcr":
            lines[-1] = lines[-1].replace("fpcr 0", "fpcr 16777216")
        elif name in {
            "wrong-input-bit",
            "wrong-source-bit",
            "erased-matrix-channel",
            "nonfinite-matrix",
            "missing-vector",
        }:
            path = sorted(wrong.glob("*-stage-vectors.bin"))[0]
            data = bytearray(path.read_bytes())
            if name == "missing-vector":
                del data[-36:]
            elif name == "wrong-input-bit":
                data[36] ^= 1
            elif name == "wrong-source-bit":
                data[48] ^= 1
            else:
                data[28:32] = struct.pack(
                    "<I", 0 if name == "erased-matrix-channel" else 0x7FC00000
                )
            path.write_bytes(data)
        header.write_text("\n".join(lines) + "\n")
        # Each altered stage artifact still passes the independent preceding
        # gamma/profile/pipeline evidence. A foreign PID intentionally cannot.
        if name != "foreign-pid":
            gamma_acceptance.capture(wrong, pid, native)
        try:
            capture(wrong, pid + (name == "foreign-pid"), native, disassembly)
        except ValueError as error:
            controls[name] = str(error)
        else:
            raise ValueError("Wrong stage observation credited: " + name)
    try:
        verify_dispatch_abi(disassembly.replace("[x0, #0x30]", "[x0, #0x38]"))
    except ValueError as error:
        controls["wrong-disassembly"] = str(error)
    else:
        raise ValueError("Wrong stage disassembly credited")
    try:
        target_acceptance.observe(
            [*plain.command[:-1], str(output / "wrong-abi")],
            fixtures / "wrong-stage-abi-observer.dylib",
            output / "wrong-abi-capture",
        )
    except ValueError as error:
        if not str(error).startswith("Native observation failed 150:"):
            raise
        (output / "wrong-native-abi.txt").write_text(str(error))
        controls["wrong-native-abi"] = (
            "actual native child rejects offset before stage read/call, exit 150"
        )
    else:
        raise ValueError("Wrong actual stage ABI credited")
    dp, disabled = target_acceptance.observe(
        [*plain.command[:-1], str(output / "disabled")],
        fixtures / "stage-observer.dylib",
        output / "disabled-capture",
        enabled=False,
    )
    with Image.open(output / "disabled.png") as image:
        assert image.size == plain.size and image.tobytes() == plain.rgb
    try:
        capture(output / "disabled-capture", dp, disabled, disassembly)
    except ValueError as error:
        controls["disabled-observation"] = str(error)
    else:
        raise ValueError("Disabled stage observation credited")
    assert set(controls) == set(truth["controls"])
    saved.verify()
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    assert all(digest(Path(p)) == d for p, d in truth["build_subjects_before"].items())
    report: dict[str, object] = {
        "format": "BookScanBuilderStageEvaluationObservation",
        "version": 1,
        "source_sha256": saved.sha256,
        "rgb_sha256": hashlib.sha256(plain.rgb).hexdigest(),
        "pixels": list(plain.size),
        "stages": measured,
        "controls": controls,
        "native": native,
        "disabled_native": disabled,
        "raw_files": {p.name: digest(p) for p in sorted((output / "capture").iterdir())},
        "source_stage_evaluation_verified": True,
        "matrix_finite_arithmetic_verified": True,
        "pipeline_traversal_observed": False,
        "complete_cmm_precision_verified": False,
        "cairo_fidelity_verified": False,
        "runtime_resources_verified": False,
        "accepted_project_delivered": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["build", "check"])
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "check" and args.fixtures is None:
        parser.error("check requires --fixtures")
    print(
        json.dumps(
            build(args.artifacts) if args.mode == "build" else run(args.fixtures, args.artifacts),
            indent=2,
        )
    )
