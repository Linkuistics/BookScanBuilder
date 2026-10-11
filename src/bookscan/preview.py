"""Temporary explicitly dry-run module, deliberately no installed write entry."""

import json
import os
import signal
import sys
from collections.abc import Callable
from pathlib import Path
from types import FrameType
from typing import TextIO

from bookscan.prepare import plan
from bookscan.results import Json, PreparationError
from bookscan.selections import parse

HELP = """PDF preparation preview (temporary; produces no PDF)
Usage: uv run --locked python -m bookscan.preview [OPTIONS] --dry-run

--front PDF [PAGES]    Repeatable explicit front pages.
--content PDF [PAGES]  Repeatable content (required); interior covers are content.
--back PDF [PAGES]     Repeatable explicit back pages.
--output PDF          New destination in an existing directory; no overwrite.
--dry-run             Required in this preview. Hash every source and run all
                      preservation gates and stability checks. No output or
                      temporary file, copying, save, or permission trial occurs.
                      A plan is no reservation or promise that writing succeeds.
--json                One schema-version-1 result, including structured errors.
--help                This help takes precedence; opens no inputs.

Order: all front, then content, then back, regardless of argument interleaving;
retain order within each role and each selection. No inference/deduplication.
Pages are one-based PDF pages: all, N, inclusive A-B (ascending/descending).
Comma-separated, no whitespace. !N and !A-B exclude their union from this
selection only. Exclusions alone start with all. Repetitions are retained.
Single-quote ! expressions in interactive zsh/bash, e.g. 'all,!3'.
Errors never clamp ranges or overwrite sources. No automatic retry; after an
interruption inspect the destination and choose a new path if it exists.
Supported: static PDF 1.0–1.7, bounded ADBE 1.7 levels 1–3, static appearances;
no encryption, recovery, interactive forms/media, external/optional rendering.

Examples (quoted paths, explicit roles):
  --content 'Assembled Book.pdf' --output 'Prepared.pdf' --dry-run
  --front 'Covers.pdf' 1 --content 'Book.pdf' 'all,!3' --back 'Covers.pdf' 4 \\
    --output 'Prepared.pdf' --dry-run --json
  --content 'Book.pdf' 2 --content 'Covers.pdf' 3 --content 'Book.pdf' 1 \\
    --output 'Interior cover.pdf' --dry-run
"""


def interrupt(signum: int, _frame: FrameType | None) -> None:
    raise PreparationError(
        "INTERRUPTED",
        f"Caught signal {signum} before publication.",
        "Inspect the destination before retrying; keep sources stable.",
        128 + signum,
    )


def emit(record: dict[str, Json], json_mode: bool) -> str:
    if json_mode:
        return json.dumps(record, ensure_ascii=True, allow_nan=False) + "\n"
    if record["status"] == "error":
        return f"{record['code']}: {record['message']}\n{record['remediation']}\n"
    lines: list[str] = []
    pages = record["pages"]
    assert isinstance(pages, list)
    for page in pages:
        assert isinstance(page, dict)
        lines.append(
            f"{page['output_page']}: {page['role']} {page['source']} PDF page {page['source_page']}"
        )
    lines.append(f"Total: {record['page_count']} pages; destination: {record['output']}")
    return "\n".join(lines) + "\n"


def run(args: list[str], stdout: TextIO, stderr: TextIO) -> int:
    json_mode = "--json" in args
    output: str | None = None
    exit_code = 0
    try:
        if "--help" in args:
            try:
                stdout.write(HELP)
                stdout.flush()
                return 0
            except OSError:
                try:
                    stderr.write("RESULT_DELIVERY_FAILED: Cannot deliver help. Check stdout.\n")
                    stderr.flush()
                except OSError:
                    pass
                return 5
        # Resolve an available output even when parsing later fails.
        if "--output" in args:
            i = args.index("--output") + 1
            if i < len(args) and not args[i].startswith("-"):
                output = str(Path(args[i]).absolute())
        request = parse(args, preview=True)
        output = str(request.output)
        record = plan(request).record()
    except PreparationError as exc:
        record = exc.record(output)
        exit_code = exc.exit_code
    text = emit(record, json_mode)  # Serialize completely before the first output byte.
    try:
        target = stdout if json_mode or exit_code == 0 else stderr
        target.write(text)
        target.flush()
    except OSError:
        try:
            stderr.write(
                "RESULT_DELIVERY_FAILED: Cannot deliver/flush result. "
                "Check stdout/stderr and rerun the preview.\n"
            )
            stderr.flush()
        except OSError:
            pass
        return exit_code or 5
    return exit_code


def main() -> int:
    handlers: dict[signal.Signals, int | Callable[[int, FrameType | None], None] | None] = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        handlers[sig] = signal.signal(sig, interrupt)
    try:
        result = run(sys.argv[1:], sys.stdout, sys.stderr)
        if result == 5:
            # Avoid Python's shutdown reflush turning EPIPE's defined exit 5 into exit 120.
            sys.stdout = open(os.devnull, "w")
        return result
    finally:
        for sig, handler in handlers.items():
            if handler is not None:
                signal.signal(sig, handler)


if __name__ == "__main__":
    sys.exit(main())
