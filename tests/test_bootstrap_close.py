"""A close-only bootstrap failure must not strand an unchanged new project header."""

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from bookscan import assets, checkpoints, ownership, project_header


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    path = tmp_path / "Closing project"
    path.mkdir()
    with ownership.Writer.acquire(path, ownership.provision(path)) as writer:
        yield writer


def close_fault(
    patch: pytest.MonkeyPatch,
    owner: ownership.Writer,
    stage: str,
    mutate: Callable[[], None],
    after_release: Callable[[], None] = lambda: None,
) -> tuple[OSError, list[int]]:
    """Use real descriptors and release the selected one before reporting failure.

    Original provision descriptors remain open throughout store creation. The
    publisher's first root open precedes readback opens; capture that original,
    never a later fd with the same filesystem identity.
    """
    original_open, original_close = os.open, os.close
    original_publish = project_header._publish  # pyright: ignore[reportPrivateUsage]
    publishing = False
    captured: dict[str, int] = {}
    failures: list[int] = []
    selected = OSError("selected close failure after actual release")

    def opened(target: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        descriptor = original_open(target, flags, mode, dir_fd=dir_fd)
        if publishing:
            if target == owner.path:
                captured.setdefault("publisher-root", descriptor)
            elif str(target).startswith(".header-"):
                captured.setdefault("publisher-file", descriptor)
        elif target == owner.path.parent:
            captured.setdefault("provision-parent", descriptor)
        elif target == owner.path.name and dir_fd == captured.get("provision-parent"):
            captured.setdefault("provision-root", descriptor)
        return descriptor

    def published(*args: Any, **kwargs: Any) -> Any:
        nonlocal publishing
        publishing = True
        try:
            return original_publish(*args, **kwargs)
        finally:
            publishing = False

    def closed(descriptor: int) -> None:
        if not failures and descriptor == captured.get(stage):
            assert (owner.path / "project.json").is_file()
            mutate()
            original_close(descriptor)
            failures.append(descriptor)
            after_release()
            raise selected
        original_close(descriptor)

    patch.setattr(project_header, "_publish", published)
    patch.setattr(os, "open", opened)
    patch.setattr(os, "close", closed)
    return selected, failures


@pytest.mark.parametrize(
    "stage", ["publisher-file", "publisher-root", "provision-root", "provision-parent"]
)
@pytest.mark.parametrize("change", ["none", "read", "missing"])
def test_close_only_failure_removes_exact_unchanged_bootstrap(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, stage: str, change: str
) -> None:
    header = owner.path / "project.json"

    def mutate() -> None:
        if change == "read":
            header.read_bytes()
            for name in ("assets", "checkpoints", "native-blobs", "packets"):
                list((owner.path / name).iterdir())
        elif change == "missing":
            header.unlink()

    with monkeypatch.context() as patch:
        selected, failures = close_fault(patch, owner, stage, mutate)
        with pytest.raises(project_header.HeaderError) as caught:
            project_header.Stores.provision(owner)
    assert failures and caught.value.__cause__ is selected
    assert (caught.value.code, caught.value.exit_code) == ("WRITE_FAILED", 5)
    assert {path.name for path in owner.path.iterdir()} == {"writer.lock"}
    owner.verify()
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)


@pytest.mark.parametrize(
    "stage", ["publisher-file", "publisher-root", "provision-root", "provision-parent"]
)
@pytest.mark.parametrize(
    "change",
    [
        "bytes",
        "mode",
        "mtime",
        "hardlink",
        "replace",
        "symlink",
        "store",
        "checkpoint",
        "store-mode",
        "store-mtime",
        "store-emptied",
    ],
)
def test_close_only_failure_preserves_changed_header_or_store(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, stage: str, change: str
) -> None:
    header = owner.path / "project.json"
    retained: list[bytes] = []
    checkpoint: list[str] = []

    def mutate() -> None:
        if change == "bytes":
            raw = header.read_bytes()
            header.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
        elif change == "mode":
            header.chmod(0o640)
        elif change == "mtime":
            info = header.stat()
            os.utime(header, ns=(info.st_atime_ns, info.st_mtime_ns + 1))
        elif change == "hardlink":
            os.link(header, owner.path / "foreign-link")
        elif change in {"replace", "symlink"}:
            header.rename(owner.path / "original-header")
            if change == "replace":
                header.write_bytes(b"foreign header")
            else:
                header.symlink_to("original-header")
        elif change == "store":
            (owner.path / "assets" / "foreign").write_bytes(b"foreign asset")
        elif change == "store-mode":
            (owner.path / "assets").chmod(0o750)
        elif change == "store-mtime":
            path = owner.path / "assets"
            info = path.stat()
            os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1))
        elif change == "store-emptied":
            path = owner.path / "assets" / "temporary"
            path.write_bytes(b"unknown temporary asset")
            path.unlink()
        else:
            info = (owner.path / "checkpoints").stat()
            history = checkpoints.Checkpoints(
                owner, assets.DirectoryIdentity(info.st_dev, info.st_ino)
            )
            result = history.commit({"protected": True}, expected=None, verify_state=lambda s: None)
            checkpoint.append(result.checkpoint.sha256)
        retained.append(header.read_bytes())

    with monkeypatch.context() as patch:
        selected, failures = close_fault(patch, owner, stage, mutate)
        with pytest.raises(project_header.HeaderError) as caught:
            project_header.Stores.provision(owner)
    assert failures and caught.value.__cause__ is selected
    assert header.read_bytes() == retained[0]
    assert all(
        (owner.path / name).is_dir()
        for name in ("assets", "checkpoints", "native-blobs", "packets")
    )
    if checkpoint:
        assert (owner.path / "checkpoints/current").readlink().name == checkpoint[0] + ".json"
    if change == "symlink":
        assert header.is_symlink()
    owner.verify()


@pytest.mark.parametrize(
    "stage", ["publisher-file", "publisher-root", "provision-root", "provision-parent"]
)
@pytest.mark.parametrize("change", ["root", "parent", "parent-same-root"])
def test_close_only_failure_retains_replaced_ancestry(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, stage: str, change: str
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
            selected, failures = close_fault(patch, owner, stage, mutate)
            with pytest.raises(project_header.HeaderError) as caught:
                project_header.Stores.provision(owner)
        assert failures and caught.value.__cause__ is selected
        retained = (
            owner.path
            if change == "parent-same-root"
            else moved
            if change == "root"
            else moved / owner.path.name
        )
        assert (retained / "project.json").is_file()
        if change == "parent-same-root":
            assert list(original.iterdir()) == [owner.path]
        else:
            assert list(original.iterdir()) == []
    finally:
        if moved.exists():
            if change == "parent-same-root":
                owner.path.rename(moved / owner.path.name)
            original.rmdir()
            moved.rename(original)
    owner.verify()


@pytest.mark.parametrize(
    "stage", ["publisher-file", "publisher-root", "provision-root", "provision-parent"]
)
@pytest.mark.parametrize("failure", ["reopen", "unlink", "rmdir", "close"])
def test_rollback_failure_keeps_first_close_error(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, stage: str, failure: str
) -> None:
    original_open, original_unlink, original_rmdir, original_close = (
        os.open,
        os.unlink,
        os.rmdir,
        os.close,
    )

    def denied_open(
        target: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        if target == owner.path.parent:
            raise PermissionError("rollback reopen denied")
        return original_open(target, flags, mode, dir_fd=dir_fd)

    def denied_unlink(target: Any, *, dir_fd: int | None = None) -> None:
        if target == "project.json":
            raise PermissionError("rollback unlink denied")
        original_unlink(target, dir_fd=dir_fd)

    def denied_rmdir(target: Any, *, dir_fd: int | None = None) -> None:
        if target in {"assets", "checkpoints", "native-blobs", "packets"}:
            raise PermissionError("rollback rmdir denied")
        original_rmdir(target, dir_fd=dir_fd)

    def denied_close(descriptor: int) -> None:
        original_close(descriptor)
        raise OSError("additional close failure after release")

    with monkeypatch.context() as patch:

        def mutate() -> None:
            patch.setattr(
                os,
                {"reopen": "open", "unlink": "unlink", "rmdir": "rmdir", "close": "close"}[failure],
                {
                    "reopen": denied_open,
                    "unlink": denied_unlink,
                    "rmdir": denied_rmdir,
                    "close": denied_close,
                }[failure],
            )

        selected, failures = close_fault(patch, owner, stage, mutate)
        with pytest.raises(project_header.HeaderError) as caught:
            project_header.Stores.provision(owner)
    assert failures and caught.value.__cause__ is selected
    if failure in {"reopen", "unlink"}:
        assert (owner.path / "project.json").is_file()
    elif failure == "rmdir":
        assert not (owner.path / "project.json").exists()
        assert (owner.path / "native-blobs").is_dir()
    else:
        assert {path.name for path in owner.path.iterdir()} == {"writer.lock"}
    assert any("cleanup" in note.lower() for note in getattr(caught.value, "__notes__", []))
    owner.verify()


@pytest.mark.parametrize(
    "stage", ["publisher-file", "publisher-root", "provision-root", "provision-parent"]
)
def test_failed_close_descriptor_number_is_never_retried(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    sentinel = owner.path.parent / "unrelated-descriptor"
    sentinel.write_bytes(b"unrelated live descriptor")
    held: list[int] = []
    original_open, original_close = os.open, os.close

    def after_release() -> None:
        held.append(original_open(sentinel, os.O_RDONLY | os.O_CLOEXEC))

    try:
        with monkeypatch.context() as patch:
            selected, failures = close_fault(patch, owner, stage, lambda: None, after_release)
            with pytest.raises(project_header.HeaderError) as caught:
                project_header.Stores.provision(owner)
        assert failures == held and caught.value.__cause__ is selected
        assert os.read(held[0], 100) == b"unrelated live descriptor"
        assert {path.name for path in owner.path.iterdir()} == {"writer.lock"}
    finally:
        for descriptor in held:
            original_close(descriptor)
    owner.verify()
