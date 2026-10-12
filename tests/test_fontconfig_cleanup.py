"""Fontconfig cache/snapshot cleanup preserves changed or unknown entries.

Actual native construction over empty test-owned font directories; no collection
is consulted. Originally authored red as the diagnostic under
docs/acceptance/baseline-fontconfig-cleanup-probe, preserved unchanged there.
"""

import hashlib
import json
import os
import stat
import subprocess
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import cast
from xml.sax.saxutils import escape

import pytest

from bookscan import fontconfig
from bookscan.import_publications import stamp
from bookscan.owned_tree import _Entry  # pyright: ignore[reportPrivateUsage]
from bookscan.render import renderer_path
from bookscan.skew import NativeError


class SelectedError(RuntimeError):
    pass


def inventory(root: Path) -> dict[str, object]:
    result: dict[str, object] = {}
    if not root.exists() and not root.is_symlink():
        return result
    for path in [root, *sorted(root.rglob("*"))]:
        info = path.lstat()
        item: dict[str, object] = {"stamp": stamp(info)}
        if stat.S_ISLNK(info.st_mode):
            item["target"] = os.readlink(path)
        elif stat.S_ISREG(info.st_mode):
            item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        result[str(path.relative_to(root))] = item
    return result


@contextmanager
def prepared(base: Path, kind: str) -> Iterator[tuple[Path, Path, fontconfig.FontconfigDiscovery]]:
    host = base / "host"
    config_dir, fonts = host / "config", host / "fonts"
    config_dir.mkdir(parents=True)
    fonts.mkdir()
    config = config_dir / "fonts.conf"
    config.write_text(
        "<fontconfig><dir>"
        + escape(str(fonts))
        + "</dir><cachedir>"
        + escape(str(host / "cache"))
        + "</cachedir></fontconfig>\n"
    )
    environment = dict(os.environ, FONTCONFIG_FILE=str(config), FONTCONFIG_PATH=str(config_dir))
    for name in ("FONTCONFIG_SYSROOT", "FC_DEBUG", "DYLD_INSERT_LIBRARIES", "DYLD_PRINT_LIBRARIES"):
        environment.pop(name, None)
    root = base / "private"
    renderer = renderer_path()
    if kind == "cache":
        config.write_text(
            config.read_text().replace(escape(str(host / "cache")), escape(str(root)))
        )
        context = fontconfig.prepared_fontconfig_cache(renderer, root, environment=environment)
    else:
        context = fontconfig.prepared_fontconfig_snapshot(
            renderer, root, config, environment=environment
        )
    with context as found:
        # Select a real native cache file or a real copied XML, never a mock.
        if kind == "cache":
            candidates = [p for p in root.iterdir() if p.is_file() and not p.is_symlink()]
        else:
            candidates = [Path(p) for p in found.scope.parsed_files if Path(p).is_relative_to(root)]
        assert candidates, "Native construction produced no subject"
        yield root, sorted(candidates)[0], found


KINDS = ("cache", "snapshot")
MUTATIONS = (
    "changed-bytes",
    "replaced-file",
    "file-mode",
    "hard-link",
    "extra-file",
    "extra-directory",
    "extra-symlink",
    "root-mode",
)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("outcome", ("success", "cancel", "error", "replaced-root"))
def test_clean_controls(tmp_path: Path, kind: str, outcome: str) -> None:
    selected: BaseException | None = None
    root = tmp_path / "private"
    before: dict[str, object] = {}
    try:
        with prepared(tmp_path, kind) as (root, _, found):
            found.binding.verify()
            before = inventory(root)
            if outcome == "cancel":
                selected = InterruptedError("selected cancellation")
                raise selected
            if outcome == "error":
                selected = SelectedError("selected processing error")
                raise selected
            if outcome == "replaced-root":
                root.rename(tmp_path / "displaced")
                root.mkdir()
                (root / "foreign").write_bytes(b"foreign root sentinel")
    except BaseException as error:
        if selected is not None:
            assert error is selected
        elif outcome == "replaced-root":
            assert isinstance(error, NativeError)
        else:
            raise
    (tmp_path / "observation.json").write_text(
        json.dumps({"before": before, "after": inventory(root)}, indent=2) + "\n"
    )
    if outcome == "replaced-root":
        assert (root / "foreign").read_bytes() == b"foreign root sentinel"
        displaced = inventory(tmp_path / "displaced")
        # Our rename changes only the displaced root's ctime; do not mistake
        # that authorized filesystem effect for deletion of supporting files.
        root_before = cast(dict[str, object], before["."])
        root_after = cast(dict[str, object], displaced["."])
        assert (
            cast(tuple[int, ...], root_after["stamp"])[:6]
            == cast(tuple[int, ...], root_before["stamp"])[:6]
        )
        assert displaced | {".": before["."]} == before
    else:
        assert not root.exists()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("outcome", ("return", "cancel", "error"))
@pytest.mark.parametrize("mutation", MUTATIONS)
def test_changed_entries_survive_cleanup(
    tmp_path: Path, kind: str, outcome: str, mutation: str
) -> None:
    # Removing a changed entry or recapturing it during teardown must fail this
    # independently declared preservation requirement. No byte equality can
    # authorize adopting a replacement inode or deleting an unknown child.
    selected: BaseException | None = None
    root = tmp_path / "private"
    expected: dict[str, object] = {}
    caught: dict[str, object] | None = None
    try:
        with prepared(tmp_path, kind) as (root, subject, _):
            original = inventory(root)
            if mutation == "changed-bytes":
                subject.write_bytes(subject.read_bytes() + b"changed after binding")
            elif mutation == "replaced-file":
                subject.rename(tmp_path / "displaced-file")
                subject.write_bytes(b"replacement sentinel")
            elif mutation == "file-mode":
                subject.chmod(0o640)
            elif mutation == "hard-link":
                os.link(subject, tmp_path / "extra-link")
            elif mutation == "extra-file":
                (root / "unknown").write_bytes(b"unknown child sentinel")
            elif mutation == "extra-directory":
                (root / "unknown").mkdir()
                (root / "unknown/sentinel").write_bytes(b"unknown nested sentinel")
            elif mutation == "extra-symlink":
                (tmp_path / "outside").write_bytes(b"outside sentinel")
                (root / "unknown").symlink_to(tmp_path / "outside")
            elif mutation == "root-mode":
                root.chmod(0o750)
            else:
                raise AssertionError(mutation)
            expected = inventory(root)
            assert expected != original, "Mutation did not change the measured subject"
            if outcome == "cancel":
                selected = InterruptedError("selected cancellation")
                raise selected
            if outcome == "error":
                selected = SelectedError("selected processing error")
                raise selected
    except BaseException as error:
        if selected is not None:
            assert error is selected, "Cleanup replaced the selected error"
        else:
            assert isinstance(error, NativeError)
        caught = {
            "type": type(error).__name__,
            "message": str(error),
            "notes": error.__notes__ if hasattr(error, "__notes__") else [],
        }
    actual = inventory(root)
    (tmp_path / "observation.json").write_text(
        json.dumps(
            {
                "expected": expected,
                "actual": actual,
                "error": caught,
                "preserved": actual == expected,
            },
            indent=2,
        )
        + "\n"
    )
    assert expected, "Construction/mutation did not complete"
    assert actual == expected, "Cleanup removed or changed an entry whose ownership was invalid"
    if mutation == "extra-symlink":
        assert (tmp_path / "outside").read_bytes() == b"outside sentinel"


def test_native_cache_replaces_precreated_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # FcDirCacheBasenameMD5 hashes this unsalted logical font path. The verified
    # 2.18.3 Mac build uses le64/cache-12 and compatibility symlinks 9..11.
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccache.c
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcatomic.c
    original = fontconfig.execute
    records: list[dict[str, object]] = []

    def execute(
        argv: list[str],
        *,
        environment: Mapping[str, str] | None = None,
        directory: Path | None = None,
        check_cancel: Callable[[], None] = lambda: None,
    ) -> subprocess.CompletedProcess[str]:
        if "--build-cache" not in argv:
            return original(
                argv, environment=environment, directory=directory, check_cancel=check_cancel
            )
        digest = hashlib.md5(os.fsencode(tmp_path / "host/fonts")).hexdigest()
        target = Path(argv[-1]) / (digest + "-le64.cache-12")
        with target.open("x+b", buffering=0) as held:
            held.write(b"precreated cache sentinel")
            before = stamp(os.fstat(held.fileno()))
            result = original(
                argv, environment=environment, directory=directory, check_cancel=check_cancel
            )
            named, after = stamp(target.lstat()), stamp(os.fstat(held.fileno()))
            held.seek(0)
            assert held.read() == b"precreated cache sentinel"
            assert before[:2] == after[:2] and named[:2] != before[:2]
            assert after[3] == 0 and named[3] == 1
            assert result.returncode == 0 and not result.stderr
            records.append(
                {"command": argv, "before": before, "held_after": after, "named_after": named}
            )
            return result

    monkeypatch.setattr(fontconfig, "execute", execute)
    with prepared(tmp_path, "cache") as (_, _, found):
        found.binding.verify()
    assert len(records) == 1
    (tmp_path / "observation.json").write_text(json.dumps(records, indent=2) + "\n")


def test_entry_match_binds_link_target_and_kind_beyond_the_stamp() -> None:
    # A retargeted link changes its inode/ctime on a real filesystem, so the stamp
    # alone already catches it; the target and kind remain independently bound.
    same = (1, 2, 3, 1, 4, 5, 6)
    assert _Entry("symlink", same, "a").matches(_Entry("symlink", same, "a"))
    assert not _Entry("symlink", same, "a").matches(_Entry("symlink", same, "b"))
    assert not _Entry("file", same).matches(_Entry("symlink", same, "a"))
