"""An initial checkpoint cannot mix independently valid import contexts.

Constructed saved RGB tests persistence, not rendering fidelity. Coherent record
rehashes catch missing association checks; restart must use saved source/assets.
"""

import copy
import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
from test_assessed_record import owner as owner
from test_assessed_record import state as assessed_fixture
from test_dependency_record import RENDERER
from test_dependency_record import literal as dependency_literal
from test_fontconfig_discovery_record import literal as discovery_literal
from test_fontconfig_discovery_record import snapshot_literal

from bookscan import ownership, project_header
from bookscan.ownership import Writer
from bookscan.project_header import Stores


@pytest.fixture
def evidence(owner: Writer, tmp_path: Path) -> tuple[Stores, dict[str, Any]]:  # noqa: F811
    build = cast(
        Callable[[Writer, Path], tuple[Stores, dict[str, object]]],
        getattr(assessed_fixture, "__wrapped__"),
    )
    stores, assessed = build(owner, tmp_path)
    dependencies, binding = dependency_literal()
    value: dict[str, Any] = dict(
        assessed, dependencies=dependencies, resource_binding=binding, fontconfig=None
    )
    for page in value["occurrences"]:
        page["render"]["command"][0] = RENDERER
        page["render"]["resource_binding"] = copy.deepcopy(binding)
    return stores, value


def configured(value: dict[str, Any], kind: str) -> None:
    discovery = snapshot_literal() if kind == "copy" else discovery_literal(cache=kind == "cache")
    # Production discovery captures the renderer graph and executable context.
    discovery = json.loads(json.dumps(discovery).replace("/historical/program", RENDERER))
    discovery["linked"]["executable_context"] = RENDERER
    if "resource_snapshot" in discovery:
        discovery["resource_snapshot"]["original"]["linked"]["executable_context"] = RENDERER
    value["dependencies"]["linked"]["pdftocairo"] = copy.deepcopy(discovery["linked"])
    binding = value["resource_binding"]
    names = {item["path"] for item in binding["files"]}
    binding["files"].extend(
        item for item in discovery["binding"]["files"] if item["path"] not in names
    )
    cast(list[dict[str, Any]], binding["files"]).sort(key=lambda item: item["path"])
    binding["directories"] = copy.deepcopy(discovery["binding"]["directories"])
    binding["fontconfig_scope_guard"] = copy.deepcopy(
        discovery["binding"]["fontconfig_scope_guard"]
    )
    value["fontconfig"] = discovery
    for page in value["occurrences"]:
        page["render"]["resource_binding"] = copy.deepcopy(binding)


def digest(domain: str, value: object) -> str:
    raw = json.dumps(
        {"domain": domain, "value": value},
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("kind", ["absent", "scope", "cache", "copy"])
def test_initial_retention_has_no_review_or_ack_and_distinct_identities(
    evidence: tuple[Stores, dict[str, Any]],
    kind: str,
) -> None:
    from bookscan import baseline_state

    stores, value = evidence
    if kind != "absent":
        configured(value, kind)
    record = baseline_state.initial(stores, value)
    result = baseline_state.restore(stores, record)
    assert result.project_id == "project-" + stores.header.lock.token
    assert [page.core.id for page in result.occurrences] == [
        "occ-000001",
        "occ-000002",
        "occ-000003",
    ]
    assert result.occurrences[0].core.baseline == result.occurrences[1].core.baseline
    assert result.image_revisions[0] == result.image_revisions[1]
    assert result.snapshot_id != result.review_revision
    assert record["review"] == {
        "dispositions": [],
        "inspections": [],
        "acknowledgements": [],
        "retries": [],
    }
    assert result.fontconfig is None if kind == "absent" else result.fontconfig is not None
    assert "Historical" in result.limitations[0]
    assert record["snapshot_id"] == digest("BookScanBuilderExportSnapshot-v1", record["snapshot"])
    assert record["review_revision"] == digest(
        "BookScanBuilderReview-v1",
        {
            "project_id": record["project_id"],
            "import": value,
            "dispositions": [],
            "inspections": [],
        },
    )
    before = copy.deepcopy(record)
    value["occurrences"][0]["render"]["diagnostics"] = "changed externally"
    assert record == before and result.occurrences[0].render.diagnostics == "decoder café"


FAULTS = (
    "format",
    "version",
    "version-bool",
    "extra",
    "missing",
    "foreign-project",
    "review-digest",
    "snapshot-digest",
    "snapshot-fields",
    "image-revision",
    "disposition",
    "inspection",
    "acknowledgement",
    "retry",
    "review-extra",
    "missing-render-binding",
    "render-environment",
    "render-cwd",
    "render-native",
    "render-extra-file",
    "missing-discovery",
    "discovery-environment",
    "discovery-cwd",
    "discovery-native",
    "discovery-extra-file",
    "discovery-directory",
    "discovery-architecture",
    "discovery-build",
    "discovery-context",
    "orphan-discovery",
    "analysis-version",
    "scope-change",
    "tuple",
    "nan",
    "surrogate",
    "nonstring-key",
)


def corrupt(record: dict[str, Any], fault: str) -> None:
    if fault in ("format", "version", "version-bool", "foreign-project"):
        record[{"foreign-project": "project_id", "version-bool": "version"}.get(fault, fault)] = (
            True if fault == "version-bool" else 2 if fault == "version" else "foreign"
        )
    elif fault == "extra":
        record["accepted"] = True
    elif fault == "missing":
        del record["fontconfig"]
    elif fault in ("review-digest", "snapshot-digest"):
        record["review_revision" if fault == "review-digest" else "snapshot_id"] = "0" * 64
    elif fault == "snapshot-fields":
        record["snapshot"]["limitation"] = "verified"
    elif fault == "image-revision":
        record["image_revisions"][0] = "0" * 64
    elif fault in ("disposition", "inspection", "acknowledgement", "retry"):
        key = {
            "disposition": "dispositions",
            "inspection": "inspections",
            "acknowledgement": "acknowledgements",
            "retry": "retries",
        }[fault]
        record["review"][key] = [{"claimed": True}]
    elif fault == "review-extra":
        record["review"]["accepted"] = True
    elif fault == "missing-render-binding":
        del record["occurrences"][1]["render"]["resource_binding"]
    elif fault.startswith("render-"):
        binding = record["occurrences"][1]["render"]["resource_binding"]
        if fault == "render-environment":
            binding["environment_sha256"] = "1" * 64
        elif fault == "render-cwd":
            binding["working_directory_identity"] = [3, 4]
        elif fault == "render-native":
            binding["files"][0]["inode"] += 1
        else:
            binding["files"].append({**binding["files"][0], "path": "/zzz-extra"})
    elif fault == "missing-discovery":
        record["fontconfig"] = None
    elif fault.startswith("discovery-"):
        discovery = record["fontconfig"]
        binding = discovery["binding"]
        if fault == "discovery-environment":
            binding["environment_sha256"] = "1" * 64
        elif fault == "discovery-cwd":
            binding["working_directory_identity"] = [3, 4]
        elif fault == "discovery-native":
            binding["files"][0]["inode"] += 1
        elif fault == "discovery-extra-file":
            binding["files"].append({**binding["files"][0], "path": "/zzz-extra"})
        elif fault == "discovery-directory":
            binding["directories"][0]["entries"] = None
        else:
            discovery["linked"][
                {
                    "discovery-architecture": "architecture",
                    "discovery-build": "os_build",
                    "discovery-context": "executable_context",
                }[fault]
            ] = (
                "x86_64"
                if fault == "discovery-architecture"
                else "other"
                if fault == "discovery-build"
                else "/foreign/python"
            )
    elif fault == "orphan-discovery":
        del record["resource_binding"]["fontconfig_scope_guard"]
        for page in record["occurrences"]:
            del page["render"]["resource_binding"]["fontconfig_scope_guard"]
    elif fault == "analysis-version":
        record["occurrences"][0]["analysis"]["library_version"] = "future"
    elif fault == "scope-change":
        record["occurrences"][0]["render"]["resource_binding"]["fontconfig_scope_guard"]["scope"][
            "font_dirs"
        ] = []
    elif fault == "tuple":
        record["image_revisions"] = tuple(record["image_revisions"])
    elif fault == "nan":
        record["version"] = float("nan")
    elif fault == "surrogate":
        record["format"] = "\ud800"
    elif fault == "nonstring-key":
        cast(dict[object, object], record)[1] = "invalid"
    else:
        raise AssertionError(fault)


def reseal(record: dict[str, Any]) -> None:
    """Independently recompute declared identities after a semantic corruption."""
    value = {
        key: record[key]
        for key in (
            "source",
            "occurrences",
            "baselines",
            "native_blobs",
            "dependencies",
            "resource_binding",
            "fontconfig",
        )
    }
    record["review_revision"] = digest(
        "BookScanBuilderReview-v1",
        {
            "project_id": record["project_id"],
            "import": value,
            "dispositions": [],
            "inspections": [],
        },
    )
    for page, shown in zip(value["occurrences"], record["snapshot"]["pages"], strict=True):
        for key in ("geometry", "analysis", "triage_reasons"):
            shown[key] = copy.deepcopy(page[key])
    record["snapshot"]["toolchain"] = copy.deepcopy(value["dependencies"])
    record["snapshot_id"] = digest("BookScanBuilderExportSnapshot-v1", record["snapshot"])


@pytest.mark.parametrize("fault", FAULTS)
def test_rehashed_contradiction_never_becomes_accepted_state(
    evidence: tuple[Stores, dict[str, Any]],
    fault: str,
) -> None:
    from bookscan import baseline_state

    stores, value = evidence
    configured(value, "scope")
    record = baseline_state.initial(stores, value)
    corrupt(record, fault)
    if fault.startswith(("render-", "discovery-")) or fault in (
        "missing-render-binding",
        "missing-discovery",
        "orphan-discovery",
        "analysis-version",
        "scope-change",
    ):
        reseal(record)
    # The outer checkpoint writer may coherently rehash any corrupt payload.
    # It must still fail this semantic verifier, without changing saved bytes.
    before = copy.deepcopy(record)
    with pytest.raises(baseline_state.BaselineStateError) as caught:
        baseline_state.restore(stores, record)
    assert caught.value.code == "INVALID_PROJECT" and caught.value.exit_code == 3
    if fault != "nan":
        assert record == before


@pytest.mark.parametrize(
    "fault", ["valid", "render-native", "discovery-context", "acknowledgement"]
)
def test_source_loss_history_verifies_all_predecessors_and_releases_ownership(
    evidence: tuple[Stores, dict[str, Any]],
    fault: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import baseline_state

    stores, value = evidence
    configured(value, "scope")
    record = baseline_state.initial(stores, value)
    prior = copy.deepcopy(record)
    if fault != "valid":
        corrupt(prior, fault)
        reseal(prior)
    previous = stores.checkpoints.commit(
        prior, expected=None, verify_state=lambda _: None
    ).checkpoint
    stores.checkpoints.commit(record, expected=previous, verify_state=lambda _: None)
    path = stores.owner.path
    stores.owner.close()
    before = {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()}

    def denied(*args: object, **kwargs: object) -> object:
        raise PermissionError("native launch forbidden")

    monkeypatch.setattr(subprocess, "Popen", denied)
    with pytest.raises(PermissionError):
        subprocess.Popen(["forbidden"])

    def verify(held: Stores, payload: dict[str, object]) -> None:
        baseline_state.restore(held, payload)

    if fault == "valid":
        with project_header.resume(path, verify_state=verify) as (_, current):
            assert current.revision == 2
    else:
        with pytest.raises(baseline_state.BaselineStateError):
            with project_header.resume(path, verify_state=verify):
                pytest.fail("Corrupt predecessor accepted")
    assert before == {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()}
    with ownership.Writer.acquire(path, stores.header.lock):
        pass


def test_caller_held_owner_and_selected_cancellation_are_preserved(
    evidence: tuple[Stores, dict[str, Any]],
) -> None:
    from bookscan import baseline_state

    stores, value = evidence
    record = baseline_state.initial(stores, value)
    with pytest.raises(ownership.OwnershipError) as busy:
        ownership.Writer.acquire(stores.owner.path, stores.header.lock)
    assert busy.value.code == "PROJECT_BUSY"
    selected = OSError("operation-owner selected cancellation")
    count = 0

    def cancel() -> None:
        nonlocal count
        count += 1
        if count == 7:
            raise selected

    with pytest.raises(OSError) as caught:
        baseline_state.restore(stores, record, check_cancel=cancel)
    assert caught.value is selected
    stores.verify()


@pytest.mark.parametrize("operation", ["initial", "restore"])
@pytest.mark.parametrize("boundary", [1, 7, 25])
def test_selected_domain_failure_keeps_exact_identity(
    evidence: tuple[Stores, dict[str, Any]],
    operation: str,
    boundary: int,
) -> None:
    from bookscan import baseline_state

    stores, value = evidence
    record = baseline_state.initial(stores, value)
    selected = baseline_state.BaselineStateError("Selected operation outcome")
    count = 0

    def cancel() -> None:
        nonlocal count
        count += 1
        if count == boundary:
            raise selected

    with pytest.raises(baseline_state.BaselineStateError) as caught:
        if operation == "initial":
            baseline_state.initial(stores, value, check_cancel=cancel)
        else:
            baseline_state.restore(stores, record, check_cancel=cancel)
    assert caught.value is selected
    stores.verify()


# --- saved review facts: replay-verified restore and the action boundary -------------


def shown(state: Any, page: int, view: str, request: str, *, summary: bool = False) -> Any:
    from bookscan.review_facts import Displayed

    return Displayed(
        request,
        state.project_id,
        state.review_revision,
        state.snapshot_id,
        "summary" if summary else view,
        None if summary else state.occurrences[page].core.id,
        None if summary else state.image_revisions[page],
        () if summary else ("full",) if view == "full" else ("native-0",),
    )


def acted(
    stores: Stores, record: dict[str, Any], action: Any, revision: int
) -> tuple[dict[str, Any], Any]:
    from bookscan import baseline_state

    moved = baseline_state.act(stores, record, action, checkpoint_revision=revision)
    assert moved.state is not None and not moved.replayed
    return moved.state, baseline_state.restore(stores, moved.state)


def test_restore_replays_saved_review_and_derives_identities(
    evidence: tuple[Stores, dict[str, Any]],
) -> None:
    from bookscan import baseline_state
    from bookscan.review_facts import Acknowledgement, Disposition, Inspection

    stores, value = evidence
    record = baseline_state.initial(stores, value)
    start = baseline_state.restore(stores, record)
    first = start
    record, state = acted(
        stores,
        record,
        Disposition(shown(start, 0, "full", "r-1"), "skew-nonzero", "reject", "not skewed"),
        2,
    )
    assert state.review_revision != first.review_revision
    assert state.snapshot_id != first.snapshot_id
    assert state.facts.unresolved["occ-000001"] == (
        "orientation-unverified",
        "import-fidelity",
        "extent-change",
        "decoder-warning",
    )
    record, state = acted(
        stores,
        record,
        Inspection(shown(state, 1, "full", "r-2"), "full", "Preview", "1:1", "looked"),
        3,
    )
    pages = {p["id"]: p for p in record["snapshot"]["pages"]}
    assert pages["occ-000002"]["inspections"][0]["viewer"] == "Preview"
    assert record["snapshot"]["pages"][0]["triage_reasons"][1]["disposition"] == (
        "suggestion-rejected"
    )
    before_ack = state
    record, state = acted(
        stores,
        record,
        Acknowledgement(shown(state, 0, "full", "r-3", summary=True), "ack all", None),
        4,
    )
    # Acknowledgement advances the checkpoint alone, never either identity.
    assert state.review_revision == before_ack.review_revision
    assert state.snapshot_id == before_ack.snapshot_id
    assert len(record["review"]["retries"]) == 3
    assert [r["checkpoint_revision"] for r in record["review"]["dispositions"]] == [2]
    assert baseline_state.restore(stores, copy.deepcopy(record)).facts.acknowledgements


def test_identical_retry_is_durable_and_commits_nothing(
    evidence: tuple[Stores, dict[str, Any]],
) -> None:
    from bookscan import baseline_state
    from bookscan.packet_receipts import ReceiptError
    from bookscan.review_facts import Disposition, ReviewError

    stores, value = evidence
    record = baseline_state.initial(stores, value)
    start = baseline_state.restore(stores, record)
    action = Disposition(shown(start, 0, "full", "r-1"), "skew-nonzero", "reject", "n")
    record, state = acted(stores, record, action, 2)
    saved = copy.deepcopy(record)
    again = baseline_state.act(stores, record, action, checkpoint_revision=3)
    assert again.replayed and again.state is None
    assert again.result["review_revision"] == state.review_revision
    assert again.result["checkpoint_revision"] == 2
    assert again.facts.review_revision == state.review_revision
    assert record == saved
    other = Disposition(action.displayed, "skew-nonzero", "retain-unresolved", "n")
    with pytest.raises(ReceiptError) as used:
        baseline_state.act(stores, record, other, checkpoint_revision=3)
    assert used.value.context == "receipt-used"
    fresh = Disposition(shown(start, 1, "full", "r-2"), "skew-nonzero", "reject", "n")
    with pytest.raises(ReviewError) as stale:
        baseline_state.act(stores, record, fresh, checkpoint_revision=3)
    assert stale.value.code == "STALE_ACTION" and record == saved


def test_integrity_is_not_consulted_for_a_retry_but_blocks_a_new_action(
    evidence: tuple[Stores, dict[str, Any]],
) -> None:
    from bookscan import baseline_state
    from bookscan.review_facts import Inspection

    stores, value = evidence
    record = baseline_state.initial(stores, value)
    start = baseline_state.restore(stores, record)
    marker = RuntimeError("packet file changed")

    def broken() -> None:
        raise marker

    first = Inspection(shown(start, 0, "full", "r-1"), "full", "Preview", "1:1", "n")
    with pytest.raises(RuntimeError) as caught:
        baseline_state.act(stores, record, first, checkpoint_revision=2, integrity=broken)
    assert caught.value is marker
    record, _ = acted(stores, record, first, 2)
    again = baseline_state.act(stores, record, first, checkpoint_revision=3, integrity=broken)
    assert again.replayed


@pytest.mark.parametrize(
    "fault",
    [
        "decision-outside-domain",
        "stale-displayed-revision",
        "foreign-project",
        "record-without-retry",
        "retry-without-record",
        "top-level-revision",
        "top-level-snapshot",
        "snapshot-ignores-decision",
        "reused-request",
        "unknown-occurrence",
        "result-edited",
    ],
)
def test_forged_review_history_never_becomes_state_even_when_rehashed(
    evidence: tuple[Stores, dict[str, Any]], fault: str
) -> None:
    from bookscan import baseline_state
    from bookscan.review_facts import Disposition, Inspection

    stores, value = evidence
    record = baseline_state.initial(stores, value)
    start = baseline_state.restore(stores, record)
    record, state = acted(
        stores,
        record,
        Disposition(shown(start, 0, "full", "r-1"), "skew-nonzero", "reject", "n"),
        2,
    )
    record, state = acted(
        stores,
        record,
        Inspection(shown(state, 1, "full", "r-2"), "full", "Preview", "1:1", "n"),
        3,
    )
    review = record["review"]
    if fault == "decision-outside-domain":
        review["retries"][0]["request"]["values"]["reason"] = "import-fidelity"
        review["dispositions"][0]["reason"] = "import-fidelity"
    elif fault == "stale-displayed-revision":
        review["retries"][1]["request"]["displayed"]["review_revision"] = "0" * 64
    elif fault == "foreign-project":
        review["retries"][0]["request"]["displayed"]["project_id"] = "project-other"
    elif fault == "record-without-retry":
        review["retries"].pop()
    elif fault == "retry-without-record":
        review["inspections"].pop()
    elif fault == "top-level-revision":
        record["review_revision"] = "0" * 64
    elif fault == "top-level-snapshot":
        record["snapshot"]["pages"][1]["inspections"] = []
        record["snapshot_id"] = digest("BookScanBuilderExportSnapshot-v1", record["snapshot"])
    elif fault == "snapshot-ignores-decision":
        record["snapshot"]["pages"][0]["triage_reasons"][1].pop("decision")
        record["snapshot_id"] = digest("BookScanBuilderExportSnapshot-v1", record["snapshot"])
    elif fault == "reused-request":
        review["retries"][1]["request"]["request_id"] = "r-1"
        review["inspections"][0]["request_id"] = "r-1"
    elif fault == "unknown-occurrence":
        review["retries"][1]["request"]["displayed"]["occurrence_id"] = "occ-999999"
        review["inspections"][0]["occurrence_id"] = "occ-999999"
    else:
        review["retries"][0]["result"]["status"] = "forged"
    before = copy.deepcopy(record)
    with pytest.raises(baseline_state.BaselineStateError) as caught:
        baseline_state.restore(stores, record)
    assert caught.value.code == "INVALID_PROJECT" and caught.value.exit_code == 3
    assert record == before


def test_restored_state_and_transition_are_detached_from_the_saved_record(
    evidence: tuple[Stores, dict[str, Any]],
) -> None:
    from bookscan import baseline_state
    from bookscan.review_facts import Disposition

    stores, value = evidence
    record = baseline_state.initial(stores, value)
    start = baseline_state.restore(stores, record)
    record, state = acted(
        stores,
        record,
        Disposition(shown(start, 0, "full", "r-1"), "skew-nonzero", "reject", "n"),
        2,
    )
    saved = copy.deepcopy(record)
    state.review["retries"].clear()
    state.base.imported["occurrences"][0]["id"] = "changed"
    state.base.snapshot["limitation"] = "changed"
    assert record == saved
    moved = baseline_state.act(
        stores,
        record,
        Disposition(shown(state, 1, "full", "r-2"), "skew-nonzero", "reject", "n"),
        checkpoint_revision=3,
    )
    assert moved.state is not None and moved.state is not record
    cast(dict[str, Any], moved.state["review"])["retries"].clear()
    cast(dict[str, Any], moved.state["snapshot"])["limitation"] = "changed"
    assert record == saved
    assert moved.facts.snapshot["limitation"] != "changed"
