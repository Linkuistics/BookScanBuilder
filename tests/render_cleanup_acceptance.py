"""Observe actual pinned Poppler writes into precreated PNGs and exact cleanup.

Uses the existing independently constructed renderer corpus and wrong-subject
controls. This private observer supplies no installed public-create acceptance.
"""

import argparse
import json
import stat
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path

from render_acceptance import run as render_run

from bookscan import render
from bookscan.import_publications import stamp


def run(artifacts: Path) -> dict[str, object]:
    artifacts.mkdir()
    original = render.execute
    records: list[dict[str, object]] = []
    directories: list[Path] = []

    def execute(
        argv: list[str],
        *,
        check_cancel: Callable[[], None] = lambda: None,
        environment: Mapping[str, str] | None = None,
        directory: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if "-png" not in argv:
            return original(
                argv, check_cancel=check_cancel, environment=environment, directory=directory
            )
        target = Path(argv[-1] + ".png")
        before = target.lstat()
        root = target.parent.lstat()
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == 0
        assert before.st_mode & 0o777 == 0o600
        assert {p.name for p in target.parent.iterdir()} == {"page.png"}
        result = original(
            argv, check_cancel=check_cancel, environment=environment, directory=directory
        )
        after = target.lstat()
        assert result.returncode == 0 and after.st_size > 0
        assert stamp(before)[:4] == stamp(after)[:4]
        assert stamp(root) == stamp(target.parent.lstat())
        assert {p.name for p in target.parent.iterdir()} == {"page.png"}
        records.append(
            {
                "command": argv,
                "file_before": stamp(before),
                "file_after": stamp(after),
                "root": stamp(root),
                "exit_code": result.returncode,
            }
        )
        directories.append(target.parent)
        return result

    render.execute = execute
    try:
        construction = render_run(artifacts / "construction")
    finally:
        render.execute = original
    assert records and all(not directory.exists() for directory in directories)
    report: dict[str, object] = {
        "construction": construction,
        "native_writes": records,
        "all_exact_workspaces_removed": True,
        "public_create_delivered": False,
    }
    (artifacts / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.artifacts), indent=2))


if __name__ == "__main__":
    main()
