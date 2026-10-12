"""Actual bounded Fontconfig/environment binding; no general glyph-fidelity oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast
from xml.sax.saxutils import escape

import pikepdf
from PIL import Image

from bookscan.intake import snapshot
from bookscan.native_setup import digest, execute, tool
from bookscan.render import render_page, renderer_path
from bookscan.resources import ResourceBinding
from bookscan.skew import NativeError


def subjects(directory: Path) -> dict[str, str]:
    return {str(path): digest(path) for path in sorted(directory.rglob("*")) if path.is_file()}


def build(directory: Path) -> None:
    directory.mkdir()
    fonts: list[str] = []
    for label, family in (("a", "Helvetica"), ("b", "Courier")):
        result = execute([str(tool("fc-match")), "-f", "%{file}\\n", family])
        found = result.stdout.strip().splitlines()
        if result.returncode or len(found) != 1:
            raise ValueError("Cannot identify one actual font candidate")
        original = Path(found[0]).resolve(strict=True)
        fonts.append(str(original))
        fontdir = directory / ("fonts-" + label)
        fontdir.mkdir()
        (fontdir / original.name).symlink_to(original)
        cache = directory / ("cache-" + label)
        cache.mkdir()
        config = directory / (label + ".conf")
        # No default includes: this test-controlled candidate scope has one face file.
        # FONTCONFIG_FILE selects the config; <dir>/<cachedir> meanings are official.
        # https://fontconfig.pages.freedesktop.org/fontconfig/fontconfig-user.html
        config.write_text(
            "<fontconfig><dir>"
            + escape(str(fontdir))
            + "</dir><cachedir>"
            + escape(str(cache))
            + "</cachedir></fontconfig>\n"
        )
        environment = dict(os.environ)
        environment.update(
            FONTCONFIG_FILE=str(config), FONTCONFIG_PATH=str(directory), FC_DEBUG="0"
        )
        warmed = execute([str(tool("fc-list")), "-f", "%{file}\\n"], environment=environment)
        if warmed.returncode or not warmed.stdout.strip():
            raise ValueError("Controlled Fontconfig scope did not warm/list fonts")
        (directory / (label + "-candidates.txt")).write_text(warmed.stdout)
    if fonts[0] == fonts[1]:
        raise ValueError("The two test-controlled resource subjects must differ")
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(144, 36))
        font = pdf.make_indirect(
            pikepdf.Dictionary(
                Type=pikepdf.Name.Font,
                Subtype=pikepdf.Name.Type1,
                BaseFont=pikepdf.Name.Helvetica,
                Encoding=pikepdf.Name.WinAnsiEncoding,
            )
        )
        page.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
        page.Contents = pikepdf.Stream(
            pdf, b"q 1 0 0 rg 0 0 12 36 re f Q BT /F1 16 Tf 16 12 Td (MMMmmlll) Tj ET"
        )
        pdf.save(directory / "source.pdf")
    # Contract declared before any comparison raster, no tolerance fitted from outputs.
    truth = {
        "version": 1,
        "size": [600, 150],
        "font_files": fonts,
        "expected_environment_stdout": "captured\n",
        "expected_changed_resource": ["DEPENDENCY_UNAVAILABLE", 5],
        "runtime_resources_verified": False,
        "fidelity": "unavailable: no independent whole-glyph raster/coverage truth",
        "fontconfig_version": "2.18.3",
        "files": subjects(directory),
        "external_fonts": {path: digest(Path(path)) for path in fonts},
    }
    (directory / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")


def observe(command: list[str], environment: dict[str, str]) -> dict[str, object]:
    child = subprocess.Popen(
        command,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        close_fds=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = child.communicate(timeout=120)
    except BaseException:
        child.kill()
        child.communicate()
        raise
    if child.returncode:
        raise ValueError(f"Native renderer exited {child.returncode}: {stderr}")
    return {
        "pid": child.pid,
        "reaped": child.poll() is not None,
        "command": command,
        "returncode": child.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    truth = json.loads((fixtures / "truth.json").read_text())
    before = subjects(fixtures)
    for path, expected in {**truth["files"], **truth["external_fonts"]}.items():
        if digest(Path(path)) != expected:
            raise ValueError(f"Changed construction subject: {path}")
    version = execute([str(tool("fc-list")), "--version"])
    if (version.stdout + version.stderr).strip() != "fontconfig version 2.18.3":
        raise ValueError("Unverified Fontconfig version")
    renderer = renderer_path()
    saved = snapshot(fixtures / "source.pdf", output / "snapshot.pdf")
    environment = dict(os.environ)
    environment.update(
        FONTCONFIG_FILE=str(fixtures / "a.conf"),
        FONTCONFIG_PATH=str(fixtures),
        FC_DEBUG="1",
    )
    paths = [fixtures / "a.conf", *(fixtures / "fonts-a").iterdir()]
    paths += [path for path in (fixtures / "cache-a").rglob("*") if path.is_file()]
    guard = ResourceBinding.capture(paths, environment=environment)
    # Ambient changes after capture cannot select the second config for this child.
    old = os.environ.get("FONTCONFIG_FILE")
    os.environ["FONTCONFIG_FILE"] = str(fixtures / "b.conf")
    try:
        raster = render_page(saved, saved.pages[0], renderer, resources=guard)
    finally:
        if old is None:
            os.environ.pop("FONTCONFIG_FILE", None)
        else:
            os.environ["FONTCONFIG_FILE"] = old
    if list(raster.size) != truth["size"] or raster.resource_binding != guard.record():
        raise ValueError("Wrong frame/resource provenance")
    raw: list[dict[str, object]] = []
    hashes: dict[str, str] = {"guarded": hashlib.sha256(raster.rgb).hexdigest()}
    for label in ("a", "b"):
        env = dict(environment)
        env["FONTCONFIG_FILE"] = str(fixtures / (label + ".conf"))
        command = list(raster.command)
        command[-1] = str(output / label)
        record = observe(command, env)
        # This is an actual Fontconfig match log, not a claim about all native opens.
        font_name = Path(truth["font_files"][0 if label == "a" else 1]).name
        if font_name not in str(record["stdout"]):
            raise ValueError("Actual selected font absent from native match diagnostics")
        with Image.open(output / (label + ".png")) as image:
            if image.mode != "RGB" or list(image.size) != truth["size"]:
                raise ValueError("Wrong direct native frame")
            hashes[label] = hashlib.sha256(image.tobytes()).hexdigest()
        record["binding"] = ResourceBinding.capture(
            [fixtures / (label + ".conf"), *(fixtures / ("fonts-" + label)).iterdir()],
            environment=env,
        ).record()
        raw.append(record)
    if hashes["guarded"] != hashes["a"] or hashes["a"] == hashes["b"]:
        raise ValueError("Captured environment or actual different-font control failed")
    changed = output / "change.conf"
    changed.write_bytes((fixtures / "a.conf").read_bytes())
    change_guard = ResourceBinding.capture([changed], environment=environment)
    changed.write_bytes((fixtures / "b.conf").read_bytes())
    try:
        render_page(saved, saved.pages[0], renderer, resources=change_guard)
    except NativeError as error:
        rejection = [error.code, error.exit_code]
    else:
        raise ValueError("Changed-resource control returned usable pixels")
    if rejection != truth["expected_changed_resource"]:
        raise ValueError("Wrong changed-resource outcome")
    env_guard = ResourceBinding.capture([], environment={"BOOKSCAN_RESOURCE_TEST": "captured"})
    printed = execute(
        [sys.executable, "-c", "import os; print(os.environ['BOOKSCAN_RESOURCE_TEST'])"],
        environment=env_guard.environment(),
    )
    if printed.returncode or printed.stdout != truth["expected_environment_stdout"]:
        raise ValueError("Wrong literal child environment")
    after = subjects(fixtures)
    if after != before:
        raise ValueError("Construction/font/config/cache subjects changed during reading")
    for path, expected in truth["external_fonts"].items():
        if digest(Path(path)) != expected:
            raise ValueError("External font subject changed")
    result: dict[str, object] = {
        "module": str(Path(__import__("bookscan.resources", fromlist=["x"]).__file__).resolve()),
        "renderer_sha256": digest(renderer),
        "binding": guard.record(),
        "hashes": hashes,
        "raw": raw,
        "controls": {
            "different-font-is-distinct": True,
            "ambient-environment-cannot-change-bound-render": True,
            "changed-resource-rejected": rejection,
            "literal-child-environment": printed.stdout,
        },
        "subjects_before": before,
        "subjects_after": after,
        "runtime_resources_verified": False,
        "fidelity": truth["fidelity"],
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["build", "check"])
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "build":
        build(args.artifacts)
    else:
        if args.fixtures is None:
            parser.error("check requires --fixtures")
        result = run(cast(Path, args.fixtures), args.artifacts)
        print(json.dumps(result["controls"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
