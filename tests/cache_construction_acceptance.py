"""Exercise the product's owned cache lifetime with actual Fontconfig and Cairo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from font_loading_acceptance import subjects
from PIL import Image

from bookscan import fontconfig
from bookscan.fontconfig import FontconfigBinding, prepared_fontconfig_cache
from bookscan.intake import snapshot
from bookscan.native_setup import digest, execute
from bookscan.render import render_page, renderer_path
from bookscan.skew import NativeError


def case(fixtures: Path, output: Path, label: str) -> dict[str, object]:
    output.mkdir()
    fonts, cache, config_dir = output / "fonts", output / "cache", output / "config"
    fonts.mkdir()
    config_dir.mkdir()
    source_font = next((fixtures / ("fonts-" + label)).iterdir())
    font = fonts / source_font.name
    shutil.copyfile(source_font, font)
    config = config_dir / "fonts.conf"
    config.write_text(
        "<fontconfig><dir>"
        + escape(str(fonts))
        + "</dir><cachedir>"
        + escape(str(cache))
        + "</cachedir></fontconfig>\n"
    )
    environment = dict(os.environ, FONTCONFIG_FILE=str(config), FONTCONFIG_PATH=str(config_dir))
    for key in ("FC_DEBUG", "FONTCONFIG_SYSROOT", "DYLD_INSERT_LIBRARIES", "DYLD_PRINT_LIBRARIES"):
        environment.pop(key, None)
    renderer = renderer_path()
    saved = snapshot(fixtures / "source.pdf", output / "snapshot.pdf")
    before = subjects(fonts) | subjects(config_dir)
    # Declare these comparison rules before invoking the constructor or renderer.
    # They test lifetime/RGB pass-through, not independent glyph or full-page truth.
    truth = {
        "frame": [600, 150],
        "cache_initially_absent": True,
        "cache_removed_after_context": True,
        "mutation_outcome": ["DEPENDENCY_UNAVAILABLE", 5],
        "foreign_cache_outcome": ["DEPENDENCY_UNAVAILABLE", 5],
        "direct_child_foreign_exit": 5,
        "font_sha256": digest(font),
        "runtime_resources_verified": False,
    }
    (output / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    if cache.exists():
        raise ValueError("Private cache destination was already occupied")
    with prepared_fontconfig_cache(renderer, cache, environment=environment) as found:
        if not list(cache.iterdir()):
            raise ValueError("Product cache constructor did not populate its new root")
        frozen = subjects(cache)
        raster = render_page(saved, saved.pages[0], renderer, resources=found.binding)
        if raster.size != (600, 150) or raster.diagnostics:
            raise ValueError("Wrong guarded renderer result")
        repeat = render_page(saved, saved.pages[0], renderer, resources=found.binding)
        if repeat.rgb != raster.rgb or subjects(cache) != frozen:
            raise ValueError("Completed cache/render was not immutable")
        with Image.frombytes("RGB", raster.size, raster.rgb) as image:
            image.save(output / "baseline.png")
        marker = cache / "changed-after-binding"
        marker.write_bytes(b"unbound candidate")
        try:
            render_page(saved, saved.pages[0], renderer, resources=found.binding)
        except NativeError as error:
            mutation = [error.code, error.exit_code]
        else:
            raise ValueError("Mutated completed cache returned raster bytes")
        marker.unlink()
        found.binding.verify()
        # Preserve exact cache bytes for evidence before the owner removes them.
        shutil.copytree(cache, output / "completed-cache-copy")
        record = found.record()
    if cache.exists() or subjects(fonts) | subjects(config_dir) != before:
        raise ValueError("Private cache cleanup changed a source input or left its root")
    # Foreign caches must be rejected both by the owning operation and inside the
    # actual child before BuildFonts, even if the child is invoked independently.
    foreign = output / "foreign-cache"
    foreign.mkdir()
    bad_config = config_dir / "bad.conf"
    bad_config.write_text(config.read_text().replace(str(cache), str(foreign)))
    bad_environment = dict(environment, FONTCONFIG_FILE=str(bad_config))
    try:
        with prepared_fontconfig_cache(renderer, cache, environment=bad_environment):
            raise ValueError("Unowned cache root was accepted")
    except NativeError as error:
        foreign_outcome = [error.code, error.exit_code]
    if cache.exists() or list(foreign.iterdir()):
        raise ValueError("Refused owner construction wrote a foreign cache")
    module_file = fontconfig.__file__
    if not isinstance(found.binding, FontconfigBinding):
        raise ValueError("Missing bound Fontconfig module/library")
    probe = Path(module_file).with_name("fontconfig_probe.py")
    library = found.binding.library
    cache.mkdir()
    command = [sys.executable, "-I", str(probe), str(library), "--build-cache", str(cache)]
    refused = execute(command, environment=bad_environment)
    if (
        refused.returncode != 5
        or refused.stdout
        or list(foreign.iterdir())
        or list(cache.iterdir())
    ):
        raise ValueError("Child confinement check allowed foreign cache construction")
    cache.rmdir()
    result: dict[str, object] = {
        "size": list(raster.size),
        "rgb_sha256": hashlib.sha256(raster.rgb).hexdigest(),
        "font_sha256": digest(font),
        "binding": record,
        "cache_removed_after_context": True,
        "immutable_render_repeat": True,
        "mutation_outcome": mutation,
        "foreign_cache_outcome": foreign_outcome,
        "direct_child": {
            "command": command,
            "exit_code": refused.returncode,
            "stdout": refused.stdout,
            "stderr": refused.stderr,
        },
        "runtime_resources_verified": False,
        "limitation": (
            "Controlled owned cache only; no general configuration/font copy or glyph truth"
        ),
    }
    if mutation != truth["mutation_outcome"] or foreign_outcome != truth["foreign_cache_outcome"]:
        raise ValueError("Wrong cache mutation/confinement result")
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def run(fixtures: Path, output: Path) -> None:
    before = subjects(fixtures)
    output.mkdir()
    results = {label: case(fixtures, output / label, label) for label in ("a", "b")}
    if results["a"]["rgb_sha256"] == results["b"]["rgb_sha256"]:
        raise ValueError("Different controlled fonts were not distinguished")
    if before != subjects(fixtures):
        raise ValueError("Cache construction changed an input fixture")
    (output / "result.json").write_text(json.dumps(results, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    run(args.fixtures, args.artifacts)
    print(json.dumps({"controlled_fonts": 2, "runtime_resources_verified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
