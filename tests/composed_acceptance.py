"""Fresh actual native probes with conditional ideal source-to-byte envelopes."""

import argparse
import json
import struct
from pathlib import Path
from typing import cast

import reversed_acceptance
from composed_envelope import verify_composed
from lut_saturation import verify_words
from reversed_target import verify_target
from stage_evaluation import verify_stages

from bookscan.native_setup import digest


def wrong_byte(data: bytes, coefficients: list[str], curves: object) -> bytes:
    """Alter final output association while leaving all preceding arithmetic exact.

    This deliberately violates the formatter too. It cannot keep a validated
    deterministic formatter green while changing its final byte; no such
    isolating claim is made. The independent ideal-byte oracle must reject it.
    """
    wrong = bytearray(data)
    column = 28
    actual = struct.unpack_from("<I", wrong, 17 * 136 + column * 4)[0]
    struct.pack_into(
        "<I", wrong, 17 * 136 + column * 4, actual + 2 if actual <= 253 else actual - 2
    )
    stages = b"".join(
        struct.pack("<9I", *row[7:13], *row[16:19]) for row in struct.iter_unpack("<34I", wrong)
    )
    verify_stages(stages, coefficients, denominator=255)
    verify_target(bytes(wrong), curves)
    verify_words(bytes(wrong))
    return bytes(wrong)


def run(fixtures: Path, output: Path) -> dict[str, object]:
    output.mkdir()
    upstream = reversed_acceptance.run(fixtures, output / "upstream")
    subjects = cast(dict[str, str], upstream["read_subjects_before"])
    saturation = cast(dict[str, object], upstream["upstream"])
    observed = cast(dict[str, dict[str, object]], saturation["records"])
    target_records = cast(dict[str, list[dict[str, object]]], upstream["records"])
    records: dict[str, list[dict[str, object]]] = {}
    controls: dict[str, str] = {}
    for label in ["a", "b"]:
        directory = output / "upstream/upstream" / label
        traversals = cast(dict[str, dict[str, object]], observed[label]["upstream"])["traversals"]
        paths = sorted((directory / "capture").glob("*-traversal.bin"))
        if len(paths) != 2:
            raise ValueError("Missing/extra actual composed transforms")
        values: list[dict[str, object]] = []
        for path in paths:
            sequence = path.name.split("-")[1]
            previous = cast(dict[str, object], traversals[sequence])
            stages = cast(dict[str, object], previous["preceding_stages"])
            gamma = cast(dict[str, object], stages["preceding_gamma"])
            pipeline = cast(dict[str, object], gamma["pipeline"])
            chain = cast(list[dict[str, object]], pipeline["stages"])
            coefficients = cast(list[str], chain[1]["matrix"])
            data = path.read_bytes()
            # All preceding pipeline/curve/dispatch/source/matrix/target/word/
            # formatter/restoration readers already ran unchanged upstream.
            record = verify_composed(data, coefficients)
            record["input_format"] = target_records[label][len(values)]["input_format"]
            values.append(record)
            wrong = wrong_byte(data, coefficients, chain[2]["curves"])
            (output / f"{label}-{sequence}-wrong-byte.bin").write_bytes(wrong)
            try:
                verify_composed(wrong, coefficients)
            except ValueError as error:
                controls[f"{label}-{sequence}-wrong-byte-preceding-arithmetic-unchanged"] = str(
                    error
                )
            else:
                raise ValueError("Wrong composed final byte credited")
        records[label] = values
    if records["a"] != records["b"]:
        raise ValueError("Composed per-value rerun differs")
    after = {path: digest(Path(path)) for path in subjects}
    if subjects != after:
        raise ValueError("Composed-envelope measurement subject changed")
    report: dict[str, object] = {
        "format": "BookScanBuilderControlledComposedByteEnvelope",
        "version": 1,
        "read_subjects_before": subjects,
        "read_subjects_after": after,
        "upstream": upstream,
        "records": records,
        "controls": controls,
        "per_value_rerun_equal": True,
        "controlled_composed_byte_envelope_verified": True,
        "renderer_pixel_traversal_observed": False,
        "arbitrary_icc_verified": False,
        "page_composition_fidelity_verified": False,
        "accepted_project_delivered": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Test-owned macOS arm64 acceptance; use unchanged verified traversal fixtures "
            "and an unused artifact directory. Example: python tests/composed_acceptance.py "
            "--fixtures /tmp/traversal-fixtures --artifacts /tmp/NEW. "
            "Exit 0: checked, 1: failed, 2: usage. No arbitrary ICC/page-fidelity claim."
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
                if k not in {"records", "upstream", "read_subjects_before", "read_subjects_after"}
            },
            indent=2,
        )
    )
