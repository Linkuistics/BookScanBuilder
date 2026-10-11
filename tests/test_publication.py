"""Real filesystem faults and observed signals/kill windows of the installed writer."""

import io
import json
import os
import signal
import stat
import subprocess
import time
from pathlib import Path
from typing import BinaryIO, cast

import pikepdf
import pytest
from test_faults import BrokenOutput
from test_preview import labels
from test_writes import digest, invoke

from bookscan import copying
from bookscan.cli import run
from bookscan.publication import Control, Staged, failure


def args(source: Path, *, dry: bool = False) -> list[str]:
    return [
        "--content",
        str(source),
        "--output",
        str(source.parent / "out.pdf"),
        "--json",
        *(["--dry-run"] if dry else []),
    ]


@pytest.mark.parametrize(
    "fault,code",
    [
        ("create", "WRITE_FAILED"),
        ("copy", "COPY_FAILED"),
        ("save", "WRITE_FAILED"),
        ("reopen", "OUTPUT_INVALID"),
        ("mismatch", "OUTPUT_INVALID"),
        ("mode", "WRITE_FAILED"),
        ("flush", "WRITE_FAILED"),
        ("fsync", "WRITE_FAILED"),
        ("link", "PUBLISH_FAILED"),
        ("race", "OUTPUT_EXISTS"),
        ("source-change", "SOURCE_CHANGED"),
        ("save-warning", "COPY_FAILED"),
        ("output-warning", "OUTPUT_INVALID"),
    ],
)
def test_precommit_faults_preserve_sources_and_sentinels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    code: str,
) -> None:
    source = labels(tmp_path / "in.pdf", 2)
    before = digest(source)
    control = Control()
    original_fchmod = os.fchmod
    original_validate = copying.validate
    original_open = pikepdf.Pdf.open

    def fail(*_a: object, **_k: object) -> None:
        raise PermissionError("controlled denial")

    if fault == "create":
        monkeypatch.setattr(os, "open", fail)
    elif fault == "copy":
        monkeypatch.setattr(copying, "copy_page", fail)
    elif fault == "save":
        monkeypatch.setattr(pikepdf.Pdf, "save", fail)
    elif fault == "reopen":

        def reopen(stream: BinaryIO, **kwargs: object) -> pikepdf.Pdf:
            if "b" in str(getattr(stream, "mode", "")) and "+" in str(getattr(stream, "mode", "")):
                raise pikepdf.PdfError("controlled output parser failure")
            return original_open(stream, **kwargs)  # pyright: ignore[reportArgumentType]

        monkeypatch.setattr(pikepdf.Pdf, "open", reopen)
    elif fault == "mismatch":

        def mismatch(*_a: object, **_k: object) -> None:
            raise failure("OUTPUT_INVALID", "controlled mismatch")

        monkeypatch.setattr(copying, "validate", mismatch)
    elif fault == "mode":

        def mode(fd: int, value: int) -> None:
            if value != 0o600:
                raise PermissionError("controlled final mode failure")
            original_fchmod(fd, value)

        monkeypatch.setattr(os, "fchmod", mode)
    elif fault == "flush":
        original_create = Staged.create

        class FailingFlush(io.BufferedRandom):
            enabled: bool = False

            def flush(self) -> None:
                if self.enabled:
                    raise OSError("controlled completed-stream flush failure")
                super().flush()

        def create(destination: Path, mode: int, control: Control) -> Staged:
            stage = original_create(destination, mode, control)
            raw = io.FileIO(os.dup(stage.stream.fileno()), "r+")
            stage.stream.close()
            stage.stream = cast(BinaryIO, FailingFlush(raw))
            return stage

        def enable_after_validation(plan: object, stream: BinaryIO) -> None:
            original_validate(plan, stream)  # pyright: ignore[reportArgumentType]
            assert isinstance(stream, FailingFlush)
            stream.enabled = True

        monkeypatch.setattr(Staged, "create", create)
        monkeypatch.setattr(copying, "validate", enable_after_validation)
    elif fault == "fsync":
        monkeypatch.setattr(os, "fsync", fail)
    elif fault == "link":
        monkeypatch.setattr(os, "link", fail)
    elif fault == "race":
        original_link = os.link

        def race(temp: Path, output: Path) -> None:
            output.write_bytes(b"race sentinel")
            original_link(temp, output)

        monkeypatch.setattr(os, "link", race)
    elif fault == "source-change":

        def change(self: Staged) -> None:
            source.write_bytes(source.read_bytes() + b"\nchanged")

        monkeypatch.setattr(Staged, "finish", change)

        # Changes must precede the source recheck, not follow it.
        def validate_then_change(*values: object) -> None:
            original_validate(*values)  # pyright: ignore[reportArgumentType]
            source.write_bytes(source.read_bytes() + b"\nchanged")

        monkeypatch.setattr(copying, "validate", validate_then_change)
    elif fault in {"save-warning", "output-warning"}:
        phase = "save" if fault == "save-warning" else "validate"
        method = getattr(copying, phase)

        def warning_host(*values: object) -> None:
            def warnings(pdf: pikepdf.Pdf) -> list[str]:
                return ["controlled phase warning"]

            with monkeypatch.context() as scoped:
                scoped.setattr(pikepdf.Pdf, "get_warnings", warnings)
                method(*values)

        monkeypatch.setattr(copying, phase, warning_host)
    stdout, stderr = io.StringIO(), io.StringIO()
    result = run(args(source), stdout, stderr, control=control, mode=0o644)
    record = json.loads(stdout.getvalue())
    assert record["code"] == code and result == (
        4 if code == "OUTPUT_EXISTS" else 3 if code == "SOURCE_CHANGED" else 5
    )
    assert not list(tmp_path.glob(".bookscan-prepare-*"))
    output = tmp_path / "out.pdf"
    if fault == "race":
        assert output.read_bytes() == b"race sentinel"
    else:
        assert not output.exists()
    if fault != "source-change":
        assert digest(source) == before


def test_planned_then_stage_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = labels(tmp_path / "in.pdf")
    before = digest(source)
    planned = invoke(*args(source, dry=True))
    assert json.loads(planned.stdout)["status"] == "planned"

    def denied(*_a: object, **_k: object) -> None:
        raise PermissionError("controlled creation")

    monkeypatch.setattr(os, "open", denied)
    out = io.StringIO()
    assert run(args(source), out, io.StringIO()) == 5
    assert json.loads(out.getvalue())["code"] == "WRITE_FAILED"
    assert digest(source) == before and not (tmp_path / "out.pdf").exists()


@pytest.mark.parametrize("committed", [False, True])
def test_cleanup_failure_preserves_commit_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, committed: bool
) -> None:
    source = labels(tmp_path / "in.pdf")
    original_unlink = Path.unlink

    def deny(path: Path, **kwargs: object) -> None:
        if path.name.startswith(".bookscan-prepare-"):
            raise PermissionError("cleanup denied")
        original_unlink(path, **kwargs)  # pyright: ignore[reportArgumentType]

    monkeypatch.setattr(Path, "unlink", deny)
    if not committed:

        def mismatch(*_a: object, **_k: object) -> None:
            raise failure("OUTPUT_INVALID", "mismatch")

        monkeypatch.setattr(copying, "validate", mismatch)
    out, err = io.StringIO(), io.StringIO()
    result = run(args(source), out, err)
    record = json.loads(out.getvalue())
    assert result == (0 if committed else 5)
    assert record["status"] == ("written" if committed else "error")
    assert record["warnings"][0]["code"] == "TEMP_CLEANUP_FAILED"
    private = list(tmp_path.glob(".bookscan-prepare-*.tmp"))
    assert len(private) == 1
    assert str(private[0]) in record["warnings"][0]["message"]
    if committed:
        assert os.path.samefile(private[0], tmp_path / "out.pdf")
    else:
        assert record["code"] == "OUTPUT_INVALID" and not (tmp_path / "out.pdf").exists()


def test_postcommit_delivery_keeps_success(tmp_path: Path) -> None:
    source = labels(tmp_path / "in.pdf")
    stderr = io.StringIO()
    assert run(args(source), BrokenOutput(), stderr) == 0
    assert "RESULT_DELIVERY_FAILED" in stderr.getvalue()
    with pikepdf.Pdf.open(tmp_path / "out.pdf") as pdf:
        assert len(pdf.pages) == 6


def start_writer(
    tmp_path: Path, source: Path, hook: str, mask: int | None = None, *, dry: bool = False
) -> tuple[subprocess.Popen[str], Path]:
    customization = tmp_path / "instrumentation"
    customization.mkdir()
    channel = tmp_path / "barrier.json"
    (customization / "sitecustomize.py").write_text(
        "import os\nfrom pathlib import Path\nfrom writer_hooks import install\n"
        + (f"os.umask({mask})\n" if mask is not None else "")
        + f"install({hook!r}, Path({str(channel)!r}))\n"
    )
    root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join([str(customization), str(root / "tests")])
    process = subprocess.Popen(
        [str(root / ".venv/bin/bookscan"), "prepare", *args(source, dry=dry)],
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 10
    while not channel.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert channel.exists(), "Writer did not acknowledge the requested barrier"
    record = json.loads(channel.read_text())
    assert record["pid"] == process.pid and record["hook"] == hook
    return process, channel


@pytest.mark.parametrize(
    "hook,dry,want,code",
    [
        ("validation", False, None, "INTERRUPTED"),
        ("recheck", False, None, "INTERRUPTED"),
        ("recheck", True, None, "INTERRUPTED"),
        ("finish", False, None, "INTERRUPTED"),
        ("dry-traversal", True, None, "INTERRUPTED"),
        ("after-open", False, None, "INTERRUPTED"),
        ("plan-emit", True, None, "INTERRUPTED"),
        ("error-emit", False, 3, "SOURCE_NOT_FOUND"),
        ("cleanup-error", False, 5, "OUTPUT_INVALID"),
    ],
)
@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_signal_lifetime_gaps(
    tmp_path: Path, hook: str, dry: bool, want: int | None, code: str, signum: signal.Signals
) -> None:
    """Catch relabelled cancellation, unowned files and interrupted error delivery/cleanup."""
    source = labels(tmp_path / "in.pdf", 2)
    before = digest(source)
    argument = tmp_path / "missing.pdf" if hook == "error-emit" else source
    process, channel = start_writer(tmp_path, argument, hook, dry=dry)
    try:
        os.kill(process.pid, signum)
        stdout, stderr = process.communicate(input="continue\n", timeout=10)
        assert process.returncode == (128 + signum if want is None else want), stderr + stdout
        record = json.loads(stdout)
        assert record["status"] == "error" and record["code"] == code
        assert "Traceback" not in stderr
        assert not (tmp_path / "out.pdf").exists()
        assert not list(tmp_path.glob(".bookscan-prepare-*.tmp"))
        assert digest(source) == before
        (tmp_path / "evidence.json").write_text(
            json.dumps(
                {
                    "pid": process.pid,
                    "hook": hook,
                    "dry_run": dry,
                    "signal": int(signum),
                    "exit": process.returncode,
                    "result": record,
                    "private_removed": True,
                    "source_unchanged": True,
                    "writer_reaped": process.poll() is not None,
                    "observed_barrier": json.loads(channel.read_text()),
                },
                indent=2,
            )
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_second_signal_cannot_interrupt_cleanup(tmp_path: Path, signum: signal.Signals) -> None:
    source = labels(tmp_path / "in.pdf", 2)
    before = digest(source)
    process, channel = start_writer(tmp_path, source, "cleanup-interrupted")
    try:
        os.kill(process.pid, signum)
        assert process.stdin is not None
        process.stdin.write("continue\n")
        process.stdin.flush()
        deadline = time.monotonic() + 10
        while (
            json.loads(channel.read_text())["hook"] != "cleanup-second-signal"
            and process.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        assert json.loads(channel.read_text())["hook"] == "cleanup-second-signal"
        os.kill(process.pid, signum)
        stdout, stderr = process.communicate(input="continue\n", timeout=10)
        assert process.returncode == 128 + signum, stderr + stdout
        record = json.loads(stdout)
        assert record["code"] == "INTERRUPTED"
        assert not list(tmp_path.glob(".bookscan-prepare-*.tmp"))
        assert not (tmp_path / "out.pdf").exists() and digest(source) == before
        (tmp_path / "evidence.json").write_text(
            json.dumps(
                {
                    "pid": process.pid,
                    "hook": "cleanup-interrupted",
                    "signal": int(signum),
                    "signals_sent": 2,
                    "exit": process.returncode,
                    "result": record,
                    "private_removed": True,
                    "source_unchanged": True,
                    "writer_reaped": process.poll() is not None,
                    "observed_barrier": json.loads(channel.read_text()),
                },
                indent=2,
            )
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)


@pytest.mark.parametrize(
    "hook",
    [
        "writing",
        "pre-region",
        "pending",
        "after-block",
        "blocked",
        "after-link",
        "committed",
        "cleanup",
    ],
)
@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_real_signals_at_observed_barriers(
    tmp_path: Path, hook: str, signum: signal.Signals
) -> None:
    source = labels(tmp_path / "in.pdf", 2)
    before = digest(source)
    process, channel = start_writer(tmp_path, source, hook)
    try:
        os.kill(process.pid, signum)
        if hook in {"pending", "after-block", "blocked", "after-link", "committed"}:
            assert process.stdin is not None
            process.stdin.write("continue\n")
            process.stdin.flush()
        stdout, stderr = process.communicate(timeout=10)
        record = json.loads(stdout)
        committed = hook in {"after-block", "blocked", "after-link", "committed", "cleanup"}
        assert process.returncode == (0 if committed else 128 + signum), stderr + stdout
        assert record["status"] == ("written" if committed else "error")
        if committed:
            assert "POST_COMMIT_SIGNAL" in [w["code"] for w in record["warnings"]]
            with pikepdf.Pdf.open(tmp_path / "out.pdf", attempt_recovery=False) as pdf:
                assert len(pdf.pages) == 2
        else:
            assert record["code"] == "INTERRUPTED" and not (tmp_path / "out.pdf").exists()
        assert not list(tmp_path.glob(".bookscan-prepare-*.tmp"))
        assert digest(source) == before and channel.exists()
        (tmp_path / "evidence.json").write_text(
            json.dumps(
                {
                    "pid": process.pid,
                    "hook": hook,
                    "signal": int(signum),
                    "exit": process.returncode,
                    "result": record,
                    "complete_destination": committed,
                    "private_removed": True,
                    "source_unchanged": True,
                    "writer_reaped": process.poll() is not None,
                    "observed_barrier": json.loads(channel.read_text()),
                },
                indent=2,
            )
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)


@pytest.mark.parametrize("hook", ["writing", "after-link"])
def test_sigkill_observes_state_and_no_surviving_writer(tmp_path: Path, hook: str) -> None:
    source = labels(tmp_path / "in.pdf", 2)
    before = digest(source)
    process, channel = start_writer(tmp_path, source, hook)
    private = Path(json.loads(channel.read_text())["private"][0])
    output = tmp_path / "out.pdf"
    if hook == "writing":
        assert not output.exists() and private.stat().st_size > 0
        assert stat.S_IMODE(private.stat().st_mode) == 0o600
    else:
        assert os.path.samefile(private, output)
        with pikepdf.Pdf.open(output, attempt_recovery=False) as pdf:
            assert len(pdf.pages) == 2
    os.kill(process.pid, signal.SIGKILL)
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == -signal.SIGKILL and stdout == "", stderr
    with pytest.raises(ProcessLookupError):
        os.kill(process.pid, 0)
    assert digest(source) == before and private.exists()
    if hook == "after-link":
        assert os.path.samefile(private, output)
        with pikepdf.Pdf.open(output, attempt_recovery=False) as pdf:
            assert len(pdf.pages) == 2
    else:
        assert not output.exists()
    (tmp_path / "evidence.json").write_text(
        json.dumps(
            {
                "pid": process.pid,
                "hook": hook,
                "signal": 9,
                "exit": process.returncode,
                "destination_before_kill": hook == "after-link",
                "destination_after_exit": output.exists(),
                "private_before_kill": True,
                "private_after_exit": private.exists(),
                "same_file_before_and_after": hook == "after-link",
                "complete_destination": hook == "after-link",
                "source_unchanged": True,
                "writer_reaped": True,
                "observed_barrier": json.loads(channel.read_text()),
            },
            indent=2,
        )
    )
    # Test cleanup occurs only after both pre-kill and post-exit observations.
    private.unlink()


@pytest.mark.parametrize("mask", [0o027, 0o077, 0o777])
def test_private_and_startup_umask_modes(tmp_path: Path, mask: int) -> None:
    source = labels(tmp_path / "in.pdf")
    process, channel = start_writer(tmp_path, source, "writing", mask)
    private = Path(json.loads(channel.read_text())["private"][0])
    assert stat.S_IMODE(private.stat().st_mode) == 0o600
    assert process.stdin is not None
    process.stdin.write("continue\n")
    process.stdin.flush()
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 0, stderr + stdout
    assert stat.S_IMODE((tmp_path / "out.pdf").stat().st_mode) == 0o666 & ~mask


@pytest.mark.parametrize("case,want", [("dry", 5), ("error", 3), ("write", 0)])
def test_real_epipe_exit_and_destination(tmp_path: Path, case: str, want: int) -> None:
    source = tmp_path / "missing.pdf" if case == "error" else labels(tmp_path / "in.pdf", 2)
    root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen(
        [str(root / ".venv/bin/bookscan"), "prepare", *args(source, dry=case == "dry")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None and process.stderr is not None
    process.stdout.close()
    code = process.wait(timeout=10)
    stderr = process.stderr.read()
    assert code == want, stderr
    assert "RESULT_DELIVERY_FAILED" in stderr
    output = tmp_path / "out.pdf"
    assert output.exists() == (case == "write")
    if case == "write":
        with pikepdf.Pdf.open(output) as pdf:
            assert len(pdf.pages) == 2
