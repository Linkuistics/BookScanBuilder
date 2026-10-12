"""A changed bound resource must never produce a usable uncommitted raster."""

import os
import sys
from pathlib import Path
from typing import cast

import pytest

from bookscan.native_setup import execute
from bookscan.skew import NativeError


def binding(path: Path):
    from bookscan.resources import ResourceBinding

    return ResourceBinding.capture([path], environment={"BOOKSCAN_RESOURCE_TEST": "captured"})


def test_child_uses_captured_environment_not_later_ambient(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BOOKSCAN_RESOURCE_TEST", "ambient")
    result = execute(
        [sys.executable, "-c", "import os; print(os.environ['BOOKSCAN_RESOURCE_TEST'])"],
        environment={"BOOKSCAN_RESOURCE_TEST": "captured"},
    )
    assert (result.returncode, result.stdout) == (0, "captured\n")


@pytest.mark.parametrize("fault", ["bytes", "inode", "deleted", "symlink"])
def test_changed_named_file_is_rejected(tmp_path: Path, fault: str):
    resource = tmp_path / "font"
    resource.write_bytes(b"original")
    guard = binding(resource)
    if fault == "bytes":
        resource.write_bytes(b"changed!")
    elif fault == "deleted":
        resource.unlink()
    elif fault == "inode":
        replacement = tmp_path / "replacement"
        replacement.write_bytes(b"original")
        replacement.replace(resource)
    else:
        replacement = tmp_path / "replacement"
        replacement.write_bytes(b"original")
        resource.unlink()
        resource.symlink_to(replacement)
    with pytest.raises(NativeError, match="resource"):
        guard.verify()


def test_optional_missing_configuration_cannot_appear_silently(tmp_path: Path):
    from bookscan.resources import ResourceBinding

    config = tmp_path / "optional.conf"
    guard = ResourceBinding.capture([], optional_files=[config])
    guard.verify()
    config.write_bytes(b"new config")
    with pytest.raises(NativeError, match="resource"):
        guard.verify()


def test_dangling_optional_link_is_not_absence(tmp_path: Path):
    from bookscan.resources import ResourceBinding

    config = tmp_path / "optional.conf"
    config.symlink_to(tmp_path / "missing")
    with pytest.raises(NativeError, match="resource"):
        ResourceBinding.capture([], optional_files=[config])


def test_missing_required_file_is_dependency_failure(tmp_path: Path):
    with pytest.raises(NativeError) as caught:
        binding(tmp_path / "missing")
    assert (caught.value.code, caught.value.exit_code) == ("DEPENDENCY_UNAVAILABLE", 5)


def test_record_has_digest_and_limitation_without_environment_values(tmp_path: Path):
    import json

    font = tmp_path / "font"
    font.write_bytes(b"font")
    guard = binding(font)
    environment = guard.environment()
    environment["BOOKSCAN_RESOURCE_TEST"] = "mutated-copy"
    assert guard.environment() == {"BOOKSCAN_RESOURCE_TEST": "captured"}
    record = guard.record()
    assert record["runtime_resources_verified"] is False
    assert "captured" not in json.dumps(record)
    assert len(str(record["environment_sha256"])) == 64


def test_cancel_during_resource_capture_propagates(tmp_path: Path):
    from bookscan.resources import ResourceBinding

    resource = tmp_path / "font"
    resource.write_bytes(b"font")
    selected = KeyboardInterrupt()

    def cancelled():
        raise selected

    with pytest.raises(KeyboardInterrupt) as caught:
        ResourceBinding.capture([resource], check_cancel=cancelled)
    assert caught.value is selected


def test_symlink_argument_binding_keeps_spelling_and_target(tmp_path: Path):
    resource = tmp_path / "font"
    resource.write_bytes(b"original")
    link = tmp_path / "alias"
    link.symlink_to(resource)
    guard = binding(link)
    guard.verify()
    link.unlink()
    link.symlink_to(tmp_path / "missing")
    with pytest.raises(NativeError, match="resource"):
        guard.verify()


def test_changing_environment_input_cannot_change_binding(tmp_path: Path):
    from bookscan.resources import ResourceBinding

    environment = {"BOOKSCAN_RESOURCE_TEST": "captured"}
    guard = ResourceBinding.capture([], environment=environment)
    environment["BOOKSCAN_RESOURCE_TEST"] = "changed"
    assert guard.environment()["BOOKSCAN_RESOURCE_TEST"] == "captured"
    assert os.environ.get("BOOKSCAN_RESOURCE_TEST") != "captured"


@pytest.mark.parametrize("phase", ["before", "during"])
def test_render_rejects_changed_resources_without_returning_pixels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
):
    import subprocess
    from collections.abc import Callable, Mapping

    from PIL import Image
    from test_render import source

    from bookscan import render

    saved = source(tmp_path)
    font = tmp_path / "font"
    font.write_bytes(b"font")
    guard = binding(font)
    launches: list[str] = []

    def child(
        argv: list[str],
        *,
        check_cancel: Callable[[], None],
        environment: Mapping[str, str],
        directory: Path,
    ) -> subprocess.CompletedProcess[str]:
        launches.append("renderer")
        assert environment["BOOKSCAN_RESOURCE_TEST"] == "captured"
        with Image.new("RGB", (10, 5), (97, 98, 99)) as image:
            image.save(argv[-1] + ".png")
        if phase == "during":
            font.write_bytes(b"changed")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(render, "execute", child)
    if phase == "before":
        font.write_bytes(b"changed")
    with pytest.raises(NativeError, match="resource"):
        render.render_page(saved, saved.pages[0], Path("/verified/renderer"), resources=guard)
    assert launches == ([] if phase == "before" else ["renderer"])
    saved.verify()


def test_render_returns_binding_provenance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import subprocess
    from collections.abc import Callable, Mapping

    from PIL import Image
    from test_render import source

    from bookscan import render

    saved = source(tmp_path)
    font = tmp_path / "font"
    font.write_bytes(b"font")
    guard = binding(font)

    def child(
        argv: list[str],
        *,
        check_cancel: Callable[[], None],
        environment: Mapping[str, str],
        directory: Path,
    ) -> subprocess.CompletedProcess[str]:
        with Image.new("RGB", (10, 5), (97, 98, 99)) as image:
            image.save(argv[-1] + ".png")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(render, "execute", child)
    raster = render.render_page(saved, saved.pages[0], Path("/verified/renderer"), resources=guard)
    assert raster.rgb == b"abc" * 50
    assert raster.resource_binding == guard.record()


@pytest.mark.parametrize("changed_during_analysis", [False, True])
def test_all_occurrence_assessment_carries_and_rechecks_resource_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed_during_analysis: bool
):
    import subprocess
    from collections.abc import Callable, Mapping

    from PIL import Image
    from test_assessment import native, source

    from bookscan import assessment, native_setup, render

    saved = source(tmp_path)
    font = tmp_path / "font"
    font.write_bytes(b"font")
    guard = binding(font)
    native(monkeypatch)
    original_assess = native_setup.assess

    def renderer(
        argv: list[str],
        *,
        check_cancel: Callable[[], None],
        environment: Mapping[str, str],
        directory: Path,
    ) -> subprocess.CompletedProcess[str]:
        with Image.frombytes("RGB", (10, 5), b"\x11\x22\x33" * 50) as image:
            image.save(argv[-1] + ".png")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def helper(
        binary: Path,
        baseline: Image.Image,
        directory: Path,
        *,
        check_cancel: Callable[[], None],
    ):
        result = original_assess(binary, baseline, directory, check_cancel=check_cancel)
        if changed_during_analysis:
            font.write_bytes(b"changed")
        return result

    monkeypatch.setattr(render, "execute", renderer)
    monkeypatch.setattr(native_setup, "assess", helper)
    iterator = assessment.assess_pages(
        saved, Path("renderer"), Path("helper"), tmp_path, resources=guard
    )
    if changed_during_analysis:
        with pytest.raises(NativeError, match="resource"):
            next(iterator)
    else:
        records = [item.to_dict() for item in iterator]
        assert [item["id"] for item in records] == ["occ-000001", "occ-000002", "occ-000003"]
        for item in records:
            render_record = cast(dict[str, object], item["render"])
            binding_record = cast(dict[str, object], render_record["resource_binding"])
            assert binding_record == guard.record()
            cast(list[object], binding_record["files"]).clear()
        assert guard.record()["files"]


def test_child_uses_explicit_working_directory(tmp_path: Path):
    result = execute([sys.executable, "-c", "import os; print(os.getcwd())"], directory=tmp_path)
    assert (result.returncode, result.stdout) == (0, str(tmp_path.resolve()) + "\n")


def test_binding_preserves_captured_cwd_after_caller_changes_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from bookscan.resources import ResourceBinding

    monkeypatch.chdir(tmp_path)
    guard = ResourceBinding.capture([])
    monkeypatch.chdir(tmp_path.parent)
    result = execute(
        [sys.executable, "-c", "import os; print(os.getcwd())"],
        environment=guard.environment(),
        directory=guard.directory,
    )
    assert result.stdout == str(tmp_path.resolve()) + "\n"


def test_binding_rejects_replaced_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from bookscan.resources import ResourceBinding

    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    guard = ResourceBinding.capture([])
    monkeypatch.chdir(tmp_path)
    cwd.rename(tmp_path / "old")
    cwd.mkdir()
    with pytest.raises(NativeError, match="directory"):
        guard.verify()
