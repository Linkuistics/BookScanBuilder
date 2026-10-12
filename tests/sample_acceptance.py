"""Independent packed-sample truth; no page renderer or composition-fidelity verdict."""

import argparse
import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import TypedDict, cast

import pikepdf

from bookscan import intake, samples


# These literal grids and metadata precede all generated PDF/decoding output.
class Truth(TypedDict):
    name: str
    size: list[int]
    bits: int
    data: str
    color: str
    pixels: list[list[int]]
    decode: list[int]


TRUTH: list[Truth] = [
    {
        "name": "gray1",
        "size": [3, 2],
        "bits": 1,
        "data": "a040",
        "color": "/DeviceGray",
        "pixels": [[1], [0], [1], [0], [1], [0]],
        "decode": [0, 1],
    },
    {
        "name": "gray2",
        "size": [3, 2],
        "bits": 2,
        "data": "18e4",
        "color": "/DeviceGray",
        "pixels": [[0], [1], [2], [3], [2], [1]],
        "decode": [0, 1],
    },
    {
        "name": "gray4",
        "size": [3, 1],
        "bits": 4,
        "data": "1f70",
        "color": "/DeviceGray",
        "pixels": [[1], [15], [7]],
        "decode": [0, 1],
    },
    {
        "name": "gray16",
        "size": [2, 1],
        "bits": 16,
        "data": "0102fffe",
        "color": "/DeviceGray",
        "pixels": [[258], [65534]],
        "decode": [0, 1],
    },
    {
        "name": "rgb",
        "size": [2, 1],
        "bits": 8,
        "data": "0080ff123456",
        "color": "/DeviceRGB",
        "pixels": [[0, 128, 255], [18, 52, 86]],
        "decode": [1, 0, 0, 1, 1, 0],
    },
    {
        "name": "cmyk",
        "size": [1, 1],
        "bits": 8,
        "data": "01234567",
        "color": "/DeviceCMYK",
        "pixels": [[1, 35, 69, 103]],
        "decode": [0, 1, 0, 1, 0, 1, 0, 1],
    },
]


def make_fixture(path: Path) -> None:
    with pikepdf.Pdf.new() as pdf:
        for row in TRUTH:
            page = pdf.add_blank_page(page_size=(72, 72))
            obj = pdf.make_stream(bytes.fromhex(str(row["data"])))  # pyright: ignore[reportUnknownMemberType]
            obj.Type, obj.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
            obj.Width, obj.Height = row["size"]
            obj.BitsPerComponent, obj.ColorSpace = row["bits"], pikepdf.Name(str(row["color"]))
            obj.Decode = pikepdf.Array(row["decode"])
            page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
            page.Contents = pdf.make_stream(b"72 0 0 72 0 0 cm /I Do")  # pyright: ignore[reportUnknownMemberType]
        # Distinct occurrences of the same complete first page, and a blank.
        pdf.pages.append(pdf.pages[0])
        pdf.add_blank_page(page_size=(72, 72))
        pdf.save(path, min_version="1.7", static_id=True)


def record(sample: samples.Sample) -> dict[str, object]:
    assert sample.color is not None and sample.packed is not None and sample.decode is not None
    return {
        "size": list(sample.placement.samples),
        "bits": sample.placement.bits_per_component,
        "data": sample.packed.hex(),
        "pixels": [list(v) for v in sample.pixels()],
        "color": sample.color.kind,
        "decode": [str(v) for v in sample.decode],
        "ppi": list(sample.placement.ppi),
        "matrix": [str(v) for v in sample.placement.matrix],
        "path": list(sample.placement.path),
        "raw_sha256": sample.raw_sha256,
        "filters": list(sample.filters),
        "parameters": sample.decode_parameters.decode() if sample.decode_parameters else None,
        "composition_verified": sample.composition_verified,
    }


def failures(row: Mapping[str, object], want: Truth) -> list[str]:
    expected = dict(want)
    expected.pop("name", None)
    expected["decode"] = [str(v) for v in want["decode"]]
    expected["ppi"] = want["size"]
    expected["matrix"] = ["300", "0", "0", "-300", "0", "300"]
    return [key for key, value in expected.items() if row.get(key) != value]


def run(output: Path) -> dict[str, object]:
    output.mkdir()
    truth = {
        "version": 1,
        "grids": TRUTH,
        "bounds": "Exact packed bytes/integer channels; no RGB conversion or rendered-page oracle.",
        "mapping": (
            "Each image unit square covers 72x72 PDF points = 300x300 baseline pixels; "
            "x-right/y-down."
        ),
        "controls": [
            "wrong-image",
            "wrong-row-padding",
            "wrong-colour",
            "wrong-decode",
            "wrong-ppi",
            "wrong-placement",
            "wrong-order",
        ],
    }
    (output / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    original = output / "input.pdf"
    make_fixture(original)
    original_sha = hashlib.sha256(original.read_bytes()).hexdigest()
    saved = intake.snapshot(original, output / "private.pdf")
    observed: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    for page in saved.pages:
        result = samples.collect(saved, page)
        assert result.samples_available
        if result.images:
            rows.append(record(result.images[0]))
        observed.append(
            {
                "source_page": page.source_page,
                "images": [record(s) for s in result.images],
                "concerns": list(result.concerns),
                "resolution": asdict(result.resolution),
                "composition_unavailable": result.composition_unavailable,
            }
        )
    wants = [*TRUTH, TRUTH[0]]
    for row, want in zip(rows, wants, strict=True):
        assert not failures(row, want), (row, want)
    assert observed[-1]["images"] == []
    assert observed[0]["source_page"] != observed[6]["source_page"]
    controls: dict[str, list[str]] = {}
    for name, field, value, index in [
        ("wrong-image", "data", "0040", 0),
        ("wrong-row-padding", "pixels", [[1], [0], [1], [0], [0], [0]], 0),
        ("wrong-colour", "color", "/DeviceGray", 4),
        ("wrong-decode", "decode", ["0", "1", "0", "1", "0", "1"], 4),
        ("wrong-ppi", "ppi", [300, 300], 0),
        ("wrong-placement", "matrix", ["300", "0", "0", "-300", "1", "300"], 0),
    ]:
        changed = dict(rows[index])
        changed[str(field)] = value
        found = failures(changed, wants[index])
        assert found == [field], (name, found)
        controls[str(name)] = found
    swapped = failures(rows[1], wants[0])
    assert swapped and "bits" in swapped
    controls["wrong-order"] = swapped
    assert hashlib.sha256(original.read_bytes()).hexdigest() == original_sha
    before = saved.path.read_bytes()
    original.unlink()
    resumed = [samples.collect(saved, p) for p in saved.pages]
    assert [[record(s) for s in inventory.images] for inventory in resumed] == [
        p["images"] for p in observed
    ]
    assert saved.path.read_bytes() == before
    # Fraction metadata is made JSON-safe without losing its exact representation.
    report = {
        "format": "BookScanBuilderNativeSampleConstruction",
        "version": 1,
        "source_sha256": original_sha,
        "pages": observed,
        "controls": controls,
        "source_loss_verified": True,
        "snapshot_bytes_unchanged": True,
        "composition_fidelity_verified": False,
        "accepted_project_delivered": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    return cast(dict[str, object], json.loads(json.dumps(report, default=str)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    run(args.artifacts)
    print(args.artifacts / "report.json")


if __name__ == "__main__":
    main()
