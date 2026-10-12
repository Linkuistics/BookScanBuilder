"""Actual supported tools through read-only preflight's private cancellation seam.

This supplements unit PID barriers. It is not installed finite-writer signal or
project-lock acceptance; no finite writer exists yet. The selected exception is
supplied by a private operation owner, not by a public fault mode.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

from bookscan import native_setup


class SelectedCancellation(RuntimeError):
    pass


PHASES = {
    "leptonica-version": ("pkg_config", "--modversion"),
    "poppler-version": ("poppler", "-v"),
    "compiler-driver": ("compiler", "-print-prog-name=clang"),
    "include-directory": ("pkg_config", "--variable=includedir"),
    "library-directory": ("pkg_config", "--variable=libdir"),
    "compiler-version": ("compiler", "--version"),
    "pkg-config-version": ("pkg_config", "--version"),
    "pkg-config-flags": ("pkg_config", "--cflags"),
    "helper-identity": ("helper", "--identity"),
    "helper-analysis": ("helper", "analyze"),
}


def subjects(cache: Path) -> dict[str, str]:
    return {
        str(p.relative_to(cache)): native_setup.digest(p) for p in cache.rglob("*") if p.is_file()
    }


def run(cache: Path) -> dict[str, object]:
    before = subjects(cache)
    ready = native_setup.preflight(cache)
    inputs = cast(dict[str, dict[str, object]], ready["inputs"])
    real_execute = native_setup.execute
    real_popen = subprocess.Popen
    outcomes: list[dict[str, object]] = []
    try:
        for phase, (component, argument) in PHASES.items():
            executable = (
                str(native_setup.load_cache(cache).binary)
                if component == "helper"
                else str(inputs[component]["path"])
            )
            for signum in (signal.SIGINT, signal.SIGTERM):
                children: list[subprocess.Popen[str]] = []
                selected = SelectedCancellation(f"private owner selected {128 + signum}")
                active = False

                def owner_check() -> None:
                    if active and children:
                        raise selected

                def observe_child(
                    argv: list[str],
                    *,
                    stdout: int,
                    stderr: int,
                    text: Literal[True],
                    close_fds: bool,
                    start_new_session: bool,
                ) -> subprocess.Popen[str]:
                    # This private runner observes the actual Popen return without
                    # replacing native execution, communication, kill or wait.
                    child = real_popen(
                        argv,
                        stdout=stdout,
                        stderr=stderr,
                        text=text,
                        close_fds=close_fds,
                        start_new_session=start_new_session,
                    )
                    if active:
                        children.append(child)
                    return child

                def observed_execute(
                    argv: list[str],
                    *,
                    check_cancel: Callable[[], None] = lambda: None,
                    timeout: float = 120,
                ) -> subprocess.CompletedProcess[str]:
                    nonlocal active
                    active = argv[0] == executable and argument in argv[1:]
                    try:
                        return real_execute(argv, check_cancel=check_cancel, timeout=timeout)
                    finally:
                        active = False

                native_setup.execute = observed_execute
                setattr(subprocess, "Popen", observe_child)
                try:
                    native_setup.preflight(cache, check_cancel=owner_check)
                except SelectedCancellation as error:
                    assert error is selected, "preflight must preserve the chosen owner outcome"
                else:
                    raise AssertionError(f"cancellation was swallowed: {phase}")
                assert len(children) == 1, (phase, len(children))
                child = children[0]
                assert child.returncode is not None, "actual owned child was not waited/reaped"
                try:
                    os.kill(child.pid, 0)
                except ProcessLookupError:
                    pass
                else:
                    raise AssertionError(f"owned native child remains live: {child.pid}")
                assert subjects(cache) == before, "read-only cancellation mutated the cache"
                outcomes.append(
                    {
                        "phase": phase,
                        "selected_signal_exit": 128 + signum,
                        "actual_os_signal_sent": False,
                        "child_pid": child.pid,
                        "reaped": True,
                        "owner_exception_preserved": True,
                        "cache_unchanged": True,
                    }
                )
    finally:
        native_setup.execute = real_execute
        setattr(subprocess, "Popen", real_popen)
    assert ready == native_setup.preflight(cache), (
        "successful native result changed after cancellation"
    )
    assert subjects(cache) == before
    return {
        "format": "BookScanBuilderNativeCancellationAcceptance",
        "version": 1,
        "preflight": ready,
        "cache_subjects_before": before,
        "cache_subjects_after": subjects(cache),
        "outcomes": outcomes,
        "limitation": (
            "Private selected-cancellation callback with actual supported native children; "
            "no installed finite writer, OS signal delivery, project ownership or checkpoint claim."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    real_checked = native_setup.checked

    def dropped_forwarding(
        argv: list[str], *, check_cancel: Callable[[], None] = lambda: None
    ) -> str:
        # Deliberately broken private boundary: dependency execution omits the
        # caller's cancellation. The same acceptance must detect this mutation.
        return real_checked(argv)

    native_setup.checked = dropped_forwarding
    try:
        try:
            run(args.cache)
        except AssertionError as error:
            assert str(error) == "cancellation was swallowed: leptonica-version"
            rejected = str(error)
        else:
            raise AssertionError("dropped-callback control passed")
    finally:
        native_setup.checked = real_checked
    result = run(args.cache)
    result["dropped_callback_control_rejected"] = rejected
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"report": str(args.output), "passed": True}))


if __name__ == "__main__":
    main()
