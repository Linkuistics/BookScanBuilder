"""Importer contracts: exact source bytes, support gates and independent physical mapping."""

import hashlib
import os
import stat
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pikepdf
import pytest

from bookscan import intake


def make_pdf(path: Path, *, hint: object = None, rotate: int = 0, unit: int = 1) -> None:
    with pikepdf.Pdf.new() as pdf:
        for _ in range(2):
            page = pdf.add_blank_page(page_size=(72, 36))
            page.obj.MediaBox = pikepdf.Array([10, 20, 82, 56])
            page.obj.CropBox = pikepdf.Array([22, 26, 70, 50])
            page.obj.BleedBox = pikepdf.Array([11, 21, 81, 55])
            page.obj.TrimBox = pikepdf.Array([12, 22, 80, 54])
            page.obj.ArtBox = pikepdf.Array([13, 23, 79, 53])
            page.obj.Rotate = rotate
            page.obj.UserUnit = unit
            if hint is not None:
                page.obj.BookScanBuilder = hint
        pdf.save(path, min_version="1.7")


def test_snapshot_retains_original_bytes_order_geometry_and_hint(tmp_path: Path) -> None:
    source, private = tmp_path / "Original book.pdf", tmp_path / "private.pdf"
    hint = pikepdf.Dictionary(Version=1, Role="front", SourceSHA256="a" * 64, SourcePage=23)
    make_pdf(source, hint=hint, rotate=-270, unit=2)
    original = source.read_bytes()
    result = intake.snapshot(source, private)
    assert private.read_bytes() == source.read_bytes() == original
    assert stat.S_IMODE(private.stat().st_mode) == 0o600
    assert result.sha256 == hashlib.sha256(original).hexdigest()
    assert [page.source_page for page in result.pages] == [1, 2]
    assert result.pages[0].geometry.rotate == -270
    assert result.pages[0].geometry.user_unit == 2
    assert result.pages[0].hint == intake.Hint("front", "a" * 64, 23)
    assert result.pages[0].geometry.boxes[4] == (13, 23, 79, 53)
    source.unlink()
    result.verify()  # The snapshot boundary never needs the original after successful copy.


@pytest.mark.parametrize(
    "hint",
    [
        None,
        "bad",
        pikepdf.Dictionary(Version=2),
        pikepdf.Dictionary(Version=True, Role="front", SourceSHA256="a" * 64, SourcePage=1),
        pikepdf.Dictionary(Version=1, Role="wrong", SourceSHA256="a" * 64, SourcePage=1),
        pikepdf.Dictionary(Version=1, Role="front", SourceSHA256="G" * 64, SourcePage=1),
        pikepdf.Dictionary(Version=1, Role="front", SourceSHA256="a" * 64, SourcePage=0),
    ],
)
def test_unavailable_advisory_hints_do_not_reject_ordinary_pdf(
    tmp_path: Path, hint: object
) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, hint=hint)
    result = intake.snapshot(source, tmp_path / "snapshot.pdf")
    assert all(page.hint is None for page in result.pages)


@pytest.mark.parametrize(
    ("rotate", "size", "corners"),
    [
        (0, (600, 300), [(0, 300), (600, 300), (600, 0), (0, 0)]),
        (90, (300, 600), [(0, 0), (0, 600), (300, 600), (300, 0)]),
        (180, (600, 300), [(600, 0), (0, 0), (0, 300), (600, 300)]),
        (270, (300, 600), [(300, 600), (300, 0), (0, 0), (0, 600)]),
        (-270, (300, 600), [(0, 0), (0, 600), (300, 600), (300, 0)]),
    ],
)
def test_independent_page_corner_mapping(
    tmp_path: Path, rotate: int, size: tuple[int, int], corners: list[tuple[int, int]]
) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, rotate=rotate, unit=2)
    frame = intake.snapshot(source, tmp_path / "snapshot.pdf").pages[0].frame
    assert frame.pixels == size
    assert frame.points == ((144, 72) if rotate % 180 == 0 else (72, 144))
    assert [
        frame.map_point(Decimal(x), Decimal(y)) for x, y in [(10, 20), (82, 20), (82, 56), (10, 56)]
    ] == corners
    assert frame.extent_changed


def test_reversed_and_inherited_boxes_preserve_original_coordinates(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        page.obj.Parent.MediaBox = pikepdf.Array([82, 56, 10, 20])
        page.obj.Parent.CropBox = pikepdf.Array([70, 50, 22, 26])
        page.obj.Parent.Rotate = 450
        del page.obj.MediaBox
        pdf.save(source)
    page = intake.snapshot(source, tmp_path / "snapshot.pdf").pages[0]
    assert page.geometry.boxes[:2] == ((82, 56, 10, 20), (70, 50, 22, 26))
    assert page.frame.pixels == (150, 300)
    assert page.frame.map_point(Decimal(10), Decimal(20)) == (0, 0)


@pytest.mark.parametrize(
    "feature", ["document", "nested", "late-page", "encrypted", "empty", "malformed"]
)
def test_source_support_failures_leave_no_snapshot(tmp_path: Path, feature: str) -> None:
    source, private = tmp_path / "source.pdf", tmp_path / "snapshot.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page()
        if feature == "document":
            pdf.Root.OCProperties = pikepdf.Dictionary()
        elif feature == "nested":
            page.obj.Resources.XObject = pikepdf.Dictionary(
                Im=pdf.make_stream(b"bad", F="external")  # pyright: ignore[reportUnknownMemberType]
            )
        elif feature == "late-page":
            bad = pdf.add_blank_page()
            bad.obj.Rotate = 13
        elif feature == "empty":
            del pdf.pages[0]
        pdf.save(
            source,
            encryption=pikepdf.Encryption(owner="x", user="") if feature == "encrypted" else False,
        )
    if feature == "malformed":
        source.write_bytes(b"%PDF-1.7\nnot a PDF")
    original = source.read_bytes()
    with pytest.raises(intake.ImportFailure) as raised:
        intake.snapshot(source, private)
    assert raised.value.code == ("SOURCE_EMPTY" if feature == "empty" else "SOURCE_UNSUPPORTED")
    assert raised.value.exit_code == 3
    assert not private.exists()
    assert source.read_bytes() == original


def test_missing_and_nonregular_input(tmp_path: Path) -> None:
    with pytest.raises(intake.ImportFailure, match="SOURCE_NOT_FOUND"):
        intake.snapshot(tmp_path / "missing", tmp_path / "snapshot")
    with pytest.raises(intake.ImportFailure, match="SOURCE_UNREADABLE"):
        intake.snapshot(tmp_path, tmp_path / "snapshot")


@pytest.mark.parametrize("alias", ["same", "symlink", "hardlink"])
def test_source_alias_precedes_occupied_destination(tmp_path: Path, alias: str) -> None:
    source, private = tmp_path / "source.pdf", tmp_path / "snapshot.pdf"
    make_pdf(source)
    if alias == "same":
        private = source
    elif alias == "symlink":
        private.symlink_to(source)
    else:
        os.link(source, private)
    original = source.read_bytes()
    with pytest.raises(intake.ImportFailure) as raised:
        intake.snapshot(source, private)
    assert raised.value.code == "SOURCE_OUTPUT_COLLISION"
    assert source.read_bytes() == original


@pytest.mark.parametrize("kind", ["regular", "dangling", "directory"])
def test_occupied_private_destination_is_never_replaced(tmp_path: Path, kind: str) -> None:
    source, private = tmp_path / "source.pdf", tmp_path / "snapshot.pdf"
    make_pdf(source)
    if kind == "regular":
        private.write_bytes(b"previous")
    elif kind == "dangling":
        private.symlink_to(tmp_path / "missing")
    else:
        private.mkdir()
    with pytest.raises(intake.ImportFailure) as raised:
        intake.snapshot(source, private)
    assert raised.value.code == "OUTPUT_EXISTS"
    assert os.path.lexists(private)
    if kind == "regular":
        assert private.read_bytes() == b"previous"


@pytest.mark.parametrize("fault", ["change", "replace", "cancel", "tamper", "replace-private"])
def test_copy_boundary_rechecks_identity_digest_and_preserves_selected_cancellation(
    tmp_path: Path,
    fault: str,
) -> None:
    source, private = tmp_path / "source.pdf", tmp_path / "snapshot.pdf"
    make_pdf(source)
    original = source.read_bytes()
    triggered = False
    selected = RuntimeError("owner interrupted")

    def check() -> None:
        nonlocal triggered
        if private.exists() and private.stat().st_size > 0 and not triggered:
            triggered = True
            if fault == "cancel":
                raise selected
            if fault == "replace-private":
                private.unlink()
                private.write_bytes(b"replacement belongs to someone else")
            elif fault == "tamper":
                with private.open("r+b") as stream:
                    stream.write(b"changed")
            elif fault == "replace":
                source.unlink()
                source.write_bytes(original)
            else:
                with source.open("r+b") as stream:
                    stream.write(b"changed")

    with pytest.raises((intake.ImportFailure, RuntimeError)) as raised:
        intake.snapshot(source, private, check_cancel=check)
    assert triggered
    if fault == "cancel":
        assert raised.value is selected
    else:
        assert isinstance(raised.value, intake.ImportFailure)
        assert raised.value.code in {"SOURCE_CHANGED", "WRITE_FAILED"}
    if fault == "replace-private":
        assert private.read_bytes() == b"replacement belongs to someone else"
    else:
        assert not private.exists()


def test_saved_snapshot_verification_rejects_replacement_and_byte_damage(tmp_path: Path) -> None:
    source, private = tmp_path / "source.pdf", tmp_path / "snapshot.pdf"
    make_pdf(source)
    result = intake.snapshot(source, private)
    private.write_bytes(b"corrupt")
    with pytest.raises(intake.ImportFailure) as raised:
        result.verify()
    assert raised.value.code == "INVALID_PROJECT"


def test_selected_source_symlink_retarget_is_detected(tmp_path: Path) -> None:
    original, other = tmp_path / "original.pdf", tmp_path / "other.pdf"
    selected, private = tmp_path / "selected.pdf", tmp_path / "snapshot.pdf"
    make_pdf(original)
    make_pdf(other)
    selected.symlink_to(original)
    triggered = False

    def check() -> None:
        nonlocal triggered
        if private.exists() and not triggered:
            selected.unlink()
            selected.symlink_to(other)
            triggered = True

    with pytest.raises(intake.ImportFailure) as raised:
        intake.snapshot(selected, private, check_cancel=check)
    assert raised.value.code == "SOURCE_CHANGED"
    assert not private.exists()


def test_fifo_is_rejected_without_waiting_for_a_writer(tmp_path: Path) -> None:
    source = tmp_path / "fifo"
    os.mkfifo(source)
    with pytest.raises(intake.ImportFailure) as raised:
        intake.snapshot(source, tmp_path / "snapshot")
    assert raised.value.code == "SOURCE_UNREADABLE"


@pytest.mark.parametrize("phase", ["fchmod", "fsync"])
def test_private_io_failure_removes_only_owned_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    source, private = tmp_path / "source.pdf", tmp_path / "snapshot.pdf"
    make_pdf(source)
    original = source.read_bytes()

    def fail(*args: object) -> None:
        raise OSError("selected I/O failure")

    monkeypatch.setattr(intake.os, phase, fail)
    with pytest.raises(intake.ImportFailure) as raised:
        intake.snapshot(source, private)
    assert raised.value.code == "WRITE_FAILED"
    assert not private.exists()
    assert source.read_bytes() == original


def test_partial_pixels_are_retained_without_rounding_physical_extent(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(3, 5))
        page.obj.CropBox = pikepdf.Array([-1, -1, 4, 6])
        pdf.save(source)
    frame = intake.snapshot(source, tmp_path / "snapshot.pdf").pages[0].frame
    assert frame.pixels == (13, 21)
    assert frame.points == (3, 5)
    assert frame.map_point(Decimal(3), Decimal(0)) == (Decimal("12.5"), Fraction(125, 6))
    assert not frame.extent_changed


def test_private_stream_acquisition_failure_does_not_leak_file_or_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, private = tmp_path / "source.pdf", tmp_path / "snapshot.pdf"
    make_pdf(source)
    real = intake.os.fdopen
    observed: list[int] = []

    def fail(fd: int, mode: str) -> object:
        if mode == "w+b":
            observed.append(fd)
            raise OSError("cannot wrap acquired descriptor")
        return real(fd, mode)

    monkeypatch.setattr(intake.os, "fdopen", fail)
    with pytest.raises(intake.ImportFailure) as raised:
        intake.snapshot(source, private)
    assert raised.value.code == "WRITE_FAILED"
    assert not private.exists()
    assert len(observed) == 1
    with pytest.raises(OSError):
        os.fstat(observed[0])
