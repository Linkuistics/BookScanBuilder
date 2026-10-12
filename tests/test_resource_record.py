"""Saved named inventories must not invent historical resource verification."""

import copy
import json
import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest

from bookscan import records
from bookscan.resources import LIMITATION, ResourceBinding

SHA = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def file() -> dict[str, object]:
    return {
        "path": "/historical/config",
        "resolved": "/resolved/config",
        "device": 1,
        "inode": 2,
        "size": 3,
        "sha256": SHA,
    }


def entry(path: str, kind: str) -> dict[str, object]:
    return {
        "path": path,
        "resolved": path,
        "device": 1,
        "inode": 2,
        "entry_device": 1,
        "entry_inode": 2,
        "kind": kind,
        "link_target": None,
        "size": 3 if kind == "file" else None,
        "sha256": SHA if kind == "file" else None,
        "members": ["font"] if kind == "directory" else None,
    }


def literal() -> dict[str, object]:
    return {
        "environment_sha256": "0" * 64,
        "working_directory": "/historical/work",
        "working_directory_identity": [1, 2],
        "files": [file()],
        "directories": [
            {
                "path": "/historical/fonts",
                "entries": [
                    entry("/historical/fonts", "directory"),
                    entry("/historical/fonts/font", "file"),
                ],
            }
        ],
        "runtime_resources_verified": False,
        "limitation": LIMITATION,
    }


def test_literal_reader_returns_detached_named_facts_only() -> None:
    from bookscan import resource_record

    value = literal()
    result = resource_record.restore_named(records.decode(json.dumps(value).encode()))
    assert result.environment_sha256 == "0" * 64
    assert result.working_directory == "/historical/work"
    assert result.working_directory_identity == (1, 2)
    assert result.files[0].sha256 == SHA and result.files[0].size == 3
    assert result.directories[0].entries is not None
    assert result.directories[0].entries[0].members == ("font",)
    assert not hasattr(result, "environment") and not hasattr(result, "verify")
    cast(list[object], value["files"]).clear()
    assert len(result.files) == 1
    with pytest.raises(FrozenInstanceError):
        result.environment_sha256 = "1" * 64  # type: ignore[misc]


@pytest.mark.parametrize(
    "fault",
    [
        "extra-field",
        "missing-field",
        "runtime-verified",
        "integer-false",
        "lost-limitation",
        "environment-value",
        "bad-environment-digest",
        "uppercase-digest",
        "cwd-relative",
        "cwd-parent",
        "cwd-nul",
        "cwd-surrogate",
        "cwd-identity-bool",
        "cwd-identity-float",
        "cwd-identity-short",
        "nonobject",
        "tuple-files",
        "duplicate-files",
        "unsorted-files",
        "file-missing-field",
        "file-extra-field",
        "file-relative",
        "file-empty",
        "file-resolved-parent",
        "file-size-bool",
        "file-negative-size",
        "file-inode-null",
        "absent-file-present-digest",
        "absent-file-present-size",
        "present-file-no-digest",
        "file-digest-malformed",
        "directories-tuple",
        "duplicate-trees",
        "entries-empty",
        "entries-tuple",
        "duplicate-entry",
        "unsorted-entries",
        "root-missing",
        "root-file",
        "foreign-entry",
        "orphan-entry",
        "missing-member",
        "extra-member",
        "duplicate-member",
        "unsorted-members",
        "member-parent",
        "member-slash",
        "directory-with-size",
        "file-with-members",
        "unknown-kind",
        "native-identity-bool",
        "nonlink-native-mismatch",
        "dangling-with-native",
        "dangling-no-link",
        "dangling-with-digest",
        "file-link-empty",
        "entry-extra-field",
        "nonobject-guard",
        "nonstring-key",
        "cycle",
        "nan",
    ],
)
def test_contradictory_named_inventory_is_refused(fault: str) -> None:
    from bookscan import resource_record

    data = literal()
    files = cast(list[dict[str, object]], data["files"])
    trees = cast(list[dict[str, object]], data["directories"])
    entries = cast(list[dict[str, object]], trees[0]["entries"])
    root, leaf = entries
    value: object = data
    direct: dict[str, tuple[str, object]] = {
        "runtime-verified": ("runtime_resources_verified", True),
        "integer-false": ("runtime_resources_verified", 0),
        "lost-limitation": ("limitation", "Verified all renderer resources"),
        "bad-environment-digest": ("environment_sha256", "0" * 63),
        "uppercase-digest": ("environment_sha256", "A" * 64),
        "cwd-relative": ("working_directory", "work"),
        "cwd-parent": ("working_directory", "/historical/../work"),
        "cwd-nul": ("working_directory", "/work\0"),
        "cwd-surrogate": ("working_directory", "/work\ud800"),
        "cwd-identity-bool": ("working_directory_identity", [True, 2]),
        "cwd-identity-float": ("working_directory_identity", [1, 2.0]),
        "cwd-identity-short": ("working_directory_identity", [1]),
        "tuple-files": ("files", tuple(files)),
        "directories-tuple": ("directories", tuple(trees)),
        "nonobject-guard": ("fontconfig_scope_guard", []),
        "nan": ("environment_sha256", float("nan")),
    }
    file_changes: dict[str, tuple[str, object]] = {
        "file-relative": ("path", "config"),
        "file-empty": ("path", ""),
        "file-resolved-parent": ("resolved", "/x/../config"),
        "file-size-bool": ("size", True),
        "file-negative-size": ("size", -1),
        "file-inode-null": ("inode", None),
        "present-file-no-digest": ("sha256", None),
        "file-digest-malformed": ("sha256", "not a digest"),
    }
    if fault in direct:
        key, changed = direct[fault]
        data[key] = changed
    elif fault in file_changes:
        key, changed = file_changes[fault]
        files[0][key] = changed
    elif fault == "extra-field":
        data["extra"] = None
    elif fault == "missing-field":
        del data["environment_sha256"]
    elif fault == "environment-value":
        data["environment"] = {"SECRET": "do not restore"}
    elif fault == "nonobject":
        value = []
    elif fault == "duplicate-files":
        files.append(copy.deepcopy(files[0]))
    elif fault == "unsorted-files":
        files.append({**file(), "path": "/a"})
    elif fault == "file-missing-field":
        del files[0]["inode"]
    elif fault == "file-extra-field":
        files[0]["verified"] = True
    elif fault.startswith("absent-file"):
        files[0].update(resolved=None, device=None, inode=None, size=None, sha256=None)
        files[0]["sha256" if fault.endswith("digest") else "size"] = (
            SHA if fault.endswith("digest") else 3
        )
    elif fault == "duplicate-trees":
        trees.append(copy.deepcopy(trees[0]))
    elif fault == "entries-empty":
        trees[0]["entries"] = []
    elif fault == "entries-tuple":
        trees[0]["entries"] = tuple(entries)
    elif fault == "duplicate-entry":
        entries.append(copy.deepcopy(leaf))
    elif fault == "unsorted-entries":
        entries.reverse()
    elif fault == "root-missing":
        entries.pop(0)
    elif fault == "root-file":
        entries[0] = entry("/historical/fonts", "file")
        entries.pop()
    elif fault == "foreign-entry":
        leaf["path"] = "/elsewhere/font"
    elif fault == "orphan-entry":
        leaf["path"] = "/historical/fonts/missing/font"
    elif fault in (
        "missing-member",
        "extra-member",
        "duplicate-member",
        "unsorted-members",
        "member-parent",
        "member-slash",
    ):
        root["members"] = {
            "missing-member": [],
            "extra-member": ["font", "missing"],
            "duplicate-member": ["font", "font"],
            "unsorted-members": ["z", "font"],
            "member-parent": [".."],
            "member-slash": ["a/b"],
        }[fault]
    elif fault == "directory-with-size":
        root["size"] = 3
    elif fault == "file-with-members":
        leaf["members"] = []
    elif fault == "unknown-kind":
        leaf["kind"] = "fifo"
    elif fault == "native-identity-bool":
        leaf["entry_inode"] = True
    elif fault == "nonlink-native-mismatch":
        leaf["inode"] = 99
    elif fault.startswith("dangling-"):
        leaf.update(
            kind="dangling-symlink",
            link_target="/missing",
            device=None,
            inode=None,
            size=None,
            sha256=None,
        )
        if fault == "dangling-with-native":
            leaf["device"] = 1
        elif fault == "dangling-no-link":
            leaf["link_target"] = None
        else:
            leaf["sha256"] = SHA
    elif fault == "file-link-empty":
        leaf["link_target"] = ""
    elif fault == "entry-extra-field":
        leaf["extra"] = None
    elif fault == "nonstring-key":
        value = {**data, 3: "wrong"}
    else:
        assert fault == "cycle"
        data["cycle"] = data
    with pytest.raises(resource_record.ResourceRecordError) as caught:
        resource_record.restore_named(value)
    assert caught.value.code == "INVALID_PROJECT" and caught.value.exit_code == 3
    assert "baseline create" in caught.value.remediation


def test_real_capture_restores_after_all_historical_subjects_disappear(tmp_path: Path) -> None:
    from bookscan import resource_record

    font = tmp_path / "fonts"
    font.mkdir()
    (font / "font").write_bytes(b"abc")
    (font / "alias").symlink_to("font")
    (font / "absent-link").symlink_to("gone")
    config = tmp_path / "config"
    config.write_bytes(b"abc")
    binding = ResourceBinding.capture(
        [config],
        optional_files=[tmp_path / "missing"],
        directories=[font],
        optional_directories=[tmp_path / "optional"],
        environment={"PRIVATE": "not serialized"},
    )
    value = records.decode(json.dumps(binding.record()).encode())
    config.unlink()
    for child in font.iterdir():
        child.unlink()
    font.rmdir()
    result = resource_record.restore_named(value)
    assert result.files[0].sha256 == SHA
    assert result.files[1].resolved is None and result.files[1].sha256 is None
    tree = result.directories[0].entries
    assert tree is not None and tree[0].members == ("absent-link", "alias", "font")
    assert tree[1].kind == "dangling-symlink" and tree[1].device is None
    assert tree[2].link_target == "font" and tree[2].sha256 == SHA
    assert result.directories[1].entries is None
    assert "PRIVATE" not in json.dumps(value)


def test_reader_does_not_open_paths_launch_or_return_unchecked_scope_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import resource_record

    value = literal()
    value["fontconfig_scope_guard"] = {"unchecked": "not native-use evidence"}

    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Historical I/O or native launch is forbidden")

    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(Path, "stat", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    result = resource_record.restore_named(value)
    assert result.files[0].sha256 == SHA and not hasattr(result, "fontconfig_scope_guard")


@pytest.mark.parametrize("bad_predecessor", [False, True])
def test_restart_checks_hash_valid_named_inventory_predecessors(
    tmp_path: Path, bad_predecessor: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import ownership, project_header, resource_record

    path = tmp_path / "Saved project"
    path.mkdir()
    with ownership.Writer.acquire(path, ownership.provision(path)) as owner:
        stores = project_header.Stores.provision(owner)
        good: dict[str, object] = {"binding": literal()}
        bad = copy.deepcopy(good)
        cast(dict[str, object], bad["binding"])["runtime_resources_verified"] = True
        previous = stores.checkpoints.commit(
            bad if bad_predecessor else good, expected=None, verify_state=lambda _: None
        ).checkpoint
        stores.checkpoints.commit(good, expected=previous, verify_state=lambda _: None)
    before = {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()}

    def verify(images: object, state: dict[str, object]) -> None:
        resource_record.restore_named(state["binding"])

    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Resume must not launch historical native tools")

    monkeypatch.setattr(subprocess, "Popen", denied)
    if bad_predecessor:
        with pytest.raises(resource_record.ResourceRecordError):
            with project_header.resume(
                path, verify_state=lambda stores, state: verify(stores.images, state)
            ):
                pytest.fail("Bad named-resource predecessor accepted")
    else:
        with project_header.resume(
            path, verify_state=lambda stores, state: verify(stores.images, state)
        ) as (_, current):
            assert current.revision == 2 and current.state == good
    assert {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()} == before


def test_logical_parent_spelling_does_not_rewrite_historical_identity() -> None:
    from bookscan import resource_record

    value = literal()
    cast(list[dict[str, object]], value["files"])[0]["path"] = "/historical/old/../config"
    result = resource_record.restore_named(value)
    assert result.files[0].path == "/historical/old/../config"
    assert result.files[0].resolved == "/resolved/config"


def test_saved_directory_cannot_claim_a_finite_walk_through_ancestor_cycle() -> None:
    from bookscan import resource_record

    value = literal()
    tree = cast(list[dict[str, object]], value["directories"])[0]
    entries = cast(list[dict[str, object]], tree["entries"])
    alias = entry("/historical/fonts/font", "directory")
    alias.update(link_target=".", members=[], resolved="/historical/fonts")
    entries[1] = alias
    with pytest.raises(resource_record.ResourceRecordError, match="[Cc]yclic"):
        resource_record.restore_named(value)
