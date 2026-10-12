"""Opaque native bytes cannot be repaired, aliased or promoted to accepted state.

Dropping digest/length checks, caller ownership or no-clobber publication must
break literal-byte cases. Real files/locks/checkpoints exercise saved history.
"""

import hashlib
import json
import os
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from test_native_sample_record import indexed

from bookscan import checkpoints, native_sample_record, ownership
from bookscan import native_blobs as module


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    project = tmp_path / "Book project"
    project.mkdir()
    identity = ownership.provision(project)
    with ownership.Writer.acquire(project, identity) as writer:
        yield writer


@pytest.mark.parametrize("raw", [b"", bytes(range(256)) * 3, b"malformed ICC\x00\xff"])
def test_exact_opaque_bytes_deduplicate_under_existing_owner(
    owner: ownership.Writer, raw: bytes
) -> None:
    store = module.Blobs.provision(owner)
    reference = store.publish(raw)
    assert reference.record() == {
        "format": "BookScanBuilderNativeBlob",
        "version": 1,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_size": len(raw),
    }
    path = owner.path / "native-blobs" / (reference.sha256 + ".bin")
    before = path.stat()
    assert store.read(module.Blob.from_record(json.loads(json.dumps(reference.record())))) == raw
    assert store.publish(raw) == reference
    assert path.stat().st_ino == before.st_ino and path.stat().st_nlink == 1
    assert set(p.name for p in path.parent.iterdir()) == {path.name}
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)


@pytest.mark.parametrize(
    "field,value",
    [
        ("format", "other"),
        ("version", True),
        ("version", 2),
        ("sha256", "../outside"),
        ("sha256", "A" * 64),
        ("sha256", 1),
        ("byte_size", True),
        ("byte_size", -1),
        ("byte_size", 3.0),
        ("extra", None),
    ],
)
def test_saved_reference_refuses_types_versions_and_extra_fields(field: str, value: object) -> None:
    record: dict[str, object] = {
        "format": "BookScanBuilderNativeBlob",
        "version": 1,
        "sha256": hashlib.sha256(b"abc").hexdigest(),
        "byte_size": 3,
    }
    record[field] = value
    with pytest.raises(module.BlobError) as error:
        module.Blob.from_record(record)
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)


@pytest.mark.parametrize("record", [None, [], "abc", {}, {"sha256": "a" * 64}])
def test_saved_reference_is_complete_object(record: object) -> None:
    with pytest.raises(module.BlobError):
        module.Blob.from_record(record)


@pytest.mark.parametrize("field,value", [("sha256", "../escape"), ("byte_size", True)])
def test_direct_reference_is_verified_before_path_use(
    owner: ownership.Writer, field: str, value: object
) -> None:
    store = module.Blobs.provision(owner)
    reference = store.publish(b"abc")
    with pytest.raises(module.BlobError):
        store.read(replace(reference, **{field: value}))


@pytest.mark.parametrize(
    "kind", ["bytes", "length", "symlink", "hardlink", "fifo", "directory", "missing"]
)
def test_changed_missing_or_aliased_blob_refused_without_repair(
    owner: ownership.Writer, kind: str
) -> None:
    store = module.Blobs.provision(owner)
    reference = store.publish(b"abc")
    path = owner.path / "native-blobs" / (reference.sha256 + ".bin")
    if kind in {"bytes", "length"}:
        path.write_bytes(b"abd" if kind == "bytes" else b"abcd")
    elif kind == "hardlink":
        os.link(path, owner.path / "alias")
    else:
        path.rename(owner.path / "original")
        if kind == "symlink":
            path.symlink_to(owner.path / "original")
        elif kind == "fifo":
            os.mkfifo(path)
        elif kind == "directory":
            path.mkdir()
    before = path.lstat() if kind != "missing" else None
    with pytest.raises(module.BlobError) as error:
        store.read(reference)
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)
    if kind != "missing":
        with pytest.raises(module.BlobError):
            store.publish(b"abc")
    assert (path.lstat() if kind != "missing" else None) == before


@pytest.mark.parametrize("kind", ["directory", "symlink", "missing"])
def test_saved_directory_identity_prevents_redirected_read_or_write(
    owner: ownership.Writer, kind: str
) -> None:
    store = module.Blobs.provision(owner)
    reference = store.publish(b"abc")
    path = owner.path / "native-blobs"
    path.rename(owner.path / "old-blobs")
    if kind == "directory":
        path.mkdir()
    elif kind == "symlink":
        path.symlink_to(owner.path / "old-blobs", target_is_directory=True)
    with pytest.raises(module.BlobError):
        store.read(reference)
    with pytest.raises(module.BlobError):
        store.publish(b"new")
    if kind == "directory":
        assert not list(path.iterdir())
    assert len(list((owner.path / "old-blobs").iterdir())) == 1


def test_closed_owner_and_occupied_directory_are_not_repaired(owner: ownership.Writer) -> None:
    store = module.Blobs.provision(owner)
    reference = store.publish(b"abc")
    with pytest.raises(module.BlobError):
        module.Blobs.provision(owner)
    owner.close()
    with pytest.raises(ownership.OwnershipError):
        store.read(reference)
    with pytest.raises(ownership.OwnershipError):
        store.publish(b"abc")


@pytest.mark.parametrize("raw", [None, bytearray(b"abc"), "abc", 3])
def test_publish_refuses_nonimmutable_input_before_creating_names(
    owner: ownership.Writer, raw: object
) -> None:
    store = module.Blobs.provision(owner)
    with pytest.raises(module.BlobError) as error:
        store.publish(cast(bytes, raw))
    assert (error.value.code, error.value.exit_code) == ("WRITE_FAILED", 5)
    assert not list((owner.path / "native-blobs").iterdir())


def test_wrong_staged_disk_bytes_never_publish(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = module.Blobs.provision(owner)
    original = os.write

    def wrong(descriptor: int, data: memoryview) -> int:
        raw = bytearray(data)
        raw[-1] ^= 1
        return original(descriptor, raw)

    monkeypatch.setattr(module.os, "write", wrong)
    with pytest.raises(module.BlobError):
        store.publish(b"abc")
    assert not list((owner.path / "native-blobs").iterdir())


@pytest.mark.parametrize("after_link", [False, True])
def test_interruption_cleans_only_owned_private_name(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, after_link: bool
) -> None:
    store = module.Blobs.provision(owner)
    foreign = owner.path / "native-blobs" / ".foreign-private"
    foreign.write_bytes(b"keep")
    original = os.link

    def interrupted(
        src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int, follow_symlinks: bool
    ) -> None:
        if after_link:
            original(
                src,
                dst,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=dst_dir_fd,
                follow_symlinks=follow_symlinks,
            )
        raise KeyboardInterrupt

    monkeypatch.setattr(module.os, "link", interrupted)
    with pytest.raises(KeyboardInterrupt):
        store.publish(b"abc")
    assert foreign.read_bytes() == b"keep"
    others = [p for p in foreign.parent.iterdir() if p != foreign]
    assert len(others) == int(after_link)
    if after_link:
        assert others[0].read_bytes() == b"abc" and others[0].stat().st_nlink == 1


def test_cleanup_failure_preserves_selected_interruption(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = module.Blobs.provision(owner)

    def interrupted(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt

    def failed(*args: object, **kwargs: object) -> None:
        raise OSError("controlled cleanup failure")

    monkeypatch.setattr(module.os, "link", interrupted)
    monkeypatch.setattr(module.os, "unlink", failed)
    with pytest.raises(KeyboardInterrupt) as error:
        store.publish(b"abc")
    assert "cleanup" in " ".join(error.value.__notes__)
    assert all(p.name.startswith(".blob-") for p in (owner.path / "native-blobs").iterdir())


def test_saved_sample_and_every_history_reference_require_exact_blobs(
    owner: ownership.Writer,
) -> None:
    store = module.Blobs.provision(owner)
    history = checkpoints.Checkpoints.provision(owner)
    value, placed, raw = indexed()
    references = {digest: store.publish(data) for digest, data in raw.items()}
    first_state: dict[str, object] = {
        "sample": value,
        "blobs": [ref.record() for ref in references.values()],
    }

    def verify(state: dict[str, object]) -> None:
        items = state["blobs"]
        assert isinstance(items, list)
        refs = [module.Blob.from_record(item) for item in cast(list[object], items)]
        retained = {ref.sha256: store.read(ref) for ref in refs}
        native_sample_record.restore(state["sample"], placed, read_blob=retained.__getitem__)

    first = history.commit(first_state, expected=None, verify_state=verify).checkpoint
    current = history.commit(first_state, expected=first, verify_state=verify).checkpoint
    assert history.load(verify_state=verify) == current
    # Every history reference must retain its exact referenced bytes.
    profile = next(ref for digest, ref in references.items() if raw[digest].startswith(b"Retained"))
    path = owner.path / "native-blobs" / (profile.sha256 + ".bin")
    path.write_bytes(b"X" * profile.byte_size)
    before = {p: p.read_bytes() for p in (owner.path / "checkpoints").glob("*.json")}
    with pytest.raises(module.BlobError):
        history.load(verify_state=verify)
    with pytest.raises(module.BlobError):
        history.commit(first_state, expected=current, verify_state=verify)
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("bad_predecessor", [False, True])
def test_hash_valid_history_cannot_hide_a_bad_native_reference(
    tmp_path: Path, bad_predecessor: bool
) -> None:
    path = tmp_path / "project"
    path.mkdir()
    identity = ownership.provision(path)
    with ownership.Writer.acquire(path, identity) as writer:
        store = module.Blobs.provision(writer)
        history = checkpoints.Checkpoints.provision(writer)
        reference = store.publish(b"Exact retained profile bytes")
        good: dict[str, object] = {"blob": reference.record()}
        bad: dict[str, object] = {"blob": {**reference.record(), "sha256": "a" * 64}}
        previous = history.commit(
            bad if bad_predecessor else good, expected=None, verify_state=lambda _: None
        ).checkpoint
        current = history.commit(good, expected=previous, verify_state=lambda _: None).checkpoint
        blob_identity, checkpoint_identity = store.identity, history.identity
    before = {p: p.read_bytes() for p in (path / "checkpoints").glob("*.json")}
    with ownership.Writer.acquire(path, identity) as writer:
        store = module.Blobs(writer, blob_identity)
        history = checkpoints.Checkpoints(writer, checkpoint_identity)

        def verify(state: dict[str, object]) -> None:
            assert (
                store.read(module.Blob.from_record(state["blob"]))
                == b"Exact retained profile bytes"
            )

        if bad_predecessor:
            with pytest.raises(module.BlobError):
                history.load(verify_state=verify)
        else:
            assert history.load(verify_state=verify) == current
    assert {p: p.read_bytes() for p in before} == before


def test_short_writes_retain_complete_bytes(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = module.Blobs.provision(owner)
    original = os.write

    def short(descriptor: int, data: memoryview) -> int:
        return original(descriptor, data[:2])

    monkeypatch.setattr(module.os, "write", short)
    raw = bytes(range(31))
    assert store.read(store.publish(raw)) == raw


@pytest.mark.parametrize("zero_write", [False, True])
def test_write_or_unsupported_link_failure_cleans_only_own_file(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, zero_write: bool
) -> None:
    store = module.Blobs.provision(owner)
    foreign = owner.path / "native-blobs" / ".foreign"
    foreign.write_bytes(b"keep")

    def failed(*args: object, **kwargs: object) -> int:
        if zero_write:
            return 0
        raise OSError("unsupported hard link")

    monkeypatch.setattr(module.os, "write" if zero_write else "link", failed)
    with pytest.raises(module.BlobError) as error:
        store.publish(b"abc")
    assert (error.value.code, error.value.exit_code) == ("WRITE_FAILED", 5)
    assert list(foreign.parent.iterdir()) == [foreign] and foreign.read_bytes() == b"keep"


@pytest.mark.parametrize("changed", ["entry", "bytes"])
def test_inflight_read_rejects_even_same_bytes_at_replaced_entry(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, changed: str
) -> None:
    store = module.Blobs.provision(owner)
    reference = store.publish(b"abc")
    path = owner.path / "native-blobs" / (reference.sha256 + ".bin")
    original = os.read

    def read(descriptor: int, count: int) -> bytes:
        result = original(descriptor, count)
        if changed == "entry":
            path.rename(path.with_suffix(".old"))
            path.write_bytes(b"abc")
        else:
            path.write_bytes(b"abd")
        return result

    monkeypatch.setattr(module.os, "read", read)
    with pytest.raises(module.BlobError):
        store.read(reference)


def test_cancelled_read_never_returns_partial_blob(owner: ownership.Writer) -> None:
    store = module.Blobs.provision(owner)
    reference = store.publish(b"a" * (2 * 1024 * 1024 + 1))
    selected = KeyboardInterrupt("selected")
    calls = 0

    def cancel() -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise selected

    with pytest.raises(KeyboardInterrupt) as error:
        store.read(reference, check_cancel=cancel)
    assert error.value is selected
    assert len(store.read(reference)) == reference.byte_size


def test_atime_update_is_not_content_corruption(owner: ownership.Writer) -> None:
    store = module.Blobs.provision(owner)
    reference = store.publish(b"abc")
    path = owner.path / "native-blobs" / (reference.sha256 + ".bin")
    os.utime(path, ns=(1, path.stat().st_mtime_ns))
    assert store.read(reference) == b"abc"


def test_replaced_private_cleanup_name_is_never_deleted(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = module.Blobs.provision(owner)
    private_name = ""

    def replaced(
        src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int, follow_symlinks: bool
    ) -> None:
        nonlocal private_name
        private_name = src
        os.rename(src, ".kept-original", src_dir_fd=src_dir_fd, dst_dir_fd=src_dir_fd)
        (owner.path / "native-blobs" / src).write_bytes(b"foreign replacement")
        raise KeyboardInterrupt

    monkeypatch.setattr(module.os, "link", replaced)
    with pytest.raises(KeyboardInterrupt) as error:
        store.publish(b"abc")
    assert "cleanup name replaced" in " ".join(error.value.__notes__)
    assert (owner.path / "native-blobs" / private_name).read_bytes() == b"foreign replacement"
    assert (owner.path / "native-blobs" / ".kept-original").read_bytes() == b"abc"
