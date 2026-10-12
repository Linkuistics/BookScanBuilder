"""Public status must verify saved bytes; a header or pointer alone cannot pass.

The constructed RGB fixture tests persistence, never rendering fidelity. Installed
processes must keep every occurrence/reason and cannot regenerate source-lost RGB.
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

from bookscan import baseline_state, ownership, project_header
from bookscan.finite_protocol import run
from bookscan.project_header import Stores


@pytest.fixture
def project(evidence: tuple[Stores, dict[str, Any]]) -> tuple[Path, dict[str, Any]]:  # noqa: F811
    stores, data = evidence
    state = baseline_state.initial(stores, data)

    def verify(value: dict[str, object]) -> None:
        baseline_state.restore(stores, value)

    stores.checkpoints.commit(state, expected=None, verify_state=verify)
    path = stores.owner.path
    stores.owner.close()
    return path, state


def invoke(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bookscan.cli", "baseline", "status", str(path), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


def bytes_at(path: Path) -> dict[str, str]:
    return {
        str(item.relative_to(path)): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in path.rglob("*")
        if item.is_file()
    }


def test_installed_status_reports_complete_uninspected_source_lost_roster(
    project: tuple[Path, dict[str, Any]],
) -> None:
    path, state = project
    before = bytes_at(path)
    result = invoke(path, "--json")
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout)
    assert result.stderr == "" and result.stdout.count("\n") == 1
    assert record["schema"] == "BookScanBuilderCommandResult"
    assert record["schema_version"] == 1
    assert (record["operation"], record["status"], record["exit_code"]) == (
        "baseline.status",
        "verified",
        0,
    )
    assert record["project_id"] == state["project_id"]
    assert (
        record["review_revision"] == record["current_review_revision"] == state["review_revision"]
    )
    assert record["snapshot_id"] == state["snapshot_id"]
    assert record["checkpoint_revision"] == 1
    assert record["committed"] is False and record["replayed"] is False
    assert record["output"] is None and record["warnings"] == []
    pages = record["pages"]
    assert [p["id"] for p in pages] == ["occ-000001", "occ-000002", "occ-000003"]
    assert [p["source_pdf_page"] for p in pages] == [1, 2, 3]
    assert pages[0]["image_sha256"] == pages[1]["image_sha256"]
    assert pages[2]["geometry"]["pixels"] == [10, 5]
    assert [p["image_revision"] for p in pages] == state["image_revisions"]
    assert all(p["inspections"] == [] and p["dispositions"] == [] for p in pages)
    assert all(p["retention"] == "baseline-retained/unresolved" for p in pages)
    assert all(p["side"] == "unknown" and p["half"] is None for p in pages)
    assert all("orientation-unverified" in [r["id"] for r in p["triage_reasons"]] for p in pages)
    assert all("Within-page" in p["limitation"] for p in pages)
    assert record["acknowledgement"] is None
    assert "Historical" in record["limitations"][0]
    assert bytes_at(path) == before


def test_human_roster_keeps_every_identity_and_limitation(
    project: tuple[Path, dict[str, Any]],
) -> None:
    result = invoke(project[0])
    assert result.returncode == 0 and result.stderr == ""
    assert all(name in result.stdout for name in ("occ-000001", "occ-000002", "occ-000003"))
    assert "orientation-unverified" in result.stdout and "Within-page" in result.stdout
    assert "uninspected" in result.stdout and "No export acknowledgement" in result.stdout


@pytest.mark.parametrize("fault", ["source", "rgb", "native", "current", "header", "capability"])
def test_damaged_saved_content_fails_without_mutation(
    project: tuple[Path, dict[str, Any]],
    fault: str,
) -> None:
    path, _ = project
    if fault == "capability":
        header = path / "project.json"
        data = json.loads(header.read_bytes())
        data["required_capabilities"].append("future-unknown")
        header.write_text(json.dumps(data))
    else:
        target = {
            "source": path / "source.pdf",
            "rgb": next((path / "assets").glob("*.png")),
            "native": next((path / "native-blobs").glob("*")),
            "current": path / "checkpoints" / "current",
            "header": path / "project.json",
        }[fault]
        target.unlink()
    before = bytes_at(path)
    result = invoke(path, "--json")
    assert result.returncode == 3, result.stderr
    record = json.loads(result.stdout)
    assert record["code"] == "INVALID_PROJECT" and record["operation"] == "baseline.status"
    assert record["status"] == "error" and record["committed"] is False
    assert "bookscan baseline create" in record["remediation"]
    assert "review facts" in record["remediation"]
    assert bytes_at(path) == before


def test_busy_is_four_and_canonical_alias_reaches_same_project(
    project: tuple[Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    path, _ = project
    alias = tmp_path / "linked parent"
    alias.symlink_to(path.parent, target_is_directory=True)
    alternate = alias / path.name.swapcase()
    header = project_header.Header.from_json((path / "project.json").read_bytes())
    with ownership.Writer.acquire(path, header.lock):
        result = invoke(alternate, "--json")
        assert result.returncode == 4, result.stderr
        assert json.loads(result.stdout)["code"] == "PROJECT_BUSY"
    assert invoke(alternate, "--json").returncode == 0


def test_status_without_output_does_not_launch_native_tools(
    project: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise PermissionError("observed denied native launch")

    monkeypatch.setattr(subprocess, "Popen", denied)
    with pytest.raises(PermissionError, match="observed denied"):
        subprocess.Popen(["denied-control"])
    output, error = StringIO(), StringIO()
    assert run(["baseline", "status", str(project[0]), "--json"], output, error) == 0
    assert json.loads(output.getvalue())["status"] == "verified"


def test_summary_option_does_not_fabricate_packet_or_verified_success(
    project: tuple[Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "summary"
    result = invoke(project[0], "--output", str(output), "--json")
    assert result.returncode == 2
    assert json.loads(result.stdout)["code"] == "COMMAND_UNAVAILABLE"
    assert not output.exists()


def test_corrupt_predecessor_is_not_hidden_by_a_good_current_checkpoint(
    evidence: tuple[Stores, dict[str, Any]],  # noqa: F811
) -> None:
    stores, data = evidence
    state = baseline_state.initial(stores, data)

    def verify(value: dict[str, object]) -> None:
        baseline_state.restore(stores, value)

    first = stores.checkpoints.commit(state, expected=None, verify_state=verify).checkpoint
    stores.checkpoints.commit(state, expected=first, verify_state=verify)
    path = stores.owner.path
    stores.owner.close()
    (path / "checkpoints" / (first.sha256 + ".json")).unlink()
    before = bytes_at(path)
    result = invoke(path, "--json")
    assert result.returncode == 3
    assert json.loads(result.stdout)["code"] == "INVALID_PROJECT"
    assert bytes_at(path) == before


def test_coherent_bad_predecessor_cannot_borrow_current_state_validity(
    evidence: tuple[Stores, dict[str, Any]],  # noqa: F811
) -> None:
    import copy

    stores, data = evidence
    state = baseline_state.initial(stores, data)
    bad = copy.deepcopy(state)
    bad["format"] = "unknown-semantic-format"
    # Both pointer/envelope hashes are valid; only complete predecessor semantics
    # can distinguish this history from a valid initial-retention history.
    first = stores.checkpoints.commit(
        bad, expected=None, verify_state=lambda value: None
    ).checkpoint
    stores.checkpoints.commit(state, expected=first, verify_state=lambda value: None)
    path = stores.owner.path
    stores.owner.close()
    before = bytes_at(path)
    result = invoke(path, "--json")
    assert result.returncode == 3
    assert json.loads(result.stdout)["code"] == "INVALID_PROJECT"
    assert bytes_at(path) == before


def test_coherently_hashed_nonempty_review_is_not_silently_discarded(
    evidence: tuple[Stores, dict[str, Any]],  # noqa: F811
) -> None:
    stores, data = evidence
    state = baseline_state.initial(stores, data)
    state["review"]["inspections"] = [{"unverified": True}]  # type: ignore[index]
    # Simulate a foreign writer's coherent envelope, without the semantic reader.
    stores.checkpoints.commit(state, expected=None, verify_state=lambda value: None)
    path = stores.owner.path
    stores.owner.close()
    result = invoke(path, "--json")
    assert result.returncode == 3
    assert json.loads(result.stdout)["code"] == "INVALID_PROJECT"


class BrokenOutput(StringIO):
    def write(self, value: str) -> int:
        raise BrokenPipeError("consumer closed")


def test_status_delivery_failure_is_five_and_selected_project_error_is_three(
    project: tuple[Path, dict[str, Any]],
) -> None:
    errors = StringIO()
    assert run(["baseline", "status", str(project[0]), "--json"], BrokenOutput(), errors) == 5
    assert errors.getvalue().count("RESULT_DELIVERY_FAILED") == 1
    (project[0] / "source.pdf").unlink()
    assert run(["baseline", "status", str(project[0]), "--json"], BrokenOutput(), errors) == 3


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_signal_during_selected_result_delivery_never_replaces_it(
    project: tuple[Path, dict[str, Any]],
    sig: signal.Signals,
) -> None:
    class SignallingOutput(StringIO):
        def write(self, value: str) -> int:
            os.kill(os.getpid(), sig)
            return super().write(value)

    output, errors = SignallingOutput(), StringIO()
    assert run(["baseline", "status", str(project[0]), "--json"], output, errors) == 0
    assert json.loads(output.getvalue())["status"] == "verified"
    (project[0] / "source.pdf").unlink()
    output = SignallingOutput()
    assert run(["baseline", "status", str(project[0]), "--json"], output, errors) == 3
    assert json.loads(output.getvalue())["code"] == "INVALID_PROJECT"


def test_signal_before_success_serialization_finishes_is_interrupted(
    project: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import finite_status

    real = json.dumps

    def interrupted(value: Any, *args: Any, **kwargs: Any) -> str:
        if isinstance(value, dict) and cast(dict[str, object], value).get("status") == "verified":
            os.kill(os.getpid(), signal.SIGTERM)
        return real(value, *args, **kwargs)

    monkeypatch.setattr(finite_status.json, "dumps", interrupted)
    output, errors = StringIO(), StringIO()
    assert run(["baseline", "status", str(project[0]), "--json"], output, errors) == 143
    assert json.loads(output.getvalue())["code"] == "INTERRUPTED"


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_read_signal_keeps_130_143_no_commit_and_releases_ownership(
    project: tuple[Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    sig: signal.Signals,
) -> None:
    real = baseline_state.restore
    fired = False

    def interrupted(*args: Any, **kwargs: Any) -> baseline_state.InitialState:
        nonlocal fired
        if not fired:
            fired = True
            os.kill(os.getpid(), sig)
        return real(*args, **kwargs)

    monkeypatch.setattr(baseline_state, "restore", interrupted)
    before = bytes_at(project[0])
    output, error = StringIO(), StringIO()
    assert run(["baseline", "status", str(project[0]), "--json"], output, error) == 128 + sig
    record = json.loads(output.getvalue())
    assert record["code"] == "INTERRUPTED" and record["committed"] is False
    assert bytes_at(project[0]) == before
    monkeypatch.setattr(baseline_state, "restore", real)
    assert invoke(project[0], "--json").returncode == 0


@pytest.mark.parametrize("selection", [None, ("occ-000001",)])
def test_status_reports_replayed_review_facts_from_the_saved_history_alone(
    evidence: tuple[Stores, dict[str, Any]],  # noqa: F811
    selection: tuple[str, ...] | None,
) -> None:
    from test_baseline_state import shown

    from bookscan.review_facts import Acknowledgement, Action, Disposition, Inspection

    stores, data = evidence
    record = baseline_state.initial(stores, data)

    def verify(value: dict[str, object]) -> None:
        baseline_state.restore(stores, value)

    current = stores.checkpoints.commit(record, expected=None, verify_state=verify).checkpoint
    seen = baseline_state.restore(stores, record)
    makers: list[Callable[[Any], Action]] = [
        lambda s: Disposition(shown(s, 0, "full", "r-1"), "skew-nonzero", "reject", "flat"),
        lambda s: Inspection(shown(s, 1, "native", "r-2"), "native", "Preview", "1:1", "ok"),
        lambda s: Acknowledgement(shown(s, 0, "full", "r-3", summary=True), "all", selection),
    ]
    for number, make in enumerate(makers, start=2):
        moved = baseline_state.act(stores, record, make(seen), checkpoint_revision=number)
        assert moved.state is not None
        record = moved.state
        current = stores.checkpoints.commit(
            record, expected=current, verify_state=verify
        ).checkpoint
        seen = baseline_state.restore(stores, record)
    path = stores.owner.path
    stores.owner.close()
    before = bytes_at(path)
    result = invoke(path, "--json")
    assert result.returncode == 0, result.stderr
    status = json.loads(result.stdout)
    assert status["checkpoint_revision"] == 4
    assert status["review_revision"] == status["current_review_revision"]
    assert status["review_revision"] == record["review_revision"]
    assert status["snapshot_id"] == record["snapshot_id"]
    pages = status["pages"]
    assert pages[0]["dispositions"] == [
        {"reason": "skew-nonzero", "decision": "reject", "note": "flat"}
    ]
    assert pages[1]["inspections"][0]["scope"] == "native"
    assert pages[2]["dispositions"] == [] and pages[2]["inspections"] == []
    acknowledgement = status["acknowledgement"]
    assert acknowledgement["review_revision"] == status["review_revision"]
    everyone = ["occ-000001", "occ-000002", "occ-000003"]
    # Partial acknowledgement never omits pages: coverage lists what is missing.
    covered = everyone if selection is None else list(selection)
    assert acknowledgement["ids"] == covered
    assert acknowledgement["missing_ids"] == [i for i in everyone if i not in covered]
    assert acknowledgement["complete"] is (selection is None)
    human = invoke(path)
    assert (
        human.returncode == 0
        and "occ-000002: source PDF page 2; baseline retained, inspected." in human.stdout
    )
    assert "occ-000001: source PDF page 1; baseline retained, uninspected." in human.stdout
    expected = (
        "3 of 3 pages; complete: true." if selection is None else "1 of 3 pages; complete: false."
    )
    assert "Acknowledgement covers " + expected in human.stdout
    assert "suggestion-rejected" in human.stdout
    assert bytes_at(path) == before
