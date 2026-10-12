"""Project-owned immutable packet descriptors: lookup by issued packet ID, never by guess.

Dropping the content-address, ownership, link-count or no-clobber checks must break
literal-byte cases. Real files and a real writer lock exercise the actual store.
"""

import hashlib
import json
import os
import shutil
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from test_packet_receipts import OTHER_PACKET, PACKET, described

from bookscan import ownership, project_header
from bookscan import packet_descriptors as module
from bookscan.packet_receipts import Descriptor, ReceiptError


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    project = tmp_path / "Book project"
    project.mkdir()
    identity = ownership.provision(project)
    with ownership.Writer.acquire(project, identity) as writer:
        yield writer


def store_path(owner: ownership.Writer) -> Path:
    return owner.path / "packets"


def entry(descriptor: Descriptor) -> str:
    return f"{descriptor.packet_id}.{descriptor.id}.json"


def test_publish_then_read_returns_the_exact_sealed_descriptor(owner: ownership.Writer) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    assert store.publish(descriptor) == descriptor.id
    path = store_path(owner) / entry(descriptor)
    assert path.read_bytes() == descriptor.raw
    assert hashlib.sha256(path.read_bytes()).hexdigest() == descriptor.id
    assert (path.stat().st_mode & 0o777, path.stat().st_nlink) == (0o600, 1)
    assert [p.name for p in store_path(owner).iterdir()] == [path.name]
    assert store.read(PACKET) == descriptor


def test_identical_publication_is_idempotent_and_does_not_replace(owner: ownership.Writer) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    path = store_path(owner) / entry(descriptor)
    before = path.stat()
    assert store.publish(descriptor) == descriptor.id
    assert path.stat().st_ino == before.st_ino
    assert [p.name for p in store_path(owner).iterdir()] == [path.name]


def test_distinct_issuances_of_identical_views_coexist_and_resolve_separately(
    owner: ownership.Writer,
) -> None:
    store = module.Descriptors.provision(owner)
    (_, first), (_, second) = described(PACKET), described(OTHER_PACKET)
    assert first.id != second.id
    store.publish(first)
    store.publish(second)
    assert store.read(PACKET) == first and store.read(OTHER_PACKET) == second
    assert len(list(store_path(owner).iterdir())) == 2


def test_unknown_packet_is_an_invalid_receipt_not_project_damage(owner: ownership.Writer) -> None:
    store = module.Descriptors.provision(owner)
    with pytest.raises(ReceiptError) as error:
        store.read(PACKET)
    assert (error.value.code, error.value.exit_code, error.value.context) == (
        "INVALID_RECEIPT",
        6,
        "unknown-packet",
    )
    _, other = described(OTHER_PACKET)
    store.publish(other)
    with pytest.raises(ReceiptError, match="unknown-packet"):
        store.read(PACKET)


@pytest.mark.parametrize("packet", ["", "packet-1", "../packet-" + "0" * 32, "PACKET-" + "0" * 32])
def test_lookup_accepts_only_issued_packet_identifiers(
    owner: ownership.Writer, packet: str
) -> None:
    store = module.Descriptors.provision(owner)
    with pytest.raises(ReceiptError) as error:
        store.read(packet)
    assert error.value.context == "malformed"


def test_changed_bytes_under_the_content_address_are_project_damage(
    owner: ownership.Writer,
) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    path = store_path(owner) / entry(descriptor)
    path.write_bytes(descriptor.raw.replace(b"views/full.pdf", b"views/evil.pdf"))
    with pytest.raises(module.DescriptorError) as error:
        store.read(PACKET)
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)


def test_truncated_and_replaced_size_are_project_damage(owner: ownership.Writer) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    path = store_path(owner) / entry(descriptor)
    path.write_bytes(descriptor.raw[:-1])
    with pytest.raises(module.DescriptorError, match="INVALID_PROJECT"):
        store.read(PACKET)
    path.write_bytes(b"")
    with pytest.raises(module.DescriptorError, match="INVALID_PROJECT"):
        store.read(PACKET)


def test_a_directory_or_oversized_file_in_the_descriptor_name_is_project_damage(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    path = store_path(owner) / entry(descriptor)
    with monkeypatch.context() as patch:
        patch.setattr(module, "MAX_BYTES", len(descriptor.raw) - 1)
        with pytest.raises(module.DescriptorError, match="INVALID_PROJECT"):
            store.read(PACKET)
    assert store.read(PACKET) == descriptor
    path.unlink()
    path.mkdir()
    with pytest.raises(module.DescriptorError, match="INVALID_PROJECT"):
        store.read(PACKET)


def empty_read(descriptor: int, size: int) -> bytes:
    return b""


def test_a_file_that_shrinks_during_the_read_is_truncated_not_a_hang(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    with monkeypatch.context() as patch:
        patch.setattr(module.os, "read", empty_read)
        with pytest.raises(module.DescriptorError, match="truncated"):
            store.read(PACKET)


def test_a_file_replaced_during_verification_is_refused(owner: ownership.Writer) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    path = store_path(owner) / entry(descriptor)
    calls = 0

    def swap() -> None:
        nonlocal calls
        calls += 1
        if calls == 3:  # after the bytes were read, before the identity re-check
            data = path.read_bytes()
            path.unlink()
            path.write_bytes(data)

    with pytest.raises(module.DescriptorError, match="changed during verification"):
        store.read(PACKET, check_cancel=swap)


def test_a_descriptor_copied_under_another_packets_name_is_refused(owner: ownership.Writer) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    shutil.copy(
        store_path(owner) / entry(descriptor),
        store_path(owner) / f"{OTHER_PACKET}.{descriptor.id}.json",
    )
    # Content address and file digest agree; only the packet identity inside differs.
    with pytest.raises(module.DescriptorError, match="INVALID_PROJECT"):
        store.read(OTHER_PACKET)
    assert store.read(PACKET) == descriptor


def test_two_content_addresses_for_one_packet_are_ambiguous(owner: ownership.Writer) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    forged = descriptor.raw.replace(b"index.pdf", b"index.png")
    name = f"{PACKET}.{hashlib.sha256(forged).hexdigest()}.json"
    (store_path(owner) / name).write_bytes(forged)
    with pytest.raises(module.DescriptorError, match="INVALID_PROJECT"):
        store.read(PACKET)


def test_replacing_the_name_with_a_symlink_or_extra_link_is_refused(
    owner: ownership.Writer, tmp_path: Path
) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    path = store_path(owner) / entry(descriptor)
    outside = tmp_path / "outside.json"
    outside.write_bytes(descriptor.raw)
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(module.DescriptorError, match="INVALID_PROJECT"):
        store.read(PACKET)
    path.unlink()
    os.link(outside, path)
    with pytest.raises(module.DescriptorError, match="INVALID_PROJECT"):
        store.read(PACKET)


def test_a_replaced_store_directory_is_refused_even_with_valid_contents(
    owner: ownership.Writer, tmp_path: Path
) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    copy = tmp_path / "copy"
    shutil.copytree(store_path(owner), copy)
    shutil.rmtree(store_path(owner))
    copy.rename(store_path(owner))
    with pytest.raises(module.DescriptorError, match="INVALID_PROJECT"):
        store.read(PACKET)
    with pytest.raises(module.DescriptorError, match="INVALID_PROJECT"):
        store.publish(described(OTHER_PACKET)[1])


def test_a_symlinked_store_directory_is_refused(owner: ownership.Writer, tmp_path: Path) -> None:
    store = module.Descriptors.provision(owner)
    store_path(owner).rename(tmp_path / "moved")
    store_path(owner).symlink_to(tmp_path / "moved")
    with pytest.raises(module.DescriptorError, match="INVALID_PROJECT"):
        store.read(PACKET)


def test_unlisted_sidecar_names_never_become_descriptors(owner: ownership.Writer) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    (store_path(owner) / f"{PACKET}.notes.txt").write_text("sidecar")
    (store_path(owner) / f"{PACKET}.notes.json").write_text("sidecar")
    (store_path(owner) / f"{PACKET}.{'0' * 64}.json.bak").write_text("sidecar")
    (store_path(owner) / ".descriptor-orphan").write_bytes(b"private")
    assert store.read(PACKET) == descriptor
    with pytest.raises(ReceiptError, match="unknown-packet"):
        store.read(OTHER_PACKET)


def test_an_unsealed_or_altered_descriptor_is_not_published(owner: ownership.Writer) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    for broken in (
        replace(descriptor, id="0" * 64),
        replace(descriptor, raw=descriptor.raw + b" "),
        replace(descriptor, raw=b""),
    ):
        with pytest.raises(module.DescriptorError) as error:
            store.publish(broken)
        assert error.value.exit_code == 5
    assert list(store_path(owner).iterdir()) == []


def test_conflicting_existing_name_is_never_replaced(owner: ownership.Writer) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    path = store_path(owner) / entry(descriptor)
    path.write_bytes(b"occupied by another process")
    with pytest.raises(module.DescriptorError) as error:
        store.publish(descriptor)
    assert error.value.exit_code in {3, 5}
    assert path.read_bytes() == b"occupied by another process"
    assert [p.name for p in store_path(owner).iterdir()] == [path.name]


def test_cancellation_at_every_boundary_leaves_no_visible_or_private_name(
    owner: ownership.Writer,
) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()

    class Stop(Exception):
        pass

    calls = 0
    boundary = 0
    while True:
        remaining = boundary

        def check_cancel() -> None:
            nonlocal remaining
            if remaining == 0:
                raise Stop
            remaining -= 1

        try:
            store.publish(descriptor, check_cancel=check_cancel)
        except Stop:
            calls += 1
            names = [p.name for p in store_path(owner).iterdir()]
            # A cancel after the no-clobber link keeps the complete descriptor and
            # nothing private; a cancel before it leaves the store empty.
            assert names in ([], [entry(descriptor)])
            boundary += 1
            continue
        break
    assert calls >= 3
    assert store.read(PACKET) == descriptor
    assert [p.name for p in store_path(owner).iterdir()] == [entry(descriptor)]


def test_operations_require_live_caller_held_ownership(owner: ownership.Writer) -> None:
    store = module.Descriptors.provision(owner)
    _, descriptor = described()
    store.publish(descriptor)
    owner.close()
    with pytest.raises(ownership.OwnershipError):
        store.read(PACKET)
    with pytest.raises(ownership.OwnershipError):
        store.publish(described(OTHER_PACKET)[1])


def test_provision_refuses_an_existing_store_and_creates_it_private(
    owner: ownership.Writer,
) -> None:
    store = module.Descriptors.provision(owner)
    assert store_path(owner).stat().st_mode & 0o777 == 0o700
    assert (store.identity.device, store.identity.inode) == (
        store_path(owner).stat().st_dev,
        store_path(owner).stat().st_ino,
    )
    with pytest.raises(module.DescriptorError) as error:
        module.Descriptors.provision(owner)
    assert error.value.exit_code == 5


# --- the saved project header names the store ---------------------------------


@pytest.fixture
def stores(tmp_path: Path) -> Iterator[project_header.Stores]:
    project = tmp_path / "Descriptor project"
    project.mkdir()
    identity = ownership.provision(project)
    with ownership.Writer.acquire(project, identity) as writer:
        yield project_header.Stores.provision(writer)


def commit_state(stores: project_header.Stores) -> None:
    stores.checkpoints.commit({"literal": 1}, expected=None, verify_state=lambda state: None)


def test_header_binds_the_store_identity_and_resume_reads_a_published_descriptor(
    stores: project_header.Stores,
) -> None:
    project = stores.owner.path
    _, descriptor = described()
    stores.packets.publish(descriptor)
    commit_state(stores)
    header = project_header.Header.from_json((project / "project.json").read_bytes())
    info = (project / "packets").stat()
    assert header.packets == stores.packets.identity
    assert (header.packets.device, header.packets.inode) == (info.st_dev, info.st_ino)
    stores.owner.close()
    with project_header.resume(project, verify_state=lambda loaded, state: None) as (loaded, _):
        assert loaded.packets.read(PACKET) == descriptor


@pytest.mark.parametrize("field", ["packets"])
def test_header_without_or_with_unknown_store_fields_is_unsupported(
    stores: project_header.Stores, field: str
) -> None:
    record = json.loads((stores.owner.path / "project.json").read_bytes())
    missing = {key: value for key, value in record.items() if key != field}
    with pytest.raises(project_header.HeaderError, match="Unsupported project header"):
        project_header.Header.from_json(json.dumps(missing).encode())
    with pytest.raises(project_header.HeaderError, match="Unsupported project header"):
        project_header.Header.from_json(
            json.dumps({**record, "extra-store": record[field]}).encode()
        )


@pytest.mark.parametrize("kind", ["copy", "missing", "symlink", "file"])
def test_replaced_descriptor_directory_refuses_before_semantics_and_releases_lock(
    stores: project_header.Stores, tmp_path: Path, kind: str
) -> None:
    _, descriptor = described()
    stores.packets.publish(descriptor)
    commit_state(stores)
    project = stores.owner.path
    path = project / "packets"
    original = tmp_path / "original-packets"
    path.rename(original)
    if kind == "copy":
        shutil.copytree(original, path)
    elif kind == "symlink":
        path.symlink_to(original, target_is_directory=True)
    elif kind == "file":
        path.write_bytes(b"not a directory")
    stores.owner.close()
    called = False

    def forbidden(loaded: project_header.Stores, state: dict[str, object]) -> None:
        nonlocal called
        called = True

    with pytest.raises(project_header.HeaderError, match="packets"):
        with project_header.resume(project, verify_state=forbidden):
            pytest.fail("Replaced descriptor directory yielded a project")
    assert not called
    with ownership.Writer.acquire(project, stores.header.lock):
        pass
