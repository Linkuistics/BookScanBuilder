"""Renderer cleanup must preserve changed/unknown entries and the chosen failure."""

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from test_render import source, write_png

from bookscan import native_setup, project_reservation, render, render_workspace


class Selected(RuntimeError):
    pass


CHANGES = [
    "extra-file",
    "extra-directory",
    "file-mode",
    "file-link",
    "file-replace",
    "root-replace",
    "root-mode",
]


def change_output(target: Path, outside: Path, change: str) -> dict[Path, bytes]:
    root = target.parent
    if change == "extra-file":
        (root / "foreign").write_bytes(b"unknown input")
    elif change == "extra-directory":
        (root / "foreign").mkdir()
        (root / "foreign/child").write_bytes(b"unknown child")
    elif change == "file-mode":
        target.chmod(0o400)
    elif change == "file-link":
        os.link(target, outside / "external-link")
    elif change == "file-replace":
        data = target.read_bytes()
        target.rename(outside / "old-output")
        target.write_bytes(data)
    elif change == "root-replace":
        root.rename(outside / "old-root")
        root.mkdir()
        target.write_bytes(b"replacement output")
    elif change == "root-mode":
        root.chmod(0o755)
    else:
        assert change == "file-bytes"
        target.write_bytes(b"changed after native writer completed")
    return {
        p: p.read_bytes() for folder in (root, outside) for p in folder.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize("selected", [False, True])
@pytest.mark.parametrize("change", CHANGES)
def test_native_boundary_preserves_changed_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str, selected: bool
) -> None:
    # Recursive cleanup or adopting the name's current identity erases these
    # actual changed files, including same-byte replacement of the output.
    saved = source(tmp_path)
    captured: dict[Path, bytes] = {}
    chosen = Selected("selected native error")

    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        target = Path(argv[-1] + ".png")
        write_png(target, (10, 5), (97, 98, 99))
        captured.update(change_output(target, tmp_path, change))
        if selected:
            raise chosen
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(render, "execute", execute)
    with pytest.raises((Selected, render.RenderFailed)) as caught:
        render.render_page(saved, saved.pages[0], Path("unused-renderer"))
    if selected:
        assert caught.value is chosen
    assert captured and {p: p.read_bytes() for p in captured} == captured
    saved.verify()


@pytest.mark.parametrize("selected", [False, True])
@pytest.mark.parametrize("change", CHANGES + ["file-bytes"])
def test_decode_boundary_preserves_changed_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str, selected: bool
) -> None:
    # Dropping the post-native stamp check accepts or removes data changed
    # after the native writer's authorized write boundary.
    saved = source(tmp_path)
    captured: dict[Path, bytes] = {}
    chosen = Selected("selected decoder error")
    original = render._decode  # pyright: ignore[reportPrivateUsage]

    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        write_png(Path(argv[-1] + ".png"), (10, 5), (97, 98, 99))
        return subprocess.CompletedProcess(argv, 0, "", "")

    def decode(target: Path, size: tuple[int, int]) -> bytes:
        data = original(target, size)
        captured.update(change_output(target, tmp_path, change))
        if selected:
            raise chosen
        return data

    monkeypatch.setattr(render, "execute", execute)
    monkeypatch.setattr(render, "_decode", decode)
    with pytest.raises((Selected, render.RenderFailed)) as caught:
        render.render_page(saved, saved.pages[0], Path("unused-renderer"))
    if selected:
        assert caught.value is chosen
    assert captured and {p: p.read_bytes() for p in captured} == captured
    saved.verify()


@pytest.mark.parametrize("outcome", ["success", "failure", "cancelled", "empty-cancelled"])
def test_unchanged_output_cleanup_keeps_native_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    saved = source(tmp_path)
    targets: list[Path] = []
    chosen = Selected("selected cancellation")

    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        target = Path(argv[-1] + ".png")
        targets.append(target)
        if outcome != "empty-cancelled":
            write_png(target, (10, 5), (97, 98, 99))
        if outcome in {"cancelled", "empty-cancelled"}:
            raise chosen
        return subprocess.CompletedProcess(argv, 17 if outcome == "failure" else 0, "", "")

    monkeypatch.setattr(render, "execute", execute)
    if outcome == "success":
        assert render.render_page(saved, saved.pages[0], Path("unused-renderer")).rgb == b"abc" * 50
    else:
        with pytest.raises((Selected, render.RenderFailed)) as caught:
            render.render_page(saved, saved.pages[0], Path("unused-renderer"))
        if outcome != "failure":
            assert caught.value is chosen
    assert len(targets) == 1 and not targets[0].parent.exists()
    saved.verify()


def test_selected_oserror_is_not_reclassified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = source(tmp_path)
    chosen = OSError("already selected by owner")

    def execute(_argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise chosen

    monkeypatch.setattr(render, "execute", execute)
    with pytest.raises(OSError) as caught:
        render.render_page(saved, saved.pages[0], Path("unused-renderer"))
    assert caught.value is chosen


def test_returned_native_error_precedes_refused_ownership_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = source(tmp_path)
    targets: list[Path] = []

    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        target = Path(argv[-1] + ".png")
        targets.append(target)
        target.write_bytes(b"own partial native output")
        target.parent.chmod(0o755)
        return subprocess.CompletedProcess(argv, 17, "", "native selected diagnostic")

    monkeypatch.setattr(render, "execute", execute)
    with pytest.raises(render.RenderFailed, match="Poppler exited 17: native selected diagnostic"):
        render.render_page(saved, saved.pages[0], Path("unused-renderer"))
    assert targets[0].read_bytes() == b"own partial native output"


@pytest.mark.parametrize("selected", [False, True])
@pytest.mark.parametrize("fault", ["refused-unlink", "changed-empty-root"])
def test_cleanup_preserves_selected_error_and_remaining_owned_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected: bool, fault: str
) -> None:
    saved = source(tmp_path)
    original = os.unlink
    targets: list[Path] = []
    chosen = Selected("selected native failure")

    def unlink(path: str | Path, *, dir_fd: int | None = None) -> None:
        if str(path) == "page.png":
            if fault == "refused-unlink":
                raise PermissionError("output removal refused")
            original(path, dir_fd=dir_fd)
            targets[0].parent.chmod(0o755)
            return
        original(path, dir_fd=dir_fd)

    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        target = Path(argv[-1] + ".png")
        targets.append(target)
        write_png(target, (10, 5), (97, 98, 99))
        if selected:
            raise chosen
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(project_reservation.os, "unlink", unlink)
    monkeypatch.setattr(render, "execute", execute)
    with pytest.raises((Selected, render.RenderFailed)) as caught:
        render.render_page(saved, saved.pages[0], Path("unused-renderer"))
    if selected:
        assert caught.value is chosen
    assert len(targets) == 1 and targets[0].parent.is_dir()
    if fault == "refused-unlink":
        assert targets[0].is_file()
    else:
        assert list(targets[0].parent.iterdir()) == []
        assert targets[0].parent.stat().st_mode & 0o777 == 0o755


@pytest.mark.parametrize("created", [False, True])
def test_open_without_returned_descriptor_grants_no_file_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, created: bool
) -> None:
    saved = source(tmp_path)
    original_open, original_close = os.open, os.close
    targets: list[Path] = []

    def opened(
        path: str | Path, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        if Path(path).name == "page.png":
            targets.append(Path(path))
            if created:
                descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
                os.write(descriptor, b"uncaptured file")
                original_close(descriptor)
            raise PermissionError("open returned no descriptor")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    def execute(_argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("native launch after failed creation")

    monkeypatch.setattr(render_workspace.os, "open", opened)
    monkeypatch.setattr(render, "execute", execute)
    with pytest.raises(render.RenderFailed):
        render.render_page(saved, saved.pages[0], Path("must-not-launch"))
    assert len(targets) == 1
    if created:
        assert targets[0].read_bytes() == b"uncaptured file"
    else:
        assert not targets[0].parent.exists()


@pytest.mark.parametrize("selected", [False, True])
def test_output_descriptor_close_is_attempted_once_after_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected: bool
) -> None:
    saved = source(tmp_path)
    original_open, original_close = os.open, os.close
    descriptor = replacement = -1
    targets: list[Path] = []
    chosen = Selected("selected native failure")

    def opened(
        path: str | Path, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        nonlocal descriptor
        result = original_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path).name == "page.png":
            descriptor = result
        return result

    def closed(fd: int) -> None:
        nonlocal descriptor, replacement
        if fd == descriptor:
            descriptor = -1
            original_close(fd)
            replacement = original_open(
                tmp_path / "reused-descriptor", os.O_CREAT | os.O_RDWR, 0o600
            )
            assert replacement == fd
            raise OSError("reported after release")
        original_close(fd)

    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert descriptor >= 0 and not os.get_inheritable(descriptor)
        target = Path(argv[-1] + ".png")
        targets.append(target)
        write_png(target, (10, 5), (97, 98, 99))
        if selected:
            raise chosen
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(render_workspace.os, "open", opened)
    monkeypatch.setattr(render_workspace.os, "close", closed)
    monkeypatch.setattr(render, "execute", execute)
    try:
        with pytest.raises((Selected, render.RenderFailed)) as caught:
            render.render_page(saved, saved.pages[0], Path("unused-renderer"))
        if selected:
            assert caught.value is chosen
        assert len(targets) == 1 and not targets[0].parent.exists()
        os.write(replacement, b"still held")
        assert (tmp_path / "reused-descriptor").read_bytes() == b"still held"
    finally:
        if replacement >= 0:
            original_close(replacement)


@pytest.mark.parametrize("selected", [False, True])
def test_reservation_close_failure_has_processing_class_without_replacing_selected_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected: bool
) -> None:
    saved = source(tmp_path)
    original = project_reservation.Reservation.close
    chosen = Selected("selected native error")

    def close(reservation: project_reservation.Reservation) -> None:
        original(reservation)
        raise project_reservation.ReservationError("WRITE_FAILED", "close reported failure", 5)

    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        write_png(Path(argv[-1] + ".png"), (10, 5), (97, 98, 99))
        if selected:
            raise chosen
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(project_reservation.Reservation, "close", close)
    monkeypatch.setattr(render, "execute", execute)
    with pytest.raises((Selected, render.RenderFailed)) as caught:
        render.render_page(saved, saved.pages[0], Path("unused-renderer"))
    if selected:
        assert caught.value is chosen
    else:
        assert isinstance(caught.value, render.RenderFailed) and caught.value.exit_code == 5


def test_actual_cancelled_child_is_reaped_before_exact_output_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = source(tmp_path)
    barrier = tmp_path / "native-ready"
    child_script = tmp_path / "child.py"
    child_script.write_text(
        "import os,sys,signal\n"
        "from pathlib import Path\n"
        "output,barrier=map(Path,sys.argv[1:3])\n"
        "held=int(sys.argv[3])\n"
        "try:\n"
        " info=os.fstat(held)\n"
        " leaked=(info.st_dev,info.st_ino)==(output.stat().st_dev,output.stat().st_ino)\n"
        "except OSError:\n"
        " leaked=False\n"
        "with output.open('ab') as stream:\n"
        " stream.write(b'own partial native output');stream.flush();os.fsync(stream.fileno())\n"
        "barrier.write_text(str(os.getpid())+' '+str(leaked))\n"
        "signal.pause()\n"
    )
    chosen = Selected("cancel actual parked renderer")
    original = os.open
    descriptor = -1
    targets: list[Path] = []

    def opened(
        path: str | Path, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        nonlocal descriptor
        result = original(path, flags, mode, dir_fd=dir_fd)
        if Path(path).name == "page.png":
            descriptor = result
        return result

    def cancel() -> None:
        if barrier.exists():
            raise chosen

    def execute(
        argv: list[str], *, check_cancel: Callable[[], None]
    ) -> subprocess.CompletedProcess[str]:
        target = Path(argv[-1] + ".png")
        targets.append(target)
        return native_setup.execute(
            [str(sys.executable), str(child_script), str(target), str(barrier), str(descriptor)],
            check_cancel=check_cancel,
            timeout=5,
        )

    monkeypatch.setattr(render_workspace.os, "open", opened)
    monkeypatch.setattr(render, "execute", execute)
    with pytest.raises(Selected) as caught:
        render.render_page(saved, saved.pages[0], Path("private-child"), check_cancel=cancel)
    assert caught.value is chosen
    pid, leaked = barrier.read_text().split()
    assert leaked == "False"
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid), 0)
    assert len(targets) == 1 and not targets[0].parent.exists()
    saved.verify()
