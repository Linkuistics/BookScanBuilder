"""Private installed native-blob writer barriers; no public fault mode or checkpoint."""

import argparse
import hashlib
import json
import os
import signal
import sys
from dataclasses import asdict
from pathlib import Path

from bookscan import native_blobs, ownership


class Interrupted(Exception):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("phase", choices=["pre-link", "post-link"])
    args = parser.parse_args()
    signum = 0

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
    raw = b"Opaque packed/profile/palette bytes\x00\xff"
    expected = native_blobs.Blob(hashlib.sha256(raw).hexdigest(), len(raw))
    try:
        with ownership.Writer.acquire(args.project, identity) as owner:
            store = native_blobs.Blobs.provision(owner)
            original_link = os.link

            def barrier() -> None:
                print(
                    json.dumps(
                        {
                            "writer_pid": os.getpid(),
                            "phase": args.phase,
                            "lock": asdict(identity),
                            "directory": asdict(store.identity),
                            "reference": expected.record(),
                            "package": str(Path(native_blobs.__file__).resolve()),
                        }
                    ),
                    flush=True,
                )
                # Driver chooses release or a signal against this observed PID.
                while not signum:
                    import select

                    readable, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if readable:
                        if sys.stdin.readline().strip() != "release":
                            raise ValueError("Missing private barrier release")
                        break
                check()

            def linked(
                src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int, follow_symlinks: bool
            ) -> None:
                if args.phase == "pre-link":
                    barrier()
                original_link(
                    src,
                    dst,
                    src_dir_fd=src_dir_fd,
                    dst_dir_fd=dst_dir_fd,
                    follow_symlinks=follow_symlinks,
                )
                if args.phase == "post-link":
                    barrier()

            # Only the test adapter installs barriers; the installed operation is real.
            native_blobs.os.link = linked
            result = store.publish(raw, check_cancel=check)
            saved = json.dumps(result.record()).encode("utf-8")
            if (
                result != expected
                or store.read(native_blobs.Blob.from_record(json.loads(saved))) != raw
            ):
                raise ValueError("Installed native blob identity/byte mismatch")
        return 0
    except Interrupted:
        return 128 + signum


if __name__ == "__main__":
    sys.exit(main())
