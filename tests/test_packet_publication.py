"""Exclusive no-replace packet directory publication on the actual filesystem.

Real renames on a test-owned directory; the native mechanism is the product's
macOS ``renameatx_np``. Substituted renames model only unsupported filesystems,
which cannot be constructed here without a second volume.
"""

import errno
import os
import stat
import threading
from pathlib import Path

import pytest

from bookscan import packet_publication
from bookscan.packet_publication import PacketPublicationError, stage


def names(directory: Path) -> list[str]:
    return sorted(item.name for item in directory.iterdir())


def build(packet: packet_publication.PacketStage) -> None:
    (packet.path / "index.pdf").write_bytes(b"%PDF-index")
    (packet.path / "receipts").mkdir()
    (packet.path / "receipts" / "full.json").write_text("{}")


def test_publication_makes_the_complete_directory_visible_at_once(tmp_path: Path) -> None:
    destination = tmp_path / "Page 20 views"
    with stage(destination) as packet:
        assert packet.path.parent == tmp_path.resolve()
        assert not destination.exists()
        build(packet)
        published = packet.publish()
    assert published.identity_verified
    assert names(tmp_path) == ["Page 20 views"]
    assert names(destination) == ["index.pdf", "receipts"]
    assert (destination / "receipts" / "full.json").read_text() == "{}"
    mask = os.umask(0)
    os.umask(mask)
    assert stat.S_IMODE(destination.stat().st_mode) == 0o777 & ~mask


def test_empty_existing_directory_is_never_replaced(tmp_path: Path) -> None:
    # os.rename would silently replace this; the exclusive mechanism must not.
    destination = tmp_path / "packet"
    with stage(destination) as packet:
        build(packet)
        destination.mkdir()
        before = destination.stat()
        with pytest.raises(PacketPublicationError) as caught:
            packet.publish()
    assert (caught.value.code, caught.value.exit_code) == ("OUTPUT_EXISTS", 4)
    assert destination.stat().st_ino == before.st_ino and names(destination) == []
    assert names(tmp_path) == ["packet"]


@pytest.mark.parametrize("kind", ["directory", "file", "dangling", "symlink-to-directory"])
def test_occupied_destination_is_refused_before_any_stage(tmp_path: Path, kind: str) -> None:
    destination = tmp_path / "packet"
    other = tmp_path / "other"
    other.mkdir()
    if kind == "directory":
        destination.mkdir()
    elif kind == "file":
        destination.write_bytes(b"x")
    elif kind == "dangling":
        destination.symlink_to(tmp_path / "missing")
    else:
        destination.symlink_to(other)
    before = names(tmp_path)
    with pytest.raises(PacketPublicationError) as caught:
        with stage(destination):
            raise AssertionError("must not stage")
    assert (caught.value.code, caught.value.exit_code) == ("OUTPUT_EXISTS", 4)
    assert names(tmp_path) == before


@pytest.mark.parametrize("kind", ["missing-parent", "file-parent"])
def test_unusable_parent_is_an_invalid_directory(tmp_path: Path, kind: str) -> None:
    if kind == "missing-parent":
        destination = tmp_path / "absent" / "packet"
    else:
        (tmp_path / "plain").write_bytes(b"x")
        destination = tmp_path / "plain" / "packet"
    with pytest.raises(PacketPublicationError) as caught:
        with stage(destination):
            raise AssertionError("must not stage")
    assert (caught.value.code, caught.value.exit_code) == ("OUTPUT_DIRECTORY_INVALID", 4)
    assert names(tmp_path) == (["plain"] if kind == "file-parent" else [])


def test_symlinked_parent_publishes_into_the_real_directory(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real)
    with stage(alias / "packet") as packet:
        build(packet)
        published = packet.publish()
    assert published.path == real.resolve() / "packet"
    assert names(real) == ["packet"]


@pytest.mark.parametrize("phase", ["probe", "publish"])
def test_unsupported_exclusive_rename_is_a_publish_failure_without_leftovers(
    tmp_path: Path, phase: str
) -> None:
    calls = {"count": 0}

    def unsupported(parent: int, source: str, target: str) -> None:
        calls["count"] += 1
        if phase == "probe" or calls["count"] > 1:
            raise OSError(errno.ENOTSUP, "Operation not supported", target)
        packet_publication.native_exclusive_rename(parent, source, target)

    with pytest.raises(PacketPublicationError) as caught:
        with stage(tmp_path / "packet", rename=unsupported) as packet:
            build(packet)
            packet.publish()
    assert (caught.value.code, caught.value.exit_code) == ("PUBLISH_FAILED", 5)
    assert names(tmp_path) == []


def test_rename_that_replaces_an_occupied_name_is_not_trusted(tmp_path: Path) -> None:
    def replacing(parent: int, source: str, target: str) -> None:
        os.rename(source, target, src_dir_fd=parent, dst_dir_fd=parent)

    with pytest.raises(PacketPublicationError) as caught:
        with stage(tmp_path / "packet", rename=replacing):
            raise AssertionError("must not stage")
    assert caught.value.code == "PUBLISH_FAILED"
    assert names(tmp_path) == []


def test_failure_before_publication_removes_only_the_captured_stage(tmp_path: Path) -> None:
    class Selected(RuntimeError):
        pass

    with pytest.raises(Selected):
        with stage(tmp_path / "packet") as packet:
            build(packet)
            packet.capture()
            raise Selected
    assert names(tmp_path) == []


def test_unpublished_normal_exit_discards_the_captured_stage(tmp_path: Path) -> None:
    with stage(tmp_path / "packet") as packet:
        build(packet)
        packet.capture()
    assert names(tmp_path) == []
    assert not packet.published


def test_uncaptured_contents_are_never_adopted_by_cleanup(tmp_path: Path) -> None:
    # Ownership is captured at the builder's own completion boundary, not inferred
    # from the stage's name; contents written after no capture are retained.
    with pytest.raises(PacketPublicationError):
        with stage(tmp_path / "packet") as packet:
            build(packet)
    leftovers = list(tmp_path.iterdir())
    assert len(leftovers) == 1 and names(leftovers[0]) == ["index.pdf", "receipts"]


def test_foreign_entry_after_capture_is_retained_and_noted(tmp_path: Path) -> None:
    class Selected(RuntimeError):
        pass

    with pytest.raises(Selected) as caught:
        with stage(tmp_path / "packet") as packet:
            build(packet)
            packet.capture()
            (packet.path / "foreign.txt").write_text("not ours")
            raise Selected
    assert any("retained" in note for note in caught.value.__notes__)
    leftovers = [item for item in tmp_path.iterdir()]
    assert len(leftovers) == 1 and (leftovers[0] / "foreign.txt").read_text() == "not ours"


def test_published_packet_survives_a_later_failure(tmp_path: Path) -> None:
    class Late(RuntimeError):
        pass

    with pytest.raises(Late):
        with stage(tmp_path / "packet") as packet:
            build(packet)
            packet.publish()
            raise Late
    assert names(tmp_path / "packet") == ["index.pdf", "receipts"]
    assert names(tmp_path) == ["packet"]


def test_two_concurrent_publishers_have_exactly_one_winner(tmp_path: Path) -> None:
    destination = tmp_path / "packet"
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def contender(label: str) -> None:
        try:
            with stage(destination) as packet:
                (packet.path / "who.txt").write_text(label)
                barrier.wait(timeout=10)
                packet.publish()
                outcomes.append(f"won:{label}")
        except PacketPublicationError as error:
            outcomes.append(f"lost:{error.code}")

    first = threading.Thread(target=contender, args=("a",))
    second = threading.Thread(target=contender, args=("b",))
    first.start()
    second.start()
    first.join(20)
    second.join(20)
    winners = [item for item in outcomes if item.startswith("won:")]
    assert len(winners) == 1
    assert sorted(item for item in outcomes if item.startswith("lost:")) == ["lost:OUTPUT_EXISTS"]
    assert (destination / "who.txt").read_text() == winners[0].split(":")[1]
    assert names(tmp_path) == ["packet"]
