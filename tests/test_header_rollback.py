"""Failed bootstrap publication owns exact names, never checkpoint or foreign state."""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from bookscan import assets, checkpoints, ownership, project_header


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    path = tmp_path / "Rollback project"
    path.mkdir()
    with ownership.Writer.acquire(path, ownership.provision(path)) as writer:
        yield writer


@pytest.mark.parametrize("stage", ["private-unlink", "readback", "verification"])
@pytest.mark.parametrize(
    "change",
    [
        "none",
        "read",
        "missing",
        "bytes",
        "mode",
        "mtime",
        "hardlink",
        "replace",
        "symlink",
        "root",
        "parent",
        "store",
        "checkpoint",
        "unlink-denied",
    ],
)
def test_failed_published_bootstrap_respects_captured_names(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, stage: str, change: str
) -> None:
    selected = RuntimeError("chosen published bootstrap failure")
    original_read = project_header._read  # pyright: ignore[reportPrivateUsage]
    original_verify = project_header.Stores.verify
    original_unlink = os.unlink
    header = owner.path / "project.json"
    original_root = owner.path.parent if change == "parent" else owner.path
    moved_root = original_root.with_name(original_root.name + "-moved")
    retained: dict[str, bytes] = {}

    def fail() -> None:
        names = [header, *owner.path.glob(".header-*")]
        if change == "read":
            for path in names:
                path.read_bytes()
        elif change == "missing":
            for path in names:
                path.unlink()
        elif change == "bytes":
            raw = header.read_bytes()
            header.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
        elif change == "mode":
            header.chmod(0o640)
        elif change == "mtime":
            info = header.stat()
            os.utime(header, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000))
        elif change == "hardlink":
            os.link(header, owner.path / "foreign-link")
        elif change in {"replace", "symlink"}:
            header.rename(owner.path / "moved-header")
            if change == "replace":
                header.write_bytes(b"foreign header")
            else:
                header.symlink_to(owner.path / "moved-header")
        elif change in {"root", "parent"}:
            original_root.rename(moved_root)
            original_root.mkdir()
        elif change == "store":
            (owner.path / "assets" / "foreign").write_bytes(b"unknown asset")
        elif change == "checkpoint":
            info = (owner.path / "checkpoints").stat()
            history = checkpoints.Checkpoints(
                owner, assets.DirectoryIdentity(info.st_dev, info.st_ino)
            )
            history.commit({"protected": True}, expected=None, verify_state=lambda state: None)
        elif change == "unlink-denied":

            def denied(target: Any, *, dir_fd: int | None = None) -> None:
                if target == "project.json" or str(target).startswith(".header-"):
                    raise PermissionError("published cleanup denied")
                original_unlink(target, dir_fd=dir_fd)

            monkeypatch.setattr(os, "unlink", denied)
        if change not in {"root", "parent", "missing"}:
            retained.update({p.name: p.read_bytes() for p in names})
        raise selected

    def failed_read(*args: Any, **kwargs: Any) -> Any:
        original_read(*args, **kwargs)
        fail()

    def failed_verify(self: project_header.Stores, **kwargs: Any) -> None:
        original_verify(self, **kwargs)
        fail()

    if stage == "private-unlink":

        def failed_unlink(*args: Any) -> None:
            fail()

        monkeypatch.setattr(project_header, "_unlink", failed_unlink)
    elif stage == "readback":
        monkeypatch.setattr(project_header, "_read", failed_read)
    else:
        monkeypatch.setattr(project_header.Stores, "verify", failed_verify)
    try:
        with pytest.raises(RuntimeError) as caught:
            project_header.Stores.provision(owner)
        assert caught.value is selected
        if change in {"none", "read", "missing"}:
            assert {p.name for p in owner.path.iterdir()} == {"writer.lock"}
        elif change in {"root", "parent"}:
            retained_root = moved_root if change == "root" else moved_root / owner.path.name
            assert (retained_root / "project.json").is_file()
            assert list(original_root.iterdir()) == []
        else:
            assert header.exists()
            assert all((owner.path / name).read_bytes() == raw for name, raw in retained.items())
            if change == "checkpoint":
                assert (owner.path / "checkpoints" / "current").is_symlink()
        if change not in {"none", "read", "missing"}:
            assert any("cleanup" in note.lower() for note in getattr(selected, "__notes__", []))
    finally:
        if change in {"root", "parent"} and moved_root.exists():
            original_root.rmdir()
            moved_root.rename(original_root)
    owner.verify()
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)


@pytest.mark.parametrize("stage", ["link", "unlink"])
@pytest.mark.parametrize("change", ["bytes", "mode", "mtime", "hardlink"])
def test_header_transition_does_not_adopt_unrelated_mutation(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, stage: str, change: str
) -> None:
    original_link = os.link
    original_unlink = project_header._unlink  # pyright: ignore[reportPrivateUsage]
    header = owner.path / "project.json"
    retained: list[bytes] = []

    def mutate() -> None:
        if change == "bytes":
            raw = header.read_bytes()
            header.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
        elif change == "mode":
            header.chmod(0o640)
        elif change == "mtime":
            before = header.stat()
            os.utime(header, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000))
        else:
            original_link(header, owner.path / "foreign-link")
        retained.append(header.read_bytes())

    def linked(*args: Any, **kwargs: Any) -> None:
        original_link(*args, **kwargs)
        mutate()

    def unlinked(*args: Any, **kwargs: Any) -> None:
        original_unlink(*args, **kwargs)
        mutate()

    if stage == "link":
        monkeypatch.setattr(os, "link", linked)
    else:
        monkeypatch.setattr(project_header, "_unlink", unlinked)
    with pytest.raises(project_header.HeaderError):
        project_header.Stores.provision(owner)
    assert retained and header.read_bytes() == retained[0]
    assert all(
        (owner.path / name).is_dir()
        for name in ("assets", "checkpoints", "native-blobs", "packets")
    )
    owner.verify()


@pytest.mark.parametrize("links", [1, 2])
def test_unknown_postlink_capture_retains_names_and_selected_failure(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, links: int
) -> None:
    original_fstat = os.fstat
    selected = PermissionError("postlink metadata capture denied")
    header = owner.path / "project.json"
    denied = False

    def capture(descriptor: int) -> os.stat_result:
        nonlocal denied
        info = original_fstat(descriptor)
        if header.exists() and info.st_ino == header.stat().st_ino and info.st_nlink == links:
            denied = True
            raise selected
        return info

    with monkeypatch.context() as patch:
        patch.setattr(os, "fstat", capture)
        with pytest.raises(project_header.HeaderError) as caught:
            project_header.Stores.provision(owner)
    assert denied and caught.value.__cause__ is selected
    assert header.is_file()
    assert header.stat().st_nlink == links
    assert "identity unavailable" in " ".join(getattr(selected, "__notes__", []))
    owner.verify()


@pytest.mark.parametrize("stage", ["readback", "verification"])
def test_postpublication_cleanup_close_failure_preserves_selected_exception(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    selected = KeyboardInterrupt("selected postpublication interruption")
    original_read = project_header._read  # pyright: ignore[reportPrivateUsage]
    original_close = os.close
    failures: list[int] = []

    def failed_read(*args: Any, **kwargs: Any) -> Any:
        original_read(*args, **kwargs)
        raise selected

    def failed_verify(*args: Any, **kwargs: Any) -> None:
        raise selected

    def closed(descriptor: int) -> None:
        import sys

        original_close(descriptor)
        if sys.exception() is selected:
            failures.append(descriptor)
            raise OSError("postpublication descriptor release failure")

    with monkeypatch.context() as patch:
        patch.setattr(os, "close", closed)
        patch.setattr(
            project_header if stage == "readback" else project_header.Stores,
            "_read" if stage == "readback" else "verify",
            failed_read if stage == "readback" else failed_verify,
        )
        with pytest.raises(KeyboardInterrupt) as caught:
            project_header.Stores.provision(owner)
    assert caught.value is selected and failures
    assert {p.name for p in owner.path.iterdir()} == {"writer.lock"}
    assert any("descriptor" in note.lower() for note in getattr(selected, "__notes__", []))
    owner.verify()


@pytest.mark.parametrize("change", ["bytes", "mode", "mtime", "hardlink"])
def test_mutation_during_rollback_unlink_retains_remaining_private_name(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    original_unlink = os.unlink
    selected = RuntimeError("selected publication failure before private unlink")
    remaining: list[tuple[str, bytes]] = []

    def failed_unlink(*args: Any) -> None:
        raise selected

    def mutate_after(target: Any, *, dir_fd: int | None = None) -> None:
        original_unlink(target, dir_fd=dir_fd)
        if target == "project.json":
            private = next(owner.path.glob(".header-*"))
            if change == "bytes":
                raw = private.read_bytes()
                private.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
            elif change == "mode":
                private.chmod(0o640)
            elif change == "mtime":
                before = private.stat()
                os.utime(private, ns=(before.st_atime_ns, before.st_mtime_ns + 1))
            else:
                os.link(private, owner.path / "foreign-link")
            remaining.append((private.name, private.read_bytes()))

    monkeypatch.setattr(project_header, "_unlink", failed_unlink)
    monkeypatch.setattr(os, "unlink", mutate_after)
    with pytest.raises(RuntimeError) as caught:
        project_header.Stores.provision(owner)
    assert caught.value is selected and remaining
    name, raw = remaining[0]
    assert (owner.path / name).read_bytes() == raw
    assert "cleanup" in " ".join(getattr(selected, "__notes__", []))
    owner.verify()


@pytest.mark.parametrize("stage", ["private-unlink", "readback"])
def test_checkpoint_activity_before_header_write_is_never_adopted_as_empty(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    from bookscan import native_blobs

    original_native = native_blobs.Blobs.provision
    selected = RuntimeError("header publication failure with preceding checkpoint")
    checkpoint_hash: list[str] = []

    def native(*args: Any, **kwargs: Any) -> native_blobs.Blobs:
        result = original_native(*args, **kwargs)
        info = (owner.path / "checkpoints").stat()
        history = checkpoints.Checkpoints(owner, assets.DirectoryIdentity(info.st_dev, info.st_ino))
        committed = history.commit(
            {"protected": True}, expected=None, verify_state=lambda state: None
        )
        checkpoint_hash.append(committed.checkpoint.sha256)
        return result

    def failed(*args: Any, **kwargs: Any) -> Any:
        raise selected

    monkeypatch.setattr(native_blobs.Blobs, "provision", native)
    monkeypatch.setattr(project_header, "_unlink" if stage == "private-unlink" else "_read", failed)
    with pytest.raises((RuntimeError, project_header.HeaderError)):
        project_header.Stores.provision(owner)
    assert checkpoint_hash
    assert (owner.path / "checkpoints/current").readlink().name == checkpoint_hash[0] + ".json"
    header = owner.path / "project.json"
    # Either refuse before creating the header, or retain it with the existing checkpoint.
    # A publisher that ran and then removed its header has crossed the wrong boundary.
    assert header.exists() or not getattr(selected, "__traceback__", None)
    owner.verify()
