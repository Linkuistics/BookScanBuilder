"""Fresh actual renderer-owned probes plus independent finite saturation arithmetic."""

import argparse
import json
import struct
import sys
import sysconfig
from pathlib import Path
from typing import cast

import traversal_acceptance
from lut_saturation import verify_native, verify_words
from lut_traversal import verify_vectors
from target_observation import parse_event

from bookscan.native_setup import checked, digest, tool


def run(fixtures: Path, output: Path) -> dict[str, object]:
    """Keep previous readers intact and bind the new claim to their full evidence."""
    output.mkdir()
    root = Path(__file__).resolve().parent.parent
    paths = checked([str(tool("jj")), "--repository", str(root), "file", "list"]).splitlines()
    library = Path("/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib").resolve(strict=True)
    truth = json.loads((fixtures / "truth.json").read_text())
    stdlib = Path(sysconfig.get_path("stdlib"))
    subjects = (
        {root / p for p in paths}
        | {p for p in fixtures.rglob("*") if p.is_file()}
        | {Path(p) for p in truth["build_subjects_before"]}
        | {
            library,
            Path(sys.executable).resolve(),
            tool("otool").resolve(),
            tool("jj").resolve(),
            tool("task").resolve(),
            tool("uv").resolve(),
        }
        | {p for p in (root / ".venv").rglob("*") if p.is_file()}
        | {p for p in stdlib.rglob("*") if p.is_file()}
    )
    before = {str(p): digest(p) for p in sorted(subjects)}
    disassembly = checked([str(tool("otool")), "-tvV", str(library)])
    constants = checked([str(tool("otool")), "-s", "__TEXT", "__const", str(library)])
    binding = verify_native(disassembly, constants)
    if disassembly != (fixtures / "native-disassembly.txt").read_text().strip():
        raise ValueError("Native saturation library differs from traversal fixture")
    (output / "native-disassembly.txt").write_text(disassembly)
    (output / "native-constants.txt").write_text(constants)
    records: dict[str, object] = {}
    identities: dict[str, list[dict[str, object]]] = {}
    controls: dict[str, str] = {}
    for label in ["a", "b"]:
        directory = output / label
        upstream = traversal_acceptance.run(fixtures, directory)
        values: list[dict[str, object]] = []
        observed = cast(dict[str, object], upstream["traversals"])
        paths = sorted((directory / "capture").glob("*-traversal.bin"))
        if len(paths) != 2:
            raise ValueError("Missing actual saturation transforms")
        for path in paths:
            sequence = path.name.split("-")[1]
            previous = cast(dict[str, object], observed[sequence])
            stages = cast(dict[str, object], previous["preceding_stages"])
            gamma = cast(dict[str, object], stages["preceding_gamma"])
            pipeline = cast(dict[str, object], gamma["pipeline"])
            chain = cast(list[dict[str, object]], pipeline["stages"])
            coefficients = cast(list[str], chain[1]["matrix"])
            data = path.read_bytes()
            verify_vectors(data, coefficients)
            # Corrupt a word within its original byte bin and update no linked
            # stage/byte/restoration facts: the original reader must still pass.
            wrong = bytearray(data)
            row = list(struct.unpack_from("<34I", wrong, 17 * 136))
            word = row[25]
            replacement = word + 1 if (word + 129) // 257 == (word + 128) // 257 else word - 1
            if not 0 <= replacement <= 65535:
                raise ValueError("Invalid wrong-word control domain")
            struct.pack_into("<I", wrong, 17 * 136 + 25 * 4, replacement)
            verify_vectors(bytes(wrong), coefficients)
            try:
                verify_words(bytes(wrong))
            except ValueError as error:
                controls[f"{label}-{sequence}-wrong-word-same-byte"] = str(error)
            else:
                raise ValueError("Wrong saturation word credited")
            (directory / (sequence + "-wrong-word.bin")).write_bytes(wrong)
            result = verify_words(data)
            pid = int(path.name.split("-")[0])
            event = parse_event(
                (directory / "capture" / f"{pid}-{sequence}-event.txt").read_text(), pid
            )
            result["input_format"] = event.input_format
            values.append(result)
        identities[label] = values
        records[label] = {"upstream": upstream, "saturation": values}
    if identities["a"] != identities["b"]:
        raise ValueError("Per-transform saturation rerun differs")
    for label, old, new in [
        ("wrong-multiply", "fmul", "fadd"),
        ("wrong-half", "#0.50000000", "#0.25000000"),
        ("wrong-shift", "#16", "#15"),
    ]:
        try:
            verify_native(disassembly.replace(old, new), constants)
        except ValueError as error:
            controls[label] = str(error)
        else:
            raise ValueError("Wrong native instruction credited")
    for label, old, new in [
        ("wrong-scale", "40efffe0", "40efffc0"),
        ("wrong-floor-offset", "c0dfffc0", "c0dfffa0"),
    ]:
        try:
            verify_native(disassembly, constants.replace(old, new))
        except ValueError as error:
            controls[label] = str(error)
        else:
            raise ValueError("Wrong native literal credited")
    after = {str(p): digest(p) for p in sorted(subjects)}
    if before != after:
        raise ValueError("Saturation measurement subject changed")
    report: dict[str, object] = {
        "format": "BookScanBuilderLUTSaturationObservation",
        "version": 1,
        "native_binding": binding,
        "library": {"path": str(library), "sha256": digest(library)},
        "read_subjects_before": before,
        "read_subjects_after": after,
        "records": records,
        "controls": controls,
        "per_transform_rerun_equal": True,
        "saturation_arithmetic_verified": True,
        "target_precision_verified": False,
        "renderer_pixel_traversal_observed": False,
        "complete_cmm_precision_verified": False,
        "accepted_project_delivered": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Test-owned macOS arm64 acceptance; use existing verified traversal fixtures "
            "and an unused output directory. Example: python tests/saturation_acceptance.py "
            "--fixtures /tmp/traversal-fixtures --artifacts /tmp/NEW-reading. "
            "Exit 0: checked, 1: failed, 2: usage. No full ICC fidelity claim."
        ),
    )
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.fixtures, args.artifacts)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"records", "read_subjects_before", "read_subjects_after"}
            },
            indent=2,
        )
    )
