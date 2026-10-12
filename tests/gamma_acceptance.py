"""Observe actual source gamma-2 curves; complete ICC fidelity remains unverified."""

import argparse
import hashlib
import json
import re
import shlex
import shutil
from pathlib import Path
from typing import cast

import pipeline_acceptance
import target_acceptance
from PIL import Image
from source_gamma import BOUND, verify_gamma
from target_observation import parse_event

from bookscan import intake, render
from bookscan.native_setup import checked, digest, tool


def build(output: Path) -> dict[str, object]:
    output.mkdir()
    pipeline_acceptance.build(output / "base")
    source = Path(__file__).parent / "native/source_gamma_observer.c"
    compiler, pkg = tool("clang"), tool("pkg-config")
    flags = shlex.split(checked([str(pkg), "--cflags", "--libs", "lcms2"]))
    dependencies = checked([str(compiler), "-M", *flags, str(source)])
    subjects = {
        Path(p).resolve(strict=True)
        for p in shlex.split(dependencies.replace("\\\n", " ").split(":", 1)[1])
    } | {
        compiler.resolve(),
        pkg.resolve(),
        Path("/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib").resolve(),
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
        str(output / "gamma-observer.dylib"),
    ]
    checked(command)
    after = {str(p): digest(p) for p in sorted(subjects)}
    assert before == after
    truth: dict[str, object] = {
        "meaning": "actual public source-curve evaluation on all normalized 16-bit inputs",
        "rounding": "exact rational nearest-even binary32 input then square then binary32 output",
        "declared_absolute_bound": str(BOUND),
        "bound_derivation": "input/output half-ulp <=2^-25 on [0,1]; 2*e+e^2+e",
        "complete_cmm_precision_verified": False,
        "pipeline_stage_dispatch_verified": False,
        "build_command": command,
        "build_subjects_before": before,
        "build_subjects_after": after,
        "controls": [
            "foreign-pid",
            "wrong-handle",
            "wrong-channel",
            "wrong-input-bit",
            "wrong-output-bit",
            "missing-code",
            "wrong-module",
            "disabled-observation",
        ],
        "files": {
            str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*")) if p.is_file()
        },
    }
    (output / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    return truth


def capture(output: Path, pid: int, native: dict[str, object]) -> dict[str, object]:
    pipelines = pipeline_acceptance.capture(output, pid, native)
    events = [parse_event(p.read_text(), pid) for p in sorted(output.glob("*-event.txt"))]
    selected = sorted(
        (e for e in events if e.input_format in (25, 262169)), key=lambda e: e.sequence
    )
    if {e.input_format for e in selected} != {25, 262169}:
        raise ValueError("Missing actual source gamma transforms")
    expected: set[str] = set()
    result: dict[str, object] = {}
    for event in selected:
        prefix = f"{pid}-{event.sequence}-gamma"
        names = [prefix + ".txt", prefix + "-module.txt", *[prefix + f"-{c}.bin" for c in range(3)]]
        expected.update(names)
        if any(not (output / name).is_file() for name in names):
            raise ValueError("Missing source gamma subjects")
        pipeline = cast(dict[str, object], pipelines[str(event.sequence)])
        record = verify_gamma(
            (output / names[0]).read_text(),
            event,
            pid,
            pipeline,
            {c: (output / (prefix + f"-{c}.bin")).read_bytes() for c in range(3)},
        )
        fields = (output / names[1]).read_text().splitlines()
        if (
            len(fields) != 2
            or re.fullmatch(
                rf"gamma-module-v1 {pid} {event.sequence} [1-9][0-9]* [1-9][0-9]*", fields[0]
            )
            is None
        ):
            raise ValueError("Foreign source gamma module binding")
        module = cast(dict[str, object], pipeline["evaluator_module"])
        if fields[1] != module["path"]:
            raise ValueError("Wrong source gamma module")
        record["module"] = module
        record["pipeline"] = pipeline
        result[str(event.sequence)] = record
    if {p.name for p in output.glob("*-gamma*")} != expected:
        raise ValueError("Extra/foreign source gamma subjects")
    return result


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    truth = json.loads((fixtures / "truth.json").read_text())
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    assert all(digest(Path(p)) == d for p, d in truth["build_subjects_before"].items())
    saved = intake.snapshot(fixtures / "base/base/base/base/source.pdf", output / "snapshot.pdf")
    plain = render.render_page(saved, saved.pages[0], render.renderer_path())
    pid, native = target_acceptance.observe(
        [*plain.command[:-1], str(output / "observed")],
        fixtures / "gamma-observer.dylib",
        output / "capture",
    )
    measured = capture(output / "capture", pid, native)
    with Image.open(output / "observed.png") as image:
        assert (image.mode, image.size, image.tobytes()) == ("RGB", plain.size, plain.rgb)
    controls: dict[str, str] = {}
    for name in truth["controls"]:
        if name == "disabled-observation":
            continue
        wrong = output / name
        shutil.copytree(output / "capture", wrong)
        header = sorted(wrong.glob("*-gamma.txt"))[0]
        lines = header.read_text().splitlines()
        if name == "wrong-handle":
            fields = lines[0].split()
            fields[3] = str(int(fields[3]) + 1)
            lines[0] = " ".join(fields)
        elif name == "wrong-channel":
            lines[1] = lines[1].replace("channel 0", "channel 1")
        elif name in {"wrong-input-bit", "wrong-output-bit", "missing-code"}:
            path = sorted(wrong.glob("*-gamma-0.bin"))[0]
            data = bytearray(path.read_bytes())
            if name == "missing-code":
                del data[-8:]
            else:
                data[8 + (4 if name == "wrong-output-bit" else 0)] ^= 1
            path.write_bytes(data)
        elif name == "wrong-module":
            path = sorted(wrong.glob("*-gamma-module.txt"))[0]
            fields = path.read_text().splitlines()
            fields[1] = "/foreign/little-cms2.dylib"
            path.write_text("\n".join(fields) + "\n")
        header.write_text("\n".join(lines) + "\n")
        try:
            capture(wrong, pid + (name == "foreign-pid"), native)
        except ValueError as error:
            controls[name] = str(error)
        else:
            raise ValueError("Wrong source gamma observation credited: " + name)
    dp, disabled = target_acceptance.observe(
        [*plain.command[:-1], str(output / "disabled")],
        fixtures / "gamma-observer.dylib",
        output / "disabled-capture",
        enabled=False,
    )
    with Image.open(output / "disabled.png") as image:
        assert image.size == plain.size and image.tobytes() == plain.rgb
    try:
        capture(output / "disabled-capture", dp, disabled)
    except ValueError as error:
        controls["disabled-observation"] = str(error)
    else:
        raise ValueError("Disabled source gamma observation credited")
    assert set(controls) == set(truth["controls"])
    saved.verify()
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    assert all(digest(Path(p)) == d for p, d in truth["build_subjects_before"].items())
    report: dict[str, object] = {
        "format": "BookScanBuilderSourceGammaObservation",
        "version": 1,
        "source_sha256": saved.sha256,
        "rgb_sha256": hashlib.sha256(plain.rgb).hexdigest(),
        "pixels": list(plain.size),
        "curves": measured,
        "controls": controls,
        "native": native,
        "disabled_native": disabled,
        "raw_files": {p.name: digest(p) for p in sorted((output / "capture").iterdir())},
        "source_curve_evaluation_verified": True,
        "pipeline_stage_dispatch_verified": False,
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
