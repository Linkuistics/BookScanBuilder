"""Bind controlled actual Cairo CMM conversions and cache reuse to independent truth."""

import argparse
import hashlib
import json
import shlex
import struct
import sys
import sysconfig
from pathlib import Path
from typing import cast

import composed_acceptance
import pikepdf
import target_acceptance
import traversal_acceptance
from lut_saturation import verify_native, verify_words
from PIL import Image
from pixel_traversal import verify_header, verify_image_binding, verify_pixels, verify_worker
from reversed_target import verify_target
from target_observation import parse_event

from bookscan import intake, render
from bookscan.native_setup import checked, digest, tool


def build(previous: Path, output: Path) -> dict[str, object]:
    """Keep prior fixture bytes exact; construct repeated-source/cache controls separately."""
    output.mkdir()
    old = json.loads((previous / "truth.json").read_text())
    if any(digest(previous / p) != h for p, h in old["files"].items()):
        raise ValueError("Changed preceding fixture")
    source = Path(__file__).parent / "native/pixel_traversal_observer.c"
    compiler, pkg = tool("clang"), tool("pkg-config")
    flags = shlex.split(checked([str(pkg), "--cflags", "--libs", "lcms2"]))
    dependencies = checked([str(compiler), "-M", *flags, str(source)])
    subjects = {
        Path(p).resolve(strict=True)
        for p in shlex.split(dependencies.replace("\\\n", " ").split(":", 1)[1])
    } | {compiler.resolve(), pkg.resolve()}
    subjects.update(previous / p for p in old["files"])
    subjects.update(Path(p) for p in old["build_subjects_before"])
    root = Path(__file__).resolve().parent.parent
    tracked = checked([str(tool("jj")), "--repository", str(root), "file", "list"]).splitlines()
    subjects.update(root / p for p in tracked)
    subjects.update(p for p in (root / ".venv").rglob("*") if p.is_file())
    subjects.update(p for p in Path(sysconfig.get_path("stdlib")).rglob("*") if p.is_file())
    subjects.update(
        {
            Path(sys.executable).resolve(),
            tool("jj").resolve(),
            tool("task").resolve(),
            tool("uv").resolve(),
        }
    )
    before = {str(p): digest(p) for p in sorted(subjects)}
    commands: list[list[str]] = []
    for name, defines in [
        ("pixel-observer", []),
        ("wrong-pixel-output", ["-DBOOKSCAN_TEST_WRONG_PIXEL_OUTPUT"]),
        ("wrong-pixel-abi", ["-DBOOKSCAN_TEST_WRONG_PIXEL_ABI"]),
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
    codes = (
        [(0, 0, 0)] * 2
        + [c for v in range(256) for c in [(v, 255 - v, v * 73 % 256)] * 2]
        + [(255, 255, 255)] * 2
    )
    samples = bytes(value for code in codes for value in code) * 2
    # Unfiltered, opaque, grid-aligned RGB; no font, mask or arbitrary-profile claim.
    with pikepdf.Pdf.open(previous / "base/base/base/base/base/base/source.pdf") as pdf:
        page = pdf.pages[0]
        image = page.obj.Resources.XObject.I
        image.write(samples)
        image.Width, image.Height = 516, 2
        image.Interpolate = False
        page.obj.MediaBox = pikepdf.Array([0, 0, 123.84, 0.48])
        page.obj.Contents = pikepdf.Stream(pdf, b"q 123.84 0 0 0.48 0 0 cm /I Do Q")
        pdf.save(output / "repeated.pdf", deterministic_id=True)
    (output / "source-rgb.bin").write_bytes(samples)
    after = {str(p): digest(p) for p in sorted(subjects)}
    if before != after:
        raise ValueError("Pixel fixture build subject changed")
    record: dict[str, object] = {
        "format": "BookScanBuilderActualCMMCallFixtures",
        "version": 1,
        "previous": str(previous),
        "previous_truth_sha256": digest(previous / "truth.json"),
        "predeclared_pixels": [516, 2],
        "expected_calls": 2,
        "expected_misses_per_call": 257,
        "expected_hits_per_call": 259,
        "meaning": "Opaque grid-aligned constructed ICC image; actual conversion calls and cache",
        "page_composition_fidelity_verified": False,
        "build_commands": commands,
        "build_subjects_before": before,
        "build_subjects_after": after,
        "files": {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output / "truth.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def capture(
    output: Path, pid: int, native: dict[str, object], disassembly: str
) -> dict[str, object]:
    """Earlier readers stay unchanged; verify every new actual conversion call."""
    earlier = traversal_acceptance.capture(output, pid, native, disassembly)
    calls: list[dict[str, object]] = []
    expected: set[str] = set()
    unused: list[int] = []
    for sequence, prior in earlier.items():
        event = parse_event((output / f"{pid}-{sequence}-event.txt").read_text(), pid)
        record = cast(dict[str, object], prior)
        stages = cast(dict[str, object], record["preceding_stages"])
        gamma = cast(dict[str, object], stages["preceding_gamma"])
        pipeline = cast(dict[str, object], gamma["pipeline"])
        chain = cast(list[dict[str, object]], pipeline["stages"])
        matrix = cast(list[str], chain[1]["matrix"])
        probe = (output / f"{pid}-{sequence}-traversal.bin").read_bytes()
        verify_words(probe)
        verify_target(probe, chain[2]["curves"])
        from composed_envelope import verify_composed

        verify_composed(probe, matrix)
        module_lines = (
            (output / f"{pid}-{sequence}-evaluator-pipeline-module.txt").read_text().splitlines()
        )
        base = int(module_lines[0].split()[5])
        lut = int(
            (output / f"{pid}-{sequence}-pipeline.txt").read_text().splitlines()[0].split()[8]
        )
        paths = list(output.glob(f"{pid}-{sequence}-pixels-*.txt"))
        numbers = sorted(int(p.stem.split("-")[-1]) for p in paths)
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("Missing/extra actual pixel call")
        if not numbers:
            unused.append(event.input_format)
        for call in numbers:
            prefix = f"{pid}-{sequence}-pixels-{call}"
            expected.update([prefix + ".txt", prefix + ".bin"])
            bound = verify_header(
                (output / (prefix + ".txt")).read_text(),
                event,
                pid,
                call,
                lut,
                module_lines[1],
                base,
            )
            data = (output / (prefix + ".bin")).read_bytes()
            result = verify_pixels(data, matrix, (0, 0, 0), (0, 0, 0), cast(int, bound["pixels"]))
            result.update(bound)
            calls.append(result)
    if {p.name for p in output.glob("*-pixels-*")} != expected or not calls:
        raise ValueError("Missing/extra actual pixel subjects")
    return {"calls": calls, "created_formats_without_observed_calls": unused, "earlier": earlier}


def run(fixtures: Path, output: Path) -> dict[str, object]:
    """Fresh A/B runs, with native and recorded-data controls and exact source/PNG links."""
    output.mkdir()
    truth = json.loads((fixtures / "truth.json").read_text())
    previous = Path(truth["previous"])
    if digest(previous / "truth.json") != truth["previous_truth_sha256"]:
        raise ValueError("Changed preceding truth")
    if any(digest(fixtures / p) != h for p, h in truth["files"].items()):
        raise ValueError("Changed pixel fixture")
    upstream = composed_acceptance.run(previous, output / "upstream")
    subjects = cast(dict[str, str], upstream["read_subjects_before"])
    subjects = {
        **subjects,
        **{str(p): digest(p) for p in fixtures.iterdir() if p.is_file()},
        **truth["build_subjects_before"],
    }
    if any(digest(Path(p)) != h for p, h in subjects.items()):
        raise ValueError("Pixel subjects differ before measurement")
    disassembly = (previous / "native-disassembly.txt").read_text().strip()
    worker = verify_worker(disassembly)
    saturation = verify_native(
        disassembly, (output / "upstream/upstream/upstream/native-constants.txt").read_text()
    )
    records: dict[str, dict[str, object]] = {}
    native_records: dict[str, object] = {}
    for label in ["a", "b"]:
        directory = output / label
        directory.mkdir()
        saved = intake.snapshot(fixtures / "repeated.pdf", directory / "snapshot.pdf")
        plain = render.render_page(saved, saved.pages[0], render.renderer_path())
        command = [*plain.command[:-1], str(directory / "observed")]
        pid, native = target_acceptance.observe(
            command, fixtures / "pixel-observer.dylib", directory / "capture"
        )
        measured = capture(directory / "capture", pid, native, disassembly)
        calls = cast(list[dict[str, object]], measured["calls"])
        if len(calls) != 2 or any(
            (c["pixels"], c["misses"], c["hits"], c["input_format"]) != (516, 257, 259, 25)
            for c in calls
        ):
            raise ValueError("Actual repeated renderer-call inventory differs")
        source = (fixtures / "source-rgb.bin").read_bytes()
        pixel_data = [
            p.read_bytes() for p in sorted((directory / "capture").glob("*-pixels-*.bin"))
        ]
        inputs = b"".join(
            bytes(c for row in struct.iter_unpack("<34I", raw) for c in row[1:4])
            for raw in pixel_data
        )
        converted = b"".join(
            bytes(c for row in struct.iter_unpack("<34I", raw) for c in row[28:31])
            for raw in pixel_data
        )
        with Image.open(directory / "observed.png") as image:
            verify_image_binding(
                source,
                inputs,
                converted,
                image.mode,
                image.size,
                image.tobytes(),
                expected_size=(516, 2),
            )
        if plain.size != (516, 2) or plain.rgb != converted:
            raise ValueError("Injected/plain complete rendered pixels differ")
        saved.verify()
        records[label] = {
            "calls": calls,
            "source_rgb_sha256": hashlib.sha256(source).hexdigest(),
            "render_rgb_sha256": hashlib.sha256(converted).hexdigest(),
            "created_formats_without_observed_calls": measured[
                "created_formats_without_observed_calls"
            ],
        }
        native_records[label] = native
        (directory / "capture-report.json").write_text(json.dumps(measured, indent=2) + "\n")
    if records["a"] != records["b"]:
        raise ValueError("Actual pixel/cache per-item rerun differs")
    with Image.open(output / "a/observed.png") as image:
        expected_rgb = image.tobytes()
    controls: dict[str, str] = {}
    # Alter one source-associated pixel, rendered fine feature, or physical canvas
    # while preserving every actual CMM/earlier arithmetic observation.
    source = (fixtures / "source-rgb.bin").read_bytes()
    for name, changed_source, size, changed_rgb in [
        ("wrong-source-binding", source[:-3] + b"\0\0\0", (516, 2), expected_rgb),
        (
            "erased-rendered-feature",
            source,
            (516, 2),
            expected_rgb[:6] + b"\xff\xff\xff" + expected_rgb[9:],
        ),
        ("wrong-rendered-canvas", source, (258, 4), expected_rgb),
    ]:
        try:
            verify_image_binding(
                changed_source,
                source,
                expected_rgb,
                "RGB",
                size,
                changed_rgb,
                expected_size=(516, 2),
            )
        except ValueError as error:
            controls[name] = str(error)
        else:
            raise ValueError("Wrong constructed image binding credited")
    directory = output / "a"
    path = sorted((directory / "capture").glob("*-pixels-1.bin"))[0]
    data = path.read_bytes()
    seq = path.name.split("-")[1]
    native = cast(dict[str, object], native_records["a"])
    prior = capture(directory / "capture", cast(int, native["pid"]), native, disassembly)
    earlier = cast(dict[str, dict[str, object]], prior["earlier"])[seq]
    chain = cast(
        dict[str, object],
        cast(
            dict[str, object],
            cast(dict[str, object], earlier["preceding_stages"])["preceding_gamma"],
        )["pipeline"],
    )["stages"]
    matrix = cast(list[str], cast(list[dict[str, object]], chain)[1]["matrix"])
    for name, index, column, mask in [
        ("wrong-source", 2, 10, 0x3F800000),
        ("wrong-matrix", 2, 16, 0x3F800000),
        ("wrong-target", 2, 22, 0x3F800000),
        ("wrong-word", 2, 25, 2),
        ("wrong-byte", 2, 28, 2),
        ("wrong-hit-reuse", 3, 25, 2),
        ("wrong-hit-count", 3, 31, 1),
        ("wrong-order", 2, 0, 1),
    ]:
        wrong = bytearray(data)
        old = struct.unpack_from("<I", wrong, index * 136 + column * 4)[0]
        struct.pack_into("<I", wrong, index * 136 + column * 4, old ^ mask)
        (output / (name + ".bin")).write_bytes(wrong)
        try:
            verify_pixels(bytes(wrong), matrix, (0, 0, 0), (0, 0, 0), 516)
        except ValueError as error:
            controls[name] = str(error)
        else:
            raise ValueError("Wrong actual pixel credited: " + name)
    cmd = cast(list[str], native["command"])
    wp, wn = target_acceptance.observe(
        [*cmd[:-1], str(output / "wrong-native")],
        fixtures / "wrong-pixel-output.dylib",
        output / "wrong-native-capture",
    )
    traversal_acceptance.capture(output / "wrong-native-capture", wp, wn, disassembly)
    try:
        capture(output / "wrong-native-capture", wp, wn, disassembly)
    except ValueError as error:
        controls["actual-wrong-output-earlier-readers-pass"] = str(error)
    else:
        raise ValueError("Actual wrong-output observer credited")
    with Image.open(output / "wrong-native.png") as image:
        if image.tobytes() != expected_rgb:
            raise ValueError("Wrong observer changed renderer pixels")
    try:
        target_acceptance.observe(
            [*cmd[:-1], str(output / "wrong-abi")],
            fixtures / "wrong-pixel-abi.dylib",
            output / "wrong-abi-capture",
        )
    except ValueError as error:
        if not str(error).startswith("Native observation failed 180:"):
            raise
        (output / "wrong-abi.txt").write_text(str(error))
        controls["actual-wrong-abi"] = "reaped actual child exit 180"
    else:
        raise ValueError("Wrong native pixel ABI credited")
    dp, dn = target_acceptance.observe(
        [*cmd[:-1], str(output / "disabled")],
        fixtures / "pixel-observer.dylib",
        output / "disabled-capture",
        enabled=False,
    )
    try:
        capture(output / "disabled-capture", dp, dn, disassembly)
    except ValueError as error:
        controls["disabled-observation"] = str(error)
    else:
        raise ValueError("Disabled actual observation credited")
    with Image.open(output / "disabled.png") as image:
        if image.tobytes() != expected_rgb:
            raise ValueError("Disabled renderer pixels differ")
    for name, old, new in [
        ("wrong-worker-instruction", "sub\tsp", "add\tsp"),
        ("wrong-native-cache-load", "#0x30", "#0x38"),
    ]:
        wrong = disassembly.replace(old, new)
        try:
            verify_worker(wrong)
        except ValueError as error:
            controls[name] = str(error)
        else:
            raise ValueError("Wrong native worker instructions credited")
    after = {p: digest(Path(p)) for p in subjects}
    if subjects != after:
        raise ValueError("Pixel measurement subject changed")
    report: dict[str, object] = {
        "format": "BookScanBuilderActualControlledCMMCalls",
        "version": 1,
        "read_subjects_before": subjects,
        "read_subjects_after": after,
        "upstream": upstream,
        "worker": worker,
        "saturation": saturation,
        "records": records,
        "native": native_records,
        "controls": controls,
        "per_item_rerun_equal": True,
        "actual_controlled_conversion_and_cache_verified": True,
        "aligned_constructed_source_and_png_link_verified": True,
        "arbitrary_icc_verified": False,
        "general_page_composition_verified": False,
        "runtime_resources_verified": False,
        "accepted_project_delivered": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Test-owned macOS arm64 acceptance. Build from unchanged traversal fixtures; "
            "check new pixel fixtures. Use unused directories. Exit 0 checked, 1 failed, "
            "2 usage. No general ICC/composition claim. Examples: "
            "python tests/pixel_acceptance.py build --fixtures /tmp/traversal-fixtures "
            "--artifacts /tmp/NEW-pixel-fixtures; python tests/pixel_acceptance.py check "
            "--fixtures /tmp/NEW-pixel-fixtures --artifacts /tmp/NEW-reading. "
            "On failure retain diagnostics, repair the named condition and use a new directory."
        ),
    )
    parser.add_argument("mode", choices=["build", "check"])
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    result = (
        build(args.fixtures, args.artifacts)
        if args.mode == "build"
        else run(args.fixtures, args.artifacts)
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k
                not in {
                    "records",
                    "upstream",
                    "native",
                    "read_subjects_before",
                    "read_subjects_after",
                    "build_subjects_before",
                    "build_subjects_after",
                }
            },
            indent=2,
        )
    )
