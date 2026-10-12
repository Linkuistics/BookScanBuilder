"""Verify this Mac's ordinary default snapshot without changing host fonts or caches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import cast

from PIL import Image

from bookscan.fontconfig import prepared_fontconfig_snapshot
from bookscan.intake import snapshot
from bookscan.render import render_page, renderer_path


def run(source: Path, output: Path) -> None:
    output.mkdir()
    root = output / "private"
    environment = dict(os.environ)
    for key in ("FONTCONFIG_FILE", "FONTCONFIG_PATH", "FONTCONFIG_SYSROOT", "FC_DEBUG"):
        environment.pop(key, None)
    # Declare the claim before output. This checks copied bytes/scope/lifetime,
    # not independent arbitrary-font glyph correctness or original-host rendering.
    truth = {
        "configuration_file": "/opt/homebrew/etc/fonts/fonts.conf",
        "size": [600, 150],
        "snapshot_removed": True,
        "runtime_resources_verified": False,
        "glyph_truth": "unavailable: no independent arbitrary-font/full-page oracle",
    }
    (output / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    saved = snapshot(source, output / "source.pdf")
    with prepared_fontconfig_snapshot(renderer_path(), root, environment=environment) as found:
        record = found.record()
        owned = cast(dict[str, object], record["resource_snapshot"])
        if owned["configuration_file"] != truth["configuration_file"]:
            raise ValueError("Ordinary default selected a different configuration")
        original = cast(dict[str, object], owned["original"])
        original_scope = cast(dict[str, list[str]], original["scope"])
        for field in ("config_files", "config_dirs", "effective_font_dirs"):
            expected = {str(root / name.lstrip("/")) for name in original_scope[field]}
            if expected != set(getattr(found.scope, field)):
                raise ValueError("Default native scope did not retain every original input")
        originals = cast(dict[str, object], original["binding"])
        copied = {
            item.path: item for tree in found.binding.directories for item in tree.entries or ()
        }
        roots = set(original_scope["effective_font_dirs"]) | set(original_scope["config_dirs"])
        checked_files = 0
        checked_missing = 0
        for tree in cast(list[dict[str, object]], originals["directories"]):
            if tree["path"] not in roots or tree["entries"] is None:
                continue
            for item in cast(list[dict[str, object]], tree["entries"]):
                name = str(root / str(item["path"]).lstrip("/"))
                actual = copied[name]
                if (
                    item["kind"] == "file"
                    and str(item["path"]) not in original_scope["parsed_files"]
                ):
                    if actual.kind != "file" or actual.sha256 != item["sha256"]:
                        raise ValueError("An ordinary default resource lost its bound bytes")
                    checked_files += 1
                elif item["kind"] == "dangling-symlink":
                    missing = str(root / str(item["resolved"]).lstrip("/"))
                    if actual.kind != "dangling-symlink" or actual.resolved != missing:
                        raise ValueError("Ordinary default missing target escaped its private root")
                    checked_missing += 1
        if not checked_files or not checked_missing:
            raise ValueError("Default copy did not exercise files and absent-target aliases")
        raster = render_page(saved, saved.pages[0], renderer_path(), resources=found.binding)
        if raster.size != (600, 150) or raster.diagnostics:
            raise ValueError("Ordinary default private render failed its declared frame")
        with Image.frombytes("RGB", raster.size, raster.rgb) as image:
            image.save(output / "baseline.png")
        (output / "binding.json").write_text(json.dumps(record, indent=2) + "\n")
        result = {
            **truth,
            "copied_files_checked": checked_files,
            "copied_missing_targets_checked": checked_missing,
            "rgb_sha256": hashlib.sha256(raster.rgb).hexdigest(),
        }
    if root.exists():
        raise ValueError("Ordinary default snapshot cleanup failed")
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    run(args.source.resolve(), args.artifacts.resolve())
    print(json.dumps({"ordinary_default_copy": True, "runtime_resources_verified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
