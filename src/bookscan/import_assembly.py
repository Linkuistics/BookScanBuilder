"""Publish complete assessed import assets under caller-held project ownership.

This operation returns verified, uncommitted initial state. Its caller owns the
unused reservation, source snapshot, tool preflight, live resource guards,
assessment iterator, checkpoint transaction and command signal/result lifetime.
It neither acquires ownership nor infers execution/fidelity from saved metadata.
"""

import json
from collections.abc import Callable, Iterable, Iterator

from bookscan import baseline_state, records, source_record
from bookscan.assessment import AssessedPage
from bookscan.intake import Snapshot
from bookscan.native_blobs import Blob
from bookscan.project_header import Stores


def _record(value: dict[str, object]) -> dict[str, object]:
    try:
        return records.decode(
            json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        )
    except (ValueError, TypeError, RecursionError, records.RecordError) as error:
        raise baseline_state.BaselineStateError("Invalid import producer JSON.") from error


def _payloads(subject: AssessedPage, check_cancel: Callable[[], None]) -> Iterator[bytes]:
    for sample in subject.native.images:
        check_cancel()
        if sample.packed is not None:
            yield sample.packed
        color = sample.color
        seen: set[int] = set()
        while color is not None:
            check_cancel()
            if id(color) in seen:
                raise baseline_state.BaselineStateError("Cyclic native colour metadata.")
            seen.add(id(color))
            for raw in (color.profile, color.palette):
                if raw is not None:
                    yield raw
            color = color.base


def assemble(
    stores: Stores,
    saved: Snapshot,
    subjects: Iterable[AssessedPage],
    *,
    dependencies: object,
    resource_binding: object,
    fontconfig: object = None,
    check_cancel: Callable[[], None] = lambda: None,
) -> dict[str, object]:
    """Freeze metadata, publish every occurrence's assets and verify whole state.

    The lazy iterator must supply exactly one complete assessment per source
    position, in source order, including blanks and repeated content. Retain only
    metadata/references between iterations, not a second book-sized RGB buffer.
    Cancellation/failure can leave private orphan assets, never a checkpoint;
    reservation cleanup belongs to the caller and must use its owned identities.
    """
    check_cancel()
    stores.verify(check_cancel=check_cancel)
    source = source_record.record(stores.owner, saved, check_cancel=check_cancel)
    # Producer records contain tuples; capture detached JSON arrays before
    # executing lazy native work, as on the normal durable-reader boundary.
    context = _record(
        {
            "dependencies": dependencies,
            "resource_binding": resource_binding,
            "fontconfig": fontconfig,
        }
    )
    occurrences: list[dict[str, object]] = []
    baselines: list[dict[str, object]] = []
    blobs: dict[str, Blob] = {}
    for ordinal, subject in enumerate(subjects):
        check_cancel()
        stores.verify(check_cancel=check_cancel)
        saved.verify(check_cancel=check_cancel)
        if (
            ordinal >= len(saved.pages)
            or subject.source_sha256 != saved.sha256
            or subject.page != saved.pages[ordinal]
            or subject.raster.size != subject.page.frame.pixels
            or len(subject.raster.rgb) != subject.raster.size[0] * subject.raster.size[1] * 3
        ):
            raise baseline_state.BaselineStateError("Incomplete or mismatched assessed occurrence.")
        occurrences.append(_record(subject.to_dict()))
        baselines.append(
            stores.images.publish(
                subject.raster.rgb, subject.raster.size, check_cancel=check_cancel
            ).record()
        )
        for raw in _payloads(subject, check_cancel):
            reference = stores.native.publish(raw, check_cancel=check_cancel)
            blobs[reference.sha256] = reference
    check_cancel()
    if len(occurrences) != len(saved.pages):
        raise baseline_state.BaselineStateError("Incomplete assessed occurrence roster.")
    return baseline_state.initial(
        stores,
        {
            "source": source,
            "occurrences": occurrences,
            "baselines": baselines,
            "native_blobs": [blobs[key].record() for key in sorted(blobs)],
            **context,
        },
        check_cancel=check_cancel,
    )
