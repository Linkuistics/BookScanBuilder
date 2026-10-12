"""Own source-first native import through a complete initial checkpoint.

The finite command still owns signal handlers, child/result delivery and exact
owned-entry cleanup. Until that lifecycle lands, this is an internal operation,
not a public create route. Failure rolls back captured completed publications and
their untouched bootstrap/source/lock. Uncaptured or changed entries retain it.
"""

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from bookscan import (
    assessment,
    baseline_state,
    checkpoints,
    dependencies,
    fontconfig,
    import_assembly,
    intake,
    native_setup,
    ownership,
    project_header,
    project_reservation,
)
from bookscan.resources import ResourceBinding
from bookscan.skew import NativeError

Cancel = Callable[[], None]


@dataclass
class Progress:
    """One invocation's outcome, available even when post-commit cleanup raises.

    This is not saved state or proof that result delivery succeeded. Reuse is
    forbidden so a preceding invocation cannot lend its commitment to another.
    """

    started: bool = False
    path: Path | None = None
    project_id: str | None = None
    committed: bool = False
    result: checkpoints.CommitResult | None = None


@dataclass(frozen=True)
class NativeImport:
    dependencies: dict[str, object]
    resource_binding: dict[str, object]
    fontconfig: dict[str, object] | None
    subjects: Iterator[assessment.AssessedPage]
    verify: Callable[[], None]


@contextmanager
def _native(
    saved: intake.Snapshot,
    directory: Path,
    *,
    cache: Path,
    configuration_file: Path | None,
    check_cancel: Cancel,
) -> Iterator[NativeImport]:
    metadata = dependencies.preflight(cache, check_cancel=check_cancel)
    renderer = Path(cast(dict[str, str], metadata["renderer"])["path"])
    helper = native_setup.load_cache(cache).binary
    graphs = cast(dict[str, dict[str, object]], metadata["linked"])
    native = {path for graph in graphs.values() for path in cast(dict[str, object], graph["files"])}
    with fontconfig.prepared_fontconfig_snapshot(
        renderer,
        directory / ".import-resources",
        configuration_file,
        check_cancel=check_cancel,
    ) as found:
        captured = ResourceBinding.capture(
            [
                *(Path(path) for path in sorted(native)),
                *(Path(item.path) for item in found.binding.files if item.resolved is not None),
            ],
            optional_files=[
                Path(item.path) for item in found.binding.files if item.resolved is None
            ],
            optional_directories=[Path(item.path) for item in found.binding.directories],
            environment=found.binding.environment(),
            check_cancel=check_cancel,
        )
        libraries = sorted(path for path in native if Path(path).name.startswith("libfontconfig."))
        if len(libraries) != 1:
            raise NativeError("Cannot identify one preflighted Fontconfig library.")
        resources = fontconfig.FontconfigBinding.guard(captured, Path(libraries[0]), found.scope)
        subjects = assessment.assess_pages(
            saved, renderer, helper, directory, resources=resources, check_cancel=check_cancel
        )
        yield NativeImport(
            metadata,
            resources.record(),
            found.record(),
            subjects,
            lambda: resources.verify(check_cancel=check_cancel),
        )


def _cleanup_lock(
    reservation: project_reservation.Reservation,
    owner: ownership.Writer,
    captured: os.stat_result | None,
    selected: BaseException,
) -> None:
    """Clean only this failed import's captured lock while ownership is still held."""
    if captured is None:
        selected.add_note("Writer lock retained; cleanup identity unavailable.")
        return

    def matches(entry: os.stat_result) -> bool:
        owner.verify()
        return (
            intake.Identity.read(entry) == intake.Identity.read(captured)
            and entry.st_mode == captured.st_mode
        )

    try:
        reservation.remove_file(ownership.LOCK_NAME, matches=matches)
    except (project_reservation.ReservationError, ownership.OwnershipError) as failure:
        selected.add_note("Writer lock retained; cleanup: " + str(failure))


def create(
    source: Path,
    project: Path,
    *,
    cache: Path,
    progress: Progress,
    configuration_file: Path | None = None,
    check_cancel: Cancel = lambda: None,
) -> checkpoints.CommitResult:
    """Reserve, snapshot, assess all occurrences and commit only complete state.

    The callback records cancellation through the existing store transaction;
    it must not raise asynchronously from a signal handler. Commitment remains
    latched before later cancellation or context cleanup. No native runtime build,
    partial acceptance, source graph copying, or source-fidelity pass occurs.
    """
    if progress.started:
        raise ValueError("Import progress already used by another invocation.")
    progress.started = True
    check_cancel()
    retained_bootstrap = False
    with project_reservation.reserve(project, check_cancel=check_cancel) as reservation:
        progress.path = reservation.path
        # A failed static-source gate cleans its owned snapshot and empty root,
        # before any native tool preflight or bootstrap/header provision.
        saved = intake.snapshot(source, reservation.path / "source.pdf", check_cancel=check_cancel)
        try:
            reservation.verify()
            with ownership.Writer.acquire(
                reservation.path, ownership.provision(reservation.path)
            ) as owner:
                captured: os.stat_result | None = None
                stores: project_header.Stores | None = None
                try:
                    captured = (owner.path / ownership.LOCK_NAME).lstat()
                    progress.project_id = "project-" + owner.identity.token
                    stores = project_header.Stores.provision(owner, check_cancel=check_cancel)
                    with _native(
                        saved,
                        owner.path,
                        cache=cache,
                        configuration_file=configuration_file,
                        check_cancel=check_cancel,
                    ) as native:
                        state = import_assembly.assemble(
                            stores,
                            saved,
                            native.subjects,
                            dependencies=native.dependencies,
                            resource_binding=native.resource_binding,
                            fontconfig=native.fontconfig,
                            check_cancel=check_cancel,
                        )
                        native.verify()
                        reservation.verify()

                        def verify(value: dict[str, object]) -> None:
                            baseline_state.restore(stores, value, check_cancel=check_cancel)

                        try:
                            result = stores.checkpoints.commit(
                                state, expected=None, verify_state=verify, check_cancel=check_cancel
                            )
                        except checkpoints.CheckpointError as error:
                            progress.committed = error.committed
                            raise
                        progress.result = result
                        progress.committed = result.committed
                        check_cancel()
                except BaseException as error:
                    if not progress.committed:
                        if stores is not None:
                            retained_bootstrap = not stores.rollback_import(error)
                        if retained_bootstrap:
                            error.add_note(
                                "Bootstrap/source/writer lock retained; safe empty rollback "
                                "was not established."
                            )
                        if not retained_bootstrap:
                            _cleanup_lock(reservation, owner, captured, error)
                    raise
            check_cancel()
        except BaseException as error:
            if not progress.committed and not retained_bootstrap:
                try:
                    reservation.remove_file(
                        "source.pdf",
                        matches=lambda entry: intake.Identity.read(entry) == saved.private_identity,
                    )
                except project_reservation.ReservationError as failure:
                    error.add_note("Source snapshot retained; cleanup: " + str(failure))
            raise
    check_cancel()
    return result
