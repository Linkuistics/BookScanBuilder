"""Outer saved records cannot detach scope, libraries, cache or copied resources."""

import copy
import json
import subprocess
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from typing import Any, cast

import pytest
from test_fontconfig_cache_record import literal as cache_literal
from test_linked_record import CHILD, ROOT
from test_linked_record import literal as linked_literal

from bookscan import fontconfig, resource_record

ROOT_COPY = "/private/snapshot"
CACHE_COPY = ROOT_COPY + "/bookscan-private-font-cache"
SNAPSHOT_LIMITATION = (
    "Supported selected configuration/font copy; native libraries/templates stay host-bound. "
    "No independent glyph truth."
)


def literal(*, cache: bool = False) -> dict[str, Any]:
    construction, binding = cache_literal()
    linked, natives = linked_literal()
    files = cast(list[dict[str, Any]], binding["files"])
    existing = {item["path"] for item in files}
    files.extend(
        item
        for item in cast(list[dict[str, Any]], natives["files"])
        if item["path"] not in existing
    )
    files.sort(key=lambda item: item["path"])
    guard = cast(dict[str, Any], binding["fontconfig_scope_guard"])
    value: dict[str, Any] = {
        "fontconfig_version": "2.18.3",
        "scope": copy.deepcopy(guard["scope"]),
        "binding": binding,
        "linked": linked,
        "runtime_resources_verified": False,
        "limitation": fontconfig.LIMITATION,
    }
    if cache:
        inputs = copy.deepcopy(binding)
        inputs["directories"] = [
            tree
            for tree in cast(list[dict[str, Any]], inputs["directories"])
            if tree["path"] != "/historical/cache"
        ]
        construction["inputs"] = inputs
        value["cache_construction"] = construction
    return value


def snapshot_literal() -> dict[str, Any]:
    original = literal()
    value = literal(cache=True)
    scope = value["scope"]
    loaded = {"/historical/fonts.conf", "/historical/rules", "/historical/rules/10.conf"}

    def mapped(name: str) -> str:
        return ROOT_COPY + name

    for field in ("config_files", "config_dirs", "parsed_files", "effective_font_dirs"):
        scope[field] = [mapped(name) for name in scope[field]]
    scope["font_dirs"] = scope["effective_font_dirs"].copy()
    scope["cache_dirs"] = [CACHE_COPY]
    scope["effective_cache_dirs"] = [CACHE_COPY]
    binding = value["binding"]
    for item in binding["files"]:
        if item["path"] in loaded:
            item["path"] = mapped(item["path"])
            item["resolved"] = item["path"]
    for tree in binding["directories"]:
        old = tree["path"]
        if old == "/historical/cache":
            tree["path"] = CACHE_COPY
            for entry in tree["entries"]:
                entry["path"] = entry["path"].replace(old, CACHE_COPY)
                entry["resolved"] = entry["path"]
        elif old != "/historical/templates":
            tree["path"] = mapped(old)
            for entry in cast(list[dict[str, Any]], tree["entries"] or []):
                entry["path"] = mapped(entry["path"])
                entry["resolved"] = entry["path"]
    cast(list[dict[str, Any]], binding["files"]).sort(key=lambda item: item["path"])
    cast(list[dict[str, Any]], binding["directories"]).sort(key=lambda item: item["path"])
    binding["fontconfig_scope_guard"]["scope"] = copy.deepcopy(scope)
    inputs = copy.deepcopy(binding)
    inputs["directories"] = [tree for tree in inputs["directories"] if tree["path"] != CACHE_COPY]
    value["cache_construction"].update(cache_root=CACHE_COPY, inputs=inputs)
    value["cache_construction"]["command"][-1] = CACHE_COPY
    value["resource_snapshot"] = {
        "method": "copied-path-cache-redirect",
        "configuration_file": "/historical/fonts.conf",
        "selection": "captured-fontconfig",
        "root": ROOT_COPY,
        "original": original,
        "runtime_resources_verified": False,
        "limitation": SNAPSHOT_LIMITATION,
    }
    return value


def test_outer_reader_binds_detached_facts_without_historical_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import fontconfig_discovery_record

    value = snapshot_literal()

    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Saved reads must not open historical paths or launch native tools")

    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(Path, "stat", denied)
    monkeypatch.setattr(Path, "resolve", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    result = fontconfig_discovery_record.restore(value)
    assert result.scope.config_files == (
        "/private/snapshot/historical/fonts.conf",
        "/private/snapshot/historical/rules",
    )
    assert result.linked.root == ROOT
    assert result.cache is not None and result.cache.cache_root == CACHE_COPY
    assert result.snapshot is not None
    assert (
        result.snapshot.root,
        result.snapshot.configuration_file,
        result.snapshot.selection,
    ) == (ROOT_COPY, "/historical/fonts.conf", "captured-fontconfig")
    assert result.snapshot.original.scope.cache_dirs == ("/logical/cache",)
    assert not hasattr(result, "verify") and not hasattr(result, "runtime_resources_verified")
    value["scope"]["config_files"] = []
    assert result.scope.config_files[0] == "/private/snapshot/historical/fonts.conf"
    with pytest.raises(FrozenInstanceError):
        result.snapshot.root = "/other"  # type: ignore[misc]


@pytest.mark.parametrize("cache", [False, True])
def test_optional_cache_does_not_invent_copy_or_execution(cache: bool) -> None:
    from bookscan import fontconfig_discovery_record

    result = fontconfig_discovery_record.restore(literal(cache=cache))
    assert result.snapshot is None
    assert (result.cache is not None) is cache
    assert result.binding.environment_sha256 == "0" * 64


OUTER_FAULTS = (
    "extra",
    "missing",
    "version",
    "runtime",
    "runtime-int",
    "limitation",
    "scope",
    "no-guard",
    "guard-scope",
    "binding",
    "linked",
    "cache-none",
    "cache-list",
    "cache-foreign-library",
    "nan",
    "surrogate",
    "nonjson",
    "key-int",
    "tuple-scope",
)


@pytest.mark.parametrize("fault", OUTER_FAULTS)
def test_outer_contradictions_fail_before_saved_state_can_be_used(fault: str) -> None:
    from bookscan import fontconfig_discovery_record

    value = literal(cache=True)
    if fault == "extra":
        value["native_verified"] = True
    elif fault == "missing":
        del value["linked"]
    elif fault == "version":
        value["fontconfig_version"] = "2.18.2"
    elif fault in ("runtime", "runtime-int"):
        value["runtime_resources_verified"] = True if fault == "runtime" else 0
    elif fault == "limitation":
        value["limitation"] = "Verified glyph fidelity"
    elif fault == "scope":
        value["scope"]["font_dirs"] = ["/other"]
    elif fault == "no-guard":
        del value["binding"]["fontconfig_scope_guard"]
    elif fault == "guard-scope":
        value["binding"]["fontconfig_scope_guard"]["scope"]["font_dirs"] = ["/other"]
    elif fault == "binding":
        value["binding"]["environment_sha256"] = "bad"
    elif fault == "linked":
        value["linked"]["files"][ROOT]["sha256"] = "1" * 64
    elif fault == "cache-none":
        value["cache_construction"] = None
    elif fault == "cache-list":
        value["cache_construction"] = []
    elif fault == "cache-foreign-library":
        other = "/historical/libfontconfig.2.dylib"
        item = next(row for row in value["binding"]["files"] if row["path"] == CHILD)
        for bound in (value["binding"], value["cache_construction"]["inputs"]):
            bound["files"].append({**item, "path": other, "resolved": other})
            cast(list[dict[str, Any]], bound["files"]).sort(key=lambda row: row["path"])
        value["cache_construction"]["command"][3] = other
    elif fault == "nan":
        value["scope"]["font_dirs"] = [float("nan")]
    elif fault == "surrogate":
        value["scope"]["font_dirs"] = ["/bad\ud800"]
    elif fault == "nonjson":
        value["scope"]["font_dirs"] = [Path("/fonts")]
    elif fault == "key-int":
        value["scope"][1] = []
    elif fault == "tuple-scope":
        value["scope"]["font_dirs"] = ("/logical/fonts",)
    else:
        raise AssertionError(fault)
    with pytest.raises(resource_record.ResourceRecordError) as raised:
        fontconfig_discovery_record.restore(value)
    assert (raised.value.code, raised.value.exit_code) == ("INVALID_PROJECT", 3)


SNAPSHOT_FAULTS = (
    "extra",
    "missing",
    "none",
    "method",
    "runtime",
    "limitation",
    "selection",
    "root-relative",
    "root-parent",
    "root-alias",
    "root-overlap",
    "config-relative",
    "config-unloaded",
    "original-copy",
    "original-cache",
    "original-linked",
    "no-cache",
    "cache-root",
    "scope-config",
    "scope-parsed",
    "scope-font",
    "scope-template",
    "scope-cache",
    "host-template",
    "host-native",
    "working-directory",
)


@pytest.mark.parametrize("fault", SNAPSHOT_FAULTS)
def test_copied_snapshot_cannot_detach_source_selection_or_confined_subjects(fault: str) -> None:
    from bookscan import fontconfig_discovery_record

    value = snapshot_literal()
    saved = value["resource_snapshot"]
    original = saved["original"]
    if fault == "extra":
        saved["native_verified"] = True
    elif fault == "missing":
        del saved["original"]
    elif fault == "none":
        value["resource_snapshot"] = None
    elif fault in ("method", "limitation", "selection"):
        saved[fault] = "invented"
    elif fault == "runtime":
        saved["runtime_resources_verified"] = True
    elif fault.startswith("root-"):
        saved["root"] = {
            "root-relative": "snapshot",
            "root-parent": "/private/old/../snapshot",
            "root-alias": "/private//snapshot",
            "root-overlap": "/historical",
        }[fault]
    elif fault == "config-relative":
        saved["configuration_file"] = "fonts.conf"
    elif fault == "config-unloaded":
        saved["configuration_file"] = "/historical/unloaded.conf"
    elif fault == "original-copy":
        original["resource_snapshot"] = copy.deepcopy(saved)
    elif fault == "original-cache":
        original["cache_construction"] = copy.deepcopy(value["cache_construction"])
    elif fault == "original-linked":
        original["linked"]["os_build"] = "foreign-build"
    elif fault == "no-cache":
        del value["cache_construction"]
    elif fault == "cache-root":
        saved["root"] = "/foreign-snapshot"
    elif fault.startswith("scope-"):
        field = {
            "scope-config": "config_dirs",
            "scope-parsed": "parsed_files",
            "scope-font": "font_dirs",
            "scope-template": "template_dirs",
            "scope-cache": "cache_dirs",
        }[fault]
        # Keep the outer record and scope guard coherent; reject the copy mapping itself.
        if fault == "scope-config":
            value["scope"][field] = []
        elif fault == "scope-parsed":
            value["scope"][field] = [value["scope"][field][0]]
        elif fault == "scope-font":
            value["scope"][field] = ["/unconfined/fonts"]
        elif fault == "scope-template":
            value["scope"][field] = [value["scope"]["effective_font_dirs"][0]]
        else:
            value["scope"][field] = ["/logical/foreign-cache"]
        for bound in (value["binding"], value["cache_construction"]["inputs"]):
            bound["fontconfig_scope_guard"]["scope"] = copy.deepcopy(value["scope"])
    elif fault == "host-template":
        original["binding"]["directories"][-1]["entries"] = []
    elif fault == "host-native":
        original["binding"]["files"][0]["inode"] = 999
    elif fault == "working-directory":
        original["binding"]["working_directory_identity"] = [999, 2]
    else:
        raise AssertionError(fault)
    with pytest.raises(resource_record.ResourceRecordError):
        fontconfig_discovery_record.restore(value)


@pytest.mark.parametrize("selection", ["explicit", "captured-fontconfig"])
def test_copied_configuration_bytes_may_change_without_inventing_font_fidelity(
    selection: str,
) -> None:
    from bookscan import fontconfig_discovery_record

    value = snapshot_literal()
    value["resource_snapshot"]["selection"] = selection
    result = fontconfig_discovery_record.restore(json.loads(json.dumps(value)))
    assert result.snapshot is not None and result.snapshot.selection == selection
    assert asdict(result.snapshot.original.scope)["font_dirs"] == ("/logical/fonts",)


@pytest.mark.parametrize("bad_predecessor", [False, True])
def test_hash_valid_predecessor_is_verified_on_source_loss_resume(
    tmp_path: Path, bad_predecessor: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import fontconfig_discovery_record, ownership, project_header

    path = tmp_path / "Project"
    path.mkdir()
    good: dict[str, object] = {"resources": snapshot_literal()}
    bad = copy.deepcopy(good)
    cast(dict[str, Any], bad["resources"])["scope"]["font_dirs"] = ["/foreign"]
    with ownership.Writer.acquire(path, ownership.provision(path)) as owner:
        stores = project_header.Stores.provision(owner)
        previous = stores.checkpoints.commit(
            bad if bad_predecessor else good, expected=None, verify_state=lambda _: None
        ).checkpoint
        stores.checkpoints.commit(good, expected=previous, verify_state=lambda _: None)
    before = {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()}

    def verify(images: object, state: dict[str, object]) -> None:
        fontconfig_discovery_record.restore(state["resources"])

    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Resume must not launch native tools")

    monkeypatch.setattr(subprocess, "Popen", denied)
    if bad_predecessor:
        with pytest.raises(resource_record.ResourceRecordError):
            with project_header.resume(
                path, verify_state=lambda stores, state: verify(stores.images, state)
            ):
                pytest.fail("Contradictory predecessor was accepted")
    else:
        with project_header.resume(
            path, verify_state=lambda stores, state: verify(stores.images, state)
        ) as (_, current):
            assert current.revision == 2 and current.state == good
    assert {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()} == before


def font_snapshot() -> dict[str, Any]:
    from test_resource_record import entry

    value = snapshot_literal()
    original = value["resource_snapshot"]["original"]
    for data, prefix in ((original, ""), (value, ROOT_COPY)):
        tree = next(
            row
            for row in data["binding"]["directories"]
            if row["path"] == prefix + "/historical/fonts"
        )
        top = entry(prefix + "/historical/fonts", "directory")
        top["members"] = ["face"]
        tree["entries"] = [top, entry(prefix + "/historical/fonts/face", "file")]
    refresh_inputs(value)
    return value


def refresh_inputs(value: dict[str, Any]) -> None:
    inputs = copy.deepcopy(value["binding"])
    inputs["directories"] = [row for row in inputs["directories"] if row["path"] != CACHE_COPY]
    value["cache_construction"]["inputs"] = inputs


@pytest.mark.parametrize("fault", ["digest", "size", "absence", "host-alias", "foreign-entry"])
def test_copied_font_inventory_preserves_source_bytes_and_severs_host_routes(fault: str) -> None:
    from bookscan import fontconfig_discovery_record

    value = font_snapshot()
    tree = next(
        row for row in value["binding"]["directories"] if row["path"].endswith("/historical/fonts")
    )
    if fault == "absence":
        tree["entries"] = None
    elif fault == "foreign-entry":
        tree["entries"][0]["members"] = ["face", "foreign"]
        tree["entries"].append(
            {
                **tree["entries"][1],
                "path": tree["path"] + "/foreign",
                "resolved": tree["path"] + "/foreign",
            }
        )
    else:
        tree["entries"][1][
            {"digest": "sha256", "size": "size", "host-alias": "resolved"}[fault]
        ] = {"digest": "1" * 64, "size": 4, "host-alias": "/historical/fonts/face"}[fault]
    refresh_inputs(value)
    with pytest.raises(resource_record.ResourceRecordError):
        fontconfig_discovery_record.restore(value)


def test_copied_font_inventory_retains_bytes_without_retaining_native_identity() -> None:
    from bookscan import fontconfig_discovery_record

    value = font_snapshot()
    tree = next(
        row for row in value["binding"]["directories"] if row["path"].endswith("/historical/fonts")
    )
    tree["entries"][1].update(device=9, inode=10, entry_device=9, entry_inode=10)
    refresh_inputs(value)
    result = fontconfig_discovery_record.restore(value)
    assert result.snapshot is not None
    assert result.scope.font_dirs == ("/private/snapshot/historical/fonts",)


def test_snapshot_overlap_uses_saved_resolved_input_identity() -> None:
    from bookscan import fontconfig_discovery_record

    value = snapshot_literal()
    original = value["resource_snapshot"]["original"]
    next(row for row in original["binding"]["files"] if row["path"] == "/historical/fonts.conf")[
        "resolved"
    ] = "/private/snapshot/source.conf"
    with pytest.raises(resource_record.ResourceRecordError):
        fontconfig_discovery_record.restore(value)


def test_mapped_configuration_file_cannot_keep_a_route_back_to_the_host() -> None:
    from bookscan import fontconfig_discovery_record

    value = snapshot_literal()
    next(
        row for row in value["binding"]["files"] if row["path"].endswith("/historical/fonts.conf")
    )["resolved"] = "/historical/fonts.conf"
    refresh_inputs(value)
    with pytest.raises(resource_record.ResourceRecordError):
        fontconfig_discovery_record.restore(value)
