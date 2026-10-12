"""Failed bootstrap must remove its own partial lock and preserve foreign entries."""

import errno
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from bookscan import ownership


@pytest.mark.parametrize("fault", ["chmod", "write", "zero-write", "late-write", "sync"])
def test_failed_provision_removes_exact_partial_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    marker = project / "foreign"
    marker.write_bytes(b"leave unchanged")
    original_write, original_chmod = os.write, os.fchmod
    writes = 0

    def chmod(fd: int, mode: int) -> None:
        if fault == "chmod":
            raise PermissionError("chosen chmod failure")
        original_chmod(fd, mode)

    def write(fd: int, data: bytes) -> int:
        nonlocal writes
        writes += 1
        if fault == "zero-write":
            return 0
        if fault == "write" or (fault == "late-write" and writes == 2):
            raise OSError("chosen write failure")
        return original_write(fd, data[:3])

    def sync(fd: int) -> None:
        raise OSError("chosen sync failure")

    monkeypatch.setattr(os, "fchmod", chmod)
    monkeypatch.setattr(os, "write", write)
    if fault == "sync":
        monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(ownership.OwnershipError) as caught:
        ownership.provision(project)
    assert caught.value.code == "INVALID_PROJECT"
    assert not (project / "writer.lock").exists()
    assert marker.read_bytes() == b"leave unchanged"
    assert not getattr(caught.value, "__notes__", [])


@pytest.mark.parametrize(
    "change", ["replace", "symlink", "hardlink", "fifo", "modify", "root", "parent"]
)
def test_failed_provision_preserves_changed_lock_or_ancestry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    project = parent / "project"
    project.mkdir()
    selected = RuntimeError("chosen bootstrap failure")
    lock = project / "writer.lock"
    moved = tmp_path / "moved"

    def sync(fd: int) -> None:
        if change == "root":
            project.rename(moved)
            project.mkdir()
            lock.write_bytes(b"foreign root")
        elif change == "parent":
            parent.rename(moved)
            parent.mkdir()
            project.mkdir()
            lock.write_bytes(b"foreign parent")
        elif change == "modify":
            lock.write_bytes(b"foreign content")
        else:
            lock.rename(project / "old-lock")
            if change == "replace":
                lock.write_bytes(b"foreign entry")
            elif change == "symlink":
                lock.symlink_to("old-lock")
            elif change == "hardlink":
                os.link(project / "old-lock", lock)
            else:
                os.mkfifo(lock)
        raise selected

    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(RuntimeError) as caught:
        ownership.provision(project)
    assert caught.value is selected
    assert lock.lstat()
    if change == "root":
        assert (moved / "writer.lock").is_file()
        assert lock.read_bytes() == b"foreign root"
    elif change == "parent":
        assert (moved / "project" / "writer.lock").is_file()
        assert lock.read_bytes() == b"foreign parent"
    elif change == "modify":
        assert lock.read_bytes() == b"foreign content"
    assert any("cleanup" in note.lower() for note in selected.__notes__)


@pytest.mark.parametrize("missing", [False, True])
def test_bootstrap_cleanup_failure_does_not_replace_selected_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: bool
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    selected = RuntimeError("chosen bootstrap error")
    unlink = os.unlink
    lock = project / "writer.lock"

    def sync(fd: int) -> None:
        if missing:
            lock.unlink()
        raise selected

    def denied(path: Any, *args: Any, **kwargs: Any) -> None:
        if str(path) == "writer.lock":
            raise PermissionError("chosen cleanup refusal")
        unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(os, "unlink", denied)
    with pytest.raises(RuntimeError) as caught:
        ownership.provision(project)
    assert caught.value is selected
    assert lock.exists() is not missing
    if missing:
        assert not getattr(selected, "__notes__", [])
    else:
        assert any("cleanup" in note.lower() for note in selected.__notes__)


def test_successful_short_write_bootstrap_retains_usable_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    write = os.write

    def short(fd: int, data: bytes) -> int:
        return write(fd, data[:3])

    monkeypatch.setattr(os, "write", short)
    identity = ownership.provision(project)
    with ownership.Writer.acquire(project, identity) as owner:
        owner.verify()
        with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
            ownership.Writer.acquire(project, identity)
    assert (project / "writer.lock").read_bytes() == identity.content
    with ownership.Writer.acquire(project, identity) as owner:
        owner.verify()


def test_failed_provision_closes_every_owned_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    opened: list[int] = []
    original = os.open

    def capture(*args: Any, **kwargs: Any) -> int:
        descriptor = original(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def sync(fd: int) -> None:
        raise RuntimeError("chosen failure")

    monkeypatch.setattr(os, "open", capture)
    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(RuntimeError, match="chosen failure"):
        ownership.provision(project)
    assert not (project / "writer.lock").exists()
    for descriptor in opened:
        with pytest.raises(OSError) as closed:
            os.fstat(descriptor)
        assert closed.value.errno == errno.EBADF


def test_failed_provision_keeps_integer_nanosecond_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    lock = project / "writer.lock"
    write = os.write
    selected = RuntimeError("chosen failure after timestamp change")

    def fixed_time(fd: int, data: bytes) -> int:
        count = write(fd, data)
        os.utime(fd, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))
        return count

    def sync(fd: int) -> None:
        before = os.fstat(fd)
        os.utime(fd, ns=(before.st_atime_ns, before.st_mtime_ns + 1))
        after = os.fstat(fd)
        assert before.st_mtime == after.st_mtime and before.st_mtime_ns != after.st_mtime_ns
        raise selected

    monkeypatch.setattr(os, "write", fixed_time)
    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(RuntimeError) as caught:
        ownership.provision(project)
    assert caught.value is selected and lock.is_file()
    assert any("cleanup" in note.lower() for note in selected.__notes__)


def test_failed_provision_can_clean_after_read_only_atime_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    selected = RuntimeError("chosen failure after read")

    def sync(fd: int) -> None:
        assert os.pread(fd, 1, 0) == b"B"
        raise selected

    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(RuntimeError) as caught:
        ownership.provision(project)
    assert caught.value is selected and not (project / "writer.lock").exists()


def test_unavailable_created_identity_is_retained_with_explanation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    original_open, original_stat = os.open, os.fstat
    lock_descriptor = -1

    def capture(path: Any, *args: Any, **kwargs: Any) -> int:
        nonlocal lock_descriptor
        fd = original_open(path, *args, **kwargs)
        if path == "writer.lock":
            lock_descriptor = fd
        return fd

    def unavailable(fd: int) -> os.stat_result:
        if fd == lock_descriptor:
            raise OSError("chosen creation identity failure")
        return original_stat(fd)

    monkeypatch.setattr(os, "open", capture)
    monkeypatch.setattr(os, "fstat", unavailable)
    with pytest.raises(ownership.OwnershipError) as caught:
        ownership.provision(project)
    assert caught.value.code == "INVALID_PROJECT" and (project / "writer.lock").is_file()
    assert any("identity unavailable" in note for note in caught.value.__notes__)
    with pytest.raises(OSError) as closed:
        original_stat(lock_descriptor)
    assert closed.value.errno == errno.EBADF


def test_close_failures_keep_selected_failure_and_attempt_both_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    original_close = os.close
    closed: list[int] = []
    selected = RuntimeError("chosen bootstrap failure")

    def close(fd: int) -> None:
        closed.append(fd)
        original_close(fd)
        raise OSError("chosen descriptor cleanup failure")

    def sync(fd: int) -> None:
        raise selected

    monkeypatch.setattr(os, "close", close)
    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(RuntimeError) as caught:
        ownership.provision(project)
    assert caught.value is selected and len(closed) == 2
    assert not (project / "writer.lock").exists()
    assert len([note for note in selected.__notes__ if "descriptor cleanup" in note]) == 2


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit, RuntimeError])
def test_failure_before_lock_content_has_known_creation_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_type: type[BaseException]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    selected = error_type("chosen token generation failure")

    def token() -> Any:
        raise selected

    monkeypatch.setattr(ownership.uuid, "uuid4", token)
    with pytest.raises(error_type) as caught:
        ownership.provision(project)
    assert caught.value is selected and not (project / "writer.lock").exists()


@pytest.mark.parametrize("field", ["st_mtime_ns", "st_ctime_ns"])
def test_cleanup_preserves_subfloat_metadata_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    original_stat = os.stat
    selected = RuntimeError("chosen failure with changed identity observation")
    failing = False

    def sync(fd: int) -> None:
        nonlocal failing
        failing = True
        raise selected

    def changed(path: Any, *args: Any, **kwargs: Any) -> os.stat_result:
        entry = original_stat(path, *args, **kwargs)
        if failing and path == "writer.lock":
            fields = {name: getattr(entry, name) for name in dir(entry) if name.startswith("st_")}
            fields[field] += 1
            return cast(os.stat_result, SimpleNamespace(**fields))
        return entry

    monkeypatch.setattr(os, "stat", changed)
    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(RuntimeError) as caught:
        ownership.provision(project)
    assert caught.value is selected and (project / "writer.lock").is_file()
    assert any("cleanup" in note.lower() for note in selected.__notes__)
