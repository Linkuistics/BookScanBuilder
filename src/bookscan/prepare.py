"""Preparation lifetime owner. Preview completes every pre-write check."""

import hashlib
import os
import stat
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, cast

import pikepdf

from bookscan.pdf import DocumentInfo, Projection, document_info, project_page, unsupported
from bookscan.results import Json, PreparationError
from bookscan.selections import Occurrence, Request, resolve, tokenize


@dataclass(frozen=True)
class Identity:
    device: int
    inode: int
    size: int
    mtime_ns: int

    @classmethod
    def read(cls, info: os.stat_result) -> "Identity":
        return cls(info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


@dataclass
class Source:
    path: Path
    stream: BinaryIO
    pdf: pikepdf.Pdf
    identity: Identity
    sha256: str
    info: DocumentInfo

    def recheck(self) -> None:
        try:
            before = Identity.read(os.fstat(self.stream.fileno()))
            path_before = Identity.read(self.path.stat())
            digest = hash_stream(self.stream)
            after = Identity.read(os.fstat(self.stream.fileno()))
            path_after = Identity.read(self.path.stat())
        except OSError as exc:
            raise changed(self.path) from exc
        if not (
            before == path_before == after == path_after == self.identity and digest == self.sha256
        ):
            raise changed(self.path)


@dataclass(frozen=True)
class Plan:
    output: Path
    pages: tuple[Occurrence, ...]
    projections: tuple[Projection, ...]
    sources: tuple[tuple[Path, str], ...]
    version: tuple[int, int]
    extension_level: int

    def record(self) -> dict[str, Json]:
        pages: list[Json] = [
            {
                "output_page": n,
                "source": str(page.source),
                "source_page": page.source_page,
                "role": page.role,
            }
            for n, page in enumerate(self.pages, 1)
        ]
        return {
            "schema_version": 1,
            "status": "planned",
            "output": str(self.output),
            "page_count": len(pages),
            "pages": pages,
            "warnings": [],
        }


def changed(path: Path) -> PreparationError:
    return PreparationError(
        "SOURCE_CHANGED",
        f"Source changed during preparation: {path}",
        "Keep sources stable and retry with a new destination.",
        3,
        {"source": str(path)},
    )


def hash_stream(stream: BinaryIO) -> str:
    stream.seek(0)
    hasher = hashlib.sha256()
    while data := stream.read(1024 * 1024):
        hasher.update(data)
    digest = hasher.hexdigest()
    stream.seek(0)
    return digest


def source_error(code: str, path: Path) -> PreparationError:
    return PreparationError(
        code,
        f"{code}: {path}",
        "Check the explicit PDF path, file type and read permissions.",
        3,
        {"source": str(path)},
    )


def warnings(pdf: pikepdf.Pdf) -> None:
    messages = cast(list[str], pdf.get_warnings())  # pyright: ignore[reportUnknownMemberType]
    if messages:
        raise unsupported("qpdf warning: " + messages[0])


def open_source(path: Path, stack: ExitStack) -> Source:
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            raise source_error("SOURCE_UNREADABLE", path)
        stream = stack.enter_context(path.open("rb"))
        identity = Identity.read(os.fstat(stream.fileno()))
        if Identity.read(path.stat()) != identity:
            raise changed(path)
        digest = hash_stream(stream)
        if Identity.read(os.fstat(stream.fileno())) != identity:
            raise changed(path)
    except FileNotFoundError as exc:
        raise source_error("SOURCE_NOT_FOUND", path) from exc
    except OSError as exc:
        raise source_error("SOURCE_UNREADABLE", path) from exc
    try:
        # Stream ownership remains with the lifetime owner; recovery is never attempted.
        # https://pikepdf.readthedocs.io/en/stable/api/main.html#pikepdf.Pdf.open
        pdf = stack.enter_context(
            pikepdf.Pdf.open(stream, attempt_recovery=False, suppress_warnings=True)
        )
        if pdf.is_encrypted:
            raise unsupported("encryption, including an empty password")
        if not pdf.pages:
            raise source_error("SOURCE_EMPTY", path)
        info = document_info(pdf)
        warnings(pdf)
    except (pikepdf.PdfError, ValueError, TypeError, RecursionError) as exc:
        error = unsupported("PDF syntax/opening: " + str(exc))
        error.context["source"] = str(path)
        raise error from exc
    except OSError as exc:
        raise source_error("SOURCE_UNREADABLE", path) from exc
    except PreparationError as exc:
        exc.context["source"] = str(path)
        raise
    return Source(path, stream, pdf, identity, digest, info)


def destination_check(output: Path, sources: list[Source]) -> None:
    try:
        if not output.parent.is_dir():
            raise PreparationError(
                "OUTPUT_DIRECTORY_INVALID",
                f"Destination parent is not a directory: {output.parent}",
                "Choose a destination in an existing directory.",
                4,
            )
        canonical = output.resolve()
        occupant = output.stat() if output.exists() else None
        for source in sources:
            if canonical == source.path.resolve() or (
                occupant is not None
                and (occupant.st_dev, occupant.st_ino)
                == (source.identity.device, source.identity.inode)
            ):
                raise PreparationError(
                    "SOURCE_OUTPUT_COLLISION",
                    f"Destination aliases source: {source.path}",
                    "Choose a new destination distinct from every source.",
                    4,
                    {"source": str(source.path)},
                )
        if os.path.lexists(output):
            raise PreparationError(
                "OUTPUT_EXISTS",
                f"Destination already exists: {output}",
                "Inspect that PDF or choose a new destination; no overwrite "
                "or automatic retry is available.",
                4,
            )
    except (OSError, RuntimeError) as exc:
        raise PreparationError(
            "OUTPUT_DIRECTORY_INVALID",
            f"Cannot inspect destination: {output}",
            "Check the destination parent and path.",
            4,
        ) from exc


def plan(request: Request, *, before_recheck: Callable[[], None] | None = None) -> Plan:
    # Phase 2 completes across *all* selections before opening any source.
    selections = tuple(tokenize(s) for s in request.selections)
    with ExitStack() as stack:
        sources: dict[Path, Source] = {}
        for selection in selections:
            if selection.source not in sources:
                sources[selection.source] = open_source(selection.source, stack)
        resolved = [(s, resolve(s, len(sources[s.source].pdf.pages))) for s in selections]
        pages = tuple(
            Occurrence(s.source, number, role)
            for role in ("front", "content", "back")
            for s, numbers in resolved
            if s.role == role
            for number in numbers
        )
        projected: list[Projection] = []
        cache: dict[tuple[int, int, int], Projection] = {}
        for occurrence in pages:
            source = sources[occurrence.source]
            key = source.identity.device, source.identity.inode, occurrence.source_page
            try:
                if key in cache:
                    projection = cache[key]
                    if projection.annotated:
                        raise unsupported("repeated annotated source page")
                else:
                    projection = project_page(source.pdf.pages[occurrence.source_page - 1].obj)
                    cache[key] = projection
                warnings(source.pdf)
            except (pikepdf.PdfError, ValueError, TypeError, RecursionError) as exc:
                error = unsupported("retained page traversal: " + str(exc))
                error.context.update(
                    source=str(occurrence.source), source_page=occurrence.source_page
                )
                raise error from exc
            except OSError as exc:
                raise source_error("SOURCE_UNREADABLE", source.path) from exc
            except PreparationError as exc:
                exc.context.update(
                    source=str(occurrence.source), source_page=occurrence.source_page
                )
                raise
            projected.append(projection)
        destination_check(request.output, list(sources.values()))
        if before_recheck is not None:
            before_recheck()
        for source in sources.values():
            source.recheck()
            warnings(source.pdf)
        return Plan(
            request.output,
            pages,
            tuple(projected),
            tuple((s.path, s.sha256) for s in sources.values()),
            max(s.info.version for s in sources.values()),
            max(s.info.extension_level for s in sources.values()),
        )
