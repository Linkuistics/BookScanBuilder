"""An empty or incompatible version response must have a setup remedy, not crash."""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from bookscan import native_setup
from bookscan.skew import NativeError


@pytest.mark.parametrize("version", ["", "pdftoppm version 26.09.0\n", "other tool\n"])
def test_missing_renderer_version_is_dependency_error(
    monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    def native_result(
        argv: list[str], *, check_cancel: Callable[[], None]
    ) -> subprocess.CompletedProcess[str]:
        check_cancel()
        if "--modversion" in argv:
            return subprocess.CompletedProcess(argv, 0, "1.87.0", "")
        return subprocess.CompletedProcess(argv, 0, "", version)

    def tool_path(name: str) -> Path:
        return Path("/test-only") / name

    monkeypatch.setattr(native_setup, "tool", tool_path)
    monkeypatch.setattr(native_setup, "execute", native_result)
    with pytest.raises(NativeError, match="Poppler") as caught:
        native_setup.inputs()
    assert caught.value.exit_code == 5
    assert "process:setup" in caught.value.remediation
