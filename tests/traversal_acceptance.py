"""Observe actual cmsDoTransform full-LUT probes with restoring pass-through hooks."""

import argparse
import hashlib
import json
import shlex
import shutil
import struct
from pathlib import Path
from typing import cast

import stage_acceptance
import target_acceptance
from lut_traversal import verify_abi, verify_binding, verify_transform_dispatch, verify_vectors
from PIL import Image
from target_observation import parse_event

from bookscan import intake, render
from bookscan.native_setup import checked, digest, tool

CONTROLS = [
    "foreign-pid",
    "wrong-handle",
    "wrong-lut",
    "wrong-native-offset",
    "wrong-stage-chain",
    "wrong-input",
    "wrong-source",
    "wrong-matrix",
    "broken-link",
    "nonfinite-target",
    "out-of-domain-word",
    "wrong-output",
    "wrong-restored",
    "missing-vector",
    "extra-vector",
    "wrong-abi",
    "bypass-stage",
    "disabled-observation",
    "wrong-disassembly",
    "wrong-transform-dispatcher",
]


def build(output: Path) -> dict[str, object]:
    output.mkdir()
    stage_acceptance.build(output / "base")
    source = Path(__file__).parent / "native/lut_traversal_observer.c"
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
    offsets = verify_abi(disassembly)
    (output / "native-disassembly.txt").write_text(disassembly)
    commands: list[list[str]] = []
    for name, defines in [
        ("traversal-observer", []),
        ("wrong-abi", ["-DBOOKSCAN_TEST_WRONG_PIPELINE_ABI"]),
        ("bypass-stage", ["-DBOOKSCAN_TEST_BYPASS_STAGE"]),
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
        "meaning": "256 synchronous cmsDoTransform probes of each actual renderer-owned transform",
        "domain": "(v,255-v,73*v%256); every 8-bit channel once, not RGB cube",
        "observation": "one native Eval16Fn and ordered source/matrix/target EvalPtr per probe",
        "oracle": (
            "independent rational source/matrix arithmetic; exact links/formatter/restoration"
        ),
        "target_precision_verified": False,
        "saturation_arithmetic_verified": False,
        "renderer_pixel_traversal_observed": False,
        "complete_cmm_precision_verified": False,
        "native_symbol_offsets": offsets,
        "controls": CONTROLS,
        "build_commands": commands,
        "build_subjects_before": before,
        "build_subjects_after": after,
        "files": {
            str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*")) if p.is_file()
        },
    }
    (output / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    return truth


def capture(
    output: Path, pid: int, native: dict[str, object], disassembly: str
) -> dict[str, object]:
    offsets = verify_abi(disassembly)
    preceding = stage_acceptance.capture(output, pid, native, disassembly)
    events = [parse_event(p.read_text(), pid) for p in sorted(output.glob("*-event.txt"))]
    selected = sorted(
        (e for e in events if e.input_format in (25, 262169)), key=lambda e: e.sequence
    )
    expected: set[str] = set()
    records: dict[str, object] = {}
    for event in selected:
        prefix = f"{pid}-{event.sequence}-traversal"
        names = [prefix + ".txt", prefix + ".bin"]
        expected.update(names)
        if any(not (output / name).is_file() for name in names):
            raise ValueError("Missing actual traversal subjects")
        prior = cast(dict[str, object], preceding[str(event.sequence)])
        gamma = cast(dict[str, object], prior["preceding_gamma"])
        pipeline = cast(dict[str, object], gamma["pipeline"])
        module = cast(dict[str, object], pipeline["evaluator_module"])
        dispatch_offset = verify_transform_dispatch(
            (output / f"{pid}-{event.sequence}-evaluator-pipeline-module.txt").read_text(),
            event,
            pid,
            offsets,
            str(module["path"]),
        )
        lut = int(
            (output / f"{pid}-{event.sequence}-pipeline.txt").read_text().splitlines()[0].split()[8]
        )
        record = verify_binding(
            (output / names[0]).read_text(), event, pid, lut, offsets, str(module["path"])
        )
        old_binding = (
            (output / f"{pid}-{event.sequence}-stage-dispatch.txt").read_text().splitlines()
        )
        new_binding = (output / names[0]).read_text().splitlines()
        for index in range(2):
            if new_binding[3 + 2 * index].split()[:9] != old_binding[1 + 2 * index].split():
                raise ValueError("Traversal stages differ from preceding retained-stage binding")
        stages = cast(list[dict[str, object]], pipeline["stages"])
        record["vectors"] = verify_vectors(
            (output / names[1]).read_bytes(), cast(list[str], stages[1]["matrix"])
        )
        record["module"] = module
        record["transform_dispatcher"] = {"symbol": "_CachedXFORM", "offset": dispatch_offset}
        record["preceding_stages"] = prior
        records[str(event.sequence)] = record
    if {p.name for p in output.glob("*-traversal*")} != expected:
        raise ValueError("Extra/foreign traversal subjects")
    return records


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    truth = json.loads((fixtures / "truth.json").read_text())
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    assert all(digest(Path(p)) == d for p, d in truth["build_subjects_before"].items())
    source = fixtures / "base/base/base/base/base/base/source.pdf"
    saved = intake.snapshot(source, output / "snapshot.pdf")
    plain = render.render_page(saved, saved.pages[0], render.renderer_path())
    command = [*plain.command[:-1], str(output / "observed")]
    pid, native = target_acceptance.observe(
        command, fixtures / "traversal-observer.dylib", output / "capture"
    )
    disassembly = (fixtures / "native-disassembly.txt").read_text()
    measured = capture(output / "capture", pid, native, disassembly)
    with Image.open(output / "observed.png") as image:
        assert (image.mode, image.size, image.tobytes()) == ("RGB", plain.size, plain.rgb)
    controls: dict[str, str] = {}
    for name in CONTROLS[:15]:
        wrong = output / name
        shutil.copytree(output / "capture", wrong)
        header = sorted(wrong.glob("*-traversal.txt"))[0]
        lines = header.read_text().splitlines()
        if name in {"wrong-handle", "wrong-lut"}:
            fields = lines[0].split()
            column = 3 if name == "wrong-handle" else 4
            fields[column] = str(int(fields[column]) + 1)
            lines[0] = " ".join(fields)
        elif name == "wrong-native-offset":
            fields = lines[1].split()
            fields[1] = str(int(fields[1]) + 4)
            lines[1] = " ".join(fields)
        elif name == "wrong-stage-chain":
            fields = lines[3].split()
            fields[-1] = "0"
            lines[3] = " ".join(fields)
        elif name != "foreign-pid":
            path = sorted(wrong.glob("*-traversal.bin"))[0]
            data = bytearray(path.read_bytes())
            if name == "missing-vector":
                del data[-136:]
            elif name == "extra-vector":
                data.extend(data[:136])
            else:
                column = {
                    "wrong-input": 4,
                    "wrong-source": 10,
                    "wrong-matrix": 16,
                    "broken-link": 19,
                    "nonfinite-target": 22,
                    "out-of-domain-word": 25,
                    "wrong-output": 28,
                    "wrong-restored": 31,
                }[name]
                old = struct.unpack_from("<I", data, 17 * 136 + column * 4)[0]
                mask = {"wrong-matrix": 0x3F800000, "out-of-domain-word": 0x10000}.get(name, 1)
                value = 0x7FC00000 if name == "nonfinite-target" else old ^ mask
                struct.pack_into("<I", data, 17 * 136 + column * 4, value)
                if name in {"wrong-source", "wrong-matrix"}:
                    struct.pack_into("<I", data, 17 * 136 + (column + 3) * 4, value)
            path.write_bytes(data)
        header.write_text("\n".join(lines) + "\n")
        if name != "foreign-pid":
            stage_acceptance.capture(wrong, pid, native, disassembly)
        try:
            capture(wrong, pid + (name == "foreign-pid"), native, disassembly)
        except ValueError as error:
            controls[name] = str(error)
        else:
            raise ValueError("Wrong traversal credited: " + name)
    for name, code in [("wrong-abi", 160), ("bypass-stage", 162)]:
        try:
            target_acceptance.observe(
                [*command[:-1], str(output / name)],
                fixtures / (name + ".dylib"),
                output / (name + "-capture"),
            )
        except ValueError as error:
            if not str(error).startswith(f"Native observation failed {code}:"):
                raise
            (output / (name + ".txt")).write_text(str(error))
            controls[name] = f"actual child rejects with exit {code}"
        else:
            raise ValueError("Wrong actual traversal child credited: " + name)
    dp, disabled = target_acceptance.observe(
        [*command[:-1], str(output / "disabled")],
        fixtures / "traversal-observer.dylib",
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
        raise ValueError("Disabled traversal credited")
    try:
        verify_abi(disassembly.replace("ldp\tx2, x9, [x8, #0x10]", "ldp\tx2, x9, [x8, #0x18]"))
    except ValueError as error:
        controls["wrong-disassembly"] = str(error)
    else:
        raise ValueError("Wrong traversal disassembly credited")
    wrong = output / "wrong-transform-dispatcher"
    shutil.copytree(output / "capture", wrong)
    path = sorted(wrong.glob("*-evaluator-pipeline-module.txt"))[0]
    lines = path.read_text().splitlines()
    fields = lines[0].split()
    fields[4] = str(int(fields[4]) + 4)
    lines[0] = " ".join(fields)
    path.write_text("\n".join(lines) + "\n")
    stage_acceptance.capture(wrong, pid, native, disassembly)
    try:
        capture(wrong, pid, native, disassembly)
    except ValueError as error:
        controls["wrong-transform-dispatcher"] = str(error)
    else:
        raise ValueError("Wrong actual transform dispatcher credited")
    assert set(controls) == set(CONTROLS)
    saved.verify()
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    assert all(digest(Path(p)) == d for p, d in truth["build_subjects_before"].items())
    report: dict[str, object] = {
        "format": "BookScanBuilderLUTTraversalObservation",
        "version": 1,
        "source_sha256": saved.sha256,
        "rgb_sha256": hashlib.sha256(plain.rgb).hexdigest(),
        "pixels": list(plain.size),
        "traversals": measured,
        "controls": controls,
        "native": native,
        "disabled_native": disabled,
        "raw_files": {p.name: digest(p) for p in sorted((output / "capture").iterdir())},
        "pipeline_probe_traversal_observed": True,
        "renderer_pixel_traversal_observed": False,
        "complete_cmm_precision_verified": False,
        "cairo_fidelity_verified": False,
        "runtime_resources_verified": False,
        "accepted_project_delivered": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Test-owned macOS arm64 observer; use unused output directories. "
            "No complete ICC fidelity claim. Examples: "
            "python tests/traversal_acceptance.py build --artifacts /tmp/NEW-fixtures; "
            "python tests/traversal_acceptance.py check --fixtures /tmp/NEW-fixtures "
            "--artifacts /tmp/NEW-reading. Exit 0: checked, 1: failed, 2: usage."
        ),
    )
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
