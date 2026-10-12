"""Known codec channel truth, independent of page rendering or source RGB fidelity."""

import argparse
import copy
import hashlib
import io
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pikepdf
from PIL import Image
from PIL import __version__ as pillow_version
from test_codec_samples import fax, fixture, jpeg

from bookscan import samples

# Declare before any output: PDF white/black runs are self-photometric, with
# raw BlackIs1=false white=1/black=0. TIFF6 section10 provides the hand code.
TRUTH: list[dict[str, object]] = [
    {"name": "jpeg-gray", "size": [16, 8], "bits": 8, "channels": [128], "bound": 0},
    {"name": "jpeg-rgb", "size": [16, 8], "bits": 8, "channels": [128, 128, 128], "bound": 0},
    {"name": "jpeg-colour", "size": [16, 8], "bits": 8, "channels": [18, 52, 86], "bound": 2},
    {"name": "ccitt-hand-white", "size": [9, 2], "bits": 1, "packed": "ff800000"},
    {"name": "ccitt-hand-black", "size": [9, 2], "bits": 1, "packed": "0000ff80"},
    {"name": "ccitt-g4", "size": [9, 2], "bits": 1, "packed": "5500aa80"},
    {"name": "ccitt-g4-black", "size": [9, 2], "bits": 1, "packed": "aa805500"},
    {"name": "ccitt-inline", "size": [9, 2], "bits": 1, "packed": "5500aa80"},
]


def failures(row: Mapping[str, object], truth: Mapping[str, object]) -> list[str]:
    failed = [key for key in ("size", "bits") if row.get(key) != truth[key]]
    if "packed" in truth:
        if row.get("packed") != truth["packed"]:
            failed.append("packed")
    else:
        pixels = cast(list[list[int]], row["pixels"])
        target = cast(list[int], truth["channels"])
        size = cast(list[int], truth["size"])
        bound = cast(int, truth["bound"])
        if len(pixels) != size[0] * size[1] or any(
            len(pixel) != len(target)
            or any(abs(c - want) > bound for c, want in zip(pixel, target, strict=True))
            for pixel in pixels
        ):
            failed.append("channels")
    if row.get("decode") != ["1", "0"] * (3 if truth["name"] in {"jpeg-rgb", "jpeg-colour"} else 1):
        failed.append("decode")
    if row.get("composition_verified") is not False:
        failed.append("composition")
    return failed


def run(output: Path) -> dict[str, object]:
    output.mkdir()
    truth_record = {
        "cases": TRUTH,
        "bounds": (
            "Exact neutral DCT DC channels; constant colour Q100/no subsampling "
            "inverse-colour rounding <=2 per channel; exact hand T4 bits and G4 runs. "
            "No nonconstant/real JPEG or composition oracle."
        ),
        "ccitt_source": "https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf",
        "limitations": (
            "No Decode, mask, ICC conversion, page rendering, JPX/JBIG2 or CMYK interpretation."
        ),
    }
    (output / "truth.json").write_text(json.dumps(truth_record, indent=2) + "\n")
    records: list[dict[str, object]] = []
    for index, truth in enumerate(TRUTH):
        case = output / str(index)
        case.mkdir()
        name = cast(str, truth["name"])
        if name.startswith("jpeg"):
            mode = "L" if name == "jpeg-gray" else "RGB"
            if name == "jpeg-colour":
                buffer = io.BytesIO()
                with Image.new("RGB", (16, 8), (18, 52, 86)) as image:
                    image.save(buffer, format="JPEG", quality=100, subsampling=0)
                data = buffer.getvalue()
            else:
                data = jpeg(mode)
            saved = fixture(
                case,
                "/DCTDecode",
                data,
                color="/DeviceGray" if mode == "L" else "/DeviceRGB",
                inverse=True,
                wrapped=True,
            )
        else:
            hand = "hand" in name
            black = name.endswith("black")
            saved = fixture(
                case,
                "/CCITTFaxDecode",
                bytes.fromhex("001a0009a880") if hand else fax(),
                size=(9, 2),
                bits=1,
                inverse=True,
                params=pikepdf.Dictionary(K=0 if hand else -1, Columns=9, Rows=2, BlackIs1=black),
                inline=name == "ccitt-inline",
                stencil=name == "ccitt-inline",
                wrapped=name == "ccitt-g4-black",
            )
        source_bytes = (case / "input.pdf").read_bytes()
        result = samples.collect(saved, saved.pages[0])
        assert result.samples_available, result.concerns
        sample = result.images[0]
        assert sample.packed is not None and sample.decode is not None
        row: dict[str, object] = {
            "name": name,
            "size": list(sample.placement.samples),
            "bits": sample.placement.bits_per_component,
            "packed": sample.packed.hex(),
            "pixels": [list(v) for v in sample.pixels()],
            "decode": [str(v) for v in sample.decode],
            "filters": list(sample.filters),
            "raw_sha256": sample.raw_sha256,
            "parameters": sample.decode_parameters.decode() if sample.decode_parameters else None,
            "source_sha256": saved.sha256,
            "composition_verified": sample.composition_verified,
        }
        assert not failures(row, truth), failures(row, truth)
        assert source_bytes == (case / "input.pdf").read_bytes() == saved.path.read_bytes()
        (case / "input.pdf").unlink()
        assert samples.collect(saved, saved.pages[0]) == result
        records.append(row)
    controls: dict[str, list[str]] = {}
    for name, index, field, value in [
        ("wrong-size", 0, "size", [15, 8]),
        ("wrong-depth", 0, "bits", 16),
        ("wrong-channel", 2, "pixels", [[86, 52, 18]] * 128),
        ("erased-channel-feature", 2, "pixels", [[128, 128, 128]] * 128),
        ("wrong-polarity", 3, "packed", "0000ff80"),
        ("wrong-row-order", 5, "packed", "aa805500"),
        ("applied-decode", 0, "decode", ["0", "1"]),
        ("false-composition", 0, "composition_verified", True),
    ]:
        changed = copy.deepcopy(records[index])
        changed[field] = value
        rejected = failures(changed, TRUTH[index])
        assert rejected
        assert rejected == [
            {
                "size": "size",
                "bits": "bits",
                "pixels": "channels",
                "packed": "packed",
                "decode": "decode",
                "composition_verified": "composition",
            }[field]
        ]
        controls[name] = rejected
    report: dict[str, object] = {
        "format": "BookScanBuilderCodecConstruction",
        "version": 1,
        "pikepdf": pikepdf.__version__,
        "pillow": pillow_version,
        "truth_sha256": hashlib.sha256((output / "truth.json").read_bytes()).hexdigest(),
        "cases": records,
        "controls": controls,
        "source_loss_verified": True,
        "source_snapshot_bytes_unchanged": True,
        "composition_fidelity_verified": False,
        "accepted_project_delivered": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.artifacts), indent=2))
