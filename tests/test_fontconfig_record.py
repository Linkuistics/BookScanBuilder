"""Saved configuration guards must retain scope and never invent runtime use."""

import copy
import json
import shutil
import subprocess
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from typing import cast

import pytest
from test_resource_record import entry, file
from test_resource_record import literal as named_literal

from bookscan import fontconfig, records, resource_record
from bookscan.resources import ResourceBinding


def literal() -> dict[str, object]:
    value = named_literal()
    files = [
        {**file(), "path": "/historical/fonts.conf"},
        {**file(), "path": "/historical/rules/10.conf", "resolved": "/historical/rules/10.conf"},
    ]
    root = entry("/historical/rules", "directory")
    root["members"] = ["10.conf"]
    value.update(
        files=files,
        directories=[
            {"path": "/historical/cache", "entries": None},
            {"path": "/historical/fonts", "entries": None},
            {"path": "/historical/optional", "entries": None},
            {
                "path": "/historical/rules",
                "entries": [root, entry("/historical/rules/10.conf", "file")],
            },
            {"path": "/historical/templates", "entries": None},
        ],
        fontconfig_scope_guard={
            "version": 3,
            "verification": "fresh-configuration-only-rediscovery",
            "limitation": fontconfig.LIMITATION,
            "scope": {
                "config_files": ["/historical/fonts.conf", "/historical/rules"],
                "config_dirs": ["/historical/optional", "/historical/rules"],
                "font_dirs": ["/logical/fonts"],
                "cache_dirs": ["/logical/cache"],
                "template_dirs": ["/historical/templates"],
                "parsed_files": ["/historical/fonts.conf", "/historical/rules/10.conf"],
                "effective_font_dirs": ["/historical/fonts"],
                "effective_cache_dirs": ["/historical/cache"],
            },
        },
    )
    return value


def test_reader_preserves_configured_logical_effective_scope_without_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import fontconfig_record

    value = literal()

    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Historical file access/native launches are forbidden")

    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(Path, "stat", denied)
    monkeypatch.setattr(Path, "resolve", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    result = fontconfig_record.restore_guard(value)
    assert result is not None
    assert result.config_files == ("/historical/fonts.conf", "/historical/rules")
    assert result.font_dirs == ("/logical/fonts",)
    assert result.effective_font_dirs == ("/historical/fonts",)
    assert result.cache_dirs == ("/logical/cache",)
    assert result.effective_cache_dirs == ("/historical/cache",)
    assert not hasattr(result, "verify") and not hasattr(result, "runtime_resources_verified")
    guard = cast(dict[str, object], value["fontconfig_scope_guard"])
    cast(dict[str, object], guard["scope"])["config_files"] = []
    assert result.config_files == ("/historical/fonts.conf", "/historical/rules")
    with pytest.raises(FrozenInstanceError):
        result.config_files = ()  # type: ignore[misc]


def test_unguarded_binding_stays_unguarded() -> None:
    from bookscan import fontconfig_record

    value = named_literal()
    assert fontconfig_record.restore_guard(value) is None
    value["runtime_resources_verified"] = True
    with pytest.raises(resource_record.ResourceRecordError):
        fontconfig_record.restore_guard(value)


@pytest.mark.parametrize(
    "fault",
    [
        "extra-guard",
        "missing-guard",
        "version-bool",
        "old-version",
        "version-float",
        "runtime-verification",
        "lost-limitation",
        "guard-list",
        "scope-list",
        "extra-scope",
        "missing-scope",
        "scope-tuple",
        "relative-path",
        "empty-path",
        "nul-path",
        "surrogate-path",
        "nonstring-path",
        "duplicate-path",
        "unsorted-path",
        "no-config",
        "no-cache",
        "no-effective-cache",
        "no-template",
        "two-templates",
        "no-parsed",
        "no-effective-fonts",
        "missing-file",
        "absent-config",
        "absent-parsed",
        "absent-config-directory",
        "unbound-config-directory",
        "unbound-effective-fonts",
        "unbound-effective-cache",
        "unbound-templates",
        "config-is-unbound-file",
        "parsed-is-directory",
        "invalid-named",
        "non-json",
        "nan",
        "nonstring-key",
    ],
)
def test_contradictory_or_unbound_configuration_scope_is_refused(fault: str) -> None:
    from bookscan import fontconfig_record

    data = literal()
    guard = cast(dict[str, object], data["fontconfig_scope_guard"])
    scope = cast(dict[str, object], guard["scope"])
    files = cast(list[dict[str, object]], data["files"])
    trees = cast(list[dict[str, object]], data["directories"])
    changes: dict[str, tuple[str, object]] = {
        "version-bool": ("version", True),
        "old-version": ("version", 2),
        "version-float": ("version", 3.0),
        "runtime-verification": ("verification", "renderer-opens-verified"),
        "lost-limitation": ("limitation", "All native font use verified"),
        "scope-list": ("scope", []),
    }
    scopes: dict[str, tuple[str, object]] = {
        "scope-tuple": ("config_files", tuple(scope["config_files"])),  # type: ignore[arg-type]
        "relative-path": ("font_dirs", ["fonts"]),
        "empty-path": ("font_dirs", [""]),
        "nul-path": ("font_dirs", ["/fonts\0"]),
        "surrogate-path": ("font_dirs", ["/fonts\ud800"]),
        "nonstring-path": ("font_dirs", [1]),
        "duplicate-path": ("font_dirs", ["/fonts", "/fonts"]),
        "unsorted-path": ("font_dirs", ["/z", "/a"]),
        "no-config": ("config_files", []),
        "no-cache": ("cache_dirs", []),
        "no-effective-cache": ("effective_cache_dirs", []),
        "no-template": ("template_dirs", []),
        "two-templates": ("template_dirs", ["/a", "/b"]),
        "no-parsed": ("parsed_files", []),
        "no-effective-fonts": ("effective_font_dirs", []),
        "unbound-config-directory": ("config_dirs", ["/unknown"]),
        "unbound-effective-fonts": ("effective_font_dirs", ["/unknown"]),
        "unbound-effective-cache": ("effective_cache_dirs", ["/unknown"]),
        "unbound-templates": ("template_dirs", ["/unknown"]),
        "config-is-unbound-file": ("config_files", ["/unknown"]),
        "parsed-is-directory": ("parsed_files", ["/historical/rules"]),
    }
    if fault in changes:
        key, value = changes[fault]
        guard[key] = value
    elif fault in scopes:
        key, value = scopes[fault]
        scope[key] = value
    elif fault == "extra-guard":
        guard["verified"] = True
    elif fault == "missing-guard":
        del guard["verification"]
    elif fault == "guard-list":
        data["fontconfig_scope_guard"] = []
    elif fault == "extra-scope":
        scope["runtime_fonts"] = []
    elif fault == "missing-scope":
        del scope["parsed_files"]
    elif fault == "missing-file":
        files.pop()
    elif fault in ("absent-config", "absent-parsed"):
        files[0 if fault == "absent-config" else 1].update(
            resolved=None, device=None, inode=None, size=None, sha256=None
        )
    elif fault == "absent-config-directory":
        trees[3]["entries"] = None
    elif fault == "invalid-named":
        data["working_directory_identity"] = [True, 2]
    elif fault == "non-json":
        guard["limitation"] = Path("/not-json")
    elif fault == "nan":
        guard["version"] = float("nan")
    elif fault == "nonstring-key":
        cast(dict[object, object], scope)[1] = []
    else:
        raise AssertionError(fault)
    with pytest.raises(resource_record.ResourceRecordError) as raised:
        fontconfig_record.restore_guard(data)
    assert (raised.value.code, raised.value.exit_code) == ("INVALID_PROJECT", 3)
    assert "bookscan baseline" in raised.value.remediation


def test_logical_parent_alias_spellings_stay_historical() -> None:
    from bookscan import fontconfig_record

    value = literal()
    files = cast(list[dict[str, object]], value["files"])
    files[0]["path"] = "/historical/old/../fonts.conf"
    scope = cast(
        dict[str, object], cast(dict[str, object], value["fontconfig_scope_guard"])["scope"]
    )
    scope["config_files"] = ["/historical/old/../fonts.conf", "/historical/rules"]
    scope["parsed_files"] = ["/historical/old/../fonts.conf", "/historical/rules/10.conf"]
    result = fontconfig_record.restore_guard(value)
    assert result is not None and result.config_files[0] == "/historical/old/../fonts.conf"


def test_real_guard_can_be_read_after_every_captured_input_disappears(tmp_path: Path) -> None:
    from bookscan import fontconfig_record

    root = tmp_path / "historical"
    root.mkdir()
    config = root / "fonts.conf"
    config.write_text("<fontconfig/>")
    fonts = root / "fonts"
    fonts.mkdir()
    (fonts / "face").write_bytes(b"captured font")
    scope = fontconfig.ConfiguredScope(
        (str(config),),
        (),
        (str(fonts),),
        (str(root / "cache"),),
        (str(root / "templates"),),
        (str(config),),
        (str(fonts),),
        (str(root / "cache"),),
    )
    binding = ResourceBinding.capture(
        [config],
        directories=[fonts],
        optional_directories=[root / "cache", root / "templates"],
        environment={"PRIVATE": "never serialized"},
    )
    value = records.decode(
        json.dumps(
            fontconfig.FontconfigBinding.guard(
                binding, root / "libfontconfig.1.dylib", scope
            ).record()
        ).encode()
    )
    shutil.rmtree(root)
    result = fontconfig_record.restore_guard(value)
    assert result is not None and asdict(result) == asdict(scope)
    assert "PRIVATE" not in json.dumps(value)


@pytest.mark.parametrize("bad_predecessor", [False, True])
def test_restart_verifies_guard_below_hash_valid_current_checkpoint(
    tmp_path: Path, bad_predecessor: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import fontconfig_record, ownership, project_header

    path = tmp_path / "Saved project"
    path.mkdir()
    with ownership.Writer.acquire(path, ownership.provision(path)) as owner:
        stores = project_header.Stores.provision(owner)
        good: dict[str, object] = {"binding": literal()}
        bad = copy.deepcopy(good)
        guard = cast(
            dict[str, object], cast(dict[str, object], bad["binding"])["fontconfig_scope_guard"]
        )
        guard["verification"] = "renderer-opens-verified"
        previous = stores.checkpoints.commit(
            bad if bad_predecessor else good, expected=None, verify_state=lambda _: None
        ).checkpoint
        stores.checkpoints.commit(good, expected=previous, verify_state=lambda _: None)
    before = {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()}

    def verify(images: object, state: dict[str, object]) -> None:
        fontconfig_record.restore_guard(state["binding"])

    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Restart must not launch a configuration probe")

    monkeypatch.setattr(subprocess, "Popen", denied)
    if bad_predecessor:
        with pytest.raises(resource_record.ResourceRecordError):
            with project_header.resume(
                path, verify_state=lambda stores, state: verify(stores.images, state)
            ):
                pytest.fail("Unverified guard predecessor accepted")
    else:
        with project_header.resume(
            path, verify_state=lambda stores, state: verify(stores.images, state)
        ) as (_, current):
            assert current.revision == 2 and current.state == good
    assert {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()} == before


@pytest.mark.parametrize(
    "field,value", [("sha256", "1" * 64), ("inode", 999), ("resolved", "/other/font")]
)
def test_parsed_file_cannot_disagree_with_its_captured_directory_entry(
    field: str, value: object
) -> None:
    from bookscan import fontconfig_record

    data = literal()
    files = cast(list[dict[str, object]], data["files"])
    files[1][field] = value
    with pytest.raises(resource_record.ResourceRecordError):
        fontconfig_record.restore_guard(data)


def test_configuration_cannot_be_both_file_and_directory() -> None:
    from bookscan import fontconfig_record

    data = literal()
    files = cast(list[dict[str, object]], data["files"])
    files.append({**file(), "path": "/historical/rules"})
    files.sort(key=lambda item: str(item["path"]))
    with pytest.raises(resource_record.ResourceRecordError):
        fontconfig_record.restore_guard(data)
