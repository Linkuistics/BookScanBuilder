"""Saved native identities, rather than fresh stats, own restarted store verification."""

import hashlib
import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest

from bookscan import assets, ownership


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    path = tmp_path / "Book project"
    path.mkdir()
    identity = ownership.provision(path)
    with ownership.Writer.acquire(path, identity) as writer:
        yield writer


def state_verifier(images: assets.Assets, state: dict[str, object]) -> None:
    if set(state) != {"baseline", "note"} or not isinstance(state["note"], str):
        raise ValueError("Invalid controlled semantic state")
    images.read(assets.RGBAsset.from_record(state["baseline"]))


def populate(owner: ownership.Writer) -> object:
    from bookscan import project_header

    stores = project_header.Stores.provision(owner)
    reference = stores.images.publish(bytes.fromhex("0001ff2a80fe"), (2, 1))

    def verify(state: dict[str, object]) -> None:
        state_verifier(stores.images, state)

    first = stores.checkpoints.commit(
        {"baseline": reference.record(), "note": "faint café"},
        expected=None,
        verify_state=verify,
    ).checkpoint
    stores.checkpoints.commit(
        {"baseline": reference.record(), "note": "second"},
        expected=first,
        verify_state=verify,
    )
    return stores


def test_header_reload_and_history_use_saved_identity(owner: ownership.Writer) -> None:
    from bookscan import project_header

    stores = cast(project_header.Stores, populate(owner))
    raw = (owner.path / "project.json").read_bytes()
    header = project_header.Header.from_json(raw)
    assert header == stores.header
    assert header.lock == owner.identity
    assert header.images == stores.images.identity
    assert header.checkpoints == stores.checkpoints.identity
    assert header.file.inode == (owner.path / "project.json").stat().st_ino
    assert header.record()["project_id"] == "project-" + owner.identity.token
    path = owner.path
    owner.close()
    with project_header.resume(
        path, verify_state=lambda stores, state: state_verifier(stores.images, state)
    ) as (loaded, current):
        assert loaded.header == header
        assert current.revision == 2 and current.state["note"] == "second"
        reference = assets.RGBAsset.from_record(current.state["baseline"])
        assert loaded.images.read(reference) == bytes.fromhex("0001ff2a80fe")
        with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
            ownership.Writer.acquire(path, header.lock)
        # A second descriptor's close does not release the owner.
        descriptor = os.open(path / "writer.lock", os.O_RDONLY)
        os.close(descriptor)
        with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
            ownership.Writer.acquire(path, header.lock)
    with ownership.Writer.acquire(path, header.lock):
        pass
    assert (path / "project.json").read_bytes() == raw


def test_caller_ownership_is_not_closed_or_reacquired(owner: ownership.Writer) -> None:
    from bookscan import project_header

    stores = project_header.Stores.provision(owner)
    stores.verify()
    owner.verify()
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)
    owner.verify()


@pytest.mark.parametrize("alias", ["parent", "project", "case"])
def test_resume_alias_uses_same_lock(owner: ownership.Writer, alias: str, tmp_path: Path) -> None:
    from bookscan import project_header

    stores = cast(project_header.Stores, populate(owner))
    if alias == "parent":
        parent = tmp_path / "linked parent"
        parent.symlink_to(tmp_path, target_is_directory=True)
        path = parent / owner.path.name
    elif alias == "project":
        path = tmp_path / "linked project"
        path.symlink_to(owner.path, target_is_directory=True)
    else:
        path = owner.path.with_name(owner.path.name.swapcase())
        if not path.exists():
            pytest.skip("Filesystem is case sensitive")
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        with project_header.resume(
            path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass
    owner.close()
    with project_header.resume(
        path, verify_state=lambda stores, state: state_verifier(stores.images, state)
    ) as (loaded, _):
        assert loaded.owner.path == stores.owner.path


@pytest.mark.parametrize("name", ["project.json", "assets", "checkpoints", "writer.lock"])
def test_identical_entry_replacement_fails_fresh_resume(owner: ownership.Writer, name: str) -> None:
    from bookscan import project_header

    stores = cast(project_header.Stores, populate(owner))
    path = owner.path / name
    old = path.with_name(name + "-old")
    path.rename(old)
    if old.is_dir():
        path.mkdir()
    else:
        path.write_bytes(old.read_bytes())
    before = {p.name for p in owner.path.iterdir()}
    with pytest.raises(
        (project_header.HeaderError, ownership.OwnershipError), match="INVALID_PROJECT"
    ):
        stores.verify()
    owner.close()
    with pytest.raises(
        (project_header.HeaderError, ownership.OwnershipError), match="INVALID_PROJECT"
    ):
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass
    assert {p.name for p in owner.path.iterdir()} == before


@pytest.mark.parametrize("kind", ["missing", "symlink", "hardlink", "fifo", "directory"])
def test_header_entry_types_never_follow_or_hang(owner: ownership.Writer, kind: str) -> None:
    from bookscan import project_header

    populate(owner)
    path = owner.path / "project.json"
    old = owner.path / "old.json"
    path.rename(old)
    if kind == "symlink":
        path.symlink_to(old)
    elif kind == "hardlink":
        os.link(old, path)
    elif kind == "fifo":
        os.mkfifo(path)
    elif kind == "directory":
        path.mkdir()
    with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass


@pytest.mark.parametrize(
    "field,value",
    [
        ("format", "unknown"),
        ("version", True),
        ("version", 2),
        ("project_id", "foreign"),
        ("required_capabilities", []),
        ("required_capabilities", ["future-edit-v1"]),
        ("required_capabilities", "baseline-rgb-v1"),
        ("required_capabilities", ["baseline-rgb-v1"] * 4),
        ("lock", []),
        ("assets", {"device": True, "inode": 5}),
        ("checkpoints", {"device": 1, "inode": "1"}),
        ("header", {"device": -1, "inode": 1}),
        ("semantic_unknown", True),
    ],
)
def test_incompatible_header_precedes_busy_lock_without_mutation(
    owner: ownership.Writer, field: str, value: object
) -> None:
    from bookscan import project_header

    populate(owner)
    path = owner.path / "project.json"
    data = json.loads(path.read_bytes())
    data[field] = value
    raw = json.dumps(data).encode()
    path.write_bytes(raw)
    before = {p.name for p in owner.path.iterdir()}
    with pytest.raises(project_header.HeaderError) as error:
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)
    assert "bookscan baseline create" in error.value.remediation
    assert "review facts" in error.value.remediation
    assert path.read_bytes() == raw and {p.name for p in owner.path.iterdir()} == before


@pytest.mark.parametrize("value", [True, -1, "1", 1.0, None])
def test_lock_identity_numbers_are_strict(owner: ownership.Writer, value: object) -> None:
    from bookscan import project_header

    stores = project_header.Stores.provision(owner)
    record = stores.header.record()
    lock = cast(dict[str, object], record["lock"])
    lock["lock_inode"] = value
    with pytest.raises(project_header.HeaderError):
        project_header.Header.from_json(json.dumps(record).encode())


@pytest.mark.parametrize("suffix", [b',"version":1}', b',"ignored":NaN}', rb',"note":"\ud800"}'])
def test_private_decoder_rejects_ambiguous_header(owner: ownership.Writer, suffix: bytes) -> None:
    from bookscan import project_header

    stores = project_header.Stores.provision(owner)
    raw = json.dumps(stores.header.record()).encode()[:-1] + suffix
    with pytest.raises(project_header.HeaderError, match="INVALID_PROJECT"):
        project_header.Header.from_json(raw)


def test_header_is_not_saved_state_and_orphans_are_not_promoted(owner: ownership.Writer) -> None:
    from bookscan import checkpoints, project_header

    stores = project_header.Stores.provision(owner)
    owner.close()
    with pytest.raises(checkpoints.CheckpointError, match="incomplete create"):
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass
    with ownership.Writer.acquire(owner.path, stores.header.lock):
        pass


def test_resume_verifier_reads_every_predecessor_and_failure_releases_lock(
    owner: ownership.Writer,
) -> None:
    from bookscan import project_header

    stores = cast(project_header.Stores, populate(owner))
    owner.close()
    seen: list[str] = []

    def verify(images: assets.Assets, state: dict[str, object]) -> None:
        state_verifier(images, state)
        seen.append(cast(str, state["note"]))
        if state["note"] == "faint café":
            raise ValueError("Bad predecessor semantics")

    with pytest.raises(ValueError, match="Bad predecessor"):
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: verify(stores.images, state)
        ):
            pass
    assert seen == ["second", "faint café"]
    with ownership.Writer.acquire(owner.path, stores.header.lock):
        pass


def test_missing_pixels_refuse_resume_without_original_source(owner: ownership.Writer) -> None:
    from bookscan import project_header

    stores = cast(project_header.Stores, populate(owner))
    for path in (owner.path / "assets").iterdir():
        path.unlink()
    owner.close()
    with pytest.raises(assets.AssetError, match="INVALID_PROJECT"):
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass
    with ownership.Writer.acquire(owner.path, stores.header.lock):
        pass


def test_header_changed_between_preflight_and_acquire_is_rejected(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    stores = cast(project_header.Stores, populate(owner))
    owner.close()
    original = ownership.Writer.acquire

    def change(path: Path, identity: ownership.LockIdentity) -> ownership.Writer:
        writer = original(path, identity)
        header = path / "project.json"
        header.write_bytes(header.read_bytes() + b" ")
        return writer

    monkeypatch.setattr(ownership.Writer, "acquire", change)
    with pytest.raises(project_header.HeaderError, match="changed"):
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass
    monkeypatch.setattr(ownership.Writer, "acquire", original)
    with ownership.Writer.acquire(owner.path, stores.header.lock):
        pass


def test_provision_refuses_occupied_header_without_replacing_it(owner: ownership.Writer) -> None:
    from bookscan import project_header

    header = owner.path / "project.json"
    header.symlink_to(owner.path / "absent")
    before = header.lstat()
    with pytest.raises(project_header.HeaderError) as error:
        project_header.Stores.provision(owner)
    assert (error.value.code, error.value.exit_code) == ("PROJECT_EXISTS", 4)
    assert header.lstat() == before
    assert not any(p.name.startswith(".header-") for p in owner.path.iterdir())


def test_short_writes_are_completed(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    original = os.write

    def short(descriptor: int, data: object) -> int:
        return original(descriptor, memoryview(cast(bytes, data))[:7])

    monkeypatch.setattr(os, "write", short)
    stores = project_header.Stores.provision(owner)
    stores.verify()


@pytest.mark.parametrize("phase", ["write", "fsync", "link"])
def test_header_io_failure_never_publishes_partial(
    owner: ownership.Writer, phase: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    def fail(*args: object, **kwargs: object) -> object:
        raise OSError("controlled " + phase)

    monkeypatch.setattr(os, phase, fail)
    with pytest.raises(project_header.HeaderError) as error:
        project_header.Stores.provision(owner)
    assert (error.value.code, error.value.exit_code) == ("WRITE_FAILED", 5)
    assert not (owner.path / "project.json").exists()
    assert not any(p.name.startswith(".header-") for p in owner.path.iterdir())


def test_zero_write_fails_without_header(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    def zero(*args: object) -> int:
        return 0

    monkeypatch.setattr(os, "write", zero)
    with pytest.raises(project_header.HeaderError, match="WRITE_FAILED"):
        project_header.Stores.provision(owner)
    assert not (owner.path / "project.json").exists()


def test_prelink_cancel_preserves_selected_cause_and_cleans_private(
    owner: ownership.Writer,
) -> None:
    from bookscan import project_header

    def cancel() -> None:
        if any(p.name.startswith(".header-") for p in owner.path.iterdir()):
            raise RuntimeError("selected cancellation")

    with pytest.raises(RuntimeError, match="selected cancellation"):
        project_header.Stores.provision(owner, check_cancel=cancel)
    assert not (owner.path / "project.json").exists()
    assert not any(p.name.startswith(".header-") for p in owner.path.iterdir())


def test_corrupt_store_after_checkpoint_is_not_a_successful_resume(owner: ownership.Writer) -> None:
    from bookscan import project_header

    stores = cast(project_header.Stores, populate(owner))
    path = owner.path / "checkpoints" / os.readlink(owner.path / "checkpoints" / "current")
    raw = path.read_bytes()
    path.write_bytes(b"{}")
    owner.close()
    from bookscan.checkpoints import CheckpointError

    with pytest.raises(CheckpointError, match="INVALID_PROJECT"):
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass
    assert hashlib.sha256(raw).hexdigest() == path.stem
    with ownership.Writer.acquire(owner.path, stores.header.lock):
        pass


def test_resume_close_failure_preserves_selected_semantic_error(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    stores = cast(project_header.Stores, populate(owner))
    owner.close()
    original = ownership.Writer.close

    def close(writer: ownership.Writer) -> None:
        original(writer)
        raise OSError("controlled writer close")

    def fail(images: assets.Assets, state: dict[str, object]) -> None:
        raise ValueError("selected semantic failure")

    monkeypatch.setattr(ownership.Writer, "close", close)
    with pytest.raises(ValueError, match="selected semantic failure") as error:
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: fail(stores.images, state)
        ):
            pass
    assert "controlled writer close" in " ".join(error.value.__notes__)
    monkeypatch.setattr(ownership.Writer, "close", original)
    with ownership.Writer.acquire(owner.path, stores.header.lock):
        pass


def test_header_read_close_failure_preserves_invalid_json(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    project_header.Stores.provision(owner)
    (owner.path / "project.json").write_bytes(b"not JSON")
    original = os.close

    def close(descriptor: int) -> None:
        original(descriptor)
        raise OSError("controlled read close")

    monkeypatch.setattr(os, "close", close)
    with pytest.raises(project_header.HeaderError, match="header JSON") as error:
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass
    assert "controlled read close" in " ".join(error.value.__notes__)


@pytest.mark.parametrize("phase", ["read", "stat"])
def test_header_read_io_fault_is_domain_error(
    owner: ownership.Writer, phase: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    populate(owner)

    def fail(*args: object, **kwargs: object) -> object:
        raise PermissionError("controlled read permission")

    monkeypatch.setattr(os, phase, fail)
    with pytest.raises(project_header.HeaderError) as error:
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)


def test_truncated_header_is_invalid(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    populate(owner)

    def empty(*args: object) -> bytes:
        return b""

    monkeypatch.setattr(os, "read", empty)
    with pytest.raises(project_header.HeaderError, match="Truncated"):
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass


def test_header_size_guard_refuses_before_read(owner: ownership.Writer) -> None:
    from bookscan import project_header

    populate(owner)
    (owner.path / "project.json").write_bytes(b" " * 16_385)
    with pytest.raises(project_header.HeaderError, match="size"):
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass


def test_double_provision_precedes_store_writes(owner: ownership.Writer) -> None:
    from bookscan import project_header

    stores = project_header.Stores.provision(owner)
    raw = (owner.path / "project.json").read_bytes()
    with pytest.raises(project_header.HeaderError, match="PROJECT_EXISTS"):
        project_header.Stores.provision(owner)
    stores.verify()
    assert (owner.path / "project.json").read_bytes() == raw


def test_foreign_private_replacement_is_neither_published_nor_deleted(
    owner: ownership.Writer,
) -> None:
    from bookscan import project_header

    replacement: Path | None = None

    def replace() -> None:
        nonlocal replacement
        for entry in owner.path.iterdir():
            if entry.name.startswith(".header-") and entry.stat().st_size and replacement is None:
                entry.rename(owner.path / "original-private")
                entry.write_bytes(b"foreign")
                replacement = entry

    with pytest.raises(project_header.HeaderError, match="replaced"):
        project_header.Stores.provision(owner, check_cancel=replace)
    assert replacement is not None and replacement.read_bytes() == b"foreign"
    assert not (owner.path / "project.json").exists()


def test_cancel_cleanup_cannot_delete_foreign_private_name(owner: ownership.Writer) -> None:
    from bookscan import project_header

    replacement: Path | None = None

    def replace_and_cancel() -> None:
        nonlocal replacement
        for entry in owner.path.iterdir():
            if entry.name.startswith(".header-"):
                entry.rename(owner.path / "owned-private")
                entry.write_bytes(b"foreign")
                replacement = entry
                raise RuntimeError("selected cancellation")

    with pytest.raises(RuntimeError, match="selected cancellation") as error:
        project_header.Stores.provision(owner, check_cancel=replace_and_cancel)
    assert replacement is not None and replacement.read_bytes() == b"foreign"
    assert "replaced" in " ".join(error.value.__notes__)
    assert not (owner.path / "project.json").exists()


def test_successful_read_descriptor_close_failure_is_domain_error(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    populate(owner)
    original = os.close

    def close(descriptor: int) -> None:
        original(descriptor)
        raise OSError("controlled successful read close")

    monkeypatch.setattr(os, "close", close)
    with pytest.raises(project_header.HeaderError) as error:
        with project_header.resume(
            owner.path, verify_state=lambda stores, state: state_verifier(stores.images, state)
        ):
            pass
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)


@pytest.mark.parametrize(
    "change",
    ["bytes", "size", "mode", "nanoseconds", "hardlink", "replacement", "symlink"],
)
def test_cancel_retains_changed_private_header(owner: ownership.Writer, change: str) -> None:
    from bookscan import project_header

    selected = RuntimeError("selected private-header cancellation")
    private: Path | None = None

    def cancel() -> None:
        nonlocal private
        for entry in owner.path.iterdir():
            if entry.name.startswith(".header-") and entry.stat().st_size:
                private = entry
                if change == "bytes":
                    raw = entry.read_bytes()
                    entry.write_bytes(b"!" + raw[1:])
                elif change == "size":
                    with entry.open("ab") as file:
                        file.write(b"!")
                elif change == "mode":
                    entry.chmod(0o400)
                elif change == "nanoseconds":
                    stamp = entry.stat()
                    os.utime(entry, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1))
                elif change == "hardlink":
                    os.link(entry, owner.path / "foreign-link")
                else:
                    entry.rename(owner.path / "original-private")
                    if change == "replacement":
                        entry.write_bytes(b"foreign header")
                    else:
                        entry.symlink_to(owner.path / "original-private")
                raise selected

    with pytest.raises(RuntimeError) as caught:
        project_header.Stores.provision(owner, check_cancel=cancel)
    assert caught.value is selected
    assert private is not None and private.exists()
    assert "Private header" in " ".join(getattr(selected, "__notes__", []))
    assert not (owner.path / "project.json").exists()


@pytest.mark.parametrize("change", ["root", "parent"])
def test_cancel_retains_private_header_after_ancestry_replacement(
    owner: ownership.Writer, change: str
) -> None:
    from bookscan import project_header

    selected = RuntimeError("selected ancestry cancellation")
    original = owner.path if change == "root" else owner.path.parent
    moved = original.with_name(original.name + "-moved")
    private_name: str | None = None

    def cancel() -> None:
        nonlocal private_name
        for entry in owner.path.iterdir():
            if entry.name.startswith(".header-") and entry.stat().st_size:
                private_name = entry.name
                original.rename(moved)
                original.mkdir()
                if change == "root":
                    # Copies of owned names do not grant ownership of a replacement root.
                    (original / "writer.lock").write_bytes(owner.identity.content)
                else:
                    # Even the original root at its old path has a different parent.
                    (moved / owner.path.name).rename(owner.path)
                raise selected

    try:
        with pytest.raises(RuntimeError) as caught:
            project_header.Stores.provision(owner, check_cancel=cancel)
        assert caught.value is selected
        retained = moved if change == "root" else owner.path
        assert private_name is not None and (retained / private_name).exists()
        assert "Private header" in " ".join(getattr(selected, "__notes__", []))
    finally:
        if moved.exists():
            if change == "root":
                (original / "writer.lock").unlink()
            else:
                owner.path.rename(moved / owner.path.name)
            original.rmdir()
            moved.rename(original)


@pytest.mark.parametrize("change", ["missing", "atime"])
def test_cancel_cleans_only_unchanged_private_header(owner: ownership.Writer, change: str) -> None:
    from bookscan import project_header

    selected = RuntimeError("selected clean cancellation")

    def cancel() -> None:
        for entry in owner.path.iterdir():
            if entry.name.startswith(".header-") and entry.stat().st_size:
                if change == "missing":
                    entry.unlink()
                else:
                    entry.read_bytes()
                raise selected

    with pytest.raises(RuntimeError) as caught:
        project_header.Stores.provision(owner, check_cancel=cancel)
    assert caught.value is selected
    assert not any(p.name.startswith(".header-") for p in owner.path.iterdir())
    assert not getattr(selected, "__notes__", [])
    assert not (owner.path / "project.json").exists()


@pytest.mark.parametrize("phase", ["created", "written"])
def test_private_header_with_unavailable_capture_is_retained(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    from bookscan import project_header

    original = os.fstat
    failed = False

    def fstat(descriptor: int) -> os.stat_result:
        nonlocal failed
        info = original(descriptor)
        for entry in owner.path.iterdir():
            if (
                entry.name.startswith(".header-")
                and entry.lstat().st_ino == info.st_ino
                and (info.st_size == 0 if phase == "created" else info.st_size > 0)
                and not failed
            ):
                failed = True
                raise OSError("selected unavailable capture")
        return info

    monkeypatch.setattr(os, "fstat", fstat)
    with pytest.raises(project_header.HeaderError) as caught:
        project_header.Stores.provision(owner)
    assert (caught.value.code, caught.value.exit_code) == ("WRITE_FAILED", 5)
    assert isinstance(caught.value.__cause__, OSError)
    assert str(caught.value.__cause__) == "selected unavailable capture"
    assert "Private header" in " ".join(getattr(caught.value.__cause__, "__notes__", []))
    assert any(p.name.startswith(".header-") for p in owner.path.iterdir())
    assert not (owner.path / "project.json").exists()


def test_cancel_after_short_header_write_cleans_completed_mutation(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    original = os.write
    selected = RuntimeError("selected short-write cancellation")

    def short(descriptor: int, data: bytes) -> int:
        return original(descriptor, memoryview(data)[:7])

    def cancel() -> None:
        for entry in owner.path.iterdir():
            if entry.name.startswith(".header-") and entry.stat().st_size:
                assert entry.stat().st_size == 7
                raise selected

    monkeypatch.setattr(os, "write", short)
    with pytest.raises(RuntimeError) as caught:
        project_header.Stores.provision(owner, check_cancel=cancel)
    assert caught.value is selected
    assert not getattr(selected, "__notes__", [])
    assert not any(p.name.startswith(".header-") for p in owner.path.iterdir())
    assert not (owner.path / "project.json").exists()


@pytest.mark.parametrize("fault", ["unlink", "close"])
def test_private_header_cleanup_preserves_selected_failure(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    from bookscan import project_header

    selected = RuntimeError("selected cleanup cancellation")
    unlink, close = os.unlink, os.close
    cancelled = False

    def cancel() -> None:
        nonlocal cancelled
        if any(p.name.startswith(".header-") for p in owner.path.iterdir()):
            cancelled = True
            raise selected

    def deny_unlink(path: str, *, dir_fd: int | None = None) -> None:
        if path.startswith(".header-"):
            raise PermissionError("controlled private unlink denial")
        unlink(path, dir_fd=dir_fd)

    def deny_close(descriptor: int) -> None:
        close(descriptor)
        if cancelled:
            raise OSError("controlled descriptor close")

    with monkeypatch.context() as patch:
        if fault == "unlink":
            patch.setattr(os, "unlink", deny_unlink)
        else:
            patch.setattr(os, "close", deny_close)
        with pytest.raises(RuntimeError) as caught:
            project_header.Stores.provision(owner, check_cancel=cancel)
    assert caught.value is selected
    assert "controlled" in " ".join(getattr(selected, "__notes__", []))
    assert any(p.name.startswith(".header-") for p in owner.path.iterdir()) == (fault == "unlink")
    assert not (owner.path / "project.json").exists()


def test_postlink_private_cleanup_failure_rolls_back_owned_header_names(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    def deny(*args: object) -> None:
        raise OSError("selected postlink unlink failure")

    monkeypatch.setattr(project_header, "_unlink", deny)
    with pytest.raises(project_header.HeaderError) as caught:
        project_header.Stores.provision(owner)
    assert (caught.value.code, caught.value.exit_code) == ("WRITE_FAILED", 5)
    assert {p.name for p in owner.path.iterdir()} == {"writer.lock"}
    assert not (owner.path / "checkpoints" / "current").exists()


@pytest.mark.parametrize(
    "stage", ["after-history", "header-write", "occupied-history", "occupied-native"]
)
def test_failed_provision_removes_only_returned_empty_stores(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    from bookscan import checkpoints, native_blobs, project_header

    selected = RuntimeError("selected provision cancellation")
    name = "checkpoints" if stage == "occupied-history" else "native-blobs"
    if stage.startswith("occupied-"):
        (owner.path / name).mkdir()
        (owner.path / name / "foreign").write_bytes(b"keep foreign store")

    def cancelled() -> None:
        if stage == "after-history" and (owner.path / "checkpoints").exists():
            raise selected

    def failed_write(descriptor: int, value: object) -> int:
        raise OSError("header write denied")

    if stage == "header-write":
        monkeypatch.setattr(project_header.os, "write", failed_write)
    error_types = (RuntimeError, project_header.HeaderError, checkpoints.CheckpointError)
    with pytest.raises(error_types) as caught:
        project_header.Stores.provision(owner, check_cancel=cancelled)
    if stage == "after-history":
        assert caught.value is selected
    elif stage == "header-write":
        assert isinstance(caught.value, project_header.HeaderError)
        assert caught.value.code == "WRITE_FAILED"
    elif stage == "occupied-native":
        assert isinstance(caught.value, project_header.HeaderError)
        assert isinstance(caught.value.__cause__, native_blobs.BlobError)
    expected = {"writer.lock"}
    if stage.startswith("occupied-"):
        expected.add(name)
        assert (owner.path / name / "foreign").read_bytes() == b"keep foreign store"
    assert {path.name for path in owner.path.iterdir()} == expected
    owner.verify()
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)


@pytest.mark.parametrize("change", ["nonempty", "replaced", "symlink", "missing"])
def test_failed_provision_preserves_unknown_store_entries(
    owner: ownership.Writer, change: str, tmp_path: Path
) -> None:
    from bookscan import project_header

    selected = RuntimeError("cancel with changed store")
    target = owner.path / "assets"
    moved = owner.path / "old-assets"
    foreign = tmp_path / "foreign-assets"
    foreign.mkdir()
    (foreign / "foreign").write_bytes(b"untouched")

    def cancelled() -> None:
        if not (owner.path / "checkpoints").exists():
            return
        if change == "nonempty":
            (target / "unknown").write_bytes(b"untouched")
        elif change in {"replaced", "symlink"}:
            target.rename(moved)
            if change == "replaced":
                target.mkdir()
            else:
                target.symlink_to(foreign, target_is_directory=True)
        else:
            target.rmdir()
        raise selected

    with pytest.raises(RuntimeError) as caught:
        project_header.Stores.provision(owner, check_cancel=cancelled)
    assert caught.value is selected
    assert not (owner.path / "checkpoints").exists()
    if change == "nonempty":
        assert (target / "unknown").read_bytes() == b"untouched"
    elif change in {"replaced", "symlink"}:
        assert moved.is_dir() and target.exists()
        assert target.is_symlink() == (change == "symlink")
    else:
        assert not target.exists()
    assert (foreign / "foreign").read_bytes() == b"untouched"
    owner.verify()


def test_failed_provision_rolls_back_unchanged_published_header_and_stores(
    owner: ownership.Writer,
) -> None:
    from bookscan import project_header

    selected = RuntimeError("cancel after published header")

    def cancelled() -> None:
        if (owner.path / "project.json").exists():
            raise selected

    with pytest.raises(RuntimeError) as caught:
        project_header.Stores.provision(owner, check_cancel=cancelled)
    assert caught.value is selected
    assert {path.name for path in owner.path.iterdir()} == {"writer.lock"}
    owner.verify()


def test_failed_provision_cleanup_error_keeps_selected_failure(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import project_header

    selected = RuntimeError("selected cancellation survives cleanup denial")
    original = os.rmdir

    def denied(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes], *, dir_fd: int | None = None
    ) -> None:
        if path == "assets":
            raise PermissionError("empty store cleanup denied")
        original(path, dir_fd=dir_fd)

    def cancelled() -> None:
        if (owner.path / "checkpoints").exists():
            raise selected

    monkeypatch.setattr(os, "rmdir", denied)
    with pytest.raises(RuntimeError) as caught:
        project_header.Stores.provision(owner, check_cancel=cancelled)
    assert caught.value is selected
    assert (owner.path / "assets").is_dir()
    assert not (owner.path / "checkpoints").exists()
    assert any("cleanup" in note.lower() for note in getattr(selected, "__notes__", []))
    owner.verify()


@pytest.mark.parametrize("ancestry", ["root", "parent"])
def test_failed_provision_retains_stores_after_ancestry_replacement(
    owner: ownership.Writer, ancestry: str
) -> None:
    from bookscan import project_header

    selected = RuntimeError("cancel after ancestry replacement")
    original = owner.path if ancestry == "root" else owner.path.parent
    moved = original.with_name(original.name + "-moved")
    retained = moved if ancestry == "root" else moved / owner.path.name

    def cancelled() -> None:
        if not (owner.path / "checkpoints").exists():
            return
        original.rename(moved)
        original.mkdir()
        raise selected

    try:
        with pytest.raises(RuntimeError) as caught:
            project_header.Stores.provision(owner, check_cancel=cancelled)
        assert caught.value is selected
        assert {path.name for path in retained.iterdir()} == {
            "writer.lock",
            "assets",
            "checkpoints",
        }
        assert list(original.iterdir()) == []
        assert any("cleanup" in note.lower() for note in getattr(selected, "__notes__", []))
    finally:
        if moved.exists():
            original.rmdir()
            moved.rename(original)
    owner.verify()


def test_failed_provision_preserves_unreturned_store_identity(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import checkpoints, project_header

    selected = RuntimeError("store failed before returning cleanup identity")

    def failed_store(writer: ownership.Writer) -> checkpoints.Checkpoints:
        (writer.path / "checkpoints").mkdir()
        raise selected

    monkeypatch.setattr(checkpoints.Checkpoints, "provision", failed_store)
    with pytest.raises(RuntimeError) as caught:
        project_header.Stores.provision(owner)
    assert caught.value is selected
    assert {path.name for path in owner.path.iterdir()} == {"writer.lock", "checkpoints"}
    owner.verify()


@pytest.mark.parametrize("mutation", ["mode", "mtime", "populated-then-emptied"])
def test_failed_provision_keeps_mutated_empty_store(owner: ownership.Writer, mutation: str) -> None:
    from bookscan import project_header

    selected = RuntimeError("cancel with mutated empty store")
    path = owner.path / "assets"
    retained: os.stat_result | None = None

    def cancelled() -> None:
        nonlocal retained
        if not (owner.path / "checkpoints").exists():
            return
        before = path.stat()
        if mutation == "mode":
            path.chmod(0o750)
        elif mutation == "mtime":
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000))
        else:
            child = path / "unknown"
            child.write_bytes(b"foreign mutation")
            child.unlink()
        retained = path.stat()
        raise selected

    with pytest.raises(RuntimeError) as caught:
        project_header.Stores.provision(owner, check_cancel=cancelled)
    assert caught.value is selected
    assert not (owner.path / "checkpoints").exists()
    assert path.is_dir() and retained is not None
    current = path.stat()
    assert (current.st_ino, current.st_mode, current.st_mtime_ns, current.st_ctime_ns) == (
        retained.st_ino,
        retained.st_mode,
        retained.st_mtime_ns,
        retained.st_ctime_ns,
    )
    assert any("assets" in note for note in getattr(selected, "__notes__", []))
    owner.verify()
