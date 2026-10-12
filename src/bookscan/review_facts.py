"""Replayable review facts: Q1 dispositions, scoped inspection, snapshot acknowledgement, retries.

Pure data over a detached initial snapshot: no store, writer ownership, packet file
or checkpoint. One derivation serves a new action and the verification of saved
review state, so a saved project can contain nothing this module would not have
produced. Receipts are identity evidence; nothing here treats opening a file as
inspection, and acknowledgement never changes the review revision or snapshot.

An action is identified by a request ID (a finite receipt ID, or a browser request
ID) plus the displayed identity it was issued against; the finite receipt adapter
and a future browser envelope both build the same ``Displayed``.
"""

import copy
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, Self, cast

from bookscan import records
from bookscan.packet_receipts import Receipt, ReceiptError

# Q1 reason domains (spec "Integrated public protocol repairs"); reject dismisses only
# the skew suggestion and never clears any other limitation.
REASON_DECISIONS: Mapping[str, tuple[str, ...]] = {
    "skew-nonzero": ("reject", "retain-unresolved"),
    "assessment-unavailable": ("retain-unresolved",),
    "orientation-unverified": ("retain-unresolved",),
    "import-fidelity": ("retain-unresolved",),
    "extent-change": ("retain-unresolved",),
    "skew-range-edge": ("retain-unresolved",),
    "decoder-warning": ("retain-unresolved",),
    "canvas-warning": ("retain-unresolved",),
}
SCOPES = ("full", "native", "source-native")
REVIEW_FIELDS = {"dispositions", "inspections", "acknowledgements", "retries"}
SUPPRESSED = "suggestion-rejected"

type Kind = Literal["disposition", "inspected", "acknowledge"]
OPERATIONS: Mapping[Kind, str] = {
    "disposition": "baseline.disposition",
    "inspected": "baseline.inspected",
    "acknowledge": "baseline.acknowledge",
}
_LISTS: Mapping[Kind, str] = {
    "disposition": "dispositions",
    "inspected": "inspections",
    "acknowledge": "acknowledgements",
}


@dataclass
class ReviewError(Exception):
    """INVALID_ARGUMENT (2), STALE_ACTION (6) or INVALID_PROJECT (3); never mutates."""

    code: str
    message: str
    exit_code: int
    command: str | None = None
    reason: str | None = None
    allowed: tuple[str, ...] = ()

    @property
    def remediation(self) -> str:
        if self.code == "INVALID_ARGUMENT":
            return self.command or "Use bookscan baseline --help for the valid syntax."
        if self.code == "STALE_ACTION":
            return (
                "Verify current status and obtain a newly issued view or summary with "
                "bookscan baseline views PROJECT --page ID --output NEW or "
                "bookscan baseline status PROJECT --output NEW."
            )
        return (
            "Use the compatible BookScanBuilder review-records-v1 reader with bookscan "
            "baseline status PROJECT; for damaged saved content use bookscan baseline "
            "create PDF --workdir NEW with an intact supported input. Fresh import loses "
            "review facts. Without intact input or a verifiable saved state no recovery "
            "is available."
        )

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def _corrupt(message: str) -> ReviewError:
    return ReviewError("INVALID_PROJECT", "Saved review facts: " + message, 3)


def _argument(
    message: str,
    command: str | None = None,
    reason: str | None = None,
    allowed: tuple[str, ...] = (),
) -> ReviewError:
    return ReviewError("INVALID_ARGUMENT", message, 2, command, reason, allowed)


def disposition_command(reason: str, decision: str) -> str:
    return (
        "bookscan baseline disposition PROJECT --receipt FILE "
        f"--reason {reason} --decision {decision} --note TEXT"
    )


def _json(value: object) -> bytes:
    try:
        raw = json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        records.decode(b'{"value":' + raw + b"}")
        return raw
    except (TypeError, ValueError, RecursionError, records.RecordError) as error:
        raise _corrupt("values are not strict UTF-8 JSON.") from error


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(_json({"domain": domain, "value": value})).hexdigest()


@dataclass(frozen=True)
class Displayed:
    """The identity an action was issued against; ``request_id`` is single-use."""

    request_id: str
    project_id: str
    review_revision: str
    snapshot_id: str
    view: str
    occurrence_id: str | None = None
    image_revision: str | None = None
    regions: tuple[str, ...] = ()

    @classmethod
    def from_receipt(cls, receipt: Receipt) -> Self:
        coverage, identity = receipt.coverage, receipt.identity
        return cls(
            receipt.receipt_id,
            identity.project_id,
            identity.review_revision,
            identity.snapshot_id,
            coverage.view,
            coverage.occurrence_id,
            coverage.image_revision,
            coverage.regions,
        )

    def record(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "review_revision": self.review_revision,
            "snapshot_id": self.snapshot_id,
            "view": self.view,
            "occurrence_id": self.occurrence_id,
            "image_revision": self.image_revision,
            "regions": list(self.regions),
        }


@dataclass(frozen=True)
class Disposition:
    displayed: Displayed
    reason: str
    decision: str
    note: str
    kind: Kind = "disposition"


@dataclass(frozen=True)
class Inspection:
    displayed: Displayed
    scope: str
    viewer: str
    scale: str
    note: str
    kind: Kind = "inspected"


@dataclass(frozen=True)
class Acknowledgement:
    displayed: Displayed
    note: str
    pages: tuple[str, ...] | None  # None is --all; otherwise a named selection
    kind: Kind = "acknowledge"


type Action = Disposition | Inspection | Acknowledgement


def _text(value: object, what: str) -> str:
    if type(value) is not str or not value.strip():
        raise _argument(f"{what} must be nonblank text.")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise _argument(f"{what} is not valid UTF-8 text.") from error
    return value


def check_values(action: Action) -> None:
    """Static argument checks that need no project: usable at invocation, before any read."""
    if isinstance(action, Disposition):
        allowed = REASON_DECISIONS.get(action.reason)
        if allowed is None:
            raise _argument(
                f"Unknown reason {action.reason!r}; valid reasons are "
                + ", ".join(REASON_DECISIONS)
                + ".",
                command=disposition_command("REASON", "retain-unresolved"),
                reason=action.reason,
            )
        if action.decision not in allowed:
            raise _argument(
                f"Decision {action.decision!r} is not allowed for reason {action.reason}; "
                "allowed: " + ", ".join(allowed) + ".",
                command=disposition_command(action.reason, allowed[-1]),
                reason=action.reason,
                allowed=allowed,
            )
        _text(action.note, "Note")
    elif isinstance(action, Inspection):
        if action.scope not in SCOPES:
            raise _argument("Inspection scope must be one of " + ", ".join(SCOPES) + ".")
        _text(action.viewer, "Viewer")
        _text(action.scale, "Scale")
        _text(action.note, "Note")
    else:
        _text(action.note, "Note")
        if action.pages is not None and not action.pages:
            raise _argument("Name at least one --page ID, or use --all.")


def _values(action: Action) -> dict[str, object]:
    if isinstance(action, Disposition):
        return {"reason": action.reason, "decision": action.decision, "note": action.note}
    if isinstance(action, Inspection):
        return {
            "scope": action.scope,
            "viewer": action.viewer,
            "scale": action.scale,
            "note": action.note,
        }
    return {
        "all": action.pages is None,
        "pages": [] if action.pages is None else sorted(set(action.pages)),
        "note": action.note,
    }


def request_record(action: Action) -> dict[str, object]:
    """The normalized request identity: operation, ID, displayed identity, values."""
    return {
        "operation": OPERATIONS[action.kind],
        "request_id": action.displayed.request_id,
        "displayed": action.displayed.record(),
        "values": _values(action),
    }


def request_digest(action: Action) -> str:
    return _digest("BookScanBuilderActionRequest-v1", request_record(action))


def _object(value: object, fields: set[str], what: str) -> dict[str, object]:
    if type(value) is not dict or set(cast(dict[str, object], value)) != fields:
        raise _corrupt(f"unsupported {what} fields.")
    return cast(dict[str, object], value)


def _str(value: object, what: str) -> str:
    if type(value) is not str:
        raise _corrupt(f"{what} is not text.")
    return value


def _opt_str(value: object, what: str) -> str | None:
    return None if value is None else _str(value, what)


def _strings(value: object, what: str) -> tuple[str, ...]:
    if type(value) is not list or any(type(v) is not str for v in cast(list[object], value)):
        raise _corrupt(f"{what} is not a text array.")
    return tuple(cast(list[str], value))


def _parse_request(value: object) -> Action:
    data = _object(value, {"operation", "request_id", "displayed", "values"}, "request")
    shown = _object(
        data["displayed"],
        {
            "project_id",
            "review_revision",
            "snapshot_id",
            "view",
            "occurrence_id",
            "image_revision",
            "regions",
        },
        "displayed identity",
    )
    displayed = Displayed(
        _str(data["request_id"], "Request ID"),
        _str(shown["project_id"], "Project ID"),
        _str(shown["review_revision"], "Review revision"),
        _str(shown["snapshot_id"], "Snapshot ID"),
        _str(shown["view"], "View"),
        _opt_str(shown["occurrence_id"], "Occurrence ID"),
        _opt_str(shown["image_revision"], "Image revision"),
        _strings(shown["regions"], "Regions"),
    )
    operation, values = data["operation"], data["values"]
    if operation == OPERATIONS["disposition"]:
        v = _object(values, {"reason", "decision", "note"}, "disposition values")
        return Disposition(
            displayed,
            _str(v["reason"], "Reason"),
            _str(v["decision"], "Decision"),
            _str(v["note"], "Note"),
        )
    if operation == OPERATIONS["inspected"]:
        v = _object(values, {"scope", "viewer", "scale", "note"}, "inspection values")
        return Inspection(
            displayed,
            _str(v["scope"], "Scope"),
            _str(v["viewer"], "Viewer"),
            _str(v["scale"], "Scale"),
            _str(v["note"], "Note"),
        )
    if operation == OPERATIONS["acknowledge"]:
        v = _object(values, {"all", "pages", "note"}, "acknowledgement values")
        if type(v["all"]) is not bool:
            raise _corrupt("acknowledgement scope flag is not boolean.")
        pages = _strings(v["pages"], "Pages")
        if v["all"] == bool(pages):
            raise _corrupt("acknowledgement names both or neither of all and pages.")
        return Acknowledgement(displayed, _str(v["note"], "Note"), None if v["all"] else pages)
    raise _corrupt("unknown saved operation.")


@dataclass(frozen=True)
class Base:
    """Initial immutable facts the review is derived from.

    ``imported`` is the value hashed into the review revision; ``snapshot`` is the
    initial export snapshot with no review facts. Both are retained detached.
    """

    project_id: str
    imported: dict[str, object]
    snapshot: dict[str, object]

    def pages(self) -> list[dict[str, object]]:
        return cast(list[dict[str, object]], self.snapshot["pages"])


@dataclass(frozen=True)
class Facts:
    review_revision: str
    snapshot: dict[str, object]
    snapshot_id: str
    page_ids: tuple[str, ...]
    unresolved: Mapping[str, tuple[str, ...]]
    inspections: tuple[dict[str, object], ...]
    acknowledgements: tuple[dict[str, object], ...]


def _derive(base: Base, review: Mapping[str, list[dict[str, object]]]) -> Facts:
    dispositions, inspections = review["dispositions"], review["inspections"]
    revision = _digest(
        "BookScanBuilderReview-v1",
        {
            "project_id": base.project_id,
            "import": base.imported,
            "dispositions": dispositions,
            "inspections": inspections,
        },
    )
    latest: dict[tuple[str, str], dict[str, object]] = {}
    for record in dispositions:
        latest[(cast(str, record["occurrence_id"]), cast(str, record["reason"]))] = record
    snapshot = copy.deepcopy(base.snapshot)
    unresolved: dict[str, tuple[str, ...]] = {}
    for page in cast(list[dict[str, object]], snapshot["pages"]):
        identifier = cast(str, page["id"])
        page["inspections"] = [
            {
                key: record[key]
                for key in ("image_revision", "scope", "regions", "viewer", "scale", "note")
            }
            for record in inspections
            if record["occurrence_id"] == identifier
        ]
        remaining: list[str] = []
        for reason in cast(list[dict[str, object]], page["triage_reasons"]):
            decided = latest.get((identifier, cast(str, reason["id"])))
            if decided is not None:
                reason["decision"] = {"decision": decided["decision"], "note": decided["note"]}
                if decided["decision"] == "reject":
                    reason["disposition"] = SUPPRESSED
            if reason["disposition"] != SUPPRESSED:
                remaining.append(cast(str, reason["id"]))
        unresolved[identifier] = tuple(remaining)
    return Facts(
        revision,
        snapshot,
        _digest("BookScanBuilderExportSnapshot-v1", snapshot),
        tuple(cast(str, page["id"]) for page in base.pages()),
        unresolved,
        tuple(copy.deepcopy(inspections)),
        tuple(copy.deepcopy(review["acknowledgements"])),
    )


def _currency(base: Base, facts: Facts, action: Action) -> None:
    shown = action.displayed
    if shown.project_id != base.project_id:
        raise ReceiptError("Receipt names a different project.", "foreign")
    if shown.review_revision != facts.review_revision or shown.snapshot_id != facts.snapshot_id:
        raise ReviewError(
            "STALE_ACTION",
            "The displayed review revision is no longer current; review facts changed "
            "after this view was issued.",
            6,
        )
    if shown.occurrence_id is not None:
        page = next((p for p in base.pages() if p["id"] == shown.occurrence_id), None)
        if page is None:
            raise _argument(f"Unknown occurrence {shown.occurrence_id}.")
        if page["image_revision"] != shown.image_revision:
            raise ReviewError(
                "STALE_ACTION", "The displayed image revision is no longer current.", 6
            )


def _wrong_view(action: Action) -> ReceiptError | None:
    view = action.displayed.view
    if isinstance(action, Acknowledgement):
        if view != "summary":
            return ReceiptError(
                f"Acknowledgement needs a summary receipt, not a {view} view receipt.",
                "wrong-view",
            )
    elif view == "summary" or action.displayed.occurrence_id is None:
        return ReceiptError(
            "This action needs a page view receipt, not a summary receipt.", "wrong-view"
        )
    return None


def _record(base: Base, facts: Facts, action: Action, revision: int) -> dict[str, object]:
    """Domain checks and the saved record; every failure is an argument error."""
    wrong = _wrong_view(action)
    if wrong is not None:
        raise wrong
    shown = action.displayed
    head: dict[str, object] = {"checkpoint_revision": revision, "request_id": shown.request_id}
    if isinstance(action, Disposition):
        present = {
            cast(str, r["id"])
            for p in base.pages()
            if p["id"] == shown.occurrence_id
            for r in cast(list[dict[str, object]], p["triage_reasons"])
        }
        if action.reason not in present:
            raise _argument(
                f"Occurrence {shown.occurrence_id} has no reason {action.reason!r}; "
                "its reasons are " + ", ".join(sorted(present)) + ".",
                command=disposition_command(sorted(present)[0], "retain-unresolved"),
                reason=action.reason,
            )
        return {
            **head,
            "occurrence_id": shown.occurrence_id,
            "image_revision": shown.image_revision,
            "reason": action.reason,
            "decision": action.decision,
            "note": action.note,
        }
    if isinstance(action, Inspection):
        if action.scope != shown.view:
            raise _argument(
                f"Scope {action.scope!r} does not match this receipt's {shown.view} view; "
                f"record --scope {shown.view}."
            )
        return {
            **head,
            "occurrence_id": shown.occurrence_id,
            "image_revision": shown.image_revision,
            "scope": action.scope,
            "regions": list(shown.regions),
            "viewer": action.viewer,
            "scale": action.scale,
            "note": action.note,
        }
    known = set(facts.page_ids)
    if action.pages is not None:
        unknown = sorted(set(action.pages) - known)
        if unknown:
            raise _argument("Unknown occurrence(s): " + ", ".join(unknown) + ".")
    selected = [i for i in facts.page_ids if action.pages is None or i in set(action.pages)]
    return {
        **head,
        "review_revision": facts.review_revision,
        "snapshot_id": facts.snapshot_id,
        "all": action.pages is None,
        "pages": [{"id": i, "reasons": list(facts.unresolved[i])} for i in selected],
        "limitation": base.snapshot["limitation"],
        "note": action.note,
    }


def effective_acknowledgement(facts: Facts) -> dict[str, object] | None:
    """Union of acknowledgements bound to exactly this review revision and snapshot."""
    covered: dict[str, set[str]] = {}
    scopes: list[dict[str, object]] = []
    for record in facts.acknowledgements:
        # The review revision binds the snapshot: an identical re-record changes it too.
        if record["review_revision"] != facts.review_revision:
            continue
        pages = cast(list[dict[str, object]], record["pages"])
        for page in pages:
            covered.setdefault(cast(str, page["id"]), set()).update(
                cast(list[str], page["reasons"])
            )
        scopes.append(
            {
                "request_id": record["request_id"],
                "checkpoint_revision": record["checkpoint_revision"],
                "all": record["all"],
                "ids": [page["id"] for page in pages],
                "note": record["note"],
            }
        )
    if not scopes:
        return None
    ids = [i for i in facts.page_ids if i in covered and set(facts.unresolved[i]) <= covered[i]]
    missing = [i for i in facts.page_ids if i not in set(ids)]
    return {
        "review_revision": facts.review_revision,
        "snapshot_id": facts.snapshot_id,
        "complete": not missing,
        "ids": ids,
        "missing_ids": missing,
        "limitation": facts.snapshot["limitation"],
        "scopes": scopes,
    }


def inspection_scope(facts: Facts) -> list[dict[str, object]]:
    """Inspection recorded per page, separate from unresolved coverage."""
    result: list[dict[str, object]] = []
    for identifier in facts.page_ids:
        mine = [r for r in facts.inspections if r["occurrence_id"] == identifier]

        def union(scope: str, mine: list[dict[str, object]] = mine) -> list[str]:
            return sorted(
                {
                    region
                    for r in mine
                    if r["scope"] == scope
                    for region in cast(list[str], r["regions"])
                }
            )

        result.append(
            {
                "id": identifier,
                "inspected": bool(mine),
                "full": any(r["scope"] == "full" for r in mine),
                "native_regions": union("native"),
                "source_native_regions": union("source-native"),
            }
        )
    return result


def unresolved_digest(facts: Facts) -> str:
    """Digest of the complete unresolved roster a summary receipt displays."""
    return _digest(
        "BookScanBuilderUnresolvedRoster-v1",
        {
            "limitation": facts.snapshot["limitation"],
            "pages": [{"id": i, "reasons": list(facts.unresolved[i])} for i in facts.page_ids],
        },
    )


def inspection_digest(facts: Facts) -> str:
    """Digest of effective decisions and recorded inspections a summary displays."""
    pages = cast(list[dict[str, object]], facts.snapshot["pages"])
    return _digest(
        "BookScanBuilderInspectionDisposition-v1",
        [
            {
                "id": page["id"],
                "decisions": [
                    {"reason": r["id"], "decision": r["decision"]}
                    for r in cast(list[dict[str, object]], page["triage_reasons"])
                    if "decision" in r
                ],
                "inspections": page["inspections"],
            }
            for page in pages
        ],
    )


def _empty() -> dict[str, list[dict[str, object]]]:
    return {name: [] for name in sorted(REVIEW_FIELDS)}


def _shape(review: object) -> dict[str, list[dict[str, object]]]:
    data = _object(review, REVIEW_FIELDS, "review")
    result: dict[str, list[dict[str, object]]] = {}
    for name, items in data.items():
        if type(items) is not list or any(type(i) is not dict for i in cast(list[object], items)):
            raise _corrupt(f"{name} is not an array of records.")
        result[name] = cast(list[dict[str, object]], items)
    return result


def _result(
    action: Action, record: dict[str, object], facts: Facts, revision: int
) -> dict[str, object]:
    detail: dict[str, object]
    if isinstance(action, Disposition):
        detail = {
            "reason": action.reason,
            "decision": action.decision,
            "unresolved_reasons": list(facts.unresolved[cast(str, record["occurrence_id"])]),
        }
        affected = [record["occurrence_id"]]
    elif isinstance(action, Inspection):
        detail = {
            "scope": record["scope"],
            "regions": record["regions"],
            "viewer": action.viewer,
            "scale": action.scale,
        }
        affected = [record["occurrence_id"]]
    else:
        detail = {"acknowledgement": effective_acknowledgement(facts)}
        affected = [page["id"] for page in cast(list[dict[str, object]], record["pages"])]
    return {
        "operation": OPERATIONS[action.kind],
        "status": "acknowledged" if action.kind == "acknowledge" else "recorded",
        "checkpoint_revision": revision,
        "review_revision": facts.review_revision,
        "snapshot_id": facts.snapshot_id,
        "affected_ids": affected,
        "detail": detail,
    }


def _apply(
    base: Base,
    review: dict[str, list[dict[str, object]]],
    action: Action,
    record: dict[str, object],
    revision: int,
) -> tuple[dict[str, list[dict[str, object]]], Facts, dict[str, object]]:
    after = {name: list(items) for name, items in review.items()}
    after[_LISTS[action.kind]].append(record)
    facts = _derive(base, after)
    result = _result(action, record, facts, revision)
    after["retries"].append(
        {
            "request": request_record(action),
            "request_sha256": request_digest(action),
            "result": result,
        }
    )
    return after, facts, result


def replay(base: Base, review: object) -> Facts:
    """Re-derive the saved history from its normalized requests and require equality.

    Each retry's request is re-run through the same currency and domain rules at
    the checkpoint revision of its record; the rebuilt lists must then equal the
    saved ones exactly. Raises INVALID_PROJECT/3 for any state this module could
    not have produced: out-of-domain decision, stale or foreign displayed identity,
    changed record/result/digest, reused request ID, orphan record or list order.
    """
    saved = _shape(review)
    retries = saved["retries"]
    revisions: list[int] = []
    for name in _LISTS.values():
        for item in saved[name]:
            revision = item.get("checkpoint_revision")
            if type(revision) is not int or revision < 2:
                raise _corrupt(f"{name} record lacks a valid checkpoint revision.")
            revisions.append(revision)
    revisions.sort()
    if len(set(revisions)) != len(revisions):
        raise _corrupt("two review records share one checkpoint revision.")
    if len(revisions) != len(retries):
        raise _corrupt("every committed action needs exactly one retry record.")
    running = _empty()
    facts = _derive(base, running)
    seen: set[str] = set()
    for revision, retry in zip(revisions, retries, strict=True):
        data = _object(retry, {"request", "request_sha256", "result"}, "retry")
        action = _parse_request(data["request"])
        if action.displayed.request_id in seen:
            raise _corrupt("a request ID was committed twice.")
        seen.add(action.displayed.request_id)
        try:
            check_values(action)
            _currency(base, facts, action)
            record = _record(base, facts, action, revision)
        except (ReviewError, ReceiptError) as error:
            raise _corrupt("a committed action is not derivable: " + str(error)) from error
        running, facts, _ = _apply(base, running, action, record, revision)
    if running != saved:
        raise _corrupt("saved review differs from its derivation.")
    return facts


@dataclass(frozen=True)
class Acted:
    review: dict[str, list[dict[str, object]]]
    result: dict[str, object]
    replayed: bool
    facts: Facts


def initial_review() -> dict[str, list[dict[str, object]]]:
    return _empty()


def _prior(saved: dict[str, list[dict[str, object]]], action: Action, facts: Facts) -> Acted | None:
    """Durable retry lookup: the original result for an identical request, else refuse."""
    digest = request_digest(action)
    for retry in saved["retries"]:
        request = cast(dict[str, object], retry["request"])
        if request["request_id"] != action.displayed.request_id:
            continue
        if retry["request_sha256"] != digest:
            raise ReceiptError(
                "This receipt was already used for a different action.", "receipt-used"
            )
        result = cast(dict[str, object], retry["result"])
        return Acted(copy.deepcopy(saved), copy.deepcopy(result), True, facts)
    return None


def _check_order(saved: dict[str, list[dict[str, object]]], checkpoint_revision: int) -> None:
    newest = max(
        (cast(int, r["checkpoint_revision"]) for name in _LISTS.values() for r in saved[name]),
        default=1,
    )
    if checkpoint_revision <= newest:
        raise _corrupt("a new checkpoint revision must exceed every recorded action.")


def act(
    base: Base,
    review: object,
    action: Action,
    *,
    checkpoint_revision: int,
    integrity: Callable[[], None] = lambda: None,
) -> Acted:
    """Replay-verify, then durable retry, currency, external integrity, domain, commit data.

    The returned review replaces the saved one in the next checkpoint. A replay
    returns the original result with the review unchanged and records nothing;
    ``integrity`` (external packet-file verification) is never called for it.
    """
    check_values(action)
    facts = replay(base, review)
    saved = _shape(review)
    prior = _prior(saved, action, facts)
    if prior is not None:
        return prior
    _check_order(saved, checkpoint_revision)
    _currency(base, facts, action)
    integrity()
    record = _record(base, facts, action, checkpoint_revision)
    after, derived, result = _apply(base, saved, action, record, checkpoint_revision)
    return Acted(after, result, False, derived)
