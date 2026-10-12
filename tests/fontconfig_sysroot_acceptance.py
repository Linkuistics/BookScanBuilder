"""Bind effective native font/cache paths under an output-owned sysroot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from xml.sax.saxutils import escape

from bookscan.fontconfig import discover_fontconfig
from bookscan.native_setup import execute, tool
from bookscan.render import renderer_path
from bookscan.resources import ResourceBinding
from bookscan.skew import NativeError


def case(fixtures: Path, output: Path, *, already_prefixed: bool) -> dict[str, object]:
    output.mkdir()
    root = output / "sysroot"
    root.mkdir()
    logical_parent = root if already_prefixed else output
    logical_fonts = logical_parent / "logical-fonts"
    logical_cache = logical_parent / "logical-cache"
    fonts = root / str(logical_fonts).lstrip("/")
    cache = root / str(logical_cache).lstrip("/")
    fonts.mkdir(parents=True)
    cache.mkdir(parents=True)
    original = next((fixtures / "fonts-a").iterdir()).resolve(strict=True)
    font = fonts / original.name
    shutil.copyfile(original, font)
    config = root / "fonts.conf"
    config.write_text(
        "<fontconfig><dir>"
        + escape(str(logical_fonts))
        + "</dir><cachedir>"
        + escape(str(logical_cache))
        + "</cachedir></fontconfig>\n"
    )
    environment = dict(os.environ, FONTCONFIG_FILE=str(config), FONTCONFIG_SYSROOT=str(root))
    environment.pop("FC_DEBUG", None)
    declared = {
        "logical_font_dir": str(logical_fonts),
        "logical_cache_dir": str(logical_cache),
        "effective_font_dir": str(fonts),
        "effective_cache_dir": str(cache),
        "mutated_guard": ["DEPENDENCY_UNAVAILABLE", 5],
        "runtime_resources_verified": False,
        "glyph_truth": "unavailable; candidate enumeration is not a glyph raster oracle",
    }
    (output / "declared.json").write_text(json.dumps(declared, indent=2) + "\n")
    renderer = renderer_path()
    found = discover_fontconfig(renderer, environment=environment)
    weak = ResourceBinding.capture(
        [config], optional_directories=[logical_fonts, logical_cache], environment=environment
    )
    outcomes: dict[str, object] = {}
    # No font/cache build first: adding bytes only inside the effective font tree
    # must invalidate the saved guard, even with unchanged logical getter paths.
    added = fonts / "added-font"
    added.write_bytes(b"new native candidate")
    weak.verify()
    try:
        found.binding.verify()
    except NativeError as error:
        outcomes["font_growth"] = [error.code, error.exit_code]
    else:
        raise ValueError("Effective sysroot font growth escaped the resource guard")
    added.unlink()
    fresh = discover_fontconfig(renderer, environment=environment)
    added_cache = cache / "later-cache"
    added_cache.write_bytes(b"new native cache subject")
    weak.verify()
    try:
        fresh.binding.verify()
    except NativeError as error:
        outcomes["cache_growth"] = [error.code, error.exit_code]
    else:
        raise ValueError("Effective sysroot cache growth escaped the resource guard")
    added_cache.unlink()
    # Native FcInit/BuildFonts is confined to this test-owned root. Discovery
    # itself must leave these initially empty caches untouched.
    if list(cache.iterdir()) or logical_fonts.exists() or logical_cache.exists():
        raise ValueError("Configuration discovery mutated native resources")
    cold = discover_fontconfig(renderer, environment=environment)
    native_command = [str(tool("fc-list")), "-f", "%{file}\n"]
    listing = execute(native_command, environment=environment)
    if (
        listing.returncode
        or listing.stderr
        or str(logical_fonts / original.name) not in (listing.stdout.splitlines())
        or not list(cache.iterdir())
    ):
        raise ValueError("Native Fontconfig did not read effective fonts/write effective cache")
    weak.verify()
    try:
        cold.binding.verify()
    except NativeError as error:
        outcomes["cold_cache_population"] = [error.code, error.exit_code]
    else:
        raise ValueError("Native cold-cache writes escaped the resource guard")
    warm = discover_fontconfig(renderer, environment=environment)
    warm.binding.verify()
    scope = warm.record()["scope"]
    if warm.scope.effective_font_dirs != (str(fonts),) or (
        warm.scope.effective_cache_dirs != (str(cache),)
    ):
        raise ValueError("Effective native roots were not reported separately")
    if any(value != declared["mutated_guard"] for value in outcomes.values()):
        raise ValueError("Wrong effective-resource failure class")
    result: dict[str, object] = {
        "declared": declared,
        "outcomes": outcomes,
        "scope": scope,
        "native_command": native_command,
        "native_listing": listing.stdout.splitlines(),
        "font_sha256": hashlib.sha256(font.read_bytes()).hexdigest(),
        "wrong_logical_only_guard_misses_changes": True,
        "logical_roots_stay_absent": True,
        "runtime_resources_verified": False,
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    result: dict[str, object] = {
        label: case(fixtures, output / label, already_prefixed=already)
        for label, already in (("ordinary", False), ("already-prefixed", True))
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.fixtures, args.artifacts)
    print(json.dumps({"cases": list(result), "runtime_resources_verified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
