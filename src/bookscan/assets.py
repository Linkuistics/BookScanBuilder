"""Immutable exact RGB assets under caller-held project ownership."""

import hashlib
import io
import os
import re
import stat
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Self, cast

from PIL import Image

from bookscan import records
from bookscan.import_publications import Publications
from bookscan.ownership import Writer


@dataclass
class AssetError(Exception):
    code: str
    message: str
    exit_code: int = 3

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True)
class DirectoryIdentity:
    device: int
    inode: int


@contextmanager
def _closing(descriptor: int, *, writing: bool = False) -> Iterator[None]:
    """Close once, preserving only a failure from this descriptor's own scope."""
    # A contextmanager receives the body's exception at yield; a caller's
    # already-handled exception must not hide a new close-only failure.
    # https://docs.python.org/3.12/library/contextlib.html#contextlib.contextmanager
    selected: BaseException | None = None
    try:
        yield
    except BaseException as error:
        selected = error
        raise
    finally:
        try:
            # A failed close may have released the fd; never retry its number.
            # https://docs.python.org/3.12/library/os.html#os.close
            os.close(descriptor)
        except OSError as error:
            if selected is not None:
                selected.add_note("RGB descriptor close: " + str(error))
            else:
                raise AssetError(
                    "WRITE_FAILED" if writing else "INVALID_PROJECT",
                    "Cannot close RGB descriptor.",
                    5 if writing else 3,
                ) from error


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_identity(info: os.stat_result) -> tuple[int, ...]:
    # Reading may advance atime; preserve nanosecond modification/change checks.
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _id(size: tuple[int, int], rgb_sha256: str) -> str:
    return _sha(f"BookScanBuilderRGB:1\n{size[0]} {size[1]}\n{rgb_sha256}\n".encode("ascii"))


def _size(size: object) -> bool:
    if not isinstance(size, tuple):
        return False
    dimensions = cast(tuple[object, ...], size)
    return len(dimensions) == 2 and all(type(value) is int and value > 0 for value in dimensions)


def _digest(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


@dataclass(frozen=True)
class RGBAsset:
    """A checkpoint must retain the whole reference, not just its asset filename."""

    id: str
    size: tuple[int, int]
    rgb_sha256: str
    png_sha256: str
    png_size: int

    def verify(self) -> None:
        if (
            not _size(self.size)
            or type(self.png_size) is not int
            or self.png_size <= 0
            or not all(_digest(value) for value in (self.id, self.rgb_sha256, self.png_sha256))
            or self.id != _id(self.size, self.rgb_sha256)
        ):
            raise AssetError("INVALID_PROJECT", "Invalid RGB asset reference.")

    def record(self) -> dict[str, object]:
        """Complete private reference v1; independent of project/report versions."""
        self.verify()
        return {
            "format": "BookScanBuilderRGBAsset",
            "version": 1,
            "id": self.id,
            "size": list(self.size),
            "rgb_sha256": self.rgb_sha256,
            "png_sha256": self.png_sha256,
            "png_size": self.png_size,
        }

    @classmethod
    def from_json(cls, raw: bytes) -> Self:
        """Decode the complete saved reference before verifying its meaning."""
        try:
            value = records.decode(raw)
        except records.RecordError as error:
            raise AssetError("INVALID_PROJECT", "Invalid RGB reference JSON.") from error
        return cls.from_record(value)

    @classmethod
    def from_record(cls, value: object) -> Self:
        """Validate saved JSON meaning without coercion, file reads or repair.

        No optional/nonsemantic fields are defined for this reference version.
        The checkpoint JSON reader must reject duplicate keys before this boundary.
        Pixel and encoded digests are subsequently verified by Assets.read.
        """
        if not isinstance(value, dict):
            raise AssetError("INVALID_PROJECT", "RGB asset reference is not an object.")
        data = cast(dict[object, object], value)
        fields = {"format", "version", "id", "size", "rgb_sha256", "png_sha256", "png_size"}
        if (
            set(data) != fields
            or data["format"] != "BookScanBuilderRGBAsset"
            or type(data["version"]) is not int
            or data["version"] != 1
        ):
            raise AssetError("INVALID_PROJECT", "Unsupported RGB asset reference fields/version.")
        size = data["size"]
        if not isinstance(size, list):
            raise AssetError("INVALID_PROJECT", "Invalid saved RGB dimensions.")
        dimensions = tuple(cast(list[object], size))
        if not _size(dimensions):
            raise AssetError("INVALID_PROJECT", "Invalid saved RGB dimensions.")
        result = cls(
            cast(str, data["id"]),
            cast(tuple[int, int], dimensions),
            cast(str, data["rgb_sha256"]),
            cast(str, data["png_sha256"]),
            cast(int, data["png_size"]),
        )
        # Casts declare storage types only; verify rejects every malformed value.
        result.verify()
        return result


def _decode(raw: bytes, reference: RGBAsset) -> bytes:
    if len(raw) != reference.png_size or _sha(raw) != reference.png_sha256:
        raise AssetError("INVALID_PROJECT", "RGB asset encoded bytes changed.")
    try:
        # 12.3.0 open is lazy: tobytes forces complete decoding before acceptance.
        # Restrict the decoder; never convert mode, colour, scale or pixels.
        # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.open
        with Image.open(io.BytesIO(raw), formats=["PNG"]) as image:
            if (
                image.mode != "RGB"
                or image.size != reference.size
                or getattr(image, "n_frames", 1) != 1
            ):
                raise AssetError("INVALID_PROJECT", "RGB asset mode/dimensions/frames changed.")
            rgb = image.tobytes()
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise AssetError("INVALID_PROJECT", "RGB asset cannot be decoded.") from error
    if len(rgb) != reference.size[0] * reference.size[1] * 3 or _sha(rgb) != reference.rgb_sha256:
        raise AssetError("INVALID_PROJECT", "RGB asset decoded pixels changed.")
    return rgb


class Assets:
    """Publish/read exact images without acquiring a second writer or making a checkpoint.

    The containing project header must persist directory identity and references.
    No enumeration or orphan promotes an image to accepted state. A killed writer
    can leave private names; these operations neither consume nor sweep them.
    """

    def __init__(self, owner: Writer, identity: DirectoryIdentity) -> None:
        self.owner = owner
        self.identity = identity
        self.publications: Publications | None = None

    @classmethod
    def provision(cls, owner: Writer) -> Self:
        from bookscan.project_reservation import provision_store

        owner.verify()
        try:
            with provision_store(owner, "assets") as info:
                result = cls(owner, DirectoryIdentity(info.st_dev, info.st_ino))
                with result._directory(writing=True):
                    pass
                return result
        except OSError as error:
            raise AssetError(
                "WRITE_FAILED", "Cannot reserve unused RGB assets directory.", 5
            ) from error

    def _verify_directory(self, descriptor: int) -> None:
        self.owner.verify()
        held = os.fstat(descriptor)
        current = (self.owner.path / "assets").lstat()
        expected = (self.identity.device, self.identity.inode)
        if (
            not stat.S_ISDIR(current.st_mode)
            or (held.st_dev, held.st_ino) != expected
            or (current.st_dev, current.st_ino) != expected
        ):
            raise AssetError("INVALID_PROJECT", "RGB assets directory was replaced.")

    @contextmanager
    def _directory(self, *, writing: bool = False) -> Iterator[int]:
        self.owner.verify()
        try:
            descriptor = os.open(
                self.owner.path / "assets",
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            with _closing(descriptor, writing=writing):
                self._verify_directory(descriptor)
                yield descriptor
                self._verify_directory(descriptor)
        except OSError as error:
            raise AssetError("INVALID_PROJECT", "Cannot verify RGB assets directory.") from error

    def _read(
        self,
        directory: int,
        reference: RGBAsset,
        check_cancel: Callable[[], None],
        *,
        name: str | None = None,
    ) -> bytes:
        name = reference.id + ".png" if name is None else name
        try:
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                dir_fd=directory,
            )
            with _closing(descriptor):
                before = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(before.st_mode)
                    or before.st_nlink != 1
                    or before.st_size != reference.png_size
                ):
                    raise AssetError("INVALID_PROJECT", "RGB asset file type/links/size changed.")
                chunks: list[bytes] = []
                remaining = reference.png_size
                while remaining:
                    check_cancel()
                    chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                    if not chunk:
                        raise AssetError("INVALID_PROJECT", "RGB asset is truncated.")
                    chunks.append(chunk)
                    remaining -= len(chunk)
                rgb = _decode(b"".join(chunks), reference)
                check_cancel()
                after = os.fstat(descriptor)
                current = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if _file_identity(after) != _file_identity(before) or _file_identity(
                    current
                ) != _file_identity(after):
                    raise AssetError("INVALID_PROJECT", "RGB asset changed during verification.")
                self._verify_directory(directory)
                return rgb
        except OSError as error:
            raise AssetError("INVALID_PROJECT", "RGB asset is missing or unreadable.") from error

    def read(
        self, reference: RGBAsset, *, check_cancel: Callable[[], None] = lambda: None
    ) -> bytes:
        self.owner.verify()
        reference.verify()
        check_cancel()
        with self._directory() as directory:
            return self._read(directory, reference, check_cancel)

    def publish(
        self, rgb: bytes, size: tuple[int, int], *, check_cancel: Callable[[], None] = lambda: None
    ) -> RGBAsset:
        self.owner.verify()
        check_cancel()
        if not _size(size) or len(rgb) != size[0] * size[1] * 3:
            raise AssetError("WRITE_FAILED", "RGB dimensions do not match complete pixels.", 5)
        buffer = io.BytesIO()
        try:
            # Lossless PNG, from exact interleaved RGB; no inherited source metadata.
            # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.frombytes
            with Image.frombytes("RGB", size, rgb) as image:
                image.save(buffer, format="PNG")
        except (OSError, ValueError) as error:
            raise AssetError("WRITE_FAILED", "Cannot encode complete RGB PNG.", 5) from error
        raw = buffer.getvalue()
        reference = RGBAsset(_id(size, _sha(rgb)), size, _sha(rgb), _sha(raw), len(raw))
        _decode(raw, reference)
        check_cancel()
        with self._directory(writing=True) as directory:
            if self.publications is not None:
                self.publications.verify(directory)
            name = reference.id + ".png"
            private = ".rgb-" + uuid.uuid4().hex
            descriptor = -1
            owned = False
            published = False

            def cleanup() -> None:
                if not owned:
                    return
                try:
                    held = os.fstat(descriptor)
                    current = os.stat(private, dir_fd=directory, follow_symlinks=False)
                    if (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino):
                        raise AssetError(
                            "WRITE_FAILED", "Private asset cleanup name was replaced.", 5
                        )
                    expected = _file_identity(held)
                    try:
                        os.unlink(private, dir_fd=directory)
                    except OSError as error:
                        if self.publications is not None:
                            try:
                                self.publications.refused(
                                    directory,
                                    descriptor,
                                    private,
                                    expected,
                                    linked_name=name if published else None,
                                )
                            except OSError as failure:
                                error.add_note("Private ownership capture: " + str(failure))
                        raise
                except OSError as error:
                    raise AssetError(
                        "WRITE_FAILED", "Cannot clean owned private asset.", 5
                    ) from error

            try:
                descriptor = os.open(
                    private,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                    dir_fd=directory,
                )
            except OSError as error:
                raise AssetError("WRITE_FAILED", "Cannot create private RGB asset.", 5) from error
            with _closing(descriptor, writing=True):
                try:
                    owned = True
                    view = memoryview(raw)
                    while view:
                        check_cancel()
                        written = os.write(descriptor, view)
                        if written == 0:
                            raise OSError("Zero-length asset write.")
                        view = view[written:]
                    os.fsync(descriptor)
                    check_cancel()
                    self._read(directory, reference, check_cancel, name=private)
                    self._verify_directory(directory)
                    # Link publication cannot replace an occupied name. Unlike a
                    # checkpoint, a linked asset alone is never saved review state.
                    # https://docs.python.org/3.12/library/os.html#os.link
                    try:
                        os.link(
                            private,
                            name,
                            src_dir_fd=directory,
                            dst_dir_fd=directory,
                            follow_symlinks=False,
                        )
                        published = True
                    except FileExistsError:
                        self._read(directory, reference, check_cancel)
                except BaseException as error:
                    try:
                        cleanup()
                        if owned and self.publications is not None:
                            if published:
                                self.publications.completed(
                                    directory, descriptor, name, created=True
                                )
                            else:
                                self.publications.aborted(directory)
                    except (AssetError, OSError) as failure:
                        error.add_note("Asset cleanup: " + str(failure))
                    if isinstance(error, OSError):
                        raise AssetError(
                            "WRITE_FAILED", "Cannot publish complete RGB asset.", 5
                        ) from error
                    raise
                else:
                    cleanup()
                    if self.publications is not None:
                        self.publications.completed(directory, descriptor, name, created=published)
            # Complete on-disk bytes are checked too, not just the encoder buffer.
            self._read(directory, reference, check_cancel)
        return reference
