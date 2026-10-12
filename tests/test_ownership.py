"""Real project ownership; dropping flock/identity checks must break these contracts."""

from __future__ import annotations

import errno
import fcntl
import os
from dataclasses import replace
from pathlib import Path

import pytest

from bookscan import ownership


def prepared(path: Path) -> ownership.LockIdentity:
    path.mkdir()
    return ownership.provision(path)


def test_second_open_in_same_process_is_busy_and_release_keeps_inode(tmp_path: Path) -> None:
    project = tmp_path / "Book project"
    identity = prepared(project)
    before = (project / "writer.lock").stat()
    with ownership.Writer.acquire(project, identity) as owner:
        owner.verify()
        with pytest.raises(ownership.OwnershipError) as error:
            ownership.Writer.acquire(project, identity)
        assert (error.value.code, error.value.exit_code) == ("PROJECT_BUSY", 4)
    with ownership.Writer.acquire(project, identity) as resumed:
        resumed.verify()
    after = (project / "writer.lock").stat()
    assert (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)


def test_closing_another_descriptor_does_not_release_ownership(tmp_path: Path) -> None:
    project = tmp_path / "project"
    identity = prepared(project)
    with ownership.Writer.acquire(project, identity) as owner:
        descriptor = os.open(project / "writer.lock", os.O_RDONLY)
        os.close(descriptor)
        owner.verify()
        with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
            ownership.Writer.acquire(project, identity)


def test_symlinked_parent_and_project_reach_same_ownership(tmp_path: Path) -> None:
    parent = tmp_path / "real"
    parent.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(parent, target_is_directory=True)
    project = parent / "project"
    identity = prepared(project)
    with ownership.Writer.acquire(alias / "project", identity) as owner:
        assert owner.path == project.resolve()
        with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
            ownership.Writer.acquire(project, identity)


@pytest.mark.parametrize("replacement", ["empty", "exact", "symlink", "hardlink", "fifo"])
def test_replaced_lock_fails_under_owner_and_on_reacquisition(
    tmp_path: Path, replacement: str
) -> None:
    project = tmp_path / "project"
    identity = prepared(project)
    lock = project / "writer.lock"
    original = lock.read_bytes()
    with ownership.Writer.acquire(project, identity) as owner:
        lock.rename(project / "old-lock")
        if replacement in {"empty", "exact"}:
            lock.write_bytes(b"" if replacement == "empty" else original)
        elif replacement == "symlink":
            lock.symlink_to(project / "old-lock")
        elif replacement == "hardlink":
            os.link(project / "old-lock", lock)
        else:
            os.mkfifo(lock)
        with pytest.raises(ownership.OwnershipError, match="INVALID_PROJECT"):
            owner.verify()
        with pytest.raises(ownership.OwnershipError, match="INVALID_PROJECT"):
            ownership.Writer.acquire(project, identity)
    assert lock.lstat().st_ino != identity.lock_inode or replacement == "hardlink"


def test_root_replacement_cannot_redirect_owned_operations(tmp_path: Path) -> None:
    project = tmp_path / "project"
    identity = prepared(project)
    with ownership.Writer.acquire(project, identity) as owner:
        project.rename(tmp_path / "old-project")
        project.mkdir()
        with pytest.raises(ownership.OwnershipError, match="INVALID_PROJECT"):
            owner.verify()
        with pytest.raises(ownership.OwnershipError, match="INVALID_PROJECT"):
            ownership.Writer.acquire(project, identity)


@pytest.mark.parametrize("change", [b"", b"foreign", b"x" * 4096])
def test_lock_content_change_rejected_without_replacing_inode(
    tmp_path: Path, change: bytes
) -> None:
    project = tmp_path / "project"
    identity = prepared(project)
    with ownership.Writer.acquire(project, identity) as owner:
        (project / "writer.lock").write_bytes(change)
        with pytest.raises(ownership.OwnershipError, match="INVALID_PROJECT"):
            owner.verify()


@pytest.mark.parametrize("field", ["project_inode", "lock_inode", "project_device", "lock_device"])
def test_foreign_saved_identity_cannot_acquire(tmp_path: Path, field: str) -> None:
    project = tmp_path / "project"
    identity = prepared(project)
    wrong = replace(identity, **{field: getattr(identity, field) + 1})
    with pytest.raises(ownership.OwnershipError, match="INVALID_PROJECT"):
        ownership.Writer.acquire(project, wrong)


def test_missing_lock_never_created_by_read(tmp_path: Path) -> None:
    project = tmp_path / "project"
    identity = prepared(project)
    (project / "writer.lock").unlink()
    with pytest.raises(ownership.OwnershipError, match="INVALID_PROJECT"):
        ownership.Writer.acquire(project, identity)
    assert list(project.iterdir()) == []


def test_provision_never_replaces_occupied_lock(tmp_path: Path) -> None:
    project = tmp_path / "project"
    identity = prepared(project)
    original = (project / "writer.lock").read_bytes()
    with pytest.raises(ownership.OwnershipError) as error:
        ownership.provision(project)
    assert (error.value.code, error.value.exit_code) == ("PROJECT_EXISTS", 4)
    assert (project / "writer.lock").read_bytes() == original
    with ownership.Writer.acquire(project, identity) as owner:
        owner.verify()


def test_closed_owner_cannot_be_used_and_double_close_is_safe(tmp_path: Path) -> None:
    project = tmp_path / "project"
    identity = prepared(project)
    owner = ownership.Writer.acquire(project, identity)
    owner.close()
    owner.close()
    with pytest.raises(ownership.OwnershipError, match="INVALID_PROJECT"):
        owner.verify()


def test_failed_context_entry_releases_its_already_acquired_lock(tmp_path: Path) -> None:
    project = tmp_path / "project"
    identity = prepared(project)
    owner = ownership.Writer.acquire(project, identity)
    lock = project / "writer.lock"
    lock.rename(project / "old-lock")
    lock.write_bytes(b"wrong")
    try:
        with pytest.raises(ownership.OwnershipError, match="INVALID_PROJECT"):
            with owner:
                raise AssertionError("Context with replaced lock must not start.")
        lock.unlink()
        (project / "old-lock").rename(lock)
        with ownership.Writer.acquire(project, identity) as replacement:
            replacement.verify()
    finally:
        owner.close()


@pytest.mark.parametrize(
    ("number", "code", "exit_code"),
    [(errno.ENOTSUP, "DEPENDENCY_UNAVAILABLE", 5), (errno.EACCES, "PROJECT_BUSY", 4)],
)
def test_failed_kernel_acquisition_closes_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, number: int, code: str, exit_code: int
) -> None:
    project = tmp_path / "project"
    identity = prepared(project)
    original = fcntl.flock
    descriptors: list[int] = []

    def unavailable(fd: int, flags: int) -> None:
        descriptors.append(fd)
        raise OSError(number, "private unavailable-lock fault")

    monkeypatch.setattr(fcntl, "flock", unavailable)
    with pytest.raises(ownership.OwnershipError) as error:
        ownership.Writer.acquire(project, identity)
    assert (error.value.code, error.value.exit_code) == (code, exit_code)
    assert len(descriptors) == 1
    with pytest.raises(OSError) as closed:
        os.fstat(descriptors[0])
    assert closed.value.errno == errno.EBADF
    monkeypatch.setattr(fcntl, "flock", original)
    with ownership.Writer.acquire(project, identity) as owner:
        owner.verify()


def test_writer_context_close_failure_keeps_selected_error_and_closes_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    identity = prepared(project)
    owner = ownership.Writer.acquire(project, identity)
    original = os.close
    failed = False
    selected = RuntimeError("chosen operation failure")
    descriptors: list[int] = []

    def denied(fd: int) -> None:
        nonlocal failed
        descriptors.append(fd)
        original(fd)
        if not failed:
            failed = True
            raise OSError("chosen close failure after closing")

    with monkeypatch.context() as patch:
        patch.setattr(os, "close", denied)
        with pytest.raises(RuntimeError) as caught:
            with owner:
                raise selected
    assert caught.value is selected and len(descriptors) == 2
    assert any("cleanup" in note.lower() for note in selected.__notes__)
    for descriptor in descriptors:
        with pytest.raises(OSError) as closed:
            os.fstat(descriptor)
        assert closed.value.errno == errno.EBADF
    with ownership.Writer.acquire(project, identity) as resumed:
        resumed.verify()
