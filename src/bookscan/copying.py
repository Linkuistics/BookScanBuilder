"""Lossless retained-graph copying and independently reopened output validation."""

import re
import secrets
from typing import TYPE_CHECKING, BinaryIO, cast

import pikepdf

from bookscan.pdf import (
    Projection,
    Ref,
    Value,
    annotations,
    document_info,
    get,
    items,
    project_page,
)
from bookscan.publication import failure
from bookscan.results import PreparationError

if TYPE_CHECKING:
    from bookscan.prepare import Plan


def compare(source: Projection, output: Projection) -> None:
    if source.geometry != output.geometry:
        raise failure("OUTPUT_INVALID", "Effective page geometry differs.")
    visited: set[tuple[int, int]] = set()

    def match(left: Value, right: Value) -> None:
        if isinstance(left, Ref) and isinstance(right, Ref):
            pair = left.node, right.node
            if pair in visited:
                return
            visited.add(pair)
            a, b = source.nodes[left.node], output.nodes[right.node]
            if a.kind != b.kind or a.raw != b.raw or len(a.items) != len(b.items):
                raise failure("OUTPUT_INVALID", "Retained object type/stream/array differs.")
            if tuple(k for k, _ in a.entries) != tuple(k for k, _ in b.entries):
                raise failure("OUTPUT_INVALID", "Retained dictionary keys differ.")
            for (_, x), (_, y) in zip(a.entries, b.entries, strict=True):
                match(x, y)
            for x, y in zip(a.items, b.items, strict=True):
                match(x, y)
        elif isinstance(left, Ref) or isinstance(right, Ref):
            raise failure("OUTPUT_INVALID", "Retained object/scalar type differs.")
        elif (
            isinstance(left, bool) != isinstance(right, bool)
            or (isinstance(left, (str, bytes, type(None))) and type(left) is not type(right))
            or left != right
        ):
            raise failure("OUTPUT_INVALID", "Retained scalar differs.")

    match(source.root, output.root)


def copy_page(pdf: pikepdf.Pdf, projection: Projection) -> pikepdf.Object:
    page = pdf.add_blank_page().obj
    objects: list[pikepdf.Object] = []
    for index, node in enumerate(projection.nodes):
        if index == projection.root.node:
            objects.append(page)
        elif node.kind == "stream":
            objects.append(pdf.make_stream(node.raw or b""))  # pyright: ignore[reportUnknownMemberType]
        elif node.kind == "array":
            objects.append(pdf.make_indirect(pikepdf.Array()))
        else:
            objects.append(pdf.make_indirect(pikepdf.Dictionary()))

    def materialize(value: Value) -> object:
        if isinstance(value, Ref):
            return objects[value.node]
        if isinstance(value, str):
            return pikepdf.Name(value)
        if isinstance(value, bytes):
            return pikepdf.String(value)
        return value

    for obj, node in zip(objects, projection.nodes, strict=True):
        if node.kind == "array":
            for value in node.items:
                obj.append(materialize(value))
        else:
            if obj is page:
                for key in list(page.keys()):
                    if key not in {"/Type", "/Parent"}:
                        del page[key]
            for key, value in node.entries:
                obj[key] = materialize(value)
    return page


def warnings(pdf: pikepdf.Pdf, code: str) -> None:
    messages = cast(list[str], pdf.get_warnings())  # pyright: ignore[reportUnknownMemberType]
    if messages:
        raise failure(code, "qpdf warning: " + str(messages[0]))


def restore_empty_streams(stream: BinaryIO, tag: str) -> None:
    """Restore qpdf's empty-stream metadata elision via a standard incremental revision."""
    stream.seek(0)
    data = stream.read()
    match = list(re.finditer(rb"startxref\s+(\d+)\s+%%EOF", data))[-1]
    updates: list[tuple[int, int, bytes]] = []
    with pikepdf.Pdf.open(stream, attempt_recovery=False, suppress_warnings=True) as reopened:
        for obj in reopened.objects:
            if isinstance(obj, pikepdf.Stream) and tag in obj:
                saved = obj[tag]
                declaration = pikepdf.Dictionary(dict(items(saved)))
                declaration["/Length"] = 0
                updates.append((*obj.objgen, declaration.unparse()))
        warnings(reopened, "COPY_FAILED")
        trailer = pikepdf.Dictionary(dict(items(reopened.trailer)))
        for key in (
            "/XRefStm",
            "/Prev",
            "/Type",
            "/W",
            "/Index",
            "/Length",
            "/Filter",
            "/DecodeParms",
        ):
            if key in trailer:
                del trailer[key]
        trailer["/Prev"] = int(match[1])
        serialized_trailer = trailer.unparse()
    if not updates:
        return
    stream.seek(0, 2)
    offsets: list[tuple[int, int, int]] = []
    for number, generation, declaration in updates:
        offsets.append((number, generation, stream.tell() + 1))
        stream.write(
            f"\n{number} {generation} obj\n".encode()
            + declaration
            + b"\nstream\n\nendstream\nendobj\n"
        )
    startxref = stream.tell()
    stream.write(b"xref\n")
    for number, generation, offset in sorted(offsets):
        stream.write(f"{number} 1\n{offset:010d} {generation:05d} n \n".encode())
    # ISO 32000-1 §7.5.6: same object IDs, previous xref and original trailer identity.
    # https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
    stream.write(b"trailer\n" + serialized_trailer + f"\nstartxref\n{startxref}\n%%EOF\n".encode())


def save(plan: "Plan", stream: BinaryIO) -> None:
    with pikepdf.Pdf.new() as pdf:
        try:
            hashes = dict(plan.sources)
            for occurrence, projection in zip(plan.pages, plan.projections, strict=True):
                page = copy_page(pdf, projection)
                _, annots = annotations(page)
                for annot, owner in zip(annots, projection.annotation_owners, strict=True):
                    if owner:
                        annot["/P"] = page
                page["/BookScanBuilder"] = pdf.make_indirect(
                    pikepdf.Dictionary(
                        Version=1,
                        Role=pikepdf.String(occurrence.role),
                        SourceSHA256=pikepdf.String(hashes[occurrence.source]),
                        SourcePage=occurrence.source_page,
                    )
                )
            warnings(pdf, "COPY_FAILED")
        except (pikepdf.PdfError, ValueError, TypeError, OSError, RecursionError) as exc:
            raise failure("COPY_FAILED", "Cannot copy retained page graph: " + str(exc)) from exc
        tag = "/BookScanBuilderRestore" + secrets.token_hex(16)
        needs_restore = False
        for obj in pdf.objects:
            if isinstance(obj, pikepdf.Stream) and not obj.read_raw_bytes() and "/Filter" in obj:
                needs_restore = True
                # Keep the encoded dictionary reachable while qpdf elides an empty stream's filter.
                saved = pikepdf.Dictionary(dict(items(obj.stream_dict)))
                if "/Length" in saved:
                    del saved["/Length"]
                obj[tag] = saved
        numeric = ".".join(map(str, plan.version))
        minimum: str | tuple[str, int] = (
            (numeric, plan.extension_level) if plan.extension_level else numeric
        )
        try:
            # Pinned release verifies stream-only saving and tuple extension controls.
            # https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/_methods.py
            pdf.save(
                stream,
                min_version=minimum,
                compress_streams=False,
                stream_decode_level=pikepdf.StreamDecodeLevel.none,
                recompress_flate=False,
                normalize_content=False,
                object_stream_mode=pikepdf.ObjectStreamMode.disable,
            )
        except (pikepdf.PdfError, ValueError, TypeError, OSError) as exc:
            raise failure("WRITE_FAILED", "Cannot save staged PDF: " + str(exc)) from exc
        warnings(pdf, "COPY_FAILED")
        try:
            if needs_restore:
                restore_empty_streams(stream, tag)
        except (OSError, pikepdf.PdfError, ValueError, TypeError, IndexError) as exc:
            raise failure(
                "WRITE_FAILED", "Cannot retain encoded empty-stream dictionaries."
            ) from exc


def validate(plan: "Plan", stream: BinaryIO) -> None:
    try:
        stream.seek(0)
        with pikepdf.Pdf.open(stream, attempt_recovery=False, suppress_warnings=True) as pdf:
            info = document_info(pdf)
            if info.version != plan.version or info.extension_level != plan.extension_level:
                raise failure("OUTPUT_INVALID", "Effective version/extensions differ.")
            if len(pdf.pages) != len(plan.pages):
                raise failure("OUTPUT_INVALID", "Output page count differs.")
            markers: set[tuple[int, int]] = set()
            annotation_ids: set[tuple[int, int]] = set()
            hashes = dict(plan.sources)
            for page, occurrence, source in zip(
                pdf.pages, plan.pages, plan.projections, strict=True
            ):
                marker = get(page.obj, "/BookScanBuilder")
                if not isinstance(marker, pikepdf.Dictionary) or not marker.is_indirect:
                    raise failure("OUTPUT_INVALID", "Missing independent page marker.")
                if marker.objgen in markers or set(marker.keys()) != {
                    "/Version",
                    "/Role",
                    "/SourceSHA256",
                    "/SourcePage",
                }:
                    raise failure("OUTPUT_INVALID", "Aliased/malformed page marker.")
                markers.add(marker.objgen)
                expected = {
                    "/Version": 1,
                    "/Role": occurrence.role,
                    "/SourceSHA256": hashes[occurrence.source],
                    "/SourcePage": occurrence.source_page,
                }
                for key, value in expected.items():
                    actual = get(marker, key)
                    if isinstance(value, str):
                        equal = (
                            isinstance(actual, pikepdf.String) and bytes(actual) == value.encode()
                        )
                    else:
                        equal = type(actual) is int and actual == value
                    if not equal:
                        raise failure("OUTPUT_INVALID", "Incorrect page marker " + key)
                projected = project_page(page.obj)
                compare(source, projected)
                _, annots = annotations(page.obj)
                if len(annots) != len(source.annotation_owners):
                    raise failure("OUTPUT_INVALID", "Output annotation count differs.")
                for annot, owner in zip(annots, source.annotation_owners, strict=True):
                    if not annot.is_indirect or annot.objgen in annotation_ids:
                        raise failure("OUTPUT_INVALID", "Annotation lacks a unique indirect owner.")
                    annotation_ids.add(annot.objgen)
                    if ("/P" in annot) != owner or (
                        owner and annot["/P"].objgen != page.obj.objgen
                    ):
                        raise failure("OUTPUT_INVALID", "Annotation owning page differs.")
                warnings(pdf, "OUTPUT_INVALID")
            warnings(pdf, "OUTPUT_INVALID")
    except PreparationError as exc:
        if exc.code != "SOURCE_UNSUPPORTED":
            raise
        raise failure("OUTPUT_INVALID", "Unsupported staged output: " + exc.message) from exc
    except (pikepdf.PdfError, ValueError, TypeError, OSError, RecursionError) as exc:
        raise failure("OUTPUT_INVALID", "Cannot validate staged output: " + str(exc)) from exc
    finally:
        stream.seek(0, 2)
