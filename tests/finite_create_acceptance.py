"""Actual installed public create on constructed native pages, with writer barriers.

Run with --artifacts NEW --cache CACHE [--bookscan INSTALLED]. Construction uses
the real selected renderer/estimator and the installed ``bookscan baseline create``
route imports it. Private sitecustomize barriers stop the actual installed writer
PID at asset-complete, checkpoint pre/post-commit and with a native child alive;
they only choose where a signal lands and add no public fault mode. The child-alive
barrier delays the real pdftocairo exec behind /bin/sh so the child exists when the
signal arrives; that substitution is recorded, not hidden. No packet, review,
export or composition-fidelity claim is made.
"""

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

import assessment_acceptance
import finite_protocol_acceptance

from bookscan import ownership, project_header

BARRIER = """import json, os, subprocess, time
from pathlib import Path
from bookscan import native_setup
native_setup.default_cache = lambda: Path(os.environ['BOOKSCAN_TEST_CACHE'])
phase = os.environ.get('BOOKSCAN_TEST_CREATE_PHASE')
ready = os.environ.get('BOOKSCAN_TEST_CREATE_READY')
fired = []

def mark(**extra):
    Path(ready).write_text(json.dumps({'pid': os.getpid(), 'phase': phase, **extra}))

def hold(check):
    while True:
        check()
        time.sleep(0.01)

if phase == 'asset-complete':
    from bookscan import assets
    real = assets.Assets.publish
    def publish(self, *args, **kwargs):
        result = real(self, *args, **kwargs)
        if not fired:
            fired.append(1)
            mark(assets=len(list((self.owner.path / 'assets').iterdir())))
            hold(kwargs['check_cancel'])
        return result
    assets.Assets.publish = publish
elif phase == 'checkpoint-pre':
    from bookscan import checkpoints
    real = checkpoints.Checkpoints.commit
    def commit(self, *args, **kwargs):
        mark(project=str(self.owner.path))
        hold(kwargs['check_cancel'])
    checkpoints.Checkpoints.commit = commit
elif phase == 'checkpoint-post':
    # Stop after the real commit returned and the progress latch is set: the first
    # place a caught signal can be observed once the pointer change is authoritative.
    from bookscan import finite_command, initial_import
    caught = []
    real_interrupt = finite_command.Control.interrupt
    def interrupt(self, number, frame):
        caught.append(number)
        real_interrupt(self, number, frame)
    finite_command.Control.interrupt = interrupt
    real_set = initial_import.Progress.__setattr__
    def setter(self, name, value):
        real_set(self, name, value)
        if name == 'committed' and value is True:
            mark(project=str(self.path))
            while not caught:
                time.sleep(0.01)
    initial_import.Progress.__setattr__ = setter
elif phase == 'child-alive':
    real = subprocess.Popen
    class Popen(real):
        def __init__(self, argv, *args, **kwargs):
            native = (
                not fired and argv and Path(str(argv[0])).name == 'pdftocairo'
                and '-v' not in argv[1:]
            )
            if native:
                fired.append(1)
                argv = ['/bin/sh', '-c', 'sleep 30; exec "$@"', 'sh', *argv]
            super().__init__(argv, *args, **kwargs)
            if native:
                mark(child=self.pid)
    subprocess.Popen = Popen
"""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def create(
    command: list[str], source: Path, project: Path, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*command, "baseline", "create", str(source), "--workdir", str(project), "--json"],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
        timeout=300,
    )


def status(command: list[str], project: Path) -> subprocess.CompletedProcess[str]:
    return finite_protocol_acceptance.invoke(
        command, ["baseline", "status", str(project), "--json"]
    )


def run(directory: Path, cache: Path, executable: Path) -> dict[str, object]:
    command = [str(executable)]
    directory.mkdir()
    prior = assessment_acceptance.run(directory / "construction", cache)
    expected = [
        cast(str, item["rgb_sha256"]) for item in cast(list[dict[str, object]], prior["records"])
    ]
    snapshot = directory / "construction" / "snapshot.pdf"
    inputs = directory / "inputs"
    inputs.mkdir()
    source = inputs / "Book.pdf"
    shutil.copyfile(snapshot, source)
    source_digest = digest(source)
    hooks = directory / "hooks"
    hooks.mkdir()
    (hooks / "sitecustomize.py").write_text(BARRIER)

    def environment(phase: str | None = None, ready: Path | None = None) -> dict[str, str]:
        result = dict(os.environ, PYTHONPATH=str(hooks), BOOKSCAN_TEST_CACHE=str(cache))
        if phase is not None and ready is not None:
            result.update(BOOKSCAN_TEST_CREATE_PHASE=phase, BOOKSCAN_TEST_CREATE_READY=str(ready))
        return result

    # Ordinary installed create, then source-loss status on the saved baseline.
    started = time.monotonic()
    project = directory / "Project One"
    normal = create(command, source, project, environment())
    assert normal.returncode == 0 and normal.stderr == "", normal
    record = json.loads(normal.stdout)
    assert record["status"] == "created" and record["committed"] is True
    assert record["operation"] == "baseline.create" and record["output"] == str(project)
    shutil.move(source, directory / "inputs-moved.pdf")  # source loss
    resumed = status(command, project)
    assert resumed.returncode == 0, resumed
    saved = json.loads(resumed.stdout)
    pages = cast(list[dict[str, object]], saved["pages"])
    assert [page["image_sha256"] for page in pages] == expected, "pixels differ from construction"
    for field in ("project_id", "review_revision", "snapshot_id", "checkpoint_sha256"):
        assert saved[field] == record[field], field
    shutil.move(directory / "inputs-moved.pdf", source)
    assert digest(source) == source_digest
    elapsed = time.monotonic() - started
    occupied = create(command, source, project, environment())
    assert occupied.returncode == 4 and json.loads(occupied.stdout)["code"] == "PROJECT_EXISTS"
    assert json.loads(occupied.stdout)["committed"] is False
    assert json.loads(status(command, project).stdout) == saved

    observations: list[dict[str, object]] = []
    for phase in ("asset-complete", "checkpoint-pre", "checkpoint-post", "child-alive"):
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
            label = f"{phase}-{number.name}"
            target = directory / f"{label} project"
            ready = directory / f"{label}.ready.json"
            process = subprocess.Popen(
                [
                    *command,
                    "baseline",
                    "create",
                    str(source),
                    "--workdir",
                    str(target),
                    "--json",
                ],
                env=environment(phase, ready),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            child: int | None = None
            try:
                deadline = time.monotonic() + 240
                while not ready.exists():
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise AssertionError(f"{label}: installed writer missed its barrier")
                    time.sleep(0.01)
                time.sleep(0.05)
                observed = json.loads(ready.read_bytes())
                assert observed["pid"] == process.pid and observed["phase"] == phase
                child = cast(int | None, observed.get("child"))
                header = project_header.Header.from_json((target / "project.json").read_bytes())
                # The live writer holds the actual kernel ownership at its barrier.
                try:
                    with ownership.Writer.acquire(target, header.lock):
                        raise AssertionError(f"{label}: ownership was not held at the barrier")
                except ownership.OwnershipError as busy:
                    assert busy.code == "PROJECT_BUSY"
                if child is not None:
                    assert alive(child)
                process.send_signal(number)
                stdout, stderr = process.communicate(timeout=60)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=60)
            expected_exit = -signal.SIGKILL if number == signal.SIGKILL else 128 + number
            assert process.returncode == expected_exit, (label, process.returncode, stdout, stderr)
            committed = phase == "checkpoint-post"
            result = None if number == signal.SIGKILL else json.loads(stdout)
            if result is not None:
                assert stderr == ""
                assert result["code"] == "INTERRUPTED" and result["operation"] == "baseline.create"
                assert result["committed"] is committed and result["exit_code"] == expected_exit
                assert (result["output"] == str(target)) is committed
            if child is not None:
                if number == signal.SIGKILL:
                    # A killed writer leaves its separate-session child; ownership is
                    # still immediately reacquirable, never inherited by that child.
                    assert alive(child)
                else:
                    assert not alive(child), f"{label}: owned child was not reaped"
            if target.exists() and (target / "project.json").exists():
                header = project_header.Header.from_json((target / "project.json").read_bytes())
                with ownership.Writer.acquire(target, header.lock):
                    pass
            if child is not None and alive(child):
                os.killpg(child, signal.SIGKILL)
            after = status(command, target)
            if committed:
                assert after.returncode == 0
                again = json.loads(after.stdout)
                assert [p["image_sha256"] for p in again["pages"]] == expected
            else:
                if number == signal.SIGKILL:
                    assert after.returncode == 3 and json.loads(after.stdout)["code"] == (
                        "INVALID_PROJECT"
                    )
                    retry = create(command, source, target, environment())
                    assert retry.returncode == 4 and json.loads(retry.stdout)["code"] == (
                        "PROJECT_EXISTS"
                    )
                else:
                    assert not target.exists(), f"{label}: caught signal left a project"
            assert digest(source) == source_digest
            observations.append(
                {
                    "label": label,
                    "writer_pid": process.pid,
                    "observed_pid": observed["pid"],
                    "child_pid": child,
                    "exit": process.returncode,
                    "result": result,
                    "committed": committed,
                    "status_after": after.returncode,
                }
            )
    # After every interruption a fresh create to a new destination still succeeds.
    fresh = directory / "Project Fresh"
    retried = create(command, source, fresh, environment())
    assert retried.returncode == 0, retried
    fresh_saved = json.loads(status(command, fresh).stdout)
    assert [p["image_sha256"] for p in fresh_saved["pages"]] == expected
    assert digest(source) == source_digest
    # Real closed stdout, with the same private cache hook as every other run: the
    # project must still commit and verify; only delivery fails, exactly once.
    reader, writer = os.pipe()
    os.close(reader)
    try:
        pipe = subprocess.run(
            [
                *command,
                "baseline",
                "create",
                str(source),
                "--workdir",
                str(directory / "Project Pipe"),
                "--json",
            ],
            stdout=writer,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env=environment(),
            timeout=300,
        )
    finally:
        os.close(writer)
    assert pipe.returncode == 5 and pipe.stderr.count("RESULT_DELIVERY_FAILED") == 1
    piped = json.loads(status(command, directory / "Project Pipe").stdout)
    assert piped["status"] == "verified"
    assert [p["image_sha256"] for p in piped["pages"]] == expected
    result_record: dict[str, object] = {
        "format": "BookScanBuilderFiniteCreateAcceptance",
        "version": 1,
        "executable": str(executable),
        "executable_sha256": digest(executable),
        "truth_sha256": prior["truth_sha256"],
        "baseline_sha256": expected,
        "source_sha256": source_digest,
        "checkpoint_sha256": record["checkpoint_sha256"],
        "elapsed_seconds_first_create": round(elapsed, 2),
        "writer_observations": observations,
        "epipe_exit": pipe.returncode,
        "epipe_committed_project_verifies": True,
        "child_alive_barrier": "sh sleep before the real pdftocairo exec",
        "complete_finite_handoff": False,
        "composition_fidelity_verified": False,
    }
    (directory / "result.json").write_text(json.dumps(result_record, indent=2) + "\n")
    return result_record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--bookscan", type=Path, default=Path(sys.executable).with_name("bookscan"))
    args = parser.parse_args()
    result = run(args.artifacts.absolute(), args.cache.absolute(), args.bookscan.absolute())
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "baseline_sha256",
                    "elapsed_seconds_first_create",
                    "epipe_exit",
                    "complete_finite_handoff",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
