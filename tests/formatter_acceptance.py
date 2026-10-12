"""Bound actual RGB formatters and exhaustive codes; not full CMM fidelity."""

import argparse
import hashlib
import json
import re
import shlex
import shutil
from pathlib import Path
from typing import cast

import memory_acceptance
import target_acceptance
from PIL import Image
from target_observation import parse_event
from transform_formatters import verify_formatter

from bookscan import intake, render
from bookscan.native_setup import checked, digest, tool


def build(output: Path) -> dict[str, object]:
    output.mkdir()
    memory_acceptance.build(output / "base")
    source = Path(__file__).parent / "native/transform_formatter_observer.c"
    compiler, pkg = tool("clang"), tool("pkg-config")
    flags = shlex.split(checked([str(pkg), "--cflags", "--libs", "lcms2"]))
    dependencies = checked([str(compiler), "-M", *flags, str(source)])
    subjects = {
        Path(p).resolve(strict=True)
        for p in shlex.split(dependencies.replace("\\\n", " ").split(":", 1)[1])
    } | {
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
        str(output / "formatter-observer.dylib"),
    ]
    checked(command)
    after = {str(p): digest(p) for p in sorted(subjects)}
    assert before == after
    truth: dict[str, object] = {
        "meaning": "Actual completed-transform integer formatters; no intermediate CMM proof",
        "input_oracle": "v*257; distinct (v,255-v,73*v%256) per-channel permutations",
        "output_oracle": "(v+128)//257; distinct (v,65535-v,73*v%65536) permutations",
        "input_codes": 256,
        "output_codes": 65536,
        "maximum_output_error_8bit": "128/257",
        "limitation": "All per-channel codes in declared permutations, not all RGB tuples",
        "build_command": command,
        "build_subjects_before": before,
        "build_subjects_after": after,
        "controls": [
            "foreign-pid",
            "wrong-transform",
            "missing-formatter",
            "wrong-channel",
            "wrong-rounding",
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
    events = [parse_event(p.read_text(), pid) for p in sorted(output.glob("*-event.txt"))]
    selected = sorted(
        (e for e in events if e.input_format in (262169, 25)), key=lambda e: e.sequence
    )
    if {e.input_format for e in selected} != {262169, 25}:
        raise ValueError("Missing actual formatter transforms")
    records: dict[str, object] = {}
    expected: set[str] = set()
    for event in selected:
        name = f"{pid}-{event.sequence}-formatter.bin"
        expected.add(name)
        path = output / name
        if not path.is_file():
            raise ValueError("Missing formatter")
        data = path.read_bytes()
        records[str(event.sequence)] = verify_formatter(data, event, pid)
        function_line = data.split(b"\n", 2)[1].split()
        for role, address in zip(["input", "output"], function_line[1:], strict=True):
            module_name = f"{pid}-{event.sequence}-{role}-formatter-module.txt"
            expected.add(module_name)
            fields = (output / module_name).read_text().splitlines()
            match = re.fullmatch(
                rf"module-v1 {pid} {event.sequence} {role} {int(address)} ([1-9][0-9]*)",
                fields[0] if fields else "",
            )
            if len(fields) != 2 or match is None:
                raise ValueError("Foreign formatter module binding")
            modules = native.get("mapped_images")
            if not isinstance(modules, list):
                raise ValueError("Missing actual mapped modules")
            found = [
                cast(dict[str, object], m)
                for m in cast(list[object], modules)
                if isinstance(m, dict) and cast(dict[str, object], m).get("path") == fields[1]
            ]
            if len(found) != 1 or "little-cms2" not in fields[1]:
                raise ValueError("Unrelated formatter module")
            module = found[0]
            record = records[str(event.sequence)]
            assert isinstance(record, dict)
            record[role + "_module"] = {
                k: module[k] for k in ["path", "sha256", "mapped_uuid", "disk_uuid"]
            }
    if {p.name for p in output.glob("*-formatter*")} != expected:
        raise ValueError("Extra/foreign formatter subjects")
    return records


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    truth = json.loads((fixtures / "truth.json").read_text())
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    legacy = memory_acceptance.run(fixtures / "base", output / "legacy")
    saved = intake.snapshot(fixtures / "base/base/source.pdf", output / "snapshot.pdf")
    plain = render.render_page(saved, saved.pages[0], render.renderer_path())
    pid, native = target_acceptance.observe(
        [*plain.command[:-1], str(output / "observed")],
        fixtures / "formatter-observer.dylib",
        output / "capture",
    )
    measured = capture(output / "capture", pid, native)
    memory = output / "memory-subset"
    memory.mkdir()
    for p in (output / "capture").iterdir():
        if "-formatter" not in p.name:
            shutil.copyfile(p, memory / p.name)
    observed_memory = memory_acceptance.capture(
        memory, pid, (fixtures / "base/base/input.icc").read_bytes()
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
        if name == "disabled-observation":
            continue
        wrong = output / name
        shutil.copytree(output / "capture", wrong)
        path = sorted(wrong.glob("*-formatter.bin"))[0]
        data = path.read_bytes()
        head, functions, payload = data.split(b"\n", 2)
        if name == "missing-formatter":
            path.unlink()
        elif name == "wrong-transform":
            fields = head.split()
            fields[3] = str(int(fields[3]) + 1).encode()
            path.write_bytes(b" ".join(fields) + b"\n" + functions + b"\n" + payload)
        elif name in ("wrong-channel", "wrong-rounding"):
            altered = bytearray(payload)
            altered[0 if name == "wrong-channel" else 256 * 6 + 128 * 3] ^= 1
            path.write_bytes(head + b"\n" + functions + b"\n" + altered)
        elif name == "wrong-module":
            module_path = sorted(wrong.glob("*-formatter-module.txt"))[0]
            fields = module_path.read_text().splitlines()
            fields[1] = "/unobserved/little-cms2.dylib"
            module_path.write_text("\n".join(fields) + "\n")
        try:
            capture(wrong, pid + (name == "foreign-pid"), native)
        except ValueError as error:
            controls[name] = str(error)
        else:
            raise ValueError("Incorrect formatter evidence credited: " + name)
    disabled_pid, disabled = target_acceptance.observe(
        [*plain.command[:-1], str(output / "disabled")],
        fixtures / "formatter-observer.dylib",
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
        raise ValueError("Disabled formatter observation credited")
    assert set(controls) == set(truth["controls"])
    assert all(digest(fixtures / p) == d for p, d in truth["files"].items())
    saved.verify()
    report: dict[str, object] = {
        "format": "BookScanBuilderFormatterObservation",
        "version": 1,
        "source_sha256": saved.sha256,
        "rgb_sha256": hashlib.sha256(plain.rgb).hexdigest(),
        "pixels": list(plain.size),
        "formatters": measured,
        "memory": observed_memory,
        "legacy": legacy,
        "native": native,
        "disabled_native": disabled,
        "controls": controls,
        "raw_files": {p.name: digest(p) for p in sorted((output / "capture").iterdir())},
        "formatter_codes_verified": True,
        "cmm_pipeline_verified": False,
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
