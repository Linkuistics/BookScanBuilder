"""Saved native directory identity reaches every predecessor's semantic verifier.

These literal inventory/checkpoint constructions are not a complete import schema.
"""

import copy
import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest
from test_native_inventory_record import literal
from test_native_sample_record import PACKED

from bookscan import assets, native_blobs, native_inventory_record, ownership, project_header


@pytest.fixture
def stores(tmp_path: Path) -> Iterator[project_header.Stores]:
    project = tmp_path / "Native book project"
    project.mkdir()
    identity = ownership.provision(project)
    with ownership.Writer.acquire(project, identity) as owner:
        yield project_header.Stores.provision(owner)


def verify(stores: project_header.Stores, state: dict[str, object]) -> None:
    references = {
        ref.sha256: ref
        for ref in (
            native_blobs.Blob.from_record(value)
            for value in cast(list[object], state["native_blobs"])
        )
    }
    native_inventory_record.restore(
        state["inventory"], read_blob=lambda digest: stores.native.read(references[digest])
    )


def populate(stores: project_header.Stores) -> None:
    reference = stores.native.publish(PACKED)
    state: dict[str, object] = {"inventory": literal(), "native_blobs": [reference.record()]}
    previous = stores.checkpoints.commit(
        state, expected=None, verify_state=lambda value: verify(stores, value)
    ).checkpoint
    # Current has no samples; predecessor alone needs the packed native bytes.
    empty = literal()
    empty["resolution"].update(placements=[], maximum_ppi=None)
    empty["native_samples"] = []
    stores.checkpoints.commit(
        {"inventory": empty, "native_blobs": []},
        expected=previous,
        verify_state=lambda value: verify(stores, value),
    )


def test_native_identity_and_inventory_resume_from_header_only(
    stores: project_header.Stores, monkeypatch: pytest.MonkeyPatch
) -> None:
    populate(stores)
    project = stores.owner.path
    raw = (project / "project.json").read_bytes()
    header = project_header.Header.from_json(raw)
    assert header.native == stores.native.identity
    info = (project / "native-blobs").stat()
    assert header.native == assets.DirectoryIdentity(info.st_dev, info.st_ino)
    assert header.record()["native_blobs"] == {"device": info.st_dev, "inode": info.st_ino}
    stores.owner.close()

    def denied(*args: object, **kwargs: object) -> None:
        raise PermissionError("historical I/O denied")

    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    with pytest.raises(PermissionError):
        Path("lost-original.pdf").open()
    with pytest.raises(PermissionError):
        subprocess.Popen(["forbidden-native-tool"])
    seen: list[int] = []

    def checked(loaded: project_header.Stores, state: dict[str, object]) -> None:
        verify(loaded, state)
        seen.append(len(cast(list[object], state["native_blobs"])))
        assert loaded.native.owner is loaded.images.owner is loaded.owner
        with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
            ownership.Writer.acquire(project, header.lock)

    with project_header.resume(project, verify_state=checked) as (loaded, current):
        assert loaded.header == header and current.revision == 2
        assert (
            loaded.native.read(native_blobs.Blob(hashlib.sha256(PACKED).hexdigest(), 6)) == PACKED
        )
    assert seen == [0, 1]
    assert os.readlink(project / "checkpoints" / "current") == current.sha256 + ".json"


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {},
        {"device": 1, "inode": 0},
        {"device": True, "inode": 1},
        {"device": 1, "inode": "2"},
        {"device": -1, "inode": 2},
        {"device": 1, "inode": 2, "extra": 3},
    ],
)
def test_native_header_identity_is_strict_before_lock(
    stores: project_header.Stores, value: object
) -> None:
    record = stores.header.record()
    record["native_blobs"] = value
    raw = json.dumps(record).encode()
    path = stores.owner.path / "project.json"
    path.write_bytes(raw)
    before = set(stores.owner.path.iterdir())
    with pytest.raises(project_header.HeaderError) as caught:
        with project_header.resume(stores.owner.path, verify_state=verify):
            pytest.fail("Invalid native header yielded a project")
    assert (caught.value.code, caught.value.exit_code) == ("INVALID_PROJECT", 3)
    assert path.read_bytes() == raw and set(stores.owner.path.iterdir()) == before


def test_missing_native_identity_has_no_fresh_stat_fallback(stores: project_header.Stores) -> None:
    record = stores.header.record()
    record.pop("native_blobs", None)
    with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
        project_header.Header.from_json(json.dumps(record).encode())


@pytest.mark.parametrize("kind", ["copy", "missing", "symlink", "file", "fifo"])
def test_native_directory_replacement_refuses_before_semantics_and_releases_lock(
    stores: project_header.Stores, kind: str
) -> None:
    populate(stores)
    project = stores.owner.path
    path = project / "native-blobs"
    original = project / "original-native"
    path.rename(original)
    if kind == "copy":
        shutil.copytree(original, path)
    elif kind == "symlink":
        path.symlink_to(original, target_is_directory=True)
    elif kind == "file":
        path.write_bytes(b"not a directory")
    elif kind == "fifo":
        os.mkfifo(path)
    stores.owner.close()
    called = False

    def forbidden(loaded: project_header.Stores, state: dict[str, object]) -> None:
        nonlocal called
        called = True
        raise AssertionError("Replacement reached semantic verifier")

    with pytest.raises(project_header.HeaderError, match="native-blobs"):
        with project_header.resume(project, verify_state=forbidden):
            pytest.fail("Replaced directory yielded a project")
    assert not called
    with ownership.Writer.acquire(project, stores.header.lock):
        pass


def test_native_replacement_during_semantics_is_checked_after_callback(
    stores: project_header.Stores,
) -> None:
    populate(stores)
    project = stores.owner.path
    stores.owner.close()

    def replace(loaded: project_header.Stores, state: dict[str, object]) -> None:
        path = project / "native-blobs"
        if path.exists() and not (project / "old-native").exists():
            path.rename(project / "old-native")
            path.mkdir()

    with pytest.raises(project_header.HeaderError, match="native-blobs"):
        with project_header.resume(project, verify_state=replace):
            pytest.fail("Replacement survived semantic verification")
    with ownership.Writer.acquire(project, stores.header.lock):
        pass


def test_predecessor_only_native_corruption_cannot_hide_behind_empty_current(
    stores: project_header.Stores,
) -> None:
    populate(stores)
    project = stores.owner.path
    path = project / "native-blobs" / (hashlib.sha256(PACKED).hexdigest() + ".bin")
    path.write_bytes(b"broken")
    before = {p: p.read_bytes() for p in project.rglob("*") if p.is_file()}
    stores.owner.close()
    with pytest.raises(native_blobs.BlobError, match="digest"):
        with project_header.resume(project, verify_state=verify):
            pytest.fail("Bad predecessor bytes yielded a project")
    assert {p: p.read_bytes() for p in before} == before
    with ownership.Writer.acquire(project, stores.header.lock):
        pass


def test_predecessor_inventory_semantics_are_not_replaced_by_blob_digest(
    stores: project_header.Stores,
) -> None:
    reference = stores.native.publish(PACKED)
    bad = copy.deepcopy(literal())
    bad["resolution"]["maximum_ppi"] = 600.0
    # Controlled grammar-only writer creates a hash-valid semantic counterexample.
    prior = stores.checkpoints.commit(
        {"inventory": bad, "native_blobs": [reference.record()]},
        expected=None,
        verify_state=lambda state: None,
    ).checkpoint
    stores.checkpoints.commit(
        {"inventory": literal(), "native_blobs": [reference.record()]},
        expected=prior,
        verify_state=lambda state: None,
    )
    stores.owner.close()
    with pytest.raises(native_inventory_record.NativeInventoryRecordError, match="maximum"):
        with project_header.resume(stores.owner.path, verify_state=verify):
            pytest.fail("Bad predecessor meaning yielded a project")


@pytest.mark.parametrize("error", [OSError("chosen cancel"), KeyError("chosen cancel")])
def test_resume_preserves_selected_owner_error_and_releases_lock(
    stores: project_header.Stores, error: Exception
) -> None:
    populate(stores)
    stores.owner.close()

    def cancel(loaded: project_header.Stores, state: dict[str, object]) -> None:
        raise error

    with pytest.raises(type(error)) as caught:
        with project_header.resume(stores.owner.path, verify_state=cancel):
            pytest.fail("Cancellation yielded state")
    assert caught.value is error
    with ownership.Writer.acquire(stores.owner.path, stores.header.lock):
        pass


def test_occupied_native_directory_cannot_publish_bootstrap_header(tmp_path: Path) -> None:
    project = tmp_path / "occupied-native-project"
    project.mkdir()
    lock = ownership.provision(project)
    path = project / "native-blobs"
    path.mkdir()
    sentinel = path / "foreign"
    sentinel.write_bytes(b"keep this")
    with ownership.Writer.acquire(project, lock) as owner:
        with pytest.raises(project_header.HeaderError) as caught:
            project_header.Stores.provision(owner)
        assert (caught.value.code, caught.value.exit_code) == ("WRITE_FAILED", 5)
        assert sentinel.read_bytes() == b"keep this"
        assert not (project / "project.json").exists()
        owner.verify()
