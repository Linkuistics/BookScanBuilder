"""Observe actual Cairo ICC target handles/serialized coefficients; no fidelity verdict."""

import argparse
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

import pikepdf
from icc_fixtures import profile
from PIL import Image
from runtime_acceptance import identities
from runtime_loader import parse_log
from target_observation import bind_capture

from bookscan import intake, render, samples
from bookscan.native_setup import checked, digest, tool


def build(output: Path) -> dict[str, object]:
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("Observer characterized for this macOS arm64 host only")
    output.mkdir()
    compiler, pkg = tool("clang"), tool("pkg-config")
    source = Path(__file__).parent / "native/target_observer.c"
    flags = shlex.split(checked([str(pkg), "--cflags", "--libs", "lcms2"]))
    if checked([str(pkg), "--modversion", "lcms2"]) != "2.19":
        raise ValueError("Unsupported observer-linked LittleCMS headers/library")
    dependencies = checked([str(compiler), "-M", *flags, str(source)])
    headers = [
        Path(p).resolve(strict=True)
        for p in shlex.split(dependencies.replace("\\\n", " ").split(":", 1)[1])
    ]
    subjects = {
        source.resolve(),
        compiler.resolve(),
        pkg.resolve(),
        *headers,
        Path("/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib").resolve(strict=True),
    }
    before = {str(p): digest(p) for p in sorted(subjects)}
    command = [
        str(compiler),
        "-Wall",
        "-Wextra",
        "-Werror",
        "-dynamiclib",
        "-MD",
        "-MF",
        str(output / "observer.d"),
        *flags,
        str(source),
        "-o",
        str(output / "observer.dylib"),
    ]
    checked(command)
    after = {str(p): digest(p) for p in sorted(subjects)}
    if before != after:
        raise ValueError("Observer build subject changed")
    inputs = profile(2)
    (output / "input.icc").write_bytes(inputs)
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        icc = pikepdf.Stream(pdf, inputs)
        icc.N = 3
        image = pikepdf.Stream(pdf, bytes([51, 153, 204]))
        image.Type, image.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
        image.Width, image.Height, image.BitsPerComponent = 1, 1, 8
        image.ColorSpace = pikepdf.Array([pikepdf.Name.ICCBased, icc])
        page.obj.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image))
        page.obj.Contents = pikepdf.Stream(pdf, b"q 36 0 0 36 0 0 cm /I Do Q")
        pdf.save(output / "source.pdf", deterministic_id=True)
    record: dict[str, object] = {
        "meaning": "Runtime target identity/serialized metadata, never CMM precision or fidelity",
        "build_command": command,
        "build_subjects_before": before,
        "build_subjects_after": after,
        "declared_pixels": [300, 150],
        "declared_native_pixel": [51, 153, 204],
        "expected_rgb_formats": [262169, 25],
        "expected_intent": 1,
        "expected_flags": 8448,
        "controls": [
            "disabled-observation",
            "foreign-pid",
            "wrong-target-handle",
            "wrong-input-profile",
        ],
        "files": {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output / "truth.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def observe(
    command: list[str], observer: Path, output: Path, *, enabled: bool = True
) -> tuple[int, dict[str, object]]:
    output.mkdir()
    environment = dict(os.environ)
    # Injection is confined to this direct test child, never product state or shell environment.
    environment["DYLD_PRINT_LIBRARIES"] = "1"
    environment.pop("DYLD_INSERT_LIBRARIES", None)
    environment.pop("BOOKSCAN_TEST_PROFILE_DIR", None)
    if enabled:
        environment.update(
            DYLD_INSERT_LIBRARIES=str(observer), BOOKSCAN_TEST_PROFILE_DIR=str(output)
        )
    child = subprocess.Popen(
        command,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = child.communicate(timeout=60)
    except BaseException:
        child.kill()
        child.communicate()
        raise
    if child.returncode != 0:
        raise ValueError(f"Native observation failed {child.returncode}: {stderr.decode()}")
    raw = stderr.decode("utf-8")
    log = parse_log(raw, child.pid)
    record: dict[str, object] = {
        "pid": child.pid,
        "command": command,
        "returncode": child.returncode,
        "reaped": child.poll() is not None,
        "stdout": stdout.decode("utf-8"),
        "stderr": raw,
        "environment_sha256": hashlib.sha256(
            json.dumps(environment, sort_keys=True).encode()
        ).hexdigest(),
        "override": {
            "DYLD_PRINT_LIBRARIES": "1",
            "DYLD_INSERT_LIBRARIES": str(observer),
            "BOOKSCAN_TEST_PROFILE_DIR": str(output),
        }
        if enabled
        else {"DYLD_PRINT_LIBRARIES": "1"},
        "mapped_images": identities(log),
    }
    return child.pid, record


def capture(output: Path, pid: int, source: bytes) -> tuple[dict[str, object], dict[str, object]]:
    events = sorted(output.glob("*-event.txt"), key=lambda p: int(p.name.split("-")[1]))
    lines = [p.read_text() for p in events]
    targets = {int(p.name.split("-")[1]): p.read_bytes() for p in output.glob("*-target.icc")}
    inputs = {int(p.name.split("-")[1]): p.read_bytes() for p in output.glob("*-input.icc")}
    parsed, target = bind_capture(lines, targets, inputs, pid, source)
    expected = (
        {f"{pid}-{e.sequence}-event.txt" for e in parsed}
        | {f"{pid}-{s}-target.icc" for s in targets}
        | {f"{pid}-{s}-input.icc" for s in inputs}
    )
    if {p.name for p in output.iterdir()} != expected:
        raise ValueError("Foreign/missing capture file identity")
    # Handles and profile creation timestamps are observation identities, not A/B semantic keys.
    # Retain raw bytes; normalize only these separately documented volatile fields.
    semantic: dict[str, object] = {
        "events": [
            {k: v for k, v in asdict(e).items() if not k.endswith("_handle")} for e in parsed
        ],
        "target_matrix": [[str(v) for v in row] for row in target.matrix],
        "serialized_target_inverse": [[str(v) for v in row] for row in target.inverse],
        "serialized_target_inverse_norm": str(
            max(sum(abs(v) for v in row) for row in target.inverse)
        ),
        "target_curves": [[f, [str(v) for v in params]] for f, params in target.curves],
        "target_white": [str(v) for v in target.white],
        "target_tags": dict(target.tags),
        "input_tags_verified": True,
        "image_transforms_bound": [e.sequence for e in parsed if e.input_format in (262169, 25)],
        "image_input_formats": sorted(
            {e.input_format for e in parsed if e.input_format in (262169, 25)}
        ),
    }
    raw: dict[str, object] = {
        "events": [asdict(e) for e in parsed],
        "files": {p.name: digest(p) for p in sorted(output.iterdir())},
    }
    return semantic, raw


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    truth = json.loads((fixtures / "truth.json").read_text())
    if any(digest(fixtures / n) != d for n, d in truth["files"].items()):
        raise ValueError("Changed observer fixture")
    subjects = {p: digest(p) for p in fixtures.iterdir() if p.is_file()}
    source = (fixtures / "input.icc").read_bytes()
    saved = intake.snapshot(fixtures / "source.pdf", output / "snapshot.pdf")
    sample = samples.collect(saved, saved.pages[0]).images[0]
    assert sample.color is not None and sample.color.profile == source
    assert sample.packed == bytes([51, 153, 204])
    plain = render.render_page(saved, saved.pages[0], render.renderer_path())
    command = [*plain.command[:-1], str(output / "observed")]
    pid, native = observe(command, fixtures / "observer.dylib", output / "capture")
    semantic, raw = capture(output / "capture", pid, source)
    with Image.open(output / "observed.png") as image:
        assert (image.format, image.mode, image.size) == ("PNG", "RGB", plain.size)
        observed = image.tobytes()
    assert observed == plain.rgb
    assert observed[(149 * 3) : 150 * 3] != b"\xff\xff\xff"
    assert all(
        observed[(y * 300 + 150) * 3 : (y * 300 + 300) * 3] == b"\xff" * 450 for y in range(150)
    )
    controls: dict[str, str] = {}
    disabled_pid, disabled = observe(
        [*plain.command[:-1], str(output / "disabled")],
        fixtures / "observer.dylib",
        output / "disabled-capture",
        enabled=False,
    )
    with Image.open(output / "disabled.png") as image:
        assert (image.format, image.mode, image.size) == ("PNG", "RGB", plain.size)
        assert image.tobytes() == plain.rgb
    try:
        capture(output / "disabled-capture", disabled_pid, source)
    except ValueError:
        controls["disabled-observation"] = "rejected; actual uninjected RGB/geometry unchanged"
    else:
        raise ValueError("Disabled observation credited")
    for name, wrong_pid, wrong_source in [
        ("foreign-pid", pid + 1, source),
        ("wrong-input-profile", pid, profile(1)),
    ]:
        try:
            capture(output / "capture", wrong_pid, wrong_source)
        except ValueError:
            controls[name] = "rejected; actual captured profiles/RGB/geometry unchanged"
        else:
            raise ValueError(f"Incorrect evidence passed: {name}")
    # Alter only an observed transform's claimed target handle. Keep the actual
    # profile bytes, process identity, rendered pixels and geometry unchanged.
    wrong = output / "wrong-target-capture"
    shutil.copytree(output / "capture", wrong)
    selected = semantic["image_transforms_bound"]
    assert isinstance(selected, list) and selected
    event_path = wrong / f"{pid}-{selected[0]}-event.txt"
    fields = event_path.read_text().split()
    handles = [
        int(path.read_text().split()[5]) for path in (output / "capture").glob("*-event.txt")
    ]
    fields[5] = str(max(handles) + 1)
    event_path.write_text(" ".join(fields) + "\n")
    try:
        capture(wrong, pid, source)
    except ValueError as error:
        if str(error) != "Unrelated target handle":
            raise
        controls["wrong-target-handle"] = (
            "rejected; altered event binding only, actual profiles/RGB/geometry unchanged"
        )
    else:
        raise ValueError("Unobserved target handle credited")
    assert set(controls) == set(truth["controls"])
    assert semantic["image_input_formats"] == sorted(truth["expected_rgb_formats"])
    report: dict[str, object] = {
        "format": "BookScanBuilderTargetObservation",
        "version": 1,
        "source_sha256": saved.sha256,
        "input_sha256": digest(fixtures / "input.icc"),
        "plain_rgb_sha256": hashlib.sha256(plain.rgb).hexdigest(),
        "observed_rgb_sha256": hashlib.sha256(observed).hexdigest(),
        "pixels": list(plain.size),
        "semantic": semantic,
        "raw_capture": raw,
        "native": native,
        "disabled_native": disabled,
        "controls": controls,
        "wrong_target_files": {p.name: digest(p) for p in sorted(wrong.iterdir())},
        "observer_rgb_unchanged": True,
        "serialized_matrix_only": True,
        "cmm_precision_verified": False,
        "cairo_fidelity_verified": False,
        "runtime_resources_verified": False,
        "accepted_project_delivered": False,
    }
    assert all(digest(p) == d for p, d in subjects.items())
    saved.verify()
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
