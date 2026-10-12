"""Actual static loader/codec identity and selected cancellation; no project/fidelity claim."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

from render_identity import linked_files

from bookscan import dependencies, native_setup, render
from bookscan.skew import NativeError


class SelectedCancellation(RuntimeError):
    pass


def cache_bytes(cache: Path) -> dict[str, str]:
    return {
        str(path.relative_to(cache)): native_setup.digest(path)
        for path in cache.rglob("*")
        if path.is_file()
    }


def semantic(record: dict[str, object]) -> dict[str, object]:
    """Compare complete static edge identities while retaining path-bearing raw records.

    Installed modules live in a different environment. Compare file bytes and
    edge kind/reference/resolved bytes, architecture/build/system references,
    codecs/renderer/helper meanings; no PID/private-root equivalence is inferred.
    """
    graphs = cast(dict[str, dict[str, object]], record["linked"])
    result: dict[str, object] = {}
    for name, graph in graphs.items():
        files = cast(dict[str, dict[str, object]], graph["files"])
        rows: list[dict[str, object]] = []
        for path, item in files.items():
            references = cast(list[dict[str, str]], item["references"])
            refs = [
                {
                    "kind": ref["kind"],
                    "reference": ref["reference"],
                    "resolved_sha256": files[ref["resolved"]]["sha256"],
                }
                if "resolved" in ref
                else ref
                for ref in references
            ]
            rows.append({"name": Path(path).name, "sha256": item["sha256"], "references": refs})
        result[name] = {
            "files": sorted(rows, key=lambda row: str(row["name"])),
            "architecture": graph["architecture"],
            "os_build": graph["os_build"],
            "system_references": graph["system_references"],
            "runtime_resources_verified": graph["runtime_resources_verified"],
            "limitation": graph["limitation"],
        }
    return {
        "helper": record["helper"],
        "renderer_version": cast(dict[str, object], record["renderer"])["version"],
        "graphs": result,
        "pillow_features": record["pillow_features"],
        "runtime_resources_verified": record["runtime_resources_verified"],
        "limitation": record["limitation"],
    }


def cancellations(cache: Path, *, drop_callback: bool = False) -> list[dict[str, object]]:
    real_execute, real_render_execute, real_popen = (
        native_setup.execute,
        render.execute,
        subprocess.Popen,
    )
    rows: list[dict[str, object]] = []
    try:
        for phase in ("pdftocairo", "os-build", "load-commands"):
            for signum in (signal.SIGINT, signal.SIGTERM):
                children: list[subprocess.Popen[str]] = []
                selected = SelectedCancellation(f"owner selected {128 + signum}")
                active = False

                def owner_check() -> None:
                    if active and children:
                        raise selected

                def observed_popen(
                    argv: list[str],
                    *,
                    stdout: int,
                    stderr: int,
                    text: Literal[True],
                    close_fds: bool,
                    start_new_session: bool,
                ) -> subprocess.Popen[str]:
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
                    active = (
                        (phase == "pdftocairo" and Path(argv[0]).name == "pdftocairo")
                        or (phase == "os-build" and argv[0] == "/usr/bin/sw_vers")
                        or (phase == "load-commands" and "-l" in argv)
                    )
                    try:
                        return real_execute(
                            argv,
                            check_cancel=(lambda: None)
                            if drop_callback and active
                            else check_cancel,
                            timeout=timeout,
                        )
                    finally:
                        active = False

                native_setup.execute = observed_execute
                render.execute = observed_execute
                setattr(subprocess, "Popen", observed_popen)
                try:
                    dependencies.preflight(cache, check_cancel=owner_check)
                except SelectedCancellation as error:
                    assert error is selected
                else:
                    raise AssertionError(f"cancellation was swallowed: {phase}")
                assert len(children) == 1
                child = children[0]
                assert child.returncode is not None
                try:
                    os.kill(child.pid, 0)
                except ProcessLookupError:
                    pass
                else:
                    raise AssertionError(f"owned child remains live: {child.pid}")
                rows.append(
                    {
                        "phase": phase,
                        "selected_exit": 128 + signum,
                        "child_pid": child.pid,
                        "reaped": True,
                        "owner_exception_preserved": True,
                        "actual_os_signal_sent": False,
                    }
                )
    finally:
        native_setup.execute, render.execute = real_execute, real_render_execute
        setattr(subprocess, "Popen", real_popen)
    return rows


def run(cache: Path) -> dict[str, object]:
    before = cache_bytes(cache)
    record = dependencies.preflight(cache)
    old = linked_files(render.renderer_path())
    cairo = cast(dict[str, dict[str, object]], record["linked"])["pdftocairo"]
    actual = cast(dict[str, dict[str, object]], cairo["files"])
    expected = cast(dict[str, dict[str, object]], old["files"])
    assert {path: item["sha256"] for path, item in actual.items()} == {
        path: item["sha256"] for path, item in expected.items()
    }
    assert cairo["os_build"] == old["os_build"]
    real_renderer = dependencies.renderer_path

    def unavailable(*, check_cancel: Callable[[], None]) -> Path:
        check_cancel()
        raise NativeError("Observed private missing Cairo control")

    dependencies.renderer_path = unavailable
    try:
        try:
            dependencies.preflight(cache)
        except NativeError as error:
            assert str(error) == "Observed private missing Cairo control"
        else:
            raise AssertionError("missing selected renderer was ignored")
    finally:
        dependencies.renderer_path = real_renderer
    try:
        cancellations(cache, drop_callback=True)
    except AssertionError as error:
        assert str(error) == "cancellation was swallowed: pdftocairo"
        dropped = str(error)
    else:
        raise AssertionError("dropped native cancellation was ignored")
    outcomes = cancellations(cache)
    assert dependencies.preflight(cache) == record
    assert cache_bytes(cache) == before
    return {
        "format": "BookScanBuilderDependencyAcceptance",
        "version": 1,
        "preflight": record,
        "semantic": semantic(record),
        "cancellation_outcomes": outcomes,
        "controls": {"missing_renderer_rejected": True, "dropped_callback_rejected": dropped},
        "legacy_static_cairo_file_bytes_equal": True,
        "cache_subjects_before": before,
        "cache_subjects_after": cache_bytes(cache),
        "limitation": (
            "Static dependencies/private callback with actual native children only; "
            "no runtime resource, source fidelity, installed finite writer or OS signal claim."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = run(args.cache)
    with args.output.open("x") as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"report": str(args.output), "passed": True}))


if __name__ == "__main__":
    main()
