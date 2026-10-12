"""Exercise copied explicit configuration/fonts/cache with actual Cairo rendering."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

from font_loading_acceptance import subjects
from PIL import Image

from bookscan.fontconfig import prepared_fontconfig_cache, prepared_fontconfig_snapshot
from bookscan.intake import snapshot
from bookscan.native_setup import digest
from bookscan.render import render_page, renderer_path
from bookscan.skew import NativeError


def case(
    fixtures: Path,
    output: Path,
    label: str,
    selection: str = "explicit",
    path_form: str = "absolute",
) -> dict[str, object]:
    output.mkdir()
    host = output / "host"
    fonts, config, rules = host / "fonts", host / "config", host / "config/conf.d"
    if path_form == "font-space":
        fonts = host / "fonts "
    elif path_form == "include-space":
        rules = config / " conf.d "
    font_form = path_form.removeprefix("remap-")
    remapped = path_form.startswith("remap-")
    if font_form.startswith("xdg"):
        fonts = host / "data/fonts"
    elif path_form == "relative-alias":
        fonts = host / "real/fonts"
    for path in (fonts, rules):
        path.mkdir(parents=True)
    source_font = next((fixtures / ("fonts-" + label)).iterdir())
    font = fonts / source_font.name
    shutil.copyfile(source_font, font)
    dangling = path_form.startswith("dangling-")
    absent = host / "never-present"
    aliases: list[Path] = []
    if dangling:
        alias = fonts / ".missing-face"
        aliases.append(alias)
        if path_form == "dangling-chain":
            intermediate = fonts / "intermediate"
            intermediate.symlink_to(absent)
            aliases.append(intermediate)
            alias.symlink_to("intermediate")
        else:
            alias.symlink_to(absent if path_form == "dangling-absolute" else "../never-present")
    cache = host / "cache"
    main = config / "fonts.conf"
    include = (
        '<include prefix="xdg">config/conf.d</include>'
        if path_form.startswith("xdg")
        else "<include>" + escape(str(rules)) + "</include>"
    )
    home_include = path_form.startswith(("home-include", "home-optional"))
    home_prefix = "~" if path_form.endswith("-bare") else "~/"
    if home_include:
        include = "<include>" + home_prefix + "config/conf.d</include>"
    if path_form in {"include-space", "include-relative"}:
        prefix = ' prefix="relative"' if path_form == "include-relative" else ""
        include = "<include" + prefix + ">" + rules.name + "</include>"
    search_include = path_form.startswith("search-")
    other_rules = host / "other/conf.d"
    if search_include:
        include = "<include>conf.d</include>"
        # Load another same-suffix directory independently. Search resolution
        # must still choose the configured first target, rather than guessing.
        other_rules.mkdir(parents=True)
        include += "<include>" + escape(str(other_rules)) + "</include>"
    optional_paths: list[Path] = []
    if "optional" in path_form:
        for index, boolean in enumerate(("yes", "TRUE", "1", "On", "dontcare", "2", "or")):
            optional_paths.append((config if search_include else host) / f"missing-{index}.conf")
            include += (
                "<include"
                + (' prefix="xdg"' if path_form.startswith("xdg") else "")
                + ' ignore_missing="'
                + boolean
                + '">'
                + (home_prefix if home_include else "")
                + f"missing-{index}.conf</include>"
            )
    main.write_text(
        "<fontconfig>" + include + "<cachedir>" + escape(str(cache)) + "</cachedir>"
        '<cachedir prefix="xdg">cache</cachedir></fontconfig>\n'
    )
    rule = rules / "10-font.conf"
    if path_form == "relative-alias":
        rule.symlink_to(host / "real/10-font.conf")
    font_paths = [fonts]
    if font_form.startswith("xdg"):
        font_paths.extend([host / "system/fonts", host / "other/fonts"])
        for path in font_paths[1:]:
            path.mkdir(parents=True)
            shutil.copyfile(source_font, path / source_font.name)
        font_element = '<dir prefix="xdg" salt="fixture">fonts</dir>'
    elif font_form.startswith("relative"):
        value = "fonts" if path_form == "relative-alias" else "../../fonts"
        font_element = '<dir prefix="relative">' + value + "</dir>"
    elif path_form == "cwd":
        font_element = '<dir prefix="cwd">' + escape(os.path.relpath(fonts)) + "</dir>"
    elif font_form == "home":
        font_element = "<dir>~/fonts</dir>"
    else:
        font_element = "<dir>" + escape(str(fonts)) + "</dir>"
    logical_path = "/bookscan-logical-cache/fonts"
    if font_form == "logical-home":
        logical_path = "~/logical-cache/fonts"
    elif font_form == "logical-relative":
        logical_path = "logical-cache/fonts"
    salt = "remap&fixture"
    if remapped:
        font_element = font_element.replace(
            "<dir", '<remap-dir as-path="' + logical_path + '" salt="' + escape(salt) + '"'
        ).replace("</dir>", "</remap-dir>")
        # XDG dir's existing salt is replaced by this remap's cache identity.
        font_element = font_element.replace(' salt="fixture"', "")
        if font_form == "override":
            font_element += '<dir salt="last">' + escape(str(fonts)) + "</dir>"
    rule.write_text(
        "<fontconfig>" + font_element + '<match target="font"><edit name="antialias" mode="assign">'
        "<bool>false</bool></edit></match></fontconfig>\n"
    )
    environment = dict(os.environ, FONTCONFIG_PATH=str(config), XDG_CACHE_HOME=str(host))
    if search_include:
        search_roots = str(config) + ":" + str(host / "other") + ":"
        if path_form == "search-second":
            search_roots = str(host / "absent") + ":" + search_roots
        elif path_form == "search-relative":
            search_roots = os.path.relpath(config) + ":" + os.path.relpath(host / "other")
        elif path_form == "search-empty":
            search_roots = "::" + search_roots
        environment["FONTCONFIG_PATH"] = search_roots
    if path_form != "absolute":
        environment["HOME"] = str(host)
    if font_form.startswith("xdg"):
        environment.update(
            XDG_CONFIG_HOME=str(host),
            XDG_DATA_HOME=str(host / "data"),
            XDG_DATA_DIRS=str(host / "system") + "::" + str(host / "other") + "/",
        )
    for key in ("FC_DEBUG", "FONTCONFIG_SYSROOT", "DYLD_INSERT_LIBRARIES", "DYLD_PRINT_LIBRARIES"):
        environment.pop(key, None)
    environment.pop("FONTCONFIG_FILE", None)
    if selection == "environment":
        environment["FONTCONFIG_FILE"] = "fonts.conf"
    direct_environment = dict(environment, FONTCONFIG_FILE=str(main))
    renderer = renderer_path()
    saved = snapshot(fixtures / "source.pdf", output / "source.pdf")
    root = output / "private"
    truth: dict[str, object] = {
        "selection": selection,
        "size": [600, 150],
        "font_sha256": digest(font),
        "font_rule_sha256": digest(rule),
        "copied_font_rule_sha256": hashlib.sha256(
            rule.read_bytes().replace(
                font_element.encode(),
                "".join(
                    ("<remap-dir" if remapped else "<dir")
                    + (
                        ' as-path="' + logical_path + '" salt="' + escape(salt) + '"'
                        if remapped
                        else ' salt="fixture"'
                        if path_form.startswith("xdg")
                        else ""
                    )
                    + ">"
                    + escape(str(root / str(path).lstrip("/")))
                    + ("</remap-dir>" if remapped else "</dir>")
                    for path in font_paths
                ).encode()
                + (
                    (
                        '<dir salt="last">' + escape(str(root / str(fonts).lstrip("/"))) + "</dir>"
                    ).encode()
                    if remapped and font_form == "override"
                    else b""
                ),
            )
        ).hexdigest(),
        "before_after_rgb_exact": True,
        "host_loss_rgb_exact": True,
        "snapshot_removed": True,
        "mutation_outcome": ["DEPENDENCY_UNAVAILABLE", 5],
        "runtime_resources_verified": False,
    }
    if optional_paths:
        truth["optional_include_count"] = len(optional_paths)
        truth["optional_appearance_outcome"] = ["DEPENDENCY_UNAVAILABLE", 5]
    if dangling:
        truth["dangling_names"] = sorted(path.name for path in aliases)
        truth["dangling_target_appearance"] = ["DEPENDENCY_UNAVAILABLE", 5]
    if remapped:
        logical_key = (
            str(host / "logical-cache/fonts")
            if font_form == "logical-home"
            else str(Path.cwd() / "logical-cache/fonts")
            if font_form == "logical-relative"
            else logical_path
        )
        keys = (
            [str(root / str(fonts).lstrip("/")) + "last"]
            if font_form == "override"
            else [logical_key + salt]
        )
        # FcDirCacheBasenameMD5 hashes the mapped directory plus salt. Derive
        # the expected keys before any native cache/render, never from outputs.
        # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccache.c
        truth["cache_key_prefixes"] = sorted(hashlib.md5(key.encode()).hexdigest() for key in keys)
        truth["wrong_cache_key_refused"] = True
    (output / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    frozen = subjects(host)
    with prepared_fontconfig_cache(renderer, cache, environment=direct_environment) as direct:
        original = render_page(saved, saved.pages[0], renderer, resources=direct.binding)
    if subjects(host) != frozen:
        raise ValueError("Original-resource render changed a fixture")
    with prepared_fontconfig_snapshot(
        renderer, root, main if selection == "explicit" else None, environment=environment
    ) as found:
        copied_font = root / str(font).lstrip("/")
        copied_rule = root / str(rule).lstrip("/")
        if (
            digest(copied_font) != truth["font_sha256"]
            or digest(copied_rule) != truth["copied_font_rule_sha256"]
        ):
            raise ValueError("Copied font/rules did not retain original bytes")
        if set(found.scope.effective_font_dirs) != {
            str(root / str(path).lstrip("/")) for path in font_paths
        }:
            raise ValueError("Native scope resolved outside the copied font directory")
        if remapped:
            cache_files = sorted((root / "bookscan-private-font-cache").glob("*.cache-9"))
            prefixes = sorted({path.name.split("-", 1)[0] for path in cache_files})
            if prefixes != truth["cache_key_prefixes"]:
                raise ValueError("Native cache lost the constructed remap/order/salt identity")
            wrong = [hashlib.md5((logical_path + "wrong-salt").encode()).hexdigest()]
            if prefixes == wrong:
                raise ValueError("Wrong logical cache-key control was accepted")
        if search_include:
            includes = ET.parse(root / str(main).lstrip("/")).findall("include")
            expected = [str(root / str(path).lstrip("/")) for path in (rules, other_rules)]
            if [element.text for element in includes[:2]] != expected:
                raise ValueError("Copied include chose a different search target")
        if path_form in {"include-space", "include-relative"}:
            target = ET.parse(root / str(main).lstrip("/")).findtext("include")
            if target != str(root / str(rules).lstrip("/")):
                raise ValueError("Copied include changed its exact native target")
        if dangling:
            missing = root / str(absent).lstrip("/")
            copied_aliases = [root / str(path).lstrip("/") for path in aliases]
            if any(
                not path.is_symlink() or path.exists() or path.readlink() != missing
                for path in copied_aliases
            ):
                raise ValueError("Copied missing font names were dropped or escaped the copy")
            missing.parent.mkdir(parents=True, exist_ok=True)
            missing.write_bytes(font.read_bytes())
            try:
                render_page(saved, saved.pages[0], renderer, resources=found.binding)
            except NativeError as error:
                if [error.code, error.exit_code] != truth["dangling_target_appearance"]:
                    raise ValueError("Wrong copied-target appearance outcome") from error
            else:
                raise ValueError("New dangling font target reached native rendering")
            finally:
                missing.unlink()
            found.binding.verify()
        first = render_page(saved, saved.pages[0], renderer, resources=found.binding)
        if first.rgb != original.rgb or first.size != (600, 150) or first.diagnostics:
            raise ValueError("Private-resource render differs from original-resource render")
        if optional_paths:
            private_paths = [root / str(path).lstrip("/") for path in optional_paths]
            includes = ET.parse(root / str(main).lstrip("/")).findall("include")
            if [element.text for element in includes[2 if search_include else 1 :]] != [
                str(path) for path in private_paths
            ]:
                raise ValueError("Missing optional includes were removed or escaped the copy")
            if any(path.exists() or path.is_symlink() for path in private_paths):
                raise ValueError("Optional include absence changed during copying")
            # Native scope rediscovery must catch a newly appearing private rule,
            # even though the immutable loaded files have not changed.
            appeared = private_paths[0]
            appeared.parent.mkdir(parents=True, exist_ok=True)
            appeared.write_text("<fontconfig/>")
            try:
                found.binding.verify()
            except NativeError as error:
                appearance = [error.code, error.exit_code]
                if appearance != truth["optional_appearance_outcome"]:
                    raise ValueError("Wrong optional-include appearance outcome") from error
            else:
                raise ValueError("Appearing optional include escaped native scope guard")
            finally:
                appeared.unlink()
            found.binding.verify()
        # This is a test-owned source directory, not a user source. Remove its
        # original paths to prove that the retained context uses copied resources.
        host.rename(output / "detached-host")
        after_loss = render_page(saved, saved.pages[0], renderer, resources=found.binding)
        for name, raster in (("before-host-loss", first), ("after-host-loss", after_loss)):
            with Image.frombytes("RGB", raster.size, raster.rgb) as image:
                image.save(output / (name + ".png"))
        if after_loss.rgb != original.rgb:
            raise ValueError("Original resource disappearance changed private rendering")
        font_bytes = copied_font.read_bytes()
        copied_font.write_bytes(b"wrong copied font")
        try:
            render_page(saved, saved.pages[0], renderer, resources=found.binding)
        except NativeError as error:
            mutation = [error.code, error.exit_code]
        else:
            raise ValueError("A changed copied font reached rendering")
        copied_font.write_bytes(font_bytes)
        found.binding.verify()
        # Exact copied config/fonts/templates/completed cache retained before exit.
        shutil.copytree(root, output / "private-copy", symlinks=True)
        record = found.record()
        provenance = record["resource_snapshot"]
        if not isinstance(provenance, dict) or provenance["configuration_file"] != str(main):
            raise ValueError("Snapshot selected an included rule instead of the configuration")
        with Image.frombytes("RGB", first.size, first.rgb) as image:
            image.save(output / "baseline.png")
        with Image.frombytes("RGB", original.size, original.rgb) as image:
            image.save(output / "original-resource.png")
    if root.exists() or mutation != truth["mutation_outcome"]:
        raise ValueError("Incorrect snapshot cleanup/mutation refusal")
    result: dict[str, object] = {
        **truth,
        "rgb_sha256": hashlib.sha256(first.rgb).hexdigest(),
        "mutation_outcome": mutation,
        "binding": record,
        "limitation": (
            "Controlled explicit configuration copy/render equivalence only; "
            "ordinary default path forms, complete native resources/reads and independent "
            "glyph/full-page truth remain unfinished."
        ),
    }
    # Keep preceding absolute-path evidence's public/private record exact.
    if path_form != "absolute":
        result["path_form"] = path_form
        result["font_roots"] = [str(path) for path in font_paths]
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def run(
    fixtures: Path, output: Path, selection: str = "explicit", path_form: str = "absolute"
) -> None:
    before = subjects(fixtures)
    output.mkdir()
    results = {
        label: case(fixtures, output / label, label, selection, path_form) for label in ("a", "b")
    }
    if results["a"]["rgb_sha256"] == results["b"]["rgb_sha256"]:
        raise ValueError("Different controlled font identities were not distinguished")
    if subjects(fixtures) != before:
        raise ValueError("Input fixtures changed")
    (output / "result.json").write_text(json.dumps(results, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument(
        "--selection", choices=("explicit", "default", "environment"), default="explicit"
    )
    parser.add_argument(
        "--path-form",
        choices=(
            "absolute",
            "xdg",
            "xdg-optional",
            "relative",
            "relative-alias",
            "cwd",
            "home",
            "home-include",
            "home-include-bare",
            "home-optional",
            "home-optional-bare",
            "search-first",
            "search-second",
            "search-relative",
            "search-empty",
            "search-optional",
            "remap-absolute",
            "remap-relative",
            "remap-home",
            "remap-xdg",
            "remap-override",
            "remap-logical-home",
            "remap-logical-relative",
            "font-space",
            "include-space",
            "include-relative",
            "dangling-absolute",
            "dangling-relative",
            "dangling-chain",
        ),
        default="absolute",
    )
    args = parser.parse_args()
    run(args.fixtures.resolve(), args.artifacts.resolve(), args.selection, args.path_form)
    print(
        json.dumps(
            {
                "selection": args.selection,
                "controlled_fonts": 2,
                "runtime_resources_verified": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
