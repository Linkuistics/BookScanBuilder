"""Private actual-process reservation barrier; no public create or checkpoint claim."""

import argparse
import json
import os
import signal
from pathlib import Path
from types import FrameType

from bookscan.project_header import HeaderError
from bookscan.project_reservation import reserve


class Interrupted(Exception):
    def __init__(self, number: int) -> None:
        self.exit_code = 128 + number


def interrupt(number: int, _frame: FrameType | None) -> None:
    raise Interrupted(number)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--hold", action="store_true")
    parser.add_argument("--content", action="store_true")
    args = parser.parse_args()
    if args.hold:
        for number in (signal.SIGINT, signal.SIGTERM):
            signal.signal(number, interrupt)
    try:
        with reserve(args.project) as reservation:
            if args.content:
                (reservation.path / "incomplete").write_bytes(b"uncommitted private construction")
            if args.hold:
                print(
                    json.dumps({"pid": os.getpid(), "path": str(reservation.path), "ready": True}),
                    flush=True,
                )
                if input() != "release":
                    raise ValueError("Expected release at private barrier")
        print(json.dumps({"exit_code": 0, "committed": False}), flush=True)
        return 0
    except (HeaderError, Interrupted) as error:
        print(
            json.dumps(
                {
                    "exit_code": error.exit_code,
                    "code": error.code if isinstance(error, HeaderError) else "INTERRUPTED",
                    "notes": getattr(error, "__notes__", []),
                    "committed": False,
                }
            ),
            flush=True,
        )
        return error.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
