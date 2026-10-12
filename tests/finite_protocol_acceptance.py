"""Actual installed Q2 entry, Mac read denial and real EPIPE (no state success).

The executable parameter lets the identical cases exercise an installed wheel.
This test-owned runner introduces no public product fault option or native API.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TypedDict


class Report(TypedDict):
    complete_finite_handoff: bool
    denied_read_control: bool
    epipe: dict[str, int]
    preparation_unchanged: bool
    cases: dict[str, dict[str, object]]
    executable: dict[str, str]


def invoke(command: list[str], args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*command, *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


def broken_pipe(command: list[str], args: list[str]) -> subprocess.CompletedProcess[str]:
    reader, writer = os.pipe()
    os.close(reader)  # No reader exists before the actual installed process starts.
    try:
        return subprocess.run(
            [*command, *args],
            stdout=writer,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=20,
        )
    finally:
        os.close(writer)


def run(directory: Path, executable: Path) -> Report:
    directory.mkdir()
    blocked = directory / "blocked"
    blocked.mkdir()
    source = blocked / "Input.pdf"
    source.write_bytes(b"not a PDF; a help/parser path must never open this")
    (blocked / "Project").mkdir()
    (blocked / "cache").mkdir()
    before = source.read_bytes()
    # Deny real filesystem access to input/project/cache/collection and PDF/RGB
    # dependency packages. Library loading for this interface must be unnecessary.
    packages = Path(sys.executable).parent.parent / "lib" / "python3.12" / "site-packages"
    denied = [
        blocked,
        Path("/Volumes/Glass/Book Conversion"),
        packages / "pikepdf",
        packages / "PIL",
    ]
    profile = "(version 1)(allow default)" + "".join(
        "(deny file-read* (subpath " + json.dumps(str(path.resolve())) + "))" for path in denied
    )
    profile_path = directory / "read-denial.sb"
    profile_path.write_text(profile)
    prefix = ["/usr/bin/sandbox-exec", "-f", str(profile_path)]
    control = invoke([*prefix, "/bin/cat"], [str(source)])
    assert control.returncode != 0 and "Operation not permitted" in control.stderr, control
    command = [*prefix, str(executable)]
    cases: dict[str, dict[str, object]] = {}
    for name, args in [
        ("help.top", []),
        ("help.create", ["baseline", "create", str(source), "--workdir", str(blocked / "Project")]),
        ("help.status", ["baseline", "status", str(blocked / "Project")]),
        ("help.views", ["baseline", "views"]),
        ("help.disposition", ["baseline", "disposition"]),
        ("help.inspected", ["baseline", "inspected"]),
        ("help.acknowledge", ["baseline", "acknowledge"]),
        ("help.export", ["export"]),
    ]:
        value = invoke(command, [*args, "--help", "--json"])
        assert value.returncode == 0 and value.stdout.startswith("BookScanBuilder"), value
        assert value.stderr == "" and "not yet available" in value.stdout
        cases[name] = {"exit": value.returncode, "stdout": value.stdout, "stderr": value.stderr}
    for operation, args in [
        ("baseline.create", ["baseline", "create"]),
        ("baseline.status", ["baseline", "status"]),
        ("baseline.views", ["baseline", "views", "P"]),
        ("baseline.disposition", ["baseline", "disposition", "P"]),
        ("baseline.inspected", ["baseline", "inspected", "P"]),
        ("baseline.acknowledge", ["baseline", "acknowledge", "P"]),
        ("export", ["export", "P"]),
    ]:
        value = invoke(command, ["--json", *args])
        record = json.loads(value.stdout)
        assert value.returncode == 2 and value.stderr == ""
        assert record["operation"] == operation and record["code"] == "INVALID_ARGUMENT"
        assert record["schema"] == "BookScanBuilderCommandResult" and record["committed"] is False
        cases["invalid." + operation] = {"exit": value.returncode, "record": record}
    for name, args in [
        ("unknown", ["bseline", "status", "P"]),
        ("process", ["process", str(source), "--workdir", str(blocked / "Project")]),
        ("review", ["review", str(blocked / "Project")]),
    ]:
        value = invoke(command, ["--json", *args])
        record = json.loads(value.stdout)
        assert value.returncode == 2 and record["operation"] is None and value.stderr == ""
        assert record["code"] == "COMMAND_UNAVAILABLE" and record["current_review_revision"] is None
        cases[name] = {"exit": value.returncode, "record": record}
    for note in ("--help", "--json"):
        value = invoke(
            command,
            [
                "baseline",
                "disposition",
                "P",
                "--receipt",
                "R",
                "--reason",
                "skew-nonzero",
                "--decision",
                "reject",
                "--note",
                note,
            ],
        )
        # The action route is live: the note is data, not help, and the absent
        # receipt file is the selected INVALID_RECEIPT/6 before any project read.
        assert value.returncode == 6 and value.stdout == "" and "INVALID_RECEIPT" in value.stderr
        assert not value.stderr.startswith("BookScanBuilder")
        cases["literal." + note] = {"exit": value.returncode, "stderr": value.stderr}
    for literal in ("--help", "--json"):
        # Keep this no-I/O grammar check on the unimplemented summary form;
        # plain status now legitimately loads/verifies saved project bytes.
        value = invoke(command, ["baseline", "status", "--output", "Summary", "--", literal])
        assert (
            value.returncode == 2 and value.stdout == "" and "COMMAND_UNAVAILABLE" in value.stderr
        )
        cases["terminator." + literal] = {"exit": value.returncode, "stderr": value.stderr}
    pipe_error = broken_pipe(command, ["--json", "bseline"])
    pipe_help = broken_pipe(command, ["--help", "--json"])
    assert pipe_error.returncode == 2 and pipe_help.returncode == 5
    assert pipe_error.stderr.count("RESULT_DELIVERY_FAILED") == 1
    assert pipe_help.stderr.count("RESULT_DELIVERY_FAILED") == 1
    for name, result in (("pipe-error", pipe_error), ("pipe-help", pipe_help), ("denied", control)):
        (directory / (name + ".stderr")).write_text(result.stderr)
    # Preparation must retain the existing unnamed record/all-token help. It
    # legitimately loads its PDF library on an actual operation, outside denial.
    prepare_help = invoke([str(executable)], ["prepare", "--output", "--help", "--json"])
    prepare_error = invoke([str(executable)], ["prepare", "--json"])
    old = json.loads(prepare_error.stdout)
    assert prepare_help.returncode == 0 and prepare_help.stdout.startswith("PDF preparation:")
    assert prepare_error.returncode == 2 and "schema" not in old and "operation" not in old
    assert source.read_bytes() == before
    assert sorted(path.name for path in blocked.iterdir()) == ["Input.pdf", "Project", "cache"]
    report: Report = {
        "complete_finite_handoff": False,
        "denied_read_control": True,
        "epipe": {"selected_error": pipe_error.returncode, "help": pipe_help.returncode},
        "preparation_unchanged": True,
        "cases": cases,
        "executable": {
            "path": str(executable),
            "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        },
    }
    (directory / "result.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument(
        "--executable", type=Path, default=Path(sys.executable).with_name("bookscan")
    )
    args = parser.parse_args()
    result = run(args.artifacts.absolute(), args.executable.absolute())
    print(
        json.dumps(
            {
                "cases": len(result["cases"]),
                "denied_read_control": result["denied_read_control"],
                "epipe": result["epipe"],
                "preparation_unchanged": result["preparation_unchanged"],
                "complete_finite_handoff": result["complete_finite_handoff"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
