"""Cache construction may mutate only a new owned root before immutable binding."""

import json
import subprocess
from contextlib import AbstractContextManager
from pathlib import Path
from typing import cast

import pytest

from bookscan import fontconfig
from bookscan.skew import NativeError


@pytest.fixture
def configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    library = tmp_path / "libfontconfig.1.dylib"
    library.write_bytes(b"native test boundary")
    config = tmp_path / "config/fonts.conf"
    config.parent.mkdir()
    config.write_bytes(b"configuration")
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    (fonts / "face").write_bytes(b"font")
    cache = tmp_path / "cache"
    scope: dict[str, object] = {
        "schema": "BookScanBuilderFontconfigScope",
        "version": 3,
        "fontconfig_version": 21803,
        "config_files": [str(config)],
        "config_dirs": [str(config.parent)],
        "font_dirs": [str(fonts)],
        "effective_font_dirs": [str(fonts)],
        "cache_dirs": [str(cache)],
        "effective_cache_dirs": [str(cache)],
        "template_dirs": [str(tmp_path / "templates")],
        "parsed_files": [str(config)],
    }

    def linked(*args: object, **kwargs: object) -> dict[str, object]:
        return {"files": {str(library): {}}, "system_references": []}

    def execute(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "--build-cache" in argv:
            (cache / "constructed").write_bytes(b"cache")
        return subprocess.CompletedProcess(argv, 0, json.dumps(scope), "")

    monkeypatch.setattr(fontconfig, "linked_identity", linked)
    monkeypatch.setattr(fontconfig, "execute", execute)
    return scope


def prepared(tmp_path: Path) -> AbstractContextManager[fontconfig.FontconfigDiscovery]:
    return fontconfig.prepared_fontconfig_cache(
        tmp_path / "renderer", tmp_path / "cache", environment={}
    )


def test_build_precedes_binding_and_context_removes_owned_cache(
    configured: dict[str, object], tmp_path: Path
) -> None:
    with prepared(tmp_path) as found:
        assert (tmp_path / "cache/constructed").read_bytes() == b"cache"
        found.binding.verify()
    assert not (tmp_path / "cache").exists()
    assert (tmp_path / "fonts/face").read_bytes() == b"font"


@pytest.mark.parametrize("kind", ["directory", "file", "dangling", "alias"])
def test_occupied_cache_never_reused_or_removed(
    configured: dict[str, object], tmp_path: Path, kind: str
) -> None:
    cache = tmp_path / "cache"
    if kind == "directory":
        cache.mkdir()
        (cache / "prior").write_bytes(b"prior")
    elif kind == "file":
        cache.write_bytes(b"prior")
    else:
        cache.symlink_to(tmp_path / ("missing" if kind == "dangling" else "fonts"))
    before = cache.lstat()
    with pytest.raises(NativeError):
        with prepared(tmp_path):
            pytest.fail("occupied reservation was reused")
    assert cache.lstat().st_ino == before.st_ino
    assert (tmp_path / "fonts/face").read_bytes() == b"font"


@pytest.mark.parametrize("field", ["cache_dirs", "effective_cache_dirs"])
def test_effective_cache_scope_cannot_include_an_unowned_root(
    configured: dict[str, object], tmp_path: Path, field: str
) -> None:
    # Logical paths alone are not filesystem roots (sysroot changes them).
    if field == "cache_dirs":
        configured[field] = ["/logical/cache"]
        with prepared(tmp_path) as found:
            found.binding.verify()
    else:
        cast(list[str], configured[field]).append(str(tmp_path / "foreign"))
        with pytest.raises(NativeError):
            with prepared(tmp_path):
                pytest.fail("foreign cache root reached the consumer")
        assert not (tmp_path / "foreign").exists()
    assert not (tmp_path / "cache").exists()


def test_font_input_cannot_be_the_mutable_cache(
    configured: dict[str, object], tmp_path: Path
) -> None:
    configured["effective_font_dirs"] = [str(tmp_path / "cache")]
    with pytest.raises(NativeError):
        with prepared(tmp_path):
            pytest.fail("font input was exempted from immutability")
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("kind", ["font-change", "native-error", "diagnostic", "cancel"])
def test_failed_construction_cannot_return_binding_or_leave_cache(
    configured: dict[str, object], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    ordinary = fontconfig.execute

    def execute(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        result = ordinary(argv)
        if "--build-cache" in argv:
            if kind == "font-change":
                (tmp_path / "fonts/face").write_bytes(b"changed")
            elif kind == "cancel":
                raise InterruptedError("owner cancellation")
            else:
                return subprocess.CompletedProcess(
                    argv, 5 if kind == "native-error" else 0, result.stdout, "native diagnostic"
                )
        return result

    monkeypatch.setattr(fontconfig, "execute", execute)
    with pytest.raises(InterruptedError if kind == "cancel" else NativeError):
        with prepared(tmp_path):
            pytest.fail("failed constructor returned a usable binding")
    assert not (tmp_path / "cache").exists()


def test_post_construction_cache_mutation_is_rejected(
    configured: dict[str, object], tmp_path: Path
) -> None:
    with pytest.raises(NativeError):
        with prepared(tmp_path) as found:
            (tmp_path / "cache/constructed").write_bytes(b"changed after binding")
            found.binding.verify()
    # A changed owned entry is never adopted or deleted; its root is retained.
    assert (tmp_path / "cache/constructed").read_bytes() == b"changed after binding"


def test_replaced_root_is_never_cleaned(configured: dict[str, object], tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    with pytest.raises(NativeError):
        with prepared(tmp_path):
            cache.rename(tmp_path / "displaced-cache")
            cache.mkdir()
            (cache / "foreign").write_bytes(b"foreign")
    assert (cache / "foreign").read_bytes() == b"foreign"
    assert (tmp_path / "displaced-cache/constructed").read_bytes() == b"cache"


def test_consumer_cancellation_keeps_selected_error_and_cleans(
    configured: dict[str, object], tmp_path: Path
) -> None:
    with pytest.raises(InterruptedError, match="consumer cancellation"):
        with prepared(tmp_path):
            raise InterruptedError("consumer cancellation")
    assert not (tmp_path / "cache").exists()


def test_symlinked_parent_reaches_the_same_reservation(
    configured: dict[str, object], tmp_path: Path
) -> None:
    alias = tmp_path / "parent-alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    with prepared(alias) as found:
        found.binding.verify()
        assert (tmp_path / "cache/constructed").read_bytes() == b"cache"
    assert not (tmp_path / "cache").exists()
