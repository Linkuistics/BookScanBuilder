"""Real store-creation failures clean only a captured unchanged empty directory."""

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from bookscan import (
    assets,
    checkpoints,
    native_blobs,
    ownership,
    packet_descriptors,
    project_header,
)


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    project = tmp_path / "Store project"
    project.mkdir()
    identity = ownership.provision(project)
    with ownership.Writer.acquire(project, identity) as writer:
        yield writer


def store_class(
    name: str,
) -> (
    type[assets.Assets]
    | type[checkpoints.Checkpoints]
    | type[native_blobs.Blobs]
    | type[packet_descriptors.Descriptors]
):
    return {
        "assets": assets.Assets,
        "checkpoints": checkpoints.Checkpoints,
        "native-blobs": native_blobs.Blobs,
        "packets": packet_descriptors.Descriptors,
    }[name]


@pytest.mark.parametrize("name", ["assets", "checkpoints", "native-blobs", "packets"])
@pytest.mark.parametrize(
    "change",
    [
        "none",
        "read",
        "missing",
        "mode",
        "mtime",
        "populated-then-emptied",
        "nonempty",
        "replace",
        "symlink",
        "header",
        "root",
        "parent",
        "unlink-denied",
    ],
)
def test_individual_provision_failure_respects_captured_ownership(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, name: str, change: str
) -> None:
    cls = store_class(name)
    selected = RuntimeError("selected store creation failure")
    path = owner.path / name
    original_root = owner.path if change != "parent" else owner.path.parent
    moved_root = original_root.with_name(original_root.name + "-moved")
    original_rmdir = os.rmdir

    def denied(
        target: str | bytes | os.PathLike[str] | os.PathLike[bytes], *, dir_fd: int | None = None
    ) -> None:
        if target == name:
            raise PermissionError("store cleanup denied")
        original_rmdir(target, dir_fd=dir_fd)

    @contextmanager
    def fail_after_creation(self: object, *, writing: bool = False) -> Iterator[int]:
        assert path.is_dir()
        before = path.stat()
        if change == "read":
            list(path.iterdir())
        elif change == "missing":
            path.rmdir()
        elif change == "mode":
            path.chmod(0o750)
        elif change == "mtime":
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000))
        elif change in {"nonempty", "populated-then-emptied"}:
            child = path / "foreign"
            child.write_bytes(b"foreign contents")
            if change == "populated-then-emptied":
                child.unlink()
        elif change in {"replace", "symlink"}:
            path.rename(owner.path / "moved-store")
            if change == "replace":
                path.mkdir()
            else:
                path.symlink_to(owner.path / "moved-store", target_is_directory=True)
        elif change == "header":
            (owner.path / "project.json").write_bytes(b"foreign header")
        elif change in {"root", "parent"}:
            original_root.rename(moved_root)
            original_root.mkdir()
        elif change == "unlink-denied":
            monkeypatch.setattr(os, "rmdir", denied)
        raise selected
        yield -1

    monkeypatch.setattr(cls, "_directory", fail_after_creation)
    try:
        with pytest.raises(RuntimeError) as caught:
            cls.provision(owner)
        assert caught.value is selected
        if change in {"none", "read", "missing"}:
            assert not path.exists()
        elif change in {"root", "parent"}:
            retained = moved_root if change == "root" else moved_root / owner.path.name
            assert (retained / name).is_dir()
            assert list(original_root.iterdir()) == []
        else:
            assert path.is_dir()
            if change == "nonempty":
                assert (path / "foreign").read_bytes() == b"foreign contents"
            if change == "symlink":
                assert path.is_symlink() and (owner.path / "moved-store").is_dir()
            if change == "header":
                assert (owner.path / "project.json").read_bytes() == b"foreign header"
        if change not in {"none", "read", "missing"}:
            assert any("retained" in note.lower() for note in getattr(selected, "__notes__", []))
    finally:
        if change in {"root", "parent"} and moved_root.exists():
            original_root.rmdir()
            moved_root.rename(original_root)
    owner.verify()
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)


@pytest.mark.parametrize("name", ["assets", "checkpoints", "native-blobs", "packets"])
def test_complete_provision_cleans_store_that_failed_before_return(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    selected = RuntimeError("store failure before return")

    @contextmanager
    def failed(self: object, *, writing: bool = False) -> Iterator[int]:
        assert (owner.path / name).is_dir()
        raise selected
        yield -1

    monkeypatch.setattr(store_class(name), "_directory", failed)
    with pytest.raises(RuntimeError) as caught:
        project_header.Stores.provision(owner)
    assert caught.value is selected
    assert {p.name for p in owner.path.iterdir()} == {"writer.lock"}
    owner.verify()


@pytest.mark.parametrize("name", ["assets", "checkpoints", "native-blobs", "packets"])
def test_store_capture_failure_retains_unknown_directory_and_selected_io_error(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    path = owner.path / name
    selected = PermissionError("creation metadata denied")
    original_stat = os.stat
    original_lstat = Path.lstat

    def denied_stat(
        target: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        if target == name and dir_fd is not None:
            raise selected
        return original_stat(target, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    def denied_lstat(target: Path) -> os.stat_result:
        if target == path:
            raise selected
        return original_lstat(target)

    with monkeypatch.context() as patch:
        patch.setattr(os, "stat", denied_stat)
        patch.setattr(Path, "lstat", denied_lstat)
        with pytest.raises(
            (
                assets.AssetError,
                checkpoints.CheckpointError,
                native_blobs.BlobError,
                packet_descriptors.DescriptorError,
            )
        ) as caught:
            store_class(name).provision(owner)
    assert caught.value.__cause__ is selected
    assert (caught.value.code, caught.value.exit_code) == ("WRITE_FAILED", 5)
    assert path.is_dir()
    assert any("not captured" in note for note in getattr(selected, "__notes__", []))
    owner.verify()


@pytest.mark.parametrize("name", ["assets", "checkpoints", "native-blobs", "packets"])
def test_failed_store_descriptor_close_keeps_selected_exception(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    selected = KeyboardInterrupt("selected store interruption")
    original_close = os.close
    closed: list[int] = []

    @contextmanager
    def failed(self: object, *, writing: bool = False) -> Iterator[int]:
        raise selected
        yield -1

    def denied(descriptor: int) -> None:
        original_close(descriptor)
        if sys.exception() is selected:
            closed.append(descriptor)
            raise OSError("descriptor close denied after release")

    monkeypatch.setattr(store_class(name), "_directory", failed)
    with monkeypatch.context() as patch:
        patch.setattr(os, "close", denied)
        with pytest.raises(KeyboardInterrupt) as caught:
            store_class(name).provision(owner)
    assert caught.value is selected
    assert not (owner.path / name).exists()
    assert len(closed) == 2 and len(set(closed)) == 2
    assert any("descriptor" in note.lower() for note in getattr(selected, "__notes__", []))
    owner.verify()


@pytest.mark.parametrize("name", ["assets", "checkpoints", "native-blobs", "packets"])
def test_occupied_store_remains_byte_exact(owner: ownership.Writer, name: str) -> None:
    path = owner.path / name
    path.mkdir()
    (path / "foreign").write_bytes(b"occupied store contents")
    before = path.stat()
    with pytest.raises(
        (
            assets.AssetError,
            checkpoints.CheckpointError,
            native_blobs.BlobError,
            packet_descriptors.DescriptorError,
        )
    ) as caught:
        store_class(name).provision(owner)
    assert (caught.value.code, caught.value.exit_code) == ("WRITE_FAILED", 5)
    assert (path / "foreign").read_bytes() == b"occupied store contents"
    after = path.stat()
    assert (after.st_ino, after.st_mode, after.st_mtime_ns, after.st_ctime_ns) == (
        before.st_ino,
        before.st_mode,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    owner.verify()
