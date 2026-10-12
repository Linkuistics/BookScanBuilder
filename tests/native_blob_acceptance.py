"""Actual Mac native-blob publication/death/reopen, optionally using a locked installed wheel."""

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

from bookscan import native_blobs, ownership


def run(output: Path, python: Path) -> dict[str, object]:
    output.mkdir()
    records: list[dict[str, object]] = []
    worker = Path(__file__).with_name("native_blob_worker.py")
    # Expectations precede any process reading; exact known samples supply truth.
    raw = b"Opaque packed/profile/palette bytes\x00\xff"
    truth = {
        "raw_hex": raw.hex(),
        "byte_size": len(raw),
        "checkpoint": False,
        "pre-link_visible": False,
        "post-link_visible": True,
        "signals": {"INT": 130, "TERM": 143, "KILL": -9},
    }
    (output / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    for phase in ("pre-link", "post-link"):
        for number in (None, signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
            label = phase + "-" + str(int(number) if number else 0)
            project = output / label
            command = [str(python), str(worker), str(project), phase]
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
                    ready, _, _ = select.select([child.stdout], [], [], 10)
                    if not ready:
                        raise AssertionError("Missing actual writer barrier")
                    line = child.stdout.readline()
                    if not line:
                        raise AssertionError(
                            "Worker exited before its barrier; inspect " + str(errors.name)
                        )
                    event = cast(dict[str, object], json.loads(line))
                    assert event["writer_pid"] == child.pid and event["phase"] == phase
                    fields = cast(dict[str, int | str], event["lock"])
                    identity = ownership.LockIdentity(
                        cast(int, fields["project_device"]),
                        cast(int, fields["project_inode"]),
                        cast(int, fields["lock_device"]),
                        cast(int, fields["lock_inode"]),
                        cast(str, fields["token"]),
                    )
                    lock_before = (project / "writer.lock").read_bytes()
                    try:
                        ownership.Writer.acquire(project, identity)
                    except ownership.OwnershipError as error:
                        assert (error.code, error.exit_code) == ("PROJECT_BUSY", 4)
                    else:
                        raise AssertionError("Observed writer did not own kernel lock")
                    visible_before = sorted(
                        p.name for p in (project / "native-blobs").glob("*.bin")
                    )
                    assert bool(visible_before) == (phase == "post-link")
                    if number is None:
                        child.stdin.write("release\n")
                        child.stdin.flush()
                    else:
                        os.kill(child.pid, number)
                    # Keep stdin open until termination; communicate closes it and
                    # can make barrier EOF win the race against the caught signal.
                    child.wait(timeout=10)
                    tail, _ = child.communicate(timeout=10)
                    assert not tail
                    expected_exit = (
                        0 if number is None else -9 if number == signal.SIGKILL else 128 + number
                    )
                    assert child.returncode == expected_exit
                    directory = cast(dict[str, int], event["directory"])
                    reference = native_blobs.Blob.from_record(event["reference"])
                    visible = sorted(p.name for p in (project / "native-blobs").glob("*.bin"))
                    expected_visible = number is None or phase == "post-link"
                    assert bool(visible) == expected_visible
                    # A kill can leave its private hard link. Such an orphan is
                    # not silently promoted; read must refuse multiple links.
                    private = sorted(p.name for p in (project / "native-blobs").glob(".blob-*"))
                    assert bool(private) == (number == signal.SIGKILL)
                    with ownership.Writer.acquire(project, identity) as owner:
                        store = native_blobs.Blobs(
                            owner, native_blobs.DirectoryIdentity(**directory)
                        )
                        if expected_visible and not private:
                            assert store.read(reference) == raw
                        else:
                            try:
                                store.read(reference)
                            except native_blobs.BlobError as error:
                                assert (error.code, error.exit_code) == ("INVALID_PROJECT", 3)
                            else:
                                raise AssertionError("Missing/private orphan became usable")
                    if visible:
                        assert (project / "native-blobs" / visible[0]).read_bytes() == raw
                    assert (project / "writer.lock").read_bytes() == lock_before
                    assert not (project / "current").exists()
                    records.append(
                        {
                            "case": label,
                            "exit": child.returncode,
                            "visible_before": visible_before,
                            "visible_after": visible,
                            "private_names": private,
                            "immediate_reacquisition": True,
                            "checkpoint": False,
                            "command": command,
                            "barrier": event,
                        }
                    )
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=10)
    result: dict[str, object] = {
        "truth": truth,
        "records": records,
        "product": str(Path(native_blobs.__file__).resolve()),
        "product_sha256": hashlib.sha256(Path(native_blobs.__file__).read_bytes()).hexdigest(),
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    # Preserve the venv executable spelling: realpath selects the base interpreter
    # and drops installed dependencies, even when the bytes are the same binary.
    result = run(args.artifacts.resolve(), args.python.absolute())
    print(json.dumps({"native_blob_process_cases": len(cast(list[object], result["records"]))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
