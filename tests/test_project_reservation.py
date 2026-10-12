"""Reservation failures must never replace or sweep unrelated project content."""

import os
from pathlib import Path

import pytest

from bookscan import project_header
from bookscan.project_reservation import reserve


def _stamp(info: os.stat_result) -> tuple[int, ...]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def test_remove_owned_directory_keeps_unknown_names_and_is_idempotent(tmp_path: Path) -> None:
    with reserve(tmp_path / "project") as reservation:
        path = reservation.path / "assets"
        path.mkdir()
        expected = _stamp(path.lstat())
        (reservation.path / "unknown").write_bytes(b"untouched")
        (reservation.path / "unknown-directory").mkdir()
        (reservation.path / "unknown-link").symlink_to(tmp_path / "absent")
        reservation.remove_directory("assets", matches=lambda entry: _stamp(entry) == expected)
        reservation.remove_directory("assets", matches=lambda entry: _stamp(entry) == expected)
        assert not path.exists()
        assert (reservation.path / "unknown").read_bytes() == b"untouched"
        assert (reservation.path / "unknown-directory").is_dir()
        assert (reservation.path / "unknown-link").is_symlink()


@pytest.mark.parametrize("kind", ["file", "directory", "dangling"])
def test_remove_directory_preserves_every_unknown_child(tmp_path: Path, kind: str) -> None:
    with reserve(tmp_path / "project") as reservation:
        path = reservation.path / "assets"
        path.mkdir()
        unknown = path / "unknown"
        if kind == "file":
            unknown.write_bytes(b"foreign")
        elif kind == "directory":
            unknown.mkdir()
        else:
            unknown.symlink_to(tmp_path / "missing")
        before = _stamp(unknown.lstat())
        with pytest.raises(project_header.HeaderError) as error:
            reservation.remove_directory("assets", matches=lambda entry: True)
        assert (error.value.code, error.value.exit_code) == ("WRITE_FAILED", 5)
        assert _stamp(unknown.lstat()) == before and path.is_dir()


@pytest.mark.parametrize("kind", ["symlink", "dangling", "file", "fifo"])
def test_remove_directory_refuses_links_and_other_types(tmp_path: Path, kind: str) -> None:
    with reserve(tmp_path / "project") as reservation:
        foreign = tmp_path / "foreign"
        foreign.mkdir()
        (foreign / "keep").write_bytes(b"foreign")
        path = reservation.path / "assets"
        if kind == "file":
            path.write_bytes(b"foreign")
        elif kind == "fifo":
            os.mkfifo(path)
        else:
            path.symlink_to(foreign if kind == "symlink" else tmp_path / "missing")
        before = _stamp(path.lstat())
        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_directory("assets", matches=lambda entry: True)
        assert _stamp(path.lstat()) == before
        assert (foreign / "keep").read_bytes() == b"foreign"


@pytest.mark.parametrize(
    "name", ["", ".", "..", "nested/child", "../foreign", "/foreign", "bad\0name"]
)
def test_remove_directory_never_accepts_a_path(tmp_path: Path, name: str) -> None:
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    with reserve(tmp_path / "project") as reservation:
        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_directory(name, matches=lambda entry: True)
    assert foreign.is_dir()


def test_remove_directory_requires_captured_identity(tmp_path: Path) -> None:
    with reserve(tmp_path / "project") as reservation:
        path = reservation.path / "assets"
        path.mkdir()
        expected = _stamp(path.lstat())
        moved = reservation.path / "old-assets"
        path.rename(moved)
        path.mkdir()
        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_directory("assets", matches=lambda entry: _stamp(entry) == expected)
        assert path.is_dir() and moved.is_dir()


@pytest.mark.parametrize("change", ["closed", "root", "parent"])
def test_remove_directory_requires_live_unchanged_reservation(tmp_path: Path, change: str) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    reservation = reserve(parent / "project")
    path = reservation.path / "assets"
    path.mkdir()
    try:
        if change == "closed":
            reservation.close()
        elif change == "root":
            reservation.path.rename(parent / "old-project")
            path.mkdir(parents=True)
        else:
            parent.rename(tmp_path / "old-parent")
            path.mkdir(parents=True)
        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_directory("assets", matches=lambda entry: True)
        assert path.is_dir()
        if change == "root":
            assert (parent / "old-project" / "assets").is_dir()
        elif change == "parent":
            assert (tmp_path / "old-parent" / "project" / "assets").is_dir()
    finally:
        reservation.close()


@pytest.mark.parametrize("change", ["directory", "symlink", "root", "parent", "nanosecond"])
def test_remove_directory_rechecks_after_identity_predicate(tmp_path: Path, change: str) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    with reserve(parent / "project") as reservation:
        path = reservation.path / "assets"
        path.mkdir()
        os.utime(path, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))

        def changed(entry: os.stat_result) -> bool:
            if change in {"directory", "symlink"}:
                path.rename(reservation.path / "old-assets")
                if change == "directory":
                    path.mkdir()
                else:
                    path.symlink_to(reservation.path / "old-assets")
            elif change == "root":
                reservation.path.rename(parent / "old-project")
                path.mkdir(parents=True)
            elif change == "parent":
                parent.rename(tmp_path / "old-parent")
                path.mkdir(parents=True)
            else:
                os.utime(path, ns=(entry.st_atime_ns, entry.st_mtime_ns + 1))
            return True

        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_directory("assets", matches=changed)
        assert path.is_dir()
        if change in {"directory", "symlink"}:
            assert (reservation.path / "old-assets").is_dir()
        elif change == "root":
            assert (parent / "old-project" / "assets").is_dir()
        elif change == "parent":
            assert (tmp_path / "old-parent" / "project" / "assets").is_dir()


@pytest.mark.parametrize("fault", ["populated", "denied"])
def test_remove_directory_preserves_selected_failure_on_syscall_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    selected = ValueError("chosen import failure")
    real_rmdir = os.rmdir
    path = tmp_path / "project" / "assets"
    with pytest.raises(ValueError) as caught:
        with reserve(tmp_path / "project") as reservation:
            path.mkdir()
            expected = _stamp(path.lstat())

            def failed(name: str, *, dir_fd: int | None = None) -> None:
                if name == "assets":
                    assert dir_fd is not None
                    root = os.fstat(dir_fd)
                    named = reservation.path.lstat()
                    assert (root.st_dev, root.st_ino) == (named.st_dev, named.st_ino)
                    if fault == "denied":
                        raise PermissionError("constructed denial")
                    (path / "late-child").write_bytes(b"foreign")
                real_rmdir(name, dir_fd=dir_fd)

            monkeypatch.setattr(os, "rmdir", failed)
            try:
                raise selected
            except ValueError as error:
                try:
                    reservation.remove_directory(
                        "assets", matches=lambda entry: _stamp(entry) == expected
                    )
                except project_header.HeaderError as failure:
                    assert (failure.code, failure.exit_code) == ("WRITE_FAILED", 5)
                    error.add_note(str(failure))
                raise
    assert caught.value is selected
    assert path.is_dir() and any("WRITE_FAILED" in note for note in selected.__notes__)
    if fault == "populated":
        assert (path / "late-child").read_bytes() == b"foreign"


def test_remove_owned_file_keeps_unknown_names_and_is_idempotent(tmp_path: Path) -> None:
    with reserve(tmp_path / "project") as reservation:
        path = reservation.path / "source.pdf"
        path.write_bytes(b"owned")
        expected = _stamp(path.lstat())
        (reservation.path / "unknown").write_bytes(b"untouched")
        (reservation.path / "unknown-directory").mkdir()
        (reservation.path / "unknown-link").symlink_to(tmp_path / "absent")
        reservation.remove_file("source.pdf", matches=lambda entry: _stamp(entry) == expected)
        reservation.remove_file("source.pdf", matches=lambda entry: _stamp(entry) == expected)
        assert not path.exists()
        assert (reservation.path / "unknown").read_bytes() == b"untouched"
        assert (reservation.path / "unknown-directory").is_dir()
        assert (reservation.path / "unknown-link").is_symlink()


@pytest.mark.parametrize("kind", ["symlink", "dangling", "directory", "fifo", "hardlink"])
def test_remove_file_rejects_links_and_nonregular_entries(tmp_path: Path, kind: str) -> None:
    with reserve(tmp_path / "project") as reservation:
        foreign = tmp_path / "foreign"
        foreign.write_bytes(b"foreign")
        path = reservation.path / "source.pdf"
        if kind == "directory":
            path.mkdir()
        elif kind == "fifo":
            os.mkfifo(path)
        elif kind == "hardlink":
            os.link(foreign, path)
        else:
            path.symlink_to(foreign if kind == "symlink" else tmp_path / "missing")
        before = path.lstat()
        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_file("source.pdf", matches=lambda entry: True)
        assert _stamp(path.lstat()) == _stamp(before)
        assert foreign.read_bytes() == b"foreign"


@pytest.mark.parametrize(
    "name", ["", ".", "..", "nested/file", "../foreign", "/foreign", "bad\0name"]
)
def test_remove_file_never_accepts_a_path(tmp_path: Path, name: str) -> None:
    foreign = tmp_path / "foreign"
    foreign.write_bytes(b"foreign")
    with reserve(tmp_path / "project") as reservation:
        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_file(name, matches=lambda entry: True)
    assert foreign.read_bytes() == b"foreign"


@pytest.mark.parametrize("change", ["replace", "modify"])
def test_remove_file_refuses_changed_identity(tmp_path: Path, change: str) -> None:
    with reserve(tmp_path / "project") as reservation:
        path = reservation.path / "source.pdf"
        path.write_bytes(b"owned")
        expected = _stamp(path.lstat())
        if change == "replace":
            path.rename(reservation.path / "old-source.pdf")
        path.write_bytes(b"externally changed")
        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_file("source.pdf", matches=lambda entry: _stamp(entry) == expected)
        assert path.read_bytes() == b"externally changed"


@pytest.mark.parametrize("change", ["closed", "root", "parent"])
def test_remove_file_requires_live_unchanged_reservation(tmp_path: Path, change: str) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    reservation = reserve(parent / "project")
    path = reservation.path / "source.pdf"
    path.write_bytes(b"owned")
    try:
        if change == "closed":
            reservation.close()
        elif change == "root":
            reservation.path.rename(parent / "old-project")
            reservation.path.mkdir()
            path.write_bytes(b"foreign")
        else:
            parent.rename(tmp_path / "old-parent")
            path.parent.mkdir(parents=True)
            path.write_bytes(b"foreign")
        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_file("source.pdf", matches=lambda entry: True)
        assert path.read_bytes() == (b"owned" if change == "closed" else b"foreign")
    finally:
        reservation.close()


def test_remove_file_rechecks_after_identity_predicate(tmp_path: Path) -> None:
    with reserve(tmp_path / "project") as reservation:
        path = reservation.path / "source.pdf"
        path.write_bytes(b"owned")

        def changed(entry: os.stat_result) -> bool:
            path.rename(reservation.path / "old-source.pdf")
            path.write_bytes(b"foreign")
            return True

        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_file("source.pdf", matches=changed)
        assert path.read_bytes() == b"foreign"


def test_remove_file_preserves_nanosecond_identity_change(tmp_path: Path) -> None:
    with reserve(tmp_path / "project") as reservation:
        path = reservation.path / "source.pdf"
        path.write_bytes(b"owned")
        # At this timestamp one nanosecond is below tuple float-time resolution.
        os.utime(path, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))

        def changed(entry: os.stat_result) -> bool:
            os.utime(path, ns=(entry.st_atime_ns, entry.st_mtime_ns + 1))
            return True

        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_file("source.pdf", matches=changed)
        assert path.read_bytes() == b"owned"


def test_remove_file_rechecks_root_after_identity_predicate(tmp_path: Path) -> None:
    with reserve(tmp_path / "project") as reservation:
        path = reservation.path / "source.pdf"
        path.write_bytes(b"owned")
        moved = tmp_path / "old-project"

        def changed(entry: os.stat_result) -> bool:
            reservation.path.rename(moved)
            reservation.path.mkdir()
            path.write_bytes(b"foreign")
            return True

        with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
            reservation.remove_file("source.pdf", matches=changed)
        assert path.read_bytes() == b"foreign"
        assert (moved / "source.pdf").read_bytes() == b"owned"


def test_reserves_private_canonical_directory_and_normal_release_retains_it(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with reserve(alias / "Book project") as reservation:
        assert reservation.path == real.resolve() / "Book project"
        assert reservation.path.stat().st_mode & 0o777 == 0o700
        reservation.verify()
    assert (real / "Book project").is_dir()
    with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
        reservation.verify()


@pytest.mark.parametrize("kind", ["directory", "file", "symlink", "dangling"])
def test_existing_name_is_untouched_and_returns_conflict(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "project"
    if kind == "directory":
        path.mkdir()
        (path / "original").write_bytes(b"original")
    elif kind == "file":
        path.write_bytes(b"original")
    else:
        path.symlink_to(tmp_path / ("existing" if kind == "symlink" else "missing"))
        if kind == "symlink":
            (tmp_path / "existing").write_bytes(b"original")
    before = path.lstat()
    with pytest.raises(project_header.HeaderError) as error:
        reserve(path)
    assert (error.value.code, error.value.exit_code) == ("PROJECT_EXISTS", 4)
    assert path.lstat() == before


def test_missing_parent_is_not_created(tmp_path: Path) -> None:
    with pytest.raises(project_header.HeaderError) as error:
        reserve(tmp_path / "missing" / "project")
    assert (error.value.code, error.value.exit_code) == ("OUTPUT_DIRECTORY_INVALID", 4)
    assert "parent" in error.value.remediation and "existing" in error.value.remediation
    assert not (tmp_path / "missing").exists()


def test_failure_removes_only_owned_empty_reservation(tmp_path: Path) -> None:
    class Failed(Exception):
        pass

    path = tmp_path / "project"
    with pytest.raises(Failed):
        with reserve(path):
            raise Failed("operation failed")
    assert not path.exists()


def test_failure_with_unknown_content_keeps_it_and_selected_error(tmp_path: Path) -> None:
    path = tmp_path / "project"
    failure = ValueError("chosen")
    with pytest.raises(ValueError) as error:
        with reserve(path):
            (path / "unknown").write_bytes(b"do not sweep")
            raise failure
    assert error.value is failure
    assert (path / "unknown").read_bytes() == b"do not sweep"
    assert any("retained" in note.lower() for note in failure.__notes__)


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_replaced_root_is_rejected_and_neither_tree_is_deleted(tmp_path: Path, kind: str) -> None:
    path, moved, foreign = tmp_path / "project", tmp_path / "owned", tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "keep").write_bytes(b"foreign")
    failure = ValueError("chosen")
    with pytest.raises(ValueError) as error:
        with reserve(path) as reservation:
            path.rename(moved)
            if kind == "directory":
                path.mkdir()
            else:
                path.symlink_to(foreign, target_is_directory=True)
            with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
                reservation.verify()
            raise failure
    assert error.value is failure
    assert moved.is_dir() and path.lstat()
    assert (foreign / "keep").read_bytes() == b"foreign"


def test_replaced_parent_is_rejected_without_deleting_old_or_new_tree(tmp_path: Path) -> None:
    parent, moved = tmp_path / "parent", tmp_path / "moved"
    parent.mkdir()
    failure = ValueError("chosen")
    with pytest.raises(ValueError) as error:
        with reserve(parent / "project") as reservation:
            parent.rename(moved)
            parent.mkdir()
            (parent / "keep").write_bytes(b"foreign")
            with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
                reservation.verify()
            raise failure
    assert error.value is failure
    assert (moved / "project").is_dir()
    assert (parent / "keep").read_bytes() == b"foreign"


@pytest.mark.parametrize("when", ["before", "after"])
def test_cancellation_never_leaves_an_empty_reservation(tmp_path: Path, when: str) -> None:
    path = tmp_path / "project"

    def cancelled() -> None:
        if when == "before" or path.exists():
            raise InterruptedError("cancelled")

    with pytest.raises(InterruptedError):
        reserve(path, check_cancel=cancelled)
    assert not path.exists()


def test_owned_descriptors_are_noninheritable_and_close_is_idempotent(tmp_path: Path) -> None:
    reservation = reserve(tmp_path / "project")
    descriptors = [fd for fd in range(3, 256) if _directory_fd(fd, reservation.path)]
    assert len(descriptors) == 1
    assert all(not os.get_inheritable(fd) for fd in descriptors)
    reservation.close()
    reservation.close()
    assert all(not _directory_fd(fd, reservation.path) for fd in descriptors)


def _directory_fd(fd: int, path: Path) -> bool:
    try:
        held = os.fstat(fd)
    except OSError:
        return False
    actual = path.stat()
    return (held.st_dev, held.st_ino) == (actual.st_dev, actual.st_ino)


def test_callback_io_error_preserves_chosen_error_and_owned_cleanup(tmp_path: Path) -> None:
    path = tmp_path / "project"
    failure = OSError("chosen callback failure")

    def check() -> None:
        if path.exists():
            raise failure

    with pytest.raises(OSError) as error:
        reserve(path, check_cancel=check)
    assert error.value is failure
    assert not path.exists()


def test_root_destination_is_conflict(tmp_path: Path) -> None:
    with pytest.raises(project_header.HeaderError) as error:
        reserve(Path("/"))
    assert (error.value.code, error.value.exit_code) == ("PROJECT_EXISTS", 4)


def test_descriptor_cleanup_failure_cannot_replace_selected_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "project"
    failure = ValueError("chosen")
    reservation = reserve(path)
    real_close = os.close

    def faulty_close(fd: int) -> None:
        real_close(fd)
        raise OSError("close failure")

    with pytest.raises(ValueError) as error:
        with reservation:
            monkeypatch.setattr(os, "close", faulty_close)
            raise failure
    assert error.value is failure
    assert not path.exists()
    assert any("descriptor" in note.lower() for note in failure.__notes__)


def test_permission_finalization_failure_cleans_captured_empty_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "project"

    def denied(_fd: int, _mode: int) -> None:
        raise PermissionError("denied mode change")

    monkeypatch.setattr(os, "fchmod", denied)
    with pytest.raises(project_header.HeaderError) as error:
        reserve(path)
    assert (error.value.code, error.value.exit_code) == ("WRITE_FAILED", 5)
    assert not path.exists()
