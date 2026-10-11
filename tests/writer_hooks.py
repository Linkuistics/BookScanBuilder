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
