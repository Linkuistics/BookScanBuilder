"""Verify every initial assessed-occurrence payload under saved store ownership.

The caller separately verifies the checkpoint envelope, historical toolchain and
outer discovery/review/acknowledgement records. This reader returns checked
immutable occurrence facts only. Saved consistency does not attest historical
execution, native decoder accuracy or independent complete-page fidelity.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from bookscan import (
    fontconfig_record,
    native_inventory_record,
    occurrence_record,
    placement,
    render_record,
    resource_record,
    source_record,
    triage_record,
)
from bookscan.fontconfig import ConfiguredScope
from bookscan.intake import ImportFailure
from bookscan.native_blobs import Blob, BlobError
from bookscan.occurrence_record import CoreOccurrence, OccurrenceRecordError
from bookscan.project_header import HeaderError, Stores
from bookscan.render_record import RenderFacts
from bookscan.resource_record import NamedResources
from bookscan.samples import Inventory
from bookscan.triage_record import Reason


class AssessedRecordError(OccurrenceRecordError):
    """An incomplete or inconsistent saved initial occurrence roster."""


@dataclass(frozen=True)
class AssessedOccurrence:
    core: CoreOccurrence
    render: RenderFacts
    native: Inventory
    reasons: tuple[Reason, ...]
    resources: NamedResources | None
    scope: ConfiguredScope | None


def _references(value: object) -> dict[str, Blob]:
    if type(value) is not list:
        raise AssessedRecordError("Saved native references must be an array.")
    references = [Blob.from_record(item) for item in cast(list[object], value)]
    keys = [item.sha256 for item in references]
    if keys != sorted(set(keys)):
        raise AssessedRecordError("Native references must be sorted and unique.")
    return {item.sha256: item for item in references}


def restore(
    stores: Stores,
    source_value: object,
    occurrences: object,
    baselines: object,
    native_blobs: object,
    renderer: Path,
    *,
    check_cancel: Callable[[], None] = lambda: None,
) -> tuple[AssessedOccurrence, ...]:
    """Bind all occurrence facts, source placements and exact native-byte closure.

    Caller supplies a separately verified historical renderer identity. Resume
    neither preflights that old executable nor redecodes/rerenders saved pixels.
    Named resource records retain their historical, unverified-use meaning;
    optional absent bindings stay explicit. Full checkpoint acceptance requires
    the caller's remaining envelope/toolchain/discovery/review checks too.
    """
    selected: BaseException | None = None

    def checked() -> None:
        nonlocal selected
        try:
            check_cancel()
        except BaseException as error:
            # Component readers can classify OSError/KeyError as corrupt content.
            # Preserve the operation owner's already-selected cancellation.
            selected = error
            raise

    try:
        stores.verify(check_cancel=checked)
        cores = occurrence_record.verify_cores(
            stores.images, source_value, occurrences, baselines, check_cancel=checked
        )
        saved = source_record.restore(stores.owner, source_value, check_cancel=checked)
        references = _references(native_blobs)
        consumed: set[str] = set()

        def read_blob(digest: str) -> bytes:
            checked()
            reference = references.get(digest)
            if reference is None:
                raise AssessedRecordError("Native sample lacks its saved byte reference.")
            raw = stores.native.read(reference, check_cancel=checked)
            consumed.add(digest)
            checked()
            return raw

        result: list[AssessedOccurrence] = []
        for core, value in zip(cores, cast(list[dict[str, object]], occurrences), strict=True):
            stores.verify(check_cancel=checked)
            rendered = render_record.restore(value["render"], core.page, saved.path, renderer)
            render_value = cast(dict[str, object], value["render"])
            binding = scope = None
            if "resource_binding" in render_value:
                resource_value = render_value["resource_binding"]
                binding = resource_record.restore_named(resource_value)
                scope = fontconfig_record.restore_guard(resource_value)
                if not any(
                    item.resolved is not None
                    and (item.path == str(renderer) or item.resolved == str(renderer))
                    for item in binding.files
                ):
                    raise AssessedRecordError("Named render resources lack the renderer identity.")
            native = native_inventory_record.restore(
                {key: value[key] for key in native_inventory_record.FIELDS},
                read_blob=read_blob,
                check_cancel=checked,
            )
            actual = placement.analyze(saved, core.page, check_cancel=checked)
            if native.resolution != actual:
                raise AssessedRecordError("Saved placements/concerns differ from the source page.")
            reasons = triage_record.restore(
                value["triage_reasons"], core.page, core.analysis, native, rendered.diagnostics
            )
            result.append(AssessedOccurrence(core, rendered, native, reasons, binding, scope))
        if consumed != set(references):
            raise AssessedRecordError("Native references include unreferenced bytes.")
        # Bracket all page/resource/native reads with verified saved ownership/source.
        saved.verify(check_cancel=checked)
        stores.verify(check_cancel=checked)
        return tuple(result)
    except (
        OccurrenceRecordError,
        source_record.SourceRecordError,
        render_record.RenderRecordError,
        resource_record.ResourceRecordError,
        native_inventory_record.NativeInventoryRecordError,
        triage_record.TriageRecordError,
        BlobError,
        HeaderError,
        ImportFailure,
    ) as error:
        if selected is not None:
            raise selected
        raise AssessedRecordError(
            "Saved assessed roster could not verify: " + error.message
        ) from error
