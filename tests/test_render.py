"""Private renderer faults; actual Poppler constructions have a separate runner."""

import subprocess
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import NoReturn

import pikepdf
import pytest
from PIL import Image

from bookscan import intake


def write_png(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    with Image.new("RGB", size, color) as image:
        image.save(path, format="PNG")


def unexpected(argv: list[str], *, check_cancel: Callable[[], None]) -> NoReturn:
    pytest.fail("launched")


def source(tmp_path: Path, unit: float = 1) -> intake.Snapshot:
    original = tmp_path / "input.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        page.obj.MediaBox = pikepdf.Array([0, 0, 2.4, 1.2])
        page.obj.UserUnit = unit
        pdf.save(original, min_version="1.7")
    return intake.snapshot(original, tmp_path / "snapshot.pdf")


def test_complete_rgb_and_user_unit_compensation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from bookscan import render

    saved = source(tmp_path, unit=2)
    seen: list[list[str]] = []

    def execute(
        argv: list[str], *, check_cancel: Callable[[], None]
    ) -> subprocess.CompletedProcess[str]:
        check_cancel()
        seen.append(argv)
        write_png(Path(argv[-1] + ".png"), (20, 10), (17, 34, 51))
        return subprocess.CompletedProcess(argv, 0, "", "decoder advisory")

    monkeypatch.setattr(render, "execute", execute)
    result = render.render_page(saved, saved.pages[0], Path("/verified/pdftocairo"))
    assert result.size == (20, 10)
    assert result.rgb == b"\x11\x22\x33" * 200
    assert result.diagnostics == "decoder advisory"
    command = seen[0]
    assert command[command.index("-r") + 1] == "600"
    assert command[command.index("-W") + 1] == "20"
    assert command[command.index("-H") + 1] == "10"
    assert "-cropbox" not in command and "-hide-annotations" not in command
    assert command[-2] == str(saved.path)
    assert not Path(command[-1]).parent.exists()


@pytest.mark.parametrize("fault", ["exit", "missing", "malformed", "wrong-size", "gray"])
def test_renderer_failure_never_returns_partial_rgb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
):
    from bookscan import render

    saved = source(tmp_path)

    def execute(
        argv: list[str], *, check_cancel: Callable[[], None]
    ) -> subprocess.CompletedProcess[str]:
        check_cancel()
        target = Path(argv[-1] + ".png")
        if fault == "malformed":
            target.write_bytes(b"bad")
        elif fault == "wrong-size":
            write_png(target, (1, 1), (97, 98, 99))
        elif fault == "gray":
            with Image.new("L", (10, 5), 77) as gray:
                gray.save(target, format="PNG")
        return subprocess.CompletedProcess(
            argv, 1 if fault == "exit" else 0, "", "native diagnostic"
        )

    monkeypatch.setattr(render, "execute", execute)
    with pytest.raises(render.RenderFailed) as caught:
        render.render_page(saved, saved.pages[0], Path("/verified/pdftocairo"))
    assert caught.value.code == "RENDER_FAILED" and caught.value.exit_code == 5
    assert saved.path.exists()


def test_corrupt_snapshot_precedes_native_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from bookscan import render

    saved = source(tmp_path)
    saved.path.write_bytes(b"replaced")
    monkeypatch.setattr(render, "execute", unexpected)
    with pytest.raises(intake.ImportFailure, match="INVALID_PROJECT"):
        render.render_page(saved, saved.pages[0], Path("/verified/pdftocairo"))


def test_foreign_page_geometry_is_rejected_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from bookscan import render

    saved = source(tmp_path)
    monkeypatch.setattr(render, "execute", unexpected)
    with pytest.raises(intake.ImportFailure, match="INVALID_PROJECT"):
        render.render_page(
            saved, replace(saved.pages[0], source_page=2), Path("/verified/pdftocairo")
        )


def test_owner_cancellation_propagates_and_private_directory_is_cleaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from bookscan import render

    saved = source(tmp_path)
    selected = RuntimeError("selected cancellation")
    directories: list[Path] = []

    def execute(
        argv: list[str], *, check_cancel: Callable[[], None]
    ) -> subprocess.CompletedProcess[str]:
        directories.append(Path(argv[-1]).parent)
        raise selected

    monkeypatch.setattr(render, "execute", execute)
    with pytest.raises(RuntimeError) as caught:
        render.render_page(saved, saved.pages[0], Path("/verified/pdftocairo"))
    assert caught.value is selected
    assert directories and not directories[0].exists()
    saved.verify()


def test_source_loss_does_not_prevent_rendering_saved_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from bookscan import render

    saved = source(tmp_path)
    saved.original_path.unlink()

    def execute(
        argv: list[str], *, check_cancel: Callable[[], None]
    ) -> subprocess.CompletedProcess[str]:
        write_png(Path(argv[-1] + ".png"), (10, 5), (97, 98, 99))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(render, "execute", execute)
    assert (
        render.render_page(saved, saved.pages[0], Path("/verified/pdftocairo")).rgb == b"abc" * 50
    )


@pytest.mark.parametrize("version", ["", "pdftocairo version 26.9.0", "not a version"])
def test_renderer_preflight_rejects_unverified_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    from bookscan import render

    def tool(name: str) -> Path:
        return tmp_path / name

    monkeypatch.setattr(render, "tool", tool)

    def execute(
        argv: list[str], *, check_cancel: Callable[[], None]
    ) -> subprocess.CompletedProcess[str]:
        check_cancel()
        return subprocess.CompletedProcess(argv, 0, "", version)

    monkeypatch.setattr(render, "execute", execute)
    with pytest.raises(render.NativeError, match="Poppler"):
        render.renderer_path()


def test_renderer_preflight_forwards_owner_cancellation(monkeypatch: pytest.MonkeyPatch) -> None:
    from bookscan import render

    selected = RuntimeError("owner cancellation")

    def cancel() -> None:
        raise selected

    with pytest.raises(RuntimeError) as caught:
        render.renderer_path(check_cancel=cancel)
    assert caught.value is selected
