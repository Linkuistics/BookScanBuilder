"""Real private reservation processes; public create remains unavailable.

Observe exclusive names, canonical aliases, selected signal exits, empty-only
cleanup, kill/reap and incomplete-state refusal. No native child/commit fault or
complete finite handoff is established by this focused mechanism.
"""

import argparse
import json
import os
import select
import signal
import subprocess
import sys
from pathlib import Path
from typing import cast

from bookscan.project_reservation import reserve


def run(directory: Path) -> dict[str, object]:
    directory.mkdir()
    worker = Path(__file__).with_name("reservation_worker.py")
    observations: list[dict[str, object]] = []
    cases = [
        ("normal", None, False),
        ("int-empty", signal.SIGINT, False),
        ("term-empty", signal.SIGTERM, False),
        ("kill-empty", signal.SIGKILL, False),
        ("int-content", signal.SIGINT, True),
        ("term-content", signal.SIGTERM, True),
        ("term-replaced", signal.SIGTERM, False),
    ]
    for name, number, content in cases:
        project = directory / name
        command = [sys.executable, str(worker), str(project), "--hold"]
        if content:
            command.append("--content")
        child = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            close_fds=True,
        )
        try:
            assert child.stdout is not None
            ready, _, _ = select.select([child.stdout], [], [], 10)
            assert ready, "No observed reservation barrier"
            line = child.stdout.readline()
            barrier = json.loads(line)
            assert barrier == {"pid": child.pid, "path": str(project.resolve()), "ready": True}
            aliases = [project, project.with_name(project.name.swapcase())]
            parent_alias = directory / (name + "-parent")
            parent_alias.symlink_to(directory.resolve(), target_is_directory=True)
            aliases.append(parent_alias / project.name)
            conflicts: list[dict[str, object]] = []
            for alias in aliases:
                assert alias.is_dir(), "Actual filesystem case alias unavailable"
                attempt = subprocess.run(
                    [sys.executable, str(worker), str(alias)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                record = json.loads(attempt.stdout)
                assert attempt.returncode == 4 and not attempt.stderr
                assert record["code"] == "PROJECT_EXISTS" and not record["committed"]
                conflicts.append(record)
            moved = directory / (name + "-owned")
            if name == "term-replaced":
                project.rename(moved)
                project.mkdir()
                (project / "foreign").write_bytes(b"do not delete")
            if number is None:
                assert child.stdin is not None
                child.stdin.write("release\n")
                child.stdin.flush()
            else:
                os.kill(child.pid, number)
            tail, errors = child.communicate(timeout=10)
            expected = 0 if number is None else -9 if number == signal.SIGKILL else 128 + number
            assert child.returncode == expected and not errors
            result = json.loads(tail) if tail else None
            if expected == -9:
                assert result is None
            else:
                assert result is not None
                assert result["exit_code"] == expected and not result["committed"]
            retained = name in {
                "normal",
                "kill-empty",
                "int-content",
                "term-content",
                "term-replaced",
            }
            assert project.exists() == retained
            if content:
                assert (project / "incomplete").read_bytes() == b"uncommitted private construction"
                assert result is not None and result["notes"]
            if name == "term-replaced":
                assert moved.is_dir() and (project / "foreign").read_bytes() == b"do not delete"
                assert result is not None and result["notes"]
            if retained:
                status = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "bookscan.cli",
                        "baseline",
                        "status",
                        str(project),
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                record = json.loads(status.stdout)
                assert status.returncode == 3 and not status.stderr
                assert record["code"] == "INVALID_PROJECT" and not record["committed"]
                assert "--workdir NEW" in record["remediation"]
            else:
                with reserve(project) as resumed:
                    resumed.verify()
                    resumed.remove_empty()
            observations.append(
                {
                    "case": name,
                    "pid": child.pid,
                    "barrier": barrier,
                    "conflicts": conflicts,
                    "exit_code": expected,
                    "result": result,
                    "retained": retained,
                }
            )
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=10)
    report: dict[str, object] = {
        "format": "BookScanBuilderReservationAcceptance",
        "version": 1,
        "observations": observations,
        "public_create": False,
        "complete_finite_handoff": False,
        "composition_fidelity_verified": False,
    }
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.artifacts)
    print(
        json.dumps(
            {"cases": len(cast(list[object], result["observations"])), "public_create": False}
        )
    )


if __name__ == "__main__":
    main()
