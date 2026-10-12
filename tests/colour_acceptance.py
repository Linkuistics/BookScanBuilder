"""Independent native Decode/palette/colour-key truth; no page-colour oracle."""

import argparse
import copy
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pikepdf

from bookscan import colour, intake, samples

# Literal bit/byte constructions and hand-derived rational/channel truth, fixed
# before any PDF or interpreted display. The RGB bytes are device diagnostics.
TRUTH: list[dict[str, object]] = [
    {
        "name": "gray2",
        "size": [3, 2],
        "bits": 2,
        "packed": "18e4",
        "channels": [["0"], ["1/3"], ["2/3"], ["1"], ["2/3"], ["1/3"]],
        "rgb": "000000555555aaaaaaffffffaaaaaa555555",
        "alpha": None,
        "unavailable": False,
    },
    {
        "name": "inverse-gray",
        "size": [3, 1],
        "bits": 8,
        "packed": "0080ff",
        "channels": [["1"], ["127/255"], ["0"]],
        "rgb": "ffffff7f7f7f000000",
        "alpha": None,
        "unavailable": False,
    },
    {
        "name": "rgb-key",
        "size": [2, 1],
        "bits": 8,
        "packed": "010203010204",
        "channels": [["254/255", "253/255", "84/85"], ["254/255", "253/255", "251/255"]],
        "rgb": "fefdfcfefdfb",
        "alpha": "00ff",
        "unavailable": False,
    },
    {
        "name": "indexed-rgb",
        "size": [4, 1],
        "bits": 2,
        "packed": "1b",
        "channels": [
            ["0", "128/255", "1"],
            ["1", "128/255", "0"],
            ["1", "128/255", "0"],
            ["1", "128/255", "0"],
        ],
        "rgb": "0080ffff8000ff8000ff8000",
        "alpha": None,
        "unavailable": False,
    },
    {
        "name": "stencil",
        "size": [2, 1],
        "bits": 1,
        "packed": "40",
        "channels": [["1"], ["0"]],
        "rgb": "ffffff000000",
        "alpha": None,
        "unavailable": False,
    },
    {
        "name": "icc",
        "size": [1, 1],
        "bits": 8,
        "packed": "0080ff",
        "channels": [["-1", "128/255", "4"]],
        "rgb": None,
        "alpha": None,
        "unavailable": True,
    },
    {
        "name": "cmyk",
        "size": [1, 1],
        "bits": 8,
        "packed": "001122ff",
        "channels": [["0", "1/15", "2/15", "1"]],
        "rgb": None,
        "alpha": None,
        "unavailable": True,
    },
    {
        "name": "gray16",
        "size": [2, 1],
        "bits": 16,
        "packed": "0001fffe",
        "channels": [["1/65535"], ["65534/65535"]],
        "rgb": "000000ffffff",
        "alpha": None,
        "unavailable": False,
    },
]


def failures(row: Mapping[str, object], truth: Mapping[str, object]) -> list[str]:
    return [
        key
        for key in ("size", "bits", "packed", "channels", "rgb", "alpha", "unavailable")
        if row.get(key) != truth[key]
    ] + (["composition"] if row.get("composition_verified") is not False else [])


def fixture(source: Path) -> None:
    with pikepdf.Pdf.new() as pdf:
        objects: list[pikepdf.Object] = []
        for truth in TRUTH:
            name = truth["name"]
            obj = pdf.make_stream(bytes.fromhex(cast(str, truth["packed"])))  # pyright: ignore[reportUnknownMemberType]
            obj.Type, obj.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
            obj.Width, obj.Height = cast(list[int], truth["size"])
            obj.BitsPerComponent = truth["bits"]
            obj.ColorSpace = pikepdf.Name.DeviceGray
            if name == "inverse-gray":
                obj.Decode = pikepdf.Array([1, 0])
            elif name == "rgb-key":
                obj.ColorSpace = pikepdf.Name.DeviceRGB
                obj.Decode = pikepdf.Array([1, 0] * 3)
                obj.Mask = pikepdf.Array([1, 1, 2, 2, 3, 3])
            elif name == "indexed-rgb":
                obj.ColorSpace = pikepdf.Array(
                    [
                        pikepdf.Name.Indexed,
                        pikepdf.Name.DeviceRGB,
                        1,
                        pikepdf.String(bytes.fromhex("0080ffff8000")),
                    ]
                )
            elif name == "stencil":
                obj.ImageMask, obj.Decode = True, pikepdf.Array([1, 0])
                del obj.ColorSpace
            elif name == "icc":
                profile = pdf.make_stream(b"intentionally unverified ICC profile")  # pyright: ignore[reportUnknownMemberType]
                profile.N, profile.Range = 3, pikepdf.Array([-1, 1, 0, 1, 2, 4])
                obj.ColorSpace = pikepdf.Array([pikepdf.Name.ICCBased, profile])
            elif name == "cmyk":
                obj.ColorSpace = pikepdf.Name.DeviceCMYK
            page = pdf.add_blank_page(page_size=(72, 72))
            page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
            page.Contents = pdf.make_stream(b"72 0 0 72 0 0 cm /I Do")  # pyright: ignore[reportUnknownMemberType]
            objects.append(obj)
        pdf.add_blank_page(page_size=(72, 72))
        duplicate = pdf.add_blank_page(page_size=(72, 72))
        duplicate.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=objects[0]))
        duplicate.Contents = pdf.make_stream(b"72 0 0 72 0 0 cm /I Do")  # pyright: ignore[reportUnknownMemberType]
        pdf.save(source, static_id=True)


def record(subject: samples.Sample, name: str) -> dict[str, object]:
    shown = colour.display(subject)
    assert shown.limitations and "uncombined" in shown.label
    return {
        "name": name,
        "size": list(shown.size),
        "bits": subject.placement.bits_per_component,
        "packed": subject.packed.hex() if subject.packed is not None else None,
        "channels": [[str(v) for v in pixel] for pixel in colour.channels(subject)],
        "rgb": shown.rgb.hex() if shown.rgb is not None else None,
        "alpha": shown.colour_key_alpha.hex() if shown.colour_key_alpha is not None else None,
        "colour_space": shown.colour_space,
        "unavailable": shown.unavailable is not None,
        "missing_oracle": shown.unavailable,
        "label": shown.label,
        "limitations": list(shown.limitations),
        "composition_verified": subject.composition_verified,
    }


def run(output: Path) -> dict[str, object]:
    output.mkdir()
    truth_record = {
        "cases": TRUTH,
        "source": "https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf",
        "sections": ["8.9.5.2", "8.6.6.3", "8.9.6.4"],
        "bounds": "Exact rational channels; device RGB nearest-8-bit/half-up display. No sampling.",
        "limitations": (
            "No validated ICC/CMYK conversion, mask painting/composition, "
            "interpolation or complete-page fidelity."
        ),
    }
    (output / "truth.json").write_text(json.dumps(truth_record, indent=2) + "\n")
    source = output / "input.pdf"
    fixture(source)
    saved = intake.snapshot(source, output / "snapshot.pdf")
    before = saved.path.read_bytes()
    inventories = [samples.collect(saved, page) for page in saved.pages]
    assert len(inventories) == 10 and not inventories[8].images
    assert all(item.samples_available for item in inventories)
    rows = [
        record(item.images[0], cast(str, truth["name"]))
        for item, truth in zip(inventories[:8], TRUTH, strict=True)
    ]
    for row, truth in zip(rows, TRUTH, strict=True):
        assert not failures(row, truth), failures(row, truth)
    assert record(inventories[9].images[0], "gray2") == rows[0]
    assert source.read_bytes() == saved.path.read_bytes() == before
    source.unlink()
    assert [samples.collect(saved, page) for page in saved.pages] == inventories
    assert saved.path.read_bytes() == before
    controls: dict[str, list[str]] = {}
    for name, index, field, value in [
        ("wrong-grid", 0, "size", [2, 3]),
        ("wrong-depth", 7, "bits", 8),
        ("erased-source-feature", 0, "packed", "0000"),
        ("ignored-decode", 1, "channels", [["0"], ["128/255"], ["1"]]),
        ("wrong-palette-colour", 3, "rgb", "ff8000" * 4),
        ("decode-before-key", 2, "alpha", "ffff"),
        ("fabricated-icc-rgb", 5, "rgb", "0080ff"),
        ("false-conversion-availability", 6, "unavailable", False),
        ("false-composition", 0, "composition_verified", True),
    ]:
        changed = copy.deepcopy(rows[index])
        changed[field] = value
        rejected = failures(changed, TRUTH[index])
        assert rejected == ["composition" if field == "composition_verified" else field]
        controls[name] = rejected
    report: dict[str, object] = {
        "format": "BookScanBuilderColourConstruction",
        "version": 1,
        "pikepdf": pikepdf.__version__,
        "source_sha256": saved.sha256,
        "truth_sha256": hashlib.sha256((output / "truth.json").read_bytes()).hexdigest(),
        "cases": rows,
        "controls": controls,
        "source_positions": list(range(1, 11)),
        "blank_source_position": 9,
        "duplicate_source_position": 10,
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
