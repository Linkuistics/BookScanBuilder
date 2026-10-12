"""Packet issuance, receipt authenticity, descriptor content address and file integrity."""

import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from bookscan.packet_receipts import (
    Coverage,
    Descriptor,
    Header,
    Identity,
    Issuance,
    Receipt,
    ReceiptError,
    authenticate,
    describe,
    header_lines,
    header_text,
    issue,
    verify_files,
)

D = {name: hashlib.sha256(name.encode()).hexdigest() for name in "abcdef"}
IDENTITY = Identity("project-0123", D["a"], D["b"], D["c"])
type Json = dict[str, Any]
PACKET = "packet-" + "0" * 32
OTHER_PACKET = "packet-" + "1" * 32


def full(**changes: object) -> Coverage:
    base = Coverage(
        "full",
        occurrence_id="occ-000001",
        source_pdf_page=1,
        image_revision=D["d"],
        box="MediaBox (CropBox guide)",
        scale="0.24 point per pixel",
    )
    return replace(base, **changes)


def native(*regions: str) -> Coverage:
    return full(view="native", regions=regions or ("native-001",), scale="1 point per pixel")


def summary() -> Coverage:
    return Coverage(
        "summary",
        box="Whole export snapshot",
        scale="not applicable",
        unresolved_sha256=D["e"],
        inspection_sha256=D["f"],
    )


def issuance(packet_id: str = PACKET) -> Issuance:
    return issue(
        IDENTITY,
        "views",
        [("receipts/full.json", full()), ("receipts/native-001.json", native("native-001"))],
        packet_id=packet_id,
    )


def files_for(item: Issuance) -> dict[str, bytes]:
    files = {receipt.path: receipt.raw() for receipt in item.receipts}
    files["index.pdf"] = b"%PDF-index"
    files["views/full.pdf"] = b"%PDF-full"
    return files


def headers_for(item: Issuance) -> list[Header]:
    return [Header("views/full.pdf", r.receipt_id, header_text(r)) for r in item.receipts]


def described(packet_id: str = PACKET) -> tuple[Issuance, Descriptor]:
    item = issuance(packet_id)
    return item, describe(item, files_for(item), headers_for(item))


# --- issuance --------------------------------------------------------------


def test_fresh_issuance_ids_differ_for_identical_views_at_unchanged_snapshot() -> None:
    plan = [("r.json", full())]
    first = issue(IDENTITY, "views", plan)
    second = issue(IDENTITY, "views", plan)
    assert first.packet_id != second.packet_id
    assert first.receipts[0].receipt_id != second.receipts[0].receipt_id
    assert first.packet_id.startswith("packet-") and len(first.packet_id) == 39


def test_unchanged_summaries_get_distinct_content_addressed_descriptors() -> None:
    plan = [("receipt.json", summary())]
    descriptors: list[Descriptor] = []
    for _ in range(2):
        item = issue(IDENTITY, "summary", plan)
        descriptors.append(describe(item, {"receipt.json": item.receipts[0].raw()}, []))
    assert descriptors[0].id != descriptors[1].id


def test_receipt_id_is_deterministic_for_fixed_issuance_and_binds_every_coverage_field() -> None:
    assert issuance().receipts[0].receipt_id == issuance().receipts[0].receipt_id
    base = issue(IDENTITY, "views", [("r.json", full())], packet_id=PACKET).receipts[0].receipt_id
    changed = [
        full(occurrence_id="occ-000002"),
        full(source_pdf_page=2),
        full(image_revision=D["e"]),
        full(box="CropBox"),
        full(scale="0.25 point per pixel"),
        native("native-001"),
    ]
    ids = {
        issue(IDENTITY, "views", [("r.json", c)], packet_id=PACKET).receipts[0].receipt_id
        for c in changed
    }
    assert base not in ids and len(ids) == len(changed)
    for identity in (
        replace(IDENTITY, project_id="project-other"),
        replace(IDENTITY, source_sha256=D["e"]),
        replace(IDENTITY, review_revision=D["e"]),
        replace(IDENTITY, snapshot_id=D["e"]),
    ):
        other = issue(identity, "views", [("r.json", full())], packet_id=PACKET).receipts[0]
        assert other.receipt_id != base
    assert (
        issue(IDENTITY, "views", [("r.json", full())], packet_id=OTHER_PACKET)
        .receipts[0]
        .receipt_id
        != base
    )


@pytest.mark.parametrize(
    "coverage",
    [
        full(regions=("native-001",)),  # full never names regions
        native(),  # placeholder replaced below
    ],
)
def test_invalid_full_coverage_is_rejected(coverage: Coverage) -> None:
    if coverage.view == "native":
        coverage = replace(coverage, regions=())
    with pytest.raises(ReceiptError):
        issue(IDENTITY, "views", [("r.json", coverage)])


@pytest.mark.parametrize(
    "coverage",
    [
        native("native-002", "native-001"),  # unsorted
        native("native-001", "native-001"),  # repeated
        native("tile-1"),  # not a region identifier
        full(source_pdf_page=0),
        full(image_revision="abc"),
        full(occurrence_id=""),
        full(unresolved_sha256=D["e"]),  # digests belong to summaries only
        replace(summary(), occurrence_id="occ-000001"),
        replace(summary(), unresolved_sha256=None),
        replace(summary(), inspection_sha256="zz"),
        full(scale=""),
        full(box="Media\nBox"),
    ],
)
def test_invalid_coverage_is_rejected(coverage: Coverage) -> None:
    with pytest.raises(ReceiptError):
        issue(
            IDENTITY, "views" if coverage.view != "summary" else "summary", [("r.json", coverage)]
        )


def test_packet_kind_and_path_rules() -> None:
    with pytest.raises(ReceiptError):
        issue(IDENTITY, "views", [("r.json", summary())])
    with pytest.raises(ReceiptError):
        issue(IDENTITY, "summary", [("r.json", full())])
    with pytest.raises(ReceiptError):
        issue(IDENTITY, "summary", [("a.json", summary()), ("b.json", summary())])
    with pytest.raises(ReceiptError):
        issue(IDENTITY, "views", [("r.json", full()), ("r.json", native())])
    with pytest.raises(ReceiptError):  # identical coverage twice in one issuance
        issue(IDENTITY, "views", [("a.json", full()), ("b.json", full())])
    with pytest.raises(ReceiptError):
        issue(IDENTITY, "views", [])
    for bad in ("/abs.json", "../up.json", "a//b.json", "a/./b.json", "a\\b.json", ""):
        with pytest.raises(ReceiptError):
            issue(IDENTITY, "views", [(bad, full())])
    with pytest.raises(ReceiptError):
        issue(IDENTITY, "views", [("r.json", full())], packet_id="packet-xyz")


# --- receipt grammar -------------------------------------------------------


def test_receipt_round_trips_exactly() -> None:
    receipt = issuance().receipts[1]
    again = Receipt.parse(receipt.raw())
    assert again == receipt and again.raw() == receipt.raw()
    assert again.coverage.regions == ("native-001",)


def test_receipt_rejects_unknown_fields_version_format_and_duplicates() -> None:
    record: Json = issuance().receipts[0].record()
    mutations: list[Callable[[Json], object]] = [
        lambda r: r.update(extra=1),
        lambda r: r.update(version=2),
        lambda r: r.update(format="Other"),
        lambda r: r.pop("path"),
        lambda r: r["coverage"].update(extra=1),
        lambda r: r["identity"].update(extra=1),
    ]
    for mutate in mutations:
        copy = json.loads(json.dumps(record))
        mutate(copy)
        with pytest.raises(ReceiptError):
            Receipt.parse(json.dumps(copy).encode())
    with pytest.raises(ReceiptError):
        Receipt.parse(b'{"format":"x","format":"y"}')
    with pytest.raises(ReceiptError):
        Receipt.parse(b"not json")
    with pytest.raises(ReceiptError):
        Receipt.parse(b"[]")


def test_edited_receipt_value_fails_id_recomputation_as_tampered() -> None:
    record: Json = issuance().receipts[0].record()
    record["coverage"]["occurrence_id"] = "occ-000099"
    with pytest.raises(ReceiptError) as caught:
        Receipt.parse(json.dumps(record).encode())
    assert caught.value.context == "tampered" and caught.value.exit_code == 6


# --- header identity -------------------------------------------------------


def test_headers_name_every_required_identity_from_the_receipt() -> None:
    receipt = issuance().receipts[1]
    fields = dict(line.split(": ", 1) for line in header_lines(receipt))
    assert fields["Project"] == IDENTITY.project_id
    assert fields["Source snapshot"] == IDENTITY.source_sha256
    assert fields["Review revision"] == IDENTITY.review_revision
    assert fields["Packet"] == PACKET and fields["Receipt"] == receipt.receipt_id
    assert fields["Source PDF page"] == "1"
    assert fields["Occurrence"] == "occ-000001"
    assert fields["Image revision"] == D["d"]
    assert fields["View"] == "native" and fields["Region"] == "native-001"
    assert fields["Box"] == "MediaBox (CropBox guide)" and fields["Scale"] == "1 point per pixel"
    assert (
        dict(line.split(": ", 1) for line in header_lines(issuance().receipts[0]))["Region"]
        == "whole page"
    )


def test_summary_header_names_snapshot_and_roster_digests_not_an_occurrence() -> None:
    item = issue(IDENTITY, "summary", [("receipt.json", summary())], packet_id=PACKET)
    fields = dict(line.split(": ", 1) for line in header_lines(item.receipts[0]))
    assert fields["Export snapshot"] == IDENTITY.snapshot_id
    assert fields["Unresolved roster"] == D["e"] and fields["Inspection/disposition"] == D["f"]
    assert "Occurrence" not in fields


# --- descriptor ------------------------------------------------------------


def test_descriptor_is_content_addressed_canonical_and_reparses() -> None:
    item, descriptor = described()
    assert descriptor.id == hashlib.sha256(descriptor.raw).hexdigest()
    again = Descriptor.parse(descriptor.raw, descriptor.id)
    assert again == descriptor
    assert set(descriptor.files) == {
        "index.pdf",
        "views/full.pdf",
        *(r.path for r in item.receipts),
    }
    assert len(descriptor.headers) == 2
    assert descriptor.receipt(item.receipts[1].receipt_id) == item.receipts[1]


def test_describe_requires_every_receipt_file_with_exact_bytes() -> None:
    item = issuance()
    files = files_for(item)
    missing = {k: v for k, v in files.items() if k != "receipts/full.json"}
    with pytest.raises(ReceiptError):
        describe(item, missing, [])
    files["receipts/full.json"] = files["receipts/full.json"] + b" "
    with pytest.raises(ReceiptError):
        describe(item, files, [])


def test_describe_rejects_headers_that_differ_from_their_receipt_or_issuance() -> None:
    item = issuance()
    files = files_for(item)
    good = item.receipts[0]
    with pytest.raises(ReceiptError):
        describe(
            item, files, [Header("views/full.pdf", good.receipt_id, header_text(good) + "\nX: y")]
        )
    with pytest.raises(ReceiptError):
        describe(item, files, [Header("views/full.pdf", "receipt-" + "9" * 64, header_text(good))])
    with pytest.raises(ReceiptError):
        describe(item, files, [Header("views/absent.pdf", good.receipt_id, header_text(good))])
    other = issuance(OTHER_PACKET).receipts[0]  # a header from a different issuance
    with pytest.raises(ReceiptError):
        describe(item, files, [Header("views/full.pdf", other.receipt_id, header_text(other))])


def test_describe_rejects_unsafe_file_paths() -> None:
    item = issuance()
    files = files_for(item)
    files["../escape.pdf"] = b"x"
    with pytest.raises(ReceiptError):
        describe(item, files, [])


def test_descriptor_parse_rejects_wrong_address_or_edited_bytes() -> None:
    _, descriptor = described()
    with pytest.raises(ReceiptError) as caught:
        Descriptor.parse(descriptor.raw, "0" * 64)
    assert caught.value.context == "tampered"
    edited = descriptor.raw.replace(b"index.pdf", b"index.pdg")
    with pytest.raises(ReceiptError) as changed:
        Descriptor.parse(edited, descriptor.id)  # the saved address catches any edit
    assert changed.value.context == "tampered"
    assert Descriptor.parse(edited).id != descriptor.id  # a different, self-consistent issuance


def canonical(record: object) -> bytes:
    """Re-encode an edited record canonically, so only its meaning can be rejected."""
    return (
        json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        + b"\n"
    )


def relisted(record: Json, receipt: Receipt) -> None:
    """Point one file entry at a replacement receipt's exact bytes."""
    for entry in record["files"]:
        if entry["path"] == receipt.path:
            entry["sha256"], entry["size"] = (
                hashlib.sha256(receipt.raw()).hexdigest(),
                len(receipt.raw()),
            )


def edited_descriptor() -> Json:
    _, descriptor = described()
    record = json.loads(descriptor.raw)
    assert canonical(record) == descriptor.raw  # the control: unedited bytes are accepted
    Descriptor.parse(canonical(record))
    return record


def test_descriptor_parse_rejects_missing_receipt_file_listing() -> None:
    record = edited_descriptor()
    record["files"] = [f for f in record["files"] if f["path"] != "receipts/full.json"]
    with pytest.raises(ReceiptError):
        Descriptor.parse(canonical(record))


def test_descriptor_parse_rejects_a_receipt_file_listed_with_other_bytes() -> None:
    record = edited_descriptor()
    for entry in record["files"]:
        if entry["path"] == "receipts/full.json":
            entry["sha256"] = hashlib.sha256(b"other receipt bytes").hexdigest()
    with pytest.raises(ReceiptError):
        Descriptor.parse(canonical(record))


def test_descriptor_parse_rejects_receipt_from_another_issuance_even_if_listed() -> None:
    record = edited_descriptor()
    foreign = issuance(OTHER_PACKET).receipts[1]  # fully valid, files updated to match
    record["receipts"][1] = foreign.record()
    relisted(record, foreign)
    record["headers"] = []
    with pytest.raises(ReceiptError) as caught:
        Descriptor.parse(canonical(record))
    assert caught.value.context == "tampered"


def test_descriptor_parse_rejects_receipts_naming_different_projects() -> None:
    record = edited_descriptor()
    stranger = issue(
        replace(IDENTITY, project_id="project-other"),
        "views",
        [("receipts/native-001.json", native("native-001"))],
        packet_id=PACKET,
    ).receipts[0]
    record["receipts"][1] = stranger.record()  # same issuance, different project
    relisted(record, stranger)
    record["headers"] = []
    with pytest.raises(ReceiptError):
        Descriptor.parse(canonical(record))


def test_descriptor_parse_rejects_a_repeated_receipt() -> None:
    record = edited_descriptor()
    record["receipts"].append(record["receipts"][0])
    with pytest.raises(ReceiptError):
        Descriptor.parse(canonical(record))


def test_descriptor_parse_rejects_headers_for_unlisted_files_or_unknown_receipts() -> None:
    record = edited_descriptor()
    digest = hashlib.sha256(b"h").hexdigest()
    real = record["receipts"][0]["receipt_id"]
    for entry in (
        {"path": "zzz-ghost.pdf", "receipt_id": real, "sha256": digest},
        {"path": "index.pdf", "receipt_id": "receipt-" + "9" * 64, "sha256": digest},
    ):
        edited = json.loads(json.dumps(record))
        edited["headers"].append(entry)
        with pytest.raises(ReceiptError):
            Descriptor.parse(canonical(edited))


def test_descriptor_parse_rejects_wrong_version_and_noncanonical_encoding() -> None:
    record = edited_descriptor()
    record["version"] = 2
    with pytest.raises(ReceiptError):
        Descriptor.parse(canonical(record))
    record["version"] = 1
    with pytest.raises(ReceiptError):  # valid JSON, not the canonical encoding
        Descriptor.parse(json.dumps(record, indent=2).encode())


# --- authenticity ----------------------------------------------------------


def test_authenticate_accepts_the_saved_receipt_without_touching_files() -> None:
    item, descriptor = described()
    for receipt in item.receipts:
        got = authenticate(
            descriptor, receipt.raw(), project_id=IDENTITY.project_id, source_sha256=D["a"]
        )
        assert got == receipt


@pytest.mark.parametrize(
    ("project", "source", "context"),
    [("project-other", D["a"], "foreign"), ("project-0123", D["e"], "foreign")],
)
def test_authenticate_rejects_a_foreign_project_or_source(
    project: str, source: str, context: str
) -> None:
    item, descriptor = described()
    with pytest.raises(ReceiptError) as caught:
        authenticate(descriptor, item.receipts[0].raw(), project_id=project, source_sha256=source)
    assert caught.value.context == context and caught.value.exit_code == 6


def test_authenticate_rejects_receipts_issued_for_another_project_or_source() -> None:
    _, descriptor = described()
    for identity in (
        replace(IDENTITY, project_id="project-other"),
        replace(IDENTITY, source_sha256=D["e"]),
    ):
        stranger = issue(identity, "views", [("receipts/full.json", full())], packet_id=PACKET)
        with pytest.raises(ReceiptError) as caught:
            authenticate(
                descriptor,
                stranger.receipts[0].raw(),
                project_id="project-0123",
                source_sha256=D["a"],
            )
        assert caught.value.context == "foreign"


def test_authenticate_rejects_receipt_from_another_issuance_with_identical_coverage() -> None:
    _, descriptor = described()
    twin = issuance(OTHER_PACKET).receipts[0]
    with pytest.raises(ReceiptError) as caught:
        authenticate(descriptor, twin.raw(), project_id=IDENTITY.project_id, source_sha256=D["a"])
    assert caught.value.context == "foreign"


def test_authenticate_rejects_receipt_not_listed_or_reformatted() -> None:
    item, descriptor = described()
    extra = issue(
        IDENTITY, "views", [("receipts/extra.json", full(source_pdf_page=2))], packet_id=PACKET
    )
    with pytest.raises(ReceiptError) as listed:
        authenticate(
            descriptor,
            extra.receipts[0].raw(),
            project_id=IDENTITY.project_id,
            source_sha256=D["a"],
        )
    assert listed.value.context == "foreign"
    reformatted = json.dumps(item.receipts[0].record(), indent=1).encode()
    with pytest.raises(ReceiptError) as caught:
        authenticate(descriptor, reformatted, project_id=IDENTITY.project_id, source_sha256=D["a"])
    assert caught.value.context == "tampered"
    with pytest.raises(ReceiptError):
        authenticate(descriptor, b"garbage", project_id=IDENTITY.project_id, source_sha256=D["a"])


# --- external file integrity -----------------------------------------------


def packet_dir(tmp_path: Path, item: Issuance) -> Path:
    root = tmp_path / "packet"
    for path, data in files_for(item).items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return root


def check(root: Path, descriptor: Descriptor) -> None:
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        verify_files(descriptor, fd)
    finally:
        os.close(fd)


def test_verify_files_accepts_the_unchanged_packet(tmp_path: Path) -> None:
    item, descriptor = described()
    check(packet_dir(tmp_path, item), descriptor)
    # Additional files (a viewer's sidecar) are not part of the issued packet.
    (tmp_path / "packet" / "sidecar.tmp").write_bytes(b"x")
    check(tmp_path / "packet", descriptor)


@pytest.mark.parametrize("path", ["index.pdf", "views/full.pdf", "receipts/native-001.json"])
def test_verify_files_names_a_changed_file_as_packet_file_changed(
    tmp_path: Path, path: str
) -> None:
    item, descriptor = described()
    root = packet_dir(tmp_path, item)
    original = (root / path).read_bytes()
    (root / path).write_bytes(original[:-1] + b"Z")  # same size, different content
    with pytest.raises(ReceiptError) as caught:
        check(root, descriptor)
    assert caught.value.context == "packet-file-changed" and path in caught.value.message
    (root / path).write_bytes(original + b"+")  # different size
    with pytest.raises(ReceiptError):
        check(root, descriptor)


def test_verify_files_rejects_missing_file_and_replaced_symlinks(tmp_path: Path) -> None:
    item, descriptor = described()
    root = packet_dir(tmp_path, item)
    (root / "index.pdf").unlink()
    with pytest.raises(ReceiptError):
        check(root, descriptor)
    root = packet_dir(tmp_path / "second", item)
    kept = (root / "views" / "full.pdf").read_bytes()
    elsewhere = tmp_path / "elsewhere.pdf"
    elsewhere.write_bytes(kept)  # identical bytes, but reached through a symlink
    (root / "views" / "full.pdf").unlink()
    (root / "views" / "full.pdf").symlink_to(elsewhere)
    with pytest.raises(ReceiptError):
        check(root, descriptor)
    root = packet_dir(tmp_path / "third", item)
    moved = tmp_path / "moved"
    (root / "views").rename(moved)
    (root / "views").symlink_to(moved)  # a replaced directory is never followed
    with pytest.raises(ReceiptError):
        check(root, descriptor)
