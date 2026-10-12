"""Complete baseline payload meaning under caller-held store ownership.

The payload is the immutable import evidence plus replayable review facts. Every
top-level review/snapshot identity is derived by ``review_facts`` from the import
and the saved normalized requests, so a saved project can hold nothing that module
could not have produced. Historical resource metadata is consistency evidence,
never native-use or fidelity truth. Checkpoint envelopes/pointers and header
identities remain their store owners'.
"""

import copy
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from bookscan import (
    assessed_record,
    dependency_record,
    fontconfig_discovery_record,
    fontconfig_record,
    records,
    resource_record,
    review_facts,
)
from bookscan.assessment import LIMITATION
from bookscan.occurrence_record import OccurrenceRecordError
from bookscan.project_header import HeaderError, Stores
from bookscan.resource_record import NamedResources, ResourceRecordError

IMPORT_FIELDS = {
    "source",
    "occurrences",
    "baselines",
    "native_blobs",
    "dependencies",
    "resource_binding",
    "fontconfig",
}
LIMITATIONS = (
    "Historical resource/dependency consistency does not attest execution or actual file use.",
    "Helper metadata has a binary digest, not a retained binary-byte/path reference.",
    "Native metadata and baseline equality do not establish source composition fidelity.",
)


class BaselineStateError(OccurrenceRecordError):
    """Unsupported, incomplete or contradictory initial baseline payload."""


@dataclass(frozen=True)
class InitialState:
    project_id: str
    dependencies: dependency_record.DependencyFacts
    resources: NamedResources
    fontconfig: fontconfig_discovery_record.SavedDiscovery | None
    occurrences: tuple[assessed_record.AssessedOccurrence, ...]
    image_revisions: tuple[str, ...]
    review_revision: str
    snapshot_id: str
    base: review_facts.Base
    review: dict[str, list[dict[str, object]]]
    facts: review_facts.Facts
    limitations: tuple[str, ...] = LIMITATIONS


@dataclass(frozen=True)
class Transition:
    """A verified action's outcome: ``state`` is None for a durable identical retry."""

    state: dict[str, object] | None
    result: dict[str, object]
    replayed: bool
    facts: review_facts.Facts


def _json(value: object) -> bytes:
    # Validate direct inputs too: JSON encoding alone coerces tuples/nonstring keys.
    try:
        raw = json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        pending = [value]
        while pending:
            item = pending.pop()
            if type(item) is dict:
                data = cast(dict[object, object], item)
                if any(type(key) is not str for key in data):
                    raise ValueError("Non-string initial state key.")
                pending.extend(data.values())
            elif type(item) is list:
                pending.extend(cast(list[object], item))
            elif item is not None and type(item) not in (str, bool, int, float):
                raise ValueError("Non-JSON initial value.")
        records.decode(b'{"value":' + raw + b"}")
        return raw
    except (ValueError, TypeError, RecursionError, records.RecordError) as error:
        raise BaselineStateError("Invalid initial state JSON values.") from error


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(cast(dict[str, object], value)) != fields:
        raise BaselineStateError("Unsupported initial baseline fields.")
    return cast(dict[str, object], value)


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(_json({"domain": domain, "value": value})).hexdigest()


def _subset(part: NamedResources, whole: NamedResources) -> None:
    if (
        part.environment_sha256 != whole.environment_sha256
        or part.working_directory != whole.working_directory
        or part.working_directory_identity != whole.working_directory_identity
        or not set(part.files).issubset(whole.files)
        or not set(part.directories).issubset(whole.directories)
    ):
        raise BaselineStateError("Discovery and render resource contexts disagree.")


def _imports(
    stores: Stores, value: dict[str, object], check_cancel: Callable[[], None]
) -> tuple[
    dependency_record.DependencyFacts,
    NamedResources,
    fontconfig_discovery_record.SavedDiscovery | None,
    tuple[assessed_record.AssessedOccurrence, ...],
]:
    stores.verify(check_cancel=check_cancel)
    dependencies = dependency_record.restore(value["dependencies"], value["resource_binding"])
    named = resource_record.restore_named(value["resource_binding"])
    scope = fontconfig_record.restore_guard(value["resource_binding"])
    discovery = (
        None
        if value["fontconfig"] is None
        else fontconfig_discovery_record.restore(value["fontconfig"])
    )
    if (scope is None) != (discovery is None) or (
        discovery is not None and scope != discovery.scope
    ):
        raise BaselineStateError("Initial configured scope lacks matching outer discovery.")
    if discovery is not None:
        _subset(discovery.binding, named)
        cairo = dict(dependencies.linked)["pdftocairo"]
        if discovery.linked != cairo:
            raise BaselineStateError("Discovery native context differs from import dependencies.")
    check_cancel()
    occurrences = assessed_record.restore(
        stores,
        value["source"],
        value["occurrences"],
        value["baselines"],
        value["native_blobs"],
        dependencies.renderer,
        check_cancel=check_cancel,
    )
    for occurrence in occurrences:
        check_cancel()
        # One verified import resource context is frozen for every render.
        if occurrence.resources != named or occurrence.scope != scope:
            raise BaselineStateError("Occurrence render does not use the complete import context.")
        if occurrence.core.analysis.to_dict()["leptonica"] != (
            "leptonica-" + dependencies.helper.inputs.leptonica.version
        ):
            raise BaselineStateError("Occurrence assessment differs from the saved helper library.")
    stores.verify(check_cancel=check_cancel)
    return dependencies, named, discovery, occurrences


def _initial_snapshot(
    project_id: str,
    value: dict[str, object],
) -> tuple[list[str], dict[str, object]]:
    """Image revisions and the review-free export snapshot every review derives from."""
    pages = cast(list[dict[str, object]], value["occurrences"])
    image_revisions = [
        _digest(
            "BookScanBuilderImage-v1",
            {
                "rgb_sha256": page["rgb_sha256"],
                "geometry": page["geometry"],
            },
        )
        for page in pages
    ]
    snapshot: dict[str, object] = {
        "project_id": project_id,
        "source_sha256": pages[0]["source_sha256"],
        "toolchain": copy.deepcopy(value["dependencies"]),
        "limitation": LIMITATION,
        "pages": [
            {
                "id": page["id"],
                "source_pdf_page": page["source_pdf_page"],
                "image_revision": revision,
                "image_sha256": page["rgb_sha256"],
                "geometry": copy.deepcopy(page["geometry"]),
                "analysis": copy.deepcopy(page["analysis"]),
                "triage_reasons": copy.deepcopy(page["triage_reasons"]),
                "retention": "baseline-retained/unresolved",
                "inspections": [],
                "half": None,
                "group": None,
                "run": None,
                "side": "unknown",
                "anchors": [],
                "placement": None,
            }
            for page, revision in zip(pages, image_revisions, strict=True)
        ],
    }
    return image_revisions, snapshot


def _replayed(base: review_facts.Base, review: object) -> review_facts.Facts:
    try:
        return review_facts.replay(base, review)
    except review_facts.ReviewError as error:
        raise BaselineStateError("Saved review facts could not verify: " + error.message) from error


def initial(
    stores: Stores,
    evidence: object,
    *,
    check_cancel: Callable[[], None] = lambda: None,
) -> dict[str, object]:
    """Build a detached initial record only after all evidence/assets verify.

    This creates no checkpoint or public successful import by itself. The owner
    commits it through Checkpoints with restore as its required state verifier.
    """
    selected: BaseException | None = None

    def checked() -> None:
        nonlocal selected
        try:
            check_cancel()
        except BaseException as error:
            selected = error
            raise

    try:
        checked()
        _json(evidence)
        value = copy.deepcopy(_object(evidence, IMPORT_FIELDS))
        _imports(stores, value, checked)
        project_id = "project-" + stores.header.lock.token
        revisions, initial_snapshot = _initial_snapshot(project_id, value)
        review = review_facts.initial_review()
        base = review_facts.Base(project_id, value, initial_snapshot)
        facts = _replayed(base, review)
        checked()
        return {
            "format": "BookScanBuilderInitialBaseline",
            "version": 1,
            "project_id": project_id,
            **value,
            "image_revisions": revisions,
            "review_revision": facts.review_revision,
            "snapshot": facts.snapshot,
            "snapshot_id": facts.snapshot_id,
            "review": review,
        }
    except (OccurrenceRecordError, ResourceRecordError, HeaderError) as error:
        if selected is not None:
            raise selected
        raise BaselineStateError("Initial baseline could not verify: " + error.message) from error


def restore(
    stores: Stores,
    record: object,
    *,
    check_cancel: Callable[[], None] = lambda: None,
) -> InitialState:
    """Verify initial payload and identities without rebuilding or original I/O.

    The owner verifies every checkpoint predecessor through this same boundary.
    Saved review facts are replayed from their normalized requests, and the
    top-level review/snapshot identities must equal that derivation. Retry or
    acknowledgement bookkeeping never substitutes for snapshot identity.
    """
    selected: BaseException | None = None

    def checked() -> None:
        nonlocal selected
        try:
            check_cancel()
        except BaseException as error:
            selected = error
            raise

    try:
        checked()
        _json(record)
        data = _object(
            record,
            IMPORT_FIELDS
            | {
                "format",
                "version",
                "project_id",
                "image_revisions",
                "review_revision",
                "snapshot",
                "snapshot_id",
                "review",
            },
        )
        project_id = "project-" + stores.header.lock.token
        if (
            data["format"] != "BookScanBuilderInitialBaseline"
            or type(data["version"]) is not int
            or data["version"] != 1
            or data["project_id"] != project_id
        ):
            raise BaselineStateError("Unsupported initial format/version or foreign project.")
        value = {key: data[key] for key in IMPORT_FIELDS}
        dependencies, named, discovery, occurrences = _imports(stores, value, checked)
        revisions, initial_snapshot = _initial_snapshot(project_id, value)
        base = review_facts.Base(project_id, copy.deepcopy(value), initial_snapshot)
        facts = _replayed(base, data["review"])
        if (
            data["image_revisions"] != revisions
            or data["review_revision"] != facts.review_revision
            or _json(data["snapshot"]) != _json(facts.snapshot)
            or data["snapshot_id"] != facts.snapshot_id
        ):
            raise BaselineStateError("Image/review/export snapshot identities disagree.")
        checked()
        stores.verify(check_cancel=checked)
        return InitialState(
            project_id,
            dependencies,
            named,
            discovery,
            occurrences,
            tuple(revisions),
            facts.review_revision,
            facts.snapshot_id,
            base,
            copy.deepcopy(cast(dict[str, list[dict[str, object]]], data["review"])),
            facts,
        )
    except (OccurrenceRecordError, ResourceRecordError, HeaderError) as error:
        if selected is not None:
            raise selected
        raise BaselineStateError(
            "Saved initial baseline could not verify: " + error.message
        ) from error


def act(
    stores: Stores,
    record: object,
    action: review_facts.Action,
    *,
    checkpoint_revision: int,
    integrity: Callable[[], None] = lambda: None,
    check_cancel: Callable[[], None] = lambda: None,
) -> Transition:
    """Verify the saved state, then apply one action in replay-before-currency order.

    ``checkpoint_revision`` is the revision the caller's commit will assign. The
    returned state is detached and not yet verified or committed: the owner commits
    it through Checkpoints with restore as the verifier. A durable identical retry
    returns the original result with ``state`` None. ``ReviewError``/``ReceiptError``
    for stale, tampered, out-of-domain or reused requests propagate unchanged and
    leave the saved record untouched.
    """
    current = restore(stores, record, check_cancel=check_cancel)
    check_cancel()
    acted = review_facts.act(
        current.base,
        current.review,
        action,
        checkpoint_revision=checkpoint_revision,
        integrity=integrity,
    )
    if acted.replayed:
        return Transition(None, acted.result, True, acted.facts)
    state = copy.deepcopy(cast(dict[str, object], record))
    state["review"] = acted.review
    state["review_revision"] = acted.facts.review_revision
    state["snapshot"] = copy.deepcopy(acted.facts.snapshot)
    state["snapshot_id"] = acted.facts.snapshot_id
    check_cancel()
    return Transition(state, acted.result, False, acted.facts)
