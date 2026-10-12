"""Native analysis may clean only its captured unchanged input and empty root."""

import json
import os
import subprocess
from pathlib import Path
from typing import BinaryIO

import pytest
from PIL import Image

from bookscan import analysis_workspace, native_setup, project_reservation
from bookscan.skew import NativeError


class Selected(RuntimeError):
    pass


def answer(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        argv,
        0,
        json.dumps(
            {
                "schema": "BookScanBuilderSkew",
                "version": 1,
                "leptonica": "leptonica-1.87.0",
                "width": 24,
                "height": 16,
                "status": 0,
                "angle_degrees": 0,
                "score_ratio": 10,
            }
        ),
        "",
    )


@pytest.mark.parametrize("selected", [False, True])
@pytest.mark.parametrize(
    "change",
    [
        "extra-file",
        "extra-directory",
        "file-bytes",
        "file-mode",
        "file-link",
        "file-replace",
        "root-replace",
        "root-mode",
    ],
)
def test_changed_analysis_entries_are_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str, selected: bool
) -> None:
    # Recursive deletion, digest-only file ownership or root-only ownership
    # destroys these real changed entries, including same-byte replacements.
    captured: dict[Path, bytes] = {}
    chosen = Selected("native invocation selected this error")

    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        image = Path(argv[-1])
        root = image.parent
        if change == "extra-file":
            (root / "foreign").write_bytes(b"unknown input")
        elif change == "extra-directory":
            (root / "foreign").mkdir()
            (root / "foreign/child").write_bytes(b"unknown child")
        elif change == "file-bytes":
            image.write_bytes(b"changed input")
        elif change == "file-mode":
            image.chmod(0o400)
        elif change == "file-link":
            os.link(image, tmp_path / "external-link")
        elif change == "file-replace":
            data = image.read_bytes()
            image.rename(tmp_path / "old-input")
            image.write_bytes(data)
        elif change == "root-mode":
            root.chmod(0o755)
        else:
            root.rename(tmp_path / "old-root")
            root.mkdir()
            image.write_bytes(b"replacement root input")
        captured.update((p, p.read_bytes()) for p in tmp_path.rglob("*") if p.is_file())
        if selected:
            raise chosen
        return answer(argv)

    monkeypatch.setattr(native_setup, "execute", execute)
    with Image.new("RGB", (24, 16), "white") as baseline:
        with pytest.raises((Selected, NativeError)) as caught:
            native_setup.assess(Path("unused-helper"), baseline, tmp_path)
        assert baseline.tobytes() == b"\xff" * (24 * 16 * 3)
    if selected:
        assert caught.value is chosen
    assert captured
    assert {path: path.read_bytes() for path in captured} == captured


@pytest.mark.parametrize("outcome", ["success", "failure", "cancelled"])
def test_unchanged_analysis_cleans_exact_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        with Image.open(argv[-1]) as analysis:
            assert analysis.mode == "L" and analysis.size == (24, 16)
        if outcome == "cancelled":
            raise Selected("selected cancellation")
        result = answer(argv)
        if outcome == "failure":
            result.returncode = 17
        return result

    monkeypatch.setattr(native_setup, "execute", execute)
    with Image.new("RGB", (24, 16), "white") as baseline:
        if outcome == "success":
            estimate = native_setup.assess(Path("unused-helper"), baseline, tmp_path)
            assert estimate.available and estimate.angle_degrees == 0
        else:
            with pytest.raises((Selected, NativeError)):
                native_setup.assess(Path("unused-helper"), baseline, tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("selected", [False, True])
def test_unlink_refusal_keeps_input_and_selected_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected: bool
) -> None:
    original = project_reservation.os.unlink
    paths: list[Path] = []
    chosen = Selected("selected native failure")

    def refuse(path: str | Path, *, dir_fd: int | None = None) -> None:
        if str(path) == "whole.png":
            raise PermissionError("analysis removal refused")
        original(path, dir_fd=dir_fd)

    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        paths.append(Path(argv[-1]))
        if selected:
            raise chosen
        return answer(argv)

    monkeypatch.setattr(project_reservation.os, "unlink", refuse)
    monkeypatch.setattr(native_setup, "execute", execute)
    with Image.new("RGB", (24, 16), "white") as baseline:
        with pytest.raises((Selected, NativeError)) as caught:
            native_setup.assess(Path("unused-helper"), baseline, tmp_path)
    if selected:
        assert caught.value is chosen
    assert len(paths) == 1 and paths[0].is_file()


@pytest.mark.parametrize("changed", [False, True])
def test_partial_encoder_failure_cleans_only_captured_own_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: bool
) -> None:
    chosen = Selected("encoder stopped after partial write")
    paths: list[Path] = []

    def write(_baseline: Image.Image, stream: BinaryIO) -> None:
        stream.write(b"own incomplete image")
        root = next(tmp_path.glob(".analysis-*"))
        paths.append(root / "whole.png")
        if changed:
            (root / "foreign").write_bytes(b"not owned")
        raise chosen

    monkeypatch.setattr(analysis_workspace, "write_analysis_stream", write)
    with Image.new("RGB", (24, 16), "white") as baseline:
        with pytest.raises(Selected) as caught:
            native_setup.assess(Path("must-not-launch"), baseline, tmp_path)
    assert caught.value is chosen
    if changed:
        assert paths[0].read_bytes() == b"own incomplete image"
        assert (paths[0].parent / "foreign").read_bytes() == b"not owned"
    else:
        assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("selected", [False, True])
def test_creation_descriptor_close_is_not_retried_or_allowed_to_replace_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected: bool
) -> None:
    original_open, original_close = os.open, os.close
    descriptor = -1
    replacement = -1
    chosen = Selected("already selected native error")

    def opened(
        path: str | Path, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        nonlocal descriptor
        result = original_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path).name == "whole.png":
            descriptor = result
        return result

    def closed(fd: int) -> None:
        nonlocal descriptor, replacement
        if fd == descriptor:
            descriptor = -1
            original_close(fd)
            replacement = original_open(tmp_path / "replacement-fd", os.O_CREAT | os.O_RDWR, 0o600)
            assert replacement == fd
            raise OSError("reported after descriptor release")
        original_close(fd)

    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert descriptor >= 0 and not os.get_inheritable(descriptor)
        if selected:
            raise chosen
        return answer(argv)

    monkeypatch.setattr(analysis_workspace.os, "open", opened)
    monkeypatch.setattr(analysis_workspace.os, "close", closed)
    monkeypatch.setattr(native_setup, "execute", execute)
    try:
        with Image.new("RGB", (24, 16), "white") as baseline:
            with pytest.raises((Selected, NativeError)) as caught:
                native_setup.assess(Path("unused-helper"), baseline, tmp_path)
        if selected:
            assert caught.value is chosen
        assert replacement >= 0
        os.write(replacement, b"still held")
        assert (tmp_path / "replacement-fd").read_bytes() == b"still held"
        assert not list(tmp_path.glob(".analysis-*"))
    finally:
        if replacement >= 0:
            original_close(replacement)


def test_unknown_open_outcome_cannot_grant_file_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = os.open
    chosen = PermissionError("creation returned no descriptor")

    def opened(
        path: str | Path, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        descriptor = original(path, flags, mode, dir_fd=dir_fd)
        if Path(path).name == "whole.png":
            os.close(descriptor)
            raise chosen
        return descriptor

    monkeypatch.setattr(analysis_workspace.os, "open", opened)
    with Image.new("RGB", (24, 16), "white") as baseline:
        with pytest.raises(PermissionError) as caught:
            native_setup.assess(Path("must-not-launch"), baseline, tmp_path)
    assert caught.value is chosen
    inputs = list(tmp_path.glob(".analysis-*/whole.png"))
    assert len(inputs) == 1 and inputs[0].read_bytes() == b""


def test_missing_input_cannot_authorize_deleting_changed_empty_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    roots: list[Path] = []

    def execute(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        image = Path(argv[-1])
        roots.append(image.parent)
        image.unlink()
        image.parent.chmod(0o755)
        raise Selected("native removed input and changed root")

    monkeypatch.setattr(native_setup, "execute", execute)
    with Image.new("RGB", (24, 16), "white") as baseline:
        with pytest.raises(Selected):
            native_setup.assess(Path("unused-helper"), baseline, tmp_path)
    assert len(roots) == 1 and roots[0].is_dir()
    assert roots[0].stat().st_mode & 0o777 == 0o755
