"""Cancellation must reap the real helper/compiler process, not leave it running."""

import os
import sys
from pathlib import Path

import pytest

from bookscan.native_setup import execute
from bookscan.skew import NativeError


def test_cancellation_reaps_child(tmp_path: Path) -> None:
    pid_file = tmp_path / "child-pid"

    def cancelled() -> None:
        if pid_file.exists():
            raise KeyboardInterrupt

    script = (
        "import os, time; from pathlib import Path; "
        f"Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(60)"
    )
    with pytest.raises(KeyboardInterrupt):
        execute([sys.executable, "-c", script], check_cancel=cancelled)
    pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_timeout_reaps_child(tmp_path: Path) -> None:
    pid_file = tmp_path / "child-pid"
    script = (
        "import os, time; from pathlib import Path; "
        f"Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(60)"
    )
    with pytest.raises(NativeError, match="timed out"):
        execute([sys.executable, "-c", script], timeout=0.2)
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text()), 0)


def test_both_pipes_are_drained() -> None:
    result = execute(
        [
            sys.executable,
            "-c",
            "import sys; print('x' * 100000); print('y' * 100000, file=sys.stderr)",
        ]
    )
    assert (result.returncode, len(result.stdout), len(result.stderr)) == (0, 100001, 100001)
