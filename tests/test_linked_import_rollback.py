"""Known linked aliases are removable; changed/unknown names never earn ownership.

Removing returned-link capture must fail the clean rollback cases. Updating alias
metadata without an own successful unlink, or adopting an extra link, must fail
preservation controls. Native assessment alone is replaced; import filesystem,
source, writer, stores and checkpoints remain real.
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn

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
@pytest.mark.parametrize("dedup", [False, True])
@pytest.mark.parametrize("preceding", [False, True])
def test_successful_publication_private_unlink_refusal_rolls_back_import(
    failed_import: Run,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    dedup: bool,
    preceding: bool,
) -> None:
    selected = PermissionError("selected private cleanup refusal")
    unlink = os.unlink
    refused = False

    def exercise(stores: project_header.Stores, directory: Path) -> None:
        if preceding:
            publish(stores, "rgb", first=True)
            publish(stores, "native", first=True)
        if dedup and not preceding:
            publish(stores, kind, first=True)

        def refuse_once(path: Any, *args: Any, **kwargs: Any) -> None:
            nonlocal refused
            if not refused and isinstance(path, str) and path.startswith((".rgb-", ".blob-")):
                refused = True
                raise selected
            unlink(path, *args, **kwargs)

        monkeypatch.setattr(os, "unlink", refuse_once)
        publish(stores, kind, first=dedup)

    caught = failed_import(exercise)
    assert caught.__cause__ is selected
    assert not (tmp_path / "project").exists()


@pytest.mark.parametrize("kind", ["rgb", "native"])
@pytest.mark.parametrize("dedup", [False, True])
@pytest.mark.parametrize(
    "change",
    [
        "bytes",
        "mode",
        "mtime",
        "replace-private",
        "replace-final",
        "extra-link",
        "foreign",
        "prior-bytes",
        "directory-mode",
        "checkpoint",
        "persistent",
    ],
)
def test_refused_linked_cleanup_preserves_changed_or_committed_import(
    failed_import: Run,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    dedup: bool,
    change: str,
) -> None:
    selected = PermissionError("selected refused cleanup with changed evidence")
    unlink = os.unlink
    captured: dict[str, bytes | tuple[int, ...]] = {}

    def exercise(stores: project_header.Stores, directory: Path) -> None:
        publish(stores, "rgb", first=True)
        publish(stores, "native", first=True)
        folder = directory / ("assets" if kind == "rgb" else "native-blobs")
        prior = next(folder.iterdir())

        def refuse(path: Any, *args: Any, **kwargs: Any) -> None:
            if not isinstance(path, str) or not path.startswith((".rgb-", ".blob-")):
                unlink(path, *args, **kwargs)
                return
            private = folder / path
            final = (
                prior
                if dedup
                else next(p for p in folder.iterdir() if p != prior and not p.name.startswith("."))
            )
            if change == "bytes":
                private.write_bytes(b"changed held file")
            elif change == "mode":
                private.chmod(0o640)
            elif change == "mtime":
                info = private.stat()
                os.utime(private, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000))
            elif change in {"replace-private", "replace-final"}:
                target = private if change == "replace-private" else final
                raw = target.read_bytes()
                target.rename(tmp_path / "original-held-file")
                target.write_bytes(raw)
            elif change == "extra-link":
                os.link(private, tmp_path / "outside-link")
            elif change == "foreign":
                (folder / "foreign").write_bytes(b"uncaptured remains")
            elif change == "prior-bytes":
                prior.write_bytes(b"changed prior file")
            elif change == "directory-mode":
                folder.chmod(0o750)
            elif change == "checkpoint":
                stores.checkpoints.commit(
                    {"already": "committed"}, expected=None, verify_state=lambda state: None
                )
            captured.update(freeze(directory))
            if change != "persistent":
                monkeypatch.setattr(os, "unlink", unlink)
            raise selected

        monkeypatch.setattr(os, "unlink", refuse)
        publish(stores, kind, first=dedup)

    caught = failed_import(exercise)
    assert caught.__cause__ is selected
    project = tmp_path / "project"
    if change == "persistent":
        # Cleanup can remove earlier captured names before reaching the refused
        # name; it must retain that name and its supporting source/bootstrap.
        folder = project / ("assets" if kind == "rgb" else "native-blobs")
        private = next(p for p in folder.iterdir() if p.name.startswith("."))
        key = str(private.relative_to(project))
        assert private.read_bytes() == captured[key]
        assert private.stat().st_nlink == (1 if dedup else 2)
        for name in ["source.pdf", "writer.lock", "project.json"]:
            assert (project / name).read_bytes() == captured[name]
            assert freeze(project)[name + ":stat"] == captured[name + ":stat"]
        assert any("retained" in note.lower() for note in caught.__notes__)
    else:
        assert freeze(project) == captured


@pytest.mark.parametrize("kind", ["rgb", "native"])
@pytest.mark.parametrize("change", ["bytes", "extra-link", "foreign", "checkpoint"])
def test_change_after_capture_before_rollback_preserves_linked_import(
    failed_import: Run,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    change: str,
) -> None:
    selected = PermissionError("first private cleanup refused")
    unlink = os.unlink
    captured: dict[str, bytes | tuple[int, ...]] = {}

    def exercise(stores: project_header.Stores, directory: Path) -> None:
        def refuse_once(path: Any, *args: Any, **kwargs: Any) -> None:
            if isinstance(path, str) and path.startswith((".rgb-", ".blob-")):
                monkeypatch.setattr(os, "unlink", unlink)
                raise selected
            unlink(path, *args, **kwargs)

        monkeypatch.setattr(os, "unlink", refuse_once)
        try:
            publish(stores, kind)
        except BaseException:
            folder = directory / ("assets" if kind == "rgb" else "native-blobs")
            private = next(p for p in folder.iterdir() if p.name.startswith("."))
            if change == "bytes":
                private.write_bytes(b"changed after capture")
            elif change == "extra-link":
                os.link(private, tmp_path / "outside-link")
            elif change == "foreign":
                (folder / "foreign").write_bytes(b"never captured")
            else:
                stores.checkpoints.commit(
                    {"already": "committed"}, expected=None, verify_state=lambda state: None
                )
            captured.update(freeze(directory))
            raise

    assert failed_import(exercise).__cause__ is selected
    assert freeze(tmp_path / "project") == captured


@pytest.mark.parametrize("kind", ["rgb", "native"])
@pytest.mark.parametrize(
    "change", ["bytes", "mode", "mtime", "replace", "extra-link", "foreign", "checkpoint", "refuse"]
)
def test_own_alias_unlink_never_adopts_changed_surviving_name(
    failed_import: Run,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    change: str,
) -> None:
    selected = PermissionError("selected initial private cleanup refusal")
    unlink = os.unlink
    captured: dict[str, bytes | tuple[int, ...]] = {}
    first = True
    final: Path | None = None

    def exercise(stores: project_header.Stores, directory: Path) -> None:
        folder = directory / ("assets" if kind == "rgb" else "native-blobs")

        def fault(path: Any, *args: Any, **kwargs: Any) -> None:
            nonlocal first, final
            if isinstance(path, str) and path.startswith((".rgb-", ".blob-")):
                if first:
                    first = False
                    final = next(p for p in folder.iterdir() if not p.name.startswith("."))
                    raise selected
                unlink(path, *args, **kwargs)
                assert final is not None
                if change == "bytes":
                    final.write_bytes(b"changed surviving alias")
                elif change == "mode":
                    final.chmod(0o640)
                elif change == "mtime":
                    info = final.stat()
                    os.utime(final, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000))
                elif change == "replace":
                    raw = final.read_bytes()
                    final.rename(tmp_path / "original-held-file")
                    final.write_bytes(raw)
                elif change == "extra-link":
                    os.link(final, tmp_path / "outside-link")
                elif change == "foreign":
                    (folder / "foreign").write_bytes(b"unknown remains")
                elif change == "checkpoint":
                    stores.checkpoints.commit(
                        {"already": "committed"}, expected=None, verify_state=lambda state: None
                    )
                captured.update(freeze(directory))
                return
            if change == "refuse" and final is not None and path == final.name:
                raise PermissionError("surviving final alias unlink refused")
            unlink(path, *args, **kwargs)

        monkeypatch.setattr(os, "unlink", fault)
        publish(stores, kind)

    assert failed_import(exercise).__cause__ is selected
    assert freeze(tmp_path / "project") == captured


@pytest.mark.parametrize("kind", ["rgb", "native"])
def test_returned_link_with_unknown_third_alias_never_grants_ownership(
    failed_import: Run,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    selected = PermissionError("private cleanup refused after additional link")
    link, unlink = os.link, os.unlink
    captured: dict[str, bytes | tuple[int, ...]] = {}

    def exercise(stores: project_header.Stores, directory: Path) -> None:
        def additional(*args: Any, **kwargs: Any) -> None:
            link(*args, **kwargs)
            link(args[0], tmp_path / "outside-link", src_dir_fd=kwargs["src_dir_fd"])

        def refuse_once(path: Any, *args: Any, **kwargs: Any) -> None:
            if isinstance(path, str) and path.startswith((".rgb-", ".blob-")):
                captured.update(freeze(directory))
                monkeypatch.setattr(os, "unlink", unlink)
                raise selected
            unlink(path, *args, **kwargs)

        monkeypatch.setattr(os, "link", additional)
        monkeypatch.setattr(os, "unlink", refuse_once)
        publish(stores, kind)

    assert failed_import(exercise).__cause__ is selected
    assert freeze(tmp_path / "project") == captured
    assert (tmp_path / "outside-link").is_file()
