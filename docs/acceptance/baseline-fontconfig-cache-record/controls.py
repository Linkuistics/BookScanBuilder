"""Repack contradictory observations with valid digests; require semantic refusal."""

import gzip
import io
import json
import tempfile
import zipfile
from pathlib import Path
from typing import cast

from verify import load, sha, verify


def repack(directory: Path, entries: dict[str, bytes]) -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(entries.items()):
            archive.writestr(name, raw)
    raw = stream.getvalue()
    parts: list[dict[str, str]] = []
    for ordinal, start in enumerate(range(0, len(raw), 900_000)):
        name = f"raw-{ordinal:03d}.zippart"
        chunk = raw[start : start + 900_000]
        (directory / name).write_bytes(chunk)
        parts.append({"name": name, "sha256": sha(chunk)})
    index = {"parts": parts, "entries": {name: sha(raw) for name, raw in entries.items()}}
    (directory / "index.json.gz").write_bytes(gzip.compress(json.dumps(index).encode(), mtime=0))


def main() -> None:
    source = Path(__file__).parent
    original = load(source)
    verify(original)
    outcomes: dict[str, str] = {}
    for control in ("cache-method-upgrade", "missing-fixed-subject-disproof"):
        changed = dict(original)
        if control == "cache-method-upgrade":

            def upgrade(value: object) -> None:
                if isinstance(value, dict):
                    mapping = cast(dict[str, object], value)
                    if "cache_construction" in mapping:
                        cast(dict[str, object], mapping["cache_construction"])["method"] = (
                            "renderer-opens-verified"
                        )
                    for item in mapping.values():
                        upgrade(item)
                elif isinstance(value, list):
                    for item in cast(list[object], value):
                        upgrade(item)

            for lane in ("source", "wheel"):
                for suffix in ("a", "b"):
                    name = f"frozen/cache-{lane}-{suffix}/result.json"
                    data = cast(dict[str, object], json.loads(changed[name]))
                    upgrade(data)
                    changed[name] = json.dumps(data).encode()
        else:
            name = "mutations/fixed-subjects/result.xml"
            text = changed[name].decode()
            # Change the failure into a passing record, and change its ledger too.
            start = text.index("<failure ")
            end = text.index("</failure>", start) + len("</failure>")
            changed[name] = (text[:start] + text[end:]).encode()
            ledger = cast(
                dict[str, dict[str, object]], json.loads(changed["mutations/result.json"])
            )
            failed = cast(list[str], ledger["fixed-subjects"]["failed"])
            failed.pop(0)
            changed["mutations/result.json"] = json.dumps(ledger).encode()
        with tempfile.TemporaryDirectory(prefix="bookscan-cache-record-repack-") as temporary:
            target = Path(temporary)
            repack(target, changed)
            try:
                verify(load(target))
            except ValueError as error:
                outcomes[control] = str(error)
            else:
                raise ValueError("Coherent contradictory archive was accepted: " + control)
    wanted = {
        "cache-method-upgrade": "cache method",
        "missing-fixed-subject-disproof": "isolated mutation failures",
    }
    if outcomes != wanted:
        raise ValueError("Unexpected coherent control failures: " + repr(outcomes))
    result = {"passed": True, "controls": outcomes}
    (source / "controls-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
