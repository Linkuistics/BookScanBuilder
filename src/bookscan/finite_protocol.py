"""Finite invocation grammar and delivery, independent of project/tool I/O.

This boundary parses the agreed commands; their actual state operations must be
connected before any successful finite result can be produced.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TextIO

from bookscan.results import Json

VALUE_OPTIONS = frozenset(
    {
        "--workdir",
        "--output",
        "--page",
        "--receipt",
        "--reason",
        "--decision",
        "--scope",
        "--viewer",
        "--scale",
        "--note",
    }
)

# Closed version-1 grammar, not an extensible command registry.
REQUIRED: dict[str, tuple[str, ...]] = {
    "baseline.create": ("--workdir",),
    "baseline.status": (),
    "baseline.views": ("--output",),
    "baseline.disposition": ("--receipt", "--reason", "--decision", "--note"),
    "baseline.inspected": ("--receipt", "--scope", "--viewer", "--scale", "--note"),
    "baseline.acknowledge": ("--receipt", "--note"),
    "export": ("--output",),
}
OPTIONAL: dict[str, tuple[str, ...]] = {
    "baseline.status": ("--output",),
    "baseline.views": ("--page", "--all"),
    "baseline.acknowledge": ("--page", "--all"),
}
EXAMPLES: dict[str, tuple[str, str]] = {
    "baseline.create": (
        "bookscan baseline create Book.pdf --workdir Project",
        "bookscan baseline create 'Prepared book.pdf' --workdir 'Book project' --json",
    ),
    "baseline.status": (
        "bookscan baseline status Project --json",
        "bookscan baseline status 'Book project'",
    ),
    "baseline.views": (
        "bookscan baseline views Project --page occ-000020 --output Views",
        "bookscan baseline views 'Book project' --all --output 'All page views'",
    ),
    "baseline.disposition": (
        "bookscan baseline disposition Project --receipt Views/full.json "
        "--reason skew-nonzero --decision reject --note 'Keep baseline'",
        "bookscan baseline disposition 'Book project' --receipt 'Page views/full.json' "
        "--reason orientation-unverified --decision retain-unresolved --note 'Unverified'",
    ),
    "baseline.inspected": (
        "bookscan baseline inspected Project --receipt Views/full.json --scope full "
        "--viewer Preview --scale 'Fit page' --note 'Inspected full view'",
        "bookscan baseline inspected 'Book project' --receipt 'Page views/native-001.json' "
        "--scope native --viewer Preview --scale 'Measured 1:1' --note 'Named tile only'",
    ),
    "baseline.acknowledge": (
        "bookscan baseline acknowledge Project --receipt Summary/receipt.json "
        "--all --note 'Export unresolved pages'",
        "bookscan baseline acknowledge 'Book project' --receipt 'Summary B/receipt.json' "
        "--page occ-000001 --page occ-000002 --note 'Named selection'",
    ),
    "export": (
        "bookscan export Project --output Baseline.pdf --json",
        "bookscan export 'Book project' --output 'Baseline book.pdf'",
    ),
}
USAGE: dict[str, str] = {
    "baseline.create": "bookscan baseline create PDF --workdir PROJECT",
    "baseline.status": "bookscan baseline status PROJECT [--output DIR]",
    "baseline.views": "bookscan baseline views PROJECT --page ID|--all --output DIR",
    "baseline.disposition": "bookscan baseline disposition PROJECT --receipt FILE --reason ID "
    "--decision reject|retain-unresolved --note TEXT",
    "baseline.inspected": "bookscan baseline inspected PROJECT --receipt FILE "
    "--scope full|native|source-native --viewer TEXT --scale TEXT --note TEXT",
    "baseline.acknowledge": "bookscan baseline acknowledge PROJECT --receipt FILE "
    "--page ID|--all --note TEXT",
    "export": "bookscan export PROJECT --output PDF",
}
ACTIONS = ("baseline.disposition", "baseline.inspected", "baseline.acknowledge")
UNAVAILABLE = (
    "Packets and export are not yet available in this unfinished implementation. "
    "process/review are reserved for foreground browser servers; they never alias finite commands."
)
REMEDY = (
    "Use bookscan --help for command availability. The agreed finite forms include "
    "bookscan baseline create 'Book.pdf' --workdir 'Book project' and "
    "bookscan baseline status 'Book project'. "
    "Create imports and saves a baseline; status without --output verifies it; "
    "views, status --output and export remain unavailable until implemented; "
    "use bookscan prepare --help for the available preparation command."
)


@dataclass(frozen=True)
class Flags:
    tokens: tuple[str, ...]
    help: bool
    json: bool
    json_count: int


@dataclass(frozen=True)
class Request:
    operation: str
    subject: str
    options: Mapping[str, tuple[str, ...]]
    json: bool


@dataclass
class Delivery:
    failed: bool = False


@dataclass
class InvocationError(Exception):
    operation: str | None
    code: str
    message: str
    remediation: str

    def record(self) -> dict[str, Json]:
        return {
            "schema": "BookScanBuilderCommandResult",
            "schema_version": 1,
            "operation": self.operation,
            "status": "error",
            "exit_code": 2,
            "project_id": None,
            "review_revision": None,
            "snapshot_id": None,
            "output": None,
            "committed": False,
            "warnings": [],
            "replayed": False,
            "current_review_revision": None,
            "code": self.code,
            "message": self.message,
            "remediation": self.remediation,
            "affected_ids": [],
            "context": {},
        }


def scan(args: list[str]) -> Flags:
    """Recognize standalone help/JSON without opening or interpreting any path.

    Known value options consume their next token verbatim, even --help/--json.
    After -- every token is positional data, including further -- tokens.
    """
    tokens: list[str] = []
    help_mode = False
    count = 0
    index = 0
    while index < len(args):
        token = args[index]
        index += 1
        if token == "--":
            tokens.extend([token, *args[index:]])
            break
        if token == "--help":
            help_mode = True
        elif token == "--json":
            count += 1
        else:
            tokens.append(token)
            if token in VALUE_OPTIONS and index < len(args):
                tokens.append(args[index])
                index += 1
    return Flags(tuple(tokens), help_mode, count > 0, count)


def _operation(tokens: tuple[str, ...]) -> tuple[str | None, int]:
    if tokens and tokens[0] == "export":
        return "export", 1
    if len(tokens) >= 2 and tokens[0] == "baseline":
        operation = "baseline." + tokens[1]
        if operation in REQUIRED:
            return operation, 2
    return None, 0


def parse(args: list[str]) -> Request:
    """Parse the closed finite grammar into immutable lexical request data.

    Presence/authenticity/current reason domains belong to the state operation;
    this parser neither opens receipts nor infers identities from ordinals.
    """
    flags = scan(args)
    operation, start = _operation(flags.tokens)
    if operation is None:
        raise InvocationError(None, "COMMAND_UNAVAILABLE", "Unknown or reserved command.", REMEDY)

    def invalid(message: str) -> InvocationError:
        return InvocationError(operation, "INVALID_ARGUMENT", message, "Use " + USAGE[operation])

    if flags.json_count > 1:
        raise invalid("--json is a singleton option.")
    values: list[str] = []
    options: dict[str, tuple[str, ...]] = {}
    allowed = set(REQUIRED[operation]) | set(OPTIONAL.get(operation, ()))
    index = start
    positional = False
    while index < len(flags.tokens):
        token = flags.tokens[index]
        index += 1
        if not positional and token == "--":
            positional = True
        elif not positional and token.startswith("-"):
            if token not in allowed:
                raise invalid("Unknown option: " + token)
            if token in options and not (operation == "baseline.acknowledge" and token == "--page"):
                raise invalid("Repeated singleton option: " + token)
            if token == "--all":
                options[token] = ()
            else:
                if index == len(flags.tokens):
                    raise invalid("Missing value for " + token)
                value = flags.tokens[index]
                index += 1
                if not value and token != "--note":
                    raise invalid("Empty value for " + token)
                options[token] = (*options.get(token, ()), value)
        else:
            values.append(token)
    if len(values) != 1 or not values[0]:
        raise invalid("Exactly one nonempty PDF/project path is required.")
    for required in REQUIRED[operation]:
        if required not in options:
            raise invalid("Missing required option " + required)
    if operation in ("baseline.views", "baseline.acknowledge"):
        if ("--all" in options) == ("--page" in options):
            raise invalid("Exactly one of --page or --all is required.")
    if "--decision" in options and options["--decision"][0] not in ("reject", "retain-unresolved"):
        raise invalid("Decision must be reject or retain-unresolved for the named reason.")
    if "--scope" in options and options["--scope"][0] not in ("full", "native", "source-native"):
        raise invalid("Inspection scope must be full, native or source-native.")
    return Request(operation, values[0], MappingProxyType(options), flags.json)


def help_text(args: list[str]) -> str:
    operation, _ = _operation(scan(args).tokens)
    selected = [operation] if operation is not None else list(REQUIRED)
    lines = [
        "BookScanBuilder finite baseline commands — agreed interface, implementation unfinished",
        UNAVAILABLE,
        "Available: prepare, baseline create, baseline status PROJECT without --output and",
        "baseline disposition|inspected|acknowledge for receipts this project issued.",
        "Packet publication (views, status --output) is not yet available, so no command",
        "issues a receipt yet; export is not yet available either.",
        "Baseline/export always remain finite; no prompt,",
        "pager or automatic viewer. process/review will be blocking from their first release.",
        "",
    ]
    for name in selected:
        lines.extend(["Usage: " + USAGE[name], "Examples (see availability above):"])
        lines.extend("  " + example for example in EXAMPLES[name])
        lines.append("")
    lines.extend(
        [
            "--json: one BookScanBuilderCommandResult v1; diagnostics on stderr.",
            "--help: human help/0 even with --json; reads no input/project/dependency/cache.",
            "Only standalone flags before -- count. --note '--help' is literal data.",
            "Quote paths with spaces; use ./ for a leading-dash path or put positionals after --.",
            "Finite limits: unchanged 300-dpi full MediaBox RGB; no estimate is applied.",
            "Orientation/fractional/crop/split/group edits are unsupported. Blanks, duplicates and",
            "order remain. Import can lose source detail/colour or reveal CropBox-hidden content.",
            "Saved baseline is uninspected. Disposition, inspection and acknowledgement differ.",
            "Every page retains orientation and within-page geometry unverified; reject only",
            "dismisses a skew-nonzero suggestion. Other limitations permit retain-unresolved only.",
            "Native means one image pixel per framebuffer pixel. Use the supplied pixel ruler,",
            "measure actual viewer/display backing scale and named tile region at actual size.",
            "A percentage/fit/full view is no 1:1 claim; source-native resolution is separate.",
            "After any review-fact action refresh all packets and inspect the new named view.",
            "Annotate a separate copy: viewer autosaves invalidate new receipt actions.",
            "One receipt permits one request plus identical durable retries; reuse conflicts fail.",
            "Acknowledgement covers an exact current snapshot; partial scope never drops pages.",
            "New project/packet/output destinations must be unused; no overwrite/--force.",
            "Fresh import loses old review facts; an export report cannot resume a project.",
            "Checkpoint/packet signals retain committed fact with 130/143; export after its",
            "successful no-clobber link retains written/0. Kill cannot promise a delivered record.",
            "Verify status/destination before retrying; never promote private orphan assets.",
            "Exits: 2 syntax/unavailable (use help); 3 invalid source/project (supported PDF,",
            "compatible reader or create into NEW with intact input; review facts are lost);",
            "4 conflict/busy (unused path or finish/Stop owner); 5 processing/dependency/I/O",
            "(process:setup or named I/O remedy); 6 receipt/review/ack (refresh/current coverage);",
            "130/143 interrupted (verify committed fact). No recovery without verified bytes.",
            "Packet publication, export and their acceptance remain unfinished.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(
    args: list[str], stdout: TextIO, stderr: TextIO, *, delivery: Delivery | None = None
) -> int:
    """Deliver help/invocation outcomes; never fabricate a successful state operation."""
    flags = scan(args)
    if flags.help:
        text, target, result = help_text(args), stdout, 0
    else:
        try:
            request = parse(args)
        except InvocationError as error:
            selected = error
        else:
            if request.operation == "baseline.status" and "--output" not in request.options:
                from bookscan.finite_status import run as run_status

                return run_status(request, stdout, stderr, delivery=delivery)
            if request.operation in ACTIONS:
                # Receipt actions read saved state only; no native tool is imported.
                from bookscan.finite_action import run as run_action

                return run_action(request, stdout, stderr, delivery=delivery)
            if request.operation == "baseline.create":
                # Native/PDF dependencies belong to the actual create route only;
                # help and invocation errors above never import them.
                from bookscan.finite_create import run as run_create

                return run_create(request, stdout, stderr, delivery=delivery)
            selected = InvocationError(
                request.operation, "COMMAND_UNAVAILABLE", UNAVAILABLE, REMEDY
            )
        record = selected.record()
        # Whole serialization precedes delivery; no second record after EPIPE.
        text = (
            (json.dumps(record, ensure_ascii=True, allow_nan=False) + "\n")
            if flags.json
            else (f"{selected.code}: {selected.message}\n{selected.remediation}\n")
        )
        target, result = (stdout if flags.json else stderr), 2
    try:
        target.write(text)
        target.flush()
    except OSError:
        if delivery is not None:
            delivery.failed = True
        try:
            stderr.write(
                "RESULT_DELIVERY_FAILED: Cannot deliver result/help. Check stdout/stderr.\n"
            )
            stderr.flush()
        except OSError:
            pass
        return result or 5
    return result
