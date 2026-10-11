"""One private stream and an atomic, signal-protected no-clobber commit point."""

import os
import secrets
import signal
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import BinaryIO

from bookscan.results import Json, PreparationError


def failure(code: str, message: str, exit_code: int = 5) -> PreparationError:
    return PreparationError(
        code, message, "Inspect the destination and choose a new path to retry.", exit_code
    )


@dataclass
class Control:
    committed: bool = False
    warnings: list[Json] = field(default_factory=lambda: list[Json]())

    def warn(self, code: str, message: str) -> None:
        self.warnings.append(
            {
                "code": code,
                "message": message,
                "remediation": "Inspect the destination and any named private file.",
            }
        )

    def interrupt(self, signum: int, _frame: FrameType | None) -> None:
        if self.committed:
            self.warn("POST_COMMIT_SIGNAL", f"Caught signal {signum} after publication.")
        else:
            raise failure(
                "INTERRUPTED", f"Caught signal {signum} before publication.", 128 + signum
            )


def startup_mode() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return 0o666 & ~mask


@dataclass
class Staged:
    stream: BinaryIO
    path: Path
    destination: Path
    mode: int
    control: Control

    @classmethod
    def create(cls, destination: Path, mode: int, control: Control) -> "Staged":
        path = destination.parent / f".bookscan-prepare-{secrets.token_hex(16)}.tmp"
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        except OSError as exc:
            raise failure(
                "WRITE_FAILED", f"Cannot create private staged file in {destination.parent}"
            ) from exc
        try:
            # A restrictive umask may strip owner bits; the private file is exactly 0600.
            os.fchmod(descriptor, 0o600)
            stream = os.fdopen(descriptor, "w+b")
        except OSError as exc:
            os.close(descriptor)
            try:
                path.unlink()
            except OSError:
                control.warn("TEMP_CLEANUP_FAILED", f"Cannot remove private file: {path}")
            raise failure("WRITE_FAILED", f"Cannot open private staged stream: {path}") from exc
        return cls(stream, path, destination, mode, control)

    def finish(self) -> None:
        try:
            self.stream.flush()
            os.fchmod(self.stream.fileno(), self.mode)
            os.fsync(self.stream.fileno())
        except OSError as exc:
            raise failure(
                "WRITE_FAILED", f"Cannot flush/set mode/fsync staged file: {self.path}"
            ) from exc

    def commit(self) -> None:
        blocked = {signal.SIGINT, signal.SIGTERM}
        # POSIX signal masking closes the Python between-bytecodes link/state window.
        # https://docs.python.org/3.12/library/signal.html#signal.pthread_sigmask
        pending = signal.sigpending() & blocked
        old = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
        try:
            if pending:
                signum = min(int(sig) for sig in pending)
                raise failure(
                    "INTERRUPTED", f"Signal {signum} pending before publication.", 128 + signum
                )
            try:
                os.link(self.path, self.destination)
            except FileExistsError as exc:
                raise failure(
                    "OUTPUT_EXISTS", f"Destination already exists: {self.destination}", 4
                ) from exc
            except OSError as exc:
                raise failure(
                    "PUBLISH_FAILED", f"Cannot atomically link destination: {self.destination}"
                ) from exc
            self.control.committed = True
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, old)

    def cleanup(self) -> None:
        try:
            self.stream.close()
        except OSError:
            self.control.warn("TEMP_CLEANUP_FAILED", f"Cannot close private stream: {self.path}")
        try:
            self.path.unlink()
        except OSError:
            self.control.warn("TEMP_CLEANUP_FAILED", f"Cannot remove private file: {self.path}")
