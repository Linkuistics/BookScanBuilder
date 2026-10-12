"""Q1 dispositions, scoped inspection, snapshot acknowledgement, replay and verification."""

import copy
import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from typing import Any, cast

import pytest

from bookscan.packet_receipts import (
    Coverage,
    Identity,
    ReceiptError,
    issue,
)
from bookscan.review_facts import (
    REASON_DECISIONS,
    Acknowledgement,
    Acted,
    Action,
    Base,
    Displayed,
    Disposition,
    Inspection,
    ReviewError,
    act,
    check_values,
    effective_acknowledgement,
    initial_review,
    inspection_digest,
    inspection_scope,
    replay,
    request_digest,
    unresolved_digest,
)
from bookscan.triage_record import Reason

type Json = dict[str, Any]

PROJECT = "project-0123"
IMG = {
    name: hashlib.sha256(name.encode()).hexdigest()
    for name in ("occ-000001", "occ-000002", "occ-000003")
}
LIMITATION = "Within-page geometry unverified."
REASONS = {
    "occ-000001": ("orientation-unverified", "skew-nonzero", "import-fidelity"),
    "occ-000002": ("orientation-unverified",),
    "occ-000003": ("orientation-unverified", "extent-change"),
}


def make_base() -> Base:
    pages: list[Json] = []
    for number, (occurrence, reasons) in enumerate(REASONS.items(), start=1):
        pages.append(
            {
                "id": occurrence,
                "source_pdf_page": number,
                "image_revision": IMG[occurrence],
                "inspections": [],
                "triage_reasons": [
                    {
                        "id": reason,
                        "details": [f"{reason} detail"],
                        "allowed_decisions": list(REASON_DECISIONS[reason]),
                        "disposition": "baseline-retained/unresolved",
                    }
                    for reason in reasons
                ],
            }
        )
    snapshot: Json = {
        "project_id": PROJECT,
        "source_sha256": "a" * 64,
        "limitation": LIMITATION,
        "pages": pages,
    }
    return Base(PROJECT, {"occurrences": [p["id"] for p in pages], "tool": "x"}, snapshot)


BASE = make_base()


def shown(
    review: object, request: str, *, view: str = "full", occ: str = "occ-000001"
) -> Displayed:
    facts = replay(BASE, review)
    if view == "summary":
        return Displayed(request, PROJECT, facts.review_revision, facts.snapshot_id, "summary")
    regions = ("native-001", "native-002") if view == "native" else ()
    return Displayed(
        request, PROJECT, facts.review_revision, facts.snapshot_id, view, occ, IMG[occ], regions
    )


def go(review: dict[str, list[dict[str, object]]], action: Action, revision: int) -> Acted:
    return act(BASE, review, action, checkpoint_revision=revision)


def disposition(
    review: object, request: str, reason: str, decision: str, *, occ: str = "occ-000001"
) -> Disposition:
    return Disposition(shown(review, request, occ=occ), reason, decision, f"note {request}")


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode()


def test_reason_domains_equal_triage_reason_domains() -> None:
    for reason, decisions in REASON_DECISIONS.items():
        assert Reason(reason, ()).allowed_decisions == decisions


def test_initial_identities_match_independently_computed_digests() -> None:
    facts = replay(BASE, initial_review())
    expected_review = hashlib.sha256(
        canonical(
            {
                "domain": "BookScanBuilderReview-v1",
                "value": {
                    "project_id": PROJECT,
                    "import": BASE.imported,
                    "dispositions": [],
                    "inspections": [],
                },
            }
        )
    ).hexdigest()
    expected_snapshot = hashlib.sha256(
        canonical({"domain": "BookScanBuilderExportSnapshot-v1", "value": BASE.snapshot})
    ).hexdigest()
    assert facts.review_revision == expected_review
    assert facts.snapshot_id == expected_snapshot
    assert facts.snapshot == BASE.snapshot
    assert effective_acknowledgement(facts) is None


def test_reject_dismisses_only_the_suggestion_and_keeps_every_other_limitation() -> None:
    review = initial_review()
    before = replay(BASE, review)
    outcome = go(review, disposition(review, "r1", "skew-nonzero", "reject"), 2)
    facts = outcome.facts
    assert facts.unresolved["occ-000001"] == ("orientation-unverified", "import-fidelity")
    assert facts.unresolved["occ-000002"] == before.unresolved["occ-000002"]
    page = cast(list[Json], facts.snapshot["pages"])[0]
    skew = page["triage_reasons"][1]
    assert skew["disposition"] == "suggestion-rejected"
    assert skew["decision"] == {"decision": "reject", "note": "note r1"}
    assert page["triage_reasons"][2]["disposition"] == "baseline-retained/unresolved"
    assert "decision" not in page["triage_reasons"][0]
    assert facts.review_revision != before.review_revision
    assert facts.snapshot_id != before.snapshot_id
    assert outcome.result["status"] == "recorded"
    assert outcome.result["operation"] == "baseline.disposition"
    assert outcome.result["affected_ids"] == ["occ-000001"]
    assert outcome.result["checkpoint_revision"] == 2
    assert replay(BASE, outcome.review) == facts


@pytest.mark.parametrize(
    "reason",
    [
        "assessment-unavailable",
        "orientation-unverified",
        "import-fidelity",
        "extent-change",
        "skew-range-edge",
        "decoder-warning",
        "canvas-warning",
    ],
)
def test_reject_outside_domain_is_argument_error_naming_allowed_and_command(reason: str) -> None:
    review = initial_review()
    action = Disposition(shown(review, "r1"), reason, "reject", "n")
    with pytest.raises(ReviewError) as caught:
        go(review, action, 2)
    error = caught.value
    assert (error.code, error.exit_code) == ("INVALID_ARGUMENT", 2)
    assert error.reason == reason
    assert error.allowed == ("retain-unresolved",)
    assert error.remediation == (
        f"bookscan baseline disposition PROJECT --receipt FILE --reason {reason} "
        "--decision retain-unresolved --note TEXT"
    )
    assert review == initial_review()


def test_unknown_decision_and_reason_are_argument_errors() -> None:
    review = initial_review()
    with pytest.raises(ReviewError) as decision:
        go(review, Disposition(shown(review, "r1"), "skew-nonzero", "accept", "n"), 2)
    assert decision.value.allowed == ("reject", "retain-unresolved")
    with pytest.raises(ReviewError) as reason:
        go(review, Disposition(shown(review, "r1"), "made-up", "retain-unresolved", "n"), 2)
    assert (reason.value.code, reason.value.exit_code) == ("INVALID_ARGUMENT", 2)
    assert reason.value.reason == "made-up"
    assert "valid reasons are" in reason.value.message


def test_reason_absent_from_the_occurrence_is_an_argument_error_without_state_change() -> None:
    review = initial_review()
    action = disposition(review, "r1", "skew-nonzero", "reject", occ="occ-000002")
    with pytest.raises(ReviewError) as caught:
        go(review, action, 2)
    assert caught.value.code == "INVALID_ARGUMENT"
    assert "orientation-unverified" in caught.value.message
    assert review == initial_review()


def test_static_value_checks_need_no_project() -> None:
    displayed = Displayed("r", PROJECT, "b" * 64, "c" * 64, "full", "occ-000001", "d" * 64)
    for action in (
        Disposition(displayed, "skew-nonzero", "retain-unresolved", "   "),
        Inspection(displayed, "everything", "Preview", "1:1", "n"),
        Inspection(displayed, "full", " ", "1:1", "n"),
        Inspection(displayed, "full", "Preview", "", "n"),
        Acknowledgement(displayed, "n", ()),
        Acknowledgement(displayed, "\ud800", None),
    ):
        with pytest.raises(ReviewError) as caught:
            check_values(action)
        assert caught.value.exit_code == 2


def test_later_decision_supersedes_and_history_is_kept() -> None:
    review = initial_review()
    review = go(review, disposition(review, "r1", "skew-nonzero", "reject"), 2).review
    review = go(review, disposition(review, "r2", "skew-nonzero", "retain-unresolved"), 3).review
    facts = replay(BASE, review)
    assert "skew-nonzero" in facts.unresolved["occ-000001"]
    assert [r["decision"] for r in review["dispositions"]] == ["reject", "retain-unresolved"]
    page = cast(list[Json], facts.snapshot["pages"])[0]
    assert page["triage_reasons"][1]["decision"]["decision"] == "retain-unresolved"
    assert page["triage_reasons"][1]["disposition"] == "baseline-retained/unresolved"


def test_retain_unresolved_records_the_note_and_keeps_coverage() -> None:
    review = initial_review()
    outcome = go(
        review, disposition(review, "r1", "extent-change", "retain-unresolved", occ="occ-000003"), 2
    )
    assert outcome.facts.unresolved["occ-000003"] == ("orientation-unverified", "extent-change")
    page = cast(list[Json], outcome.facts.snapshot["pages"])[2]
    assert page["triage_reasons"][1]["decision"] == {
        "decision": "retain-unresolved",
        "note": "note r1",
    }


def test_inspection_records_scope_and_regions_without_disposition_or_acknowledgement() -> None:
    review = initial_review()
    first = Inspection(
        shown(review, "i1", view="full"), "full", "Preview 11", "1:1 ruler", "saw it"
    )
    review = go(review, first, 2).review
    second = Inspection(
        shown(review, "i2", view="native"), "native", "Preview 11", "1:1 ruler", "tiles 1-2"
    )
    outcome = go(review, second, 3)
    facts = outcome.facts
    assert [r["scope"] for r in outcome.review["inspections"]] == ["full", "native"]
    assert outcome.review["inspections"][0]["regions"] == []
    assert outcome.review["inspections"][1]["regions"] == ["native-001", "native-002"]
    assert outcome.review["dispositions"] == []
    assert facts.unresolved["occ-000001"] == REASONS["occ-000001"]
    assert effective_acknowledgement(facts) is None
    scope = inspection_scope(facts)
    assert scope[0] == {
        "id": "occ-000001",
        "inspected": True,
        "full": True,
        "native_regions": ["native-001", "native-002"],
        "source_native_regions": [],
    }
    assert scope[1]["inspected"] is False and scope[2]["inspected"] is False
    assert cast(Json, outcome.result["detail"])["regions"] == ["native-001", "native-002"]


def test_inspection_scope_must_match_the_receipt_view() -> None:
    review = initial_review()
    mismatch = Inspection(shown(review, "i1", view="full"), "native", "V", "1:1", "n")
    with pytest.raises(ReviewError) as caught:
        go(review, mismatch, 2)
    assert (caught.value.code, caught.value.exit_code) == ("INVALID_ARGUMENT", 2)
    assert "--scope full" in caught.value.message


def test_inspection_changes_review_revision_and_invalidates_acknowledgement() -> None:
    review = initial_review()
    review = go(review, Acknowledgement(shown(review, "a1", view="summary"), "ok", None), 2).review
    before = replay(BASE, review)
    ack = effective_acknowledgement(before)
    assert ack is not None and ack["complete"] is True
    review = go(review, Inspection(shown(review, "i1"), "full", "V", "1:1", "n"), 3).review
    after = replay(BASE, review)
    assert after.review_revision != before.review_revision
    assert effective_acknowledgement(after) is None


def test_acknowledgement_advances_neither_review_revision_nor_snapshot() -> None:
    review = initial_review()
    before = replay(BASE, review)
    outcome = go(review, Acknowledgement(shown(review, "a1", view="summary"), "all of it", None), 2)
    assert outcome.facts.review_revision == before.review_revision
    assert outcome.facts.snapshot_id == before.snapshot_id
    ack = effective_acknowledgement(outcome.facts)
    assert ack is not None
    assert ack["complete"] is True
    assert ack["ids"] == ["occ-000001", "occ-000002", "occ-000003"]
    assert ack["missing_ids"] == []
    assert ack["limitation"] == LIMITATION
    record = outcome.review["acknowledgements"][0]
    assert cast(list[Json], record["pages"])[0] == {
        "id": "occ-000001",
        "reasons": list(REASONS["occ-000001"]),
    }
    assert outcome.result["status"] == "acknowledged"
    assert outcome.result["affected_ids"] == ["occ-000001", "occ-000002", "occ-000003"]


def test_two_summaries_at_one_snapshot_acknowledge_a_selection_union() -> None:
    review = initial_review()
    summary_a = shown(review, "sum-a", view="summary")
    summary_b = shown(review, "sum-b", view="summary")
    review = go(review, Acknowledgement(summary_a, "first", ("occ-000001",)), 2).review
    partial = effective_acknowledgement(replay(BASE, review))
    assert partial is not None
    assert partial["complete"] is False
    assert partial["ids"] == ["occ-000001"]
    assert partial["missing_ids"] == ["occ-000002", "occ-000003"]
    # The second summary's receipt is still current: acknowledgement changed nothing.
    review = go(review, Acknowledgement(summary_b, "rest", ("occ-000003", "occ-000002")), 3).review
    union = effective_acknowledgement(replay(BASE, review))
    assert union is not None
    assert union["complete"] is True
    assert union["ids"] == ["occ-000001", "occ-000002", "occ-000003"]
    scopes = cast(list[Json], union["scopes"])
    assert [s["request_id"] for s in scopes] == ["sum-a", "sum-b"]
    assert [s["ids"] for s in scopes] == [["occ-000001"], ["occ-000002", "occ-000003"]]


def test_acknowledgement_requires_known_pages_and_summary_receipt() -> None:
    review = initial_review()
    with pytest.raises(ReviewError) as unknown:
        go(review, Acknowledgement(shown(review, "a", view="summary"), "n", ("occ-9",)), 2)
    assert unknown.value.code == "INVALID_ARGUMENT"
    with pytest.raises(ReceiptError) as wrong:
        go(review, Acknowledgement(shown(review, "a", view="full"), "n", None), 2)
    assert wrong.value.context == "wrong-view"


def test_page_actions_reject_a_summary_receipt() -> None:
    review = initial_review()
    for action in (
        Disposition(shown(review, "s", view="summary"), "skew-nonzero", "reject", "n"),
        Inspection(shown(review, "s", view="summary"), "full", "V", "1:1", "n"),
    ):
        with pytest.raises(ReceiptError) as caught:
            go(review, action, 2)
        assert caught.value.context == "wrong-view"


def test_identical_retry_replays_original_result_before_currency_and_integrity() -> None:
    review = initial_review()
    first_action = disposition(review, "r1", "skew-nonzero", "reject")
    first = go(review, first_action, 2)
    later = go(
        first.review,
        Inspection(shown(first.review, "i1", occ="occ-000002"), "full", "V", "1:1", "n"),
        3,
    ).review
    assert replay(BASE, later).review_revision != first.facts.review_revision

    def forbidden() -> None:
        raise AssertionError("external file integrity must not run for a replay")

    again = act(BASE, later, first_action, checkpoint_revision=4, integrity=forbidden)
    assert again.replayed is True
    assert again.result == first.result
    assert again.review == later
    assert again.result["review_revision"] == first.facts.review_revision
    assert again.facts.review_revision != first.facts.review_revision


def test_conflicting_receipt_reuse_is_receipt_used_without_a_new_record() -> None:
    review = initial_review()
    first = disposition(review, "r1", "skew-nonzero", "reject")
    review = go(review, first, 2).review
    snapshot = copy.deepcopy(review)
    conflicting = replace(first, decision="retain-unresolved")
    with pytest.raises(ReceiptError) as caught:
        go(review, conflicting, 3)
    assert (caught.value.code, caught.value.exit_code) == ("INVALID_RECEIPT", 6)
    assert caught.value.context == "receipt-used"
    different_operation = Inspection(first.displayed, "full", "V", "1:1", "n")
    with pytest.raises(ReceiptError) as other:
        go(review, different_operation, 3)
    assert other.value.context == "receipt-used"
    assert review == snapshot


def test_stale_new_request_fails_before_integrity_and_commits_nothing() -> None:
    review = initial_review()
    stale = disposition(review, "r1", "skew-nonzero", "reject")
    review = go(review, disposition(review, "r0", "import-fidelity", "retain-unresolved"), 2).review
    calls: list[str] = []
    with pytest.raises(ReviewError) as caught:
        act(BASE, review, stale, checkpoint_revision=3, integrity=lambda: calls.append("x"))
    assert (caught.value.code, caught.value.exit_code) == ("STALE_ACTION", 6)
    assert calls == []


def test_integrity_runs_after_currency_and_blocks_a_new_action() -> None:
    review = initial_review()
    action = disposition(review, "r1", "skew-nonzero", "reject")

    def changed() -> None:
        raise ReceiptError("Packet file changed.", "packet-file-changed")

    with pytest.raises(ReceiptError) as caught:
        act(BASE, review, action, checkpoint_revision=2, integrity=changed)
    assert caught.value.context == "packet-file-changed"
    calls: list[str] = []
    act(BASE, review, action, checkpoint_revision=2, integrity=lambda: calls.append("ok"))
    assert calls == ["ok"]


def test_foreign_project_and_changed_image_revision_are_refused() -> None:
    review = initial_review()
    good = shown(review, "r1")
    with pytest.raises(ReceiptError) as foreign:
        go(
            review,
            Disposition(replace(good, project_id="project-other"), "skew-nonzero", "reject", "n"),
            2,
        )
    assert foreign.value.context == "foreign"
    with pytest.raises(ReviewError) as image:
        go(
            review,
            Disposition(replace(good, image_revision="e" * 64), "skew-nonzero", "reject", "n"),
            2,
        )
    assert image.value.code == "STALE_ACTION"
    with pytest.raises(ReviewError) as unknown:
        go(
            review,
            Disposition(replace(good, occurrence_id="occ-404"), "skew-nonzero", "reject", "n"),
            2,
        )
    assert unknown.value.code == "INVALID_ARGUMENT"


def test_checkpoint_revision_must_follow_every_recorded_action() -> None:
    review = initial_review()
    review = go(review, disposition(review, "r1", "skew-nonzero", "reject"), 5).review
    with pytest.raises(ReviewError) as caught:
        go(
            review,
            disposition(review, "r2", "extent-change", "retain-unresolved", occ="occ-000003"),
            5,
        )
    assert caught.value.code == "INVALID_PROJECT"
    go(review, disposition(review, "r2", "extent-change", "retain-unresolved", occ="occ-000003"), 6)


def test_inputs_are_not_mutated_and_outputs_are_detached() -> None:
    review = initial_review()
    outcome = go(review, disposition(review, "r1", "skew-nonzero", "reject"), 2)
    assert review == initial_review()
    inspected = go(
        outcome.review, Inspection(shown(outcome.review, "i1"), "full", "V", "1:1", "n"), 3
    )
    inspected.review["inspections"][0]["note"] = "tampered"
    assert inspected.facts.inspections[0]["note"] == "n"
    outcome.review["dispositions"][0]["note"] = "tampered"
    outcome.result["review_revision"] = "tampered"
    with pytest.raises(ReviewError):
        replay(BASE, outcome.review)
    assert BASE.snapshot == make_base().snapshot


def test_browser_style_request_uses_the_same_boundary_as_a_receipt() -> None:
    review = initial_review()
    facts = replay(BASE, review)
    browser = Disposition(
        Displayed(
            "request-7f3",
            PROJECT,
            facts.review_revision,
            facts.snapshot_id,
            "full",
            "occ-000002",
            IMG["occ-000002"],
        ),
        "orientation-unverified",
        "retain-unresolved",
        "browser note",
    )
    first = go(review, browser, 2)
    assert go(first.review, browser, 3).replayed is True
    with pytest.raises(ReceiptError) as caught:
        go(first.review, replace(browser, note="different"), 3)
    assert caught.value.context == "receipt-used"


def test_displayed_from_a_real_receipt_matches_its_coverage() -> None:
    facts = replay(BASE, initial_review())
    identity = Identity(PROJECT, "a" * 64, facts.review_revision, facts.snapshot_id)
    issuance = issue(
        identity,
        "views",
        [
            (
                "receipts/native-001.json",
                Coverage(
                    "native",
                    occurrence_id="occ-000001",
                    source_pdf_page=1,
                    image_revision=IMG["occ-000001"],
                    regions=("native-001", "native-003"),
                    scale="1 point per pixel",
                ),
            )
        ],
    )
    receipt = issuance.receipts[0]
    displayed = Displayed.from_receipt(receipt)
    assert displayed.request_id == receipt.receipt_id
    assert displayed.regions == ("native-001", "native-003")
    outcome = go(initial_review(), Inspection(displayed, "native", "V", "1:1 ruler", "regions"), 2)
    assert outcome.review["inspections"][0]["regions"] == ["native-001", "native-003"]
    assert outcome.review["inspections"][0]["request_id"] == receipt.receipt_id


def test_digests_track_exactly_the_facts_they_name() -> None:
    review = initial_review()
    base_facts = replay(BASE, review)
    base_unresolved = unresolved_digest(base_facts)
    base_inspection = inspection_digest(base_facts)
    assert unresolved_digest(replay(BASE, initial_review())) == base_unresolved

    retained = go(review, disposition(review, "r1", "skew-nonzero", "retain-unresolved"), 2).review
    facts = replay(BASE, retained)
    assert unresolved_digest(facts) == base_unresolved
    assert inspection_digest(facts) != base_inspection

    rejected = go(review, disposition(review, "r1", "skew-nonzero", "reject"), 2).review
    assert unresolved_digest(replay(BASE, rejected)) != base_unresolved

    inspected = go(review, Inspection(shown(review, "i1"), "full", "V", "1:1", "n"), 2).review
    facts = replay(BASE, inspected)
    assert unresolved_digest(facts) == base_unresolved
    assert inspection_digest(facts) != base_inspection

    acknowledged = go(review, Acknowledgement(shown(review, "a1", view="summary"), "n", None), 2)
    assert unresolved_digest(acknowledged.facts) == base_unresolved
    assert inspection_digest(acknowledged.facts) == base_inspection


def test_request_digest_binds_operation_id_displayed_identity_and_values() -> None:
    review = initial_review()
    action = disposition(review, "r1", "skew-nonzero", "reject")
    digest = request_digest(action)
    assert request_digest(disposition(review, "r1", "skew-nonzero", "reject")) == digest
    assert request_digest(replace(action, note="other")) != digest
    assert request_digest(replace(action, decision="retain-unresolved")) != digest
    assert (
        request_digest(replace(action, displayed=replace(action.displayed, request_id="r2")))
        != digest
    )
    assert (
        request_digest(
            replace(action, displayed=replace(action.displayed, review_revision="f" * 64))
        )
        != digest
    )
    a = Acknowledgement(shown(review, "s", view="summary"), "n", ("occ-000002", "occ-000001"))
    b = replace(a, pages=("occ-000001", "occ-000002", "occ-000001"))
    assert request_digest(a) == request_digest(b)


def _saved() -> Json:
    review: Json = initial_review()
    review = go(review, disposition(review, "r1", "skew-nonzero", "reject"), 2).review
    native = Inspection(shown(review, "i1", view="native"), "native", "V", "1:1", "n")
    review = go(review, native, 3).review
    review = go(review, Acknowledgement(shown(review, "a1", view="summary"), "ok", None), 4).review
    return review


def test_replay_accepts_a_complete_saved_history() -> None:
    saved = _saved()
    facts = replay(BASE, saved)
    ack = effective_acknowledgement(facts)
    assert ack is not None and ack["complete"] is True
    assert [r["checkpoint_revision"] for r in saved["dispositions"]] == [2]
    assert replay(BASE, json.loads(json.dumps(saved))) == facts


type Mutation = Callable[[Json], object]
MUTATIONS: list[tuple[str, Mutation]] = [
    ("reason", lambda s: s["dispositions"][0].update(reason="extent-change")),
    ("note", lambda s: s["dispositions"][0].update(note="edited")),
    ("revision", lambda s: s["dispositions"][0].update(checkpoint_revision=9)),
    ("image", lambda s: s["dispositions"][0].update(image_revision="e" * 64)),
    ("regions", lambda s: s["inspections"][0].update(regions=["native-009"])),
    ("scope", lambda s: s["inspections"][0].update(scope="full")),
    ("ack-snapshot", lambda s: s["acknowledgements"][0].update(snapshot_id="e" * 64)),
    ("ack-pages", lambda s: s["acknowledgements"][0]["pages"].pop()),
    ("missing-retry", lambda s: s["retries"].pop()),
    ("retry-order", lambda s: s["retries"].reverse()),
    ("request-digest", lambda s: s["retries"][0].update(request_sha256="e" * 64)),
    ("result", lambda s: s["retries"][0]["result"].update(review_revision="e" * 64)),
    (
        "request-values",
        lambda s: s["retries"][0]["request"]["values"].update(decision="retain-unresolved"),
    ),
    (
        "request-swap",
        lambda s: s["retries"][1].update(request=copy.deepcopy(s["retries"][0]["request"])),
    ),
    ("duplicate-record", lambda s: s["dispositions"].append(copy.deepcopy(s["dispositions"][0]))),
    ("extra-list", lambda s: s.update(extra=[])),
    ("missing-list", lambda s: s.pop("retries")),
    ("record-field", lambda s: s["inspections"][0].pop("viewer")),
]


@pytest.mark.parametrize(("name", "change"), MUTATIONS, ids=[n for n, _ in MUTATIONS])
def test_replay_rejects_records_this_module_could_not_have_produced(
    name: str, change: Mutation
) -> None:
    assert name
    saved = _saved()
    change(saved)
    with pytest.raises(ReviewError) as caught:
        replay(BASE, saved)
    assert (caught.value.code, caught.value.exit_code) == ("INVALID_PROJECT", 3)


def test_replay_rejects_a_decision_outside_the_reason_domain_even_if_self_consistent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domains = cast(dict[str, tuple[str, ...]], REASON_DECISIONS)
    monkeypatch.setitem(domains, "extent-change", ("reject", "retain-unresolved"))
    review = initial_review()
    forged = go(
        review, disposition(review, "r1", "extent-change", "reject", occ="occ-000003"), 2
    ).review
    assert replay(BASE, forged).unresolved["occ-000003"] == ("orientation-unverified",)
    monkeypatch.undo()
    with pytest.raises(ReviewError) as caught:
        replay(BASE, forged)
    assert caught.value.code == "INVALID_PROJECT"


def _no_prior(saved: object, action: object, facts: object) -> None:
    """Stand-in for the durable-retry lookup, to forge histories the boundary refuses."""


def _no_order(saved: object, revision: object) -> None:
    """Stand-in for the revision-order guard, to forge histories the boundary refuses."""


def test_replay_rejects_a_reused_request_id_in_an_otherwise_consistent_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review = initial_review()
    review = go(review, disposition(review, "same", "skew-nonzero", "reject"), 2).review
    # Bypass the durable-retry lookup the public boundary applies, to forge the state.
    monkeypatch.setattr("bookscan.review_facts._prior", _no_prior)
    forged = go(
        review, disposition(review, "same", "import-fidelity", "retain-unresolved"), 3
    ).review
    monkeypatch.undo()
    with pytest.raises(ReviewError) as caught:
        replay(BASE, forged)
    assert "twice" in caught.value.message


def test_replay_rejects_two_records_at_one_checkpoint_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review = initial_review()
    review = go(review, disposition(review, "r1", "skew-nonzero", "reject"), 2).review
    monkeypatch.setattr("bookscan.review_facts._check_order", _no_order)
    forged = go(review, Inspection(shown(review, "i1"), "full", "V", "1:1", "n"), 2).review
    monkeypatch.undo()
    with pytest.raises(ReviewError) as caught:
        replay(BASE, forged)
    assert "share one checkpoint revision" in caught.value.message


def test_replay_rejects_an_action_claiming_the_initial_import_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review = initial_review()
    monkeypatch.setattr("bookscan.review_facts._check_order", _no_order)
    forged = go(review, disposition(review, "r1", "skew-nonzero", "reject"), 1).review
    monkeypatch.undo()
    with pytest.raises(ReviewError) as caught:
        replay(BASE, forged)
    assert "valid checkpoint revision" in caught.value.message


def test_replay_rejects_saved_list_order_that_differs_from_commit_order() -> None:
    review = initial_review()
    review = go(review, disposition(review, "r1", "skew-nonzero", "reject"), 2).review
    review = go(review, disposition(review, "r2", "import-fidelity", "retain-unresolved"), 3).review
    review["dispositions"].reverse()
    with pytest.raises(ReviewError) as caught:
        replay(BASE, review)
    assert caught.value.code == "INVALID_PROJECT"


def test_identical_rerecord_changes_review_revision_and_invalidates_acknowledgement() -> None:
    review = initial_review()
    first = Disposition(shown(review, "r1"), "skew-nonzero", "retain-unresolved", "same note")
    review = go(review, first, 2).review
    review = go(review, Acknowledgement(shown(review, "a1", view="summary"), "ok", None), 3).review
    before = replay(BASE, review)
    ack = effective_acknowledgement(before)
    assert ack is not None and ack["complete"] is True
    again = Disposition(shown(review, "r2"), "skew-nonzero", "retain-unresolved", "same note")
    outcome = go(review, again, 4)
    assert outcome.facts.snapshot_id == before.snapshot_id
    assert outcome.facts.review_revision != before.review_revision
    assert effective_acknowledgement(outcome.facts) is None


def test_displayed_snapshot_must_match_even_when_the_review_revision_does() -> None:
    review = initial_review()
    good = shown(review, "r1")
    action = Disposition(replace(good, snapshot_id="e" * 64), "skew-nonzero", "reject", "n")
    with pytest.raises(ReviewError) as caught:
        go(review, action, 2)
    assert caught.value.code == "STALE_ACTION"


def test_replay_rejects_a_forged_displayed_revision_even_with_a_consistent_digest() -> None:
    review = initial_review()
    review = go(review, disposition(review, "r1", "skew-nonzero", "reject"), 2).review
    review = go(review, disposition(review, "r2", "import-fidelity", "retain-unresolved"), 3).review
    request = cast(Json, review["retries"][1]["request"])
    # The second action claims it was issued before the first changed review facts.
    request["displayed"]["review_revision"] = replay(BASE, initial_review()).review_revision
    request["displayed"]["snapshot_id"] = replay(BASE, initial_review()).snapshot_id
    review["retries"][1]["request_sha256"] = hashlib.sha256(
        canonical({"domain": "BookScanBuilderActionRequest-v1", "value": request})
    ).hexdigest()
    with pytest.raises(ReviewError) as caught:
        replay(BASE, review)
    assert caught.value.code == "INVALID_PROJECT"
