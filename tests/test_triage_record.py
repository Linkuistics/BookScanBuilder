"""Catch lost/forged initial limitations and inconsistent saved reason domains.

Literal expected details are independent of the writer. Source/geometry and
checkpoint tests use real files; these remain component checks, not acceptance
of unverified render/native payloads or a complete imported project.
"""

import copy
import json
import subprocess
from collections.abc import Iterator
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import cast

import pikepdf
import pytest

from bookscan import assessment, intake, ownership, placement, project_header, records, samples
from bookscan.skew import Estimate, parse_estimate


@pytest.fixture
def subject(tmp_path: Path) -> tuple[intake.Page, Estimate, samples.Inventory]:
    original = tmp_path / "original.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        page.obj.MediaBox = pikepdf.Array([0, 0, 2.4, 1.2])
        page.obj.CropBox = pikepdf.Array([0.24, 0, 2.4, 1.2])
        pdf.save(original)
    saved = intake.snapshot(original, tmp_path / "source.pdf")
    original.unlink()
    estimate = parse_estimate(
        '{"schema":"BookScanBuilderSkew","version":1,"leptonica":"leptonica-1.87.0",'
        '"width":10,"height":5,"status":0,"angle_degrees":6.5,"score_ratio":10}',
        "sweep diagnostic",
        (10, 5),
    )
    # Two source samples across one baseline pixel: exactly 600 ppi.
    image = placement.Placement(
        ("page[1]", "ImA"),
        (7, 0),
        "image",
        (2, 1),
        8,
        "/DeviceRGB",
        (Fraction(1), Fraction(0), Fraction(0), Fraction(1), Fraction(0), Fraction(0)),
        (600.0, 300.0),
    )
    native = samples.Inventory(
        placement.Analysis((image,), ("resolution concern",)),
        (),
        ("sample concern",),
        "Missing independent composition truth",
    )
    return saved.pages[0], estimate, native


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    path = tmp_path / "saved café project"
    path.mkdir()
    with ownership.Writer.acquire(path, ownership.provision(path)) as held:
        yield held


def literal() -> list[dict[str, object]]:
    return [
        {
            "id": name,
            "details": details,
            "allowed_decisions": decisions,
            "disposition": "baseline-retained/unresolved",
        }
        for name, details, decisions in [
            (
                "orientation-unverified",
                ["No orientation review or edit applied."],
                ["retain-unresolved"],
            ),
            ("skew-nonzero", ["sweep diagnostic"], ["reject", "retain-unresolved"]),
            ("skew-range-edge", ["sweep diagnostic"], ["retain-unresolved"]),
            (
                "import-fidelity",
                [
                    "resolution concern",
                    "sample concern",
                    "Above-300-ppi contributing placement: page[1]/ImA",
                    "Missing independent composition truth",
                ],
                ["retain-unresolved"],
            ),
            (
                "extent-change",
                ["Effective MediaBox and CropBox display regions differ."],
                ["retain-unresolved"],
            ),
            ("decoder-warning", ["decoder café"], ["retain-unresolved"]),
        ]
    ]


def test_restore_binds_all_initial_reasons_and_returns_detached_facts(
    subject: tuple[intake.Page, Estimate, samples.Inventory],
) -> None:
    from bookscan import triage_record

    page, estimate, native = subject
    value = literal()
    parsed = records.decode(json.dumps({"reasons": value}).encode())["reasons"]
    result = triage_record.restore(parsed, page, estimate, native, "decoder café")
    assert [r.id for r in result] == [
        "orientation-unverified",
        "skew-nonzero",
        "skew-range-edge",
        "import-fidelity",
        "extent-change",
        "decoder-warning",
    ]
    assert [r.to_dict() for r in result] == value
    assert result[3].details == (
        "resolution concern",
        "sample concern",
        "Above-300-ppi contributing placement: page[1]/ImA",
        "Missing independent composition truth",
    )
    assert result[1].allowed_decisions == ("reject", "retain-unresolved")
    value[0]["details"] = ["changed"]
    assert result[0].details == ("No orientation review or edit applied.",)


@pytest.mark.parametrize(
    "fault",
    [
        "drop-orientation",
        "drop-fidelity",
        "drop-extent",
        "drop-decoder",
        "drop-edge",
        "drop-skew",
        "swap",
        "duplicate",
        "unknown",
        "canvas-invented",
        "extra-field",
        "missing-field",
        "nonobject",
        "tuple-roster",
        "dict-roster",
        "bool-id",
        "tuple-details",
        "string-details",
        "bool-detail",
        "surrogate-detail",
        "wrong-detail",
        "lost-concern",
        "wrong-placement",
        "fidelity-reject",
        "skew-no-reject",
        "tuple-domain",
        "claimed-accepted",
        "claimed-rejected",
        "claimed-retained",
        "bool-disposition",
    ],
)
def test_saved_reasons_cannot_drop_concerns_or_grant_acceptance(
    subject: tuple[intake.Page, Estimate, samples.Inventory], fault: str
) -> None:
    from bookscan import triage_record

    reasons = literal()
    value: object = reasons
    if fault.startswith("drop-"):
        reasons.pop(
            {"orientation": 0, "skew": 1, "edge": 2, "fidelity": 3, "extent": 4, "decoder": 5}[
                fault[5:]
            ]
        )
    elif fault == "swap":
        reasons[0], reasons[1] = reasons[1], reasons[0]
    elif fault == "duplicate":
        reasons.append(copy.deepcopy(reasons[0]))
    elif fault in {"unknown", "canvas-invented"}:
        reasons[0]["id"] = "unknown" if fault == "unknown" else "canvas-warning"
    elif fault == "extra-field":
        reasons[0]["inspected"] = True
    elif fault == "missing-field":
        del reasons[0]["details"]
    elif fault == "nonobject":
        reasons[0] = cast(dict[str, object], [])
    elif fault == "tuple-roster":
        value = tuple(reasons)
    elif fault == "dict-roster":
        value = {"reasons": reasons}
    elif fault == "bool-id":
        reasons[0]["id"] = True
    elif fault in {
        "tuple-details",
        "string-details",
        "bool-detail",
        "surrogate-detail",
        "wrong-detail",
    }:
        reasons[0]["details"] = {
            "tuple-details": ("No orientation review or edit applied.",),
            "string-details": "No orientation review or edit applied.",
            "bool-detail": [True],
            "surrogate-detail": ["\ud800"],
            "wrong-detail": ["Geometry verified"],
        }[fault]
    elif fault in {"lost-concern", "wrong-placement"}:
        details = cast(list[str], reasons[3]["details"])
        if fault == "lost-concern":
            details.pop()
        else:
            details[2] = "Above-300-ppi contributing placement: page[2]/ImA"
    elif fault == "fidelity-reject":
        reasons[3]["allowed_decisions"] = ["reject", "retain-unresolved"]
    elif fault == "skew-no-reject":
        reasons[1]["allowed_decisions"] = ["retain-unresolved"]
    elif fault == "tuple-domain":
        reasons[0]["allowed_decisions"] = ("retain-unresolved",)
    else:
        reasons[0]["disposition"] = {
            "claimed-accepted": "accepted",
            "claimed-rejected": "reject",
            "claimed-retained": "retain-unresolved",
            "bool-disposition": False,
        }[fault]
    with pytest.raises(triage_record.TriageRecordError) as caught:
        triage_record.restore(value, *subject, "decoder café")
    assert caught.value.code == "INVALID_PROJECT" and caught.value.exit_code == 3


@pytest.mark.parametrize(
    ("status", "angle", "ratio", "diagnostic", "wanted"),
    [
        (0, 0.0, 10.0, "", []),
        (0, -0.00001, 10.0, "", ["skew-nonzero"]),
        (0, 0.0, 0.0, "", ["assessment-unavailable"]),
        (1, 0.0, 10.0, "", ["assessment-unavailable"]),
        (0, None, 10.0, "", ["assessment-unavailable"]),
        (0, 1.0, None, "", ["assessment-unavailable"]),
        (0, 0.0, 0.0, "max found at sweep edge", ["assessment-unavailable", "skew-range-edge"]),
    ],
)
def test_checked_estimator_outcomes_keep_their_precise_reason_domains(
    subject: tuple[intake.Page, Estimate, samples.Inventory],
    status: int,
    angle: float | None,
    ratio: float | None,
    diagnostic: str,
    wanted: list[str],
) -> None:
    from bookscan import triage_record

    page, _, _ = subject
    page = replace(page, frame=replace(page.frame, extent_changed=False))
    estimate = parse_estimate(
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
        diagnostic,
        (10, 5),
    )
    native = samples.Inventory(placement.Analysis((), ()), (), (), "")
    expected = literal()[:1] + [
        {
            "id": name,
            "details": [diagnostic] if diagnostic else [],
            "allowed_decisions": ["reject", "retain-unresolved"]
            if name == "skew-nonzero"
            else ["retain-unresolved"],
            "disposition": "baseline-retained/unresolved",
        }
        for name in wanted
    ]
    result = triage_record.restore(expected, page, estimate, native, "")
    assert [r.to_dict() for r in result] == expected


def test_serializer_refuses_inconsistent_initial_reason_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from test_assessment import native, source

    from bookscan import triage_record

    saved = source(tmp_path, cropped=True)
    native(monkeypatch)
    result = assessment.assess_page(
        saved, saved.pages[0], Path("renderer"), Path("helper"), tmp_path
    )
    original = result.to_dict()
    wrong = replace(result, reasons=tuple(r for r in result.reasons if r.id != "extent-change"))
    with pytest.raises(triage_record.TriageRecordError):
        wrong.to_dict()
    assert result.to_dict() == original


def test_bad_predecessor_triage_is_rejected_even_when_current_is_good(
    owner: ownership.Writer,
    subject: tuple[intake.Page, Estimate, samples.Inventory],
) -> None:
    from bookscan import triage_record

    stores = project_header.Stores.provision(owner)
    bad = literal()
    bad.pop(3)  # Silently omitting fidelity is a semantic defect, with valid JSON/hash.
    previous = stores.checkpoints.commit(
        {"triage": bad}, expected=None, verify_state=lambda _: None
    ).checkpoint
    stores.checkpoints.commit({"triage": literal()}, expected=previous, verify_state=lambda _: None)
    path = owner.path
    owner.close()

    def verify(images: object, state: dict[str, object]) -> None:
        triage_record.restore(state["triage"], *subject, "decoder café")

    with pytest.raises(triage_record.TriageRecordError):
        with project_header.resume(
            path, verify_state=lambda stores, state: verify(stores.images, state)
        ):
            pytest.fail("lost predecessor limitation accepted")


def test_good_triage_history_resumes_without_native_launch_or_source_reads(
    owner: ownership.Writer,
    subject: tuple[intake.Page, Estimate, samples.Inventory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import triage_record

    stores = project_header.Stores.provision(owner)
    state: dict[str, object] = {"triage": literal()}

    def verify(images: object, state: dict[str, object]) -> None:
        triage_record.restore(state["triage"], *subject, "decoder café")

    previous = stores.checkpoints.commit(
        state, expected=None, verify_state=lambda state: verify(stores.images, state)
    ).checkpoint
    stores.checkpoints.commit(
        state, expected=previous, verify_state=lambda state: verify(stores.images, state)
    )
    path = owner.path
    owner.close()
    before = {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()}

    def deny(*args: object, **kwargs: object) -> None:
        raise PermissionError("native launch denied")

    monkeypatch.setattr(subprocess, "Popen", deny)
    with pytest.raises(PermissionError, match="native launch denied"):
        subprocess.Popen(["forbidden"])
    with project_header.resume(
        path, verify_state=lambda stores, state: verify(stores.images, state)
    ) as (_, current):
        assert current.revision == 2 and current.state == state
    assert {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()} == before


def test_pure_triage_reader_performs_no_file_io(
    subject: tuple[intake.Page, Estimate, samples.Inventory], monkeypatch: pytest.MonkeyPatch
) -> None:
    from bookscan import triage_record

    def deny(*args: object, **kwargs: object) -> None:
        raise PermissionError("file open denied")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", deny)
        with pytest.raises(PermissionError, match="file open denied"):
            Path("forbidden").open()
        result = triage_record.restore(literal(), *subject, "decoder café")
    assert len(result) == 6
