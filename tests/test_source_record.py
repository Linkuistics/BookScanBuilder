"""Saved source meaning must be verified against bytes, never reconstructed from a report."""

import copy
import hashlib
import json
import os
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import cast

import pikepdf
import pytest

from bookscan import intake, ownership


@pytest.fixture
def source(owner: ownership.Writer, tmp_path: Path) -> intake.Snapshot:
    original = tmp_path / "Original café.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        page.obj.MediaBox = pikepdf.Array([82, 56, 10, 20])
        page.obj.CropBox = pikepdf.Array([70, 50, 22, 26])
        page.obj.Rotate = -270
        page.obj.UserUnit = 2
        page.obj.BookScanBuilder = pikepdf.Dictionary(
            Version=1, Role="front", SourceSHA256="a" * 64, SourcePage=23
        )
        pdf.add_blank_page(page_size=(36, 72))
        pdf.pages.append(page)
        pdf.save(original, min_version="1.7")
    return intake.snapshot(original, owner.path / "source.pdf")


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    path = tmp_path / "Book project"
    path.mkdir()
    identity = ownership.provision(path)
    with ownership.Writer.acquire(path, identity) as writer:
        yield writer


def test_source_loss_resume_preserves_all_occurrences_and_mapping(
    owner: ownership.Writer, source: intake.Snapshot
) -> None:
    from bookscan import source_record

    record = source_record.record(owner, source)
    raw = json.dumps(record, ensure_ascii=False).encode()
    expected = hashlib.sha256(source.path.read_bytes()).hexdigest()
    source.original_path.unlink()
    loaded = source_record.restore_json(owner, raw)
    assert loaded == source
    assert loaded.sha256 == expected
    assert [p.source_page for p in loaded.pages] == [1, 2, 3]
    assert loaded.pages[0] != loaded.pages[2]
    first = loaded.pages[0]
    assert first.geometry.boxes[:2] == ((82, 56, 10, 20), (70, 50, 22, 26))
    assert first.geometry.rotate == -270 and first.geometry.user_unit == 2
    assert first.frame.points == (72, 144) and first.frame.pixels == (300, 600)
    assert tuple(str(v) for v in first.frame.matrix) == (
        "0",
        "25/3",
        "25/3",
        "0",
        "-500/3",
        "-250/3",
    )
    assert first.hint == intake.Hint("front", "a" * 64, 23)
    assert loaded.pages[1].hint is None
    assert first.frame.extent_changed
    assert loaded.path.read_bytes() == source.path.read_bytes()
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)


def _pages(record: dict[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], record["pages"])


@pytest.mark.parametrize(
    "change",
    [
        "unknown",
        "version",
        "bool-version",
        "format",
        "path",
        "digest",
        "upper-digest",
        "original-relative",
        "original-nul",
        "identity-type",
        "identity-bool",
        "identity-size",
        "identity-inode",
        "identity-extra",
        "original-alias",
        "count",
        "order",
        "duplicate",
        "ordinal",
        "bool-ordinal",
        "id",
        "box",
        "rotate",
        "unit",
        "physical",
        "pixels",
        "matrix",
        "extent",
        "bool-rotate",
        "float-pixels",
        "hint",
        "hint-extra",
        "invented-hint",
        "document",
        "page-extra",
        "tuple-pages",
    ],
)
def test_corrupt_record_cannot_supply_source_or_page_truth(
    owner: ownership.Writer, source: intake.Snapshot, change: str
) -> None:
    from bookscan import source_record

    value = copy.deepcopy(source_record.record(owner, source))
    pages = _pages(value)
    first = pages[0]
    geometry = cast(dict[str, object], first["geometry"])
    identity = cast(dict[str, object], value["snapshot_identity"])
    if change == "unknown":
        value["acceptance"] = True
    elif change == "version":
        value["version"] = 2
    elif change == "bool-version":
        value["version"] = True
    elif change == "format":
        value["format"] = "BookScanBuilderGeometryReview"
    elif change == "path":
        value["snapshot"] = "../Original café.pdf"
    elif change in {"digest", "upper-digest"}:
        value["source_sha256"] = "0" * 64 if change == "digest" else "A" * 64
    elif change == "original-relative":
        value["original_path"] = "source.pdf"
    elif change == "original-nul":
        value["original_path"] = "/x\x00y"
    elif change == "identity-type":
        identity["size"] = str(identity["size"])
    elif change == "identity-bool":
        identity["device"] = False
    elif change == "identity-size":
        identity["size"] = cast(int, identity["size"]) + 1
    elif change == "identity-inode":
        identity["inode"] = 0
    elif change == "identity-extra":
        identity["optional"] = True
    elif change == "original-alias":
        value["original_identity"] = identity
    elif change == "count":
        pages.pop()
    elif change == "order":
        pages[0], pages[1] = pages[1], pages[0]
    elif change == "duplicate":
        pages[1] = copy.deepcopy(first)
    elif change == "ordinal":
        first["source_pdf_page"] = 3
    elif change == "bool-ordinal":
        first["source_pdf_page"] = True
    elif change == "id":
        first["id"] = "occ-000003"
    elif change == "box":
        cast(list[list[str]], geometry["boxes"])[0][0] = "83"
    elif change == "rotate":
        geometry["rotate"] = 90
    elif change == "bool-rotate":
        geometry["rotate"] = True
    elif change == "unit":
        geometry["user_unit"] = "1"
    elif change == "physical":
        geometry["physical_points"] = ["300", "600"]
    elif change == "pixels":
        geometry["pixels"] = [600, 300]
    elif change == "float-pixels":
        geometry["pixels"] = [300.0, 600.0]
    elif change == "matrix":
        geometry["matrix"] = ["1", "0", "0", "1", "0", "0"]
    elif change == "extent":
        geometry["extent_changed"] = 1
    elif change == "hint":
        cast(dict[str, object], first["advisory_hint"])["source_page"] = 24
    elif change == "hint-extra":
        cast(dict[str, object], first["advisory_hint"])["geometry_exempt"] = True
    elif change == "invented-hint":
        pages[1]["advisory_hint"] = first["advisory_hint"]
    elif change == "document":
        value["document"] = {"version": [1, 4], "extension_level": 0}
    elif change == "page-extra":
        first["inspected"] = True
    elif change == "tuple-pages":
        value["pages"] = tuple(pages)
    before = source.path.read_bytes()
    with pytest.raises(source_record.SourceRecordError) as raised:
        source_record.restore(owner, value)
    assert raised.value.code == "INVALID_PROJECT" and raised.value.exit_code == 3
    assert "baseline create" in raised.value.remediation
    assert "loses review facts" in raised.value.remediation
    assert source.path.read_bytes() == before
    owner.verify()


@pytest.mark.parametrize(
    "kind", ["missing", "bytes", "replacement", "symlink", "hardlink", "fifo", "directory"]
)
def test_changed_snapshot_never_resumes_even_with_identical_replacement_bytes(
    owner: ownership.Writer, source: intake.Snapshot, kind: str
) -> None:
    from bookscan import source_record

    value = source_record.record(owner, source)
    original = source.path.read_bytes()
    backup = owner.path / "old.pdf"
    source.path.rename(backup)
    if kind == "bytes":
        source.path.write_bytes(b"%PDF-bad")
    elif kind == "replacement":
        source.path.write_bytes(original)
    elif kind == "symlink":
        source.path.symlink_to(backup)
    elif kind == "hardlink":
        os.link(backup, source.path)
    elif kind == "fifo":
        os.mkfifo(source.path)
    elif kind == "directory":
        source.path.mkdir()
    with pytest.raises(source_record.SourceRecordError, match="INVALID_PROJECT"):
        source_record.restore(owner, value)
    assert backup.read_bytes() == original
    owner.verify()


@pytest.mark.parametrize("raw", [b"{}", b'{"version":1,"version":1}', b'{"x":NaN}', b"[]", b"\xff"])
def test_saved_json_grammar_is_checked_before_file_use(owner: ownership.Writer, raw: bytes) -> None:
    from bookscan import source_record

    with pytest.raises(source_record.SourceRecordError, match="INVALID_PROJECT"):
        source_record.restore_json(owner, raw)
    assert not (owner.path / "source.pdf").exists()


@pytest.mark.parametrize("change", ["wrong-path", "wrong-roster", "wrong-document"])
def test_recording_cannot_freeze_forged_in_memory_source_metadata(
    owner: ownership.Writer, source: intake.Snapshot, change: str
) -> None:
    from bookscan import source_record

    if change == "wrong-path":
        changed = replace(source, path=source.original_path)
    elif change == "wrong-roster":
        changed = replace(source, pages=source.pages[:1])
    else:
        changed = replace(source, document=replace(source.document, version=(1, 4)))
    with pytest.raises(source_record.SourceRecordError):
        source_record.record(owner, changed)


def test_cancellation_preserves_selected_failure_and_does_not_write(
    owner: ownership.Writer, source: intake.Snapshot
) -> None:
    from bookscan import source_record

    value = source_record.record(owner, source)
    selected = RuntimeError("owner cancellation")
    calls = 0

    def check() -> None:
        nonlocal calls
        calls += 1
        if calls == 5:
            raise selected

    before = source.path.read_bytes()
    with pytest.raises(RuntimeError) as raised:
        source_record.restore(owner, value, check_cancel=check)
    assert raised.value is selected and calls == 5
    assert source.path.read_bytes() == before
    owner.verify()


def test_complete_source_and_rgb_are_required_for_every_checkpoint_predecessor(
    owner: ownership.Writer, source: intake.Snapshot
) -> None:
    from bookscan import assets, project_header, source_record

    stores = project_header.Stores.provision(owner)
    saved = source_record.record(owner, source)
    image = stores.images.publish(b"\x00\x7f\xff", (1, 1))
    seen: list[str] = []

    def verify(images: assets.Assets, state: dict[str, object]) -> None:
        loaded = source_record.restore(images.owner, state["source"])
        assert images.read(assets.RGBAsset.from_record(state["rgb"])) == b"\x00\x7f\xff"
        seen.append(loaded.sha256)

    first = stores.checkpoints.commit(
        {"source": saved, "rgb": image.record(), "note": "first"},
        expected=None,
        verify_state=lambda state: verify(stores.images, state),
    ).checkpoint
    stores.checkpoints.commit(
        {"source": saved, "rgb": image.record(), "note": "second"},
        expected=first,
        verify_state=lambda state: verify(stores.images, state),
    )
    source.original_path.unlink()
    path = owner.path
    owner.close()
    seen.clear()
    with project_header.resume(
        path, verify_state=lambda stores, state: verify(stores.images, state)
    ) as (_, current):
        assert current.revision == 2 and current.state["note"] == "second"
    assert seen == [source.sha256, source.sha256]
    source.path.unlink()
    with pytest.raises(source_record.SourceRecordError):
        with project_header.resume(
            path, verify_state=lambda stores, state: verify(stores.images, state)
        ):
            pytest.fail("missing saved source was accepted")


@pytest.mark.parametrize("phase", ["before-inspection", "during-inspection", "after-inspection"])
def test_source_changed_during_read_is_rejected(
    owner: ownership.Writer, source: intake.Snapshot, phase: str
) -> None:
    from bookscan import source_record

    value = source_record.record(owner, source)
    calls = 0
    target = {"before-inspection": 2, "during-inspection": 6, "after-inspection": 13}[phase]
    changed = False

    def check() -> None:
        nonlocal calls, changed
        calls += 1
        if calls == target:
            source.path.write_bytes(source.path.read_bytes())
            changed = True

    with pytest.raises(source_record.SourceRecordError):
        source_record.restore(owner, value, check_cancel=check)
    assert changed
    owner.verify()


@pytest.mark.parametrize("selected", [False, True])
def test_native_close_failure_is_mapped_or_preserves_selected_cancellation(
    owner: ownership.Writer,
    source: intake.Snapshot,
    monkeypatch: pytest.MonkeyPatch,
    selected: bool,
) -> None:
    from bookscan import source_record

    value = source_record.record(owner, source)
    close = os.close
    expected = RuntimeError("selected cancellation")
    calls = 0

    def failed(descriptor: int) -> None:
        info = os.fstat(descriptor)
        close(descriptor)
        if info.st_ino == source.private_identity.inode:
            raise OSError("injected source close fault")

    def check() -> None:
        nonlocal calls
        calls += 1
        if selected and calls == 5:
            raise expected

    monkeypatch.setattr(source_record.os, "close", failed)
    with pytest.raises(RuntimeError if selected else source_record.SourceRecordError) as raised:
        source_record.restore(owner, value, check_cancel=check)
    if selected:
        assert raised.value is expected
        assert "source close fault" in " ".join(getattr(raised.value, "__notes__", []))
    else:
        assert cast(source_record.SourceRecordError, raised.value).exit_code == 3
    owner.verify()


def test_matching_digest_and_native_metadata_do_not_bypass_static_pdf_gate(
    owner: ownership.Writer, source: intake.Snapshot
) -> None:
    from bookscan import source_record

    value = source_record.record(owner, source)
    source.path.write_bytes(b"%PDF-1.7\ninvalid")
    value["source_sha256"] = hashlib.sha256(source.path.read_bytes()).hexdigest()
    info = source.path.stat()
    value["snapshot_identity"] = {
        "device": info.st_dev,
        "inode": info.st_ino,
        "size": info.st_size,
        "mtime_ns": info.st_mtime_ns,
        "ctime_ns": info.st_ctime_ns,
    }
    cast(dict[str, object], value["original_identity"])["size"] = info.st_size
    with pytest.raises(source_record.SourceRecordError, match="support"):
        source_record.restore(owner, value)


def test_original_path_is_never_opened_or_statted_on_resume(
    owner: ownership.Writer, source: intake.Snapshot, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import source_record

    value = source_record.record(owner, source)
    path_stat = Path.stat
    denied = 0

    def denied_stat(self: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        nonlocal denied
        if self == source.original_path:
            denied += 1
            raise PermissionError("original collection denied")
        return path_stat(self, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", denied_stat)
    with pytest.raises(PermissionError):
        source.original_path.stat()
    assert denied == 1
    assert source_record.restore(owner, value).sha256 == source.sha256
    assert denied == 1


@pytest.mark.parametrize("alias", ["symlink-parent", "case"])
def test_canonical_project_alias_uses_the_same_saved_source_and_writer(
    owner: ownership.Writer, source: intake.Snapshot, tmp_path: Path, alias: str
) -> None:
    from bookscan import source_record

    value = source_record.record(owner, source)
    path, identity = owner.path, owner.identity
    owner.close()
    if alias == "symlink-parent":
        parent = tmp_path / "alias"
        parent.symlink_to(path.parent, target_is_directory=True)
        alternate = parent / path.name
    else:
        alternate = path.with_name(path.name.swapcase())
        if not alternate.exists():
            pytest.skip("case-sensitive filesystem")
    with ownership.Writer.acquire(alternate, identity) as writer:
        assert source_record.restore(writer, value).path == path / "source.pdf"
        with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
            ownership.Writer.acquire(path, identity)


def test_lost_writer_refuses_a_source_read(
    owner: ownership.Writer, source: intake.Snapshot
) -> None:
    from bookscan import source_record

    value = source_record.record(owner, source)
    owner.close()
    with pytest.raises(ownership.OwnershipError):
        source_record.restore(owner, value)
