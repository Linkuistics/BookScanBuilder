"""Actual native loader discovery; a test instrument, never accepted import preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import cast

import pikepdf
from PIL import Image
from runtime_loader import Log, parse_log, verify_uuid

from bookscan.native_setup import checked, digest, tool
from bookscan.render import renderer_path


def observe(command: list[str], *, enabled: bool = True) -> tuple[Log, dict[str, object], str]:
    """Own/reap this direct test child and retain its exact decoded stderr/PID.

    The private environment flag changes logging only. No production executor,
    interpreter settings, caches or persistent environment are changed.
    """
    environment = dict(os.environ)
    if enabled:
        environment["DYLD_PRINT_LIBRARIES"] = "1"
    else:
        environment.pop("DYLD_PRINT_LIBRARIES", None)
    # Apple documents image logging; this host's event grammar is characterized.
    # https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/LoggingDynamicLoaderEvents.html
    child = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        close_fds=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = child.communicate(timeout=120)
    except BaseException:
        child.kill()
        child.communicate()
        raise
    if child.returncode != 0:
        raise ValueError(f"Actual native child failed ({child.returncode}): {stderr.decode()}")
    raw = stderr.decode("utf-8")
    result = parse_log(raw, child.pid)
    record: dict[str, object] = {
        "pid": child.pid,
        "reaped": child.poll() is not None,
        "command": command,
        "returncode": child.returncode,
        "stdout": stdout.decode("utf-8"),
        "stderr": raw,
        # Opaque identity binds every inherited value without exposing credentials.
        "environment_sha256": hashlib.sha256(
            json.dumps(environment, sort_keys=True).encode()
        ).hexdigest(),
        "logging_override": {"DYLD_PRINT_LIBRARIES": "1"} if enabled else {},
    }
    return result, record, stdout.decode("utf-8")


def identities(log: Log) -> list[dict[str, object]]:
    """Mapped UUIDs bind observed events to unchanged non-system disk subjects.

    UUID is no cryptographic memory digest. Final acceptance freezes all discovered
    disk subjects across the entire run; shared-cache images retain reported UUIDs.
    """
    result: list[dict[str, object]] = []
    inspector = tool("otool")
    for path, mapped in dict(log.images).items():
        item: dict[str, object] = {"path": path, "mapped_uuid": mapped}
        if path.startswith(("/System/Library/", "/usr/lib/")):
            item["identity"] = "Reported mapped UUID; system shared-cache disk bytes not claimed"
        else:
            source = Path(path).resolve(strict=True)
            before = digest(source)
            commands = checked([str(inspector), "-arch", platform.machine(), "-l", str(source)])
            uuids = re.findall(r"\buuid (" + re.compile(r"[0-9A-F-]{36}").pattern + r")", commands)
            if len(uuids) != 1:
                raise ValueError(f"Missing or ambiguous native-architecture LC_UUID: {path}")
            verify_uuid(mapped, uuids[0])
            if digest(source) != before:
                raise ValueError(f"Changed native disk subject: {path}")
            item.update({"resolved": str(source), "sha256": before, "disk_uuid": uuids[0]})
        result.append(item)
    return result


def build_fixtures(output: Path) -> dict[str, object]:
    output.mkdir()
    native = Path(__file__).parent / "native"
    compiler = tool("clang")
    commands: list[list[str]] = []
    for name, source, flags in [
        ("probe", "loader_probe.c", []),
        ("leaf73.dylib", "loader_leaf.c", ["-dynamiclib", "-DLEAF_VALUE=73"]),
        ("leaf74.dylib", "loader_leaf.c", ["-dynamiclib", "-DLEAF_VALUE=74"]),
    ]:
        command = [
            str(compiler),
            "-Wall",
            "-Wextra",
            "-Werror",
            "-MD",
            "-MF",
            str(output / (name + ".d")),
            *flags,
            str(native / source),
            "-o",
            str(output / name),
        ]
        checked(command)
        commands.append(command)
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        page.Contents = pikepdf.Stream(pdf, b"1 0 0 rg 0 0 36 36 re f")
        pdf.save(output / "source.pdf")
    # Literal analytic truth is declared and saved before any renderer output.
    expected = (bytes([255, 0, 0]) * 150 + bytes([255, 255, 255]) * 150) * 150
    (output / "expected.rgb").write_bytes(expected)
    record: dict[str, object] = {
        "commands": commands,
        "render_size": [300, 150],
        "expected_rgb_sha256": hashlib.sha256(expected).hexdigest(),
        "expected_leaf_stdout": "73\n",
        "wrong_leaf_stdout": "74\n",
        "runtime_resources_verified": False,
        "files": {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output / "truth.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def run(fixtures: Path, output: Path) -> dict[str, object]:
    if platform.system() != "Darwin":
        raise ValueError("This characterized observation needs macOS; no cross-platform inference")
    output.mkdir()
    before = {p.name: digest(p) for p in sorted(fixtures.iterdir()) if p.is_file()}
    truth = json.loads((fixtures / "truth.json").read_text())
    if any(before[name] != expected for name, expected in truth["files"].items()):
        raise ValueError("Changed construction fixture; rebuild into an unused directory")
    controls: dict[str, str] = {}
    probe, leaf = fixtures / "probe", fixtures / "leaf73.dylib"
    dependencies = checked([str(tool("otool")), "-L", str(probe)])
    if "leaf73" in dependencies or "leaf74" in dependencies:
        raise ValueError("Post-launch leaf was statically linked; no dlopen control")
    wrong_log, wrong_record, wrong = observe([str(probe), str(fixtures / "leaf74.dylib")])
    if wrong != "74\n":
        raise ValueError("Wrong-leaf control did not expose its independently declared value")
    controls["actual-wrong-leaf"] = (
        "Rejected expected 73; actual dynamically loaded leaf returned 74"
    )
    try:
        observe([str(probe), str(leaf)], enabled=False)
    except ValueError as error:
        if "No image events" not in str(error):
            raise
        controls["actual-disabled-observation"] = str(error)
    else:
        raise ValueError("Disabled loader observation unexpectedly passed")
    dynamic, dynamic_record, returned = observe([str(probe), str(leaf)])
    if returned != "73\n" or str(leaf) not in dict(dynamic.images):
        raise ValueError("Missing actual post-launch leaf/value")
    for name, stderr, pid in [
        ("foreign-pid", cast(str, dynamic_record["stderr"]), cast(int, dynamic_record["pid"]) + 1),
        ("missing-events", "application warning\n", cast(int, dynamic_record["pid"])),
    ]:
        try:
            parse_log(stderr, pid)
        except ValueError as error:
            controls[name] = str(error)
        else:
            raise ValueError(f"Wrong observation passed: {name}")
    try:
        verify_uuid(dict(dynamic.images)[str(leaf)], "00000000-0000-0000-0000-000000000000")
    except ValueError as error:
        controls["wrong-mapped-uuid"] = str(error)
    else:
        raise ValueError("Wrong mapped UUID passed")
    renderer = renderer_path()
    prefix = output / "render"
    render_log, render_record, _ = observe(
        [
            str(renderer),
            "-singlefile",
            "-r",
            "300",
            "-W",
            "300",
            "-H",
            "150",
            "-png",
            "-antialias",
            "default",
            str(fixtures / "source.pdf"),
            str(prefix),
        ]
    )
    with Image.open(prefix.with_suffix(".png")) as image:
        if image.mode != "RGB" or image.size != (300, 150):
            raise ValueError("Wrong actual render geometry/mode")
        rgb = image.tobytes()
    if rgb != (fixtures / "expected.rgb").read_bytes():
        raise ValueError("Actual observed render differs from pre-output every-channel truth")
    python_log, python_record, stdout = observe(
        [
            sys.executable,
            str(Path(__file__).with_name("runtime_workload.py")),
        ]
    )
    workload = json.loads(stdout)
    for required in ["PIL._imaging", "PIL._imagingcms", "PIL._imagingft", "pikepdf._core"]:
        if required not in workload["modules"]:
            raise ValueError(f"Workload missed actual extension {required}")
    cases: dict[str, object] = {}
    for name, log, record in [
        ("wrong-leaf", wrong_log, wrong_record),
        ("dynamic-leaf", dynamic, dynamic_record),
        ("renderer", render_log, render_record),
        ("python", python_log, python_record),
    ]:
        cases[name] = {"observation": record, "parsed": asdict(log), "identities": identities(log)}
    after = {p.name: digest(p) for p in sorted(fixtures.iterdir()) if p.is_file()}
    if before != after:
        raise ValueError("Fixture/source changed during observation")
    report: dict[str, object] = {
        "format": "BookScanBuilderRuntimeLoaderObservation",
        "version": 1,
        "cases": cases,
        "controls": controls,
        "python_workload": workload,
        "fixture_digests_before": before,
        "fixture_digests_after": after,
        "render_rgb_sha256": hashlib.sha256(rgb).hexdigest(),
        "os_build": checked(["/usr/bin/sw_vers", "-buildVersion"]),
        "architecture": platform.machine(),
        "runtime_resources_verified": False,
        "limitation": "Observed UUID/path events only; not font/profile/config discovery, "
        "initialized-image state, memory-byte identity or all future runtime loads.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test-owned actual Mac loader evidence; no project/public preflight.",
        epilog="Exit 0: observation passed; 1: failure; 2: syntax. Unused outputs only. "
        "Examples: build --artifacts '/tmp/unused fixtures'; "
        "check --fixtures '/tmp/unused fixtures' --artifacts '/tmp/unused observation'.",
    )
    commands = parser.add_subparsers(dest="operation", required=True)
    build = commands.add_parser(
        "build", help="Declare/build private unused native/analytic fixtures"
    )
    build.add_argument("--artifacts", type=Path, required=True)
    check = commands.add_parser("check", help="Observe real native children against existing truth")
    check.add_argument("--fixtures", type=Path, required=True)
    check.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (
            build_fixtures(args.artifacts)
            if args.operation == "build"
            else run(args.fixtures, args.artifacts)
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(
            f"Runtime observation failed: {error}. Inspect the diagnostic; use unused outputs.",
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "report": str(args.artifacts),
                "runtime_resources_verified": False,
                "format": result.get("format", "RuntimeConstructionTruth"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
