"""Observe actual final stages on this exact native ABI; no full CMM precision verdict."""

import argparse
import hashlib
import json
import re
import shlex
import shutil
from pathlib import Path
from typing import cast

import formatter_acceptance
import memory_acceptance
import target_acceptance
from PIL import Image
from profile_memory import bind_memory
from target_observation import parse_event
from transform_pipeline import parse_pipeline, verify_abi, verify_profile_stages

from bookscan import intake, render
from bookscan.native_setup import checked, digest, tool


def build(output: Path) -> dict[str, object]:
    output.mkdir()
    formatter_acceptance.build(output / "base")
    source = Path(__file__).parent / "native/transform_pipeline_observer.c"
    compiler, pkg = tool("clang"), tool("pkg-config")
    flags = shlex.split(checked([str(pkg), "--cflags", "--libs", "lcms2"]))
    library = Path("/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib").resolve(strict=True)
    disassembly = checked([str(tool("otool")), "-tvV", str(library)])
    verify_abi(disassembly)
    (output / "native-disassembly.txt").write_text(disassembly)
    dependencies = checked([str(compiler), "-M", *flags, str(source)])
    subjects = {
        Path(p).resolve(strict=True)
        for p in shlex.split(dependencies.replace("\\\n", " ").split(":", 1)[1])
    } | {compiler.resolve(), pkg.resolve(), library, tool("otool").resolve()}
    before = {str(p): digest(p) for p in sorted(subjects)}
    commands: list[list[str]] = []
    for name, defines in [
        ("pipeline-observer", []),
        ("wrong-abi-observer", ["-DBOOKSCAN_TEST_WRONG_ABI"]),
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
        "meaning": "Exact 2.19.1 arm64 test ABI and final stage binding, not a product API",
        "source_header_url": "https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/lcms2_internal.h",
        "native_lut_offset": 112,
        "native_worker_offset": 8,
        "source_stage_oracle": "exact original/reversed curve parameters, T^-1*S rational algebra",
        "matrix_envelope": "64*2^-53*max(1,||T^-1||*||S||)*max(1,cond(T)); cond(T)<=16",
        "probe_inputs": "256 RGB triples (v,255-v,73*v%256); not the complete RGB cube",
        "probe_oracle": "integer Eval16 packing (word+128)//257 equals actual cmsDoTransform",
        "build_commands": commands,
        "build_subjects_before": before,
        "build_subjects_after": after,
        "controls": [
            "foreign-pid",
            "wrong-transform",
            "missing-pipeline",
            "unsupported-stage",
            "wrong-matrix",
            "wrong-curve",
            "wrong-probe",
            "wrong-module",
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


def capture(output: Path, pid: int, native: dict[str, object]) -> dict[str, object]:
    events = [parse_event(p.read_text(), pid) for p in sorted(output.glob("*-event.txt"))]
    selected = sorted(
        (e for e in events if e.input_format in (262169, 25)), key=lambda e: e.sequence
    )
    if {e.input_format for e in selected} != {262169, 25}:
        raise ValueError("Missing actual final pipelines")
    texts: dict[tuple[int, int], str] = {}
    for path in output.glob("*-memory.txt"):
        match = re.fullmatch(rf"{pid}-([0-9]+)-([0-9]+)-memory.txt", path.name)
        if match is None:
            raise ValueError("Foreign memory identity")
        texts[(int(match[1]), int(match[2]))] = path.read_text()
    memories = bind_memory(texts, events, pid)
    expected: set[str] = set()
    records: dict[str, object] = {}
    for event in selected:
        name = f"{pid}-{event.sequence}-pipeline.txt"
        expected.add(name)
        path = output / name
        if not path.is_file():
            raise ValueError("Missing final pipeline data")
        record = parse_pipeline(path.read_text(), event, pid)
        source, target = memories[f"{event.sequence}-input"], memories[f"{event.sequence}-target"]
        if source is None or target is None:
            raise ValueError("Missing pipeline profile-memory oracle")
        record["profile_stage_comparison"] = verify_profile_stages(record, source, target)
        name = f"{pid}-{event.sequence}-evaluator-pipeline-module.txt"
        expected.add(name)
        fields = (output / name).read_text().splitlines()
        if (
            len(fields) != 2
            or re.fullmatch(
                rf"module-v1 {pid} {event.sequence} evaluator [1-9][0-9]* [1-9][0-9]*", fields[0]
            )
            is None
        ):
            raise ValueError("Foreign evaluator module binding")
        modules = native.get("mapped_images")
        if not isinstance(modules, list):
            raise ValueError("Missing actual mapped modules")
        found = [
            cast(dict[str, object], m)
            for m in cast(list[object], modules)
            if isinstance(m, dict) and cast(dict[str, object], m).get("path") == fields[1]
        ]
        if len(found) != 1 or "little-cms2" not in fields[1]:
            raise ValueError("Unrelated final evaluator module")
        record["evaluator_module"] = {
            k: found[0][k] for k in ["path", "sha256", "mapped_uuid", "disk_uuid"]
        }
        records[str(event.sequence)] = record
    if {p.name for p in output.glob("*-pipeline*")} != expected:
        raise ValueError("Extra/foreign pipeline subjects")
    return records


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    truth = json.loads((fixtures / "truth.json").read_text())
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    assert all(digest(Path(p)) == d for p, d in truth["build_subjects_before"].items())
    verify_abi((fixtures / "native-disassembly.txt").read_text())
    legacy = formatter_acceptance.run(fixtures / "base", output / "legacy")
    saved = intake.snapshot(fixtures / "base/base/base/source.pdf", output / "snapshot.pdf")
    plain = render.render_page(saved, saved.pages[0], render.renderer_path())
    pid, native = target_acceptance.observe(
        [*plain.command[:-1], str(output / "observed")],
        fixtures / "pipeline-observer.dylib",
        output / "capture",
    )
    measured = capture(output / "capture", pid, native)
    memory = output / "memory-subset"
    memory.mkdir()
    for p in (output / "capture").iterdir():
        if "-pipeline" not in p.name:
            shutil.copyfile(p, memory / p.name)
    memory_record = memory_acceptance.capture(
        memory, pid, (fixtures / "base/base/base/input.icc").read_bytes()
    )
    with Image.open(output / "observed.png") as image:
        assert (image.format, image.mode, image.size, image.tobytes()) == (
            "PNG",
            "RGB",
            plain.size,
            plain.rgb,
        )
    controls: dict[str, str] = {}
    for name in truth["controls"]:
        if name in {"disabled-observation", "wrong-native-abi", "wrong-disassembly"}:
            continue
        wrong = output / name
        shutil.copytree(output / "capture", wrong)
        path = sorted(wrong.glob("*-pipeline.txt"))[0]
        lines = path.read_text().splitlines()
        if name == "missing-pipeline":
            path.unlink()
        elif name == "wrong-transform":
            fields = lines[0].split()
            fields[3] = str(int(fields[3]) + 1)
            lines[0] = " ".join(fields)
        elif name == "unsupported-stage":
            lines[2] = lines[2].replace("1668707188", "0")
        elif name == "wrong-matrix":
            index = next(i for i, line in enumerate(lines) if line.startswith("matrix "))
            fields = lines[index].split()
            fields[2] = "0x1p+1"
            lines[index] = " ".join(fields)
        elif name == "wrong-curve":
            lines[3] = lines[3].replace("0x1p+1", "0x1p+0")
        elif name == "wrong-probe":
            fields = lines[-1].split()
            fields[-1] = str((int(fields[-1]) + 1) % 256)
            lines[-1] = " ".join(fields)
        elif name == "wrong-module":
            module = sorted(wrong.glob("*-pipeline-module.txt"))[0]
            fields = module.read_text().splitlines()
            fields[1] = "/foreign/little-cms2.dylib"
            module.write_text("\n".join(fields) + "\n")
        if path.exists():
            path.write_text("\n".join(lines) + "\n")
        try:
            capture(wrong, pid + (name == "foreign-pid"), native)
        except ValueError as error:
            controls[name] = str(error)
        else:
            raise ValueError("Incorrect pipeline evidence credited: " + name)
    bad = (fixtures / "native-disassembly.txt").read_text().replace("[x19, #0x70]", "[x19, #0x78]")
    try:
        verify_abi(bad)
    except ValueError as error:
        controls["wrong-disassembly"] = str(error)
    else:
        raise ValueError("Wrong native disassembly credited")
    try:
        target_acceptance.observe(
            [*plain.command[:-1], str(output / "wrong-abi")],
            fixtures / "wrong-abi-observer.dylib",
            output / "wrong-abi-capture",
        )
    except ValueError as error:
        if not str(error).startswith("Native observation failed 110:"):
            raise
        (output / "wrong-native-abi.txt").write_text(str(error))
        controls["wrong-native-abi"] = (
            "actual native child rejects offset before Lut read, exit 110"
        )
    else:
        raise ValueError("Wrong actual native ABI credited")
    disabled_pid, disabled = target_acceptance.observe(
        [*plain.command[:-1], str(output / "disabled")],
        fixtures / "pipeline-observer.dylib",
        output / "disabled-capture",
        enabled=False,
    )
    with Image.open(output / "disabled.png") as image:
        assert image.size == plain.size and image.tobytes() == plain.rgb
    try:
        capture(output / "disabled-capture", disabled_pid, disabled)
    except ValueError as error:
        controls["disabled-observation"] = str(error)
    else:
        raise ValueError("Disabled pipeline observation credited")
    assert set(controls) == set(truth["controls"])
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    assert all(digest(Path(p)) == d for p, d in truth["build_subjects_before"].items())
    saved.verify()
    report: dict[str, object] = {
        "format": "BookScanBuilderTransformPipelineObservation",
        "version": 1,
        "source_sha256": saved.sha256,
        "rgb_sha256": hashlib.sha256(plain.rgb).hexdigest(),
        "pixels": list(plain.size),
        "pipelines": measured,
        "memory": memory_record,
        "legacy": legacy,
        "native": native,
        "disabled_native": disabled,
        "controls": controls,
        "raw_files": {p.name: digest(p) for p in sorted((output / "capture").iterdir())},
        "final_pipeline_observed": True,
        "test_abi_portable": False,
        "cmm_precision_verified": False,
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
