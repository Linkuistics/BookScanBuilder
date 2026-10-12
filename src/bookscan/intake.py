"""Static sole-PDF validation and byte-exact private snapshot, without a project commit.

The operation owner supplies an unused private filename and cancellation policy.
The preparation adapter supplies read-only support gates, never the copied PDF.
"""

import hashlib
import math
import os
import re
import stat
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import BinaryIO, cast

import pikepdf

from bookscan.pdf import DocumentInfo, Geometry, document_info, get, project_page
from bookscan.results import PreparationError


@dataclass
class ImportFailure(Exception):
    code: str
    message: str
    exit_code: int = 3
    context: dict[str, object] = field(default_factory=lambda: dict[str, object]())

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True)
class Identity:
    device: int
    inode: int
    size: int
    mtime_ns: int
    ctime_ns: int

    @classmethod
    def read(cls, info: os.stat_result) -> "Identity":
        return cls(info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    @property
    def file_id(self) -> tuple[int, int]:
        return self.device, self.inode


@dataclass(frozen=True)
class Hint:
    role: str
    source_sha256: str
    source_page: int


def advisory_hint(page: pikepdf.Object) -> Hint | None:
    value = get(page, "/BookScanBuilder")
    if not isinstance(value, pikepdf.Dictionary):
        return None
    version, role, sha, number = (
        get(value, "/" + key) for key in ("Version", "Role", "SourceSHA256", "SourcePage")
    )
    if (
        type(version) is not int
        or version != 1
        or not isinstance(role, pikepdf.String)
        or str(role) not in {"front", "content", "back"}
        or not isinstance(sha, pikepdf.String)
        or re.fullmatch("[0-9a-f]{64}", str(sha)) is None
        or type(number) is not int
        or number <= 0
    ):
        return None
    return Hint(str(role), str(sha), number)


@dataclass(frozen=True)
class Frame:
    """PDF user-space edges -> top-left 300-dpi pixel edges; no rounding in the mapping.

    points is the original physical MediaBox extent (1/72 inch). pixels covers it
    using ceil, retaining the final partial pixel rather than clipping a page edge.
    """

    pixels: tuple[int, int]
    points: tuple[Decimal, Decimal]
    matrix: tuple[Fraction, Fraction, Fraction, Fraction, Fraction, Fraction]
    extent_changed: bool

    def map_point(self, x: Decimal, y: Decimal) -> tuple[Fraction, Fraction]:
        a, b, c, d, e, f = self.matrix
        return a * Fraction(x) + c * Fraction(y) + e, b * Fraction(x) + d * Fraction(y) + f


def effective_crop(geometry: Geometry) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """CropBox's displayed region: its intersection with the MediaBox, normalised.

    ISO 32000-1 14.11.2. https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
    """
    x0, y0, x1, y1 = geometry.boxes[0]
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    cx0, cy0, cx1, cy1 = geometry.boxes[1]
    cx0, cx1 = sorted((cx0, cx1))
    cy0, cy1 = sorted((cy0, cy1))
    return max(x0, cx0), max(y0, cy0), min(x1, cx1), min(y1, cy1)


def frame_for(geometry: Geometry) -> Frame:
    x0, y0, x1, y1 = geometry.boxes[0]
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    unit = geometry.user_unit
    width, height = (x1 - x0) * unit, (y1 - y0) * unit
    scale = Fraction(300) * Fraction(unit) / 72
    zero = Fraction(0)
    fx0, fy0, fx1, fy1 = (Fraction(value) for value in (x0, y0, x1, y1))
    rotation = geometry.rotate % 360
    if rotation == 0:
        matrix = (scale, zero, zero, -scale, -fx0 * scale, fy1 * scale)
    elif rotation == 90:
        matrix = (zero, scale, scale, zero, -fy0 * scale, -fx0 * scale)
    elif rotation == 180:
        matrix = (-scale, zero, zero, scale, fx1 * scale, -fy0 * scale)
    else:
        matrix = (zero, -scale, -scale, zero, fy1 * scale, fx1 * scale)
    if rotation in (90, 270):
        width, height = height, width
    return Frame(
        (math.ceil(Fraction(width) * 300 / 72), math.ceil(Fraction(height) * 300 / 72)),
        (width, height),
        matrix,
        effective_crop(geometry) != (x0, y0, x1, y1),
    )


@dataclass(frozen=True)
class Page:
    source_page: int
    geometry: Geometry
    frame: Frame
    hint: Hint | None


def _hash(stream: BinaryIO, check_cancel: Callable[[], None]) -> str:
    stream.seek(0)
    hasher = hashlib.sha256()
    while data := stream.read(1024 * 1024):
        check_cancel()
        hasher.update(data)
    check_cancel()
    stream.seek(0)
    return hasher.hexdigest()


def _warnings(pdf: pikepdf.Pdf) -> None:
    messages = cast(list[str], pdf.get_warnings())  # pyright: ignore[reportUnknownMemberType]
    if messages:
        raise ImportFailure("SOURCE_UNSUPPORTED", "qpdf parser warning: " + messages[0])


def _inspect(
    stream: BinaryIO, check_cancel: Callable[[], None]
) -> tuple[DocumentInfo, tuple[Page, ...]]:
    try:
        # Exact 10.16.0 source: stream remains caller-owned; no repair/overwrite fallback.
        # https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/_methods.py#L550
        with pikepdf.Pdf.open(stream, attempt_recovery=False, suppress_warnings=True) as pdf:
            if pdf.is_encrypted:
                raise ImportFailure("SOURCE_UNSUPPORTED", "encryption, including empty passwords")
            if not pdf.pages:
                raise ImportFailure("SOURCE_EMPTY", "PDF contains no pages")
            info = document_info(pdf)
            _warnings(pdf)
            pages: list[Page] = []
            for ordinal, page in enumerate(pdf.pages, 1):
                check_cancel()
                try:
                    # Only the validated geometry escapes; retained raw graphs are discarded.
                    geometry = project_page(page.obj).geometry
                    hint = advisory_hint(page.obj)
                    _warnings(pdf)
                except (ImportFailure, PreparationError) as error:
                    error.context["source_page"] = ordinal
                    raise
                pages.append(Page(ordinal, geometry, frame_for(geometry), hint))
                check_cancel()
            return info, tuple(pages)
    except PreparationError as error:
        raise ImportFailure(
            error.code, error.message, error.exit_code, dict(error.context)
        ) from error
    except (pikepdf.PdfError, ValueError, TypeError, RecursionError) as error:
        raise ImportFailure("SOURCE_UNSUPPORTED", "PDF syntax/traversal: " + str(error)) from error


def _stable(
    path: Path, stream: BinaryIO, identity: Identity, sha: str, check_cancel: Callable[[], None]
) -> None:
    check_cancel()
    try:
        before = Identity.read(os.fstat(stream.fileno()))
        path_before = Identity.read(path.stat())
        current_sha = _hash(stream, check_cancel)
        after = Identity.read(os.fstat(stream.fileno()))
        path_after = Identity.read(path.stat())
    except OSError as error:
        raise ImportFailure("SOURCE_CHANGED", f"Source became unavailable: {path}") from error
    if not (before == path_before == after == path_after == identity and current_sha == sha):
        raise ImportFailure("SOURCE_CHANGED", f"Source identity, metadata or bytes changed: {path}")


def inspect_saved(
    stream: BinaryIO,
    path: Path,
    identity: Identity,
    sha256: str,
    *,
    check_cancel: Callable[[], None] = lambda: None,
) -> tuple[DocumentInfo, tuple[Page, ...]]:
    """Rederive static source meaning between exact byte/identity checks.

    The saved-source owner gates the regular no-follow descriptor and retains
    ownership. This does not render, assess, write or reopen the original.
    """
    _stable(path, stream, identity, sha256, check_cancel)
    result = _inspect(stream, check_cancel)
    _stable(path, stream, identity, sha256, check_cancel)
    return result


@dataclass(frozen=True)
class Snapshot:
    path: Path
    sha256: str
    original_path: Path
    original_identity: Identity
    private_identity: Identity
    document: DocumentInfo
    pages: tuple[Page, ...]

    def verify(self, *, check_cancel: Callable[[], None] = lambda: None) -> None:
        check_cancel()
        try:
            with self.path.open("rb") as stream:
                if self.path.is_symlink():
                    raise ImportFailure("INVALID_PROJECT", f"Replaced snapshot: {self.path}")
                _stable(self.path, stream, self.private_identity, self.sha256, check_cancel)
        except (OSError, ImportFailure) as error:
            raise ImportFailure(
                "INVALID_PROJECT", f"Missing/changed private snapshot: {self.path}"
            ) from error


def snapshot(
    source: Path, private: Path, *, check_cancel: Callable[[], None] = lambda: None
) -> Snapshot:
    """Return a complete verified private copy; failure cleans only our owned inode.

    This is not publication or accepted state. The project owner must verify the
    completed snapshot/assets before its own initial-checkpoint transaction.
    """
    check_cancel()
    selected = source.expanduser().absolute()
    try:
        source = selected.resolve(strict=True)
        # Nonblocking open avoids waiting on FIFOs/devices before the regular-file gate.
        fd = os.open(source, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except FileNotFoundError as error:
        raise ImportFailure("SOURCE_NOT_FOUND", f"Input does not exist: {source}") from error
    except (OSError, RuntimeError) as error:
        raise ImportFailure("SOURCE_UNREADABLE", f"Cannot open input: {source}") from error
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ImportFailure("SOURCE_UNREADABLE", f"Input is not a regular file: {source}")
        identity = Identity.read(metadata)
        opened = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise
    with opened as stream:
        try:
            sha = _hash(stream, check_cancel)
            _stable(selected, stream, identity, sha, check_cancel)
            info, pages = _inspect(stream, check_cancel)
            _stable(selected, stream, identity, sha, check_cancel)
        except OSError as error:
            raise ImportFailure("SOURCE_UNREADABLE", f"Cannot read input: {source}") from error
        private = private.expanduser().absolute()
        try:
            occupant = private.stat() if private.exists() else None
            if private.resolve() == source or (
                occupant is not None and (occupant.st_dev, occupant.st_ino) == identity.file_id
            ):
                raise ImportFailure("SOURCE_OUTPUT_COLLISION", "Private snapshot aliases input", 4)
            created = os.open(private, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError as error:
            raise ImportFailure(
                "OUTPUT_EXISTS", f"Private filename is occupied: {private}", 4
            ) from error
        except OSError as error:
            raise ImportFailure(
                "WRITE_FAILED", f"Cannot create private snapshot: {private}", 5
            ) from error
        owned_id: tuple[int, int] | None = None
        try:
            owned_id = Identity.read(os.fstat(created)).file_id
            try:
                wrapped = os.fdopen(created, "w+b")
            except BaseException:
                os.close(created)
                raise
            with wrapped as output:
                check_cancel()
                # umask can remove permissions; guarantee the promised private 0600 mode.
                os.fchmod(output.fileno(), 0o600)
                stream.seek(0)
                while data := stream.read(1024 * 1024):
                    check_cancel()
                    output.write(data)
                output.flush()
                os.fsync(output.fileno())
                check_cancel()
                _stable(selected, stream, identity, sha, check_cancel)
                private_identity = Identity.read(os.fstat(output.fileno()))
                if (
                    Identity.read(private.stat()) != private_identity
                    or private.is_symlink()
                    or _hash(output, check_cancel) != sha
                    or Identity.read(os.fstat(output.fileno())) != private_identity
                    or Identity.read(private.stat()) != private_identity
                ):
                    raise ImportFailure("WRITE_FAILED", f"Private snapshot changed: {private}", 5)
                check_cancel()
                return Snapshot(private, sha, source, identity, private_identity, info, pages)
        except BaseException as error:
            # Resource cleanup only: preserve the owner's selected cancellation/error.
            try:
                if owned_id is not None:
                    current = private.lstat()
                    if (current.st_dev, current.st_ino) == owned_id:
                        private.unlink()
            except FileNotFoundError:
                pass
            except OSError as cleanup_error:
                error.add_note(f"Private snapshot cleanup failed: {private}: {cleanup_error}")
            if isinstance(error, OSError):
                raise ImportFailure(
                    "WRITE_FAILED", f"Private snapshot I/O failed: {private}", 5
                ) from error
            raise
