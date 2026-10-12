"""Close-only store initialization failures retain no unchanged owned empty store."""

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from bookscan import (
    assets,
    checkpoints,
    native_blobs,
    ownership,
    packet_descriptors,
    project_header,
    project_reservation,
)

STORES = ["assets", "checkpoints", "native-blobs", "packets"]


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    path = tmp_path / "Store close project"
    path.mkdir()
    with ownership.Writer.acquire(path, ownership.provision(path)) as writer:
        yield writer


def provision(owner: ownership.Writer, name: str) -> None:
    {
        "assets": assets.Assets,
        "checkpoints": checkpoints.Checkpoints,
        "native-blobs": native_blobs.Blobs,
        "packets": packet_descriptors.Descriptors,
    }[name].provision(owner)


def close_fault(
    patch: pytest.MonkeyPatch,
    owner: ownership.Writer,
    name: str,
    stage: str,
    mutate: Callable[[], None] = lambda: None,
    after_release: Callable[[], None] = lambda: None,
) -> tuple[OSError, list[int]]:
    """Release real provisioning descriptors, then report an injected close error.

    Observe the shared store boundary so complete bootstrap's other directory
    descriptors cannot accidentally become the fault subject.
    """
    original_open, original_close = os.open, os.close
    original_store = project_reservation.provision_store
    active = False
    captured: dict[str, int] = {}
    failures: list[int] = []
    selected = OSError("selected store close error after release")

    @contextmanager
    def observed(writer: ownership.Writer, store: str) -> Iterator[os.stat_result]:
        nonlocal active
        active = store == name
        try:
            with original_store(writer, store) as info:
                yield info
        finally:
            active = False

    def opened(target: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        descriptor = original_open(target, flags, mode, dir_fd=dir_fd)
        if active:
            if target == owner.path.parent:
                captured.setdefault("parent", descriptor)
            elif target == owner.path.name and dir_fd == captured.get("parent"):
                captured.setdefault("root", descriptor)
        return descriptor

    def closed(descriptor: int) -> None:
        if active and not failures and descriptor == captured.get(stage):
            assert (owner.path / name).is_dir()
            mutate()
            original_close(descriptor)
            failures.append(descriptor)
            after_release()
            raise selected
        original_close(descriptor)

    patch.setattr(project_reservation, "provision_store", observed)
    patch.setattr(os, "open", opened)
    patch.setattr(os, "close", closed)
    return selected, failures


@pytest.mark.parametrize("name", STORES)
@pytest.mark.parametrize("stage", ["root", "parent"])
@pytest.mark.parametrize("change", ["none", "read", "missing"])
def test_store_close_failure_removes_only_unchanged_empty_store(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, name: str, stage: str, change: str
) -> None:
    path = owner.path / name

    def mutate() -> None:
        if change == "read":
            list(path.iterdir())
        elif change == "missing":
            path.rmdir()

    with monkeypatch.context() as patch:
        selected, failures = close_fault(patch, owner, name, stage, mutate)
        with pytest.raises(project_header.HeaderError) as caught:
            provision(owner, name)
    assert failures and caught.value.__cause__ is selected
    assert (caught.value.code, caught.value.exit_code) == ("WRITE_FAILED", 5)
    assert {path.name for path in owner.path.iterdir()} == {"writer.lock"}
    owner.verify()
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)


@pytest.mark.parametrize("name", STORES)
@pytest.mark.parametrize("stage", ["root", "parent"])
@pytest.mark.parametrize(
    "change", ["mode", "mtime", "emptied", "foreign", "replace", "symlink", "header"]
)
def test_store_close_failure_preserves_changed_or_unowned_entries(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, name: str, stage: str, change: str
) -> None:
    path = owner.path / name
    retained: list[os.stat_result] = []

    def mutate() -> None:
        if change == "mode":
            path.chmod(0o750)
        elif change == "mtime":
            before = path.stat()
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1))
        elif change in {"emptied", "foreign"}:
            child = path / "foreign"
            child.write_bytes(b"unowned contents")
            if change == "emptied":
                child.unlink()
        elif change in {"replace", "symlink"}:
            path.rename(owner.path / "original-store")
            if change == "replace":
                path.mkdir()
            else:
                path.symlink_to("original-store", target_is_directory=True)
        elif change == "header":
            (owner.path / "project.json").write_bytes(b"occupied header")
        retained.append(path.lstat())

    with monkeypatch.context() as patch:
        selected, failures = close_fault(patch, owner, name, stage, mutate)
        with pytest.raises(project_header.HeaderError) as caught:
            provision(owner, name)
    assert failures and caught.value.__cause__ is selected
    before, after = retained[0], path.lstat()
    assert (after.st_dev, after.st_ino, after.st_mode, after.st_mtime_ns, after.st_ctime_ns) == (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    if change == "foreign":
        assert (path / "foreign").read_bytes() == b"unowned contents"
    if change == "header":
        assert (owner.path / "project.json").read_bytes() == b"occupied header"
    assert any("retained" in note.lower() for note in getattr(caught.value, "__notes__", []))
    owner.verify()


@pytest.mark.parametrize("name", STORES)
@pytest.mark.parametrize("stage", ["root", "parent"])
@pytest.mark.parametrize("change", ["root", "parent", "parent-same-root"])
def test_store_close_failure_preserves_replaced_ancestry(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, name: str, stage: str, change: str
) -> None:
    original = owner.path if change == "root" else owner.path.parent
    moved = original.with_name(original.name + "-moved")

    def mutate() -> None:
        original.rename(moved)
        original.mkdir()
        if change == "parent-same-root":
            (moved / owner.path.name).rename(owner.path)

    try:
        with monkeypatch.context() as patch:
            selected, failures = close_fault(patch, owner, name, stage, mutate)
            with pytest.raises(project_header.HeaderError) as caught:
                provision(owner, name)
        assert failures and caught.value.__cause__ is selected
        retained = (
            owner.path
            if change == "parent-same-root"
            else moved
            if change == "root"
            else moved / owner.path.name
        )
        assert (retained / name).is_dir()
        assert list(original.iterdir()) == ([owner.path] if change == "parent-same-root" else [])
    finally:
        if moved.exists():
            if change == "parent-same-root":
                owner.path.rename(moved / owner.path.name)
            original.rmdir()
            moved.rename(original)
    owner.verify()


@pytest.mark.parametrize("name", STORES)
@pytest.mark.parametrize("stage", ["root", "parent"])
def test_store_close_failure_cleans_earlier_stores_in_complete_bootstrap(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, name: str, stage: str
) -> None:
    with monkeypatch.context() as patch:
        selected, failures = close_fault(patch, owner, name, stage)
        with pytest.raises(project_header.HeaderError) as caught:
            project_header.Stores.provision(owner)
    assert failures and caught.value.__cause__ is selected
    assert {path.name for path in owner.path.iterdir()} == {"writer.lock"}
    owner.verify()


@pytest.mark.parametrize("name", STORES)
@pytest.mark.parametrize("stage", ["root", "parent"])
def test_store_close_failure_never_retries_reused_descriptor(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, name: str, stage: str
) -> None:
    sentinel = owner.path.parent / "unrelated-live-file"
    sentinel.write_bytes(b"unrelated live file")
    original_open, original_close = os.open, os.close
    held: list[int] = []

    def after_release() -> None:
        held.append(original_open(sentinel, os.O_RDONLY | os.O_CLOEXEC))

    try:
        with monkeypatch.context() as patch:
            selected, failures = close_fault(patch, owner, name, stage, after_release=after_release)
            with pytest.raises(project_header.HeaderError) as caught:
                provision(owner, name)
        assert failures == held and caught.value.__cause__ is selected
        assert os.read(held[0], 100) == b"unrelated live file"
        assert {path.name for path in owner.path.iterdir()} == {"writer.lock"}
    finally:
        for descriptor in held:
            original_close(descriptor)
    owner.verify()


@pytest.mark.parametrize("name", STORES)
@pytest.mark.parametrize("stage", ["root", "parent"])
@pytest.mark.parametrize("failure", ["reopen", "rmdir", "close"])
def test_store_rollback_failure_preserves_first_close_error(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, name: str, stage: str, failure: str
) -> None:
    original_open, original_rmdir, original_close = os.open, os.rmdir, os.close

    def denied_open(
        target: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        if target == owner.path.parent:
            raise PermissionError("store rollback reopen denied")
        return original_open(target, flags, mode, dir_fd=dir_fd)

    def denied_rmdir(target: Any, *, dir_fd: int | None = None) -> None:
        if target == name:
            raise PermissionError("store rollback removal denied")
        original_rmdir(target, dir_fd=dir_fd)

    def denied_close(descriptor: int) -> None:
        original_close(descriptor)
        raise OSError("additional descriptor close failure after release")

    with monkeypatch.context() as patch:

        def mutate() -> None:
            if failure == "reopen":
                patch.setattr(os, "open", denied_open)
            elif failure == "rmdir":
                patch.setattr(os, "rmdir", denied_rmdir)
            else:
                patch.setattr(os, "close", denied_close)

        selected, failures = close_fault(patch, owner, name, stage, mutate)
        with pytest.raises(project_header.HeaderError) as caught:
            provision(owner, name)
    assert failures and caught.value.__cause__ is selected
    assert (owner.path / name).exists() == (failure != "close")
    assert any("cleanup" in note.lower() for note in getattr(caught.value, "__notes__", []))
    owner.verify()


@pytest.mark.parametrize("stage", ["root", "parent"])
def test_store_close_failure_preserves_actual_committed_checkpoint(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    retained: dict[str, bytes] = {}
    current: list[str] = []

    def mutate() -> None:
        entry = (owner.path / "checkpoints").stat()
        history = checkpoints.Checkpoints(
            owner, assets.DirectoryIdentity(entry.st_dev, entry.st_ino)
        )
        result = history.commit({"retained": True}, expected=None, verify_state=lambda state: None)
        current.append(result.checkpoint.sha256 + ".json")
        retained.update({p.name: p.read_bytes() for p in (owner.path / "checkpoints").iterdir()})

    with monkeypatch.context() as patch:
        selected, failures = close_fault(patch, owner, "checkpoints", stage, mutate)
        with pytest.raises(project_header.HeaderError) as caught:
            provision(owner, "checkpoints")
    assert failures and caught.value.__cause__ is selected
    assert (owner.path / "checkpoints/current").readlink().name == current[0]
    assert {p.name: p.read_bytes() for p in (owner.path / "checkpoints").iterdir()} == retained
    owner.verify()
