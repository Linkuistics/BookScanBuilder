"""Fresh bound native probes compared with independent reversed-sRGB intervals."""

import argparse
import json
import struct
from pathlib import Path
from typing import cast

import saturation_acceptance
from lut_saturation import native_word, verify_words
from lut_traversal import verify_vectors
from reversed_target import expected_curves, verify_target

from bookscan.native_setup import digest


def wrong_output(data: bytes, coefficients: list[str]) -> bytes:
    """Isolate target truth while keeping source/matrix/word/byte checks green."""
    for index, row in enumerate(struct.iter_unpack("<34I", data)):
        for channel, bits in enumerate(row[22:25]):
            if not 0x3C000000 <= bits < 0x3F800000:
                continue
            replacement = bits + 512
            word = native_word(replacement)
            if (
                not 0 < word < 65535
                or word == row[25 + channel]
                or (word + 128) // 257 != row[28 + channel]
            ):
                continue
            wrong = bytearray(data)
            struct.pack_into("<I", wrong, index * 136 + (22 + channel) * 4, replacement)
            struct.pack_into("<I", wrong, index * 136 + (25 + channel) * 4, word)
            verify_vectors(bytes(wrong), coefficients)
            verify_words(bytes(wrong))
            try:
                verify_target(bytes(wrong), expected_curves())
            except ValueError:
                return bytes(wrong)
    raise ValueError("No isolating wrong-target control found")


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    upstream = saturation_acceptance.run(fixtures, output / "upstream")
    subjects = cast(dict[str, str], upstream["read_subjects_before"])
    records: dict[str, list[dict[str, object]]] = {}
    controls: dict[str, str] = {}
    observed = cast(dict[str, dict[str, object]], upstream["records"])
    for label in ["a", "b"]:
        directory = output / "upstream" / label
        previous = cast(dict[str, object], observed[label]["upstream"])
        traversals = cast(dict[str, dict[str, object]], previous["traversals"])
        paths = sorted((directory / "capture").glob("*-traversal.bin"))
        if len(paths) != 2:
            raise ValueError("Missing/extra actual target transforms")
        values: list[dict[str, object]] = []
        for path in paths:
            sequence = path.name.split("-")[1]
            stages = cast(dict[str, object], traversals[sequence]["preceding_stages"])
            gamma = cast(dict[str, object], stages["preceding_gamma"])
            pipeline = cast(dict[str, object], gamma["pipeline"])
            chain = cast(list[dict[str, object]], pipeline["stages"])
            coefficients = cast(list[str], chain[1]["matrix"])
            data = path.read_bytes()
            verify_vectors(data, coefficients)
            verify_words(data)
            # The complete unchanged upstream readers bind PID/native dispatch,
            # final curve parameters, source/profile/pipeline and every value.
            result = verify_target(data, chain[2]["curves"])
            result["input_format"] = cast(list[dict[str, object]], observed[label]["saturation"])[
                len(values)
            ]["input_format"]
            values.append(result)
            wrong = wrong_output(data, coefficients)
            (output / f"{label}-{sequence}-wrong-target.bin").write_bytes(wrong)
            try:
                verify_target(wrong, chain[2]["curves"])
            except ValueError as error:
                controls[f"{label}-{sequence}-wrong-target-same-byte-consistent-word"] = str(error)
            else:
                raise ValueError("Wrong target output credited")
        records[label] = values
    if records["a"] != records["b"]:
        raise ValueError("Per-vector reversed target rerun differs")
    after = {path: digest(Path(path)) for path in subjects}
    if subjects != after:
        raise ValueError("Reversed target measurement subject changed")
    report: dict[str, object] = {
        "format": "BookScanBuilderReversedTargetAccuracy",
        "version": 1,
        "read_subjects_before": subjects,
        "read_subjects_after": after,
        "upstream": upstream,
        "records": records,
        "controls": controls,
        "per_vector_rerun_equal": True,
        "reversed_target_accuracy_verified": True,
        "correctly_rounded_transcendentals_verified": False,
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
            "Test-owned macOS arm64 acceptance; existing verified traversal fixtures and "
            "unused output directory required. Example: python tests/reversed_acceptance.py "
            "--fixtures /tmp/traversal-fixtures --artifacts /tmp/NEW. "
            "Exit 0: checked, 1: failed, 2: usage. No general ICC fidelity claim."
        ),
    )
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    record = run(args.fixtures, args.artifacts)
    print(
        json.dumps(
            {
                k: v
                for k, v in record.items()
                if k not in {"records", "upstream", "read_subjects_before", "read_subjects_after"}
            },
            indent=2,
        )
    )
