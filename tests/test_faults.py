import io
import os
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pikepdf
import pytest
from pdf_fixtures import raw_pdf
from test_preview import labels

from bookscan.prepare import plan
from bookscan.preview import run
from bookscan.results import PreparationError
from bookscan.selections import parse


def arguments(path: Path) -> list[str]:
    return ["--content", str(path), "--output", str(path.parent / "out.pdf"), "--dry-run"]


@pytest.mark.parametrize("change", ["bytes", "mtime", "replace", "remove"])
def test_source_recheck_detects_changes(tmp_path: Path, change: str) -> None:
    path = labels(tmp_path / "in.pdf")
    request = parse(arguments(path))
    original_stat = path.stat()

    def mutate() -> None:
        if change == "remove":
            path.unlink()
        elif change == "replace":
            replacement = path.parent / "replacement"
            replacement.write_bytes(path.read_bytes())
            replacement.replace(path)
        elif change == "mtime":
            os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns + 1_000_000))
        else:
            contents = path.read_bytes()
            path.write_bytes(contents.replace(b"PDF", b"PDE", 1))
            os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))

    with pytest.raises(PreparationError) as exc:
        plan(request, before_recheck=mutate)
    assert exc.value.code == "SOURCE_CHANGED"
    assert not (tmp_path / "out.pdf").exists()


def test_no_output_or_temporary_creation_copy_or_save(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = labels(tmp_path / "in.pdf")
    before = sorted(tmp_path.iterdir())
    real_open = os.open

    def readonly_open(
        name: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        assert not flags & (os.O_CREAT | os.O_WRONLY | os.O_RDWR | os.O_TRUNC)
        return real_open(name, flags, mode, dir_fd=dir_fd)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Preview attempted write/copy/output validation")

    import tempfile

    monkeypatch.setattr(os, "open", readonly_open)
    monkeypatch.setattr(tempfile, "mkstemp", forbidden)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", forbidden)
    monkeypatch.setattr(pikepdf.Pdf, "save", forbidden)
    monkeypatch.setattr(pikepdf.Pdf, "new", forbidden)
    monkeypatch.setattr(pikepdf.Pdf, "copy_foreign", forbidden)
    monkeypatch.setattr(os, "link", forbidden)
    result = plan(parse(arguments(path)))
    assert len(result.pages) == 6
    assert sorted(tmp_path.iterdir()) == before


@pytest.mark.parametrize("phase", ["open", "hash", "traverse"])
def test_read_failures_are_source_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    import bookscan.prepare as preparation

    path = labels(tmp_path / "in.pdf")

    def fail(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("controlled read denial")

    if phase == "open":
        monkeypatch.setattr(Path, "open", fail)
    elif phase == "hash":
        monkeypatch.setattr(preparation, "hash_stream", fail)
    else:
        monkeypatch.setattr(preparation, "project_page", fail)
    with pytest.raises(PreparationError) as exc:
        plan(parse(arguments(path)))
    assert exc.value.code == "SOURCE_UNREADABLE"


class BrokenOutput(io.StringIO):
    def write(self, s: str) -> int:
        raise BrokenPipeError("controlled EPIPE")


@pytest.mark.parametrize("error", [False, True])
def test_result_delivery_preserves_error_exit(tmp_path: Path, error: bool) -> None:
    path = tmp_path / "missing" if error else labels(tmp_path / "in.pdf")
    stderr = io.StringIO()
    exit_code = run([*arguments(path), "--json"], BrokenOutput(), stderr)
    assert exit_code == (3 if error else 5)
    assert "RESULT_DELIVERY_FAILED" in stderr.getvalue()
    assert not (tmp_path / "out.pdf").exists()


def test_help_delivery_failure_is_structured() -> None:
    stderr = io.StringIO()
    assert run(["--help"], BrokenOutput(), stderr) == 5
    assert "RESULT_DELIVERY_FAILED" in stderr.getvalue()


def test_lazy_warning_observed_then_rejected(tmp_path: Path) -> None:
    from test_preview import check_gate

    path = raw_pdf(tmp_path / "lazy.pdf", stream=b"abc")
    # Same-size mutation preserves xref offsets and gives an intentionally wrong Length.
    path.write_bytes(path.read_bytes().replace(b"/Length 3", b"/Length 9"))
    with pikepdf.Pdf.open(path, attempt_recovery=False, suppress_warnings=True) as pdf:
        assert not pdf.get_warnings()  # pyright: ignore[reportUnknownMemberType]
        stream = pdf.pages[0].obj.get("/Contents")
        if isinstance(stream, pikepdf.Stream):
            stream.read_raw_bytes()
        assert pdf.get_warnings(), "specimen must warn during raw traversal, not opening"  # pyright: ignore[reportUnknownMemberType]
    check_gate(path)


def test_recovery_specimen(tmp_path: Path) -> None:
    from test_preview import check_gate

    path = raw_pdf(tmp_path / "recovery.pdf")
    contents = path.read_bytes()
    start = contents.index(b"startxref\n") + len(b"startxref\n")
    path.write_bytes(contents[:start] + b"0\n%%EOF\n")
    with pytest.raises(pikepdf.PdfError):
        pikepdf.Pdf.open(path, attempt_recovery=False)
    check_gate(path)


@pytest.mark.parametrize("signum", [2, 15])
def test_actual_prepublication_signals(tmp_path: Path, signum: int) -> None:
    import json
    import subprocess
    import sys

    path = labels(tmp_path / "in.pdf")
    host = """
import sys
import bookscan.preview as preview
from bookscan.prepare import plan

def ready():
    print('READY', file=sys.stderr, flush=True)
    sys.stdin.readline()

preview.plan = lambda request: plan(request, before_recheck=ready)
sys.exit(preview.main())
"""
    process = subprocess.Popen(
        [sys.executable, "-c", host, *arguments(path), "--json"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stderr is not None
    try:
        assert process.stderr.readline() == "READY\n"
        os.kill(process.pid, signum)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 128 + signum, stderr
        assert json.loads(stdout)["code"] == "INTERRUPTED"
        assert not (tmp_path / "out.pdf").exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)


def test_no_write_streams_or_output_reopen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins
    import tempfile

    path = labels(tmp_path / "in.pdf")
    original_open = cast(Callable[..., object], io.open)
    original_pdf_open = pikepdf.Pdf.open
    opened: list[object] = []

    def only_read(file: object, mode: str = "r", *args: object, **kwargs: object) -> object:
        assert not any(flag in mode for flag in ("w", "a", "x", "+"))
        # Delegate unchanged through a typed wrapper owned by pathlib/io.
        return original_open(file, mode, *args, **kwargs)

    def source_only(*args: object, **kwargs: object) -> pikepdf.Pdf:
        opened.append(args[0])
        assert len(opened) == 1, "Preview reopened output or copied a PDF"
        return original_pdf_open(*args, **kwargs)  # pyright: ignore[reportArgumentType]

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Preview attempted temporary-file creation")

    monkeypatch.setattr(io, "open", only_read)
    monkeypatch.setattr(builtins, "open", only_read)
    monkeypatch.setattr(tempfile, "TemporaryFile", forbidden)
    monkeypatch.setattr(tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(pikepdf.Pdf, "open", source_only)
    result = plan(parse(arguments(path)))
    assert len(result.pages) == 6


def test_repeated_source_symlink_annotated(tmp_path: Path) -> None:
    import json

    from test_preview import invoke

    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page()
        page.obj["/Annots"] = pikepdf.Array(
            [
                pdf.make_indirect(
                    pikepdf.Dictionary(Subtype=pikepdf.Name.Link, Border=pikepdf.Array([0, 0, 0]))
                )
            ]
        )
        pdf.save(path)
    alias = tmp_path / "alias.pdf"
    alias.symlink_to(path)
    result = invoke(
        "--front",
        str(path),
        "--content",
        str(alias),
        "--output",
        str(tmp_path / "out.pdf"),
        "--dry-run",
        "--json",
    )
    assert result.returncode == 3
    assert json.loads(result.stdout)["feature"] == "repeated annotated source page"


def test_direct_annotation_projection_omits_owner(tmp_path: Path) -> None:
    path = tmp_path / "direct.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page()
        normal = pdf.make_stream(b"")  # pyright: ignore[reportUnknownMemberType]
        normal["/Subtype"] = pikepdf.Name.Form
        normal["/Resources"] = pikepdf.Dictionary()
        normal["/BBox"] = pikepdf.Array([0, 0, 10, 10])
        page.obj["/Annots"] = pikepdf.Array(
            [
                pikepdf.Dictionary(
                    Subtype=pikepdf.Name.Stamp, P=page.obj, AP=pikepdf.Dictionary(N=normal)
                )
            ]
        )
        pdf.save(path)
    with pikepdf.Pdf.open(path) as observed:
        assert not observed.pages[0].obj["/Annots"][0].is_indirect
    result = plan(parse(arguments(path)))
    assert all(key != "/P" for node in result.projections[0].nodes for key, _ in node.entries)
