"""Reject candidate-set changes that a named-file-only guard cannot detect."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

import pytest

from bookscan.resources import ResourceBinding
from bookscan.skew import NativeError


def tree(tmp_path: Path) -> Path:
    root = tmp_path / "fonts"
    (root / "nested").mkdir(parents=True)
    (root / "original.ttf").write_bytes(b"original font")
    (root / "nested" / ".config").write_bytes(b"hidden config")
    return root


@pytest.mark.parametrize(
    "change", ["add", "hidden", "remove", "bytes", "file-inode", "root", "nested", "empty-dir"]
)
def test_directory_change_invalidates_binding(tmp_path: Path, change: str):
    root = tree(tmp_path)
    guard = ResourceBinding.capture([], directories=[root])
    guard.verify()
    if change == "add":
        (root / "nested" / "new.ttf").write_bytes(b"new candidate")
    elif change == "hidden":
        (root / ".new.conf").write_bytes(b"new candidate")
    elif change == "remove":
        (root / "original.ttf").unlink()
    elif change == "bytes":
        (root / "nested" / ".config").write_bytes(b"changed bytes")
    elif change == "file-inode":
        replacement = tmp_path / "replacement"
        replacement.write_bytes(b"original font")
        replacement.replace(root / "original.ttf")
    elif change == "root":
        root.rename(tmp_path / "old")
        tree(tmp_path)
    elif change == "nested":
        (root / "nested").rename(tmp_path / "old")
        (root / "nested").mkdir()
        (root / "nested" / ".config").write_bytes(b"hidden config")
    else:
        (root / "empty").mkdir()
    with pytest.raises(NativeError) as caught:
        guard.verify()
    assert (caught.value.code, caught.value.exit_code) == ("DEPENDENCY_UNAVAILABLE", 5)


def test_external_directory_alias_is_recursively_bound(tmp_path: Path):
    root = tree(tmp_path)
    external = tmp_path / "external"
    external.mkdir()
    (external / "face.ttf").write_bytes(b"external font")
    (root / "alias").symlink_to(external, target_is_directory=True)
    guard = ResourceBinding.capture([], directories=[root])
    guard.verify()
    (external / "new.ttf").write_bytes(b"new external candidate")
    with pytest.raises(NativeError):
        guard.verify()


def test_symlink_retarget_with_equal_bytes_is_rejected(tmp_path: Path):
    root = tree(tmp_path)
    link = tmp_path / "alias"
    link.symlink_to(root, target_is_directory=True)
    other = tmp_path / "other"
    other.mkdir()
    (other / "original.ttf").write_bytes(b"original font")
    guard = ResourceBinding.capture([], directories=[link])
    link.unlink()
    link.symlink_to(other, target_is_directory=True)
    with pytest.raises(NativeError):
        guard.verify()


def test_optional_directory_presence_is_bound(tmp_path: Path):
    root = tmp_path / "optional"
    guard = ResourceBinding.capture([], optional_directories=[root])
    guard.verify()
    root.mkdir()
    with pytest.raises(NativeError):
        guard.verify()


@pytest.mark.parametrize("bad", ["missing", "file", "dangling", "cycle", "fifo"])
def test_partial_directory_inventory_is_rejected(tmp_path: Path, bad: str):
    root = tmp_path / "fonts"
    if bad == "file":
        root.write_bytes(b"not a directory")
    elif bad == "dangling":
        root.symlink_to(tmp_path / "missing", target_is_directory=True)
    elif bad in {"cycle", "fifo"}:
        root.mkdir()
        if bad == "cycle":
            (root / "again").symlink_to(root, target_is_directory=True)
        else:
            os.mkfifo(root / "pipe")
    with pytest.raises(NativeError):
        ResourceBinding.capture([], directories=[root])


def test_dangling_optional_directory_is_not_absence(tmp_path: Path):
    root = tmp_path / "optional"
    root.symlink_to(tmp_path / "missing", target_is_directory=True)
    with pytest.raises(NativeError):
        ResourceBinding.capture([], optional_directories=[root])


@pytest.mark.parametrize("selected", [KeyboardInterrupt(), RuntimeError("owner-selected")])
def test_directory_capture_cancellation_propagates(tmp_path: Path, selected: BaseException):
    root = tree(tmp_path)
    calls = 0

    def cancel():
        nonlocal calls
        calls += 1
        if calls == 5:
            raise selected

    with pytest.raises(type(selected)) as caught:
        ResourceBinding.capture([], directories=[root], check_cancel=cancel)
    assert caught.value is selected


def test_access_time_only_changes_do_not_invalidate_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tree(tmp_path)
    original = Path.lstat
    calls: dict[Path, int] = {}

    def access(path: Path) -> os.stat_result:
        result = original(path)
        calls[path] = calls.get(path, 0) + 1
        fields = list(result)
        fields[7] += calls[path]
        return os.stat_result(fields)

    monkeypatch.setattr(Path, "lstat", access)
    guard = ResourceBinding.capture([], directories=[root])
    guard.verify()


def test_unreadable_directory_does_not_produce_partial_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from collections.abc import Iterator

    root = tree(tmp_path)
    original = Path.iterdir

    def unreadable(path: Path) -> Iterator[Path]:
        if path == root / "nested":
            raise PermissionError("unreadable candidate scope")
        return original(path)

    monkeypatch.setattr(Path, "iterdir", unreadable)
    with pytest.raises(NativeError, match="unreadable candidate scope"):
        ResourceBinding.capture([], directories=[root])


def test_provenance_records_all_members_without_environment_values(tmp_path: Path):
    root = tree(tmp_path)
    guard = ResourceBinding.capture([], directories=[root], environment={"SECRET": "private-value"})
    record = guard.record()
    directory = cast(list[dict[str, object]], record["directories"])[0]
    assert directory["path"] == str(root)
    entries = cast(list[dict[str, object]], directory["entries"])
    assert {Path(str(item["path"])).relative_to(root).as_posix() for item in entries} == {
        ".",
        "original.ttf",
        "nested",
        "nested/.config",
    }
    assert record["runtime_resources_verified"] is False
    assert "private-value" not in json.dumps(record)
    entries.clear()
    guard.verify()
    assert cast(list[dict[str, object]], guard.record()["directories"])[0]["entries"]


@pytest.mark.parametrize("phase", ["before", "during"])
def test_candidate_addition_prevents_returning_raster(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
):
    import subprocess
    from collections.abc import Callable, Mapping

    from PIL import Image
    from test_render import source

    from bookscan import render

    saved = source(tmp_path)
    root = tree(tmp_path)
    guard = ResourceBinding.capture([], directories=[root])
    launches: list[str] = []

    def child(
        argv: list[str],
        *,
        check_cancel: Callable[[], None],
        environment: Mapping[str, str],
        directory: Path,
    ) -> subprocess.CompletedProcess[str]:
        launches.append("renderer")
        with Image.new("RGB", (10, 5), "white") as image:
            image.save(argv[-1] + ".png")
        (root / "new.ttf").write_bytes(b"new candidate")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(render, "execute", child)
    if phase == "before":
        (root / "new.ttf").write_bytes(b"new candidate")
    with pytest.raises(NativeError):
        render.render_page(saved, saved.pages[0], Path("renderer"), resources=guard)
    assert launches == ([] if phase == "before" else ["renderer"])
    saved.verify()


def test_addition_while_binding_cannot_yield_partial_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from collections.abc import Callable

    from bookscan import resources

    root = tree(tmp_path)
    original = resources.digest

    def changed(path: Path, *, check_cancel: Callable[[], None]) -> str:
        value = original(path, check_cancel=check_cancel)
        (root / "new.ttf").write_bytes(b"new candidate")
        return value

    monkeypatch.setattr(resources, "digest", changed)
    with pytest.raises(NativeError, match="changed while binding"):
        ResourceBinding.capture([], directories=[root])


@pytest.mark.parametrize("name", ["missing.ttf", ".home-manager-fonts-version"])
def test_dangling_child_is_recorded_without_losing_directory_members(tmp_path: Path, name: str):
    root = tree(tmp_path)
    missing = tmp_path / "absent" / "font.ttf"
    link = root / name
    link.symlink_to(missing)
    guard = ResourceBinding.capture([], directories=[root])
    guard.verify()
    entries = guard.directories[0].entries
    assert entries is not None
    record = next(item for item in entries if item.path == str(link))
    assert (record.kind, record.resolved, record.link_target) == (
        "dangling-symlink",
        str(missing),
        str(missing),
    )
    assert (record.device, record.inode, record.sha256) == (None, None, None)
    assert {Path(item.path).relative_to(root).as_posix() for item in entries} == {
        ".",
        "nested",
        "nested/.config",
        "original.ttf",
        name,
    }


@pytest.mark.parametrize("change", ["target-file", "target-tree", "retarget", "replace", "remove"])
def test_dangling_child_change_invalidates_guard(tmp_path: Path, change: str):
    root = tree(tmp_path)
    missing = tmp_path / "missing"
    link = root / ".missing"
    link.symlink_to(missing)
    guard = ResourceBinding.capture([], directories=[root])
    if change == "target-file":
        missing.write_bytes(b"new font")
    elif change == "target-tree":
        missing.mkdir()
        (missing / "new.ttf").write_bytes(b"new font")
    elif change == "retarget":
        link.unlink()
        link.symlink_to(tmp_path / "other-missing")
    elif change == "replace":
        # Keep the old inode alive so replacement cannot accidentally reuse it.
        link.rename(tmp_path / "old-link")
        link.symlink_to(missing)
    else:
        link.unlink()
    with pytest.raises(NativeError) as caught:
        guard.verify()
    assert (caught.value.code, caught.value.exit_code) == ("DEPENDENCY_UNAVAILABLE", 5)


def test_missing_target_resolution_includes_intermediate_alias(tmp_path: Path):
    root = tree(tmp_path)
    intermediate = tmp_path / "intermediate"
    intermediate.symlink_to(tmp_path / "absent-a", target_is_directory=True)
    (root / "missing.ttf").symlink_to(intermediate / "face.ttf")
    guard = ResourceBinding.capture([], directories=[root])
    intermediate.unlink()
    intermediate.symlink_to(tmp_path / "absent-b", target_is_directory=True)
    with pytest.raises(NativeError):
        guard.verify()


@pytest.mark.parametrize("resolution", [1, 2])
def test_target_appearance_during_dangling_capture_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, resolution: int
):
    root = tree(tmp_path)
    missing = tmp_path / "missing.ttf"
    link = root / "missing.ttf"
    link.symlink_to(missing)
    original = Path.resolve
    calls = 0

    def appears(path: Path, strict: bool = False) -> Path:
        nonlocal calls
        resolved = original(path, strict=strict)
        if path == link and not strict:
            calls += 1
            if calls == resolution:
                missing.write_bytes(b"new font")
        return resolved

    monkeypatch.setattr(Path, "resolve", appears)
    with pytest.raises(NativeError, match="changed while binding"):
        ResourceBinding.capture([], directories=[root])
