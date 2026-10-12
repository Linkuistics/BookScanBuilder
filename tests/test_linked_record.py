"""Saved loader closure cannot invent linked files, digests or native execution."""

import copy
import hashlib
import json
import shutil
import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest
from test_dependencies import commands
from test_resource_record import SHA, file
from test_resource_record import literal as named_literal

from bookscan import dependencies, resource_record
from bookscan.resources import ResourceBinding

ROOT = "/historical/program"
CHILD = "/historical/libfontconfig.1.dylib"
SYSTEM = "/usr/lib/libSystem.B.dylib"


def literal() -> tuple[dict[str, object], dict[str, object]]:
    binding = named_literal()
    binding["files"] = [
        {**file(), "path": name, "resolved": name} for name in sorted((ROOT, CHILD))
    ]
    linked: dict[str, object] = {
        "root": ROOT,
        "executable_context": "/historical/python",
        "architecture": "arm64",
        "os_build": "26A434",
        "files": {
            ROOT: {
                "sha256": SHA,
                "load_commands": commands(
                    Path(ROOT),
                    ("LC_LOAD_DYLIB", "@loader_path/libfontconfig.1.dylib"),
                    ("LC_LOAD_WEAK_DYLIB", SYSTEM),
                ),
                "references": [
                    {
                        "kind": "LC_LOAD_DYLIB",
                        "reference": "@loader_path/libfontconfig.1.dylib",
                        "resolved": CHILD,
                    },
                    {
                        "kind": "LC_LOAD_WEAK_DYLIB",
                        "reference": SYSTEM,
                        "identity": "OS shared-cache reference; disk bytes not claimed",
                    },
                ],
            },
            CHILD: {
                "sha256": SHA,
                "load_commands": commands(
                    Path(CHILD), ("LC_ID_DYLIB", CHILD), ("LC_REEXPORT_DYLIB", ROOT)
                ),
                "references": [{"kind": "LC_REEXPORT_DYLIB", "reference": ROOT, "resolved": ROOT}],
            },
        },
        "system_references": [SYSTEM],
        "runtime_resources_verified": False,
        "limitation": dependencies.LIMITATION,
    }
    return linked, binding


def test_detached_static_facts_never_reopen_or_resolve_historical_subjects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import linked_record

    linked, binding = literal()

    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Historical file/native access forbidden")

    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(Path, "stat", denied)
    monkeypatch.setattr(Path, "resolve", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    result = linked_record.restore(linked, binding)
    assert (result.root, result.executable_context, result.architecture, result.os_build) == (
        ROOT,
        "/historical/python",
        "arm64",
        "26A434",
    )
    assert result.system_references == (SYSTEM,)
    assert [(item.path, item.sha256) for item in result.files] == [(CHILD, SHA), (ROOT, SHA)]
    assert result.files[0].references[0].resolved == ROOT
    assert result.files[1].references[1].resolved is None
    assert not hasattr(result, "verify") and not hasattr(result, "runtime_resources_verified")
    linked["files"] = {}
    binding["files"] = []
    assert result.files[0].sha256 == SHA
    with pytest.raises(FrozenInstanceError):
        result.root = "/foreign"  # type: ignore[misc]


@pytest.mark.parametrize("architecture", ["arm64", "x86_64"])
@pytest.mark.parametrize("kind", sorted(dependencies.LOADS))
def test_all_declared_load_kinds_and_cycles_remain_static_facts(
    architecture: str,
    kind: str,
) -> None:
    from bookscan import linked_record

    linked, binding = literal()
    linked["architecture"] = architecture
    root = cast(dict[str, dict[str, object]], linked["files"])[ROOT]
    root["load_commands"] = commands(Path(ROOT), (kind, CHILD))
    root["references"] = [{"kind": kind, "reference": CHILD, "resolved": CHILD}]
    linked["system_references"] = []
    result = linked_record.restore(linked, binding)
    assert result.files[1].references[0].kind == kind
    assert result.architecture == architecture


@pytest.mark.parametrize(
    "fault",
    [
        "not-object",
        "extra-field",
        "missing-field",
        "runtime-use",
        "limitation",
        "architecture",
        "empty-build",
        "nul-build",
        "relative-root",
        "parent-root",
        "noncanonical-root",
        "missing-root",
        "relative-context",
        "surrogate",
        "files-array",
        "extra-file-field",
        "bad-digest",
        "unbound-file",
        "absent-file",
        "digest-disagreement",
        "resolved-disagreement",
        "load-array",
        "load-nul",
        "load-wrong-file",
        "load-missing-command",
        "load-wrong-kind",
        "refs-array",
        "ref-extra",
        "ref-missing",
        "ref-order",
        "ref-kind",
        "ref-reference",
        "ref-target",
        "ref-relative",
        "ref-unrecognized",
        "system-fake-digest",
        "system-parent",
        "system-missing",
        "system-extra",
        "system-duplicate",
        "system-unsorted",
        "orphan",
        "empty-files",
        "non-json",
        "nan",
    ],
)
def test_hash_valid_contradictions_are_refused(fault: str) -> None:
    from bookscan import linked_record

    linked, binding = literal()
    files = cast(dict[str, dict[str, object]], linked["files"])
    root = files[ROOT]
    refs = cast(list[dict[str, object]], root["references"])
    named = cast(list[dict[str, object]], binding["files"])
    candidate: object = linked
    replacements: dict[str, tuple[str, object]] = {
        "runtime-use": ("runtime_resources_verified", True),
        "limitation": ("limitation", "Native resources verified"),
        "architecture": ("architecture", "aarch64"),
        "empty-build": ("os_build", ""),
        "nul-build": ("os_build", "26\0"),
        "relative-root": ("root", "program"),
        "parent-root": ("root", "/historical/a/../program"),
        "noncanonical-root": ("root", "/historical//program"),
        "missing-root": ("root", "/missing"),
        "relative-context": ("executable_context", "python"),
        "surrogate": ("os_build", "\ud800"),
        "files-array": ("files", []),
        "system-missing": ("system_references", []),
        "system-extra": ("system_references", [SYSTEM, "/usr/lib/foreign.dylib"]),
        "system-duplicate": ("system_references", [SYSTEM, SYSTEM]),
        "system-unsorted": ("system_references", ["/usr/lib/z.dylib", SYSTEM]),
        "empty-files": ("files", {}),
        "non-json": ("os_build", Path("/build")),
        "nan": ("os_build", float("nan")),
    }
    if fault in replacements:
        name, value = replacements[fault]
        linked[name] = value
    elif fault == "not-object":
        candidate = []
    elif fault == "extra-field":
        linked["verified"] = True
    elif fault == "missing-field":
        del linked["architecture"]
    elif fault == "extra-file-field":
        root["opened"] = True
    elif fault == "bad-digest":
        root["sha256"] = "not-a-digest"
    elif fault == "unbound-file":
        named.pop()
    elif fault == "absent-file":
        named[1].update(resolved=None, device=None, inode=None, size=None, sha256=None)
    elif fault == "digest-disagreement":
        root["sha256"] = "1" * 64
    elif fault == "resolved-disagreement":
        named[1]["resolved"] = "/foreign/program"
    elif fault in ("load-array", "load-nul", "load-wrong-file", "load-missing-command"):
        root["load_commands"] = {
            "load-array": [],
            "load-nul": "\0",
            "load-wrong-file": commands(Path(CHILD)),
            "load-missing-command": commands(Path(ROOT), ("LC_ID_DYLIB", ROOT)),
        }[fault]
    elif fault == "load-wrong-kind":
        root["load_commands"] = str(root["load_commands"]).replace(
            "LC_LOAD_DYLIB", "LC_REEXPORT_DYLIB"
        )
    elif fault == "refs-array":
        root["references"] = tuple(refs)
    elif fault == "ref-extra":
        refs[0]["opened"] = True
    elif fault == "ref-missing":
        refs.pop()
    elif fault == "ref-order":
        refs.reverse()
    elif fault in ("ref-kind", "ref-reference", "ref-target", "ref-relative"):
        key, value = {
            "ref-kind": ("kind", "LC_REEXPORT_DYLIB"),
            "ref-reference": ("reference", "@loader_path/foreign"),
            "ref-target": ("resolved", "/unbound"),
            "ref-relative": ("resolved", "library"),
        }[fault]
        refs[0][key] = value
    elif fault == "ref-unrecognized":
        refs[0]["reference"] = "relative.dylib"
        root["load_commands"] = str(root["load_commands"]).replace(
            "@loader_path/libfontconfig.1.dylib", "relative.dylib"
        )
    elif fault == "system-fake-digest":
        refs[1]["resolved"] = SYSTEM
        del refs[1]["identity"]
    elif fault == "system-parent":
        text = "/usr/lib/../../private/foreign.dylib"
        refs[1]["reference"] = text
        root["load_commands"] = str(root["load_commands"]).replace(SYSTEM, text)
        linked["system_references"] = [text]
    elif fault == "orphan":
        orphan = "/historical/orphan"
        files[orphan] = {
            "sha256": SHA,
            "load_commands": commands(Path(orphan), ("LC_ID_DYLIB", orphan)),
            "references": [],
        }
        named.append({**file(), "path": orphan, "resolved": orphan})
        named.sort(key=lambda item: str(item["path"]))
    else:
        raise AssertionError(fault)
    with pytest.raises(resource_record.ResourceRecordError) as caught:
        linked_record.restore(candidate, binding)
    assert (caught.value.code, caught.value.exit_code) == ("INVALID_PROJECT", 3)


def test_real_captured_subject_bytes_can_disappear_before_reading(tmp_path: Path) -> None:
    from bookscan import linked_record

    root = tmp_path / "historical"
    root.mkdir()
    native = root / "program"
    native.write_bytes(b"saved bytes")
    binding = ResourceBinding.capture([native], environment={}).record()
    linked: dict[str, object] = {
        "root": str(native),
        "executable_context": str(native),
        "architecture": "arm64",
        "os_build": "saved-build",
        "system_references": [],
        "files": {
            str(native): {
                "sha256": hashlib.sha256(b"saved bytes").hexdigest(),
                "load_commands": commands(native, ("LC_ID_DYLIB", str(native))),
                "references": [],
            }
        },
        "runtime_resources_verified": False,
        "limitation": dependencies.LIMITATION,
    }
    shutil.rmtree(root)
    result = linked_record.restore(json.loads(json.dumps(linked)), binding)
    assert result.files[0].sha256 == hashlib.sha256(b"saved bytes").hexdigest()


@pytest.mark.parametrize(
    "header", [ROOT + "-other:", ROOT + " (architecture x86_64):", ROOT + " garbage:"]
)
def test_captured_header_cannot_name_a_prefix_neighbor_or_different_architecture(
    header: str,
) -> None:
    from bookscan import linked_record

    linked, binding = literal()
    root = cast(dict[str, dict[str, object]], linked["files"])[ROOT]
    root["load_commands"] = str(root["load_commands"]).replace(ROOT + ":", header, 1)
    with pytest.raises(resource_record.ResourceRecordError):
        linked_record.restore(linked, binding)


def test_explicit_captured_architecture_header_needs_no_current_host_identity() -> None:
    from bookscan import linked_record

    linked, binding = literal()
    for path, row in cast(dict[str, dict[str, object]], linked["files"]).items():
        row["load_commands"] = str(row["load_commands"]).replace(
            path + ":", path + " (architecture arm64):", 1
        )
    result = linked_record.restore(linked, binding)
    assert result.architecture == "arm64" and len(result.files) == 2


@pytest.mark.parametrize("bad_predecessor", [False, True])
def test_restart_checks_linked_meaning_in_every_hash_valid_predecessor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_predecessor: bool,
) -> None:
    from bookscan import linked_record, ownership, project_header

    path = tmp_path / "Saved project"
    path.mkdir()
    linked, binding = literal()
    good: dict[str, object] = {"linked": linked, "binding": binding}
    bad = copy.deepcopy(good)
    cast(dict[str, object], bad["linked"])["runtime_resources_verified"] = True
    with ownership.Writer.acquire(path, ownership.provision(path)) as owner:
        stores = project_header.Stores.provision(owner)
        old = stores.checkpoints.commit(
            bad if bad_predecessor else good, expected=None, verify_state=lambda _: None
        ).checkpoint
        stores.checkpoints.commit(good, expected=old, verify_state=lambda _: None)
    before = {item.name: item.read_bytes() for item in (path / "checkpoints").iterdir()}

    def verify(images: object, state: dict[str, object]) -> None:
        linked_record.restore(state["linked"], state["binding"])

    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Restart cannot launch native tools")

    monkeypatch.setattr(subprocess, "Popen", denied)
    if bad_predecessor:
        with pytest.raises(resource_record.ResourceRecordError):
            with project_header.resume(
                path, verify_state=lambda stores, state: verify(stores.images, state)
            ):
                pytest.fail("Invalid linked predecessor accepted")
    else:
        with project_header.resume(
            path, verify_state=lambda stores, state: verify(stores.images, state)
        ) as (_, current):
            assert current.revision == 2 and current.state == good
    assert {item.name: item.read_bytes() for item in (path / "checkpoints").iterdir()} == before
