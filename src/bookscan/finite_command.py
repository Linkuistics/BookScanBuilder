"""Signal lifetime and result envelope shared by the finite state operations.

A handler only records the first caught signal; it never raises from an arbitrary
bytecode. Each operation polls ``Control.check`` at its own safe boundaries, so
ownership, child reap and cleanup are never interrupted midway.
"""

import signal
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from types import FrameType


@dataclass
class Interrupted(Exception):
    exit_code: int
    code: str = "INTERRUPTED"
    message: str = "Status verification interrupted; no new checkpoint or packet committed."
    remediation: str = "Verify saved state with bookscan baseline status PROJECT before retrying."


@dataclass
class Control:
    caught: int | None = None

    def interrupt(self, number: int, _frame: FrameType | None) -> None:
        if self.caught is None:
            self.caught = number

    def check(self) -> None:
        if self.caught is not None:
            raise Interrupted(128 + self.caught)


@contextmanager
def signals(control: Control) -> Iterator[None]:
    handlers: dict[signal.Signals, int | Callable[[int, FrameType | None], None] | None] = {}
    try:
        for number in (signal.SIGINT, signal.SIGTERM):
            handlers[number] = signal.signal(number, control.interrupt)
        yield
    finally:
        for number, handler in handlers.items():
            if handler is not None:
                signal.signal(number, handler)


def envelope(operation: str) -> dict[str, object]:
    """The version-1 CommandResult skeleton: an error with every nullable field null."""
    return {
        "schema": "BookScanBuilderCommandResult",
        "schema_version": 1,
        "operation": operation,
        "status": "error",
        "exit_code": 0,
        "project_id": None,
        "review_revision": None,
        "snapshot_id": None,
        "output": None,
        "committed": False,
        "warnings": [],
        "replayed": False,
        "current_review_revision": None,
    }
