"""Actual configured-root discovery; default binding/fidelity limitations stay explicit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast
from xml.sax.saxutils import escape

import resource_acceptance

import bookscan.render as rendering
from bookscan.dependencies import linked_identity
from bookscan.fontconfig import discover_fontconfig
from bookscan.intake import Snapshot, snapshot
from bookscan.native_setup import execute
from bookscan.render import render_page, renderer_path
from bookscan.resources import ResourceBinding
from bookscan.skew import NativeError


def template_controls(
    renderer: Path, library: Path, output: Path, environment: dict[str, str]
) -> dict[str, object]:
    """Real optional scan-only reads under an output-owned native sysroot."""
    root = output / "template-sysroot"
    root.mkdir()
    config = root / "fonts.conf"
    cache = root / "cache"
    config.write_text(f"<fontconfig><cachedir>{escape(str(cache))}</cachedir></fontconfig>\n")
    # Independent expected root from this native build's retained disassembly.
    templates = root / "opt/homebrew/Cellar/fontconfig/2.18.3/share/fontconfig/conf.avail"
    captured = dict(environment, FONTCONFIG_FILE=str(config), FONTCONFIG_SYSROOT=str(root))
    absent = discover_fontconfig(renderer, environment=captured)
    if absent.scope.template_dirs != (str(templates),):
        raise ValueError("Native template sysroot was not recorded exactly")
    tree = next(item for item in absent.binding.directories if item.path == str(templates))
    if tree.entries is not None:
        raise ValueError("Missing optional template root was not recorded absent")
    templates.mkdir(parents=True)
    template = templates / "50-inactive.conf"
    # An inactive template must be parsed without adding an active font directory.
    template.write_text("<fontconfig><dir>/never-enabled-fonts</dir></fontconfig>\n")
    try:
        absent.binding.verify()
    except NativeError as error:
        appearance = [error.code, error.exit_code]
    else:
        raise ValueError("Old template absence binding accepted root appearance")
    found = discover_fontconfig(renderer, environment=captured)
    if str(template) not in found.scope.parsed_files or str(template) in found.scope.config_files:
        raise ValueError("Actual scan-only file was omitted or falsely labelled loaded")
    if found.scope.font_dirs != ():
        raise ValueError("Optional template rules were activated")
    loaded_fields = ("config_files", "config_dirs", "font_dirs", "cache_dirs")
    if any(getattr(absent.scope, field) != getattr(found.scope, field) for field in loaded_fields):
        raise ValueError("Scan-only template unexpectedly changed a loaded scope")
    # Bind exactly the previous loaded subjects: this disproof must miss changes.
    weak = ResourceBinding.capture([config], optional_directories=[cache], environment=captured)
    template.write_text("<fontconfig><!-- altered scan-only bytes --></fontconfig>\n")
    weak.verify()
    try:
        found.binding.verify()
    except NativeError as error:
        mutation = [error.code, error.exit_code]
    else:
        raise ValueError("Altered scan-only bytes returned a current resource binding")
    # Fresh parsing must also account for a template's include outside its tree.
    external = root / "outside-template-tree.conf"
    template.write_text(
        '<fontconfig><include ignore_missing="yes">'
        + escape(str(external))
        + "</include></fontconfig>\n"
    )
    missing_include = discover_fontconfig(renderer, environment=captured)
    external.write_text("<fontconfig/>\n")
    weak.verify()
    try:
        missing_include.binding.verify()
    except NativeError as error:
        include = [error.code, error.exit_code]
    else:
        raise ValueError("Later scan-only include escaped fresh scope verification")
    fresh = discover_fontconfig(renderer, environment=captured)
    if str(external) not in fresh.scope.parsed_files or str(external) in fresh.scope.config_files:
        raise ValueError("Fresh scan-only include was omitted or labelled loaded")
    fresh.binding.verify()
    if any(getattr(found.scope, field) != getattr(fresh.scope, field) for field in loaded_fields):
        raise ValueError("Scan-only include unexpectedly changed a loaded scope")
    # The optional parser's false-complain mode can return true after errors;
    # parent stderr validation must reject this instead of crediting fallback.
    template.write_text("<fontconfig><unclosed\n")
    try:
        discover_fontconfig(renderer, environment=captured)
    except NativeError as error:
        malformed = [error.code, error.exit_code]
    else:
        raise ValueError("Malformed template diagnostics were silently accepted")
    library_copy = root / "unverified-libfontconfig.1.dylib"
    library_copy.write_bytes(library.read_bytes() + b"unverified template build")
    import bookscan.fontconfig_probe as probe

    command = [sys.executable, "-I", str(Path(probe.__file__)), str(library_copy)]
    rejected = execute(command, environment=captured)
    if rejected.returncode != 5 or rejected.stdout or not rejected.stderr:
        raise ValueError("Unknown native build guessed a template root")
    outcomes = {
        "absent_root_appearance": appearance,
        "scan_only_bytes_changed": mutation,
        "later_scan_only_include": include,
        "malformed_template": malformed,
    }
    if any(value != ["DEPENDENCY_UNAVAILABLE", 5] for value in outcomes.values()):
        raise ValueError("Wrong template failure class")
    if cache.exists():
        raise ValueError("Configuration-only template discovery built a cache")
    return {
        "outcomes": outcomes,
        "unknown_build_exit": rejected.returncode,
        "wrong_loaded_file_guard_misses_template_changes": True,
        "loaded_scopes_unchanged": True,
        "template_rules_inactive": True,
        "cache_stays_absent": True,
        "absent_scope": absent.record(),
        "parsed_scope": found.record(),
        "include_scope": fresh.record(),
        "unknown_build_command": command,
    }


def optional_include_controls(
    saved: Snapshot,
    renderer: Path,
    fixtures: Path,
    output: Path,
    environment: dict[str, str],
    expected: bytes,
) -> dict[str, object]:
    """An empty include changes native configuration scope without changing RGB."""
    results: dict[str, object] = {}
    for kind in (
        "absolute-file",
        "absolute-directory",
        "relative-file",
        "home-file",
        "xdg-file",
        "xdg-directory",
    ):
        case = output / kind
        case.mkdir()
        home, xdg, search = (case / name for name in ("home", "xdg", "search"))
        for root in (home, xdg, search):
            root.mkdir()
        attributes = 'ignore_missing="yes"'
        if kind.startswith("absolute"):
            target = case / "later"
            include = str(target)
        elif kind == "relative-file":
            target = search / "later.conf"
            include = "later.conf"
        elif kind == "home-file":
            target = home / ".later.conf"
            include = "~/.later.conf"
        else:
            target = xdg / "later"
            include = "later"
            attributes += ' prefix="xdg"'
        config = case / "fonts.conf"
        config.write_text(
            "<fontconfig><dir>"
            + escape(str(fixtures / "fonts-a"))
            + "</dir><cachedir>"
            + escape(str(fixtures / "cache-a"))
            + f"</cachedir><include {attributes}>"
            + escape(include)
            + "</include></fontconfig>\n"
        )
        captured = dict(
            environment,
            FONTCONFIG_FILE=str(config),
            FONTCONFIG_PATH=str(search),
            HOME=str(home),
            XDG_CONFIG_HOME=str(xdg),
        )
        found = discover_fontconfig(renderer, environment=captured)
        if str(target) in found.scope.config_files:
            raise ValueError("Absent include incorrectly reported as loaded")
        stable = render_page(saved, saved.pages[0], renderer, resources=found.binding)
        if stable.rgb != expected:
            raise ValueError("Absent optional include changed glyph pixels")
        # Disprove a guard binding exactly the originally reported subjects.
        # Both resource inventories are identical; only fresh resolution differs.
        weak = ResourceBinding.capture(
            [Path(item.path) for item in found.binding.files],
            optional_directories=[Path(item.path) for item in found.binding.directories],
            environment=captured,
        )
        if weak.record() != {
            name: value
            for name, value in found.binding.record().items()
            if name != "fontconfig_scope_guard"
        }:
            raise ValueError("Wrong guard does not bind the same original subjects")
        post_render: list[object] | None = None
        if kind == "absolute-file":
            decode = cast(Callable[[Path, tuple[int, int]], bytes], getattr(rendering, "_decode"))

            def decode_then_add(path: Path, size: tuple[int, int]) -> bytes:
                rgb = decode(path, size)
                target.write_text("<fontconfig/>\n")
                return rgb

            # Private boundary substitution, retaining actual native execution and
            # PNG decoding: change only after the render, before its final guard.
            setattr(rendering, "_decode", decode_then_add)
            try:
                try:
                    render_page(saved, saved.pages[0], renderer, resources=found.binding)
                except NativeError as error:
                    post_render = [error.code, error.exit_code]
                else:
                    raise ValueError("Post-render include change returned usable pixels")
                if post_render != ["DEPENDENCY_UNAVAILABLE", 5]:
                    raise ValueError("Wrong post-render changed-scope failure")
            finally:
                setattr(rendering, "_decode", decode)
                target.unlink()
        if kind.endswith("directory"):
            target.mkdir()
            (target / "50-added.conf").write_text("<fontconfig/>\n")
        else:
            target.write_text("<fontconfig/>\n")
        weak.verify()
        try:
            render_page(saved, saved.pages[0], renderer, resources=found.binding)
        except NativeError as error:
            rejected = [error.code, error.exit_code]
        else:
            raise ValueError("Later optional include returned usable pixels with stale scope")
        if rejected != ["DEPENDENCY_UNAVAILABLE", 5]:
            raise ValueError("Wrong changed-scope failure")
        unguarded = render_page(saved, saved.pages[0], renderer, resources=weak)
        if unguarded.rgb != expected:
            raise ValueError("Empty new include unexpectedly changed glyph pixels")
        fresh = discover_fontconfig(renderer, environment=captured)
        if str(target) not in fresh.scope.config_files:
            raise ValueError("Fresh native scope omitted the newly available include")
        accepted = render_page(saved, saved.pages[0], renderer, resources=fresh.binding)
        if accepted.rgb != expected:
            raise ValueError("Fresh include binding changed glyph pixels")
        results[kind] = {
            "before": found.record(),
            "after": fresh.record(),
            "changed_scope_rejected": rejected,
            "wrong_original_tree_guard_returns_same_pixels": True,
            "rediscovered_render_sha256": hashlib.sha256(accepted.rgb).hexdigest(),
            "size": list(accepted.size),
            "post_native_change_rejected": post_render,
            "commands": [list(stable.command), list(unguarded.command), list(accepted.command)],
        }
    return results


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    before = resource_acceptance.subjects(fixtures)
    truth = json.loads((fixtures / "truth.json").read_text())
    for name, expected in {**truth["files"], **truth["external_fonts"]}.items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError("Changed font construction subject")
    renderer = renderer_path()
    linked = linked_identity(renderer)
    native = cast(dict[str, object], linked["files"])
    libraries = [name for name in native if Path(name).name == "libfontconfig.1.dylib"]
    if len(libraries) != 1:
        raise ValueError("No unique actual Fontconfig library")
    import bookscan.fontconfig_probe as probe

    probe_path = Path(probe.__file__)
    command = [sys.executable, "-I", str(probe_path), libraries[0]]
    default = execute(command)
    if default.returncode or default.stderr:
        raise ValueError("Default configuration-only native probe failed")
    default_scope = json.loads(default.stdout)
    # Declare outcomes before raster comparison. Equality checks binding semantics,
    # not whole-glyph/source fidelity. Default failure is unavailable, never passed.
    declared = {
        "stable_size": [600, 150],
        "mutated_guard": ["DEPENDENCY_UNAVAILABLE", 5],
        "whole_glyph_truth": "unavailable; configured roots are no independent glyph oracle",
        "default_binding": "configured scope must bind every name, including dangling aliases",
        "optional_includes": "later-loaded absolute/relative/home/XDG scopes reject before RGB",
    }
    (output / "declared.json").write_text(json.dumps(declared, indent=2) + "\n")
    caches = ResourceBinding.capture(
        [], optional_directories=[Path(p) for p in default_scope["cache_dirs"]]
    )
    repeated = execute(command)
    caches.verify()
    if repeated.returncode or repeated.stderr or json.loads(repeated.stdout) != default_scope:
        raise ValueError("Default native enumeration changed")
    try:
        default_found = discover_fontconfig(renderer)
    except NativeError as error:
        default_binding: dict[str, object] = {
            "status": "unavailable",
            "code": error.code,
            "message": str(error),
        }
    else:
        default_binding = {"status": "configured-scope-bound", "record": default_found.record()}
    caches.verify()

    environment = dict(os.environ)
    # FcDebug prints even FC_DEBUG=0; this controlled protocol uses no debug output.
    environment.pop("FC_DEBUG", None)
    environment.update(FONTCONFIG_FILE=str(fixtures / "a.conf"), FONTCONFIG_PATH=str(fixtures))
    found = discover_fontconfig(renderer, environment=environment)
    if (
        str(fixtures / "a.conf") not in found.scope.config_files
        or str(fixtures / "fonts-a") not in found.scope.font_dirs
        or str(fixtures / "cache-a") not in found.scope.cache_dirs
    ):
        raise ValueError("Actual configured roots missing")
    saved = snapshot(fixtures / "source.pdf", output / "snapshot.pdf")
    raster = render_page(saved, saved.pages[0], renderer, resources=found.binding)
    if list(raster.size) != declared["stable_size"]:
        raise ValueError("Wrong native raster dimensions")
    direct = render_page(
        saved,
        saved.pages[0],
        renderer,
        resources=ResourceBinding.capture([], environment=environment),
    )
    if direct.rgb != raster.rgb:
        raise ValueError("Resource binding changed stable native RGB")

    controls: dict[str, object] = {}
    optional = optional_include_controls(saved, renderer, fixtures, output, environment, raster.rgb)
    templates = template_controls(renderer, Path(libraries[0]), output, environment)
    # Output-owned candidate absence and later appearance; no user tree is edited.
    font_root = output / "font-candidates"
    font_root.mkdir()
    (font_root / "Helvetica.ttc").symlink_to(fixtures / "fonts-a" / "Helvetica.ttc")
    absent = output / "absent-font"
    candidate = font_root / ".candidate.ttf"
    candidate.symlink_to(absent)
    candidate_cache = output / "candidate-cache"
    candidate_cache.mkdir()
    candidate_config = output / "candidate.conf"
    candidate_config.write_text(
        "<fontconfig><dir>"
        + escape(str(font_root))
        + "</dir><cachedir>"
        + escape(str(candidate_cache))
        + "</cachedir></fontconfig>\n"
    )
    candidate_env = dict(environment, FONTCONFIG_FILE=str(candidate_config))
    # Warm only this output-owned cache before binding. A cold render legitimately
    # creates cache files and must fail the guard, not count as stable resources.
    warm = render_page(
        saved,
        saved.pages[0],
        renderer,
        resources=ResourceBinding.capture([], environment=candidate_env),
    )
    missing = discover_fontconfig(renderer, environment=candidate_env)
    candidate_tree = next(
        tree for tree in missing.binding.directories if tree.path == str(font_root)
    )
    if candidate_tree.entries is None:
        raise ValueError("Dropped font-candidate tree")
    entry = next(item for item in candidate_tree.entries if item.path == str(candidate))
    if (entry.kind, entry.resolved, entry.link_target, entry.sha256) != (
        "dangling-symlink",
        str(absent),
        str(absent),
        None,
    ):
        raise ValueError("Missing candidate absence record")
    candidate_raster = render_page(saved, saved.pages[0], renderer, resources=missing.binding)
    if candidate_raster.rgb != raster.rgb:
        raise ValueError("Dangling entry changed stable native RGB")
    # A weak guard has the same visible pixels but misses new candidate presence.
    file_only = ResourceBinding.capture([candidate_config], environment=candidate_env)
    absent.write_bytes((fixtures / "fonts-a" / "Helvetica.ttc").read_bytes())
    try:
        render_page(saved, saved.pages[0], renderer, resources=missing.binding)
    except NativeError as error:
        controls["dangling_target_appearance_rejected"] = [error.code, error.exit_code]
    else:
        raise ValueError("New font target returned usable pixels under old binding")
    if controls["dangling_target_appearance_rejected"] != declared["mutated_guard"]:
        raise ValueError("Wrong missing-target failure")
    unguarded = render_page(saved, saved.pages[0], renderer, resources=file_only)
    if unguarded.rgb != raster.rgb:
        raise ValueError("Duplicate font unexpectedly changed stable glyphs")
    controls["wrong_file_only_guard_misses_target_appearance"] = True
    present = discover_fontconfig(renderer, environment=candidate_env)
    present_tree = next(tree for tree in present.binding.directories if tree.path == str(font_root))
    if present_tree.entries is None:
        raise ValueError("Dropped present candidate tree")
    actual = next(item for item in present_tree.entries if item.path == str(candidate))
    if actual.kind != "file" or actual.sha256 != hashlib.sha256(absent.read_bytes()).hexdigest():
        raise ValueError("Rediscovery did not bind the now-readable candidate")
    controls["dangling_candidate_record_and_rediscovery"] = True
    # Output-owned include growth; input fixtures/fonts/caches stay frozen.
    include = output / "includes"
    include.mkdir()
    config = output / "fonts.conf"
    config.write_text(
        "<fontconfig><dir>"
        + escape(str(fixtures / "fonts-a"))
        + "</dir><cachedir>"
        + escape(str(fixtures / "cache-a"))
        + "</cachedir><include>"
        + escape(str(include))
        + "</include></fontconfig>\n"
    )
    changed_env = dict(environment, FONTCONFIG_FILE=str(config))
    guarded = discover_fontconfig(renderer, environment=changed_env)
    if str(include) not in guarded.scope.config_files:
        raise ValueError("Actual parsed include directory missing")
    wrong = ResourceBinding.capture([config], environment=changed_env)
    (include / "50-added.conf").write_text("<fontconfig/>\n")
    try:
        render_page(saved, saved.pages[0], renderer, resources=guarded.binding)
    except NativeError as error:
        controls["include_growth_rejected"] = [error.code, error.exit_code]
    else:
        raise ValueError("Added actual include returned usable pixels")
    if controls["include_growth_rejected"] != declared["mutated_guard"]:
        raise ValueError("Wrong include-growth failure")
    wrong_raster = render_page(saved, saved.pages[0], renderer, resources=wrong)
    if wrong_raster.rgb != raster.rgb:
        raise ValueError("Empty include unexpectedly changed glyph pixels")
    controls["wrong_file_only_guard_returns_pixels"] = True
    fresh = discover_fontconfig(renderer, environment=changed_env)
    if str(include / "50-added.conf") not in fresh.scope.config_files:
        raise ValueError("Rediscovery omitted actual added include")

    # Invalid parsing must fail without fallback scans or cache modifications.
    invalid = output / "invalid.conf"
    invalid.write_text("<fontconfig><unclosed\n")
    frozen_cache = ResourceBinding.capture([], directories=[fixtures / "cache-a"])
    bad_env = dict(environment, FONTCONFIG_FILE=str(invalid))
    failed = execute(command, environment=bad_env)
    frozen_cache.verify()
    if failed.returncode != 5 or failed.stdout or not failed.stderr:
        raise ValueError("Malformed configuration did not fail private parsing")
    controls["malformed_config_without_cache_mutation"] = True
    if before != resource_acceptance.subjects(fixtures):
        raise ValueError("Frozen fixture bytes changed")
    for name, expected in truth["external_fonts"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError("External font changed")
    result: dict[str, object] = {
        "module": str(Path(__import__("bookscan.fontconfig", fromlist=["x"]).__file__).resolve()),
        "default_scope": default_scope,
        "default_binding": default_binding,
        "default_caches_unchanged": True,
        "controlled": found.record(),
        "rediscovered": fresh.record(),
        "controls": controls,
        "optional_include_controls": optional,
        "template_controls": templates,
        "rgb_sha256": hashlib.sha256(raster.rgb).hexdigest(),
        "size": list(raster.size),
        "commands": [
            command,
            list(raster.command),
            list(wrong_raster.command),
            list(candidate_raster.command),
            list(unguarded.command),
            list(warm.command),
        ],
        "subjects_before": before,
        "subjects_after": resource_acceptance.subjects(fixtures),
        "runtime_resources_verified": False,
        "whole_glyph_truth": declared["whole_glyph_truth"],
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.fixtures, args.artifacts)
    print(
        json.dumps(
            {
                "controls": result["controls"],
                "optional_includes": list(
                    cast(dict[str, object], result["optional_include_controls"])
                ),
                "complete_runtime_resources_verified": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
