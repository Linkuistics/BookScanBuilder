"""Failed import removes only its captured, untouched, empty bootstrap.

Native preflight is substituted at the responsible boundary. Source snapshot,
reservation, writer, header, stores and cleanup run on the real filesystem.
"""

import os
from pathlib import Path
from typing import Any, NoReturn

import pikepdf
import pytest

from bookscan import checkpoints, initial_import, ownership, project_header


def source_pdf(path: Path) -> None:
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(72, 72))
        pdf.save(path)


def contents(project: Path) -> dict[str, bytes | tuple[int, ...]]:
    """Freeze actual names, bytes and native metadata, excluding read-only atime."""
    result: dict[str, bytes | tuple[int, ...]] = {}
    for entry in project.rglob("*"):
        name = str(entry.relative_to(project))
        info = entry.lstat()
        result[name + ":stat"] = (
            info.st_dev,
            info.st_ino,
            info.st_mode,
            info.st_nlink,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        )
        if entry.is_symlink():
            result[name] = os.fsencode(entry.readlink())
        elif entry.is_file():
            result[name] = entry.read_bytes()
    return result


@pytest.mark.parametrize("cancelled", [False, True])
@pytest.mark.parametrize("change", ["none", "read", "unknown"])
def test_failed_preflight_cleans_unchanged_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cancelled: bool, change: str
) -> None:
    source, project = tmp_path / "source.pdf", tmp_path / "project"
    source_pdf(source)
    before = source.read_bytes()
    selected = InterruptedError("selected cancellation") if cancelled else OSError("preflight")

    def fail(saved: object, directory: Path, **options: Any) -> NoReturn:
        if change == "read":
            for name in ("assets", "checkpoints", "native-blobs", "packets"):
                list((directory / name).iterdir())
            (directory / "project.json").read_bytes()
        elif change == "unknown":
            (directory / "foreign").write_bytes(b"unknown file")
            (directory / "unknown-directory").mkdir()
        raise selected

    monkeypatch.setattr(initial_import, "_native", fail)
    progress = initial_import.Progress()
    with pytest.raises(type(selected)) as caught:
        initial_import.create(source, project, cache=tmp_path / "cache", progress=progress)
    assert caught.value is selected
    assert not progress.committed and progress.result is None
    assert source.read_bytes() == before
    if change == "unknown":
        assert {entry.name for entry in project.iterdir()} == {"foreign", "unknown-directory"}
        assert (project / "foreign").read_bytes() == b"unknown file"
    else:
        assert not project.exists()


@pytest.mark.parametrize("store", ["assets", "checkpoints", "native-blobs", "packets"])
@pytest.mark.parametrize(
    "change", ["mode", "mtime-ns", "nonempty", "emptied", "replace", "symlink", "missing"]
)
def test_store_activity_preserves_entire_bootstrap_and_selected_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, store: str, change: str
) -> None:
    source, project = tmp_path / "source.pdf", tmp_path / "project"
    source_pdf(source)
    selected = RuntimeError("selected native failure after store activity")
    captured: dict[str, bytes | tuple[int, ...]] = {}

    def fail(saved: object, directory: Path, **options: Any) -> NoReturn:
        path = directory / store
        if change == "mode":
            path.chmod(0o750)
        elif change == "mtime-ns":
            info = path.stat()
            os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1))
        elif change in {"nonempty", "emptied"}:
            child = path / "unknown"
            child.write_bytes(b"foreign contents")
            if change == "emptied":
                child.unlink()
        elif change in {"replace", "symlink"}:
            path.rename(directory / "original-store")
            if change == "replace":
                path.mkdir()
            else:
                path.symlink_to("original-store", target_is_directory=True)
        else:
            path.rmdir()
        captured.update(contents(directory))
        raise selected

    monkeypatch.setattr(initial_import, "_native", fail)
    with pytest.raises(RuntimeError) as caught:
        initial_import.create(
            source, project, cache=tmp_path / "cache", progress=initial_import.Progress()
        )
    assert caught.value is selected
    assert contents(project) == captured
    assert (project / "source.pdf").read_bytes() == source.read_bytes()
    assert any("retained" in note.lower() for note in selected.__notes__)


@pytest.mark.parametrize("change", ["modify", "replace", "mtime-ns", "hardlink", "symlink"])
def test_changed_header_preserves_entire_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    source, project = tmp_path / "source.pdf", tmp_path / "project"
    source_pdf(source)
    selected = RuntimeError("selected failure after changed header")
    captured: dict[str, bytes | tuple[int, ...]] = {}

    def fail(saved: object, directory: Path, **options: Any) -> NoReturn:
        path = directory / "project.json"
        if change == "modify":
            path.write_bytes(b"foreign changed header")
        elif change == "mtime-ns":
            info = path.stat()
            os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1))
        elif change == "hardlink":
            os.link(path, directory / "other-header")
        else:
            path.rename(directory / "original-header")
            if change == "replace":
                path.write_bytes((directory / "original-header").read_bytes())
            else:
                path.symlink_to("original-header")
        captured.update(contents(directory))
        raise selected

    monkeypatch.setattr(initial_import, "_native", fail)
    with pytest.raises(RuntimeError) as caught:
        initial_import.create(
            source, project, cache=tmp_path / "cache", progress=initial_import.Progress()
        )
    assert caught.value is selected
    assert contents(project) == captured


@pytest.mark.parametrize("change", ["root", "parent", "parent-root-moved-back"])
def test_changed_ancestry_keeps_original_and_replacement_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    source = tmp_path / "source.pdf"
    source_pdf(source)
    parent = tmp_path / "parent"
    parent.mkdir()
    project = parent / "project"
    moved = tmp_path / "moved"
    selected = RuntimeError("selected failure after ancestry replacement")
    captured: dict[str, bytes | tuple[int, ...]] = {}
    original = project

    def fail(saved: object, directory: Path, **options: Any) -> NoReturn:
        nonlocal original
        if change == "root":
            directory.rename(moved)
            directory.mkdir()
            original = moved
        else:
            parent.rename(moved)
            parent.mkdir()
            original = moved / "project"
            if change == "parent-root-moved-back":
                original.rename(project)
                original = project
        captured.update(contents(original))
        raise selected

    monkeypatch.setattr(initial_import, "_native", fail)
    with pytest.raises(RuntimeError) as caught:
        initial_import.create(
            source, project, cache=tmp_path / "cache", progress=initial_import.Progress()
        )
    assert caught.value is selected
    assert contents(original) == captured
    if change == "root":
        assert list(project.iterdir()) == []
    elif change == "parent":
        assert list(parent.iterdir()) == []


def test_actual_checkpoint_published_before_selected_failure_is_never_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, project = tmp_path / "source.pdf", tmp_path / "project"
    source_pdf(source)
    provision = project_header.Stores.provision
    stores: list[project_header.Stores] = []
    selected = RuntimeError("selected failure with an actual checkpoint")
    captured: dict[str, bytes | tuple[int, ...]] = {}

    def remember(cls: type[project_header.Stores], *args: Any, **kwargs: Any) -> Any:
        result = provision(*args, **kwargs)
        stores.append(result)
        return result

    def fail(saved: object, directory: Path, **options: Any) -> NoReturn:
        def verify(value: dict[str, object]) -> None:
            assert value == {"retained": "actual checkpoint"}

        result = stores[0].checkpoints.commit(
            {"retained": "actual checkpoint"}, expected=None, verify_state=verify
        )
        assert result.committed
        captured.update(contents(directory))
        raise selected

    monkeypatch.setattr(project_header.Stores, "provision", classmethod(remember))
    monkeypatch.setattr(initial_import, "_native", fail)
    with pytest.raises(RuntimeError) as caught:
        initial_import.create(
            source, project, cache=tmp_path / "cache", progress=initial_import.Progress()
        )
    assert caught.value is selected
    assert contents(project) == captured
    # The checkpoint is a real store transaction, not a baseline-semantic fixture.
    with ownership.Writer.acquire(project, stores[0].owner.identity) as owner:
        history = checkpoints.Checkpoints(owner, stores[0].header.checkpoints)
        restored = history.load(verify_state=lambda value: None)
        assert restored.state == {"retained": "actual checkpoint"}


@pytest.mark.parametrize("fault", ["header-unlink", "store-rmdir"])
def test_cleanup_failure_preserves_selected_error_and_remaining_owned_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    source, project = tmp_path / "source.pdf", tmp_path / "project"
    source_pdf(source)
    selected = InterruptedError("selected cancellation before cleanup")
    unlink, rmdir = os.unlink, os.rmdir

    def deny_unlink(path: Any, *args: Any, **kwargs: Any) -> None:
        if path == "project.json":
            raise PermissionError("header unlink denied")
        unlink(path, *args, **kwargs)

    def deny_rmdir(path: Any, *args: Any, **kwargs: Any) -> None:
        if path == "native-blobs":
            raise PermissionError("store removal denied")
        rmdir(path, *args, **kwargs)

    def fail(saved: object, directory: Path, **options: Any) -> NoReturn:
        monkeypatch.setattr(
            os,
            "unlink" if fault == "header-unlink" else "rmdir",
            deny_unlink if fault == "header-unlink" else deny_rmdir,
        )
        raise selected

    monkeypatch.setattr(initial_import, "_native", fail)
    with pytest.raises(InterruptedError) as caught:
        initial_import.create(
            source, project, cache=tmp_path / "cache", progress=initial_import.Progress()
        )
    assert caught.value is selected
    assert (project / "native-blobs").is_dir()
    assert (project / "source.pdf").read_bytes() == source.read_bytes()
    assert (project / "writer.lock").is_file()
    assert (project / "project.json").exists() is (fault == "header-unlink")
    assert any("cleanup" in note.lower() for note in selected.__notes__)
