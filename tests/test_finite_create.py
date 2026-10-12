"""Public create must freeze one result and keep the checkpoint fact exact.

The constructed native context establishes command lifetime and persistence only;
it never claims native execution or rendering fidelity. Signals are real process
signals delivered through the installed handlers.
"""

import json
import os
import signal
from io import StringIO
from pathlib import Path
from typing import Any, cast

import pytest
from test_baseline_state import evidence as evidence  # noqa: F401
from test_baseline_state import owner as owner  # noqa: F401
from test_import_assembly import inputs as inputs  # noqa: F401
from test_initial_import import constructed as constructed  # noqa: F401

from bookscan import checkpoints, finite_status
from bookscan.finite_protocol import Delivery, run


def create(
    source: Path, project: Path, *extra: str, delivery: Delivery | None = None
) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    code = run(
        ["baseline", "create", str(source), "--workdir", str(project), *extra],
        out,
        err,
        delivery=delivery,
    )
    return code, out.getvalue(), err.getvalue()


class Closed(StringIO):
    def write(self, text: str) -> int:
        raise BrokenPipeError("closed pipe")


def test_success_prints_project_path_and_resumes_after_source_loss(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
) -> None:
    source, project, _ = constructed
    code, out, err = create(source, project)
    assert (code, err) == (0, "")
    assert out == str(project.resolve()) + "\n"
    source.unlink()
    verified = finite_status.status(project)
    assert verified["status"] == "verified"


def test_json_result_is_one_created_record_matching_saved_state(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
) -> None:
    source, project, _ = constructed
    code, out, err = create(source, project, "--json")
    assert (code, err) == (0, "")
    record = json.loads(out)
    saved = finite_status.status(project)
    assert record["schema"] == "BookScanBuilderCommandResult" and record["schema_version"] == 1
    assert record["operation"] == "baseline.create"
    assert record["status"] == "created" and record["exit_code"] == 0
    assert record["committed"] is True and record["replayed"] is False
    assert record["warnings"] == []
    assert record["output"] == str(project.resolve())
    for field in ("project_id", "review_revision", "snapshot_id"):
        assert record[field] == saved[field] and record[field]
    assert record["current_review_revision"] == record["review_revision"]
    assert record["checkpoint_revision"] == saved["checkpoint_revision"]
    assert record["checkpoint_sha256"] == saved["checkpoint_sha256"]
    assert "pages" not in record


@pytest.mark.parametrize(
    ("fault", "code", "exit_code"),
    [("missing", "SOURCE_NOT_FOUND", 3), ("occupied", "PROJECT_EXISTS", 4)],
)
def test_precondition_errors_are_uncommitted_and_leave_inputs(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
    fault: str,
    code: str,
    exit_code: int,
) -> None:
    source, project, _ = constructed
    if fault == "missing":
        source.unlink()
    else:
        project.mkdir()
        (project / "keep").write_text("mine")
    result, out, err = create(source, project, "--json")
    record = json.loads(out)
    assert (result, err) == (exit_code, "")
    assert record["status"] == "error" and record["code"] == code
    assert record["exit_code"] == exit_code and record["operation"] == "baseline.create"
    assert record["committed"] is False
    assert record["project_id"] is None and record["output"] is None
    assert record["remediation"]
    if fault == "occupied":
        assert [item.name for item in project.iterdir()] == ["keep"]
    else:
        assert not project.exists()


def test_human_error_goes_to_stderr_with_exact_exit(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
) -> None:
    source, project, facts = constructed
    facts["fault"] = "dependency"
    code, out, err = create(source, project)
    assert code == 5 and out == ""
    assert err.startswith("DEPENDENCY_UNAVAILABLE: ")
    assert "process:setup" in err
    assert not project.exists()


@pytest.mark.parametrize(("number", "exit_code"), [(signal.SIGINT, 130), (signal.SIGTERM, 143)])
def test_signal_before_commit_saves_nothing(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    number: signal.Signals,
    exit_code: int,
) -> None:
    source, project, facts = constructed
    original = checkpoints.Checkpoints.commit

    def boundary(self: checkpoints.Checkpoints, *args: Any, **kwargs: Any) -> Any:
        os.kill(os.getpid(), number)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(checkpoints.Checkpoints, "commit", boundary)
    before = {signal.SIGINT: signal.getsignal(signal.SIGINT)}
    result, out, err = create(source, project, "--json")
    record = json.loads(out)
    assert (result, err) == (exit_code, "")
    assert record["status"] == "error" and record["code"] == "INTERRUPTED"
    assert record["exit_code"] == exit_code and record["committed"] is False
    assert record["project_id"] is None and record["output"] is None
    assert not project.exists()
    assert signal.getsignal(signal.SIGINT) is before[signal.SIGINT]
    assert "native-exit" in facts["events"]


@pytest.mark.parametrize(("number", "exit_code"), [(signal.SIGINT, 130), (signal.SIGTERM, 143)])
def test_signal_after_commit_returns_130_143_with_committed_fact(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    number: signal.Signals,
    exit_code: int,
) -> None:
    source, project, _ = constructed
    original = checkpoints.Checkpoints.commit

    def boundary(self: checkpoints.Checkpoints, *args: Any, **kwargs: Any) -> Any:
        result = original(self, *args, **kwargs)
        os.kill(os.getpid(), number)
        return result

    monkeypatch.setattr(checkpoints.Checkpoints, "commit", boundary)
    result, out, err = create(source, project, "--json")
    record = json.loads(out)
    saved = finite_status.status(project)
    assert (result, err) == (exit_code, "")
    assert record["status"] == "error" and record["code"] == "INTERRUPTED"
    assert record["committed"] is True and record["exit_code"] == exit_code
    assert record["project_id"] == saved["project_id"]
    assert record["output"] == str(project.resolve())
    assert "status" in record["remediation"]


def test_post_commit_cleanup_failure_keeps_selected_error_and_committed_fact(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
) -> None:
    source, project, facts = constructed
    facts["fault"] = "cleanup"
    result, out, err = create(source, project, "--json")
    record = json.loads(out)
    saved = finite_status.status(project)
    assert (result, err) == (5, "")
    assert record["committed"] is True and record["code"] == "DEPENDENCY_UNAVAILABLE"
    assert record["project_id"] == saved["project_id"]
    assert record["review_revision"] == saved["review_revision"]
    assert "status" in record["remediation"]


def test_delivery_failure_never_rolls_back_or_emits_a_second_record(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
) -> None:
    source, project, _ = constructed
    err, delivery = StringIO(), Delivery()
    result = run(
        ["baseline", "create", str(source), "--workdir", str(project), "--json"],
        Closed(),
        err,
        delivery=delivery,
    )
    assert result == 5 and delivery.failed
    assert err.getvalue().count("RESULT_DELIVERY_FAILED") == 1
    assert finite_status.status(project)["status"] == "verified"


def test_signal_during_delivery_cannot_replace_the_frozen_result(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
) -> None:
    source, project, _ = constructed

    class Interrupting(StringIO):
        def write(self, text: str) -> int:
            os.kill(os.getpid(), signal.SIGTERM)
            return super().write(text)

    out, err = Interrupting(), StringIO()
    result = run(["baseline", "create", str(source), "--workdir", str(project), "--json"], out, err)
    record = cast(dict[str, Any], json.loads(out.getvalue()))
    assert result == 0 and record["status"] == "created" and err.getvalue() == ""


@pytest.mark.parametrize(("number", "exit_code"), [(signal.SIGINT, 130), (signal.SIGTERM, 143)])
def test_signal_between_commit_and_serialization_keeps_committed_fact(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    number: signal.Signals,
    exit_code: int,
) -> None:
    """The success record is not frozen until serialization and the final check pass."""
    from bookscan import finite_create

    source, project, _ = constructed
    real = finite_create._serialize  # pyright: ignore[reportPrivateUsage]
    fired = False

    def serialize(record: Any, json_mode: bool) -> str:
        nonlocal fired
        if record["status"] == "created" and not fired:
            fired = True
            os.kill(os.getpid(), number)
        return real(record, json_mode)

    monkeypatch.setattr(finite_create, "_serialize", serialize)
    result, out, err = create(source, project, "--json")
    record = json.loads(out)
    assert (result, err) == (exit_code, "")
    assert record["code"] == "INTERRUPTED" and record["committed"] is True
    assert record["project_id"] and record["review_revision"]
    assert finite_status.status(project)["status"] == "verified"


def test_create_returning_without_a_commit_is_never_reported_as_created(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import initial_import

    source, project, _ = constructed

    def returns_nothing(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(initial_import, "create", returns_nothing)
    result, out, err = create(source, project, "--json")
    record = json.loads(out)
    assert (result, err) == (5, "")
    assert record["status"] == "error" and record["committed"] is False
    assert record["code"] == "WRITE_FAILED"


def test_committed_success_carries_checkpoint_warnings_as_structured_data(
    constructed: tuple[Path, Path, dict[str, Any]],  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    source, project, _ = constructed
    original = checkpoints.Checkpoints.commit

    def commit(self: checkpoints.Checkpoints, *args: Any, **kwargs: Any) -> Any:
        result = original(self, *args, **kwargs)
        return replace(result, warnings=("CHECKPOINT_CLEANUP_FAILED: private name retained",))

    monkeypatch.setattr(checkpoints.Checkpoints, "commit", commit)
    result, out, err = create(source, project, "--json")
    record = json.loads(out)
    assert result == 0 and record["status"] == "created" and record["committed"] is True
    [warning] = record["warnings"]
    assert warning["code"] == "CHECKPOINT_CLEANUP_FAILED"
    assert warning["message"] == "private name retained" and warning["remediation"]
    assert err == "CHECKPOINT_CLEANUP_FAILED: private name retained\n"
