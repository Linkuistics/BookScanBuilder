"""A transient private unlink failure must not strand a clean failed import.

Removing ownership capture should fail the clean cases. Ignoring the pre-unlink
stamp, exact inventory, directory mode or checkpoint guard should fail the
preservation cases. Source/reservation/writer/stores/rollback use the filesystem;
only native assessment and the named failing calls are substituted.
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn, cast

import pikepdf
import pytest
from test_aborted_publication import Run, publish
from test_import_asset_rollback import freeze

from bookscan import initial_import, project_header


@pytest.fixture
def failed_import(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Run:
    source, project = tmp_path / "input.pdf", tmp_path / "project"
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(72, 72))
        pdf.save(source)
    original_source = source.read_bytes()
    provision = project_header.Stores.provision
    stores: list[project_header.Stores] = []

    def remember(cls: type[project_header.Stores], *args: Any, **kwargs: Any) -> Any:
        result = provision(*args, **kwargs)
        stores.append(result)
        return result

    monkeypatch.setattr(project_header.Stores, "provision", classmethod(remember))

    def run(exercise: Callable[[project_header.Stores, Path], None]) -> BaseException:
        def fail(saved: object, directory: Path, **options: Any) -> NoReturn:
            exercise(stores[0], directory)
            raise AssertionError("The failing publication unexpectedly returned.")

        monkeypatch.setattr(initial_import, "_native", fail)
        progress = initial_import.Progress()
        with pytest.raises(BaseException) as caught:
            initial_import.create(source, project, cache=tmp_path / "cache", progress=progress)
        assert source.read_bytes() == original_source
        assert not progress.committed and progress.result is None
        return caught.value

    return run


@pytest.mark.parametrize("kind", ["rgb", "native"])
@pytest.mark.parametrize("stage", ["write", "fsync", "staged-read", "link", "dedup-read"])
@pytest.mark.parametrize("preceding", [False, True])
def test_transient_private_unlink_refusal_allows_import_rollback(
    failed_import: Run,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    stage: str,
    preceding: bool,
) -> None:
    selected = RuntimeError("selected publication failure")
    unlink = os.unlink
    write = os.write
    refused = False

    def exercise(stores: project_header.Stores, directory: Path) -> None:
        if preceding:
            publish(stores, "rgb", first=True)
            publish(stores, "native", first=True)
        if stage == "dedup-read" and not preceding:
            publish(stores, kind, first=True)

        def refuse_once(path: Any, *args: Any, **kwargs: Any) -> None:
            nonlocal refused
            if not refused and isinstance(path, str) and path.startswith((".rgb-", ".blob-")):
                refused = True
                raise PermissionError("first private unlink refused")
            unlink(path, *args, **kwargs)

        def fail(*args: Any, **kwargs: Any) -> NoReturn:
            if stage == "write":
                write(args[0], b"partial bytes")
            raise selected

        target = stores.images if kind == "rgb" else stores.native
        monkeypatch.setattr(os, "unlink", refuse_once)
        if stage in {"write", "fsync", "link"}:
            monkeypatch.setattr(os, stage, fail)
        elif stage == "staged-read":
            monkeypatch.setattr(target, "_read", fail)
        else:
            original_read = cast(Callable[..., bytes], getattr(target, "_read"))

            def read(*args: Any, **kwargs: Any) -> bytes:
                if kwargs.get("name") is None:
                    raise selected
                return original_read(*args, **kwargs)

            monkeypatch.setattr(target, "_read", read)
        publish(stores, kind, first=stage == "dedup-read")

    assert failed_import(exercise) is selected
    assert not (tmp_path / "project").exists()


@pytest.mark.parametrize("kind", ["rgb", "native"])
@pytest.mark.parametrize(
    "change",
    [
        "bytes",
        "mode",
        "mtime",
        "replace",
        "symlink",
        "hardlink",
        "foreign",
        "prior-bytes",
        "directory-mode",
        "checkpoint",
    ],
)
def test_refused_private_cleanup_never_adopts_changes_or_checkpoint(
    failed_import: Run,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    change: str,
) -> None:
    selected = RuntimeError("selected failed private read")
    captured: dict[str, bytes | tuple[int, ...]] = {}
    unlink = os.unlink

    def exercise(stores: project_header.Stores, directory: Path) -> None:
        publish(stores, "rgb", first=True)
        publish(stores, "native", first=True)
        folder = directory / ("assets" if kind == "rgb" else "native-blobs")
        external = tmp_path / "external"
        external.write_bytes(b"external remains")

        def refuse(path: Any, *args: Any, **kwargs: Any) -> None:
            if not isinstance(path, str) or not path.startswith((".rgb-", ".blob-")):
                unlink(path, *args, **kwargs)
                return
            private = folder / path
            if change == "bytes":
                private.write_bytes(b"changed private bytes")
            elif change == "mode":
                private.chmod(0o640)
            elif change == "mtime":
                info = private.stat()
                os.utime(private, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000))
            elif change == "replace":
                raw = private.read_bytes()
                private.rename(tmp_path / "original-held-file")
                private.write_bytes(raw)
            elif change == "symlink":
                private.rename(tmp_path / "original-held-file")
                private.symlink_to(external)
            elif change == "hardlink":
                os.link(private, tmp_path / "outside-link")
            elif change == "foreign":
                (folder / "foreign").write_bytes(b"foreign remains")
            elif change == "prior-bytes":
                next(p for p in folder.iterdir() if not p.name.startswith(".")).write_bytes(
                    b"changed prior publication"
                )
            elif change == "directory-mode":
                folder.chmod(0o750)
            else:
                stores.checkpoints.commit(
                    {"already": "committed"}, expected=None, verify_state=lambda state: None
                )
            captured.update(freeze(directory))
            # The refusal is transient. A blind retry would delete the changed
            # private file; correct rollback refuses it before any asset removal.
            monkeypatch.setattr(os, "unlink", unlink)
            raise PermissionError("refused private unlink with changed evidence")

        def fail(*args: Any, **kwargs: Any) -> NoReturn:
            raise selected

        monkeypatch.setattr(os, "unlink", refuse)
        monkeypatch.setattr(stores.images if kind == "rgb" else stores.native, "_read", fail)
        publish(stores, kind)

    assert failed_import(exercise) is selected
    assert freeze(tmp_path / "project") == captured
    assert (tmp_path / "external").read_bytes() == b"external remains"


@pytest.mark.parametrize("kind", ["rgb", "native"])
@pytest.mark.parametrize("stage", ["open-without-descriptor", "link-without-outcome"])
def test_uncertain_creation_or_link_outcome_retains_uncaptured_files(
    failed_import: Run,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    stage: str,
) -> None:
    selected = RuntimeError("operation failed before its outcome returned")
    captured: dict[str, bytes | tuple[int, ...]] = {}
    original_open, original_link, original_unlink = os.open, os.link, os.unlink

    def exercise(stores: project_header.Stores, directory: Path) -> None:
        publish(stores, "rgb", first=True)
        publish(stores, "native", first=True)

        def opened(path: Any, *args: Any, **kwargs: Any) -> int:
            descriptor = original_open(path, *args, **kwargs)
            if isinstance(path, str) and path.startswith((".rgb-", ".blob-")):
                os.close(descriptor)
                captured.update(freeze(directory))
                raise selected
            return descriptor

        def linked(*args: Any, **kwargs: Any) -> NoReturn:
            original_link(*args, **kwargs)
            captured.update(freeze(directory))
            raise selected

        def refuse_once(path: Any, *args: Any, **kwargs: Any) -> None:
            if isinstance(path, str) and path.startswith((".rgb-", ".blob-")):
                monkeypatch.setattr(os, "unlink", original_unlink)
                raise PermissionError("first unlink refused after unknown link outcome")
            original_unlink(path, *args, **kwargs)

        if stage == "open-without-descriptor":
            monkeypatch.setattr(os, "open", opened)
        else:
            monkeypatch.setattr(os, "link", linked)
            monkeypatch.setattr(os, "unlink", refuse_once)
        publish(stores, kind)

    assert failed_import(exercise) is selected
    assert freeze(tmp_path / "project") == captured
