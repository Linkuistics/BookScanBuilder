"""A cache pointer cannot authorize incomplete, changed or foreign helper bytes."""

import hashlib
import json
from pathlib import Path

import pytest

from bookscan.native_setup import load_cache, preflight
from bookscan.skew import NativeError


def cache_fixture(cache: Path) -> Path:
    subjects = {"subject": "literal test data"}
    identity = hashlib.sha256(json.dumps(subjects, sort_keys=True).encode()).hexdigest()
    entry = cache / ("native-" + identity + "-" + "b" * 32)
    entry.mkdir(parents=True)
    binary = entry / "skew"
    binary.write_bytes(b"test-owned compiled bytes")
    binary.chmod(0o700)
    manifest = {
        "schema": "BookScanBuilderNativeBuild",
        "version": 1,
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "build_identity": identity,
        "inputs": subjects,
    }
    (entry / "build.json").write_text(json.dumps(manifest))
    (cache / "current.json").write_text(json.dumps({"entry": entry.name}))
    return binary


def test_preflight_missing_cache_never_builds(tmp_path: Path) -> None:
    cache = tmp_path / "absent"
    with pytest.raises(NativeError) as caught:
        preflight(cache)
    assert caught.value.code == "DEPENDENCY_UNAVAILABLE"
    assert caught.value.exit_code == 5
    assert "process:setup" in caught.value.remediation
    assert not cache.exists()


def test_load_verifies_complete_executable_bytes(tmp_path: Path) -> None:
    binary = cache_fixture(tmp_path)
    helper = load_cache(tmp_path)
    assert helper.binary == binary
    binary.write_bytes(b"changed")
    with pytest.raises(NativeError):
        load_cache(tmp_path)


@pytest.mark.parametrize("missing", ["skew", "build.json"])
def test_incomplete_cache_is_not_a_build(tmp_path: Path, missing: str) -> None:
    binary = cache_fixture(tmp_path)
    (binary.parent / missing).unlink()
    with pytest.raises(NativeError):
        load_cache(tmp_path)


@pytest.mark.parametrize("entry", ["../outside", "/tmp/elsewhere", "native-partial", ""])
def test_foreign_pointer_is_rejected(tmp_path: Path, entry: str) -> None:
    (tmp_path / "current.json").write_text(json.dumps({"entry": entry}))
    with pytest.raises(NativeError):
        load_cache(tmp_path)


@pytest.mark.parametrize("name", ["current.json", "build.json", "skew"])
def test_replaced_symlink_entry_is_rejected(tmp_path: Path, name: str) -> None:
    binary = cache_fixture(tmp_path)
    target = tmp_path / name if name == "current.json" else binary.parent / name
    elsewhere = tmp_path / "foreign"
    target.rename(elsewhere)
    target.symlink_to(elsewhere)
    with pytest.raises(NativeError):
        load_cache(tmp_path)


def test_symlinked_build_directory_is_rejected(tmp_path: Path) -> None:
    binary = cache_fixture(tmp_path)
    directory = binary.parent
    directory.rename(tmp_path / "foreign")
    directory.symlink_to(tmp_path / "foreign", target_is_directory=True)
    with pytest.raises(NativeError):
        load_cache(tmp_path)


def test_unexecutable_bytes_are_not_a_helper(tmp_path: Path) -> None:
    binary = cache_fixture(tmp_path)
    binary.chmod(0o600)
    with pytest.raises(NativeError):
        load_cache(tmp_path)


@pytest.mark.parametrize("version", [True, 2])
def test_unknown_cache_protocol_is_rejected(tmp_path: Path, version: object) -> None:
    binary = cache_fixture(tmp_path)
    manifest_path = binary.parent / "build.json"
    manifest: dict[str, object] = json.loads(manifest_path.read_text())
    manifest["version"] = version
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(NativeError):
        load_cache(tmp_path)


def test_changed_build_inputs_cannot_retain_old_identity(tmp_path: Path) -> None:
    binary = cache_fixture(tmp_path)
    manifest_path = binary.parent / "build.json"
    manifest: dict[str, object] = json.loads(manifest_path.read_text())
    manifest["inputs"] = {"subject": "foreign build subjects"}
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(NativeError):
        load_cache(tmp_path)
