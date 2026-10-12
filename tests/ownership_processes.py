"""Actual writer/native-child lock outcomes, with a deliberately wrong lockf control."""

import argparse
import hashlib
import json
import os
import platform
import select
import signal
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import cast

from bookscan import ownership


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _read(child: subprocess.Popen[str]) -> dict[str, object]:
    assert child.stdout is not None
    ready, _, _ = select.select([child.stdout], [], [], 10)
    if not ready:
        raise AssertionError("No actual writer/native-child barrier within 10 seconds.")
    line = child.stdout.readline()
    if not line:
        raise AssertionError("Writer exited before its observed barrier.")
    return cast(dict[str, object], json.loads(line))


def _busy(project: Path, identity: ownership.LockIdentity) -> bool:
    try:
        with ownership.Writer.acquire(project, identity):
            return False
    except ownership.OwnershipError as error:
        assert (error.code, error.exit_code) == ("PROJECT_BUSY", 4)
        return True


def run(output: Path) -> dict[str, object]:
    output.mkdir()
    project = output / "Book Project"
    project.mkdir()
    identity = ownership.provision(project)
    identity_file = output / "identity.json"
    identity_file.write_text(json.dumps(asdict(identity)))
    worker = Path(__file__).with_name("ownership_worker.py")
    records: list[dict[str, object]] = []
    original = (project / "writer.lock").read_bytes()
    for mode, number in [
        ("hold", None),
        ("process-lock", None),
        ("native", signal.SIGINT),
        ("native", signal.SIGTERM),
        ("native", signal.SIGKILL),
        ("exec-open", signal.SIGKILL),
    ]:
        command = [sys.executable, str(worker), str(project), str(identity_file), mode]
        error_path = output / f"{mode}-{number}.stderr"
        with error_path.open("w") as errors:
            child = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
                text=True,
                close_fds=True,
                env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
            )
            native_pid: int | None = None
            try:
                barrier = _read(child)
                assert barrier["writer"] == child.pid
                native_pid = cast(int | None, barrier["child"])
                native_observation: str | None = None
                if native_pid is not None:
                    native_observation = subprocess.check_output(
                        ["/bin/ps", "-p", str(native_pid), "-o", "pid=,ppid=,comm="], text=True
                    ).strip()
                    fields = native_observation.split()
                    assert fields == [str(native_pid), str(child.pid), "/bin/sleep"]
                started = time.monotonic()
                busy = _busy(project, identity)
                contention_seconds = time.monotonic() - started
                assert contention_seconds < 2, "Nonblocking acquisition unexpectedly waited."
                if mode == "process-lock":
                    assert not busy, "Wrong process lock was not observed dropping ownership."
                else:
                    assert busy, "Actual writer did not exclude a competing acquisition."
                alias = output / "Parent alias"
                if not alias.exists():
                    alias.symlink_to(output.resolve(), target_is_directory=True)
                if mode != "process-lock":
                    assert _busy(alias / project.name, identity)
                    case_alias = project.with_name(project.name.swapcase())
                    assert case_alias.exists(), "Actual filesystem case-alias test unavailable."
                    assert _busy(case_alias, identity)
                    _foreign_fails(project, identity)
                if number is None:
                    assert child.stdin is not None
                    child.stdin.write("release\n")
                    child.stdin.flush()
                else:
                    assert native_pid is not None and _alive(native_pid)
                    os.kill(child.pid, number)
                tail, _ = child.communicate(timeout=10)
                assert not tail
                expected = (
                    0 if number is None else (-9 if number == signal.SIGKILL else 128 + number)
                )
                assert child.returncode == expected
                native_alive = native_pid is not None and _alive(native_pid)
                if number == signal.SIGKILL:
                    assert native_alive, "Native child must still be alive at reacquisition."
                elif number is not None:
                    assert not native_alive, "Caught signal failed to reap its native child."
                # No polling/retry loop: reacquire once immediately after writer reap.
                with ownership.Writer.acquire(project, identity) as resumed:
                    resumed.verify()
                records.append(
                    {
                        "mode": mode,
                        "signal": int(number) if number is not None else None,
                        "command": command,
                        "barrier": barrier,
                        "writer_reaped": child.returncode,
                        "busy_before_death": busy,
                        "contention_seconds": contention_seconds,
                        "native_before_signal": native_observation,
                        "native_alive_at_reacquisition": native_alive,
                        "immediate_reacquisition": True,
                    }
                )
            finally:
                if child.poll() is None:
                    child.kill()
                    child.communicate(timeout=10)
                if native_pid is not None and _alive(native_pid):
                    os.kill(native_pid, signal.SIGKILL)
                    deadline = time.monotonic() + 5
                    while _alive(native_pid) and time.monotonic() < deadline:
                        time.sleep(0.02)
                    assert not _alive(native_pid), "Native orphan did not disappear after kill."
    assert (project / "writer.lock").read_bytes() == original
    assert (project / "writer.lock").stat().st_ino == identity.lock_inode
    record: dict[str, object] = {
        "verified": True,
        "wrong_process_lock_rejected": True,
        "case_alias_verified": True,
        "os": platform.platform(),
        "os_build": subprocess.check_output(
            ["/usr/bin/sw_vers", "-buildVersion"], text=True
        ).strip(),
        "filesystem": subprocess.check_output(["/bin/df", "-P", str(project)], text=True),
        "python": sys.version,
        "package": str(Path(ownership.__file__).resolve()),
        "product_sha256": hashlib.sha256(Path(ownership.__file__).read_bytes()).hexdigest(),
        "identity": asdict(identity),
        "records": records,
    }
    (output / "report.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def _foreign_fails(project: Path, identity: ownership.LockIdentity) -> None:
    """Corrupt-token acquisition must fail without interfering with the real owner."""
    wrong = ownership.LockIdentity(
        identity.project_device,
        identity.project_inode,
        identity.lock_device,
        identity.lock_inode,
        "f" * 32 if identity.token != "f" * 32 else "e" * 32,
    )
    try:
        with ownership.Writer.acquire(project, wrong):
            raise AssertionError("Foreign identity accepted.")
    except ownership.OwnershipError as error:
        assert (error.code, error.exit_code) == ("INVALID_PROJECT", 3)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Actual local project writer/child ownership checks."
    )
    parser.add_argument("--artifacts", required=True, type=Path)
    args = parser.parse_args()
    record = run(args.artifacts)
    print(json.dumps(record, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
