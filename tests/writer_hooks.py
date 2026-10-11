"""Private subprocess instrumentation. No fault switches exist in the product."""

import json
import os
import signal
import sys
from pathlib import Path
from typing import BinaryIO

import pikepdf

from bookscan.publication import Staged


def install(hook: str, channel: Path) -> None:
    def ready(state: str) -> None:
        private = sorted(channel.parent.glob(".bookscan-prepare-*.tmp"))
        pending_channel = channel.with_suffix(".pending")
        pending_channel.write_text(
            json.dumps({"pid": os.getpid(), "hook": state, "private": [str(p) for p in private]})
        )
        pending_channel.chmod(0o600)
        pending_channel.replace(channel)
        sys.stdin.readline()

    original_save = pikepdf.Pdf.save
    original_link = os.link
    original_mask = signal.pthread_sigmask
    original_cleanup = Staged.cleanup
    if hook == "writing":

        def writing(self: pikepdf.Pdf, stream: BinaryIO, **kwargs: object) -> None:
            stream.write(b"%PDF-1.7\npartial writing barrier\n")
            stream.flush()
            ready("writing")
            stream.seek(0)
            stream.truncate()
            original_save(self, stream, **kwargs)  # pyright: ignore[reportArgumentType]

        pikepdf.Pdf.save = writing  # pyright: ignore[reportAttributeAccessIssue]
    elif hook in {"blocked", "after-link"}:

        def link(source: Path, destination: Path) -> None:
            if hook == "blocked":
                ready("blocked")
            original_link(source, destination)
            if hook == "after-link":
                ready("after-link")

        os.link = link  # type: ignore[assignment]
    elif hook in {"pre-region", "after-block", "committed", "pending"}:
        if hook == "pending":
            original_mask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
            original_pending = signal.sigpending

            def pending() -> set[signal.Signals]:
                ready("pending")
                return original_pending()

            signal.sigpending = pending

        def mask(how: int, signals: set[signal.Signals]) -> set[signal.Signals]:
            if hook == "pre-region" and how == signal.SIG_BLOCK:
                ready(hook)
            if hook == "committed" and how == signal.SIG_SETMASK:
                ready("committed")
            previous = original_mask(how, signals)
            if hook == "after-block" and how == signal.SIG_BLOCK:
                ready("after-block")
            return {signal.Signals(s) for s in previous}

        signal.pthread_sigmask = mask
    elif hook == "cleanup":

        def cleanup(self: Staged) -> None:
            ready("cleanup")
            original_cleanup(self)

        Staged.cleanup = cleanup
    elif hook in {"validation", "cleanup-interrupted"}:
        import bookscan.copying as copying

        original_project = copying.project_page
        first = True

        def project(page: pikepdf.Object):
            nonlocal first
            if first:
                first = False
                ready(hook)
            return original_project(page)

        copying.project_page = project
        if hook == "cleanup-interrupted":
            original_unlink = Path.unlink

            def unlink(self: Path, missing_ok: bool = False) -> None:
                if self.name.startswith(".bookscan-prepare-"):
                    ready("cleanup-second-signal")
                original_unlink(self, missing_ok=missing_ok)

            Path.unlink = unlink
    elif hook == "recheck":
        from bookscan.prepare import Source

        original_recheck = Source.recheck

        def recheck(self: Source) -> None:
            ready(hook)
            original_recheck(self)

        Source.recheck = recheck
    elif hook == "finish":
        original_fsync = os.fsync

        def fsync(descriptor: int) -> None:
            ready(hook)
            original_fsync(descriptor)

        os.fsync = fsync
    elif hook == "dry-traversal":
        import bookscan.prepare as preparation

        original_project = preparation.project_page

        def project_source(page: pikepdf.Object):
            ready(hook)
            return original_project(page)

        preparation.project_page = project_source
    elif hook == "after-open":
        original_open = os.open

        def opened(
            path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            flags: int,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> int:
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if flags & os.O_CREAT:
                ready(hook)
            return descriptor

        os.open = opened
    elif hook in {"plan-emit", "error-emit"}:
        import bookscan.cli as cli
        from bookscan.results import Json

        original_emit = cli.emit

        def emit(record: dict[str, Json], json_mode: bool) -> str:
            ready(hook)
            return original_emit(record, json_mode)

        cli.emit = emit
    elif hook == "cleanup-error":
        import bookscan.copying as copying
        from bookscan.publication import failure

        def invalid(*_args: object) -> None:
            raise failure("OUTPUT_INVALID", "Controlled original validation error.")

        copying.validate = invalid
        original_unlink = Path.unlink

        def unlink_error(self: Path, missing_ok: bool = False) -> None:
            if self.name.startswith(".bookscan-prepare-"):
                ready(hook)
            original_unlink(self, missing_ok=missing_ok)

        Path.unlink = unlink_error
