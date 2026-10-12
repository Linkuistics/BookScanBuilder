"""Construction records cannot invent a mutable input exemption or native use."""

import copy
import json
import shutil
import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest
from test_fontconfig_record import literal as guarded_literal
from test_resource_record import entry, file

from bookscan import fontconfig, resource_record
from bookscan.resources import ResourceBinding


def literal() -> tuple[dict[str, object], dict[str, object]]:
    warm = guarded_literal()
    files = cast(list[dict[str, object]], warm["files"])
    for path in (
        "/historical/python",
        "/historical/fontconfig_probe.py",
        "/historical/libfontconfig.1.dylib",
    ):
        files.append({**file(), "path": path, "resolved": path})
    files.sort(key=lambda item: str(item["path"]))
    trees = cast(list[dict[str, object]], warm["directories"])
    cache = entry("/historical/cache", "directory")
    cache["members"] = ["cache-file"]
    trees[0]["entries"] = [cache, entry("/historical/cache/cache-file", "file")]
    inputs = copy.deepcopy(warm)
    inputs["directories"] = copy.deepcopy(trees[1:])
    construction: dict[str, object] = {
        "method": "FcConfigBuildFonts",
        "initially_empty": True,
        "cache_root": "/historical/cache",
        "command": [
            "/historical/python",
            "-I",
            "/historical/fontconfig_probe.py",
            "/historical/libfontconfig.1.dylib",
            "--build-cache",
            "/historical/cache",
        ],
        "inputs": inputs,
    }
    return construction, warm


def test_construction_is_detached_and_never_reopens_historical_subjects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import fontconfig_cache_record

    construction, warm = literal()

    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Historical I/O and native execution forbidden")

    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(Path, "stat", denied)
    monkeypatch.setattr(Path, "resolve", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    result = fontconfig_cache_record.restore_cache(construction, warm)
    assert result is not None
    assert result.cache_root == "/historical/cache"
    assert result.command == (
        "/historical/python",
        "-I",
        "/historical/fontconfig_probe.py",
        "/historical/libfontconfig.1.dylib",
        "--build-cache",
        "/historical/cache",
    )
    assert [item.path for item in result.inputs.directories] == [
        "/historical/fonts",
        "/historical/optional",
        "/historical/rules",
        "/historical/templates",
    ]
    assert not hasattr(result.inputs, "verify")
    construction["command"] = []
    assert result.command[4] == "--build-cache"
    with pytest.raises(FrozenInstanceError):
        result.cache_root = "/foreign"  # type: ignore[misc]


def test_no_construction_does_not_infer_cache_build() -> None:
    from bookscan import fontconfig_cache_record

    _, warm = literal()
    assert fontconfig_cache_record.restore_cache(None, warm) is None
    warm["runtime_resources_verified"] = True
    with pytest.raises(resource_record.ResourceRecordError):
        fontconfig_cache_record.restore_cache(None, warm)


@pytest.mark.parametrize(
    "fault",
    [
        "not-object",
        "extra-field",
        "missing-field",
        "wrong-method",
        "empty-false",
        "empty-int",
        "relative-root",
        "parent-root",
        "alias-root",
        "foreign-root",
        "nul-root",
        "surrogate-root",
        "command-tuple",
        "command-short",
        "command-extra",
        "command-int",
        "isolation-lost",
        "wrong-mode",
        "wrong-command-root",
        "unbound-python",
        "absent-python",
        "wrong-probe",
        "wrong-library",
        "inputs-list",
        "missing-guard",
        "changed-guard",
        "missing-file",
        "extra-file",
        "changed-file",
        "missing-tree",
        "changed-tree",
        "mutable-cache-input",
        "changed-environment",
        "changed-cwd",
        "changed-cwd-identity",
        "warm-unguarded",
        "warm-absent-cache",
        "warm-cache-alias",
        "extra-effective-cache",
        "warm-runtime-use",
        "input-runtime-use",
        "non-json",
        "nan",
    ],
)
def test_contradictory_construction_is_refused(fault: str) -> None:
    from bookscan import fontconfig_cache_record

    data, warm = literal()
    inputs = cast(dict[str, object], data["inputs"])
    command = cast(list[object], data["command"])
    files = cast(list[dict[str, object]], inputs["files"])
    trees = cast(list[dict[str, object]], inputs["directories"])
    guard = cast(dict[str, object], warm["fontconfig_scope_guard"])
    scope = cast(dict[str, object], guard["scope"])
    replacements: dict[str, tuple[str, object]] = {
        "wrong-method": ("method", "renderer-opens-verified"),
        "empty-false": ("initially_empty", False),
        "empty-int": ("initially_empty", 1),
        "relative-root": ("cache_root", "cache"),
        "parent-root": ("cache_root", "/historical/old/../cache"),
        "alias-root": ("cache_root", "/historical/cache-alias"),
        "foreign-root": ("cache_root", "/foreign"),
        "nul-root": ("cache_root", "/cache\0"),
        "surrogate-root": ("cache_root", "/cache\ud800"),
        "command-tuple": ("command", tuple(command)),
        "command-short": ("command", command[:-1]),
        "command-extra": ("command", [*command, "--force"]),
        "inputs-list": ("inputs", []),
        "non-json": ("cache_root", Path("/cache")),
        "nan": ("initially_empty", float("nan")),
    }
    commands: dict[str, tuple[int, object]] = {
        "command-int": (0, 7),
        "isolation-lost": (1, "-c"),
        "wrong-mode": (4, "--resolve-configuration"),
        "wrong-command-root": (5, "/foreign"),
        "unbound-python": (0, "/unbound/python"),
        "wrong-probe": (2, "/historical/fonts.conf"),
        "wrong-library": (3, "/historical/python"),
    }
    candidate: object = data
    if fault in replacements:
        key, value = replacements[fault]
        data[key] = value
    elif fault in commands:
        index, value = commands[fault]
        command[index] = value
    elif fault == "not-object":
        candidate = []
    elif fault == "extra-field":
        data["runtime_resources_verified"] = True
    elif fault == "missing-field":
        del data["inputs"]
    elif fault == "missing-guard":
        del inputs["fontconfig_scope_guard"]
    elif fault == "changed-guard":
        cast(dict[str, object], inputs["fontconfig_scope_guard"])["verification"] = "actual-opens"
    elif fault == "missing-file":
        files.pop()
    elif fault == "extra-file":
        files.append({**file(), "path": "/z/foreign", "resolved": "/z/foreign"})
    elif fault in ("changed-file", "absent-python"):
        target = next(item for item in files if item["path"] == "/historical/python")
        target.update(
            {"sha256": "1" * 64}
            if fault == "changed-file"
            else {
                "resolved": None,
                "device": None,
                "inode": None,
                "size": None,
                "sha256": None,
            }
        )
    elif fault == "missing-tree":
        trees.pop()
    elif fault == "changed-tree":
        trees[0]["entries"] = [entry("/historical/fonts", "directory")]
    elif fault == "mutable-cache-input":
        trees.insert(0, copy.deepcopy(cast(list[dict[str, object]], warm["directories"])[0]))
    elif fault == "changed-environment":
        inputs["environment_sha256"] = "1" * 64
    elif fault == "changed-cwd":
        inputs["working_directory"] = "/other/cwd"
    elif fault == "changed-cwd-identity":
        inputs["working_directory_identity"] = [77, 88]
    elif fault == "warm-unguarded":
        del warm["fontconfig_scope_guard"]
    elif fault == "warm-absent-cache":
        cast(list[dict[str, object]], warm["directories"])[0]["entries"] = None
    elif fault == "warm-cache-alias":
        cache_entry = cast(
            list[dict[str, object]],
            cast(list[dict[str, object]], warm["directories"])[0]["entries"],
        )[0]
        cache_entry["resolved"] = "/foreign/cache"
    elif fault == "extra-effective-cache":
        scope["effective_cache_dirs"] = ["/historical/cache", "/historical/fonts"]
        inputs["fontconfig_scope_guard"] = copy.deepcopy(guard)
    elif fault == "warm-runtime-use":
        warm["runtime_resources_verified"] = True
    elif fault == "input-runtime-use":
        inputs["runtime_resources_verified"] = True
    else:
        raise AssertionError(fault)
    with pytest.raises(resource_record.ResourceRecordError) as raised:
        fontconfig_cache_record.restore_cache(candidate, warm)
    assert (raised.value.code, raised.value.exit_code) == ("INVALID_PROJECT", 3)


@pytest.mark.parametrize("canonical_named", [False, True])
def test_effective_aliases_use_recorded_targets_without_resolving_them(
    canonical_named: bool,
) -> None:
    from bookscan import fontconfig_cache_record

    data, warm = literal()
    trees = cast(list[dict[str, object]], warm["directories"])
    alias = copy.deepcopy(trees[0])
    alias["path"] = "/historical/cache-alias"
    for item in cast(list[dict[str, object]], alias["entries"]):
        item["path"] = str(item["path"]).replace("/historical/cache", "/historical/cache-alias")
    root = cast(list[dict[str, object]], alias["entries"])[0]
    root.update(link_target="cache", entry_inode=999)
    trees.insert(1, alias)
    if not canonical_named:
        trees.pop(0)
    for binding in (warm, cast(dict[str, object], data["inputs"])):
        scope = cast(
            dict[str, object], cast(dict[str, object], binding["fontconfig_scope_guard"])["scope"]
        )
        scope["effective_cache_dirs"] = ["/historical/cache-alias"]
    result = fontconfig_cache_record.restore_cache(data, warm)
    assert result is not None and result.cache_root == "/historical/cache"


@pytest.mark.parametrize("overlap", ["ancestor", "child", "same"])
def test_resolved_fixed_input_cannot_overlap_mutable_cache(overlap: str) -> None:
    from bookscan import fontconfig_cache_record

    data, warm = literal()
    target = {
        "ancestor": "/historical",
        "child": "/historical/cache/fonts",
        "same": "/historical/cache",
    }[overlap]
    for binding in (warm, cast(dict[str, object], data["inputs"])):
        trees = cast(list[dict[str, object]], binding["directories"])
        fonts = next(item for item in trees if item["path"] == "/historical/fonts")
        root = entry("/historical/fonts", "directory")
        root.update(resolved=target, link_target=target, entry_inode=999)
        fonts["entries"] = [root]
    with pytest.raises(resource_record.ResourceRecordError):
        fontconfig_cache_record.restore_cache(data, warm)


def test_real_saved_cache_can_be_read_after_all_subjects_disappear(tmp_path: Path) -> None:
    from bookscan import fontconfig_cache_record

    root = tmp_path / "historical"
    root.mkdir()
    cache, fonts = root / "cache", root / "fonts"
    cache.mkdir()
    fonts.mkdir()
    config, python, probe, library = (
        root / name
        for name in (
            "fonts.conf",
            "python",
            "fontconfig_probe.py",
            "libfontconfig.1.dylib",
        )
    )
    for item in (config, python, probe, library):
        item.write_bytes(b"captured named file")
    scope = fontconfig.ConfiguredScope(
        (str(config),),
        (),
        (str(fonts),),
        (str(cache),),
        (str(root / "templates"),),
        (str(config),),
        (str(fonts),),
        (str(cache),),
    )
    inputs = ResourceBinding.capture(
        [config, python, probe, library],
        directories=[fonts],
        optional_directories=[root / "templates"],
        environment={},
    )
    (cache / "complete").write_bytes(b"complete cache")
    warm = ResourceBinding.capture(
        [config, python, probe, library],
        directories=[fonts, cache],
        optional_directories=[root / "templates"],
        environment={},
    )
    data: dict[str, object] = {
        "method": "FcConfigBuildFonts",
        "initially_empty": True,
        "cache_root": str(cache),
        "command": [str(python), "-I", str(probe), str(library), "--build-cache", str(cache)],
        "inputs": fontconfig.FontconfigBinding.guard(inputs, library, scope).record(),
    }
    completed = json.loads(
        json.dumps(fontconfig.FontconfigBinding.guard(warm, library, scope).record())
    )
    shutil.rmtree(root)
    result = fontconfig_cache_record.restore_cache(json.loads(json.dumps(data)), completed)
    assert result is not None and result.cache_root == str(cache)


@pytest.mark.parametrize("bad_predecessor", [False, True])
def test_restart_checks_cache_meaning_in_hash_valid_predecessors(
    tmp_path: Path,
    bad_predecessor: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import fontconfig_cache_record, ownership, project_header

    path = tmp_path / "Saved project"
    path.mkdir()
    construction, binding = literal()
    good: dict[str, object] = {"construction": construction, "binding": binding}
    bad = copy.deepcopy(good)
    cast(dict[str, object], bad["construction"])["initially_empty"] = False
    with ownership.Writer.acquire(path, ownership.provision(path)) as owner:
        stores = project_header.Stores.provision(owner)
        old = stores.checkpoints.commit(
            bad if bad_predecessor else good, expected=None, verify_state=lambda _: None
        ).checkpoint
        stores.checkpoints.commit(good, expected=old, verify_state=lambda _: None)
    before = {item.name: item.read_bytes() for item in (path / "checkpoints").iterdir()}

    def verify(images: object, state: dict[str, object]) -> None:
        fontconfig_cache_record.restore_cache(state["construction"], state["binding"])

    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Restart must not execute native tools")

    monkeypatch.setattr(subprocess, "Popen", denied)
    if bad_predecessor:
        with pytest.raises(resource_record.ResourceRecordError):
            with project_header.resume(
                path, verify_state=lambda stores, state: verify(stores.images, state)
            ):
                pytest.fail("Invalid construction predecessor accepted")
    else:
        with project_header.resume(
            path, verify_state=lambda stores, state: verify(stores.images, state)
        ) as (_, current):
            assert current.revision == 2 and current.state == good
    assert {item.name: item.read_bytes() for item in (path / "checkpoints").iterdir()} == before
