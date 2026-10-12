"""Actual installed status on native saved pages, including interrupted readers.

Run with --artifacts NEW --cache CACHE [--bookscan INSTALLED]. Construction uses
the real selected renderer/estimator; saved status uses no renderer or helper.
Private sitecustomize barriers observe the installed reader PID under ownership.
No public create, packet, review, export or composition-fidelity claim is made.
"""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

import baseline_state_acceptance
import finite_protocol_acceptance

from bookscan import ownership, project_header

BARRIER = """import json, os, time
from pathlib import Path
from bookscan import baseline_state
real = baseline_state.restore
fired = False
def stopped(*args, **kwargs):
    global fired
    if fired:
        return real(*args, **kwargs)
    fired = True
    mode = os.environ['BOOKSCAN_TEST_STATUS_PHASE']
    if mode == 'after':
        result = real(*args, **kwargs)
    Path(os.environ['BOOKSCAN_TEST_STATUS_READY']).write_text(json.dumps({
        'pid': os.getpid(), 'phase': mode, 'project': str(args[0].owner.path)}))
    while True:
        kwargs['check_cancel']()
        time.sleep(0.01)
baseline_state.restore = stopped
"""


def subjects(path: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for item in sorted(path.rglob("*")):
        info = item.lstat()
        result[str(item.relative_to(path))] = {
            "sha256": hashlib.sha256(item.read_bytes()).hexdigest() if item.is_file() else None,
            "symlink": os.readlink(item) if item.is_symlink() else None,
            "native": [
                info.st_dev,
                info.st_ino,
                info.st_mode,
                info.st_size,
                info.st_mtime_ns,
                info.st_ctime_ns,
            ],
        }
    return result


def status(executable: Path, project: Path) -> subprocess.CompletedProcess[str]:
    return finite_protocol_acceptance.invoke(
        [str(executable)], ["baseline", "status", str(project), "--json"]
    )


def run(directory: Path, cache: Path, executable: Path) -> dict[str, object]:
    directory.mkdir()
    native = baseline_state_acceptance.run(directory / "native", cache)
    project = directory / "native" / "project"
    before = subjects(project)
    normal = status(executable, project)
    assert normal.returncode == 0 and normal.stderr == "", normal
    record = json.loads(normal.stdout)
    assert record["status"] == "verified" and record["committed"] is False
    assert record["review_revision"] == native["review_revision"]
    assert record["snapshot_id"] == native["snapshot_id"]
    assert record["checkpoint_sha256"] == native["checkpoint_sha256"]
    pages = cast(list[dict[str, object]], record["pages"])
    assert [page["image_sha256"] for page in pages] == native["baseline_sha256"]
    assert [page["id"] for page in pages] == [f"occ-{n:06d}" for n in range(1, 8)]
    assert all(page["inspections"] == [] and page["dispositions"] == [] for page in pages)
    (directory / "status.json").write_text(normal.stdout)
    header = project_header.Header.from_json((project / "project.json").read_bytes())
    with ownership.Writer.acquire(project, header.lock):
        busy = status(executable, project)
        assert busy.returncode == 4 and json.loads(busy.stdout)["code"] == "PROJECT_BUSY"

    hooks = directory / "hooks"
    hooks.mkdir()
    (hooks / "sitecustomize.py").write_text(BARRIER)
    observations: list[dict[str, object]] = []
    for phase in ("before", "after"):
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
            ready = directory / f"{phase}-{number}.ready.json"
            environment = dict(os.environ)
            environment.update(
                PYTHONPATH=str(hooks),
                BOOKSCAN_TEST_STATUS_PHASE=phase,
                BOOKSCAN_TEST_STATUS_READY=str(ready),
            )
            process = subprocess.Popen(
                [str(executable), "baseline", "status", str(project), "--json"],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                deadline = time.monotonic() + 15
                while not ready.exists():
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise AssertionError("Installed reader did not reach owned barrier")
                    time.sleep(0.01)
                observed = json.loads(ready.read_bytes())
                assert observed == {"pid": process.pid, "phase": phase, "project": str(project)}
                # The barrier is inside the actual reader's acquired ownership.
                blocked = status(executable, project)
                assert blocked.returncode == 4
                process.send_signal(number)
                stdout, stderr = process.communicate(timeout=15)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=15)
            expected = -signal.SIGKILL if number == signal.SIGKILL else 128 + number
            assert process.returncode == expected, (process.returncode, stdout, stderr)
            observed_result = None if number == signal.SIGKILL else json.loads(stdout)
            if observed_result is not None:
                assert (
                    observed_result["code"] == "INTERRUPTED"
                    and observed_result["committed"] is False
                )
                assert observed_result["operation"] == "baseline.status"
            assert stderr == ""
            resumed = status(executable, project)
            assert resumed.returncode == 0 and json.loads(resumed.stdout) == record
            assert subjects(project) == before
            observations.append(
                {
                    "phase": phase,
                    "signal": number.name,
                    "exit": process.returncode,
                    "owner_pid": process.pid,
                    "observed_pid": observed["pid"],
                    "result": observed_result,
                    "resumed": True,
                    "bytes_and_native_unchanged": True,
                }
            )
    # Deny collection and vanished original/resource trees at the actual processor.
    blocked = directory / "denied"
    blocked.mkdir()
    sentinel = blocked / "control"
    sentinel.write_bytes(b"must be denied")
    denied_paths = [
        blocked,
        Path("/Volumes/Glass/Book Conversion"),
        directory / "native" / "construction",
        directory / "native" / "copied-resources",
    ]
    profile = directory / "read-denial.sb"
    profile.write_text(
        "(version 1)(allow default)"
        + "".join(
            "(deny file-read* (subpath " + json.dumps(str(path)) + "))" for path in denied_paths
        )
    )
    boundary = ["/usr/bin/sandbox-exec", "-f", str(profile)]
    control = finite_protocol_acceptance.invoke([*boundary, "/bin/cat"], [str(sentinel)])
    assert control.returncode != 0 and "Operation not permitted" in control.stderr
    denied_status = finite_protocol_acceptance.invoke(
        [*boundary, str(executable)], ["baseline", "status", str(project), "--json"]
    )
    assert denied_status.returncode == 0 and json.loads(denied_status.stdout) == record
    pipe = finite_protocol_acceptance.broken_pipe(
        [str(executable)], ["baseline", "status", str(project), "--json"]
    )
    assert pipe.returncode == 5 and pipe.stderr.count("RESULT_DELIVERY_FAILED") == 1
    assert subjects(project) == before
    result: dict[str, object] = {
        "format": "BookScanBuilderFiniteStatusAcceptance",
        "version": 1,
        "executable": str(executable),
        "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "checkpoint_sha256": native["checkpoint_sha256"],
        "review_revision": native["review_revision"],
        "snapshot_id": native["snapshot_id"],
        "baseline_sha256": native["baseline_sha256"],
        "truth_sha256": native["truth_sha256"],
        "source_loss_resume": True,
        "resource_loss_resume": True,
        "denied_collection_control": True,
        "denied_read_control_exit": control.returncode,
        "writer_observations": observations,
        "epipe_exit": pipe.returncode,
        "complete_finite_handoff": False,
        "composition_fidelity_verified": False,
        "limitations": native["limitations"],
        "saved_subjects": before,
    }
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


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
                    "source_loss_resume",
                    "resource_loss_resume",
                    "denied_collection_control",
                    "epipe_exit",
                    "complete_finite_handoff",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
