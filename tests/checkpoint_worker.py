"""Private observed-PID adapter around actual installed checkpoint operations."""

import argparse
import json
import os
import select
import signal
import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import cast

import pikepdf

from bookscan import assets, checkpoints, intake, ownership, project_header, source_record


class Interrupted(Exception):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument(
        "phase",
        choices=[
            "assets-complete",
            "record-complete",
            "pre-pointer",
            "inside-pointer",
            "post-pointer",
        ],
    )
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--header", action="store_true")
    parser.add_argument("--source", action="store_true")
    args = parser.parse_args()
    args.header = args.header or args.source
    signum = 0
    committed = False

    def caught(number: int, frame: object) -> None:
        nonlocal signum
        signum = number

    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, caught)

    def check() -> None:
        if signum:
            raise Interrupted

    args.project.mkdir()
    identity = ownership.provision(args.project)
    exit_code = 0
    try:
        with ownership.Writer.acquire(args.project, identity) as owner:
            stores = project_header.Stores.provision(owner) if args.header else None
            images = stores.images if stores else assets.Assets.provision(owner)
            reference = images.publish(bytes.fromhex("0001ff2a80fe"), (2, 1))
            store = stores.checkpoints if stores else checkpoints.Checkpoints.provision(owner)
            saved_source: dict[str, object] | None = None
            if args.source:
                original = args.project.with_suffix(".input.pdf")
                with pikepdf.Pdf.new() as pdf:
                    pdf.add_blank_page(page_size=(72, 36))
                    pdf.add_blank_page(page_size=(36, 72))
                    pdf.pages.append(pdf.pages[0])
                    pdf.save(original)
                saved_source = source_record.record(
                    owner, intake.snapshot(original, owner.path / "source.pdf")
                )
                original.unlink()

            def payload(note: str) -> dict[str, object]:
                state: dict[str, object] = {"baseline": reference.record(), "note": note}
                if saved_source is not None:
                    state["source"] = saved_source
                return state

            def verify(state: dict[str, object]) -> None:
                if (
                    set(state)
                    != ({"baseline", "note", "source"} if args.source else {"baseline", "note"})
                    or not isinstance(state["note"], str)
                    or images.read(assets.RGBAsset.from_record(state["baseline"]))
                    != bytes.fromhex("0001ff2a80fe")
                ):
                    raise ValueError("Wrong installed checkpoint payload/pixels")
                if args.source:
                    source_record.restore(owner, state["source"], check_cancel=check)

            previous = None
            if args.update:
                previous = store.commit(
                    payload("first"),
                    expected=None,
                    verify_state=verify,
                ).checkpoint

            def barrier() -> None:
                print(
                    json.dumps(
                        {
                            "writer_pid": os.getpid(),
                            "phase": args.phase,
                            "lock": asdict(identity),
                            "directory": asdict(store.identity),
                            "rgb_directory": asdict(images.identity),
                            "reference": reference.record(),
                            "package": str(Path(checkpoints.__file__).resolve()),
                            "header": stores.header.record() if stores else None,
                            "native_directory": asdict(stores.native.identity) if stores else None,
                            "header_package": (
                                str(Path(project_header.__file__).resolve()) if stores else None
                            ),
                            **(
                                {
                                    "source": saved_source,
                                    "source_package": str(Path(source_record.__file__).resolve()),
                                }
                                if args.source
                                else {}
                            ),
                        }
                    ),
                    flush=True,
                )
                while not signum:
                    readable, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if readable:
                        if sys.stdin.readline().strip() != "release":
                            raise ValueError("Missing private checkpoint barrier release")
                        break
                check()

            publish = cast(
                Callable[
                    [checkpoints.Checkpoints, int, checkpoints.Checkpoint, checkpoints.Cancel], None
                ],
                getattr(checkpoints.Checkpoints, "_publish"),
            )

            def published(
                self: checkpoints.Checkpoints,
                directory: int,
                checkpoint: checkpoints.Checkpoint,
                check_cancel: checkpoints.Cancel,
            ) -> None:
                publish(self, directory, checkpoint, check_cancel)
                if args.phase == "record-complete":
                    barrier()

            mask = signal.pthread_sigmask

            def masked(
                how: signal.Sigmasks, signals: set[signal.Signals | int]
            ) -> set[signal.Signals | int]:
                if how == signal.SIG_BLOCK and args.phase == "pre-pointer":
                    barrier()
                return mask(how, signals)

            symlink, replace = os.symlink, os.replace

            def linked(src: str, dst: str, *, dir_fd: int) -> None:
                symlink(src, dst, dir_fd=dir_fd)
                if dst == "current" and args.phase == "inside-pointer":
                    barrier()

            def replaced(src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int) -> None:
                replace(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)
                if dst == "current" and args.phase == "inside-pointer":
                    barrier()

            # Only this private adapter installs barriers; all native I/O remains real.
            setattr(checkpoints.Checkpoints, "_publish", published)
            setattr(checkpoints.signal, "pthread_sigmask", masked)
            setattr(checkpoints.os, "symlink", linked)
            setattr(checkpoints.os, "replace", replaced)
            if args.phase == "assets-complete":
                barrier()
            result = store.commit(
                payload("next"),
                expected=previous,
                verify_state=verify,
                check_cancel=check,
            )
            committed = result.committed
            if args.phase == "post-pointer":
                barrier()
            check()
            if store.load(verify_state=verify).state["note"] != "next":
                raise ValueError("Wrong committed checkpoint")
        if args.header:

            def restarted(images: assets.Assets, state: dict[str, object]) -> None:
                if (
                    set(state)
                    != ({"baseline", "note", "source"} if args.source else {"baseline", "note"})
                    or not isinstance(state["note"], str)
                    or images.read(assets.RGBAsset.from_record(state["baseline"]))
                    != bytes.fromhex("0001ff2a80fe")
                ):
                    raise ValueError("Wrong resumed header state/pixels")
                if args.source:
                    source_record.restore(images.owner, state["source"])

            with project_header.resume(
                args.project, verify_state=lambda stores, state: restarted(stores.images, state)
            ) as (_, loaded):
                if loaded.state["note"] != "next":
                    raise ValueError("Wrong installed header resume")
    except Interrupted:
        exit_code = 128 + signum
    except checkpoints.CheckpointError as error:
        committed = error.committed
        exit_code = error.exit_code
        if error.code != "INTERRUPTED":
            raise
    print(json.dumps({"exit_code": exit_code, "committed": committed}), flush=True)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
