"""Completed import publications are owned; matching contents alone are not.

Native assessment is substituted. Real reservations, source snapshots, writer
ownership, PNG/blob publication and checkpoint commits remain in the path.
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn, cast

import pikepdf
import pytest

from bookscan import initial_import, project_header


def freeze(project: Path) -> dict[str, bytes | tuple[int, ...]]:
    result: dict[str, bytes | tuple[int, ...]] = {}
    for path in project.rglob("*"):
        key = str(path.relative_to(project))
        info = path.lstat()
        result[key + ":stat"] = (
            info.st_dev,
            info.st_ino,
            info.st_mode,
            info.st_nlink,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        )
        if path.is_symlink():
            result[key] = os.fsencode(path.readlink())
        elif path.is_file():
            result[key] = path.read_bytes()
    return result


@pytest.mark.parametrize("kind", ["rgb", "native", "both"])
@pytest.mark.parametrize("stop", ["failure", "cancel", "post-read"])
def test_failed_import_removes_only_its_completed_asset_publications(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, stop: str
) -> None:
    source, project = tmp_path / "input.pdf", tmp_path / "project"
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(72, 72))
        pdf.save(source)
    source_before = source.read_bytes()
    provision = project_header.Stores.provision
    stores: list[project_header.Stores] = []
    selected = (
        InterruptedError("selected cancellation")
        if stop == "cancel"
        else RuntimeError("selected failure after complete asset publication")
    )

    def remember(cls: type[project_header.Stores], *args: Any, **kwargs: Any) -> Any:
        result = provision(*args, **kwargs)
        stores.append(result)
        return result

    def fail(saved: object, directory: Path, **options: Any) -> NoReturn:
        store = stores[0]
        if kind in {"rgb", "both"}:
            first = store.images.publish(b"\xff\x00\x01" * 4, (2, 2))
            assert store.images.read(first) == b"\xff\x00\x01" * 4
            assert store.images.publish(b"\xff\x00\x01" * 4, (2, 2)) == first
            store.images.publish(b"\x02\x03\x04", (1, 1))
        if kind in {"native", "both"}:
            first_native = store.native.publish(b"native-channel")
            assert store.native.read(first_native) == b"native-channel"
            assert store.native.publish(b"native-channel") == first_native
            store.native.publish(b"")
        if stop == "post-read":
            # The final verification read can fail after a link was published
            # and its private name removed, before publish returns a reference.
            target = store.images if kind == "rgb" else store.native
            original = cast(Callable[..., bytes], getattr(target, "_read"))

            def read(*args: Any, **kwargs: Any) -> bytes:
                value = original(*args, **kwargs)
                if kwargs.get("name") is None:
                    raise selected
                return value

            monkeypatch.setattr(target, "_read", read)
            if kind == "rgb":
                store.images.publish(b"\x05\x06\x07", (1, 1))
            else:
                store.native.publish(b"third-native-channel")
        raise selected

    monkeypatch.setattr(project_header.Stores, "provision", classmethod(remember))
    monkeypatch.setattr(initial_import, "_native", fail)
    progress = initial_import.Progress()
    with pytest.raises(type(selected)) as caught:
        initial_import.create(source, project, cache=tmp_path / "cache", progress=progress)
    assert caught.value is selected
    assert not progress.committed and progress.result is None
    assert source.read_bytes() == source_before
    assert not project.exists()


@pytest.mark.parametrize("kind", ["rgb", "native"])
@pytest.mark.parametrize(
    "change",
    [
        "bytes",
        "mode",
        "mtime",
        "replace",
        "symlink",
        "hardlink",
        "unknown",
        "checkpoint",
    ],
)
def test_changed_asset_or_checkpoint_preserves_all_supporting_import_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, change: str
) -> None:
    source, project = tmp_path / "input.pdf", tmp_path / "project"
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(72, 72))
        pdf.save(source)
    provision = project_header.Stores.provision
    stores: list[project_header.Stores] = []
    selected = RuntimeError("selected failure with changed or committed assets")
    captured: dict[str, bytes | tuple[int, ...]] = {}

    def remember(cls: type[project_header.Stores], *args: Any, **kwargs: Any) -> Any:
        result = provision(*args, **kwargs)
        stores.append(result)
        return result

    def fail(saved: object, directory: Path, **options: Any) -> NoReturn:
        store = stores[0]
        rgb = store.images.publish(b"\xff\x00\x01" * 4, (2, 2))
        native = store.native.publish(b"native-channel")
        path = (
            directory
            / ("assets" if kind == "rgb" else "native-blobs")
            / (rgb.id + ".png" if kind == "rgb" else native.sha256 + ".bin")
        )
        if change == "bytes":
            path.write_bytes(b"changed owned inode")
        elif change == "mode":
            path.chmod(0o400)
        elif change == "mtime":
            info = path.stat()
            os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1))
        elif change in {"replace", "symlink"}:
            path.rename(directory / "original-asset")
            if change == "replace":
                path.write_bytes((directory / "original-asset").read_bytes())
            else:
                path.symlink_to(directory / "original-asset")
        elif change == "hardlink":
            os.link(path, directory / "another-asset-name")
        elif change == "unknown":
            (path.parent / "unknown").write_bytes(b"foreign file; do not sweep")
        else:
            result = store.checkpoints.commit(
                {"rgb": rgb.record(), "native": native.record()},
                expected=None,
                verify_state=lambda value: None,
            )
            assert result.committed
        captured.update(freeze(directory))
        raise selected

    monkeypatch.setattr(project_header.Stores, "provision", classmethod(remember))
    monkeypatch.setattr(initial_import, "_native", fail)
    with pytest.raises(RuntimeError) as caught:
        initial_import.create(
            source, project, cache=tmp_path / "cache", progress=initial_import.Progress()
        )
    assert caught.value is selected
    assert freeze(project) == captured


@pytest.mark.parametrize("kind", ["rgb", "native"])
@pytest.mark.parametrize("change", ["unlink-denied", "private-cleanup", "store-mode", "parent"])
def test_unsafe_or_incomplete_cleanup_retains_remaining_import_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, change: str
) -> None:
    source, project = tmp_path / "input.pdf", tmp_path / "project"
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(72, 72))
        pdf.save(source)
    provision = project_header.Stores.provision
    stores: list[project_header.Stores] = []
    selected = RuntimeError("selected failed import")
    original_unlink = os.unlink
    moved = tmp_path / "moved-parent"
    parent = tmp_path / "parent"
    parent.mkdir()
    project = parent / "project"

    def remember(cls: type[project_header.Stores], *args: Any, **kwargs: Any) -> Any:
        result = provision(*args, **kwargs)
        stores.append(result)
        return result

    def fail(saved: object, directory: Path, **options: Any) -> NoReturn:
        store = stores[0]
        suffix = ".png" if kind == "rgb" else ".bin"
        prefix = ".rgb-" if kind == "rgb" else ".blob-"
        if change == "private-cleanup":

            def refuse_private(path: Any, *args: Any, **kwargs: Any) -> None:
                if isinstance(path, str) and path.startswith(prefix):
                    raise selected
                original_unlink(path, *args, **kwargs)

            monkeypatch.setattr(os, "unlink", refuse_private)
        if kind == "rgb":
            store.images.publish(b"\x01\x02\x03", (1, 1))
        else:
            store.native.publish(b"native-channel")
        if change in {"unlink-denied", "store-mode"}:

            def unlink(path: Any, *args: Any, **kwargs: Any) -> None:
                if isinstance(path, str) and path.endswith(suffix):
                    if change == "unlink-denied":
                        raise PermissionError("owned asset unlink denied")
                    original_unlink(path, *args, **kwargs)
                    (directory / ("assets" if kind == "rgb" else "native-blobs")).chmod(0o750)
                    return
                original_unlink(path, *args, **kwargs)

            monkeypatch.setattr(os, "unlink", unlink)
        elif change == "parent":
            parent.rename(moved)
            parent.mkdir()
            (moved / "project").rename(project)
        raise selected

    monkeypatch.setattr(project_header.Stores, "provision", classmethod(remember))
    monkeypatch.setattr(initial_import, "_native", fail)
    with pytest.raises(RuntimeError) as caught:
        initial_import.create(
            source, project, cache=tmp_path / "cache", progress=initial_import.Progress()
        )
    assert caught.value is selected
    assert (project / "source.pdf").read_bytes() == source.read_bytes()
    assert (project / "writer.lock").is_file()
    assert (project / "project.json").is_file()
    assert (project / "assets").is_dir() and (project / "native-blobs").is_dir()
    if change == "private-cleanup":
        names = {
            p.name for p in (project / ("assets" if kind == "rgb" else "native-blobs")).iterdir()
        }
        assert len(names) == 2
        assert any(name.startswith(".rgb-" if kind == "rgb" else ".blob-") for name in names)
    assert any("retained" in note.lower() for note in selected.__notes__)
