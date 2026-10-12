"""Cancellation crosses the preflight boundary and reaps its actual native child."""

import hashlib
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from PIL import Image

from bookscan import native_setup


class Cancelled(RuntimeError):
    """Stand-in for the operation owner's already-selected signal outcome."""


def stopped() -> None:
    raise Cancelled("selected signal outcome")


def parked_tool(directory: Path, phase: str) -> tuple[Path, Path]:
    """A real private executable parks only at the declared native invocation."""
    marker = directory / "child-pid"
    binary = directory / "dependency"
    binary.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys, time\n"
        "from pathlib import Path\n"
        f"phase = {phase!r}\n"
        "if phase in sys.argv[1:]:\n"
        f"    marker = Path({str(marker)!r})\n"
        "    pending = marker.with_suffix('.pending')\n"
        "    pending.write_text(str(os.getpid()))\n"
        "    pending.replace(marker)\n"
        "    time.sleep(60)\n"
        "if '--modversion' in sys.argv:\n"
        "    print('1.87.0')\n"
        "elif '-v' in sys.argv:\n"
        "    print('pdftoppm version 26.10.0', file=sys.stderr)\n"
        "elif '-print-prog-name=clang' in sys.argv:\n"
        "    print(sys.argv[0])\n"
        "elif '--variable=includedir' in sys.argv or '--variable=libdir' in sys.argv:\n"
        f"    print({str(directory)!r})\n"
        "elif '--identity' in sys.argv:\n"
        "    print(json.dumps({'schema': 'BookScanBuilderSkewIdentity', 'version': 1, "
        "'leptonica': 'leptonica-1.87.0', 'headers': '1.87.0'}))\n"
        "else:\n"
        "    print('private tool identity')\n"
    )
    binary.chmod(0o700)
    return binary, marker


def cancelling_at(marker: Path) -> Callable[[], None]:
    def check() -> None:
        if marker.exists():
            stopped()

    return check


def assert_reaped(marker: Path) -> None:
    assert marker.is_file(), "the actual child must reach the selected phase"
    with pytest.raises(ProcessLookupError):
        os.kill(int(marker.read_text()), 0)


def test_cancelled_preflight_cannot_read_missing_cache(tmp_path: Path) -> None:
    with pytest.raises(Cancelled, match="selected signal"):
        native_setup.preflight(tmp_path / "absent", check_cancel=stopped)
    assert list(tmp_path.iterdir()) == []


def test_checked_cancels_running_native_child(tmp_path: Path) -> None:
    binary, marker = parked_tool(tmp_path, "--version")
    with pytest.raises(Cancelled):
        native_setup.checked([str(binary), "--version"], check_cancel=cancelling_at(marker))
    assert_reaped(marker)


@pytest.mark.parametrize("phase", ["--modversion", "-v", "-print-prog-name=clang", "--version"])
def test_dependency_identity_cancellation_reaps_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    binary, marker = parked_tool(tmp_path, phase)
    (tmp_path / "libleptonica.dylib").write_bytes(b"private identity subject")
    (tmp_path / "allheaders.h").write_bytes(b"private header subject")

    def tool_path(_name: str) -> Path:
        return binary

    monkeypatch.setattr(native_setup, "tool", tool_path)
    with pytest.raises(Cancelled):
        native_setup.inputs(check_cancel=cancelling_at(marker))
    assert_reaped(marker)


@pytest.mark.parametrize("phase", ["--identity", "analyze"])
def test_self_test_cancellation_reaps_helper(tmp_path: Path, phase: str) -> None:
    binary, marker = parked_tool(tmp_path, phase)
    with pytest.raises(Cancelled):
        native_setup.self_test(binary, check_cancel=cancelling_at(marker))
    assert_reaped(marker)


def test_analysis_cancellation_reaps_child_before_exact_cleanup(tmp_path: Path) -> None:
    binary, marker = parked_tool(tmp_path, "analyze")
    with Image.new("RGB", (24, 16), "white") as baseline:
        with pytest.raises(Cancelled):
            native_setup.assess(binary, baseline, tmp_path, check_cancel=cancelling_at(marker))
        assert baseline.tobytes() == b"\xff" * (24 * 16 * 3)
    assert_reaped(marker)
    assert not list(tmp_path.glob(".analysis-*"))


def test_hashing_checks_cancellation_between_chunks(tmp_path: Path) -> None:
    path = tmp_path / "large-subject"
    data = b"x" * (3 * 1024 * 1024)
    path.write_bytes(data)
    checks = 0

    def cancel_during_hash() -> None:
        nonlocal checks
        checks += 1
        if checks == 2:
            stopped()

    with pytest.raises(Cancelled):
        native_setup.digest(path, check_cancel=cancel_during_hash)
    assert path.read_bytes() == data
    assert native_setup.digest(path) == hashlib.sha256(data).hexdigest()


def test_preflight_cancellation_reaches_cached_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary, marker = parked_tool(tmp_path, "analyze")
    subjects: dict[str, object] = {"private": "identity fixture"}
    identity = hashlib.sha256(json.dumps(subjects, sort_keys=True).encode()).hexdigest()
    entry = tmp_path / f"native-{identity}-{'c' * 32}"
    entry.mkdir()
    binary.rename(entry / "skew")
    manifest = {
        "schema": "BookScanBuilderNativeBuild",
        "version": 1,
        "build_identity": identity,
        "inputs": subjects,
        "binary_sha256": native_setup.digest(entry / "skew"),
    }
    (entry / "build.json").write_text(json.dumps(manifest))
    (tmp_path / "current.json").write_text(json.dumps({"entry": entry.name}))
    original = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def identity_inputs(*, check_cancel: Callable[[], None]) -> dict[str, object]:
        check_cancel()
        return subjects

    monkeypatch.setattr(native_setup, "inputs", identity_inputs)
    with pytest.raises(Cancelled):
        native_setup.preflight(tmp_path, check_cancel=cancelling_at(marker))
    assert_reaped(marker)
    assert {p: p.read_bytes() for p in original} == original
