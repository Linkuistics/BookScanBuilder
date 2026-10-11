"""Mutation checks against the real staged-output validator, not matching fingerprints."""

import io
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pikepdf
import pytest
from pdf_fixtures import rich_pdf
from test_preview import labels

from bookscan import copying
from bookscan.pdf import Geometry, Node, Projection, Ref, items
from bookscan.prepare import operate
from bookscan.results import PreparationError
from bookscan.selections import parse


@pytest.mark.parametrize(
    "mutation",
    [
        "bytes",
        "mask",
        "soft-mask",
        "globals",
        "decode",
        "filter",
        "nested-key",
        "name",
        "string",
        "boolean",
        "MediaBox",
        "CropBox",
        "BleedBox",
        "TrimBox",
        "ArtBox",
        "Rotate",
        "UserUnit",
        "marker-role",
        "marker-version",
        "marker-page",
        "marker-hash",
        "marker-key",
        "owner",
        "direct-annot",
        "page-type",
        "version",
        "count",
    ],
)
def test_runtime_rejects_mutation(tmp_path: Path, mutation: str) -> None:
    source = rich_pdf(tmp_path / "in.pdf")
    expected = operate(
        parse(["--content", str(source), "--output", str(tmp_path / "out.pdf"), "--dry-run"])
    )
    stream = io.BytesIO()
    copying.save(expected, stream)
    copying.validate(expected, stream)
    stream.seek(0)
    with pikepdf.Pdf.open(stream, attempt_recovery=False) as pdf:
        page = pdf.pages[0].obj
        resources = page["/Resources"]
        form = resources["/XObject"]["/Form"]
        image = form["/Resources"]["/XObject"]["/Im"]
        marker = page["/BookScanBuilder"]
        if mutation in {"bytes", "mask", "soft-mask", "globals"}:
            target = {
                "bytes": image,
                "mask": form["/Resources"]["/XObject"]["/Mask"],
                "soft-mask": image["/SMask"],
                "globals": image["/DecodeParms"]["/JBIG2Globals"],
            }[mutation]
            data = target.read_raw_bytes()
            target.write(
                data[:-1] + bytes([data[-1] ^ 1]),
                filter=target.get("/Filter"),  # pyright: ignore[reportArgumentType]
                decode_parms=target.get("/DecodeParms"),  # pyright: ignore[reportArgumentType]
            )
        elif mutation == "decode":
            image["/DecodeParms"]["/Predictor"] = 2
        elif mutation == "filter":
            image["/Filter"] = pikepdf.Name.Test
        elif mutation == "nested-key":
            form["/Changed"] = 1
        elif mutation == "name":
            resources["/RetainedName"] = pikepdf.Name.Changed
        elif mutation == "string":
            resources["/RetainedString"] = pikepdf.String(b"different")
        elif mutation == "boolean":
            resources["/RetainedBoolean"] = 1
        elif mutation in {"MediaBox", "CropBox", "BleedBox", "TrimBox", "ArtBox"}:
            page["/" + mutation][0] += 1
        elif mutation == "Rotate":
            page["/Rotate"] = 180
        elif mutation == "UserUnit":
            page["/UserUnit"] = 3
        elif mutation == "marker-role":
            marker["/Role"] = pikepdf.String("back")
        elif mutation == "marker-version":
            marker["/Version"] = True
        elif mutation == "marker-page":
            marker["/SourcePage"] = 2
        elif mutation == "marker-hash":
            marker["/SourceSHA256"] = pikepdf.String("0" * 64)
        elif mutation == "marker-key":
            marker["/Extra"] = 1
        elif mutation == "owner":
            del page["/Annots"][0]["/P"]
        elif mutation == "direct-annot":
            page["/Annots"][0] = pikepdf.Dictionary(dict(items(page["/Annots"][0])))
        elif mutation == "page-type":
            page["/Type"] = pikepdf.Name.Pages
        elif mutation == "version":
            pdf.Root["/Version"] = pikepdf.Name("/1.6")
        elif mutation == "count":
            pdf.add_blank_page()
        changed = io.BytesIO()
        pdf.save(
            changed,
            min_version="1.3" if mutation == "version" else "1.7",
            force_version="1.6" if mutation == "version" else "1.7",
            compress_streams=False,
            stream_decode_level=pikepdf.StreamDecodeLevel.none,
        )
    with pytest.raises(PreparationError) as error:
        copying.validate(expected, changed)
    assert error.value.code == "OUTPUT_INVALID"


def test_pair_comparison_ignores_sharing_and_storage() -> None:
    a = Projection(
        Geometry((), 0, Decimal(1)),
        Ref(0),
        (Node("array", items=(Ref(1), Ref(1))), Node("dictionary", (("/K", 1),))),
        False,
    )
    b = replace(
        a,
        nodes=(
            Node("array", items=(Ref(1), Ref(2))),
            Node("dictionary", (("/K", 1),)),
            Node("dictionary", (("/K", 1),)),
        ),
    )
    copying.compare(a, b)
    with pytest.raises(PreparationError):
        copying.compare(a, replace(b, nodes=(*b.nodes[:2], Node("dictionary", (("/K", 2),)))))


def test_markers_cannot_alias(tmp_path: Path) -> None:
    source = labels(tmp_path / "in.pdf", 2)
    expected = operate(
        parse(["--content", str(source), "1,1", "--output", str(tmp_path / "out.pdf"), "--dry-run"])
    )
    stream = io.BytesIO()
    copying.save(expected, stream)
    with pikepdf.Pdf.open(stream) as pdf:
        pdf.pages[1].obj["/BookScanBuilder"] = pdf.pages[0].obj["/BookScanBuilder"]
        changed = io.BytesIO()
        pdf.save(changed, compress_streams=False)
    with pytest.raises(PreparationError) as error:
        copying.validate(expected, changed)
    assert error.value.code == "OUTPUT_INVALID"
