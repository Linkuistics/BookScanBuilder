"""A cleaned private write must not strand an otherwise removable import.

The break is a stale directory journal after the own unlink, or accepting foreign
store activity as that unlink. Only native assessment is substituted; source,
writer ownership, PNG/blob stores and rollback use the actual filesystem.
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn, cast

import pikepdf
import pytest
from test_import_asset_rollback import freeze

from bookscan import initial_import, project_header

Exercise = Callable[[project_header.Stores, Path], None]
Run = Callable[[Exercise], BaseException]


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

    def run(exercise: Exercise) -> BaseException:
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


def publish(stores: project_header.Stores, kind: str, *, first: bool = False) -> None:
    if kind == "rgb":
        stores.images.publish(b"abc" if first else b"def", (1, 1))
    else:
        stores.native.publish(b"first-native" if first else b"second-native")


@pytest.mark.parametrize("kind", ["rgb", "native"])
@pytest.mark.parametrize("stage", ["write", "fsync", "staged-read", "link", "dedup-read"])
@pytest.mark.parametrize("preceding", [False, True])
def test_cleaned_failed_publication_allows_exact_import_rollback(
    failed_import: Run,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    stage: str,
    preceding: bool,
) -> None:
    selected = InterruptedError("selected cancellation during publication")

    def exercise(stores: project_header.Stores, directory: Path) -> None:
        if preceding:
            publish(stores, "rgb", first=True)
            publish(stores, "native", first=True)

        def fail(*args: Any, **kwargs: Any) -> NoReturn:
            raise selected

        if stage in {"write", "fsync", "link"}:
            monkeypatch.setattr(os, stage, fail)
        elif stage == "staged-read":
            monkeypatch.setattr(stores.images if kind == "rgb" else stores.native, "_read", fail)
        else:
            if not preceding:
                publish(stores, kind, first=True)
            target = stores.images if kind == "rgb" else stores.native
            original_read = cast(Callable[..., bytes], getattr(target, "_read"))

            def dedup_read(*args: Any, **kwargs: Any) -> bytes:
                if kwargs.get("name") is None:
                    raise selected
                return original_read(*args, **kwargs)

            monkeypatch.setattr(target, "_read", dedup_read)
        publish(stores, kind, first=stage == "dedup-read")

    caught = failed_import(exercise)
    # I/O failures retain the original exception as cause; cancellation keeps
    # identity. Journal reconciliation must never replace the chosen outcome.
    assert caught is selected or caught.__cause__ is selected
    assert not (tmp_path / "project").exists()


@pytest.mark.parametrize("kind", ["rgb", "native"])
@pytest.mark.parametrize("change", ["unknown", "prior-bytes", "mode", "unlink-mode", "checkpoint"])
def test_failed_publication_does_not_adopt_changed_or_committed_store(
    failed_import: Run,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    change: str,
) -> None:
    selected = RuntimeError("selected write failure with unrelated activity")
    captured: dict[str, bytes | tuple[int, ...]] = {}

    def exercise(stores: project_header.Stores, directory: Path) -> None:
        publish(stores, "rgb", first=True)
        publish(stores, "native", first=True)
        folder = directory / ("assets" if kind == "rgb" else "native-blobs")

        original_unlink = os.unlink

        def unlink(path: Any, *args: Any, **kwargs: Any) -> None:
            original_unlink(path, *args, **kwargs)
            if isinstance(path, str) and path.startswith((".rgb-", ".blob-")):
                folder.chmod(0o750)

        def fail(*args: Any, **kwargs: Any) -> NoReturn:
            if change == "unknown":
                (folder / "foreign").write_bytes(b"do not adopt or delete")
            elif change == "prior-bytes":
                next(p for p in folder.iterdir() if not p.name.startswith(".")).write_bytes(
                    b"changed previously captured bytes"
                )
            elif change == "mode":
                folder.chmod(0o750)
            elif change == "unlink-mode":
                monkeypatch.setattr(os, "unlink", unlink)
            else:
                stores.checkpoints.commit(
                    {"already": "committed"}, expected=None, verify_state=lambda state: None
                )
            raise selected

        monkeypatch.setattr(stores.images if kind == "rgb" else stores.native, "_read", fail)
        try:
            publish(stores, kind)
        except BaseException:
            captured.update(freeze(directory))
            raise

    assert failed_import(exercise) is selected
    assert freeze(tmp_path / "project") == captured


@pytest.mark.parametrize("kind", ["rgb", "native"])
def test_unlink_refusal_retains_private_name_and_selected_error(
    failed_import: Run, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    selected = RuntimeError("selected private-read failure")
    original_unlink = os.unlink

    def exercise(stores: project_header.Stores, directory: Path) -> None:
        def fail(*args: Any, **kwargs: Any) -> NoReturn:
            raise selected

        def refuse(path: Any, *args: Any, **kwargs: Any) -> None:
            if isinstance(path, str) and path.startswith((".rgb-", ".blob-")):
                raise PermissionError("private unlink refused")
            original_unlink(path, *args, **kwargs)

        monkeypatch.setattr(stores.images if kind == "rgb" else stores.native, "_read", fail)
        monkeypatch.setattr(os, "unlink", refuse)
        publish(stores, kind)

    assert failed_import(exercise) is selected
    project = tmp_path / "project"
    assert (project / "source.pdf").is_file() and (project / "writer.lock").is_file()
    folder = project / ("assets" if kind == "rgb" else "native-blobs")
    assert len(list(folder.iterdir())) == 1
    assert next(folder.iterdir()).name.startswith((".rgb-", ".blob-"))
    assert any("cleanup" in note.lower() for note in selected.__notes__)
