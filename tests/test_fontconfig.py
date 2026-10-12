"""Configured-scope discovery must reject omitted/changeable native inputs."""

import ctypes
import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from bookscan import fontconfig, fontconfig_probe
from bookscan.skew import NativeError


@pytest.mark.parametrize("form", ["absolute", "relative", "parent", "alias", "alias-parent"])
def test_native_configuration_filename_is_absolute_without_changing_its_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, form: str
) -> None:
    # Native ConfigFiles/FileInfo getters can retain a relative PATH root.
    # Absolutizing must use the child's cwd without selecting an alias/.. sibling.
    real = tmp_path / "real"
    (real / "sub").mkdir(parents=True)
    (real / "rules.conf").write_text("<fontconfig/>")
    alias = tmp_path / "alias"
    alias.symlink_to(real / "sub", target_is_directory=True)
    monkeypatch.chdir(tmp_path)
    value = {
        "absolute": str(real / "rules.conf"),
        "relative": "real/rules.conf",
        "parent": "real/sub/../rules.conf",
        "alias": "alias/rules.conf",
        "alias-parent": "alias/../rules.conf",
    }[form]
    if form == "alias-parent":
        with pytest.raises(ValueError):
            fontconfig_probe._configuration_path(value)  # pyright: ignore[reportPrivateUsage]
    else:
        expected = str(alias / "rules.conf") if form == "alias" else str(real / "rules.conf")
        assert fontconfig_probe._configuration_path(value) == expected  # pyright: ignore[reportPrivateUsage]
        assert os.path.isabs(expected)


def test_invalid_configuration_cannot_enter_cache_building_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "built-cache"

    class Function:
        argtypes: object = None
        restype: object = None

        def __init__(self, action: Callable[[], object]) -> None:
            self.action = action

        def __call__(self, *args: object) -> object:
            return self.action()

    def fallback() -> None:
        marker.write_bytes(b"font database built before fallback failure")

    library = SimpleNamespace(
        FcGetVersion=Function(lambda: 21803),
        FcInitLoadConfig=Function(fallback),
        FcConfigCreate=Function(lambda: 1),
        FcConfigParseAndLoad=Function(lambda: 0),
        FcConfigParseOnly=Function(lambda: 1),
        FcConfigGetSysRoot=Function(lambda: None),
        FcConfigDestroy=Function(lambda: None),
        FcStrListNext=Function(lambda: None),
        FcStrListDone=Function(lambda: None),
        FcStrFree=Function(lambda: None),
        FcConfigFileInfoIterInit=Function(lambda: None),
        FcConfigFileInfoIterNext=Function(lambda: 1),
        FcConfigFileInfoIterGet=Function(lambda: 0),
    )

    def load(path: str) -> SimpleNamespace:
        return library

    def template_directory(path: str) -> str:
        return "/known-templates"

    monkeypatch.setattr(fontconfig_probe.ctypes, "CDLL", load)
    monkeypatch.setattr(fontconfig_probe, "_template_directory", template_directory)
    with pytest.raises(ValueError):
        fontconfig_probe.configured_scope("/native-boundary")
    assert not marker.exists(), "invalid config entered the cache-building fallback"


@pytest.fixture
def configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    library = tmp_path / "libfontconfig.1.dylib"
    library.write_bytes(b"test-owned native boundary")
    config = tmp_path / "config" / "fonts.conf"
    config.parent.mkdir()
    config.write_text("configured")
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    (fonts / "font").write_bytes(b"font")
    cache = tmp_path / "absent-cache"
    scope: dict[str, object] = {
        "schema": "BookScanBuilderFontconfigScope",
        "version": 3,
        "fontconfig_version": 21803,
        "config_files": [str(config)],
        "config_dirs": [str(config.parent)],
        "font_dirs": [str(fonts)],
        "cache_dirs": [str(cache)],
        "template_dirs": [str(tmp_path / "absent-templates")],
        "parsed_files": [str(config)],
        "effective_font_dirs": [str(fonts)],
        "effective_cache_dirs": [str(cache)],
    }

    def linked(*args: object, **kwargs: object) -> dict[str, object]:
        return {"files": {str(library): {}}, "system_references": []}

    def probe(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0, json.dumps(scope), "")

    monkeypatch.setattr(fontconfig, "linked_identity", linked)
    monkeypatch.setattr(fontconfig, "execute", probe)
    return scope


@pytest.mark.parametrize("kind", ["config_dirs", "font_dirs", "cache_dirs"])
def test_discovered_candidate_growth_invalidates_guard(
    configured: dict[str, object], tmp_path: Path, kind: str
) -> None:
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})
    root = Path(cast(list[str], configured[kind])[0])
    root.mkdir(exist_ok=True)
    (root / "new-candidate").write_bytes(b"new input")
    with pytest.raises(NativeError):
        found.binding.verify()


def test_config_and_native_bytes_are_bound(configured: dict[str, object], tmp_path: Path) -> None:
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})
    (tmp_path / "libfontconfig.1.dylib").write_bytes(b"changed")
    with pytest.raises(NativeError):
        found.binding.verify()


def test_config_include_directory_is_bound_without_treating_it_as_a_file(
    configured: dict[str, object], tmp_path: Path
) -> None:
    # Actual FcConfigGetConfigFiles includes directories from <include> too.
    included = tmp_path / "includes"
    included.mkdir()
    cast(list[str], configured["config_files"]).append(str(included))
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})
    found.binding.verify()
    (included / "later.conf").write_text("new configuration")
    with pytest.raises(NativeError):
        found.binding.verify()


def test_rediscovery_disagreement_is_not_a_usable_guard(
    configured: dict[str, object], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    count = 0

    def probe(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal count
        count += 1
        if count == 2:
            configured["font_dirs"] = []
        return subprocess.CompletedProcess([], 0, json.dumps(configured), "")

    monkeypatch.setattr(fontconfig, "execute", probe)
    with pytest.raises(NativeError, match="changed"):
        fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", True),
        ("fontconfig_version", 21804),
        ("font_dirs", ["relative/fonts"]),
        ("cache_dirs", "not an array"),
        ("cache_dirs", []),
        ("config_files", []),
        ("config_dirs", ["/bad\x00path"]),
        ("unknown_required", 1),
        ("version", 1),
        ("template_dirs", []),
        ("template_dirs", ["relative/templates"]),
        ("parsed_files", []),
        ("parsed_files", ["relative/template.conf"]),
        ("version", 2),
        ("effective_font_dirs", ["relative/fonts"]),
        ("effective_cache_dirs", []),
        ("effective_cache_dirs", ["/bad\x00path"]),
    ],
)
def test_incomplete_or_unknown_scope_is_rejected(
    configured: dict[str, object], tmp_path: Path, field: str, value: object
) -> None:
    configured[field] = value
    with pytest.raises(NativeError):
        fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})


@pytest.mark.parametrize("returncode", [0, 1])
def test_native_diagnostics_cannot_silently_select_fallback_config(
    configured: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
) -> None:
    def probe(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], returncode, json.dumps(configured), "parse warning")

    monkeypatch.setattr(fontconfig, "execute", probe)
    with pytest.raises(NativeError):
        fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})


def test_environment_is_copied_and_not_disclosed(
    configured: dict[str, object], tmp_path: Path
) -> None:
    environment = {"FONTCONFIG_FILE": "private-selection", "SECRET": "private-value"}
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment=environment)
    environment["SECRET"] = "changed"
    assert found.binding.environment()["SECRET"] == "private-value"
    record = found.record()
    assert "private-value" not in json.dumps(record)
    assert record["runtime_resources_verified"] is False


def test_owner_cancellation_is_not_converted_to_dependency_failure(
    configured: dict[str, object], tmp_path: Path
) -> None:
    def cancel() -> None:
        raise InterruptedError("owner-selected")

    with pytest.raises(InterruptedError, match="owner-selected"):
        fontconfig.discover_fontconfig(tmp_path / "renderer", check_cancel=cancel)


@pytest.mark.parametrize("field", ["config_files", "config_dirs", "font_dirs", "cache_dirs"])
def test_later_optional_include_scope_cannot_use_the_original_guard(
    configured: dict[str, object], tmp_path: Path, field: str
) -> None:
    # Missing includes are absent from FcConfigGetConfigFiles. Their appearance
    # can add a path outside every initially reported tree, even with identical RGB.
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})
    later = tmp_path / "outside-original-scope"
    cast(list[str], configured[field]).append(str(later))
    with pytest.raises(NativeError, match="scope changed"):
        found.binding.verify()


@pytest.mark.parametrize("failure", ["diagnostic", "version", "protocol"])
def test_lifetime_scope_verification_rejects_failed_native_rediscovery(
    configured: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})

    def probe(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        if failure == "version":
            configured["fontconfig_version"] = 21804
        if failure == "protocol":
            configured["config_files"] = None
        diagnostic = "parse warning" if failure == "diagnostic" else ""
        return subprocess.CompletedProcess([], 0, json.dumps(configured), diagnostic)

    monkeypatch.setattr(fontconfig, "execute", probe)
    with pytest.raises(NativeError):
        found.binding.verify()


def test_scan_only_template_bytes_are_bound(configured: dict[str, object], tmp_path: Path) -> None:
    template = tmp_path / "outside-loaded-trees.conf"
    template.write_text("<fontconfig/>\n")
    cast(list[str], configured["parsed_files"]).append(str(template))
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})
    template.write_text("<fontconfig><!-- changed read subject --></fontconfig>\n")
    with pytest.raises(NativeError):
        found.binding.verify()


def test_absent_template_root_appearance_is_bound(
    configured: dict[str, object], tmp_path: Path
) -> None:
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})
    templates = tmp_path / "absent-templates"
    templates.mkdir()
    (templates / "50-later.conf").write_text("<fontconfig/>\n")
    with pytest.raises(NativeError):
        found.binding.verify()


@pytest.mark.parametrize("field", ["template_dirs", "parsed_files"])
def test_later_template_scope_requires_fresh_binding(
    configured: dict[str, object], tmp_path: Path, field: str
) -> None:
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})
    if field == "template_dirs":
        configured[field] = [str(tmp_path / "later-templates")]
    else:
        cast(list[str], configured[field]).append(str(tmp_path / "later.conf"))
    with pytest.raises(NativeError, match="scope changed"):
        found.binding.verify()


def test_unknown_native_build_cannot_guess_template_directory(tmp_path: Path) -> None:
    library = tmp_path / "libfontconfig.1.dylib"
    library.write_bytes(b"unverified native build with an arbitrary compiled template path")
    with pytest.raises(ValueError, match="build"):
        fontconfig_probe.configured_scope(str(library))


@pytest.mark.parametrize("field", ["font_dirs", "cache_dirs"])
@pytest.mark.parametrize("initially_present", [False, True])
def test_effective_resource_growth_cannot_hide_behind_unchanged_logical_roots(
    configured: dict[str, object], tmp_path: Path, field: str, initially_present: bool
) -> None:
    effective = tmp_path / "effective" / field
    if initially_present:
        effective.mkdir(parents=True)
    configured["effective_" + field] = [str(effective)]
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})
    effective.mkdir(parents=True, exist_ok=True)
    (effective / "later-native-input").write_bytes(b"changed effective resource")
    with pytest.raises(NativeError):
        found.binding.verify()


def test_unrelated_logical_font_tree_is_not_a_native_read_subject(
    configured: dict[str, object], tmp_path: Path
) -> None:
    effective = tmp_path / "effective-fonts"
    effective.mkdir()
    configured["effective_font_dirs"] = [str(effective)]
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})
    (tmp_path / "fonts" / "unrelated").write_bytes(b"not in the native sysroot")
    found.binding.verify()


@pytest.mark.parametrize(
    "fault",
    ["valid", "foreign", "relative", "nul", "missing", "schema", "version", "diagnostic", "exit"],
)
def test_selected_configuration_must_be_a_bound_loaded_native_result(
    configured: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})
    selected = cast(list[str], configured["config_files"])[0]
    reply: dict[str, object] = {
        "schema": "BookScanBuilderFontconfigSelection",
        "version": 1,
        "fontconfig_version": 21803,
        "configuration_file": selected,
    }
    if fault in {"foreign", "relative", "nul", "missing"}:
        reply["configuration_file"] = {
            "foreign": "/outside-bound-inputs.conf",
            "relative": "fonts.conf",
            "nul": "/invalid\x00.conf",
            "missing": None,
        }[fault]
    elif fault == "schema":
        reply["unrecognized"] = True
    elif fault == "version":
        reply["version"] = True

    def execute(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[-1] != "--resolve-configuration":
            return subprocess.CompletedProcess(command, 0, json.dumps(configured), "")
        return subprocess.CompletedProcess(
            command,
            5 if fault == "exit" else 0,
            json.dumps(reply),
            "native warning" if fault == "diagnostic" else "",
        )

    monkeypatch.setattr(fontconfig, "execute", execute)
    if fault == "valid":
        assert fontconfig.selected_configuration(found, lambda: None) == Path(selected)
    else:
        with pytest.raises(NativeError):
            fontconfig.selected_configuration(found, lambda: None)


def test_selection_cancellation_is_preserved(configured: dict[str, object], tmp_path: Path) -> None:
    found = fontconfig.discover_fontconfig(tmp_path / "renderer", environment={})

    def cancel() -> None:
        raise InterruptedError("selection cancelled")

    with pytest.raises(InterruptedError, match="selection cancelled"):
        fontconfig.selected_configuration(found, cancel)


@pytest.mark.parametrize("missing", [False, True])
def test_native_selection_uses_empty_config_and_releases_owned_native_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: bool
) -> None:
    marker = tmp_path / "unwanted-font-build"
    freed: list[object] = []
    destroyed: list[object] = []
    name = ctypes.create_string_buffer(b"/configured/fonts.conf")
    pointer = ctypes.addressof(name)

    class Function:
        argtypes: object = None
        restype: object = None

        def __init__(self, action: Callable[..., object]) -> None:
            self.action = action

        def __call__(self, *args: object) -> object:
            return self.action(*args)

    def resolve(config: object, value: object) -> int | None:
        if config != 123 or value is not None:
            marker.write_bytes(b"wrong native selection context")
        return None if missing else pointer

    def forbidden(*args: object) -> None:
        marker.write_bytes(b"configuration selection entered loading/font construction")

    def destroy(config: object) -> None:
        destroyed.append(config)

    def free(value: object) -> None:
        freed.append(value)

    library = SimpleNamespace(
        FcGetVersion=Function(lambda: 21803),
        FcConfigCreate=Function(lambda: 123),
        FcConfigGetFilename=Function(resolve),
        FcConfigFilename=Function(forbidden),
        FcConfigSetCurrent=Function(forbidden),
        FcConfigParseAndLoad=Function(forbidden),
        FcConfigParseOnly=Function(forbidden),
        FcConfigGetSysRoot=Function(forbidden),
        FcConfigDestroy=Function(destroy),
        FcStrListNext=Function(forbidden),
        FcStrListDone=Function(forbidden),
        FcStrFree=Function(free),
        FcConfigFileInfoIterInit=Function(forbidden),
        FcConfigFileInfoIterNext=Function(forbidden),
        FcConfigFileInfoIterGet=Function(forbidden),
    )

    def load(path: str) -> SimpleNamespace:
        return library

    def templates(path: str) -> str:
        return "/templates"

    monkeypatch.setattr(fontconfig_probe.ctypes, "CDLL", load)
    monkeypatch.setattr(fontconfig_probe, "_template_directory", templates)
    if missing:
        with pytest.raises(ValueError):
            fontconfig_probe.configured_scope("/library", resolve_configuration=True)
    else:
        result = fontconfig_probe.configured_scope("/library", resolve_configuration=True)
        assert result["configuration_file"] == "/configured/fonts.conf"
    assert destroyed == [123]
    assert freed == ([] if missing else [pointer])
    assert not marker.exists()
