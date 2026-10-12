"""Packet issuance, single-use receipt identity and the content-addressed descriptor.

A receipt is local identity evidence for one displayed view or summary; it is
not proof that a human inspected anything. Authenticity means the receipt's own
bytes equal the entry in the project-owned immutable descriptor that names the
same project and source. File integrity is a separate, later check for new
actions only, so an authentic retry can replay after the external packet was
edited or deleted.

Pure data: no project store, writer ownership, packet directory or renderer is
needed to issue, describe or authenticate. Presentation records outside the
review checkpoint: issuing one never changes review facts.
"""

import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Self, cast

from bookscan import records

RECEIPT_FORMAT = "BookScanBuilderPacketReceipt"
DESCRIPTOR_FORMAT = "BookScanBuilderPacketDescriptor"
VERSION = 1

type View = Literal["full", "native", "source-native", "summary"]
type PacketKind = Literal["views", "summary"]
VIEWS: tuple[View, ...] = ("full", "native", "source-native", "summary")
PACKET_KINDS: tuple[PacketKind, ...] = ("views", "summary")

_HEX64 = re.compile("[0-9a-f]{64}")
_PACKET_ID = re.compile("packet-[0-9a-f]{32}")
_RECEIPT_ID = re.compile("receipt-[0-9a-f]{64}")
_REGION = re.compile("native-[0-9]{3,}")

CONTEXTS = (
    "malformed",
    "foreign",
    "tampered",
    "unknown-packet",
    "packet-file-changed",
    "receipt-used",
    "wrong-view",
)


@dataclass
class ReceiptError(Exception):
    """INVALID_RECEIPT (6): never mutates; the remedy is a newly issued receipt."""

    message: str
    context: str
    code: str = "INVALID_RECEIPT"
    exit_code: int = 6

    @property
    def remediation(self) -> str:
        return (
            "Publish a new packet with bookscan baseline views PROJECT --page ID --output NEW "
            "or bookscan baseline status PROJECT --output NEW, inspect it unedited and use "
            "its newly issued receipt; annotate a separate copy, not the packet."
        )

    def __str__(self) -> str:
        return f"{self.code} ({self.context}): {self.message}"


def _json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fail(message: str, context: str = "malformed") -> ReceiptError:
    return ReceiptError(message, context)


def _digest(value: object, what: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise _fail(f"{what} is not a SHA-256 digest.")
    return value


def _text(value: object, what: str) -> str:
    if type(value) is not str or not value or "\n" in value or "\r" in value:
        raise _fail(f"{what} is not a nonempty single-line string.")
    return value


def _path(value: object) -> str:
    """Descriptor paths are relative, forward-slash, with no traversal."""
    text = _text(value, "Packet file path")
    parts = text.split("/")
    if text.startswith("/") or any(part in ("", ".", "..") or "\\" in part for part in parts):
        raise _fail(f"Packet file path {text!r} is not a plain relative path.")
    return text


@dataclass(frozen=True)
class Identity:
    """The project facts every receipt and header names."""

    project_id: str
    source_sha256: str
    review_revision: str
    snapshot_id: str

    def checked(self) -> Self:
        _text(self.project_id, "Project ID")
        _digest(self.source_sha256, "Source snapshot digest")
        _digest(self.review_revision, "Review revision")
        _digest(self.snapshot_id, "Export snapshot digest")
        return self

    def record(self) -> dict[str, object]:
        self.checked()
        return {
            "project_id": self.project_id,
            "source_sha256": self.source_sha256,
            "review_revision": self.review_revision,
            "snapshot_id": self.snapshot_id,
        }


@dataclass(frozen=True)
class Coverage:
    """Exactly what one receipt's view displays; native regions are named, not implied."""

    view: View
    occurrence_id: str | None = None
    source_pdf_page: int | None = None
    image_revision: str | None = None
    regions: tuple[str, ...] = ()
    box: str = "MediaBox"
    scale: str = ""
    unresolved_sha256: str | None = None
    inspection_sha256: str | None = None

    def checked(self) -> Self:
        if self.view not in VIEWS:
            raise _fail(f"Unknown view kind {self.view!r}.")
        _text(self.box, "Box")
        _text(self.scale, "Display scale")
        if self.view == "summary":
            if (
                self.occurrence_id is not None
                or self.source_pdf_page is not None
                or self.image_revision is not None
                or self.regions
            ):
                raise _fail("A summary receipt covers the whole snapshot, not one occurrence.")
            _digest(self.unresolved_sha256, "Unresolved roster digest")
            _digest(self.inspection_sha256, "Inspection/disposition digest")
            return self
        _text(self.occurrence_id, "Occurrence ID")
        if type(self.source_pdf_page) is not int or self.source_pdf_page < 1:
            raise _fail("Source PDF page is not a one-based integer.")
        _digest(self.image_revision, "Image revision")
        if self.unresolved_sha256 is not None or self.inspection_sha256 is not None:
            raise _fail("Only a summary receipt carries roster/inspection digests.")
        if self.view == "full" and self.regions:
            raise _fail("A full comparison covers the whole page, not named regions.")
        if self.view == "native" and not self.regions:
            raise _fail("A native receipt must name its covered regions.")
        if any(
            type(region) is not str or _REGION.fullmatch(region) is None for region in self.regions
        ):
            raise _fail("Region IDs must be native-NNN identifiers.")
        if list(self.regions) != sorted(set(self.regions)):
            raise _fail("Region IDs must be unique and sorted.")
        return self

    def record(self) -> dict[str, object]:
        self.checked()
        return {
            "view": self.view,
            "occurrence_id": self.occurrence_id,
            "source_pdf_page": self.source_pdf_page,
            "image_revision": self.image_revision,
            "regions": list(self.regions),
            "box": self.box,
            "scale": self.scale,
            "unresolved_sha256": self.unresolved_sha256,
            "inspection_sha256": self.inspection_sha256,
        }

    @classmethod
    def from_record(cls, value: object) -> Self:
        fields = {
            "view",
            "occurrence_id",
            "source_pdf_page",
            "image_revision",
            "regions",
            "box",
            "scale",
            "unresolved_sha256",
            "inspection_sha256",
        }
        if type(value) is not dict or set(cast(dict[str, object], value)) != fields:
            raise _fail("Unsupported receipt coverage fields.")
        data = cast(dict[str, object], value)
        regions = data["regions"]
        if type(regions) is not list:
            raise _fail("Receipt regions are not a list.")
        view = data["view"]
        if view not in VIEWS:
            raise _fail(f"Unknown view kind {view!r}.")
        return cls(
            view,
            cast(str | None, data["occurrence_id"]),
            cast(int | None, data["source_pdf_page"]),
            cast(str | None, data["image_revision"]),
            tuple(cast(list[str], regions)),
            cast(str, data["box"]),
            cast(str, data["scale"]),
            cast(str | None, data["unresolved_sha256"]),
            cast(str | None, data["inspection_sha256"]),
        ).checked()


def _receipt_id(packet_id: str, identity: Identity, coverage: Coverage) -> str:
    # Binds the issuance, so identical views at one unchanged snapshot differ.
    body = {
        "domain": "BookScanBuilderPacketReceipt-v1",
        "packet_id": packet_id,
        "identity": identity.record(),
        "coverage": coverage.record(),
    }
    return "receipt-" + _sha(_json(body))


@dataclass(frozen=True)
class Receipt:
    packet_id: str
    receipt_id: str
    path: str
    identity: Identity
    coverage: Coverage

    def record(self) -> dict[str, object]:
        return {
            "format": RECEIPT_FORMAT,
            "version": VERSION,
            "packet_id": self.packet_id,
            "receipt_id": self.receipt_id,
            "path": self.path,
            "identity": self.identity.record(),
            "coverage": self.coverage.record(),
        }

    def raw(self) -> bytes:
        return _json(self.record()) + b"\n"

    @classmethod
    def from_record(cls, value: object) -> Self:
        fields = {"format", "version", "packet_id", "receipt_id", "path", "identity", "coverage"}
        if type(value) is not dict or set(cast(dict[str, object], value)) != fields:
            raise _fail("Unsupported receipt fields.")
        data = cast(dict[str, object], value)
        if (
            data["format"] != RECEIPT_FORMAT
            or type(data["version"]) is not int
            or data["version"] != VERSION
        ):
            raise _fail("Unsupported receipt format or version.")
        packet_id = data["packet_id"]
        receipt_id = data["receipt_id"]
        if type(packet_id) is not str or _PACKET_ID.fullmatch(packet_id) is None:
            raise _fail("Receipt packet ID is not an issued packet identifier.")
        if type(receipt_id) is not str or _RECEIPT_ID.fullmatch(receipt_id) is None:
            raise _fail("Receipt ID is not an issued receipt identifier.")
        identity_fields = {"project_id", "source_sha256", "review_revision", "snapshot_id"}
        raw_identity = data["identity"]
        if (
            type(raw_identity) is not dict
            or set(cast(dict[str, object], raw_identity)) != identity_fields
        ):
            raise _fail("Unsupported receipt identity fields.")
        identity_data = cast(dict[str, str], raw_identity)
        identity = Identity(
            identity_data["project_id"],
            identity_data["source_sha256"],
            identity_data["review_revision"],
            identity_data["snapshot_id"],
        ).checked()
        coverage = Coverage.from_record(data["coverage"])
        receipt = cls(packet_id, receipt_id, _path(data["path"]), identity, coverage)
        if _receipt_id(packet_id, identity, coverage) != receipt_id:
            raise _fail("Receipt ID does not match its issuance and coverage.", "tampered")
        return receipt

    @classmethod
    def parse(cls, raw: bytes) -> Self:
        try:
            return cls.from_record(records.decode(raw))
        except records.RecordError as error:
            raise _fail("Receipt is not a valid JSON record.") from error


@dataclass(frozen=True)
class Issuance:
    """One fresh packet issuance: opaque ID plus the receipts bound to it."""

    packet_id: str
    packet_kind: PacketKind
    identity: Identity
    receipts: tuple[Receipt, ...]


def issue(
    identity: Identity,
    packet_kind: PacketKind,
    planned: Sequence[tuple[str, Coverage]],
    *,
    packet_id: str | None = None,
) -> Issuance:
    """Issue receipts for planned ``(path, coverage)`` pairs under a fresh packet ID.

    ``packet_id`` exists for deterministic tests; production callers omit it so
    every issuance, including an unchanged re-issue, is distinct and unguessable.
    """
    identity.checked()
    if packet_kind not in PACKET_KINDS:
        raise _fail(f"Unknown packet kind {packet_kind!r}.")
    if packet_id is None:
        packet_id = "packet-" + secrets.token_hex(16)
    if _PACKET_ID.fullmatch(packet_id) is None:
        raise _fail("Packet ID is not an issued packet identifier.")
    if not planned:
        raise _fail("A packet needs at least one receipt.")
    is_summary = [coverage.view == "summary" for _, coverage in planned]
    if packet_kind == "summary" and not (len(planned) == 1 and is_summary[0]):
        raise _fail("A summary packet carries exactly one summary receipt.")
    if packet_kind == "views" and any(is_summary):
        raise _fail("A views packet carries no summary receipt.")
    paths = [_path(path) for path, _ in planned]
    if len(set(paths)) != len(paths):
        raise _fail("Receipt paths must be unique.")
    receipts = tuple(
        Receipt(
            packet_id,
            _receipt_id(packet_id, identity, coverage.checked()),
            path,
            identity,
            coverage,
        )
        for path, (_, coverage) in zip(paths, planned, strict=True)
    )
    if len({receipt.receipt_id for receipt in receipts}) != len(receipts):
        raise _fail("Two receipts in one issuance have identical coverage.")
    return Issuance(packet_id, packet_kind, identity, receipts)


def header_lines(receipt: Receipt) -> tuple[str, ...]:
    """The visible page/tile header: every identity the spec requires, from the receipt."""
    identity, coverage = receipt.identity, receipt.coverage
    lines = [
        f"Project: {identity.project_id}",
        f"Source snapshot: {identity.source_sha256}",
        f"Review revision: {identity.review_revision}",
        f"Export snapshot: {identity.snapshot_id}",
        f"Packet: {receipt.packet_id}",
        f"Receipt: {receipt.receipt_id}",
        f"View: {coverage.view}",
        f"Box: {coverage.box}",
        f"Scale: {coverage.scale}",
    ]
    if coverage.view == "summary":
        lines += [
            f"Unresolved roster: {coverage.unresolved_sha256}",
            f"Inspection/disposition: {coverage.inspection_sha256}",
        ]
    else:
        lines += [
            f"Source PDF page: {coverage.source_pdf_page}",
            f"Occurrence: {coverage.occurrence_id}",
            f"Image revision: {coverage.image_revision}",
            "Region: " + (", ".join(coverage.regions) if coverage.regions else "whole page"),
        ]
    return tuple(lines)


def header_text(receipt: Receipt) -> str:
    return "\n".join(header_lines(receipt))


@dataclass(frozen=True)
class Header:
    """A header as displayed in packet file ``path`` for the named receipt."""

    path: str
    receipt_id: str
    text: str


@dataclass(frozen=True)
class Descriptor:
    """Immutable, content-addressed presentation record of one complete issuance."""

    id: str
    raw: bytes
    packet_id: str
    packet_kind: PacketKind
    identity: Identity
    receipts: tuple[Receipt, ...]
    files: Mapping[str, tuple[str, int]]  # path -> (sha256, size)
    headers: tuple[tuple[str, str, str], ...]  # (path, receipt_id, header sha256)

    def receipt(self, receipt_id: str) -> Receipt | None:
        return next((item for item in self.receipts if item.receipt_id == receipt_id), None)

    @classmethod
    def parse(cls, raw: bytes, expected_id: str | None = None) -> Self:
        """Verify content address, grammar and that every receipt recomputes."""
        digest = _sha(raw)
        if expected_id is not None and expected_id != digest:
            raise _fail("Descriptor bytes do not match their content address.", "tampered")
        try:
            data = records.decode(raw)
        except records.RecordError as error:
            raise _fail("Descriptor is not a valid JSON record.") from error
        fields = {
            "format",
            "version",
            "packet_id",
            "packet_kind",
            "identity",
            "receipts",
            "files",
            "headers",
        }
        if set(data) != fields:
            raise _fail("Unsupported descriptor fields.")
        if (
            data["format"] != DESCRIPTOR_FORMAT
            or type(data["version"]) is not int
            or data["version"] != VERSION
        ):
            raise _fail("Unsupported descriptor format or version.")
        packet_id = data["packet_id"]
        kind = data["packet_kind"]
        if type(packet_id) is not str or _PACKET_ID.fullmatch(packet_id) is None:
            raise _fail("Descriptor packet ID is not an issued packet identifier.")
        if kind not in PACKET_KINDS:
            raise _fail(f"Unknown packet kind {kind!r}.")
        receipts_raw, files_raw, headers_raw = data["receipts"], data["files"], data["headers"]
        if (
            type(receipts_raw) is not list
            or type(files_raw) is not list
            or type(headers_raw) is not list
        ):
            raise _fail("Descriptor receipts/files/headers are not lists.")
        receipts = tuple(Receipt.from_record(item) for item in cast(list[object], receipts_raw))
        if not receipts or any(item.packet_id != packet_id for item in receipts):
            raise _fail("Descriptor receipts do not all belong to its issuance.", "tampered")
        identity = receipts[0].identity
        if any(item.identity != identity for item in receipts):
            raise _fail("Descriptor receipts name different projects/snapshots.", "tampered")
        if len({item.receipt_id for item in receipts}) != len(receipts):
            raise _fail("Descriptor repeats a receipt ID.", "tampered")
        files: dict[str, tuple[str, int]] = {}
        for entry in cast(list[object], files_raw):
            if type(entry) is not dict or set(cast(dict[str, object], entry)) != {
                "path",
                "sha256",
                "size",
            }:
                raise _fail("Unsupported descriptor file entry.")
            item = cast(dict[str, object], entry)
            path = _path(item["path"])
            size = item["size"]
            if path in files or type(size) is not int or size < 0:
                raise _fail("Descriptor file entry is duplicated or has an invalid size.")
            files[path] = (_digest(item["sha256"], "File digest"), size)
        headers: list[tuple[str, str, str]] = []
        for entry in cast(list[object], headers_raw):
            if type(entry) is not dict or set(cast(dict[str, object], entry)) != {
                "path",
                "receipt_id",
                "sha256",
            }:
                raise _fail("Unsupported descriptor header entry.")
            item = cast(dict[str, object], entry)
            path = _path(item["path"])
            receipt_id = item["receipt_id"]
            if path not in files or not any(r.receipt_id == receipt_id for r in receipts):
                raise _fail("Descriptor header names an unlisted file or receipt.", "tampered")
            headers.append((path, cast(str, receipt_id), _digest(item["sha256"], "Header digest")))
        for item in receipts:
            listed = files.get(item.path)
            if listed is None or listed != (_sha(item.raw()), len(item.raw())):
                raise _fail("A receipt file is not listed with its exact digest.", "tampered")
        descriptor = cls(
            digest,
            raw,
            packet_id,
            kind,
            identity,
            receipts,
            files,
            tuple(headers),
        )
        if raw != descriptor_bytes(descriptor):
            raise _fail("Descriptor is not in its canonical encoding.", "tampered")
        return descriptor


def descriptor_bytes(descriptor: Descriptor) -> bytes:
    body = {
        "format": DESCRIPTOR_FORMAT,
        "version": VERSION,
        "packet_id": descriptor.packet_id,
        "packet_kind": descriptor.packet_kind,
        "identity": descriptor.identity.record(),
        "receipts": [item.record() for item in descriptor.receipts],
        "files": [
            {"path": path, "sha256": digest, "size": size}
            for path, (digest, size) in sorted(descriptor.files.items())
        ],
        "headers": [
            {"path": path, "receipt_id": receipt_id, "sha256": digest}
            for path, receipt_id, digest in sorted(descriptor.headers)
        ],
    }
    return _json(body) + b"\n"


def describe(
    issuance: Issuance,
    files: Mapping[str, bytes],
    headers: Iterable[Header],
) -> Descriptor:
    """Build the immutable descriptor from the complete packet file contents.

    Every header must equal the header derived from its receipt, so header-to-receipt
    identity is guaranteed here rather than rechecked by consumers. The parse that
    seals the descriptor requires every receipt file with its exact digest.
    """
    listed: dict[str, tuple[str, int]] = {}
    for path, data in files.items():
        listed[_path(path)] = (_sha(data), len(data))
    by_id = {receipt.receipt_id: receipt for receipt in issuance.receipts}
    named: list[tuple[str, str, str]] = []
    for header in headers:
        receipt = by_id.get(header.receipt_id)
        if receipt is None or header.path not in listed:
            raise _fail("Header names a receipt or file outside this issuance.")
        if header.text != header_text(receipt):
            raise _fail(f"Header in {header.path} differs from its receipt identity.")
        named.append((header.path, header.receipt_id, _sha(header.text.encode("utf-8"))))
    draft = Descriptor(
        "",
        b"",
        issuance.packet_id,
        issuance.packet_kind,
        issuance.identity,
        issuance.receipts,
        listed,
        tuple(named),
    )
    raw = descriptor_bytes(draft)
    return Descriptor.parse(raw, _sha(raw))


def authenticate(
    descriptor: Descriptor,
    raw_receipt: bytes,
    *,
    project_id: str,
    source_sha256: str,
) -> Receipt:
    """Receipt JSON equals its saved descriptor entry for this project and source.

    Does not consult the current revision or any external packet file: durable
    replay lookup follows this check and precedes both.
    """
    receipt = Receipt.parse(raw_receipt)
    identity = descriptor.identity
    if identity.project_id != project_id or identity.source_sha256 != source_sha256:
        raise _fail("Descriptor belongs to a different project or source snapshot.", "foreign")
    # A receipt ID binds its issuance, project and coverage, so a receipt from another
    # packet, project or source is simply not listed here.
    saved = descriptor.receipt(receipt.receipt_id)
    if saved is None:
        raise _fail("Receipt was not issued by this packet descriptor.", "foreign")
    if saved != receipt or raw_receipt != saved.raw():
        raise _fail("Receipt differs from its saved descriptor entry.", "tampered")
    return saved


def _open_regular(directory: int, path: str) -> int:
    parts = path.split("/")
    current = os.dup(directory)
    try:
        for part in parts[:-1]:
            # O_NOFOLLOW: a replaced directory symlink is a changed packet, never followed.
            following = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current
            )
            os.close(current)
            current = following
        return os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
    finally:
        os.close(current)


def verify_files(descriptor: Descriptor, directory: int) -> None:
    """Every listed file exists unchanged; used only for a new action's integrity check."""
    problems: list[str] = []
    for path, (digest, size) in sorted(descriptor.files.items()):
        try:
            descriptor_fd = _open_regular(directory, path)
        except OSError:
            problems.append(f"{path} is missing or replaced")
            continue
        try:
            info = os.fstat(descriptor_fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size != size:
                problems.append(f"{path} changed size or type")
                continue
            hasher = hashlib.sha256()
            while chunk := os.read(descriptor_fd, 1 << 20):
                hasher.update(chunk)
            if hasher.hexdigest() != digest:
                problems.append(f"{path} changed content")
        finally:
            os.close(descriptor_fd)
    if problems:
        raise _fail(
            "Packet files differ from the issued packet: " + "; ".join(problems) + ".",
            "packet-file-changed",
        )
