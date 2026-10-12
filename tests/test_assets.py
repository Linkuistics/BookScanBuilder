"""Dropping identity, pixel verification or no-clobber must break these contracts."""

import hashlib
import io
import os
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from bookscan import assets, ownership


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    project = tmp_path / "Book project"
    project.mkdir()
    identity = ownership.provision(project)
    with ownership.Writer.acquire(project, identity) as writer:
        yield writer


def test_exact_pixels_deduplicate_without_replacing_asset(owner: ownership.Writer) -> None:
    store = assets.Assets.provision(owner)
    rgb = bytes((0, 1, 255, 42, 128, 254))
    reference = store.publish(rgb, (2, 1))
    path = owner.path / "assets" / (reference.id + ".png")
    before = path.stat()
    assert store.read(reference) == rgb
    assert reference.rgb_sha256 == hashlib.sha256(rgb).hexdigest()
    assert store.publish(rgb, (2, 1)) == reference
    assert path.stat().st_ino == before.st_ino
    assert set(p.name for p in path.parent.iterdir()) == {path.name}
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)


def test_normal_read_access_time_update_is_not_corruption(owner: ownership.Writer) -> None:
    store = assets.Assets.provision(owner)
    reference = store.publish(b"abc", (1, 1))
    path = owner.path / "assets" / (reference.id + ".png")
    os.utime(path, ns=(1, path.stat().st_mtime_ns))
    assert store.read(reference) == b"abc"


def test_wrong_staged_disk_bytes_never_publish(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = assets.Assets.provision(owner)
    write = os.write

    def changed(descriptor: int, data: memoryview) -> int:
        raw = bytearray(data)
        raw[-1] ^= 1
        return write(descriptor, raw)

    monkeypatch.setattr(assets.os, "write", changed)
    with pytest.raises(assets.AssetError):
        store.publish(b"abc", (1, 1))
    assert not list((owner.path / "assets").iterdir())


def test_cleanup_failure_does_not_replace_selected_interruption(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = assets.Assets.provision(owner)

    def interrupted(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt

    def failed(*args: object, **kwargs: object) -> None:
        raise OSError("controlled cleanup failure")

    monkeypatch.setattr(assets.os, "link", interrupted)
    monkeypatch.setattr(assets.os, "unlink", failed)
    with pytest.raises(KeyboardInterrupt) as error:
        store.publish(b"abc", (1, 1))
    assert "cleanup" in " ".join(error.value.__notes__)
    assert all(p.name.startswith(".rgb-") for p in (owner.path / "assets").iterdir())


def test_dimensions_are_part_of_identity(owner: ownership.Writer) -> None:
    store = assets.Assets.provision(owner)
    rgb = bytes(range(18))
    wide = store.publish(rgb, (3, 2))
    tall = store.publish(rgb, (2, 3))
    assert wide.id != tall.id
    assert store.read(wide) == store.read(tall) == rgb


def test_every_channel_byte_is_retained_without_conversion(owner: ownership.Writer) -> None:
    # A stride of three through repeated 0..255 visits every value in each RGB
    # channel, including faint one-byte differences, without a renderer oracle.
    rgb = bytes(range(256)) * 3
    store = assets.Assets.provision(owner)
    reference = store.publish(rgb, (256, 1))
    assert store.read(reference) == rgb


@pytest.mark.parametrize("size,rgb", [((0, 1), b""), ((True, 1), b"abc"), ((2, 1), b"abc")])
def test_invalid_rgb_never_creates_an_asset(
    owner: ownership.Writer, size: tuple[int, int], rgb: bytes
) -> None:
    store = assets.Assets.provision(owner)
    with pytest.raises(assets.AssetError) as error:
        store.publish(rgb, size)
    assert (error.value.code, error.value.exit_code) == ("WRITE_FAILED", 5)
    assert not list((owner.path / "assets").iterdir())


@pytest.mark.parametrize(
    "kind", ["bytes", "pixels", "mode", "dimensions", "symlink", "hardlink", "fifo", "missing"]
)
def test_changed_or_aliased_asset_refused_without_repair(
    owner: ownership.Writer, kind: str
) -> None:
    store = assets.Assets.provision(owner)
    reference = store.publish(b"\x10\x20\x30" * 2, (2, 1))
    path = owner.path / "assets" / (reference.id + ".png")
    if kind == "bytes":
        path.write_bytes(b"not png")
    elif kind in {"pixels", "mode", "dimensions"}:
        with Image.new(
            "L" if kind == "mode" else "RGB", (1, 2) if kind == "dimensions" else (2, 1)
        ) as image:
            image.save(path)
    else:
        path.rename(owner.path / "original.png")
        if kind == "symlink":
            path.symlink_to(owner.path / "original.png")
        elif kind == "hardlink":
            os.link(owner.path / "original.png", path)
        elif kind == "fifo":
            os.mkfifo(path)
    before = path.lstat() if kind != "missing" else None
    with pytest.raises(assets.AssetError) as error:
        store.read(reference)
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)
    if kind != "missing":
        with pytest.raises(assets.AssetError):
            store.publish(b"\x10\x20\x30" * 2, (2, 1))
    assert (path.lstat() if kind != "missing" else None) == before


@pytest.mark.parametrize("field", ["id", "rgb_sha256", "png_sha256", "png_size", "size"])
def test_forged_reference_refused(owner: ownership.Writer, field: str) -> None:
    store = assets.Assets.provision(owner)
    reference = store.publish(b"abc", (1, 1))
    wrong: object = (2, 1) if field == "size" else 1 if field == "png_size" else "../escape"
    with pytest.raises(assets.AssetError, match="INVALID_PROJECT"):
        store.read(replace(reference, **{field: wrong}))


def test_decoded_identity_is_checked_even_if_encoded_digest_matches(
    owner: ownership.Writer,
) -> None:
    store = assets.Assets.provision(owner)
    reference = store.publish(b"abc", (1, 1))
    path = owner.path / "assets" / (reference.id + ".png")
    buffer = io.BytesIO()
    with Image.new("RGB", (1, 1), (0, 0, 0)) as image:
        image.save(buffer, format="PNG")
    raw = buffer.getvalue()
    path.write_bytes(raw)
    forged = replace(reference, png_sha256=hashlib.sha256(raw).hexdigest(), png_size=len(raw))
    with pytest.raises(assets.AssetError, match="INVALID_PROJECT"):
        store.read(forged)


@pytest.mark.parametrize("replacement", ["directory", "symlink", "missing"])
def test_replaced_asset_directory_never_redirects_operations(
    owner: ownership.Writer, replacement: str
) -> None:
    store = assets.Assets.provision(owner)
    reference = store.publish(b"abc", (1, 1))
    directory = owner.path / "assets"
    directory.rename(owner.path / "old-assets")
    if replacement == "directory":
        directory.mkdir()
    elif replacement == "symlink":
        directory.symlink_to(owner.path / "old-assets", target_is_directory=True)
    with pytest.raises(assets.AssetError, match="INVALID_PROJECT"):
        store.read(reference)
    with pytest.raises(assets.AssetError, match="INVALID_PROJECT"):
        store.publish(b"abc", (1, 1))
    assert list((owner.path / "old-assets").iterdir())
    if replacement == "directory":
        assert not list(directory.iterdir())


def test_closed_writer_cannot_access_assets(owner: ownership.Writer) -> None:
    store = assets.Assets.provision(owner)
    reference = store.publish(b"abc", (1, 1))
    owner.close()
    with pytest.raises(ownership.OwnershipError, match="INVALID_PROJECT"):
        store.read(reference)
    with pytest.raises(ownership.OwnershipError, match="INVALID_PROJECT"):
        store.publish(b"abc", (1, 1))


def test_occupied_asset_directory_never_replaced(owner: ownership.Writer) -> None:
    assets.Assets.provision(owner)
    marker = owner.path / "assets" / "keep"
    marker.write_bytes(b"untouched")
    with pytest.raises(assets.AssetError):
        assets.Assets.provision(owner)
    assert marker.read_bytes() == b"untouched"


def test_prelink_interruption_cleans_only_owned_name(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = assets.Assets.provision(owner)
    foreign = owner.path / "assets" / ".foreign-private"
    foreign.write_bytes(b"keep")

    def interrupted(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(assets.os, "link", interrupted)
    with pytest.raises(KeyboardInterrupt):
        store.publish(b"abc", (1, 1))
    assert list((owner.path / "assets").iterdir()) == [foreign]
    assert foreign.read_bytes() == b"keep"


def test_postlink_interruption_retains_complete_orphan(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = assets.Assets.provision(owner)
    link = os.link

    def interrupted(
        src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int, follow_symlinks: bool
    ) -> None:
        link(
            src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd, follow_symlinks=follow_symlinks
        )
        raise KeyboardInterrupt

    monkeypatch.setattr(assets.os, "link", interrupted)
    with pytest.raises(KeyboardInterrupt):
        store.publish(b"abc", (1, 1))
    paths = list((owner.path / "assets").iterdir())
    assert len(paths) == 1 and paths[0].suffix == ".png"
    with Image.open(paths[0]) as image:
        assert image.tobytes() == b"abc"
    monkeypatch.setattr(assets.os, "link", link)
    reference = store.publish(b"abc", (1, 1))
    assert store.read(reference) == b"abc"
