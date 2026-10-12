"""Public receipt actions: disposition, inspected and acknowledge over saved projects.

Packets are written by the test (descriptor store plus plain files) because the
packet writer is separate work; the command under test reads only what a real
packet would leave: the immutable project descriptor and the receipt file beside
its packet's other files. Replay-before-currency, single-use receipts and the
committed fact under signals are asserted on saved bytes, not on return values.
"""

import hashlib
import json
import os
import signal
import subprocess
import sys
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import Any, cast

import pytest
from test_baseline_state import evidence as evidence
from test_baseline_state import owner as owner

from bookscan import (
    baseline_state,
    checkpoints,
    finite_status,
    ownership,
    project_header,
    review_facts,
)
from bookscan.finite_protocol import run
from bookscan.packet_receipts import Coverage, Identity, describe, issue
from bookscan.project_header import Stores

type Json = dict[str, Any]


def verify(stores: Stores, value: dict[str, object]) -> None:
    baseline_state.restore(stores, value)


@pytest.fixture
def project(evidence: tuple[Stores, Json]) -> Path:  # noqa: F811
    stores, data = evidence
    state = baseline_state.initial(stores, data)

    def verified(value: dict[str, object]) -> None:
        baseline_state.restore(stores, value)

    stores.checkpoints.commit(state, expected=None, verify_state=verified)
    path = stores.owner.path
    stores.owner.close()
    return path


def bytes_at(path: Path) -> dict[str, str]:
    return {
        str(item.relative_to(path)): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in path.rglob("*")
        if item.is_file()
    }


def issue_views(path: Path, destination: Path, page: int = 0) -> dict[str, Path]:
    """Publish a views descriptor for one occurrence and write its plain packet files."""
    with project_header.resume(path, verify_state=verify) as (stores, checkpoint):
        state = baseline_state.restore(stores, checkpoint.state)
        identity = Identity(
            state.project_id,
            cast(str, checkpoint.state["snapshot"]["source_sha256"]),  # type: ignore[index]
            state.review_revision,
            state.snapshot_id,
        )
        common: dict[str, Any] = {
            "occurrence_id": state.occurrences[page].core.id,
            "source_pdf_page": page + 1,
            "image_revision": state.image_revisions[page],
            "box": "MediaBox (CropBox guide)",
        }
        plan = [
            ("receipts/full.json", Coverage("full", scale="0.24 point per pixel", **common)),
            (
                "receipts/native-001.json",
                Coverage("native", regions=("native-001",), scale="1 point per pixel", **common),
            ),
            (
                "receipts/native-002.json",
                Coverage("native", regions=("native-002",), scale="1 point per pixel", **common),
            ),
        ]
        item = issue(identity, "views", plan)
        files = {receipt.path: receipt.raw() for receipt in item.receipts}
        files["index.pdf"] = b"%PDF-index"
        stores.packets.publish(describe(item, files, []))
    destination.mkdir()
    for name, data in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return {name: destination / name for name in files}


def issue_summary(path: Path, destination: Path) -> Path:
    with project_header.resume(path, verify_state=verify) as (stores, checkpoint):
        state = baseline_state.restore(stores, checkpoint.state)
        identity = Identity(
            state.project_id,
            cast(str, checkpoint.state["snapshot"]["source_sha256"]),  # type: ignore[index]
            state.review_revision,
            state.snapshot_id,
        )
        coverage = Coverage(
            "summary",
            box="Whole export snapshot",
            scale="not applicable",
            unresolved_sha256=review_facts.unresolved_digest(state.facts),
            inspection_sha256=review_facts.inspection_digest(state.facts),
        )
        item = issue(identity, "summary", [("receipt.json", coverage)])
        files = {"receipt.json": item.receipts[0].raw()}
        stores.packets.publish(describe(item, files, []))
    destination.mkdir()
    (destination / "receipt.json").write_bytes(files["receipt.json"])
    return destination / "receipt.json"


def invoke(*args: str, json_mode: bool = True) -> tuple[int, Json | str, str]:
    out, err = StringIO(), StringIO()
    code = run(["baseline", *args, *(["--json"] if json_mode else [])], out, err)
    text = out.getvalue()
    return code, (json.loads(text) if json_mode and text else text), err.getvalue()


def disposition(
    path: Path,
    receipt: Path,
    reason: str = "orientation-unverified",
    decision: str = "retain-unresolved",
    note: str = "Retain the baseline",
) -> tuple[int, Json, str]:
    code, record, err = invoke(
        "disposition",
        str(path),
        "--receipt",
        str(receipt),
        "--reason",
        reason,
        "--decision",
        decision,
        "--note",
        note,
    )
    return code, cast(Json, record), err


def inspected(
    path: Path, receipt: Path, scope: str = "full", scale: str = "Fit page"
) -> tuple[int, Json, str]:
    code, record, err = invoke(
        "inspected",
        str(path),
        "--receipt",
        str(receipt),
        "--scope",
        scope,
        "--viewer",
        "Preview",
        "--scale",
        scale,
        "--note",
        "Looked at it",
    )
    return code, cast(Json, record), err


def acknowledged(path: Path, receipt: Path, *selection: str) -> tuple[int, Json, str]:
    scope = [x for page in selection for x in ("--page", page)] or ["--all"]
    code, record, err = invoke(
        "acknowledge", str(path), "--receipt", str(receipt), *scope, "--note", "Export as is"
    )
    return code, cast(Json, record), err


def saved(path: Path) -> Json:
    return finite_status.status(path)


# --- recording ------------------------------------------------------------------------


def test_disposition_records_one_durable_decision_and_advances_review(
    project: Path, tmp_path: Path
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    before = saved(project)
    code, record, err = disposition(project, receipts["receipts/full.json"])
    assert code == 0 and err == ""
    assert record["schema"] == "BookScanBuilderCommandResult" and record["schema_version"] == 1
    assert (record["operation"], record["status"], record["exit_code"]) == (
        "baseline.disposition",
        "recorded",
        0,
    )
    assert (record["committed"], record["replayed"], record["output"]) == (True, False, None)
    assert record["checkpoint_revision"] == 2 and record["warnings"] == []
    assert record["project_id"] == before["project_id"]
    assert record["review_revision"] != before["review_revision"]
    assert record["review_revision"] == record["current_review_revision"]
    assert record["affected_ids"] == ["occ-000001"]
    assert record["detail"]["reason"] == "orientation-unverified"
    after = saved(project)
    assert after["checkpoint_revision"] == 2
    assert after["review_revision"] == record["review_revision"]
    assert after["snapshot_id"] == record["snapshot_id"]
    assert after["pages"][0]["dispositions"] == [
        {
            "reason": "orientation-unverified",
            "decision": "retain-unresolved",
            "note": "Retain the baseline",
        }
    ]
    assert after["pages"][1]["dispositions"] == []


def test_human_success_prints_one_line_on_stdout_and_nothing_on_stderr(
    project: Path, tmp_path: Path
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    out, err = StringIO(), StringIO()
    code = run(
        [
            "baseline",
            "disposition",
            str(project),
            "--receipt",
            str(receipts["receipts/full.json"]),
            "--reason",
            "orientation-unverified",
            "--decision",
            "retain-unresolved",
            "--note",
            "Keep",
        ],
        out,
        err,
    )
    assert code == 0 and err.getvalue() == ""
    assert out.getvalue().count("\n") == 1 and "occ-000001" in out.getvalue()
    assert "checkpoint 2" in out.getvalue()


def test_identical_retry_replays_the_original_result_without_files_or_currency(
    project: Path, tmp_path: Path
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    raw = receipts["receipts/full.json"].read_bytes()
    first = disposition(project, receipts["receipts/full.json"])[1]
    stale = inspected(project, receipts["receipts/native-001.json"], scope="native")
    assert stale[0] == 6 and stale[1]["code"] == "STALE_ACTION"
    fresh = issue_views(project, tmp_path / "fresh")
    newest = inspected(project, fresh["receipts/full.json"])[1]
    assert newest["checkpoint_revision"] == 3
    # Only the receipt file itself survives: every other packet file is gone.
    for item in receipts.values():
        item.unlink()
    receipts["receipts/full.json"].write_bytes(raw)
    before = bytes_at(project)
    code, again, err = disposition(project, receipts["receipts/full.json"])
    assert code == 0 and err == ""
    assert again["replayed"] is True and again["committed"] is True
    assert again["checkpoint_revision"] == first["checkpoint_revision"] == 2
    assert again["review_revision"] == first["review_revision"]
    assert again["current_review_revision"] == newest["review_revision"]
    assert again["current_review_revision"] != first["review_revision"]
    assert bytes_at(project) == before


def test_conflicting_reuse_is_receipt_used_and_commits_nothing(
    project: Path, tmp_path: Path
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    assert disposition(project, receipts["receipts/full.json"])[0] == 0
    before = bytes_at(project)
    code, record, err = disposition(
        project, receipts["receipts/full.json"], note="A different note"
    )
    assert code == 6 and record["code"] == "INVALID_RECEIPT"
    assert record["context"]["receipt"] == "receipt-used"
    assert (record["committed"], record["status"]) == (False, "error")
    assert record["remediation"] and err == ""
    assert bytes_at(project) == before


def test_stale_new_action_is_refused_and_a_refreshed_packet_succeeds(
    project: Path, tmp_path: Path
) -> None:
    first = issue_views(project, tmp_path / "one")
    second = issue_views(project, tmp_path / "two")
    assert disposition(project, first["receipts/full.json"])[0] == 0
    before = bytes_at(project)
    code, record, _ = inspected(project, second["receipts/full.json"])
    assert code == 6 and record["code"] == "STALE_ACTION" and record["committed"] is False
    assert "bookscan baseline views" in record["remediation"]
    assert bytes_at(project) == before
    refreshed = issue_views(project, tmp_path / "three")
    assert inspected(project, refreshed["receipts/full.json"])[0] == 0


# --- argument and receipt faults -------------------------------------------------------


def test_forbidden_or_unknown_reason_is_refused_before_any_read(tmp_path: Path) -> None:
    missing = tmp_path / "No such project"
    for reason, decision in (
        ("orientation-unverified", "reject"),
        ("assessment-unavailable", "reject"),
        ("invented-reason", "retain-unresolved"),
    ):
        code, record, err = disposition(missing, tmp_path / "none.json", reason, decision)
        assert code == 2 and record["code"] == "INVALID_ARGUMENT", record
        assert record["operation"] == "baseline.disposition" and record["committed"] is False
        assert "bookscan baseline disposition" in record["remediation"]
        assert err == ""
    assert not missing.exists()


def test_blank_note_and_viewer_are_invalid_arguments_before_any_read(tmp_path: Path) -> None:
    code, record, _ = disposition(tmp_path / "x", tmp_path / "y.json", note="   ")
    assert code == 2 and record["code"] == "INVALID_ARGUMENT"
    code, record, _ = invoke(
        "inspected",
        str(tmp_path / "x"),
        "--receipt",
        str(tmp_path / "y.json"),
        "--scope",
        "full",
        "--viewer",
        " ",
        "--scale",
        "Fit",
        "--note",
        "N",
    )
    assert code == 2 and cast(Json, record)["code"] == "INVALID_ARGUMENT"


def test_reject_on_a_limitation_that_only_permits_retain_changes_nothing(
    project: Path, tmp_path: Path
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    before = bytes_at(project)
    code, record, _ = disposition(project, receipts["receipts/full.json"], decision="reject")
    assert code == 2 and record["code"] == "INVALID_ARGUMENT"
    assert bytes_at(project) == before


@pytest.mark.parametrize("fault", ["missing", "garbage", "edited", "unknown-packet"])
def test_receipt_file_faults_are_invalid_receipts_and_change_nothing(
    project: Path, tmp_path: Path, fault: str
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    receipt = receipts["receipts/full.json"]
    data = json.loads(receipt.read_bytes())
    if fault == "missing":
        receipt.unlink()
    elif fault == "garbage":
        receipt.write_bytes(b"not json")
    elif fault == "edited":
        data["coverage"]["scale"] = "1 point per pixel"
        receipt.write_text(json.dumps(data))
    else:
        data["packet_id"] = "packet-" + "7" * 32
        receipt.write_text(json.dumps(data))
    before = bytes_at(project)
    code, record, _ = disposition(project, receipt)
    assert code == 6 and record["code"] == "INVALID_RECEIPT" and record["committed"] is False
    assert bytes_at(project) == before


def test_changed_packet_file_blocks_a_new_action_but_not_a_replay(
    project: Path, tmp_path: Path
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    other = issue_views(project, tmp_path / "other")
    other["index.pdf"].write_bytes(b"%PDF-annotated by a viewer")
    before = bytes_at(project)
    code, record, _ = disposition(project, other["receipts/full.json"])
    assert code == 6 and record["context"]["receipt"] == "packet-file-changed"
    assert "annotate" in record["remediation"].lower()
    assert bytes_at(project) == before
    assert disposition(project, receipts["receipts/full.json"])[0] == 0
    receipts["index.pdf"].write_bytes(b"%PDF-edited afterwards")
    assert disposition(project, receipts["receipts/full.json"])[1]["replayed"] is True


def test_a_receipt_copied_out_of_its_packet_cannot_start_a_new_action(
    project: Path, tmp_path: Path
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    copied = tmp_path / "loose receipt.json"
    copied.write_bytes(receipts["receipts/full.json"].read_bytes())
    before = bytes_at(project)
    code, record, _ = disposition(project, copied)
    assert code == 6 and record["context"]["receipt"] == "packet-file-changed"
    assert bytes_at(project) == before


def test_a_receipt_for_another_view_kind_is_wrong_view(project: Path, tmp_path: Path) -> None:
    receipts = issue_views(project, tmp_path / "views")
    summary = issue_summary(project, tmp_path / "summary")
    before = bytes_at(project)
    code, record, _ = disposition(project, summary)
    assert code == 6 and record["context"]["receipt"] == "wrong-view"
    code, record, _ = acknowledged(project, receipts["receipts/full.json"])
    assert code == 6 and record["context"]["receipt"] == "wrong-view"
    assert bytes_at(project) == before


# --- inspection and acknowledgement ----------------------------------------------------


def test_inspection_names_only_the_receipt_region_and_never_a_neighbour(
    project: Path, tmp_path: Path
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    code, record, _ = inspected(
        project, receipts["receipts/native-001.json"], scope="native", scale="Measured 1:1"
    )
    assert code == 0 and record["status"] == "recorded"
    assert record["detail"] == {
        "scope": "native",
        "regions": ["native-001"],
        "viewer": "Preview",
        "scale": "Measured 1:1",
    }
    page = saved(project)["pages"][0]
    assert [r["regions"] for r in page["inspections"]] == [["native-001"]]
    assert saved(project)["pages"][1]["inspections"] == []


def test_scope_must_match_the_receipt_view(project: Path, tmp_path: Path) -> None:
    receipts = issue_views(project, tmp_path / "views")
    before = bytes_at(project)
    code, record, _ = inspected(project, receipts["receipts/full.json"], scope="native")
    assert code == 2 and record["code"] == "INVALID_ARGUMENT"
    assert bytes_at(project) == before


def test_two_summaries_acknowledge_complementary_selections_of_one_snapshot(
    project: Path, tmp_path: Path
) -> None:
    first = issue_summary(project, tmp_path / "summary A")
    second = issue_summary(project, tmp_path / "summary B")
    code, one, _ = acknowledged(project, first, "occ-000001")
    assert code == 0 and one["status"] == "acknowledged"
    assert one["review_revision"] == saved(project)["review_revision"]
    partial = saved(project)["acknowledgement"]
    assert partial["complete"] is False and partial["ids"] == ["occ-000001"]
    code, two, _ = acknowledged(project, second, "occ-000002", "occ-000003")
    assert code == 0 and two["checkpoint_revision"] == 3
    full = saved(project)["acknowledgement"]
    assert full["complete"] is True and full["missing_ids"] == []
    assert two["snapshot_id"] == one["snapshot_id"]
    # Reusing the first receipt for another selection is a conflict, not a union.
    code, record, _ = acknowledged(project, first, "occ-000002")
    assert code == 6 and record["context"]["receipt"] == "receipt-used"


def test_all_pages_acknowledgement_and_later_review_fact_invalidates_it(
    project: Path, tmp_path: Path
) -> None:
    summary = issue_summary(project, tmp_path / "summary")
    assert acknowledged(project, summary)[0] == 0
    assert saved(project)["acknowledgement"]["complete"] is True
    views = issue_views(project, tmp_path / "views")
    assert saved(project)["acknowledgement"] is not None
    assert disposition(project, views["receipts/full.json"])[0] == 0
    assert saved(project)["acknowledgement"] is None


def test_unknown_page_in_a_selection_is_an_invalid_argument(project: Path, tmp_path: Path) -> None:
    summary = issue_summary(project, tmp_path / "summary")
    before = bytes_at(project)
    code, record, _ = acknowledged(project, summary, "occ-999999")
    assert code == 2 and record["code"] == "INVALID_ARGUMENT"
    assert bytes_at(project) == before


# --- ownership, signals and data ---------------------------------------------------------


def test_busy_project_is_four_and_nothing_is_committed(project: Path, tmp_path: Path) -> None:
    receipts = issue_views(project, tmp_path / "views")
    header = project_header.Header.from_json((project / "project.json").read_bytes())
    with ownership.Writer.acquire(project, header.lock):
        code, record, _ = disposition(project, receipts["receipts/full.json"])
        assert code == 4 and record["code"] == "PROJECT_BUSY" and record["committed"] is False
    assert disposition(project, receipts["receipts/full.json"])[0] == 0


def test_signal_after_the_checkpoint_commit_keeps_the_committed_fact(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    from bookscan import finite_action

    real = finite_action.apply

    def signalled(*args: Any, **kwargs: Any) -> Any:
        applied = real(*args, **kwargs)
        os.kill(os.getpid(), signal.SIGTERM)
        return applied

    monkeypatch.setattr(finite_action, "apply", signalled)
    code, record, _ = disposition(project, receipts["receipts/full.json"])
    assert code == 143 and record["code"] == "INTERRUPTED" and record["status"] == "error"
    assert record["committed"] is True and record["checkpoint_revision"] == 2
    assert saved(project)["checkpoint_revision"] == 2
    monkeypatch.undo()
    replay = disposition(project, receipts["receipts/full.json"])[1]
    assert replay["replayed"] is True and replay["checkpoint_revision"] == 2


def test_signal_before_the_pointer_commit_leaves_the_prior_checkpoint(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    real = checkpoints.Checkpoints.commit

    def signalled(self: checkpoints.Checkpoints, *args: Any, **kwargs: Any) -> Any:
        os.kill(os.getpid(), signal.SIGINT)
        return real(self, *args, **kwargs)

    monkeypatch.setattr(checkpoints.Checkpoints, "commit", signalled)
    before = bytes_at(project)
    code, record, _ = disposition(project, receipts["receipts/full.json"])
    assert code == 130 and record["code"] == "INTERRUPTED" and record["committed"] is False
    assert bytes_at(project) == before
    monkeypatch.undo()
    assert disposition(project, receipts["receipts/full.json"])[1]["replayed"] is False


@pytest.mark.parametrize("value", ["--help", "--json", "-x"])
def test_note_text_that_looks_like_an_option_is_recorded_as_data(
    project: Path, tmp_path: Path, value: str
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    out, err = StringIO(), StringIO()
    code = run(
        [
            "baseline",
            "disposition",
            str(project),
            "--receipt",
            str(receipts["receipts/full.json"]),
            "--reason",
            "orientation-unverified",
            "--decision",
            "retain-unresolved",
            "--note",
            value,
            "--json",
        ],
        out,
        err,
    )
    assert code == 0, (out.getvalue(), err.getvalue())
    assert json.loads(out.getvalue())["status"] == "recorded"
    with project_header.resume(project, verify_state=verify) as (_, checkpoint):
        notes = [r["note"] for r in cast(Json, checkpoint.state["review"])["dispositions"]]
    assert notes == [value]


def test_action_never_launches_a_native_tool(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts = issue_views(project, tmp_path / "views")

    def denied(*args: object, **kwargs: object) -> None:
        raise PermissionError("observed denied native launch")

    monkeypatch.setattr(subprocess, "Popen", denied)
    with pytest.raises(PermissionError, match="observed denied"):
        subprocess.Popen(["denied-control"])
    assert disposition(project, receipts["receipts/full.json"])[0] == 0


# --- shared state boundary for a second front end --------------------------------------


def test_apply_runs_under_caller_held_ownership_and_replays_a_request_id(
    project: Path,
) -> None:
    from bookscan import finite_action

    header = project_header.Header.from_json((project / "project.json").read_bytes())
    with project_header.resume(project, verify_state=verify) as (stores, checkpoint):
        state = baseline_state.restore(stores, checkpoint.state)
        shown = review_facts.Displayed(
            "browser-request-1",
            state.project_id,
            state.review_revision,
            state.snapshot_id,
            "full",
            state.occurrences[0].core.id,
            state.image_revisions[0],
        )
        action = review_facts.Disposition(
            shown, "orientation-unverified", "retain-unresolved", "From a browser"
        )
        with pytest.raises(ownership.OwnershipError) as busy:
            ownership.Writer.acquire(project, header.lock)
        assert busy.value.code == "PROJECT_BUSY"
        applied = finite_action.apply(stores, checkpoint, action)
        assert applied.replayed is False and applied.checkpoint is not None
        assert applied.checkpoint.revision == 2
        assert applied.result["status"] == "recorded"
        again = finite_action.apply(stores, applied.checkpoint, action)
        assert again.replayed is True and again.checkpoint is None
        assert again.result == applied.result
        stores.verify()


# --- installed command -----------------------------------------------------------------


def test_installed_command_records_a_disposition_and_a_second_process_replays(
    project: Path, tmp_path: Path
) -> None:
    receipts = issue_views(project, tmp_path / "Page views")
    command: Callable[[], subprocess.CompletedProcess[str]] = lambda: subprocess.run(  # noqa: E731
        [
            sys.executable,
            "-m",
            "bookscan.cli",
            "baseline",
            "disposition",
            str(project),
            "--receipt",
            str(receipts["receipts/full.json"]),
            "--reason",
            "orientation-unverified",
            "--decision",
            "retain-unresolved",
            "--note",
            "Installed note",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    first, second = command(), command()
    assert first.returncode == 0, first.stderr
    one, two = json.loads(first.stdout), json.loads(second.stdout)
    assert (one["replayed"], two["replayed"]) == (False, True)
    assert one["checkpoint_revision"] == two["checkpoint_revision"] == 2
    assert first.stdout.count("\n") == 1 and first.stderr == ""


# --- receipts that are well formed but not this project's ------------------------------


def _forged(project: Path, real: Path, **changes: Any) -> bytes:
    """A self-consistent receipt for the real packet ID that its descriptor never listed."""
    from dataclasses import replace

    from bookscan.packet_receipts import Receipt, _receipt_id  # type: ignore[attr-defined]

    receipt = Receipt.parse(real.read_bytes())
    identity = replace(receipt.identity, **changes.get("identity", {}))
    coverage = replace(receipt.coverage, **changes.get("coverage", {}))
    forged = replace(
        receipt,
        receipt_id=_receipt_id(receipt.packet_id, identity, coverage),
        identity=identity,
        coverage=coverage,
    )
    return forged.raw()


@pytest.mark.parametrize(
    ("kind", "changes"),
    [
        ("other-occurrence", {"coverage": {"occurrence_id": "occ-000002", "source_pdf_page": 2}}),
        ("other-project", {"identity": {"project_id": "project-" + "9" * 32}}),
        ("other-source", {"identity": {"source_sha256": "e" * 64}}),
    ],
)
def test_self_consistent_receipt_that_the_descriptor_never_listed_is_foreign(
    project: Path, tmp_path: Path, kind: str, changes: dict[str, Any]
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    receipts["receipts/full.json"].write_bytes(
        _forged(project, receipts["receipts/full.json"], **changes)
    )
    before = bytes_at(project)
    code, record, _ = disposition(project, receipts["receipts/full.json"])
    assert code == 6 and record["code"] == "INVALID_RECEIPT", kind
    assert record["context"]["receipt"] == "foreign" and record["committed"] is False
    assert bytes_at(project) == before


def test_a_faithful_copy_of_the_whole_packet_is_the_same_packet(
    project: Path, tmp_path: Path
) -> None:
    import shutil

    receipts = issue_views(project, tmp_path / "views")
    copy = tmp_path / "A copy of the views"
    shutil.copytree(receipts["index.pdf"].parent, copy)
    code, record, _ = disposition(project, copy / "receipts" / "full.json")
    assert code == 0 and record["checkpoint_revision"] == 2


def test_a_loose_receipt_inside_the_packet_tree_is_not_at_its_issued_location(
    project: Path, tmp_path: Path
) -> None:
    receipts = issue_views(project, tmp_path / "packet")
    loose = tmp_path / "packet" / "sub" / "copy.json"
    loose.parent.mkdir()
    loose.write_bytes(receipts["receipts/full.json"].read_bytes())
    before = bytes_at(project)
    code, record, _ = disposition(project, loose)
    assert code == 6 and record["context"]["receipt"] == "packet-file-changed"
    assert bytes_at(project) == before


def test_receipt_paths_that_are_not_ordinary_small_files_never_block_or_commit(
    project: Path, tmp_path: Path
) -> None:
    before = bytes_at(project)
    big = tmp_path / "big.json"
    big.write_bytes(b" " * ((1 << 20) + 1))
    fifo = tmp_path / "fifo.json"
    os.mkfifo(fifo)
    exact = tmp_path / "exact.json"
    exact.write_bytes(b" " * (1 << 20))
    for item in (tmp_path, big, fifo, exact):
        code, record, _ = disposition(project, item)
        assert code == 6 and record["code"] == "INVALID_RECEIPT", item
        assert record["context"]["receipt"] == "malformed"
    assert bytes_at(project) == before


# --- delivery, warnings and failure mapping ----------------------------------------------


class Closed(StringIO):
    def write(self, text: str, /) -> int:
        raise BrokenPipeError("closed")


def test_closed_stdout_keeps_the_committed_fact_and_reports_delivery_once(
    project: Path, tmp_path: Path
) -> None:
    from bookscan.finite_protocol import Delivery

    receipts = issue_views(project, tmp_path / "views")
    err, delivery = StringIO(), Delivery()
    code = run(
        [
            "baseline",
            "disposition",
            str(project),
            "--receipt",
            str(receipts["receipts/full.json"]),
            "--reason",
            "orientation-unverified",
            "--decision",
            "retain-unresolved",
            "--note",
            "N",
            "--json",
        ],
        Closed(),
        err,
        delivery=delivery,
    )
    assert code == 5 and delivery.failed is True
    assert err.getvalue().count("RESULT_DELIVERY_FAILED") == 1
    assert saved(project)["checkpoint_revision"] == 2


def test_cleanup_warning_after_commit_is_reported_without_failing_the_action(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    real = checkpoints.Checkpoints.commit

    def warned(self: checkpoints.Checkpoints, *args: Any, **kwargs: Any) -> Any:
        done = real(self, *args, **kwargs)
        return checkpoints.CommitResult(done.checkpoint, warnings=("CHECKPOINT_CLEANUP_FAILED: x",))

    monkeypatch.setattr(checkpoints.Checkpoints, "commit", warned)
    out, err = StringIO(), StringIO()
    code = run(
        [
            "baseline",
            "disposition",
            str(project),
            "--receipt",
            str(receipts["receipts/full.json"]),
            "--reason",
            "orientation-unverified",
            "--decision",
            "retain-unresolved",
            "--note",
            "N",
            "--json",
        ],
        out,
        err,
    )
    assert code == 0
    record = json.loads(out.getvalue())
    assert [w["code"] for w in record["warnings"]] == ["CHECKPOINT_CLEANUP_FAILED"]
    assert record["warnings"][0]["message"] == "x" and record["committed"] is True
    assert err.getvalue().startswith("CHECKPOINT_CLEANUP_FAILED: x")


def test_damaged_saved_project_is_invalid_project_with_the_recovery_remedy(
    project: Path, tmp_path: Path
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    next((project / "assets").glob("*.png")).unlink()
    code, record, _ = disposition(project, receipts["receipts/full.json"])
    assert code == 3 and record["code"] == "INVALID_PROJECT" and record["committed"] is False
    assert "bookscan baseline create" in record["remediation"]
    assert "review facts" in record["remediation"]


@pytest.mark.parametrize("failure", ["write-failed", "oserror"])
def test_commit_failures_are_exit_five_with_the_storage_remedy(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    receipts = issue_views(project, tmp_path / "views")

    def broken(self: checkpoints.Checkpoints, *args: Any, **kwargs: Any) -> Any:
        if failure == "oserror":
            raise OSError(28, "No space left on device")
        raise checkpoints.CheckpointError("WRITE_FAILED", "Cannot commit checkpoint.", 5)

    monkeypatch.setattr(checkpoints.Checkpoints, "commit", broken)
    before = bytes_at(project)
    code, record, _ = disposition(project, receipts["receipts/full.json"])
    assert code == 5 and record["code"] == "WRITE_FAILED" and record["committed"] is False
    assert "permissions" in record["remediation"]
    assert "create" not in record["remediation"]
    assert bytes_at(project) == before


def test_error_after_commit_names_the_committed_fact_and_a_verify_remedy(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts = issue_views(project, tmp_path / "views")
    real = checkpoints.Checkpoints.commit

    def late(self: checkpoints.Checkpoints, *args: Any, **kwargs: Any) -> Any:
        real(self, *args, **kwargs)
        raise checkpoints.CheckpointError("WRITE_FAILED", "Late failure.", 5, True)

    monkeypatch.setattr(checkpoints.Checkpoints, "commit", late)
    code, record, _ = disposition(project, receipts["receipts/full.json"])
    assert code == 5 and record["committed"] is True
    assert record["context"]["phase"] == "after-checkpoint"
    assert "bookscan baseline status" in record["remediation"]
    assert record["project_id"] is None and "checkpoint_revision" not in record
    assert saved(project)["checkpoint_revision"] == 2


def test_signal_after_commit_remedy_says_to_verify(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import finite_action

    receipts = issue_views(project, tmp_path / "views")
    real = finite_action.apply

    def signalled(*args: Any, **kwargs: Any) -> Any:
        applied = real(*args, **kwargs)
        os.kill(os.getpid(), signal.SIGINT)
        return applied

    monkeypatch.setattr(finite_action, "apply", signalled)
    code, record, _ = disposition(project, receipts["receipts/full.json"])
    assert code == 130 and record["context"]["phase"] == "after-checkpoint"
    assert "bookscan baseline status" in record["remediation"]
    assert record["review_revision"] == saved(project)["review_revision"]
    assert record["project_id"] == saved(project)["project_id"]
    assert record["affected_ids"] == ["occ-000001"]
