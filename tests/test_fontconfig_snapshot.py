"""Copy ownership must sever host dependencies without changing font rules."""

import os
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path
from typing import cast
from xml.sax.saxutils import escape, quoteattr

import pytest

from bookscan import fontconfig
from bookscan.fontconfig import ConfiguredScope, FontconfigDiscovery
from bookscan.resources import ResourceBinding
from bookscan.skew import NativeError


@pytest.mark.parametrize(
    "kind",
    [
        "xdg",
        "xdg-empty-dirs",
        "xdg-fallback",
        "relative",
        "relative-alias",
        "cwd",
        "default",
        "home",
    ],
)
def test_copy_resolves_font_paths_from_original_captured_context(
    inputs: FontconfigDiscovery, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    # Catches dropping an XDG root, using ambient HOME/cwd, or resolving a
    # relative directory against the copied/symlink-spelling configuration.
    host = Path(inputs.scope.font_dirs[0]).parent
    rule = Path(inputs.scope.parsed_files[1])
    environment = {"HOME": str(host), "XDG_DATA_HOME": str(host / "data")}
    if kind.startswith("xdg"):
        prefix, value = "xdg", "fonts"
        if kind == "xdg":
            environment["XDG_DATA_DIRS"] = str(host / "system") + "::" + str(host / "other") + "/"
            roots = [host / "data/fonts", host / "system/fonts", host / "other/fonts"]
        else:
            environment["XDG_DATA_DIRS"] = ""
            roots = [host / "data/fonts", Path("/usr/local/share/fonts"), Path("/usr/share/fonts")]
            if kind == "xdg-fallback":
                del environment["XDG_DATA_HOME"]
                roots[0] = host / ".local/share/fonts"
    elif kind == "relative-alias":
        real = host / "real"
        real.mkdir()
        rule.unlink()
        rule.symlink_to(real / "rule.conf")
        prefix, value, roots = "relative", "fonts", [real / "fonts"]
    elif kind == "relative":
        prefix, value, roots = "relative", "../fonts", [host / "fonts"]
    elif kind == "home":
        prefix, value, roots = "cwd", "~/fonts", [host / "fonts"]
    else:
        prefix, value, roots = kind, "host/fonts", [host / "fonts"]
        monkeypatch.chdir(tmp_path)
    rules = b'<match><test name="family"><string>Old</string></test></match>'
    rule.write_bytes(
        b'<fontconfig><dir prefix="'
        + prefix.encode()
        + b'" salt="keep">'
        + value.encode()
        + b"</dir>"
        + rules
        + b"</fontconfig>"
    )
    # System fallback roots are bound as absent/existing subjects, not written.
    for path in roots:
        if path.is_relative_to(host):
            path.mkdir(parents=True, exist_ok=True)
            (path / "owned-face").write_bytes(b"controlled font")
    scope = replace(
        inputs.scope,
        font_dirs=tuple(str(p) for p in roots),
        effective_font_dirs=tuple(str(p) for p in roots),
    )
    bound = ResourceBinding.capture(
        [Path(p) for p in scope.parsed_files],
        directories=[Path(p) for p in scope.config_dirs],
        optional_directories=roots,
        environment=environment,
    )
    found = FontconfigDiscovery(scope, bound, inputs.linked)
    root = tmp_path / "private"
    root.mkdir()
    fontconfig.copy_fontconfig_inputs(found, root)
    raw = (root / str(rule).lstrip("/")).read_bytes()
    expected_dirs = b"".join(
        b'<dir salt="keep">' + str(root / str(p).lstrip("/")).encode() + b"</dir>" for p in roots
    )
    assert raw == b"<fontconfig>" + expected_dirs + rules + b"</fontconfig>"
    for path in roots:
        if path.is_relative_to(host):
            assert (root / str(path).lstrip("/") / "owned-face").read_bytes() == b"controlled font"


@pytest.mark.parametrize("fallback", [False, True])
def test_copy_resolves_loaded_xdg_include_without_suffix_guessing(
    inputs: FontconfigDiscovery, tmp_path: Path, fallback: bool
) -> None:
    # Catches confusing a loaded XDG include with a same-name configuration
    # elsewhere, or accidentally evaluating the current process environment.
    main = Path(inputs.scope.parsed_files[0])
    home = main.parent.parent
    config = home / (".config" if fallback else "xdg-config")
    config.mkdir()
    extra = config / "rules.conf"
    extra.write_text("<fontconfig><!-- XDG rule --></fontconfig>")
    main.write_text('<fontconfig><include prefix="xdg">rules.conf</include></fontconfig>')
    environment = {"HOME": str(home)}
    if not fallback:
        environment["XDG_CONFIG_HOME"] = str(config)
    scope = replace(
        inputs.scope,
        config_files=(*inputs.scope.config_files, str(extra)),
        parsed_files=(*inputs.scope.parsed_files, str(extra)),
    )
    found = FontconfigDiscovery(
        scope,
        ResourceBinding.capture(
            [Path(p) for p in scope.parsed_files],
            directories=[Path(p) for p in (*scope.config_dirs, *scope.font_dirs)],
            environment=environment,
        ),
        inputs.linked,
    )
    root = tmp_path / "private"
    root.mkdir()
    fontconfig.copy_fontconfig_inputs(found, root)
    copied = ET.parse(root / str(main).lstrip("/"))
    assert copied.findtext("include") == str(root / str(extra).lstrip("/"))
    assert (root / str(extra).lstrip("/")).read_bytes() == extra.read_bytes()


@pytest.mark.parametrize("kind", ["extra-font-root", "same-name-include"])
def test_path_expansion_cannot_import_an_unbound_destination(
    inputs: FontconfigDiscovery, tmp_path: Path, kind: str
) -> None:
    # Catches a partial <=known-roots pass and substituting a loaded include
    # solely because its basename matches the configured XDG destination.
    main = Path(inputs.scope.parsed_files[0])
    environment = {
        "XDG_DATA_HOME": str(Path(inputs.scope.font_dirs[0]).parent),
        "XDG_DATA_DIRS": str(tmp_path / "foreign"),
        "XDG_CONFIG_HOME": str(tmp_path / "foreign-config"),
    }
    main.write_text(
        '<fontconfig><dir prefix="xdg">fonts</dir></fontconfig>'
        if kind == "extra-font-root"
        else '<fontconfig><include prefix="xdg">rules.conf</include></fontconfig>'
    )
    found = replace(
        inputs,
        binding=ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[Path(p) for p in (*inputs.scope.config_dirs, *inputs.scope.font_dirs)],
            environment=environment,
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    with pytest.raises(NativeError):
        fontconfig.copy_fontconfig_inputs(found, root)


@pytest.mark.parametrize("optional", ["yes", "TRUE", "1", "On", "dontcare", "2", "or"])
def test_copy_keeps_missing_optional_xdg_include_private(
    inputs: FontconfigDiscovery, tmp_path: Path, optional: str
) -> None:
    # Removing the include or pointing it back at the host fails this contract.
    main = Path(inputs.scope.parsed_files[0])
    parent = main.parent / "missing-config"
    main.write_text(
        '<fontconfig><!-- keep --><include prefix="xdg" ignore_missing="'
        + optional
        + '" deprecated="yes">missing.conf</include></fontconfig>'
    )
    found = replace(
        inputs,
        binding=ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[Path(p) for p in (*inputs.scope.config_dirs, *inputs.scope.font_dirs)],
            environment={"XDG_CONFIG_HOME": str(parent)},
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    fontconfig.copy_fontconfig_inputs(found, root)
    raw = (root / str(main).lstrip("/")).read_bytes()
    private_missing = root / str(parent / "missing.conf").lstrip("/")
    assert (
        raw
        == (
            '<fontconfig><!-- keep --><include ignore_missing="'
            + optional
            + '" deprecated="yes">'
            + str(private_missing)
            + "</include></fontconfig>"
        ).encode()
    )
    assert not private_missing.exists()
    assert not private_missing.is_symlink()


@pytest.mark.parametrize("kind", ["required", "false", "unknown", "file", "directory", "link"])
def test_optional_include_cannot_bypass_bound_loaded_scope(
    inputs: FontconfigDiscovery, tmp_path: Path, kind: str
) -> None:
    main = Path(inputs.scope.parsed_files[0])
    parent = tmp_path / "foreign-config"
    parent.mkdir()
    target = parent / "missing.conf"
    if kind == "file":
        target.write_text("<fontconfig/>")
    elif kind == "directory":
        target.mkdir()
    elif kind == "link":
        target.symlink_to(parent / "absent")
    optional = {
        "required": "",
        "false": ' ignore_missing="false"',
        "unknown": ' ignore_missing="?"',
    }
    main.write_text(
        '<fontconfig><include prefix="xdg"'
        + optional.get(kind, ' ignore_missing="yes"')
        + ">missing.conf</include></fontconfig>"
    )
    found = replace(
        inputs,
        binding=ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[Path(p) for p in (*inputs.scope.config_dirs, *inputs.scope.font_dirs)],
            environment={"XDG_CONFIG_HOME": str(parent)},
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    with pytest.raises(NativeError):
        fontconfig.copy_fontconfig_inputs(found, root)


@pytest.mark.parametrize("value", ["~/config/rules.conf", "~config/rules.conf"])
@pytest.mark.parametrize("prefix", [None, "cwd", "default"])
def test_copy_resolves_home_include_using_captured_native_join(
    inputs: FontconfigDiscovery, tmp_path: Path, value: str, prefix: str | None
) -> None:
    # Catches suffix guessing, ambient HOME and font-dir tilde concatenation.
    main = Path(inputs.scope.parsed_files[0])
    attr = "" if prefix is None else ' prefix="' + prefix + '"'
    main.write_text("<fontconfig><include" + attr + ">" + value + "</include></fontconfig>")
    found = replace(
        inputs,
        binding=ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[Path(p) for p in (*inputs.scope.config_dirs, *inputs.scope.font_dirs)],
            environment={"HOME": str(main.parent.parent)},
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    fontconfig.copy_fontconfig_inputs(found, root)
    copied = ET.parse(root / str(main).lstrip("/"))
    target = root / inputs.scope.parsed_files[1].lstrip("/")
    assert copied.findtext("include") == str(target)
    assert target.is_file()


@pytest.mark.parametrize("value", ["~/missing.conf", "~missing.conf"])
def test_copy_keeps_optional_home_include_absent_inside_private_namespace(
    inputs: FontconfigDiscovery, tmp_path: Path, value: str
) -> None:
    # Dropping an absent boundary or retaining its host path breaks isolation.
    main = Path(inputs.scope.parsed_files[0])
    main.write_text(
        '<fontconfig><include ignore_missing="yes" deprecated="yes">'
        + value
        + "</include></fontconfig>"
    )
    found = replace(
        inputs,
        binding=ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[Path(p) for p in (*inputs.scope.config_dirs, *inputs.scope.font_dirs)],
            environment={"HOME": str(main.parent.parent)},
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    fontconfig.copy_fontconfig_inputs(found, root)
    element = ET.parse(root / str(main).lstrip("/")).find("include")
    assert element is not None
    missing = root / str(main.parent.parent / "missing.conf").lstrip("/")
    assert element.text == str(missing)
    assert element.attrib == {"ignore_missing": "yes", "deprecated": "yes"}
    assert not missing.exists() and not missing.is_symlink()


@pytest.mark.parametrize("form", ["home", "absolute"])
@pytest.mark.parametrize("kind", ["required", "false", "unknown", "file", "directory", "link"])
def test_home_and_absolute_includes_cannot_bypass_loaded_scope(
    inputs: FontconfigDiscovery, tmp_path: Path, form: str, kind: str
) -> None:
    # Catches redirecting an unbound existing/required input into a silent absence.
    main = Path(inputs.scope.parsed_files[0])
    home = tmp_path / "foreign"
    home.mkdir()
    target = home / "missing.conf"
    if kind == "file":
        target.write_text("<fontconfig/>")
    elif kind == "directory":
        target.mkdir()
    elif kind == "link":
        target.symlink_to(home / "absent")
    attr = {
        "required": "",
        "false": ' ignore_missing="false"',
        "unknown": ' ignore_missing="?"',
    }.get(kind, ' ignore_missing="yes"')
    value = "~/missing.conf" if form == "home" else str(target)
    main.write_text("<fontconfig><include" + attr + ">" + value + "</include></fontconfig>")
    found = replace(
        inputs,
        binding=ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[Path(p) for p in (*inputs.scope.config_dirs, *inputs.scope.font_dirs)],
            environment={"HOME": str(home)},
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    with pytest.raises(NativeError):
        fontconfig.copy_fontconfig_inputs(found, root)


@pytest.mark.parametrize("prefix", [None, "cwd", "default", "relative", "home", "xdg"])
@pytest.mark.parametrize("map_path", ["/logical/fonts", "~/logical", "relative-map", ""])
def test_copy_preserves_remap_cache_identity_and_rule_order(
    inputs: FontconfigDiscovery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prefix: str | None,
    map_path: str,
) -> None:
    # Dropping the remap, mirroring its logical key or losing salt/order changes
    # cache identity. Reading the logical key would import an unbound font tree.
    rule = Path(inputs.scope.parsed_files[1])
    fonts = Path(inputs.scope.font_dirs[0])
    host = fonts.parent
    attr = "" if prefix is None or prefix == "home" else ' prefix="' + prefix + '"'
    value = {
        "cwd": "host/fonts",
        "default": "host/fonts",
        "relative": "../fonts",
        "home": "~/fonts",
        "xdg": "fonts",
    }.get(prefix or "", str(fonts))
    map_attr = " as-path=" + quoteattr(map_path) + ' salt="kept&amp;salt"'
    before = '<dir salt="first">' + str(fonts) + "</dir>"
    remap = "<remap-dir" + attr + map_attr + ">" + value + "</remap-dir>"
    after = '<dir salt="last">' + str(fonts) + "</dir>"
    rule.write_text("<fontconfig>" + before + remap + after + "</fontconfig>")
    roots = [fonts]
    monkeypatch.chdir(tmp_path)
    environment = {"HOME": str(host), "XDG_DATA_HOME": str(host)}
    if prefix == "xdg":
        environment["XDG_DATA_DIRS"] = str(host / "other")
        roots.append(host / "other/fonts")
        roots[-1].mkdir(parents=True)
        (roots[-1] / "face").write_bytes(b"other owned font")
    scope = replace(
        inputs.scope,
        font_dirs=tuple(str(p) for p in roots),
        effective_font_dirs=tuple(str(p) for p in roots),
    )
    found = replace(
        inputs,
        scope=scope,
        binding=ResourceBinding.capture(
            [Path(p) for p in scope.parsed_files],
            directories=[Path(p) for p in (*scope.config_dirs, *scope.font_dirs)],
            environment=environment,
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    fontconfig.copy_fontconfig_inputs(found, root)
    private_fonts = escape(str(root / str(fonts).lstrip("/")))
    expected = (
        '<fontconfig><dir salt="first">'
        + private_fonts
        + "</dir>"
        + "".join(
            "<remap-dir" + map_attr + ">" + escape(str(root / str(p).lstrip("/"))) + "</remap-dir>"
            for p in roots
        )
        + '<dir salt="last">'
        + private_fonts
        + "</dir></fontconfig>"
    )
    assert (root / str(rule).lstrip("/")).read_text() == expected
    assert (root / str(fonts).lstrip("/") / "face").read_bytes() == b"font bytes"
    assert not (root / "logical").exists()


@pytest.mark.parametrize("kind", ["missing-map", "empty-font", "foreign-font", "nested"])
def test_copy_refuses_incomplete_or_unbound_remap(
    inputs: FontconfigDiscovery, tmp_path: Path, kind: str
) -> None:
    rule = Path(inputs.scope.parsed_files[1])
    value = (
        ""
        if kind == "empty-font"
        else str(tmp_path / "foreign")
        if kind == "foreign-font"
        else inputs.scope.font_dirs[0]
    )
    attr = "" if kind == "missing-map" else ' as-path="/logical/fonts"'
    raw = "<remap-dir" + attr + ">" + value + "</remap-dir>"
    if kind == "nested":
        raw = "<match>" + raw + "</match>"
    rule.write_text("<fontconfig>" + raw + "</fontconfig>")
    found = replace(
        inputs,
        binding=ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[Path(p) for p in (*inputs.scope.config_dirs, *inputs.scope.font_dirs)],
            environment={},
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    with pytest.raises(NativeError):
        fontconfig.copy_fontconfig_inputs(found, root)


@pytest.fixture
def inputs(tmp_path: Path) -> FontconfigDiscovery:
    host = tmp_path / "host"
    config = host / "config"
    fonts = host / "fonts"
    templates = host / "templates"
    for path in (config, fonts, templates):
        path.mkdir(parents=True)
    (fonts / "face").write_bytes(b"font bytes")
    (fonts / "alias").symlink_to(fonts / "face")
    (fonts / ".hidden").write_bytes(b"hidden font candidate")
    main = config / "fonts.conf"
    main.write_text(
        "<fontconfig><include>" + str(config / "rules.conf") + "</include>"
        '<cachedir prefix="xdg">fontconfig</cachedir></fontconfig>'
    )
    rule = config / "rules.conf"
    rule.write_text(
        "<fontconfig><dir>" + str(fonts) + "</dir>"
        '<match target="pattern"><test name="family"><string>Old</string></test>'
        '<edit name="family" mode="assign"><string>New</string></edit></match>'
        "<cachedir>" + str(host / "cache") + "</cachedir></fontconfig>"
    )
    (templates / "unloaded.conf").write_text("<fontconfig/>")
    scope = ConfiguredScope(
        (str(main), str(rule)),
        (str(config),),
        (str(fonts),),
        (str(host / "cache"),),
        (str(templates),),
        (str(main), str(rule)),
        (str(fonts),),
        (str(host / "cache"),),
    )
    binding = ResourceBinding.capture(
        [main, rule], directories=[config, fonts, templates], environment={}
    )
    return FontconfigDiscovery(scope, binding, {"files": {}})


@pytest.mark.parametrize("prefix", [None, "cwd", "default", "relative"])
@pytest.mark.parametrize("form", ["first", "second", "relative", "empty-segment"])
def test_copy_uses_captured_include_search_order_instead_of_loaded_suffixes(
    inputs: FontconfigDiscovery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prefix: str | None,
    form: str,
) -> None:
    # Choosing a suffix match, sorting roots or using ambient cwd/PATH breaks this.
    main = Path(inputs.scope.parsed_files[0])
    first, second = tmp_path / "z-first", tmp_path / "a-second"
    for directory in (first, second):
        directory.mkdir()
    one, two = first / "rules.conf", second / "rules.conf"
    if form != "second":
        one.write_text("<fontconfig><!-- first --></fontconfig>")
    two.write_text("<fontconfig><!-- second --></fontconfig>")
    attr = "" if prefix is None else ' prefix="' + prefix + '"'
    main.write_text("<fontconfig><include" + attr + ">rules.conf</include></fontconfig>")
    roots = str(first) + ":" + str(second) + ":"
    if form == "relative":
        roots = os.path.relpath(first) + ":" + os.path.relpath(second)
    elif form == "empty-segment":
        roots = ":" + roots
    loaded = tuple(str(path) for path in (one, two) if path.exists())
    scope = replace(
        inputs.scope,
        config_files=(*inputs.scope.config_files, *loaded),
        parsed_files=(*inputs.scope.parsed_files, *loaded),
    )
    found = FontconfigDiscovery(
        scope,
        ResourceBinding.capture(
            [Path(p) for p in scope.parsed_files],
            directories=[Path(p) for p in (*scope.config_dirs, *scope.font_dirs)],
            environment={"FONTCONFIG_PATH": roots},
        ),
        inputs.linked,
    )
    root = tmp_path / "private"
    root.mkdir()
    monkeypatch.chdir(tmp_path)
    fontconfig.copy_fontconfig_inputs(found, root)
    target = two if form == "second" else one
    element = ET.parse(root / str(main).lstrip("/")).find("include")
    assert element is not None
    assert element.text == str(root / str(target).lstrip("/"))
    assert element.attrib == {}
    assert (root / str(target).lstrip("/")).read_bytes() == target.read_bytes()


@pytest.mark.parametrize("form", ["absolute", "relative", "empty-segment"])
def test_copy_keeps_missing_optional_search_include_private(
    inputs: FontconfigDiscovery, tmp_path: Path, form: str
) -> None:
    # Dropping the boundary or using cwd instead of the search root fails.
    main = Path(inputs.scope.parsed_files[0])
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    roots = str(first) + ":" + str(second)
    if form == "relative":
        roots = os.path.relpath(first) + ":" + os.path.relpath(second)
    elif form == "empty-segment":
        roots = ":" + roots
    name = "bookscan-missing-search-include.conf"
    main.write_text(
        '<fontconfig><include ignore_missing="yes" deprecated="yes">'
        + name
        + "</include></fontconfig>"
    )
    found = replace(
        inputs,
        binding=ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[Path(p) for p in (*inputs.scope.config_dirs, *inputs.scope.font_dirs)],
            environment={"FONTCONFIG_PATH": roots},
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    fontconfig.copy_fontconfig_inputs(found, root)
    target = Path("/") / name if form == "empty-segment" else first / name
    element = ET.parse(root / str(main).lstrip("/")).find("include")
    assert element is not None
    assert element.text == str(root / str(target).lstrip("/"))
    assert element.attrib == {"ignore_missing": "yes", "deprecated": "yes"}
    assert not (root / str(target).lstrip("/")).exists()


@pytest.mark.parametrize("kind", ["file", "directory", "link", "required", "false", "empty"])
def test_search_include_cannot_substitute_a_loaded_suffix_for_an_unbound_target(
    inputs: FontconfigDiscovery, tmp_path: Path, kind: str
) -> None:
    # A unique loaded rules.conf must not mask a different first search target.
    main = Path(inputs.scope.parsed_files[0])
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    target = foreign / "rules.conf"
    if kind == "file":
        target.write_text("<fontconfig/>")
    elif kind == "directory":
        target.mkdir()
    elif kind == "link":
        target.symlink_to(foreign / "absent")
    attr = (
        ""
        if kind == "required"
        else ' ignore_missing="false"'
        if kind == "false"
        else ' ignore_missing="yes"'
    )
    main.write_text(
        "<fontconfig><include"
        + attr
        + ">"
        + ("" if kind == "empty" else "rules.conf")
        + "</include></fontconfig>"
    )
    found = replace(
        inputs,
        binding=ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[Path(p) for p in (*inputs.scope.config_dirs, *inputs.scope.font_dirs)],
            environment={"FONTCONFIG_PATH": str(foreign)},
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    with pytest.raises(NativeError):
        fontconfig.copy_fontconfig_inputs(found, root)


def test_mirror_copies_aliases_hidden_members_and_preserves_rules(
    inputs: FontconfigDiscovery, tmp_path: Path
) -> None:
    root = tmp_path / "private"
    root.mkdir()
    fontconfig.copy_fontconfig_inputs(inputs, root)
    fonts = root / inputs.scope.font_dirs[0].lstrip("/")
    assert (fonts / "face").read_bytes() == b"font bytes"
    assert (fonts / "alias").read_bytes() == b"font bytes"
    assert not (fonts / "alias").is_symlink()
    assert (fonts / ".hidden").read_bytes() == b"hidden font candidate"
    rule = ET.parse(root / inputs.scope.parsed_files[1].lstrip("/"))
    assert rule.findtext("match/edit/string") == "New"
    assert rule.findtext("dir") == str(fonts)
    assert rule.findtext("cachedir") == str(root / "bookscan-private-font-cache")
    assert rule.find("cachedir").attrib == {}  # type: ignore[union-attr]
    inputs.binding.verify()
    (Path(inputs.scope.font_dirs[0]) / "face").unlink()
    assert (fonts / "face").read_bytes() == b"font bytes"


@pytest.mark.parametrize("kind", ["mutated", "dangling", "relative", "entity"])
def test_inadmissible_inputs_cannot_be_credited_as_a_copy(
    inputs: FontconfigDiscovery, tmp_path: Path, kind: str
) -> None:
    main = Path(inputs.scope.parsed_files[0])
    if kind == "mutated":
        main.write_text("<fontconfig/>")
    elif kind == "dangling":
        # An unbound new name still refuses. Bound absent targets have the
        # separate private-copy/lifetime contract exercised below.
        (Path(inputs.scope.font_dirs[0]) / "missing").symlink_to(tmp_path / "absent")
    else:
        if kind == "relative":
            main.write_text('<fontconfig><dir prefix="relative">fonts</dir></fontconfig>')
        else:
            main.write_text('<!DOCTYPE fontconfig [<!ENTITY x "value">]><fontconfig/>')
        inputs = FontconfigDiscovery(
            inputs.scope,
            ResourceBinding.capture(
                [Path(p) for p in inputs.scope.parsed_files],
                directories=[
                    Path(p)
                    for p in (
                        *inputs.scope.config_dirs,
                        *inputs.scope.font_dirs,
                        *inputs.scope.template_dirs,
                    )
                ],
                environment={},
            ),
            inputs.linked,
        )
    root = tmp_path / "private"
    root.mkdir()
    with pytest.raises(NativeError):
        fontconfig.copy_fontconfig_inputs(inputs, root)


@pytest.mark.parametrize("form", ["absolute", "relative", "chain"])
@pytest.mark.parametrize("change", ["host-loss", "target-appearance", "retarget"])
def test_copy_confines_dangling_names_and_guards_their_absence(
    inputs: FontconfigDiscovery, tmp_path: Path, form: str, change: str
) -> None:
    # Catches dropping the name, keeping a host route, or losing the missing-target
    # binding. All three would silently change the future native candidate set.
    fonts = Path(inputs.scope.font_dirs[0])
    absent = fonts.parent / "never-present"
    alias = fonts / ".missing-face"
    if form == "chain":
        intermediate = fonts / "intermediate"
        intermediate.symlink_to(absent)
        alias.symlink_to("intermediate")
    else:
        alias.symlink_to(absent if form == "absolute" else "../never-present")
    found = replace(
        inputs,
        binding=ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[Path(p) for p in (*inputs.scope.config_dirs, *inputs.scope.font_dirs)],
            environment={},
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    fontconfig.copy_fontconfig_inputs(found, root)
    copied_fonts = root / str(fonts).lstrip("/")
    copied_alias = copied_fonts / alias.name
    copied_absent = root / str(absent).lstrip("/")
    assert sorted(p.name for p in copied_fonts.iterdir()) == sorted(p.name for p in fonts.iterdir())
    assert copied_alias.is_symlink() and not copied_alias.exists()
    assert copied_alias.readlink() == copied_absent
    copied = ResourceBinding.capture([], directories=[copied_fonts], environment={})
    if change == "host-loss":
        fonts.parent.rename(tmp_path / "removed-host")
        copied.verify()
        assert copied_alias.is_symlink() and not copied_alias.exists()
    elif change == "target-appearance":
        copied_absent.parent.mkdir(parents=True, exist_ok=True)
        copied_absent.write_bytes(b"new native candidate")
        with pytest.raises(NativeError):
            copied.verify()
    else:
        copied_alias.unlink()
        copied_alias.symlink_to(copied_fonts / "face")
        with pytest.raises(NativeError):
            copied.verify()


@pytest.mark.parametrize("kind", ["occupied", "overlap", "sysroot"])
def test_context_rejects_unsafe_reservation_before_consuming(
    inputs: FontconfigDiscovery, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    def discover(*args: object, **kwargs: object) -> FontconfigDiscovery:
        return inputs

    monkeypatch.setattr(fontconfig, "discover_fontconfig", discover)
    root = tmp_path / "private"
    environment: dict[str, str] = {}
    if kind == "occupied":
        root.mkdir()
        (root / "prior").write_bytes(b"prior")
    elif kind == "overlap":
        root = Path(inputs.scope.font_dirs[0]) / "private"
    else:
        environment["FONTCONFIG_SYSROOT"] = str(tmp_path)
    with pytest.raises(NativeError):
        with fontconfig.prepared_fontconfig_snapshot(
            tmp_path / "renderer",
            root,
            Path(inputs.scope.parsed_files[0]),
            environment=environment,
        ):
            pytest.fail("unsafe snapshot reached consumer")
    if kind == "occupied":
        assert (root / "prior").read_bytes() == b"prior"
    else:
        assert not root.exists()


@pytest.fixture
def native_boundary(inputs: FontconfigDiscovery, monkeypatch: pytest.MonkeyPatch) -> None:
    def discover(*args: object, **kwargs: object) -> FontconfigDiscovery:
        environment = kwargs.get("environment")
        assert isinstance(environment, dict)
        environment = cast(dict[str, str], environment)
        root = environment.get("FONTCONFIG_FILE")
        if root is None or not Path(root).is_absolute() or root == inputs.scope.parsed_files[0]:
            return inputs
        root = str(Path(root).parents[len(Path(inputs.scope.parsed_files[0]).parts) - 2])
        mapped = {
            name: tuple(str(Path(str(root)) / p.lstrip("/")) for p in value)
            for name, value in asdict(inputs.scope).items()
        }
        mapped["template_dirs"] = inputs.scope.template_dirs
        mapped["parsed_files"] = tuple(
            str(Path(str(root)) / p.lstrip("/")) for p in inputs.scope.parsed_files
        )
        mapped["cache_dirs"] = (str(Path(str(root)) / "bookscan-private-font-cache"),)
        mapped["effective_cache_dirs"] = (str(Path(str(root)) / "bookscan-private-font-cache"),)
        scope = ConfiguredScope(**mapped)
        binding = ResourceBinding.capture(
            [Path(p) for p in scope.parsed_files],
            directories=[
                Path(p)
                for p in (*scope.config_dirs, *scope.effective_font_dirs, *scope.template_dirs)
            ],
            environment=environment,
        )
        return FontconfigDiscovery(scope, binding, inputs.linked)

    @contextmanager
    def cache(*args: object, **kwargs: object) -> Iterator[FontconfigDiscovery]:
        found = discover(*args, **kwargs)
        found.binding.verify()
        yield found
        found.binding.verify()

    monkeypatch.setattr(fontconfig, "discover_fontconfig", discover)
    monkeypatch.setattr(fontconfig, "prepared_fontconfig_cache", cache)


@pytest.mark.parametrize("kind", ["normal", "host-loss", "mutation", "cancel", "replacement"])
def test_context_lifetime_is_owned_and_independent(
    inputs: FontconfigDiscovery, native_boundary: None, tmp_path: Path, kind: str
) -> None:
    root = tmp_path / "private"

    def use() -> None:
        with fontconfig.prepared_fontconfig_snapshot(
            tmp_path / "renderer", root, Path(inputs.scope.parsed_files[0]), environment={}
        ) as found:
            record = found.record()
            provenance = record.get("resource_snapshot")
            assert isinstance(provenance, dict)
            assert cast(dict[str, object], provenance).get("method") == "copied-path-cache-redirect"
            if kind == "host-loss":
                Path(inputs.scope.parsed_files[0]).unlink()
                (Path(inputs.scope.font_dirs[0]) / "face").unlink()
            elif kind == "mutation":
                Path(found.scope.parsed_files[0]).write_bytes(b"unbound mutation")
            elif kind == "cancel":
                raise InterruptedError("owner cancellation")
            elif kind == "replacement":
                root.rename(tmp_path / "displaced")
                root.mkdir()
                (root / "foreign").write_bytes(b"foreign")
            found.binding.verify()

    if kind in {"mutation", "replacement", "cancel"}:
        with pytest.raises(InterruptedError if kind == "cancel" else NativeError):
            use()
    else:
        use()
    if kind == "replacement":
        assert (root / "foreign").read_bytes() == b"foreign"
        assert (tmp_path / "displaced").is_dir()
    elif kind == "mutation":
        # A changed owned entry is never adopted or deleted; the root is retained.
        assert (
            sorted(p.read_bytes() for p in root.rglob("*") if p.is_file()).count(
                b"unbound mutation"
            )
            == 1
        )
    else:
        assert not root.exists()


@pytest.mark.parametrize("form", ["relative", "empty-segment", "trailing-segment", "empty"])
def test_snapshot_confines_captured_search_roots_before_native_use(
    inputs: FontconfigDiscovery, native_boundary: None, tmp_path: Path, form: str
) -> None:
    # Rewriting includes alone must not leave relative/empty search roots
    # unresolved, reject them accidentally, or route later native use to host.
    config = Path(inputs.scope.config_files[0]).parent
    value = {
        "relative": os.path.relpath(config),
        "empty-segment": ":" + str(config),
        "trailing-segment": str(config) + ":",
        "empty": "",
    }[form]
    root = tmp_path / "private"
    with fontconfig.prepared_fontconfig_snapshot(
        tmp_path / "renderer",
        root,
        Path(inputs.scope.config_files[0]),
        environment={"FONTCONFIG_PATH": value},
    ) as found:
        roots = found.binding.environment()["FONTCONFIG_PATH"].split(":")
        expected: list[str] = []
        if form == "empty-segment":
            expected.append(str(root))
        if form != "empty":
            expected.append(str(root / str(config).lstrip("/")))
        expected.append(str(root / "opt/homebrew/etc/fonts"))
        assert roots == expected
        assert all(Path(path).is_absolute() and Path(path).is_relative_to(root) for path in roots)
        found.binding.verify()
    assert not root.exists()


def test_search_include_refuses_symlink_parent_normalization_that_changes_target(
    inputs: FontconfigDiscovery, tmp_path: Path
) -> None:
    # Lexically deleting alias/.. can silently select another already-loaded
    # file even though the OS resolves that path through the alias's target.
    main = Path(inputs.scope.config_files[0])
    real = tmp_path / "real"
    (real / "sub").mkdir(parents=True)
    (main.parent / "alias").symlink_to(real / "sub", target_is_directory=True)
    actual = real / "rules.conf"
    actual.write_text("<fontconfig><!-- actual OS target --></fontconfig>")
    main.write_text("<fontconfig><include>rules.conf</include></fontconfig>")
    scope = replace(
        inputs.scope,
        config_files=(*inputs.scope.config_files, str(actual)),
        parsed_files=(*inputs.scope.parsed_files, str(actual)),
    )
    found = FontconfigDiscovery(
        scope,
        ResourceBinding.capture(
            [Path(p) for p in scope.parsed_files],
            directories=[Path(p) for p in (*scope.config_dirs, *scope.font_dirs)],
            environment={"FONTCONFIG_PATH": str(main.parent / "alias") + "/.."},
        ),
        inputs.linked,
    )
    root = tmp_path / "private"
    root.mkdir()
    with pytest.raises(NativeError):
        fontconfig.copy_fontconfig_inputs(found, root)


def test_copy_preserves_fontconfig_colon_names_and_every_noncache_byte(
    inputs: FontconfigDiscovery, tmp_path: Path
) -> None:
    main = Path(inputs.scope.parsed_files[0])
    raw = (
        b'<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
        b"<fontconfig><!-- cache <cachedir/> in a comment -->"
        b'<match><test name="family"><string>family:colon</string></test></match>'
        b'<match><test name="family"><const xsi:nil="true"/></test></match>'
        b'<cachedir prefix="xdg">fontconfig</cachedir><cachedir/>'
        b"</fontconfig>\n"
    )
    main.write_bytes(raw)
    inputs = FontconfigDiscovery(
        inputs.scope,
        ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[
                Path(p)
                for p in (
                    *inputs.scope.config_dirs,
                    *inputs.scope.font_dirs,
                    *inputs.scope.template_dirs,
                )
            ],
            environment={},
        ),
        inputs.linked,
    )
    root = tmp_path / "private"
    root.mkdir()
    fontconfig.copy_fontconfig_inputs(inputs, root)
    expected = raw.replace(
        b'<cachedir prefix="xdg">fontconfig</cachedir>',
        b"<cachedir>" + str(root / "bookscan-private-font-cache").encode() + b"</cachedir>",
    ).replace(
        b"<cachedir/></fontconfig>",
        b"<cachedir>"
        + str(root / "bookscan-private-font-cache").encode()
        + b"</cachedir></fontconfig>",
    )
    assert (root / str(main).lstrip("/")).read_bytes() == expected


def test_scope_rejects_an_unbound_font_tree(inputs: FontconfigDiscovery, tmp_path: Path) -> None:
    inputs = FontconfigDiscovery(
        inputs.scope,
        ResourceBinding.capture([Path(p) for p in inputs.scope.parsed_files], environment={}),
        inputs.linked,
    )
    root = tmp_path / "private"
    root.mkdir()
    with pytest.raises(NativeError):
        fontconfig.copy_fontconfig_inputs(inputs, root)


@pytest.mark.parametrize("field", ["parsed_files", "font_dirs", "effective_cache_dirs"])
def test_copied_foreign_scope_cannot_reach_consumer(
    inputs: FontconfigDiscovery,
    native_boundary: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    original_discover = fontconfig.discover_fontconfig

    def discover(*args: object, **kwargs: object) -> FontconfigDiscovery:
        from dataclasses import replace

        found = original_discover(
            cast(Path, args[0]), environment=cast(dict[str, str] | None, kwargs.get("environment"))
        )
        if found is not inputs:
            return replace(found, scope=replace(found.scope, **{field: ("/foreign",)}))
        return found

    monkeypatch.setattr(fontconfig, "discover_fontconfig", discover)
    root = tmp_path / "private"
    with pytest.raises(NativeError):
        with fontconfig.prepared_fontconfig_snapshot(
            tmp_path / "renderer", root, Path(inputs.scope.parsed_files[0]), environment={}
        ):
            pytest.fail("foreign scope reached consumer")
    assert not root.exists()


@pytest.mark.parametrize("kind", ["source-change", "cancel"])
def test_interrupted_copy_cannot_yield_and_cleans_owned_partial(
    inputs: FontconfigDiscovery, native_boundary: None, tmp_path: Path, kind: str
) -> None:
    root = tmp_path / "private"
    copied_font = root / (inputs.scope.font_dirs[0] + "/face").lstrip("/")
    changed = False

    def check() -> None:
        nonlocal changed
        if copied_font.exists() and not changed:
            changed = True
            if kind == "cancel":
                raise InterruptedError("copy cancellation")
            Path(inputs.scope.parsed_files[0]).write_bytes(b"changed source configuration")

    with pytest.raises(InterruptedError if kind == "cancel" else NativeError):
        with fontconfig.prepared_fontconfig_snapshot(
            tmp_path / "renderer",
            root,
            Path(inputs.scope.parsed_files[0]),
            environment={},
            check_cancel=check,
        ):
            pytest.fail("interrupted copy reached consumer")
    assert changed
    assert not root.exists()


@pytest.mark.parametrize("explicit", [False, True])
def test_snapshot_uses_resolved_configuration_and_preserves_explicit_override(
    inputs: FontconfigDiscovery,
    native_boundary: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    explicit: bool,
) -> None:
    selected = Path(inputs.scope.parsed_files[0])

    def selection(found: FontconfigDiscovery, check_cancel: object) -> Path:
        if explicit:
            pytest.fail("explicit configuration invoked default selection")
        return selected

    monkeypatch.setattr(fontconfig, "selected_configuration", selection, raising=False)
    root = tmp_path / "private"
    arguments: list[Path] = [selected] if explicit else []
    with fontconfig.prepared_fontconfig_snapshot(
        tmp_path / "renderer", root, *arguments, environment={"FONTCONFIG_FILE": "rules.conf"}
    ) as found:
        provenance = cast(dict[str, object], found.record()["resource_snapshot"])
        assert provenance["configuration_file"] == str(selected)
        assert provenance["selection"] == ("explicit" if explicit else "captured-fontconfig")
        selected.unlink()
        found.binding.verify()
    assert not root.exists()


@pytest.mark.parametrize("element", ["dir", "remap-dir", "include"])
@pytest.mark.parametrize("value", [" fonts ", "fonts\t", "fonts\n", "fonts\u00a0"])
def test_copy_preserves_exact_path_character_data(
    inputs: FontconfigDiscovery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    element: str,
    value: str,
) -> None:
    # Native character data is filename data. Keep an independently bound
    # trimmed sibling so stripping can select the wrong resource without error.
    monkeypatch.chdir(tmp_path)
    main = Path(inputs.scope.config_files[0])
    target, decoy = tmp_path / value, tmp_path / value.strip()
    target.mkdir()
    decoy.mkdir()
    (target / "face").write_bytes(b"exact filename")
    (decoy / "face").write_bytes(b"wrong trimmed sibling")
    extra = ' as-path="/logical/fonts"' if element == "remap-dir" else ""
    main.write_text(
        "<fontconfig><" + element + extra + ">" + value + "</" + element + "></fontconfig>"
    )
    scope = replace(
        inputs.scope,
        config_files=(*inputs.scope.config_files, str(target), str(decoy)),
        config_dirs=(*inputs.scope.config_dirs, str(target), str(decoy)),
        font_dirs=(*inputs.scope.font_dirs, str(target), str(decoy)),
        effective_font_dirs=(*inputs.scope.effective_font_dirs, str(target), str(decoy)),
    )
    found = FontconfigDiscovery(
        scope,
        ResourceBinding.capture(
            [Path(p) for p in scope.parsed_files],
            directories=[Path(p) for p in (*scope.config_dirs, *scope.font_dirs)],
            environment={"FONTCONFIG_PATH": str(tmp_path)},
        ),
        inputs.linked,
    )
    root = tmp_path / "private"
    root.mkdir()
    fontconfig.copy_fontconfig_inputs(found, root)
    copied = ET.parse(root / str(main).lstrip("/")).find(element)
    assert copied is not None
    copied_path = copied.text
    assert copied_path is not None
    assert copied_path == str(root / str(target).lstrip("/"))
    assert (Path(copied_path) / "face").read_bytes() == b"exact filename"


@pytest.mark.parametrize("element", ["dir", "remap-dir", "include", "cachedir"])
def test_copy_refuses_flattening_nested_path_character_data(
    inputs: FontconfigDiscovery, tmp_path: Path, element: str
) -> None:
    main = Path(inputs.scope.config_files[0])
    value = (
        inputs.scope.font_dirs[0]
        if element in {"dir", "remap-dir"}
        else inputs.scope.config_files[1]
    )
    extra = ' as-path="/logical/fonts"' if element == "remap-dir" else ""
    main.write_text(
        "<fontconfig><"
        + element
        + extra
        + "><string>"
        + value
        + "</string></"
        + element
        + "></fontconfig>"
    )
    found = replace(
        inputs,
        binding=ResourceBinding.capture(
            [Path(p) for p in inputs.scope.parsed_files],
            directories=[Path(p) for p in (*inputs.scope.config_dirs, *inputs.scope.font_dirs)],
            environment={},
        ),
    )
    root = tmp_path / "private"
    root.mkdir()
    with pytest.raises(NativeError, match="Nested"):
        fontconfig.copy_fontconfig_inputs(found, root)
