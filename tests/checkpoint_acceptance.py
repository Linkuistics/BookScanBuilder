"""Actual installed-writer checkpoint barriers; no public finite-handoff claim."""

import argparse
import hashlib
import json
import os
import select
import signal
import subprocess
import sys
from pathlib import Path
from typing import cast

from bookscan import assets, checkpoints, ownership, project_header, source_record

PHASES = ("assets-complete", "record-complete", "pre-pointer", "inside-pointer", "post-pointer")


def run(
    output: Path, python: Path, *, header: bool = False, source: bool = False
) -> dict[str, object]:
    header = header or source
    output.mkdir()
    truth: dict[str, object] = {
        "pixels_hex": "0001ff2a80fe",
        "size": [2, 1],
        "before_pointer_commits": False,
        "inside_and_post_pointer_commits": True,
        "signal_exits": {"INT": 130, "TERM": 143, "KILL": -9},
        "public_project": False,
        "saved_header": header,
        **({"saved_source": True} if source else {}),
    }
    (output / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    readings: list[dict[str, object]] = []
    worker = Path(__file__).with_name("checkpoint_worker.py")
    for update in (False, True):
        for phase in PHASES:
            for number in (None, signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
                label = ("update-" if update else "initial-") + phase + "-" + str(int(number or 0))
                project = output / label
                command = [str(python), str(worker), str(project), phase]
                if update:
                    command.append("--update")
                if header:
                    command.append("--header")
                if source:
                    command.append("--source")
                with (output / (label + ".stderr")).open("w") as errors:
                    child = subprocess.Popen(
                        command,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=errors,
                        text=True,
                        close_fds=True,
                        env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
                    )
                    try:
                        assert child.stdout is not None and child.stdin is not None
                        ready, _, _ = select.select([child.stdout], [], [], 15)
                        assert ready, "Missing actual writer barrier: " + str(errors.name)
                        line = child.stdout.readline()
                        assert line, "Worker ended before barrier: " + str(errors.name)
                        event = cast(dict[str, object], json.loads(line))
                        assert event["writer_pid"] == child.pid and event["phase"] == phase
                        saved_lock = cast(dict[str, object], event["lock"])
                        lock = ownership.LockIdentity(
                            cast(int, saved_lock["project_device"]),
                            cast(int, saved_lock["project_inode"]),
                            cast(int, saved_lock["lock_device"]),
                            cast(int, saved_lock["lock_inode"]),
                            cast(str, saved_lock["token"]),
                        )
                        lock_before = (project / "writer.lock").read_bytes()
                        try:
                            ownership.Writer.acquire(project, lock)
                        except ownership.OwnershipError as error:
                            assert (error.code, error.exit_code) == ("PROJECT_BUSY", 4)
                        else:
                            raise AssertionError("Barrier writer did not hold ownership")
                        visible_before = os.path.lexists(project / "checkpoints" / "current")
                        assert visible_before == (
                            update or phase in {"inside-pointer", "post-pointer"}
                        )
                        if number is not None:
                            os.kill(child.pid, number)
                        if number is None or (
                            phase == "inside-pointer" and number != signal.SIGKILL
                        ):
                            child.stdin.write("release\n")
                            child.stdin.flush()
                        child.wait(timeout=15)
                        tail, _ = child.communicate(timeout=15)
                        expected_exit = (
                            0
                            if number is None
                            else -9
                            if number == signal.SIGKILL
                            else 128 + number
                        )
                        assert child.returncode == expected_exit, (label, tail, errors.name)
                        committed = number is None or phase in {"inside-pointer", "post-pointer"}
                        if number != signal.SIGKILL:
                            terminal = json.loads(tail)
                            assert terminal == {"exit_code": expected_exit, "committed": committed}
                        else:
                            assert not tail
                        directory = cast(dict[str, int], event["directory"])
                        rgb_directory = cast(dict[str, int], event["rgb_directory"])
                        reference = assets.RGBAsset.from_json(
                            json.dumps(event["reference"]).encode()
                        )
                        with ownership.Writer.acquire(project, lock) as owner:
                            images = assets.Assets(owner, assets.DirectoryIdentity(**rgb_directory))
                            store = checkpoints.Checkpoints(
                                owner, assets.DirectoryIdentity(**directory)
                            )

                            def verify(state: dict[str, object]) -> None:
                                assert set(state) == (
                                    {"baseline", "note", "source"}
                                    if source
                                    else {"baseline", "note"}
                                )
                                assert images.read(
                                    assets.RGBAsset.from_record(state["baseline"])
                                ) == bytes.fromhex("0001ff2a80fe")
                                assert isinstance(state["note"], str)
                                if source:
                                    loaded_source = source_record.restore(owner, state["source"])
                                    assert (
                                        loaded_source.sha256
                                        == cast(dict[str, object], event["source"])["source_sha256"]
                                    )
                                    assert [p.source_page for p in loaded_source.pages] == [1, 2, 3]
                                    assert [p.frame.pixels for p in loaded_source.pages] == [
                                        (300, 150),
                                        (150, 300),
                                        (300, 150),
                                    ]
                                    assert not loaded_source.original_path.exists()

                            assert images.read(reference) == bytes.fromhex("0001ff2a80fe")
                            revision = int(update) + int(committed)
                            if revision:
                                saved = store.load(verify_state=verify)
                                assert saved.revision == revision
                                assert saved.state["note"] == ("next" if committed else "first")
                                raw = (
                                    project / "checkpoints" / (saved.sha256 + ".json")
                                ).read_bytes()
                                assert hashlib.sha256(raw).hexdigest() == saved.sha256
                                assert (
                                    os.readlink(project / "checkpoints" / "current")
                                    == saved.sha256 + ".json"
                                )
                                checkpoint_sha: str | None = saved.sha256
                            else:
                                try:
                                    store.load(verify_state=verify)
                                except checkpoints.CheckpointError as error:
                                    assert (error.code, error.exit_code) == ("INVALID_PROJECT", 3)
                                else:
                                    raise AssertionError("Uncommitted initial create resumed")
                                checkpoint_sha = None
                        assert (project / "writer.lock").read_bytes() == lock_before
                        if header:
                            saved_header = project_header.Header.from_json(
                                (project / "project.json").read_bytes()
                            )
                            assert saved_header.record() == event["header"]
                            assert saved_header.lock == lock
                            assert saved_header.images == assets.DirectoryIdentity(**rgb_directory)
                            assert saved_header.checkpoints == assets.DirectoryIdentity(**directory)
                            assert saved_header.native == assets.DirectoryIdentity(
                                **cast(dict[str, int], event["native_directory"])
                            )

                            def restarted(images: assets.Assets, state: dict[str, object]) -> None:
                                assert set(state) == (
                                    {"baseline", "note", "source"}
                                    if source
                                    else {"baseline", "note"}
                                )
                                assert images.read(
                                    assets.RGBAsset.from_record(state["baseline"])
                                ) == bytes.fromhex("0001ff2a80fe")
                                assert isinstance(state["note"], str)
                                if source:
                                    loaded_source = source_record.restore(
                                        images.owner, state["source"]
                                    )
                                    assert (
                                        loaded_source.sha256
                                        == cast(dict[str, object], event["source"])["source_sha256"]
                                    )
                                    assert [p.source_page for p in loaded_source.pages] == [1, 2, 3]

                            if revision:
                                with project_header.resume(
                                    project,
                                    verify_state=lambda stores, state: restarted(
                                        stores.images, state
                                    ),
                                ) as (
                                    _,
                                    loaded,
                                ):
                                    assert loaded.revision == revision
                                    assert loaded.sha256 == checkpoint_sha
                            else:
                                try:
                                    with project_header.resume(
                                        project,
                                        verify_state=lambda stores, state: restarted(
                                            stores.images, state
                                        ),
                                    ):
                                        pass
                                except checkpoints.CheckpointError as error:
                                    assert (error.code, error.exit_code) == ("INVALID_PROJECT", 3)
                                else:
                                    raise AssertionError("Header alone promoted incomplete create")
                        record = {
                            "id": label,
                            "writer_pid": child.pid,
                            "phase": phase,
                            "update": update,
                            "signal": int(number or 0),
                            "exit_code": expected_exit,
                            "committed": committed,
                            "revision": revision,
                            "checkpoint_sha256": checkpoint_sha,
                            "visible_before": visible_before,
                            "reacquired": True,
                            "rgb_sha256": reference.rgb_sha256,
                            "package": event["package"],
                            **(
                                {
                                    "source_sha256": cast(dict[str, object], event["source"])[
                                        "source_sha256"
                                    ],
                                    "source_package": event["source_package"],
                                    "original_missing": True,
                                }
                                if source
                                else {}
                            ),
                        }
                        readings.append(record)
                        (output / (label + ".json")).write_text(
                            json.dumps({"event": event, "reading": record}, indent=2) + "\n"
                        )
                    finally:
                        if child.poll() is None:
                            child.kill()
                        child.wait(timeout=15)
                        if child.stdin:
                            child.stdin.close()
                        if child.stdout:
                            child.stdout.close()
    report: dict[str, object] = {"truth": truth, "cases": readings}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--header", action="store_true")
    parser.add_argument("--source", action="store_true")
    args = parser.parse_args()
    report = run(args.artifacts, args.python, header=args.header, source=args.source)
    print(json.dumps({"cases": len(cast(list[object], report["cases"])), "passed": True}))


if __name__ == "__main__":
    main()
