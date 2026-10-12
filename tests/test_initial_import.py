"""Contest the create owner with real source/assets/checkpoint transactions.

The substituted native context supplies independently constructed RGB records;
it establishes orchestration/storage, never native execution or source fidelity.
"""

import copy
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from test_baseline_state import evidence as evidence
from test_baseline_state import owner as owner
from test_import_assembly import inputs as inputs

from bookscan import assessment, baseline_state, checkpoints, finite_status, intake, ownership
from bookscan.project_header import Stores
from bookscan.skew import NativeError


def invoke(source: Path, project: Path, **options: Any) -> Any:
    from bookscan import initial_import

    return initial_import.create(source, project, cache=project.parent / "cache", **options)


@pytest.mark.parametrize("fault", ["missing", "invalid", "empty"])
def test_source_failure_precedes_native_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    from bookscan import initial_import

    source, project = tmp_path / "input.pdf", tmp_path / "project"
    if fault == "invalid":
        source.write_bytes(b"not a PDF")
    elif fault == "empty":
        import pikepdf

        with pikepdf.Pdf.new() as pdf:
            pdf.save(source)

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Native preflight must follow supported-source validation")

    monkeypatch.setattr(initial_import, "_native", denied)
    progress = initial_import.Progress()
    with pytest.raises(intake.ImportFailure) as error:
        invoke(source, project, progress=progress)
    assert (
        error.value.code
        == {
            "missing": "SOURCE_NOT_FOUND",
            "invalid": "SOURCE_UNSUPPORTED",
            "empty": "SOURCE_EMPTY",
        }[fault]
    )
    assert not progress.committed
    assert not project.exists()


@pytest.fixture
def constructed(
    inputs: tuple[Stores, intake.Snapshot, list[assessment.AssessedPage], dict[str, Any]],  # noqa: F811
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, dict[str, Any]]:
    from bookscan import initial_import

    _, saved, subjects, data = inputs
    source, project = tmp_path / "source copy.pdf", tmp_path / "created"
    source.write_bytes(saved.path.read_bytes())
    facts: dict[str, Any] = {"events": [], "fault": None, "subjects": subjects}

    @contextmanager
    def native(snapshot: intake.Snapshot, directory: Path, **options: Any) -> Iterator[Any]:
        assert snapshot.path == directory / "source.pdf"
        snapshot.verify()
        facts["events"].append("native-enter")
        if facts["fault"] == "dependency":
            raise NativeError("Constructed unavailable dependency")
        header = directory / "project.json"
        assert header.exists()

        def verify() -> None:
            snapshot.verify()
            facts["events"].append("native-verify")
            if facts["fault"] == "resource":
                raise NativeError("Constructed late resource replacement")
            if facts["fault"] == "late-corruption":
                asset = next((directory / "assets").iterdir())
                asset.write_bytes(b"late corrupt asset")

        def pages() -> Iterator[assessment.AssessedPage]:
            # The actual writer remains held while lazy native subjects run.
            from bookscan import project_header

            def verify_read(stores: Stores, value: dict[str, object]) -> None:
                baseline_state.restore(stores, value)

            with pytest.raises(ownership.OwnershipError) as busy:
                with project_header.resume(directory, verify_state=verify_read):
                    pass
            assert busy.value.code == "PROJECT_BUSY"
            current = facts["subjects"]
            for subject in current:
                command = list(subject.raster.command)
                command[15] = str(snapshot.path)
                yield replace(subject, raster=replace(subject.raster, command=tuple(command)))

        try:
            yield initial_import.NativeImport(
                copy.deepcopy(data["dependencies"]),
                copy.deepcopy(data["resource_binding"]),
                data["fontconfig"],
                pages(),
                verify,
            )
        finally:
            facts["events"].append("native-exit")
            if facts["fault"] == "cleanup":
                raise NativeError("Constructed post-commit cleanup failure")

    monkeypatch.setattr(initial_import, "_native", native)
    return source, project, facts


def test_complete_commit_reopens_after_source_loss_with_order_and_duplicates(
    constructed: tuple[Path, Path, dict[str, Any]],
) -> None:
    from bookscan import initial_import

    source, project, facts = constructed
    progress = initial_import.Progress()
    result = invoke(source, project, progress=progress)
    assert progress.committed and progress.result == result
    assert result.checkpoint.revision == 1 and result.checkpoint.previous is None
    source.unlink()
    status = finite_status.status(project)
    assert status["checkpoint_sha256"] == result.checkpoint.sha256
    pages = cast(list[dict[str, Any]], status["pages"])
    assert [page["id"] for page in pages] == ["occ-000001", "occ-000002", "occ-000003"]
    assert pages[0]["image_sha256"] == pages[1]["image_sha256"]
    assert all(page["inspections"] == [] and page["dispositions"] == [] for page in pages)
    assert status["acknowledgement"] is None
    assert facts["events"] == ["native-enter", "native-verify", "native-exit"]


@pytest.mark.parametrize(
    "fault", ["dependency", "resource", "partial", "bad-rgb", "late-corruption"]
)
def test_unfinished_or_invalid_import_never_commits(
    constructed: tuple[Path, Path, dict[str, Any]], fault: str
) -> None:
    from bookscan import initial_import

    source, project, facts = constructed
    before = source.read_bytes()
    facts["fault"] = fault
    if fault == "partial":
        facts["subjects"] = facts["subjects"][:-1]
    elif fault == "bad-rgb":
        pages = list(facts["subjects"])
        pages[-1] = replace(pages[-1], raster=replace(pages[-1].raster, rgb=b"wrong"))
        facts["subjects"] = pages
    progress = initial_import.Progress()
    with pytest.raises((NativeError, baseline_state.BaselineStateError)):
        invoke(source, project, progress=progress)
    assert not progress.committed and progress.result is None
    assert not (project / "checkpoints" / "current").exists()
    if fault != "late-corruption":
        assert not project.exists()
    else:
        # A changed published asset is no longer safe to remove. Keep source,
        # lock and all stores; captured unmodified publications roll back above.
        assert (project / "source.pdf").read_bytes() == before
        assert (project / "writer.lock").is_file()
    assert source.read_bytes() == before
    # Incomplete nonempty reservations stay unusable; no unknown-entry sweep.
    with pytest.raises(Exception) as error:
        finite_status.status(project)
    assert getattr(error.value, "code") == "INVALID_PROJECT"


def test_store_error_after_actual_commit_retains_outcome_latch(
    constructed: tuple[Path, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    original = checkpoints.Checkpoints.commit

    def failed_after(self: checkpoints.Checkpoints, *args: Any, **kwargs: Any) -> Any:
        original(self, *args, **kwargs)
        raise checkpoints.CheckpointError("WRITE_FAILED", "Post-commit store failure", 5, True)

    monkeypatch.setattr(checkpoints.Checkpoints, "commit", failed_after)
    progress = initial_import.Progress()
    with pytest.raises(checkpoints.CheckpointError, match="Post-commit store failure"):
        invoke(source, project, progress=progress)
    assert progress.committed and progress.result is None
    assert finite_status.status(project)["status"] == "verified"


def test_post_commit_native_cleanup_failure_preserves_committed_fact_and_resume(
    constructed: tuple[Path, Path, dict[str, Any]],
) -> None:
    from bookscan import initial_import

    source, project, facts = constructed
    facts["fault"] = "cleanup"
    progress = initial_import.Progress()
    with pytest.raises(NativeError, match="post-commit cleanup"):
        invoke(source, project, progress=progress)
    assert progress.committed and progress.result is not None
    assert finite_status.status(project)["checkpoint_sha256"] == progress.result.checkpoint.sha256


@pytest.mark.parametrize("committed", [False, True])
def test_cancellation_preserves_actual_checkpoint_boundary(
    constructed: tuple[Path, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    committed: bool,
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    original = checkpoints.Checkpoints.commit
    caught = False

    def check() -> None:
        if caught:
            raise InterruptedError("Chosen cancellation")

    def boundary(self: checkpoints.Checkpoints, *args: Any, **kwargs: Any) -> Any:
        nonlocal caught
        if committed:
            result = original(self, *args, **kwargs)
            caught = True
            return result
        caught = True
        check()

    monkeypatch.setattr(checkpoints.Checkpoints, "commit", boundary)
    progress = initial_import.Progress()
    with pytest.raises(InterruptedError, match="Chosen cancellation"):
        invoke(source, project, progress=progress, check_cancel=check)
    assert progress.committed is committed
    assert (project / "checkpoints" / "current").is_symlink() is committed
    if committed:
        assert (project / "source.pdf").read_bytes() == source.read_bytes()
        assert finite_status.status(project)["status"] == "verified"
    else:
        assert not project.exists()


def test_occupied_destination_is_unchanged_and_progress_cannot_be_reused(
    constructed: tuple[Path, Path, dict[str, Any]],
) -> None:
    from bookscan import initial_import
    from bookscan.project_reservation import ReservationError

    source, project, facts = constructed
    project.mkdir()
    marker = project / "foreign"
    marker.write_bytes(b"leave untouched")
    progress = initial_import.Progress()
    with pytest.raises(ReservationError) as error:
        invoke(source, project, progress=progress)
    assert error.value.code == "PROJECT_EXISTS"
    assert marker.read_bytes() == b"leave untouched" and facts["events"] == []
    with pytest.raises(ValueError, match="already used"):
        invoke(source, project.parent / "second", progress=progress)
    assert not (project.parent / "second").exists()


def test_failure_cleans_snapshot_without_sweeping_unknown_children(
    constructed: tuple[Path, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    original = source.read_bytes()
    failure = NativeError("Chosen failure after source snapshot")

    def fail(*args: Any, **kwargs: Any) -> Any:
        (project / "unknown").write_bytes(b"foreign")
        (project / "unknown-empty-directory").mkdir()
        raise failure

    monkeypatch.setattr(initial_import, "_native", fail)
    progress = initial_import.Progress()
    with pytest.raises(NativeError) as caught:
        invoke(source, project, progress=progress)
    assert caught.value is failure
    assert not (project / "source.pdf").exists()
    assert (project / "unknown").read_bytes() == b"foreign"
    assert (project / "unknown-empty-directory").is_dir()
    assert source.read_bytes() == original and not progress.committed


@pytest.mark.parametrize("change", ["replace", "modify", "symlink", "hardlink", "root"])
def test_failed_import_keeps_changed_source_or_root(
    constructed: tuple[Path, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    before = source.read_bytes()
    failure = NativeError("Chosen source replacement failure")
    moved = project.parent / "old-project"

    def fail(*args: Any, **kwargs: Any) -> Any:
        saved = project / "source.pdf"
        if change == "root":
            project.rename(moved)
            project.mkdir()
            saved.write_bytes(b"foreign")
        elif change == "modify":
            saved.write_bytes(b"changed")
        else:
            saved.rename(project / "old-source.pdf")
            if change == "replace":
                saved.write_bytes(b"foreign")
            elif change == "symlink":
                saved.symlink_to(source)
            else:
                os.link(source, saved)
        raise failure

    monkeypatch.setattr(initial_import, "_native", fail)
    with pytest.raises(NativeError) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure
    assert (project / "source.pdf").read_bytes() == (
        before
        if change in {"symlink", "hardlink"}
        else b"changed"
        if change == "modify"
        else b"foreign"
    )
    if change == "root":
        assert (moved / "source.pdf").read_bytes() == before
    assert source.read_bytes() == before
    assert any("source" in note.lower() for note in failure.__notes__)


def test_source_cleanup_error_preserves_selected_failure(
    constructed: tuple[Path, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    failure = NativeError("Chosen native failure")
    unlink = os.unlink

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise failure

    def denied(path: Any, *args: Any, **kwargs: Any) -> None:
        if str(path) == "source.pdf":
            raise PermissionError("Constructed snapshot unlink denial")
        unlink(path, *args, **kwargs)

    monkeypatch.setattr(initial_import, "_native", fail)
    monkeypatch.setattr(os, "unlink", denied)
    with pytest.raises(NativeError) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure
    assert (project / "source.pdf").read_bytes() == source.read_bytes()
    assert any("source" in note.lower() and "cleanup" in note.lower() for note in failure.__notes__)


@pytest.mark.parametrize("cancelled", [False, True])
def test_failure_before_bootstrap_cleans_snapshot_and_empty_root(
    constructed: tuple[Path, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    cancelled: bool,
) -> None:
    from bookscan import initial_import

    source, project, facts = constructed
    before = source.read_bytes()
    failure = InterruptedError("chosen cancellation") if cancelled else OSError("chosen failure")

    def fail(*args: Any, **kwargs: Any) -> Any:
        assert (project / "source.pdf").read_bytes() == before
        raise failure

    monkeypatch.setattr(ownership, "provision", fail)
    with pytest.raises(type(failure)) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure
    assert not project.exists() and source.read_bytes() == before
    assert facts["events"] == []


def test_failed_import_with_missing_snapshot_keeps_original_error_without_source_cleanup_note(
    constructed: tuple[Path, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    before = source.read_bytes()
    failure = NativeError("Chosen failure with missing owned snapshot")

    def fail(*args: Any, **kwargs: Any) -> Any:
        (project / "source.pdf").unlink()
        raise failure

    monkeypatch.setattr(initial_import, "_native", fail)
    with pytest.raises(NativeError) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure
    assert source.read_bytes() == before
    assert not any("source" in note.lower() for note in getattr(failure, "__notes__", []))


@pytest.mark.parametrize("fault", ["chmod", "sync"])
def test_bootstrap_io_failure_cleans_owned_lock_snapshot_and_empty_root(
    constructed: tuple[Path, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    from bookscan import initial_import

    source, project, facts = constructed
    before = source.read_bytes()
    provision = ownership.provision

    def fail(fd: int, *args: Any) -> None:
        raise OSError("chosen bootstrap I/O failure")

    def bootstrap(path: Path) -> ownership.LockIdentity:
        with monkeypatch.context() as patch:
            patch.setattr(os, "fchmod" if fault == "chmod" else "fsync", fail)
            return provision(path)

    monkeypatch.setattr(ownership, "provision", bootstrap)
    progress = initial_import.Progress()
    with pytest.raises(ownership.OwnershipError, match="chosen bootstrap I/O failure"):
        invoke(source, project, progress=progress)
    assert not project.exists()
    assert source.read_bytes() == before
    assert facts["events"] == [] and not progress.committed


@pytest.mark.parametrize("cancelled", [False, True])
def test_acquired_writer_bootstrap_failure_cleans_lock_source_and_empty_root(
    constructed: tuple[Path, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    cancelled: bool,
) -> None:
    from bookscan import initial_import

    source, project, facts = constructed
    before = source.read_bytes()
    failure = (
        InterruptedError("chosen cancellation") if cancelled else RuntimeError("chosen failure")
    )

    def fail(writer: ownership.Writer, **options: Any) -> Any:
        writer.verify()
        with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
            ownership.Writer.acquire(writer.path, writer.identity)
        raise failure

    monkeypatch.setattr(Stores, "provision", fail)
    progress = initial_import.Progress()
    with pytest.raises(type(failure)) as caught:
        invoke(source, project, progress=progress)
    assert caught.value is failure
    assert not project.exists() and source.read_bytes() == before
    assert not progress.committed and facts["events"] == []
    assert not getattr(failure, "__notes__", [])


@pytest.mark.parametrize("unknown", ["file", "directory"])
def test_acquired_writer_cleanup_preserves_unknown_children(
    constructed: tuple[Path, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    unknown: str,
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    failure = RuntimeError("chosen bootstrap failure with unknown child")

    def fail(writer: ownership.Writer, **options: Any) -> Any:
        marker = writer.path / "foreign"
        if unknown == "file":
            marker.write_bytes(b"unknown bytes")
        else:
            marker.mkdir()
        raise failure

    monkeypatch.setattr(Stores, "provision", fail)
    with pytest.raises(RuntimeError) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure
    assert not (project / "writer.lock").exists() and not (project / "source.pdf").exists()
    if unknown == "file":
        assert (project / "foreign").read_bytes() == b"unknown bytes"
    else:
        assert (project / "foreign").is_dir()
    assert source.is_file()


@pytest.mark.parametrize(
    "change", ["replace", "modify", "same-bytes", "symlink", "hardlink", "fifo", "root", "parent"]
)
def test_acquired_writer_cleanup_keeps_changed_lock_or_ancestry(
    constructed: tuple[Path, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    before = source.read_bytes()
    failure = RuntimeError("chosen bootstrap failure after replacement")
    moved = project.parent.parent / (project.parent.name + "-moved")
    retained: list[Path] = []

    def fail(writer: ownership.Writer, **options: Any) -> Any:
        lock = writer.path / "writer.lock"
        original = lock.read_bytes()
        if change == "root":
            writer.path.rename(moved)
            writer.path.mkdir()
            lock.write_bytes(b"foreign root")
            retained.append(moved / "writer.lock")
        elif change == "parent":
            writer.path.parent.rename(moved)
            writer.path.parent.mkdir()
            writer.path.mkdir()
            lock.write_bytes(b"foreign parent")
            retained.append(moved / project.name / "writer.lock")
        elif change in {"modify", "same-bytes"}:
            lock.write_bytes(original if change == "same-bytes" else b"changed")
        else:
            lock.rename(writer.path / "old-lock")
            if change == "replace":
                lock.write_bytes(original)
            elif change == "symlink":
                lock.symlink_to("old-lock")
            elif change == "hardlink":
                os.link(writer.path / "old-lock", lock)
            else:
                os.mkfifo(lock)
        retained.append(lock)
        raise failure

    monkeypatch.setattr(Stores, "provision", fail)
    with pytest.raises(RuntimeError) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure and all(p.lstat() for p in retained)
    if change == "parent":
        assert (moved / source.name).read_bytes() == before
    else:
        assert source.read_bytes() == before
    assert any("writer lock" in note.lower() for note in failure.__notes__)


@pytest.mark.parametrize("missing", [False, True])
def test_acquired_writer_cleanup_unlink_refusal_or_missing_lock_preserves_error(
    constructed: tuple[Path, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    missing: bool,
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    failure = RuntimeError("chosen bootstrap failure")
    unlink = os.unlink

    def fail(writer: ownership.Writer, **options: Any) -> Any:
        if missing:
            (writer.path / "writer.lock").unlink()
        raise failure

    def denied(path: Any, *args: Any, **kwargs: Any) -> None:
        if str(path) == "writer.lock":
            raise PermissionError("chosen lock cleanup refusal")
        unlink(path, *args, **kwargs)

    monkeypatch.setattr(Stores, "provision", fail)
    monkeypatch.setattr(os, "unlink", denied)
    with pytest.raises(RuntimeError) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure and source.is_file()
    if missing:
        assert not project.exists() and not getattr(failure, "__notes__", [])
    else:
        assert (project / "writer.lock").is_file()
        assert any("writer lock" in note.lower() for note in failure.__notes__)


def test_acquired_writer_cleanup_still_holds_kernel_ownership(
    constructed: tuple[Path, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    failure = RuntimeError("chosen bootstrap failure")
    unlink = os.unlink
    identities: list[ownership.LockIdentity] = []
    checked: list[bool] = []

    def fail(writer: ownership.Writer, **options: Any) -> Any:
        identities.append(writer.identity)
        raise failure

    def observe(path: Any, *args: Any, **kwargs: Any) -> None:
        if str(path) == "writer.lock":
            with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
                ownership.Writer.acquire(project, identities[0])
            checked.append(True)
        unlink(path, *args, **kwargs)

    monkeypatch.setattr(Stores, "provision", fail)
    monkeypatch.setattr(os, "unlink", observe)
    with pytest.raises(RuntimeError) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure and checked == [True]
    assert not project.exists() and source.is_file()


def test_acquired_writer_cleanup_allows_read_only_atime_change(
    constructed: tuple[Path, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    failure = RuntimeError("chosen failure after lock read")

    def fail(writer: ownership.Writer, **options: Any) -> Any:
        assert (writer.path / "writer.lock").read_bytes() == writer.identity.content
        raise failure

    monkeypatch.setattr(Stores, "provision", fail)
    with pytest.raises(RuntimeError) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure and not project.exists() and source.is_file()


@pytest.mark.parametrize("code", ["PROJECT_BUSY", "DEPENDENCY_UNAVAILABLE"])
def test_failed_writer_acquisition_keeps_successfully_provisioned_lock(
    constructed: tuple[Path, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch, code: str
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    failure = ownership.OwnershipError(
        code, "chosen acquisition refusal", 4 if code == "PROJECT_BUSY" else 5
    )

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise failure

    monkeypatch.setattr(ownership.Writer, "acquire", fail)
    with pytest.raises(ownership.OwnershipError) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure
    assert (project / "writer.lock").is_file() and source.is_file()
    assert not (project / "source.pdf").exists()


def test_acquired_writer_cleanup_keeps_integer_nanosecond_mutation(
    constructed: tuple[Path, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    provision = ownership.provision
    failure = RuntimeError("chosen bootstrap failure after timestamp mutation")

    def fixed(path: Path) -> ownership.LockIdentity:
        identity = provision(path)
        os.utime(path / "writer.lock", ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))
        return identity

    def fail(writer: ownership.Writer, **options: Any) -> Any:
        lock = writer.path / "writer.lock"
        before = lock.stat()
        os.utime(lock, ns=(before.st_atime_ns, before.st_mtime_ns + 1))
        after = lock.stat()
        assert before.st_mtime == after.st_mtime and before.st_mtime_ns != after.st_mtime_ns
        raise failure

    monkeypatch.setattr(ownership, "provision", fixed)
    monkeypatch.setattr(Stores, "provision", fail)
    with pytest.raises(RuntimeError) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure and (project / "writer.lock").is_file()
    assert source.is_file()
    assert any("writer lock" in note.lower() for note in failure.__notes__)


def test_acquired_writer_cleanup_retains_lock_when_capture_is_unavailable(
    constructed: tuple[Path, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import initial_import

    source, project, facts = constructed
    lstat = Path.lstat
    failure = OSError("chosen missing capture")

    def unavailable(path: Path) -> os.stat_result:
        if path.name == "writer.lock":
            raise failure
        return lstat(path)

    monkeypatch.setattr(Path, "lstat", unavailable)
    with pytest.raises(OSError) as caught:
        invoke(source, project, progress=initial_import.Progress())
    assert caught.value is failure and (project / "writer.lock").is_file()
    assert source.is_file() and not (project / "source.pdf").exists()
    assert any("identity unavailable" in note for note in failure.__notes__)
    assert facts["events"] == []


def test_actual_cancellation_at_store_entry_cleans_acquired_lock_and_root(
    constructed: tuple[Path, Path, dict[str, Any]],
) -> None:
    from bookscan import initial_import

    source, project, facts = constructed
    selected = InterruptedError("chosen safe-boundary cancellation")

    def cancel() -> None:
        if (project / "writer.lock").exists():
            raise selected

    progress = initial_import.Progress()
    with pytest.raises(InterruptedError) as caught:
        invoke(source, project, progress=progress, check_cancel=cancel)
    assert caught.value is selected
    assert not project.exists() and source.is_file() and not progress.committed
    assert facts["events"] == []


def test_postcommit_selected_error_survives_writer_close_failure(
    constructed: tuple[Path, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import initial_import

    source, project, facts = constructed
    facts["fault"] = "cleanup"
    close = ownership.Writer.close

    def failed_close(writer: ownership.Writer) -> None:
        close(writer)
        raise OSError("chosen writer close failure after release")

    with monkeypatch.context() as patch:
        patch.setattr(ownership.Writer, "close", failed_close)
        progress = initial_import.Progress()
        with pytest.raises(NativeError, match="Constructed post-commit cleanup failure") as caught:
            invoke(source, project, progress=progress)
    assert progress.committed and progress.result is not None
    assert any("descriptor cleanup" in note for note in caught.value.__notes__)
    assert (project / "writer.lock").is_file() and (project / "source.pdf").is_file()
    assert finite_status.status(project)["status"] == "verified" and source.is_file()


def test_actual_busy_acquisition_preserves_other_live_writer_lock(
    constructed: tuple[Path, Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed
    acquire = ownership.Writer.acquire
    holders: list[ownership.Writer] = []

    def compete(path: Path, identity: ownership.LockIdentity) -> ownership.Writer:
        holders.append(acquire(path, identity))
        return acquire(path, identity)

    monkeypatch.setattr(ownership.Writer, "acquire", compete)
    try:
        with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
            invoke(source, project, progress=initial_import.Progress())
        holders[0].verify()
        assert (project / "writer.lock").read_bytes() == holders[0].identity.content
        assert not (project / "source.pdf").exists() and source.is_file()
    finally:
        for holder in holders:
            holder.close()
