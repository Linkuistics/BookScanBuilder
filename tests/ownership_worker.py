"""Private real process for ownership acceptance; never installed as a product route."""

import argparse
import fcntl
import json
import os
import shlex
import signal
import subprocess
import sys
from pathlib import Path
from typing import cast

from bookscan.native_setup import execute
from bookscan.ownership import LockIdentity, Writer


class Interrupted(Exception):
    pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("identity", type=Path)
    parser.add_argument("mode", choices=["hold", "process-lock", "native", "exec-open"])
    args = parser.parse_args()
    fields = cast(dict[str, object], json.loads(args.identity.read_text()))
    numbers = [
        fields[key] for key in ("project_device", "project_inode", "lock_device", "lock_inode")
    ]
    assert all(type(value) is int for value in numbers) and isinstance(fields["token"], str)
    identity = LockIdentity(*cast(tuple[int, int, int, int], tuple(numbers)), fields["token"])
    if args.mode == "process-lock":
        setattr(fcntl, "flock", fcntl.lockf)  # Private wrong-kernel-mechanism control.
    signum = 0

    def cancelled(number: int, frame: object) -> None:
        nonlocal signum
        signum = number

    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, cancelled)
    try:
        with Writer.acquire(args.project, identity) as owner:
            # Closing an independent verification descriptor must not drop ownership.
            extra = os.open(args.project / "writer.lock", os.O_RDONLY)
            os.close(extra)
            owner.verify()

            def ready(child: int | None) -> None:
                print(
                    json.dumps({"writer": os.getpid(), "child": child, "path": str(owner.path)}),
                    flush=True,
                )

            if args.mode in {"hold", "process-lock"}:
                ready(None)
                if sys.stdin.readline().strip() != "release":
                    return 10
                owner.verify()
            elif args.mode == "exec-open":
                # Even an exec deliberately retaining all inheritable descriptors
                # must not retain either project descriptor (both CLOEXEC).
                child = subprocess.Popen(
                    ["/bin/sleep", "60"],
                    close_fds=False,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                ready(child.pid)
                child.wait()
            else:
                pidfile = args.project / f"native-pid-{os.getpid()}"
                emitted = False

                def check() -> None:
                    nonlocal emitted
                    if signum:
                        raise Interrupted
                    if not emitted and pidfile.exists():
                        pid = int(pidfile.read_text())
                        command = subprocess.check_output(
                            ["/bin/ps", "-p", str(pid), "-o", "comm="], text=True
                        ).strip()
                        if command == "/bin/sleep":
                            ready(pid)
                            emitted = True

                execute(
                    [
                        "/bin/sh",
                        "-c",
                        f'echo "$$" > {shlex.quote(str(pidfile))}; exec /bin/sleep 60',
                    ],
                    check_cancel=check,
                )
        return 0
    except Interrupted:
        return 128 + signum


if __name__ == "__main__":
    sys.exit(main())
