"""Observe named renderer font opens with privately built caches; no glyph oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import cast
from xml.sax.saxutils import escape

from font_loading import bind_loading
from PIL import Image
from runtime_acceptance import identities
from runtime_loader import parse_log

from bookscan.fontconfig import discover_fontconfig
from bookscan.intake import snapshot
from bookscan.native_setup import checked, digest, execute, tool
from bookscan.render import render_page, renderer_path
from bookscan.skew import NativeError


def subjects(root: Path) -> dict[str, str]:
    return {str(path): digest(path) for path in sorted(root.rglob("*")) if path.is_file()}


def build(fixtures: Path, output: Path) -> None:
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("Font observer characterized only on this Mac arm64 host")
    output.mkdir()
    source = Path(__file__).parent / "native/font_loading_observer.c"
    compiler, pkg = tool("clang"), tool("pkg-config")
    versions = checked([str(pkg), "--modversion", "fontconfig", "freetype2"])
    if versions != "2.18.3\n26.6.20":
        raise ValueError("Unsupported Fontconfig/FreeType pkg-config identities")
    flags = shlex.split(checked([str(pkg), "--cflags", "--libs", "fontconfig", "freetype2"]))
    dependencies = checked([str(compiler), "-M", *flags, str(source)])
    headers = {
        Path(name).resolve(strict=True)
        for name in shlex.split(dependencies.replace("\\\n", " ").split(":", 1)[1])
    }
    libraries = {
        Path("/opt/homebrew/opt/fontconfig/lib/libfontconfig.1.dylib").resolve(strict=True),
        Path("/opt/homebrew/opt/freetype/lib/libfreetype.6.dylib").resolve(strict=True),
    }
    inputs = headers | libraries | {source.resolve(), compiler.resolve(), pkg.resolve()}
    before = {str(path): digest(path) for path in sorted(inputs)}
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
    after = {str(path): digest(path) for path in sorted(inputs)}
    if before != after:
        raise ValueError("Font observer build subject changed")
    shutil.copyfile(fixtures / "source.pdf", output / "source.pdf")
    for label in ("a", "b"):
        directory = output / ("fonts-" + label)
        directory.mkdir()
        original = next((fixtures / ("fonts-" + label)).iterdir()).resolve(strict=True)
        shutil.copyfile(original, directory / original.name)
        if digest(original) != digest(directory / original.name):
            raise ValueError("Private font copy differs")
    # All rules are declared before any renderer output. Equality is pass-through
    # evidence only; no tolerance or independent glyph-fidelity claim follows.
    record: dict[str, object] = {
        "build_command": command,
        "build_subjects_before": before,
        "build_subjects_after": after,
        "versions": versions,
        "frame": [600, 150],
        "cold_outcome": ["DEPENDENCY_UNAVAILABLE", 5],
        "controls": ["disabled", "foreign-pid", "wrong-font", "wrong-inode", "wrong-index"],
        "runtime_resources_verified": False,
        "fidelity": "unavailable: no independent arbitrary-glyph/full-page truth",
        "files": subjects(output),
    }
    (output / "truth.json").write_text(json.dumps(record, indent=2) + "\n")


def observe(
    command: list[str], environment: dict[str, str], directory: Path, output: Path
) -> dict[str, object]:
    child = subprocess.Popen(
        command,
        env=environment,
        cwd=directory,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        close_fds=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = child.communicate(timeout=60)
    except BaseException:
        child.kill()
        child.communicate()
        raise
    record: dict[str, object] = {
        "pid": child.pid,
        "command": command,
        "returncode": child.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "reaped": child.poll() is not None,
    }
    (output / "child.json").write_text(json.dumps(record, indent=2) + "\n")
    log = parse_log(stderr, child.pid)
    record["mapped_images"] = identities(log)
    if child.returncode != 0 or stdout or log.diagnostics:
        raise ValueError("Native font observation failed or emitted diagnostics")
    (output / "child.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def case(fixtures: Path, output: Path, label: str) -> dict[str, object]:
    output.mkdir()
    fonts, cache = output / "fonts", output / "cache"
    fonts.mkdir()
    cache.mkdir()
    original = next((fixtures / ("fonts-" + label)).iterdir())
    font = fonts / original.name
    shutil.copyfile(original, font)
    config = output / "fonts.conf"
    config.write_text(
        "<fontconfig><dir>"
        + escape(str(fonts))
        + "</dir><cachedir>"
        + escape(str(cache))
        + "</cachedir></fontconfig>\n"
    )
    environment = dict(os.environ, FONTCONFIG_FILE=str(config), FONTCONFIG_PATH=str(output))
    for key in ("FC_DEBUG", "FONTCONFIG_SYSROOT", "DYLD_INSERT_LIBRARIES", "DYLD_PRINT_LIBRARIES"):
        environment.pop(key, None)
    renderer = renderer_path()
    saved = snapshot(fixtures / "source.pdf", output / "snapshot.pdf")
    cold_cache = output / "cold-cache"
    cold_cache.mkdir()
    cold_config = output / "cold.conf"
    cold_config.write_text(config.read_text().replace(str(cache), str(cold_cache)))
    cold_environment = dict(environment, FONTCONFIG_FILE=str(cold_config))
    cold = discover_fontconfig(renderer, environment=cold_environment)
    if list(cold_cache.iterdir()):
        raise ValueError("Discovery populated a private cold cache")
    # Current guard must reject output mutation if captured before cache building.
    try:
        render_page(saved, saved.pages[0], renderer, resources=cold.binding)
    except NativeError as error:
        cold_outcome = [error.code, error.exit_code]
    else:
        raise ValueError("Cold cache unexpectedly returned accepted raster bytes")
    if cold_outcome != ["DEPENDENCY_UNAVAILABLE", 5] or not list(cold_cache.iterdir()):
        raise ValueError("Wrong cold-cache outcome")
    if list(cache.iterdir()):
        raise ValueError("Managed private cache was populated by the separate cold control")
    warm_command = [str(tool("fc-list")), "-f", "%{file}\n"]
    warmed = execute(warm_command, environment=environment)
    if warmed.returncode or warmed.stderr or str(font) not in warmed.stdout.splitlines():
        raise ValueError("Private cache construction/listing failed")
    if not list(cache.iterdir()):
        raise ValueError("Explicit construction did not populate the initially empty private cache")
    # The completed cache is now an immutable input to this bounded reading.
    frozen_before = subjects(fonts) | subjects(cache) | {str(config): digest(config)}
    warm = discover_fontconfig(renderer, environment=environment)
    raster = render_page(saved, saved.pages[0], renderer, resources=warm.binding)
    if raster.size != (600, 150) or raster.diagnostics:
        raise ValueError("Wrong successful guarded raster/diagnostics")
    observations: dict[str, object] = {}
    for enabled, name in ((True, "observed"), (False, "disabled")):
        destination = output / name
        destination.mkdir()
        events_dir = destination / "events"
        events_dir.mkdir()
        env = dict(environment)
        env["DYLD_PRINT_LIBRARIES"] = "1"
        if enabled:
            env.update(
                DYLD_INSERT_LIBRARIES=str(fixtures / "observer.dylib"),
                BOOKSCAN_TEST_FONT_ROOT=str(fonts),
                BOOKSCAN_TEST_FONT_EVENTS=str(events_dir),
            )
        command = list(raster.command)
        command[-1] = str(destination / "page")
        warm.binding.verify()
        child = observe(command, env, warm.binding.directory, destination)
        warm.binding.verify()
        mapped = cast(list[dict[str, object]], child["mapped_images"])
        if enabled and str((fixtures / "observer.dylib").resolve()) not in {
            row.get("resolved") for row in mapped
        }:
            raise ValueError("Observer was not mapped into the actual renderer")
        events = [json.loads(path.read_text()) for path in sorted(events_dir.iterdir())]
        with Image.open(destination / "page.png") as image:
            if image.mode != "RGB" or image.size != raster.size or image.tobytes() != raster.rgb:
                raise ValueError("Font interposer changed pass-through RGB")
        if enabled:
            bound = bind_loading(events, cast(int, child["pid"]), font)
            controls: dict[str, bool] = {}
            for control in ("foreign-pid", "wrong-font", "wrong-inode", "wrong-index"):
                altered = json.loads(json.dumps(events))
                if control == "foreign-pid":
                    altered[0]["pid"] = cast(int, child["pid"]) + 1
                elif control == "wrong-font":
                    altered[0]["path"] = str(fonts / "wrong")
                elif control == "wrong-inode":
                    next(row for row in altered if row["kind"] == "open")["inode"] = -1
                else:
                    for row in altered:
                        if row["kind"] == "face":
                            row["index"] = 999
                try:
                    bind_loading(altered, cast(int, child["pid"]), font)
                except ValueError:
                    controls[control] = True
                else:
                    raise ValueError("Wrong native font observation was credited")
            observations[name] = {"child": child, "bound": bound, "controls": controls}
        else:
            try:
                bind_loading(events, cast(int, child["pid"]), font)
            except ValueError:
                observations[name] = {"child": child, "rejected": True}
            else:
                raise ValueError("Disabled font observer was credited")
    frozen_after = subjects(fonts) | subjects(cache) | {str(config): digest(config)}
    if frozen_before != frozen_after:
        raise ValueError("Private immutable font/config/completed cache changed")
    result: dict[str, object] = {
        "cold_outcome": cold_outcome,
        "cold_binding": cold.record(),
        "warm_command": warm_command,
        "warm_outcome": {"returncode": warmed.returncode, "stderr": warmed.stderr},
        "managed_cache_initially_empty": True,
        "managed_cache_populated_before_binding": True,
        "private_resources_unchanged": True,
        "warm_listing": warmed.stdout.splitlines(),
        "binding": warm.record(),
        "frozen_before": frozen_before,
        "frozen_after": frozen_after,
        "observations": observations,
        "size": list(raster.size),
        "rgb_sha256": hashlib.sha256(raster.rgb).hexdigest(),
        "runtime_resources_verified": False,
        "limitation": (
            "Named matched face/open only; no complete reads, transient exclusion or glyph truth"
        ),
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def run(fixtures: Path, output: Path) -> None:
    output.mkdir()
    truth = json.loads((fixtures / "truth.json").read_text())
    for name, expected in truth["files"].items():
        if digest(Path(name)) != expected:
            raise ValueError("Changed font construction input")
    before = subjects(fixtures)
    results = {label: case(fixtures, output / label, label) for label in ("a", "b")}
    if results["a"]["rgb_sha256"] == results["b"]["rgb_sha256"]:
        raise ValueError("Different-font renderer control did not distinguish glyph pixels")
    if before != subjects(fixtures):
        raise ValueError("Font construction inputs changed during reading")
    (output / "result.json").write_text(json.dumps(results, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["build", "check"])
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "build":
        build(args.fixtures, args.artifacts)
    else:
        run(args.fixtures, args.artifacts)
    print(json.dumps({"mode": args.mode, "runtime_resources_verified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
