"""Q2 consumer-visible errors/help; real installed entry, no PDF/tool setup."""

import json
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest


def invoke(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bookscan.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


@pytest.mark.parametrize(
    "args",
    [
        ["--json", "bseline", "status", "P"],
        ["--json", "process", "X", "--workdir", "Y"],
        ["review", "P", "--json"],
        ["baseline", "wat", "--json"],
        ["--json"],
    ],
)
def test_unknown_and_reserved_commands_use_named_null_operation(args: list[str]) -> None:
    # Routing through preparation would return its unnamed schema and wrong code.
    result = invoke(args)
    assert result.returncode == 2, result.stderr
    record = json.loads(result.stdout)
    assert record == {
        "schema": "BookScanBuilderCommandResult",
        "schema_version": 1,
        "operation": None,
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
        "code": "COMMAND_UNAVAILABLE",
        "message": record["message"],
        "remediation": record["remediation"],
        "affected_ids": [],
        "context": {},
    }
    assert "bookscan baseline create" in record["remediation"]
    assert "bookscan baseline status" in record["remediation"]
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("args", "operation"),
    [
        (["baseline", "create"], "baseline.create"),
        (["baseline", "status"], "baseline.status"),
        (["baseline", "views", "P"], "baseline.views"),
        (["baseline", "disposition", "P"], "baseline.disposition"),
        (["baseline", "inspected", "P"], "baseline.inspected"),
        (["baseline", "acknowledge", "P"], "baseline.acknowledge"),
        (["export", "P"], "export"),
    ],
)
def test_recognized_argument_errors_keep_exact_operation(args: list[str], operation: str) -> None:
    result = invoke(["--json", *args])
    assert result.returncode == 2
    record = json.loads(result.stdout)
    assert (record["operation"], record["code"]) == (operation, "INVALID_ARGUMENT")
    assert record["committed"] is False
    assert record["output"] is None
    assert record["remediation"]


@pytest.mark.parametrize(
    "args",
    [
        ["--help", "--json"],
        ["baseline", "create", "missing.pdf", "--workdir", "P", "--help", "--json"],
        ["baseline", "status", "missing", "--help", "--json"],
        ["baseline", "views", "P", "--help", "--json"],
        ["baseline", "disposition", "P", "--help", "--json"],
        ["baseline", "inspected", "P", "--help", "--json"],
        ["baseline", "acknowledge", "P", "--help", "--json"],
        ["export", "P", "--help", "--json"],
        ["--unknown", "--help", "--json"],
    ],
)
def test_new_help_is_human_and_distinct_from_preparation(args: list[str]) -> None:
    result = invoke(args)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("BookScanBuilder")
    assert "not yet available" in result.stdout
    assert "--json" in result.stdout
    assert "finite" in result.stdout
    assert result.stderr == ""


def test_preparation_keeps_all_token_help_and_unnamed_record() -> None:
    help_result = invoke(["prepare", "--output", "--help", "--json"])
    assert help_result.returncode == 0
    assert help_result.stdout.startswith("PDF preparation:")
    invalid = invoke(["prepare", "--json"])
    assert invalid.returncode == 2
    record = json.loads(invalid.stdout)
    assert "schema" not in record and "operation" not in record
    assert record["schema_version"] == 1


@pytest.mark.parametrize("value", ["--help", "--json"])
def test_note_option_flags_are_data_at_the_installed_boundary(value: str) -> None:
    result = invoke(
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
            value,
        ]
    )
    # The receipt file does not exist: a live action route reports that, and the
    # literal note is never promoted to help or JSON.
    assert result.returncode == 6
    assert result.stdout == ""
    assert "INVALID_RECEIPT" in result.stderr
    assert not result.stderr.startswith("BookScanBuilder")


def test_terminator_prevents_help_and_json_promotion() -> None:
    result = invoke(["baseline", "status", "--", "--help", "--json"])
    assert result.returncode == 2
    assert result.stdout == ""
    assert "INVALID_ARGUMENT" in result.stderr


@pytest.mark.parametrize(
    ("args", "operation", "subject", "options"),
    [
        (
            ["--json", "baseline", "create", "Book.pdf", "--workdir", "Project"],
            "baseline.create",
            "Book.pdf",
            {"--workdir": ("Project",)},
        ),
        (["baseline", "status", "P"], "baseline.status", "P", {}),
        (
            ["baseline", "status", "P", "--output", "Summary"],
            "baseline.status",
            "P",
            {"--output": ("Summary",)},
        ),
        (
            ["baseline", "views", "P", "--all", "--output", "Views"],
            "baseline.views",
            "P",
            {"--all": (), "--output": ("Views",)},
        ),
        (
            ["baseline", "views", "P", "--page", "occ-000020", "--output", "Views"],
            "baseline.views",
            "P",
            {"--page": ("occ-000020",), "--output": ("Views",)},
        ),
        (
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
                "--help",
            ],
            "baseline.disposition",
            "P",
            {
                "--receipt": ("R",),
                "--reason": ("skew-nonzero",),
                "--decision": ("reject",),
                "--note": ("--help",),
            },
        ),
        (
            [
                "baseline",
                "inspected",
                "P",
                "--receipt",
                "R",
                "--scope",
                "native",
                "--viewer",
                "--json",
                "--scale",
                "--help",
                "--note",
                "",
            ],
            "baseline.inspected",
            "P",
            {
                "--receipt": ("R",),
                "--scope": ("native",),
                "--viewer": ("--json",),
                "--scale": ("--help",),
                "--note": ("",),
            },
        ),
        (
            ["baseline", "acknowledge", "P", "--receipt", "R", "--all", "--note", "N"],
            "baseline.acknowledge",
            "P",
            {"--receipt": ("R",), "--all": (), "--note": ("N",)},
        ),
        (
            [
                "baseline",
                "acknowledge",
                "P",
                "--receipt",
                "R",
                "--page",
                "B",
                "--page",
                "A",
                "--note",
                "N",
            ],
            "baseline.acknowledge",
            "P",
            {"--receipt": ("R",), "--page": ("B", "A"), "--note": ("N",)},
        ),
        (
            ["export", "--output", "Book.pdf", "--", "--help"],
            "export",
            "--help",
            {"--output": ("Book.pdf",)},
        ),
    ],
)
def test_exact_request_data_remains_lexical_and_detached(
    args: list[str], operation: str, subject: str, options: dict[str, tuple[str, ...]]
) -> None:
    from bookscan.finite_protocol import parse

    request = parse(args)
    assert (request.operation, request.subject, dict(request.options)) == (
        operation,
        subject,
        options,
    )
    args.clear()
    assert request.subject == subject and dict(request.options) == options
    with pytest.raises(TypeError):
        request.options["--note"] = ("changed",)  # type: ignore[index]


@pytest.mark.parametrize(
    "args",
    [
        ["baseline", "create", "PDF"],
        ["baseline", "create", "", "--workdir", "P"],
        ["baseline", "create", "PDF", "--workdir", ""],
        ["baseline", "status", "P", "extra"],
        ["baseline", "status", "P", "--json", "--json"],
        ["baseline", "status", "P", "--output"],
        ["baseline", "status", "P", "--output", "A", "--output", "B"],
        ["baseline", "status", "P", "--force"],
        ["baseline", "views", "P", "--all", "--page", "A", "--output", "V"],
        ["baseline", "views", "P", "--all", "--all", "--output", "V"],
        ["baseline", "views", "P", "--page", "A", "--page", "B", "--output", "V"],
        ["baseline", "views", "P", "--all"],
        [
            "baseline",
            "disposition",
            "P",
            "--receipt",
            "R",
            "--reason",
            "skew-nonzero",
            "--decision",
            "accept",
            "--note",
            "N",
        ],
        [
            "baseline",
            "inspected",
            "P",
            "--receipt",
            "R",
            "--scope",
            "all",
            "--viewer",
            "Preview",
            "--scale",
            "1:1",
            "--note",
            "N",
        ],
        ["baseline", "acknowledge", "P", "--receipt", "R", "--note", "N"],
        ["export", "P", "--output", "O", "--workdir", "W"],
        ["export", "P", "--output=O"],
    ],
)
def test_closed_grammar_refuses_before_io(args: list[str]) -> None:
    from bookscan.finite_protocol import InvocationError, parse

    with pytest.raises(InvocationError) as caught:
        parse(args)
    assert caught.value.code == "INVALID_ARGUMENT"
    assert caught.value.operation is not None


@pytest.mark.parametrize("option", ["--note", "--viewer", "--scale", "--output", "--receipt"])
def test_help_scan_consumes_values_and_stops_at_terminator(option: str) -> None:
    from bookscan.finite_protocol import scan

    first = scan(["baseline", "status", "P", option, "--help", "--json"])
    assert first.help is False and first.json is True
    second = scan(["baseline", "status", "P", option, "--json", "--help"])
    assert second.help is True and second.json is False
    third = scan(["--", "--help", "--json"])
    assert third.help is False and third.json is False


def test_help_and_invocation_errors_need_no_files_or_processes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan.finite_protocol import run

    def denied(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Unexpected input/project/dependency/cache read or process")

    # Install the boundary after imports, so package-loading is not mistaken for
    # input/tool access. Its positive control below observes an actual denied read.
    monkeypatch.setattr(Path, "read_bytes", denied)
    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    with pytest.raises(AssertionError, match="Unexpected"):
        Path("denied-input.pdf").read_bytes()
    for args in (
        ["--help", "--json"],
        ["baseline", "create", "X", "--help"],
        ["--json", "process", "X", "--workdir", "Y"],
    ):
        output, error = StringIO(), StringIO()
        assert run(args, output, error) in (0, 2)
        assert output.getvalue() and not error.getvalue()


class BrokenOutput(StringIO):
    def write(self, value: str) -> int:
        raise BrokenPipeError("closed consumer")


def test_delivery_keeps_selected_error_and_never_emits_second_record() -> None:
    from bookscan.finite_protocol import run

    stderr = StringIO()
    assert run(["--json", "bseline"], BrokenOutput(), stderr) == 2
    assert stderr.getvalue().count("RESULT_DELIVERY_FAILED") == 1
    assert run(["--help", "--json"], BrokenOutput(), BrokenOutput()) == 5


def test_installed_help_loads_no_pdf_dependency_and_denial_control_fails(tmp_path: Path) -> None:
    # Import-loader denial also catches eager prepare imports before routing.
    script = tmp_path / "deny_dependencies.py"
    script.write_text(
        "import importlib.abc, runpy, sys\n"
        "class Deny(importlib.abc.MetaPathFinder):\n"
        " def find_spec(self, fullname, path=None, target=None):\n"
        "  if fullname.split('.')[0] in ('pikepdf', 'PIL'):\n"
        "   raise RuntimeError('observed denied dependency read: ' + fullname)\n"
        "sys.meta_path.insert(0, Deny())\n"
        "if sys.argv[1] == 'control':\n"
        " import pikepdf\n"
        "else:\n"
        " sys.argv = ['bookscan', *sys.argv[1:]]\n"
        " runpy.run_module('bookscan.cli', run_name='__main__')\n"
    )
    control = subprocess.run(
        [sys.executable, str(script), "control"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert control.returncode != 0 and "observed denied dependency read" in control.stderr
    result = subprocess.run(
        [sys.executable, str(script), "baseline", "create", "X", "--help", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("BookScanBuilder")


def test_real_installed_protocol_denial_and_pipe_runner(tmp_path: Path) -> None:
    import finite_protocol_acceptance

    result = finite_protocol_acceptance.run(
        tmp_path / "acceptance", Path(sys.executable).with_name("bookscan")
    )
    assert result["complete_finite_handoff"] is False
    assert result["denied_read_control"] is True
    assert result["epipe"] == {"selected_error": 2, "help": 5}
    assert result["preparation_unchanged"] is True
    assert len(result["cases"]) == 22
