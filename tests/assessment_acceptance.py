"""Actual snapshot/render/sample/helper coupling; no accepted project or public CLI claim."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import cast

import pikepdf

from bookscan import assessment, intake, native_setup, render, render_record

SIZE = (1200, 900)
LIMITATION = (
    "Within-page geometry unverified; rigid rotation and book alignment do not correct "
    "curvature or scanner-feed variation."
)


def verify_record(record: dict[str, object], wanted: dict[str, object]) -> None:
    """Check literal occurrence/truth facts; never use the product serializer as oracle."""
    for field in ("id", "source_pdf_page", "rgb_sha256", "advisory_hint"):
        if field in wanted:
            assert record[field] == wanted[field], field
    geometry = cast(dict[str, object], record["geometry"])
    assert geometry["pixels"] == wanted["pixels"], "pixels"
    if "geometry" in wanted:
        assert geometry == wanted["geometry"], "geometry"
    analysis = cast(dict[str, object], record["analysis"])
    width, height = cast(list[int], wanted["pixels"])
    assert analysis["regions"] == [[0, 0, width, height]], "regions"
    status, angle, ratio = (
        analysis["native_status"],
        analysis["angle_degrees"],
        analysis["score_ratio"],
    )
    available = status == 0 and angle is not None and ratio is not None and ratio != 0
    assert analysis["available"] is available, "validity"
    rows = cast(list[dict[str, object]], record["triage_reasons"])
    reasons = {cast(str, row["id"]) for row in rows}
    assert len(reasons) == len(rows), "duplicate-reasons"
    assert {"orientation-unverified", "import-fidelity"} <= reasons, "limitations"
    assert ("assessment-unavailable" in reasons) is (not available), "unavailable"
    assert ("skew-nonzero" in reasons) is (available and angle != 0), "nonzero"
    for row in rows:
        assert row["allowed_decisions"] == (
            ["reject", "retain-unresolved"]
            if row["id"] == "skew-nonzero"
            else ["retain-unresolved"]
        ), "decision-domain"
    for field in ("inspected", "estimate_applied", "composition_fidelity_verified"):
        assert record[field] is False, field
    assert record["limitation"] == LIMITATION, "universal-limitation"
    if "angle_target" in wanted:
        assert available and isinstance(angle, (int, float)), "native-angle-unavailable"
        assert abs(angle - cast(float, wanted["angle_target"])) <= 0.125, "sign/angle"
    if wanted.get("blank"):
        assert not available and ratio == 0, "blank-sentinel"
    if wanted.get("range_edge"):
        assert not available and {"assessment-unavailable", "skew-range-edge"} <= reasons, "edge"
    if wanted.get("high_ppi"):
        resolution = cast(dict[str, object], record["resolution"])
        assert resolution["complete"] is True and resolution["maximum_ppi"] == 600, "ppi"
        placements = cast(list[dict[str, object]], resolution["placements"])
        assert len(placements) == 1 and placements[0]["above_300_ppi"] is True, "above-300"
        samples = cast(list[dict[str, object]], record["native_samples"])
        assert samples[0]["packed_sha256"] == wanted["packed_sha256"], "native-source"


def rows(degrees: float) -> bytes:
    """Native aligned truth from declared analytic glyph-like rows, not a renderer."""
    pixels = bytearray(b"\xff" * (1200 * 900 * 3))
    slope = math.tan(math.radians(degrees))
    for row in range(24):
        for x in range(100, 1100):
            if (x // 12) % 3 == 0:
                continue
            top = 140 + row * 24 + round((x - 600) * slope)
            for y in range(top, top + 5 + (x // 12) % 4):
                offset = (y * 1200 + x) * 3
                pixels[offset : offset + 3] = b"\0\0\0"
    return bytes(pixels)


def construct(path: Path, buffers: list[bytes | None], native_detail: bytes) -> None:
    with pikepdf.Pdf.new() as pdf:
        for ordinal, rgb in enumerate(buffers, 1):
            page = pdf.add_blank_page(page_size=(288, 216))
            if ordinal <= 3:
                page.obj.BookScanBuilder = pikepdf.Dictionary(
                    Version=1,
                    Role=["front", "content", "back"][ordinal - 1],
                    SourceSHA256="a" * 64,
                    SourcePage=17 + ordinal,
                )
            elif ordinal == 5:
                page.obj.BookScanBuilder = pikepdf.Dictionary(Version=99, Role="front")
            if rgb is None:
                continue
            high = ordinal == 6
            im = pikepdf.Stream(pdf, native_detail if high else rgb)
            im.Type, im.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
            im.Width, im.Height = (2400, 1800) if high else SIZE
            im.BitsPerComponent, im.Interpolate = 8, False
            im.ColorSpace = pikepdf.Name.DeviceGray if high else pikepdf.Name.DeviceRGB
            page.obj.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=im))
            page.obj.Contents = pikepdf.Stream(pdf, b"q 288 0 0 216 0 0 cm /Im Do Q")
        pdf.pages.append(pdf.pages[0])  # pyright: ignore[reportUnknownMemberType]
        pdf.save(path, min_version="1.7", deterministic_id=True)


def normalized(record: dict[str, object], directory: Path) -> dict[str, object]:
    result = copy.deepcopy(record)
    rendered = cast(dict[str, object], result["render"])
    command = cast(list[str], rendered["command"])
    rendered["command"] = [
        "<PRIVATE_PREFIX>"
        if index == len(command) - 1
        else value.replace(str(directory), "<ARTIFACTS>")
        for index, value in enumerate(command)
    ]
    return result


def run(artifacts: Path, cache: Path) -> dict[str, object]:
    artifacts.mkdir()
    buffers: list[bytes | None] = [rows(0), rows(2), rows(-2), rows(6.5), None, b"not-oracle"]
    native_detail = b"\0\xff" * (2400 * 1800 // 2)
    wanted: list[dict[str, object]] = []
    for ordinal in range(1, 8):
        truth: dict[str, object] = {
            "id": f"occ-{ordinal:06d}",
            "source_pdf_page": ordinal,
            "pixels": [1200, 900],
            "advisory_hint": (
                {
                    "role": ["front", "content", "back"][ordinal - 1],
                    "source_sha256": "a" * 64,
                    "source_page": 17 + ordinal,
                }
                if ordinal <= 3
                else None
            ),
            "geometry": {
                "boxes": [["0", "0", "288", "216"]] * 5,
                "rotate": 0,
                "user_unit": "1",
                "physical_points": ["288", "216"],
                "pixels": [1200, 900],
                "matrix": ["25/6", "0", "0", "-25/6", "0", "900"],
                "extent_changed": False,
            },
        }
        if ordinal == 7:
            truth["advisory_hint"] = {"role": "front", "source_sha256": "a" * 64, "source_page": 18}
        rgb = buffers[ordinal - 1] if ordinal <= 6 else buffers[0]
        if ordinal != 6:
            truth["rgb_sha256"] = hashlib.sha256(
                rgb if rgb is not None else b"\xff" * 3240000
            ).hexdigest()
        if ordinal in (1, 2, 3, 7):
            truth["angle_target"] = {1: 0.0, 2: -2.0, 3: 2.0, 7: 0.0}[ordinal]
        if ordinal == 4:
            truth["range_edge"] = True
        if ordinal == 5:
            truth["blank"] = True
        if ordinal == 6:
            truth.update(high_ppi=True, packed_sha256=hashlib.sha256(native_detail).hexdigest())
        wanted.append(truth)
    manifest: dict[str, object] = {
        "pages": wanted,
        "angle_bound": "0.125 degrees: 2px/1000px phase (~0.115deg) plus 0.01deg search step",
        "pixel_bound": "Exact black/white aligned 300-ppi every-channel construction, no tolerance",
        "high_ppi_bound": "600-ppi source channels/placement only; no baseline preservation oracle",
        "unavailable": (
            "Complete composition/font/profile/real truth and accepted project/public workflow"
        ),
    }
    truth_path = artifacts / "truth.json"
    truth_path.write_text(json.dumps(manifest, indent=2) + "\n")
    truth_digest = hashlib.sha256(truth_path.read_bytes()).hexdigest()
    original = artifacts / "Ordinary assessment input.pdf"
    construct(original, buffers, native_detail)
    saved = intake.snapshot(original, artifacts / "snapshot.pdf")
    original.unlink()  # all processing now uses only the private verified snapshot
    ready = native_setup.preflight(cache)
    helper = native_setup.load_cache(cache).binary
    renderer = render.renderer_path()
    records: list[dict[str, object]] = []
    render_controls: dict[str, str] = {}
    for result, truth in zip(
        assessment.assess_pages(saved, renderer, helper, artifacts), wanted, strict=True
    ):
        record = result.to_dict()
        facts = render_record.restore(record["render"], result.page, saved.path, renderer)
        assert facts.command == result.raster.command
        assert facts.diagnostics == result.raster.diagnostics
        if result.page.source_page == 1:
            for name, index, replacement in (
                ("wrong-page", 2, "2"),
                ("wrong-density", 7, "150"),
                ("wrong-width", 9, "1199"),
                ("cropbox", 5, "-cropbox"),
                ("wrong-source", 15, str(saved.original_path)),
            ):
                wrong = copy.deepcopy(record["render"])
                cast(list[str], cast(dict[str, object], wrong)["command"])[index] = replacement
                try:
                    render_record.restore(wrong, result.page, saved.path, renderer)
                except render_record.RenderRecordError as error:
                    render_controls[name] = error.message
                else:
                    raise AssertionError("Saved render policy substitution escaped: " + name)
                verify_record(record, truth)
        verify_record(record, truth)
        # Equality to the declared raw buffer is independent construction truth;
        # the 600-ppi case deliberately supplies no 300-ppi fidelity assertion.
        rgb = buffers[result.page.source_page - 1] if result.page.source_page <= 6 else buffers[0]
        if result.page.source_page != 6:
            assert result.raster.rgb == (rgb if rgb is not None else b"\xff" * 3240000)
        assert record["source_sha256"] == saved.sha256
        records.append(normalized(record, artifacts))
    controls: dict[str, str] = {}
    faults: list[tuple[str, int, str, object]] = [
        ("wrong-occurrence", 0, "id", "occ-000002"),
        ("erased-rgb", 0, "rgb_sha256", hashlib.sha256(b"\xff" * 3240000).hexdigest()),
        ("wrong-hint", 0, "advisory_hint", None),
        ("missing-assessment", 1, "analysis", {}),
        ("missing-limitations", 1, "triage_reasons", []),
        ("implied-inspection", 2, "inspected", True),
        ("applied-estimate", 2, "estimate_applied", True),
        ("fidelity-pass", 5, "composition_fidelity_verified", True),
        ("wrong-region", 0, "analysis", {"regions": [[0, 0, 1199, 900]]}),
    ]
    for name, index, field, value in faults:
        wrong = copy.deepcopy(records[index])
        wrong[field] = value
        try:
            verify_record(wrong, wanted[index])
        except (AssertionError, KeyError) as error:
            controls[name] = str(error)
        else:
            raise AssertionError("Wrong subject escaped: " + name)
        verify_record(records[4], wanted[4])  # unrelated blank sentinel remains correct
    # A second actual coupling after source loss reproduces every record, not totals.
    resumed: list[dict[str, object]] = []
    for result in assessment.assess_pages(saved, renderer, helper, artifacts):
        record = result.to_dict()
        render_record.restore(record["render"], result.page, saved.path, renderer)
        resumed.append(normalized(record, artifacts))
    assert resumed == records
    assert not list(artifacts.glob(".analysis-*"))
    saved.verify()
    assert hashlib.sha256(truth_path.read_bytes()).hexdigest() == truth_digest
    report: dict[str, object] = {
        "format": "BookScanBuilderAssessmentAcceptance",
        "version": 1,
        "truth": manifest,
        "truth_sha256": truth_digest,
        "source_sha256": saved.sha256,
        "helper_preflight": ready,
        "records": records,
        "controls": controls,
        "render_policy_controls": render_controls,
        "source_loss_itemwise_equal": True,
        "accepted_project_delivered": False,
        "composition_fidelity_verified": False,
    }
    (artifacts / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.artifacts, args.cache), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
