"""Real files expose premature commits, corrupt history and unsafe pointer replacement."""

import hashlib
import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from bookscan import assets, ownership


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    project = tmp_path / "Book project"
    project.mkdir()
    identity = ownership.provision(project)
    with ownership.Writer.acquire(project, identity) as writer:
        yield writer


def verify(state: dict[str, object]) -> None:
    if set(state) != {"note"} or not isinstance(state["note"], str):
        raise ValueError("Invalid controlled state")


def test_initial_commit_and_restart_keep_exact_state(owner: ownership.Writer) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    state: dict[str, object] = {"note": "faint café"}
    result = store.commit(state, expected=None, verify_state=verify)
    assert result.committed and not result.warnings
    assert result.checkpoint.revision == 1
    assert result.checkpoint.previous is None
    assert result.checkpoint.state == state
    state["note"] = "caller mutation"
    first = result.checkpoint
    loaded = checkpoints.Checkpoints(owner, store.identity).load(verify_state=verify)
    assert loaded == first and loaded.state == {"note": "faint café"}
    loaded.state["note"] = "reader mutation"
    assert loaded.state == {"note": "faint café"}
    assert (owner.path / "checkpoints" / (first.sha256 + ".json")).read_bytes() == first.raw
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)


def test_update_preserves_predecessor_and_rejects_old_expectation(owner: ownership.Writer) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    second = store.commit({"note": "second"}, expected=first, verify_state=verify).checkpoint
    assert (second.revision, second.previous) == (2, first.sha256)
    assert store.load(verify_state=verify) == second
    old = owner.path / "checkpoints" / (first.sha256 + ".json")
    old_bytes = old.read_bytes()
    with pytest.raises(checkpoints.CheckpointError) as error:
        store.commit({"note": "stale"}, expected=first, verify_state=verify)
    assert (error.value.code, error.value.exit_code, error.value.committed) == (
        "STALE_ACTION",
        6,
        False,
    )
    assert old.read_bytes() == old_bytes and store.load(verify_state=verify) == second
    with pytest.raises(checkpoints.CheckpointError, match="STALE_ACTION"):
        store.commit({"note": "second initial"}, expected=None, verify_state=verify)


def test_no_pointer_means_no_saved_state_even_with_complete_orphan(owner: ownership.Writer) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "orphan"}, expected=None, verify_state=verify).checkpoint
    (owner.path / "checkpoints" / "current").unlink()
    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.load(verify_state=verify)
    assert (owner.path / "checkpoints" / (first.sha256 + ".json")).read_bytes() == first.raw


@pytest.mark.parametrize("kind", ["directory", "file", "absolute", "escape", "dangling", "fifo"])
def test_invalid_current_never_redirects_or_repairs(owner: ownership.Writer, kind: str) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    path = owner.path / "checkpoints" / "current"
    if kind == "directory":
        path.mkdir()
    elif kind == "file":
        path.write_text("not a pointer")
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        path.symlink_to(
            "/tmp/foreign.json"
            if kind == "absolute"
            else "../outside"
            if kind == "escape"
            else "a" * 64 + ".json"
        )
    before = path.lstat()
    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.load(verify_state=verify)
    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.commit({"note": "repair"}, expected=None, verify_state=verify)
    assert path.lstat() == before


@pytest.mark.parametrize("kind", ["bytes", "missing", "symlink", "hardlink", "fifo"])
def test_corrupt_current_or_predecessor_refused(owner: ownership.Writer, kind: str) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    second = store.commit({"note": "second"}, expected=first, verify_state=verify).checkpoint
    path = owner.path / "checkpoints" / (first.sha256 + ".json")
    if kind == "bytes":
        path.write_bytes(b"{}")
    else:
        original = owner.path / "predecessor.json"
        path.rename(original)
        if kind == "symlink":
            path.symlink_to(original)
        elif kind == "hardlink":
            os.link(original, path)
        elif kind == "fifo":
            os.mkfifo(path)
    current = os.readlink(owner.path / "checkpoints" / "current")
    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.load(verify_state=verify)
    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.commit({"note": "repair"}, expected=second, verify_state=verify)
    assert os.readlink(owner.path / "checkpoints" / "current") == current


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", True),
        ("version", 2),
        ("format", "foreign"),
        ("required_capabilities", ["baseline-rgb-v1", "future-edit-v1"]),
        ("required_capabilities", []),
        ("required_capabilities", "baseline-rgb-v1"),
        ("checkpoint_revision", True),
        ("checkpoint_revision", 0),
        ("checkpoint_revision", "1"),
        ("checkpoint_revision", 2),
        ("project_id", "foreign"),
        ("previous_sha256", "../escape"),
        ("previous_sha256", "f" * 64),
        ("state", []),
        ("semantic_unknown", True),
    ],
)
def test_hash_valid_unknown_or_inconsistent_record_refused(
    owner: ownership.Writer, field: str, value: object
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    data = json.loads(first.raw)
    data[field] = value
    raw = json.dumps(data).encode()
    digest = hashlib.sha256(raw).hexdigest()
    directory = owner.path / "checkpoints"
    (directory / (digest + ".json")).write_bytes(raw)
    (directory / "current").unlink()
    (directory / "current").symlink_to(digest + ".json")
    before = set(directory.iterdir())
    with pytest.raises(checkpoints.CheckpointError) as error:
        store.load(verify_state=verify)
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)
    assert set(directory.iterdir()) == before


def test_duplicate_json_key_is_not_a_valid_saved_checkpoint(owner: ownership.Writer) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    raw = first.raw[:-1] + b',"version":1}'
    digest = hashlib.sha256(raw).hexdigest()
    directory = owner.path / "checkpoints"
    (directory / (digest + ".json")).write_bytes(raw)
    (directory / "current").unlink()
    (directory / "current").symlink_to(digest + ".json")
    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.load(verify_state=verify)


def test_referenced_pixels_verified_before_commit_and_on_history_read(
    owner: ownership.Writer,
) -> None:
    from bookscan import checkpoints

    images = assets.Assets.provision(owner)
    rgb = bytes((0, 1, 255, 42, 128, 254))
    reference = images.publish(rgb, (2, 1))
    store = checkpoints.Checkpoints.provision(owner)

    def exact(state: dict[str, object]) -> None:
        assert images.read(assets.RGBAsset.from_record(state["baseline"])) == rgb

    first = store.commit(
        {"baseline": reference.record()}, expected=None, verify_state=exact
    ).checkpoint
    # The current state can use another asset; all referenced predecessors still verify.
    next_reference = images.publish(b"xyz", (1, 1))

    def any_rgb(state: dict[str, object]) -> None:
        images.read(assets.RGBAsset.from_record(state["baseline"]))

    second = store.commit(
        {"baseline": next_reference.record()}, expected=first, verify_state=any_rgb
    ).checkpoint
    (owner.path / "assets" / (reference.id + ".png")).unlink()
    with pytest.raises(assets.AssetError, match="INVALID_PROJECT"):
        store.load(verify_state=any_rgb)
    assert (owner.path / "checkpoints" / (second.sha256 + ".json")).read_bytes() == second.raw


def test_semantic_verification_failure_does_not_commit(owner: ownership.Writer) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    with pytest.raises(ValueError, match="controlled state"):
        store.commit({"note": 4}, expected=None, verify_state=verify)
    assert not list((owner.path / "checkpoints").iterdir())


@pytest.mark.parametrize("phase", ["write", "link", "pointer"])
def test_precommit_io_failure_preserves_current(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    foreign = owner.path / "checkpoints" / ".foreign"
    foreign.write_bytes(b"keep")

    def failed(*args: object, **kwargs: object) -> None:
        raise OSError("controlled I/O")

    monkeypatch.setattr(
        checkpoints.os, {"write": "write", "link": "link", "pointer": "replace"}[phase], failed
    )
    with pytest.raises(checkpoints.CheckpointError) as error:
        store.commit({"note": "next"}, expected=first, verify_state=verify)
    assert (error.value.exit_code, error.value.committed) == (5, False)
    assert store.load(verify_state=verify) == first
    assert foreign.read_bytes() == b"keep"


def test_failed_checkpoint_link_cleanup_does_not_commit(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)

    def failed(*args: object, **kwargs: object) -> None:
        raise OSError("controlled cleanup")

    # The immutable record's private link is cleaned before pointer commit, so
    # use update staging's pointer-cleanup boundary after a failed rename test below.
    result = store.commit({"note": "first"}, expected=None, verify_state=verify)
    first = result.checkpoint
    unlink = os.unlink

    def only_checkpoint(src: str, *, dir_fd: int) -> None:
        if src.startswith(".checkpoint-"):
            failed()
        unlink(src, dir_fd=dir_fd)

    monkeypatch.setattr(checkpoints.os, "unlink", only_checkpoint)
    # Failure to remove a private hard link must prevent treating a multiply-linked
    # checkpoint as saved. Selected state remains authoritative, with no new commit.
    with pytest.raises(checkpoints.CheckpointError):
        store.commit({"note": "second"}, expected=first, verify_state=verify)
    assert store.load(verify_state=verify) == first


def test_cancellation_before_pointer_keeps_predecessor(
    owner: ownership.Writer,
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint

    def cancelled() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        store.commit(
            {"note": "second"}, expected=first, verify_state=verify, check_cancel=cancelled
        )
    assert store.load(verify_state=verify) == first


@pytest.mark.parametrize("kind", ["directory", "symlink", "missing"])
def test_replaced_checkpoint_directory_refused(owner: ownership.Writer, kind: str) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    path = owner.path / "checkpoints"
    path.rename(owner.path / "old-checkpoints")
    if kind == "directory":
        path.mkdir()
    elif kind == "symlink":
        path.symlink_to(owner.path / "old-checkpoints", target_is_directory=True)
    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.load(verify_state=verify)
    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.commit({"note": "second"}, expected=first, verify_state=verify)


def test_closed_owner_and_occupied_store_refused(owner: ownership.Writer) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    with pytest.raises(checkpoints.CheckpointError):
        checkpoints.Checkpoints.provision(owner)
    owner.close()
    with pytest.raises(ownership.OwnershipError):
        store.load(verify_state=verify)


def test_postcommit_close_failure_keeps_committed_fact_and_warning(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    close = os.close

    def failed(descriptor: int) -> None:
        info = os.fstat(descriptor)
        close(descriptor)
        if (info.st_dev, info.st_ino) == (store.identity.device, store.identity.inode):
            raise OSError("controlled descriptor cleanup")

    monkeypatch.setattr(checkpoints.os, "close", failed)
    result = store.commit({"note": "saved"}, expected=None, verify_state=verify)
    assert result.committed and any("CLEANUP" in warning for warning in result.warnings)
    monkeypatch.undo()
    assert store.load(verify_state=verify).state == {"note": "saved"}


def test_initial_pointer_concurrent_occupant_is_not_replaced(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    symlink = os.symlink

    def occupied(src: str, dst: str, *, dir_fd: int) -> None:
        if dst == "current":
            (owner.path / "checkpoints" / "current").write_bytes(b"foreign")
        symlink(src, dst, dir_fd=dir_fd)

    monkeypatch.setattr(checkpoints.os, "symlink", occupied)
    with pytest.raises(checkpoints.CheckpointError) as error:
        store.commit({"note": "first"}, expected=None, verify_state=verify)
    assert (error.value.code, error.value.committed) == ("INVALID_PROJECT", False)
    assert (owner.path / "checkpoints" / "current").read_bytes() == b"foreign"


def test_pointer_replacement_during_state_verification_is_not_overwritten(
    owner: ownership.Writer,
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    pointer = owner.path / "checkpoints" / "current"

    def replaced(state: dict[str, object]) -> None:
        verify(state)
        if state["note"] == "next":
            pointer.unlink()
            pointer.write_bytes(b"foreign")

    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.commit({"note": "next"}, expected=first, verify_state=replaced)
    assert pointer.read_bytes() == b"foreign"


def test_short_write_is_completed_and_zero_write_never_commits(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    write = os.write

    def short(descriptor: int, data: memoryview) -> int:
        return write(descriptor, data[:7])

    monkeypatch.setattr(checkpoints.os, "write", short)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    assert store.load(verify_state=verify).state == {"note": "first"}

    def zero(descriptor: int, data: memoryview) -> int:
        return 0

    monkeypatch.setattr(checkpoints.os, "write", zero)
    with pytest.raises(checkpoints.CheckpointError) as error:
        store.commit({"note": "second"}, expected=first, verify_state=verify)
    assert (error.value.exit_code, error.value.committed) == (5, False)
    assert store.load(verify_state=verify) == first


def test_saved_state_verifier_runs_on_new_and_every_predecessor(owner: ownership.Writer) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    store.commit({"note": "second"}, expected=first, verify_state=verify)

    def reject_old(state: dict[str, object]) -> None:
        if state["note"] == "first":
            raise ValueError("predecessor semantic failure")

    with pytest.raises(ValueError, match="predecessor semantic"):
        store.load(verify_state=reject_old)


def test_selected_cancellation_survives_descriptor_cleanup_failure(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    close = os.close

    def failed(descriptor: int) -> None:
        close(descriptor)
        raise OSError("controlled close failure")

    def interrupted() -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(checkpoints.os, "close", failed)
    with pytest.raises(KeyboardInterrupt) as error:
        store.commit(
            {"note": "never saved"}, expected=None, verify_state=verify, check_cancel=interrupted
        )
    assert "close" in " ".join(error.value.__notes__)
    monkeypatch.undo()
    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.load(verify_state=verify)


def test_replaced_private_pointer_does_not_commit_or_delete_foreign_name(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    symlink = os.symlink
    foreign: list[Path] = []

    def replaced(src: str, dst: str, *, dir_fd: int) -> None:
        symlink(src, dst, dir_fd=dir_fd)
        if dst.startswith(".current-"):
            path = owner.path / "checkpoints" / dst
            path.unlink()
            path.write_bytes(b"foreign")
            foreign.append(path)

    monkeypatch.setattr(checkpoints.os, "symlink", replaced)
    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.commit({"note": "second"}, expected=first, verify_state=verify)
    assert store.load(verify_state=verify) == first
    assert len(foreign) == 1 and foreign[0].read_bytes() == b"foreign"


def test_corruption_observed_after_commit_keeps_committed_fact(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    replace = os.replace

    def changed(src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int) -> None:
        replace(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)
        path = owner.path / "checkpoints"
        path.rename(owner.path / "committed-checkpoints")
        path.mkdir()

    monkeypatch.setattr(checkpoints.os, "replace", changed)
    with pytest.raises(checkpoints.CheckpointError) as error:
        store.commit({"note": "second"}, expected=first, verify_state=verify)
    assert (error.value.code, error.value.committed) == ("INVALID_PROJECT", True)
    pointer = owner.path / "committed-checkpoints" / "current"
    raw = pointer.read_bytes()
    assert json.loads(raw)["checkpoint_revision"] == 2


def test_wrong_staged_disk_bytes_never_choose_checkpoint(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    write = os.write

    def corrupt(descriptor: int, data: memoryview) -> int:
        changed = bytearray(data)
        changed[-1] ^= 1
        return write(descriptor, changed)

    monkeypatch.setattr(checkpoints.os, "write", corrupt)
    with pytest.raises(checkpoints.CheckpointError, match="INVALID_PROJECT"):
        store.commit({"note": "first"}, expected=None, verify_state=verify)
    assert not os.path.lexists(owner.path / "checkpoints" / "current")


@pytest.mark.parametrize("kind", ["directory-missing", "lock-changed"])
def test_postcommit_verification_failure_is_not_a_cleanup_warning(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    replace = os.replace

    def changed(src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int) -> None:
        replace(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)
        if kind == "directory-missing":
            (owner.path / "checkpoints").rename(owner.path / "committed-checkpoints")
        else:
            (owner.path / "writer.lock").write_bytes(b"foreign")

    monkeypatch.setattr(checkpoints.os, "replace", changed)
    with pytest.raises(checkpoints.CheckpointError) as error:
        store.commit({"note": "second"}, expected=first, verify_state=verify)
    assert (error.value.code, error.value.exit_code, error.value.committed) == (
        "INVALID_PROJECT",
        3,
        True,
    )


def test_unreadable_pointer_returns_domain_corruption_without_mutation(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint
    readlink = os.readlink
    original = readlink(owner.path / "checkpoints" / "current")

    def denied(path: str, *, dir_fd: int) -> str:
        raise PermissionError("controlled pointer read")

    monkeypatch.setattr(checkpoints.os, "readlink", denied)
    with pytest.raises(checkpoints.CheckpointError) as error:
        store.load(verify_state=verify)
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)
    with pytest.raises(checkpoints.CheckpointError) as error:
        store.commit({"note": "second"}, expected=first, verify_state=verify)
    assert (error.value.code, error.value.exit_code, error.value.committed) == (
        "INVALID_PROJECT",
        3,
        False,
    )
    assert readlink(owner.path / "checkpoints" / "current") == original


def test_selected_io_error_survives_lost_ownership_during_pointer_cleanup(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import checkpoints

    store = checkpoints.Checkpoints.provision(owner)
    first = store.commit({"note": "first"}, expected=None, verify_state=verify).checkpoint

    def failed(src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int) -> None:
        (owner.path / "writer.lock").write_bytes(b"foreign")
        raise OSError("selected pointer I/O failure")

    monkeypatch.setattr(checkpoints.os, "replace", failed)
    with pytest.raises(checkpoints.CheckpointError) as error:
        store.commit({"note": "second"}, expected=first, verify_state=verify)
    assert (error.value.code, error.value.exit_code, error.value.committed) == (
        "WRITE_FAILED",
        5,
        False,
    )
    assert "selected pointer I/O" in str(error.value.__cause__)
