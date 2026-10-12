"""Breaks caught: skipped occurrences, lost concerns, applied pixels and analysis mutation."""

import json
import subprocess
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import NoReturn

import pikepdf
import pytest
from PIL import Image

from bookscan import intake, native_setup, render
from bookscan.skew import AssessmentFailed


def source(tmp_path: Path, hinted: bool = False, cropped: bool = False) -> intake.Snapshot:
    path = tmp_path / "input.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        page.obj.MediaBox = pikepdf.Array([0, 0, 2.4, 1.2])
        if hinted:
            page.obj.BookScanBuilder = pikepdf.Dictionary(
                Version=1, Role="front", SourceSHA256="a" * 64, SourcePage=19
            )
        if cropped:
            page.obj.CropBox = pikepdf.Array([0.24, 0, 2.4, 1.2])
        pdf.pages.append(page)  # pyright: ignore[reportUnknownMemberType]
        blank = pdf.add_blank_page(page_size=(72, 36))
        blank.obj.MediaBox = pikepdf.Array([0, 0, 2.4, 1.2])
        pdf.save(path)
    return intake.snapshot(path, tmp_path / "snapshot.pdf")


def native(
    monkeypatch: pytest.MonkeyPatch,
    *,
    status: int = 0,
    angle: float | None = 0.0,
    ratio: float | None = 10.0,
    diagnostics: str = "",
    rgb_warning: str = "",
    mutate_rgb: bool = False,
) -> None:
    def renderer(
        argv: list[str], *, check_cancel: Callable[[], None]
    ) -> subprocess.CompletedProcess[str]:
        check_cancel()
        with Image.frombytes("RGB", (10, 5), b"\x11\x22\x33" * 50) as image:
            image.save(argv[-1] + ".png", format="PNG")
        return subprocess.CompletedProcess(argv, 0, "", rgb_warning)

    def helper(
        argv: list[str], *, check_cancel: Callable[[], None]
    ) -> subprocess.CompletedProcess[str]:
        check_cancel()
        with Image.open(argv[-1]) as analysis:
            assert analysis.mode == "L" and analysis.size == (10, 5)
            assert analysis.tobytes() == b"\x1f" * 50  # independent RGB luma 31
        return subprocess.CompletedProcess(
            argv,
            0,
            json.dumps(
                {
                    "schema": "BookScanBuilderSkew",
                    "version": 1,
                    "leptonica": "leptonica-1.87.0",
                    "width": 10,
                    "height": 5,
                    "status": status,
                    "angle_degrees": angle,
                    "score_ratio": ratio,
                }
            ),
            diagnostics,
        )

    monkeypatch.setattr(render, "execute", renderer)
    monkeypatch.setattr(native_setup, "execute", helper)
    if mutate_rgb:

        def corrupt(
            binary: Path,
            baseline: Image.Image,
            directory: Path,
            *,
            check_cancel: Callable[[], None],
        ):
            baseline.putpixel((0, 0), (255, 0, 0))
            return native_setup.parse_estimate(
                '{"schema":"BookScanBuilderSkew","version":1,'
                '"leptonica":"leptonica-1.87.0","width":10,"height":5,'
                '"status":0,"angle_degrees":0,"score_ratio":10}',
                "",
                (10, 5),
            )

        monkeypatch.setattr(native_setup, "assess", corrupt)


def test_every_occurrence_including_cover_duplicate_blank_without_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import assessment

    saved = source(tmp_path, hinted=True)
    saved.original_path.unlink()
    native(monkeypatch, angle=-0.00001)
    results = list(assessment.assess_pages(saved, Path("renderer"), Path("helper"), tmp_path))
    assert [p.page.source_page for p in results] == [1, 2, 3]
    assert [p.to_dict()["id"] for p in results] == ["occ-000001", "occ-000002", "occ-000003"]
    assert [p.raster.rgb for p in results] == [b"\x11\x22\x33" * 50] * 3
    for result in results:
        record = result.to_dict()
        assert record["source_sha256"] == saved.sha256
        assert record["inspected"] is False and record["estimate_applied"] is False
        assert result.estimate.region == (0, 0, 10, 5)
        assert result.estimate.angle_degrees == -0.00001
        assert {r.id for r in result.reasons} == {
            "orientation-unverified",
            "skew-nonzero",
            "import-fidelity",
        }
        assert record["retention"] == "baseline-retained/unresolved"
        assert record["composition_fidelity_verified"] is False
        json.dumps(record, allow_nan=False)
    assert results[0].to_dict()["advisory_hint"] == {
        "role": "front",
        "source_sha256": "a" * 64,
        "source_page": 19,
    }
    assert results[2].to_dict()["advisory_hint"] is None
    assert not list(tmp_path.glob(".analysis-*"))


@pytest.mark.parametrize(
    ("status", "angle", "ratio", "reason"),
    [
        (0, 0.0, 10.0, None),
        (0, 1e-9, 10.0, "skew-nonzero"),
        (1, 0.0, 10.0, "assessment-unavailable"),
        (0, 0.0, 0.0, "assessment-unavailable"),
        (0, None, 10.0, "assessment-unavailable"),
        (0, 1.0, None, "assessment-unavailable"),
    ],
)
def test_invalid_estimates_and_tiny_nonzero_never_change_rgb(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    angle: float | None,
    ratio: float | None,
    reason: str | None,
) -> None:
    from bookscan import assessment

    saved = source(tmp_path)
    native(monkeypatch, status=status, angle=angle, ratio=ratio)
    result = assessment.assess_page(
        saved, saved.pages[0], Path("renderer"), Path("helper"), tmp_path
    )
    assert result.raster.rgb == b"\x11\x22\x33" * 50
    assert {r.id for r in result.reasons} == {
        "orientation-unverified",
        "import-fidelity",
        *([reason] if reason else []),
    }
    for r in result.reasons:
        assert r.allowed_decisions == (
            ("reject", "retain-unresolved") if r.id == "skew-nonzero" else ("retain-unresolved",)
        )
    assert result.to_dict()["analysis"] == result.estimate.to_dict()
    json.dumps(result.to_dict(), allow_nan=False)


def test_crop_decoder_and_range_edge_concerns_remain_separate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import assessment

    saved = source(tmp_path, cropped=True)
    native(
        monkeypatch, angle=6.5, diagnostics="max found at sweep edge", rgb_warning="decoder note"
    )
    result = assessment.assess_page(
        saved, saved.pages[0], Path("renderer"), Path("helper"), tmp_path
    )
    reasons = {r.id: r for r in result.reasons}
    assert set(reasons) == {
        "orientation-unverified",
        "import-fidelity",
        "skew-nonzero",
        "skew-range-edge",
        "extent-change",
        "decoder-warning",
    }
    assert reasons["decoder-warning"].details == ("decoder note",)
    assert result.to_dict()["geometry"] == {
        "boxes": [
            ["0", "0", "2.4", "1.2"],
            ["0.24", "0", "2.4", "1.2"],
            ["0.24", "0", "2.4", "1.2"],
            ["0.24", "0", "2.4", "1.2"],
            ["0.24", "0", "2.4", "1.2"],
        ],
        "rotate": 0,
        "user_unit": "1",
        "physical_points": ["2.4", "1.2"],
        "pixels": [10, 5],
        "matrix": ["25/6", "0", "0", "-25/6", "0", "5"],
        "extent_changed": True,
    }


def test_analysis_mutation_fails_without_returning_an_assessment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import assessment

    saved = source(tmp_path)
    native(monkeypatch, mutate_rgb=True)
    with pytest.raises(AssessmentFailed, match="modified"):
        assessment.assess_page(saved, saved.pages[0], Path("renderer"), Path("helper"), tmp_path)


@pytest.mark.parametrize("fault", ["missing", "short", "wrong-size", "wrong-page"])
def test_invalid_subject_precedes_helper_and_returns_no_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    from bookscan import assessment

    saved = source(tmp_path)
    native(monkeypatch)
    page = saved.pages[0]
    if fault == "missing":
        saved.path.unlink()
    elif fault == "wrong-page":
        page = replace(page, source_page=99)
    else:

        def bad(*args: object, **kwargs: object) -> render.Raster:
            return render.Raster((9, 5) if fault == "wrong-size" else (10, 5), b"bad", "", ())

        monkeypatch.setattr(render, "render_page", bad)

    def forbidden(*args: object, **kwargs: object) -> NoReturn:
        pytest.fail("helper called on invalid subject")

    monkeypatch.setattr(native_setup, "assess", forbidden)
    with pytest.raises((intake.ImportFailure, AssessmentFailed)):
        assessment.assess_page(saved, page, Path("renderer"), Path("helper"), tmp_path)


def test_cancellation_propagates_unchanged_and_stops_later_occurrences(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import assessment

    saved = source(tmp_path)
    native(monkeypatch)
    sentinel = RuntimeError("owner cancelled")
    stop = False

    def cancel() -> None:
        if stop:
            raise sentinel

    rows = assessment.assess_pages(
        saved, Path("renderer"), Path("helper"), tmp_path, check_cancel=cancel
    )
    assert next(rows).page.source_page == 1
    stop = True
    with pytest.raises(RuntimeError) as caught:
        next(rows)
    assert caught.value is sentinel


def test_record_is_detached_from_returned_mutable_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import assessment

    saved = source(tmp_path)
    native(monkeypatch)
    result = assessment.assess_page(
        saved, saved.pages[0], Path("renderer"), Path("helper"), tmp_path
    )
    first = result.to_dict()
    first["analysis"] = "altered"
    first["triage_reasons"] = []
    assert result.to_dict()["analysis"] == result.estimate.to_dict()
    assert len(result.reasons) == 2


def test_assessed_serialization_cannot_save_inconsistent_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    from bookscan import analysis_record, assessment

    saved = source(tmp_path)
    native(monkeypatch, ratio=0.0)
    result = assessment.assess_page(
        saved, saved.pages[0], Path("renderer"), Path("helper"), tmp_path
    )
    wrong = replace(result, estimate=replace(result.estimate, available=True, reasons=()))
    before = result.raster.rgb
    with pytest.raises(analysis_record.AnalysisRecordError):
        wrong.to_dict()
    assert result.raster.rgb == before
    assert result.to_dict()["analysis"] == {
        **result.estimate.to_dict(),
        "available": False,
        "reasons": ["assessment-unavailable"],
    }


@pytest.mark.parametrize("fault", ["id", "rgb", "region", "hint", "reason", "applied"])
def test_independent_record_verifier_rejects_wrong_subject(fault: str) -> None:
    from assessment_acceptance import verify_record

    # Literal truth is distinct from the product serializer and native estimator.
    wanted: dict[str, object] = {
        "id": "occ-000007",
        "source_pdf_page": 7,
        "rgb_sha256": "b" * 64,
        "pixels": [1200, 900],
        "advisory_hint": None,
    }
    record: dict[str, object] = {
        **wanted,
        "geometry": {"pixels": [1200, 900]},
        "analysis": {
            "regions": [[0, 0, 1200, 900]],
            "available": True,
            "native_status": 0,
            "angle_degrees": -2.0,
            "score_ratio": 10.0,
        },
        "triage_reasons": [
            {"id": reason, "allowed_decisions": decisions}
            for reason, decisions in [
                ("orientation-unverified", ["retain-unresolved"]),
                ("import-fidelity", ["retain-unresolved"]),
                ("skew-nonzero", ["reject", "retain-unresolved"]),
            ]
        ],
        "inspected": False,
        "estimate_applied": False,
        "composition_fidelity_verified": False,
        "limitation": "Within-page geometry unverified; rigid rotation and book alignment "
        "do not correct curvature or scanner-feed variation.",
    }
    verify_record(record, wanted)
    if fault == "id":
        record["id"] = "occ-000008"
    elif fault == "rgb":
        record["rgb_sha256"] = "c" * 64
    elif fault == "region":
        record["analysis"] = {"regions": [[0, 0, 1199, 900]]}
    elif fault == "hint":
        record["advisory_hint"] = {"role": "front"}
    elif fault == "reason":
        record["triage_reasons"] = []
    else:
        record["estimate_applied"] = True
    with pytest.raises(AssertionError):
        verify_record(record, wanted)
