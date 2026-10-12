"""Catch cross-page/source/image association and corrupted predecessor core facts.

These use real source snapshots, PNG stores and checkpoint history. Native/render
payloads are deliberately outside the core verifier's claim; no full project is
accepted by these constructions.
"""

import copy
import hashlib
import json
import subprocess
import sys
from collections.abc import Iterator
from fractions import Fraction
from pathlib import Path
from typing import cast

import pikepdf
import pytest
from test_analysis_record import literal as analysis_literal

from bookscan import assets, intake, ownership, project_header, records, source_record


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    path = tmp_path / "Saved café project"
    path.mkdir()
    with ownership.Writer.acquire(path, ownership.provision(path)) as held:
        yield held


@pytest.fixture
def state(
    owner: ownership.Writer, tmp_path: Path
) -> tuple[project_header.Stores, dict[str, object]]:
    original = tmp_path / "Original.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        page.obj.MediaBox = pikepdf.Array([2.4, 1.2, 0, 0])
        page.obj.CropBox = pikepdf.Array([0.24, 0, 2.4, 1.2])
        page.obj.Rotate = 90
        page.obj.UserUnit = 2
        page.obj.BookScanBuilder = pikepdf.Dictionary(
            Version=1, Role="front", SourceSHA256="a" * 64, SourcePage=23
        )
        pdf.pages.append(page)  # pyright: ignore[reportUnknownMemberType]
        page = pdf.add_blank_page(page_size=(72, 36))
        page.obj.MediaBox = pikepdf.Array([0, 0, 2.4, 4.8])
        pdf.save(original, min_version="1.7")
    saved = intake.snapshot(original, owner.path / "source.pdf")
    source = source_record.record(owner, saved)
    stores = project_header.Stores.provision(owner)
    occurrences: list[dict[str, object]] = []
    baselines: list[dict[str, object]] = []
    for ordinal, page in enumerate(cast(list[dict[str, object]], source["pages"]), 1):
        rgb = bytes([ordinal, 127, 255]) * 200
        reference = stores.images.publish(rgb, (10, 20))
        baseline = analysis_literal()
        baseline["regions"] = [[0, 0, 10, 20]]
        occurrences.append(
            {
                **copy.deepcopy(page),
                "source_sha256": saved.sha256,
                "rgb_sha256": hashlib.sha256(rgb).hexdigest(),
                "analysis": baseline,
                "limitation": (
                    "Within-page geometry unverified; rigid rotation and book alignment do not "
                    "correct curvature or scanner-feed variation."
                ),
                "retention": "baseline-retained/unresolved",
                "estimate_applied": False,
                "inspected": False,
                "composition_fidelity_verified": False,
                # Other assessment fields remain unverified by this component.
                "render": {"command": [], "diagnostics": ""},
                "resolution": {},
                "native_samples": [],
                "native_sample_concerns": [],
                "composition_unavailable": "Unavailable native truth",
                "triage_reasons": [],
            }
        )
        baselines.append(reference.record())
    return stores, {"source": source, "occurrences": occurrences, "baselines": baselines}


def verify(images: assets.Assets, state: dict[str, object]) -> None:
    from bookscan import occurrence_record

    occurrence_record.verify_cores(
        images, state["source"], state["occurrences"], state["baselines"]
    )


def first(value: dict[str, object]) -> dict[str, object]:
    return cast(list[dict[str, object]], value["occurrences"])[0]


def test_complete_core_roster_binds_every_page_after_original_loss(
    owner: ownership.Writer, state: tuple[project_header.Stores, dict[str, object]]
) -> None:
    from bookscan import occurrence_record

    stores, value = state
    Path(cast(str, cast(dict[str, object], value["source"])["original_path"])).unlink()
    raw = json.dumps(value).encode()
    saved = records.decode(raw)
    cores = occurrence_record.verify_cores(
        stores.images, saved["source"], saved["occurrences"], saved["baselines"]
    )
    assert [c.id for c in cores] == ["occ-000001", "occ-000002", "occ-000003"]
    assert [c.page.source_page for c in cores] == [1, 2, 3]
    assert cores[0].page.frame.pixels == (10, 20)
    assert cores[0].page.frame.points == (Fraction(12, 5), Fraction(24, 5))
    assert cores[0].page.geometry.rotate == 90 and cores[0].page.geometry.user_unit == 2
    assert cores[0].page.hint == intake.Hint("front", "a" * 64, 23)
    assert cores[2].page.hint is None
    assert cores[0].analysis.angle_degrees == -0.00001
    assert cores[0].analysis.region == (0, 0, 10, 20)
    assert [stores.images.read(c.baseline) for c in cores] == [
        bytes([i, 127, 255]) * 200 for i in (1, 2, 3)
    ]
    assert json.dumps(value).encode() == raw
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)
    # Return only the fields actually verified, with no untouched native payload.
    assert not hasattr(cores[0], "native_samples") and not hasattr(cores[0], "render")


@pytest.mark.parametrize(
    "change",
    [
        "missing-page",
        "extra-page",
        "swapped-pages",
        "duplicate-page",
        "swapped-rgb",
        "missing-rgb",
        "extra-rgb",
        "foreign-source",
        "foreign-rgb",
        "id",
        "ordinal",
        "bool-ordinal",
        "float-ordinal",
        "box",
        "rotate",
        "unit",
        "physical",
        "matrix",
        "extent",
        "hint",
        "bool-hint-page",
        "extra-geometry",
        "pixels-float",
        "rgb-size",
        "analysis-region",
        "analysis-availability",
        "analysis-settings",
        "retention",
        "inspected",
        "bool-inspected",
        "estimate-applied",
        "fidelity",
        "limitation",
        "missing-field",
        "unknown-field",
        "tuple-roster",
        "nonobject-page",
        "nonobject-rgb",
        "tuple-geometry",
        "nan-native",
        "surrogate-native",
        "bool-rgb-version",
    ],
)
def test_wrong_core_is_refused_without_writes(
    owner: ownership.Writer,
    state: tuple[project_header.Stores, dict[str, object]],
    change: str,
) -> None:
    from bookscan import occurrence_record

    stores, original = state
    value = copy.deepcopy(original)
    pages = cast(list[dict[str, object]], value["occurrences"])
    baselines = cast(list[dict[str, object]], value["baselines"])
    page = pages[0]
    geometry = cast(dict[str, object], page["geometry"])
    analysis = cast(dict[str, object], page["analysis"])
    if change == "missing-page":
        pages.pop()
    elif change == "extra-page":
        pages.append(copy.deepcopy(page))
    elif change == "swapped-pages":
        pages[0], pages[1] = pages[1], pages[0]
    elif change == "duplicate-page":
        pages[1] = copy.deepcopy(page)
    elif change == "swapped-rgb":
        baselines[0], baselines[1] = baselines[1], baselines[0]
    elif change == "missing-rgb":
        baselines.pop()
    elif change == "extra-rgb":
        baselines.append(copy.deepcopy(baselines[0]))
    elif change in {"foreign-source", "foreign-rgb"}:
        page["source_sha256" if change == "foreign-source" else "rgb_sha256"] = "0" * 64
    elif change == "id":
        page["id"] = "occ-000002"
    elif change in {"ordinal", "bool-ordinal", "float-ordinal"}:
        page["source_pdf_page"] = {"ordinal": 2, "bool-ordinal": True, "float-ordinal": 1.0}[change]
    elif change == "box":
        cast(list[list[str]], geometry["boxes"])[0][0] = "2.5"
    elif change in {"rotate", "unit", "physical", "matrix", "extent", "pixels-float"}:
        key, replacement = {
            "rotate": ("rotate", 0),
            "unit": ("user_unit", "1"),
            "physical": ("physical_points", ["1", "1"]),
            "matrix": ("matrix", ["1", "0", "0", "1", "0", "0"]),
            "extent": ("extent_changed", False),
            "pixels-float": ("pixels", [10.0, 20.0]),
        }[change]
        geometry[key] = replacement
    elif change == "extra-geometry":
        geometry["accepted"] = True
    elif change in {"hint", "bool-hint-page"}:
        hint = cast(dict[str, object], page["advisory_hint"])
        hint["source_page"] = 1 if change == "hint" else True
    elif change == "rgb-size":
        reference = stores.images.publish(bytes([1, 127, 255]) * 200, (20, 10))
        baselines[0] = reference.record()
    elif change == "analysis-region":
        analysis["regions"] = [[0, 0, 20, 10]]
    elif change == "analysis-availability":
        analysis["available"] = False
    elif change == "analysis-settings":
        cast(dict[str, object], analysis["settings"])["threshold"] = 161
    elif change in {"inspected", "bool-inspected", "estimate-applied", "fidelity"}:
        page[
            {
                "inspected": "inspected",
                "bool-inspected": "inspected",
                "estimate-applied": "estimate_applied",
                "fidelity": "composition_fidelity_verified",
            }[change]
        ] = 0 if change == "bool-inspected" else True
    elif change == "retention":
        page["retention"] = "accepted"
    elif change == "limitation":
        page["limitation"] = "Verified"
    elif change == "missing-field":
        del page["rgb_sha256"]
    elif change == "unknown-field":
        page["optional_acceptance"] = True
    elif change == "tuple-roster":
        value["occurrences"] = tuple(pages)
    elif change == "nonobject-page":
        pages[0] = cast(dict[str, object], [])
    elif change == "nonobject-rgb":
        baselines[0] = cast(dict[str, object], [])
    elif change == "tuple-geometry":
        geometry["pixels"] = (10, 20)
    elif change == "nan-native":
        page["native_samples"] = [float("nan")]
    elif change == "surrogate-native":
        page["composition_unavailable"] = "\ud800"
    elif change == "bool-rgb-version":
        baselines[0]["version"] = True
    else:
        raise AssertionError(change)
    before = {p.name: p.read_bytes() for p in (owner.path / "assets").iterdir()}
    with pytest.raises(occurrence_record.OccurrenceRecordError) as caught:
        verify(stores.images, value)
    assert caught.value.code == "INVALID_PROJECT" and caught.value.exit_code == 3
    assert {p.name: p.read_bytes() for p in (owner.path / "assets").iterdir()} == before
    owner.verify()


@pytest.mark.parametrize("damage", ["missing", "corrupt", "aliased"])
def test_named_rgb_asset_is_verified_not_only_its_record(
    owner: ownership.Writer, state: tuple[project_header.Stores, dict[str, object]], damage: str
) -> None:
    from bookscan import occurrence_record

    stores, value = state
    reference = cast(list[dict[str, object]], value["baselines"])[0]
    path = owner.path / "assets" / (cast(str, reference["id"]) + ".png")
    if damage == "missing":
        path.unlink()
    elif damage == "corrupt":
        path.write_bytes(b"not a PNG")
    else:
        other = owner.path / "alias.png"
        other.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(other)
    with pytest.raises(occurrence_record.OccurrenceRecordError):
        verify(stores.images, value)


def test_lost_ownership_prevents_core_reads(
    owner: ownership.Writer, state: tuple[project_header.Stores, dict[str, object]]
) -> None:
    stores, value = state
    owner.close()
    with pytest.raises(ownership.OwnershipError):
        verify(stores.images, value)


def test_cancellation_is_preserved_without_checkpoint(
    owner: ownership.Writer, state: tuple[project_header.Stores, dict[str, object]]
) -> None:
    from bookscan import occurrence_record

    stores, value = state
    selected = RuntimeError("selected cancellation")
    calls = 0

    def check() -> None:
        nonlocal calls
        calls += 1
        if calls == 20:
            raise selected

    with pytest.raises(RuntimeError) as caught:
        occurrence_record.verify_cores(
            stores.images,
            value["source"],
            value["occurrences"],
            value["baselines"],
            check_cancel=check,
        )
    assert caught.value is selected
    assert not (owner.path / "current.json").exists()
    owner.verify()


def test_restart_rejects_hash_valid_bad_predecessor_with_good_current(
    owner: ownership.Writer, state: tuple[project_header.Stores, dict[str, object]]
) -> None:
    from bookscan import occurrence_record

    stores, value = state
    bad = copy.deepcopy(value)
    first(bad)["source_sha256"] = "0" * 64
    # Deliberately inadequate predecessor writer, with internally hash-valid JSON.
    predecessor = stores.checkpoints.commit(
        bad, expected=None, verify_state=lambda _: None
    ).checkpoint
    stores.checkpoints.commit(value, expected=predecessor, verify_state=lambda _: None)
    path = owner.path
    owner.close()
    with pytest.raises(occurrence_record.OccurrenceRecordError):
        with project_header.resume(
            path, verify_state=lambda stores, state: verify(stores.images, state)
        ):
            pytest.fail("invalid predecessor accepted")


def test_good_history_resumes_cores_without_original_or_native_launch(
    owner: ownership.Writer,
    state: tuple[project_header.Stores, dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stores, value = state
    first = stores.checkpoints.commit(
        value, expected=None, verify_state=lambda state: verify(stores.images, state)
    ).checkpoint
    stores.checkpoints.commit(
        value, expected=first, verify_state=lambda state: verify(stores.images, state)
    )
    original = Path(cast(str, cast(dict[str, object], value["source"])["original_path"]))
    original.unlink()
    stat = Path.stat
    denied = 0

    def deny_original(self: Path, *, follow_symlinks: bool = True):
        nonlocal denied
        if self == original:
            denied += 1
            raise PermissionError("original read denied")
        return stat(self, follow_symlinks=follow_symlinks)

    def deny_launch(*args: object, **kwargs: object) -> None:
        raise PermissionError("native launch denied")

    monkeypatch.setattr(Path, "stat", deny_original)
    monkeypatch.setattr(subprocess, "Popen", deny_launch)
    with pytest.raises(PermissionError, match="original read denied"):
        original.stat()
    with pytest.raises(PermissionError, match="native launch denied"):
        subprocess.Popen([sys.executable, "-c", "pass"])
    path = owner.path
    owner.close()
    before = {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir() if p.is_file()}
    with project_header.resume(
        path, verify_state=lambda stores, state: verify(stores.images, state)
    ) as (_, current):
        assert current.revision == 2
    assert denied == 1
    assert {
        p.name: p.read_bytes() for p in (path / "checkpoints").iterdir() if p.is_file()
    } == before


def test_circular_direct_input_is_refused_without_hanging(tmp_path: Path) -> None:
    script = """
import sys
from pathlib import Path
from bookscan import assets, occurrence_record, ownership
path = Path(sys.argv[1])
path.mkdir()
with ownership.Writer.acquire(path, ownership.provision(path)) as owner:
    images = assets.Assets.provision(owner)
    pages = []
    pages.append(pages)
    try:
        occurrence_record.verify_cores(images, {}, pages, [])
    except occurrence_record.OccurrenceRecordError:
        print("circular JSON refused")
    else:
        raise AssertionError("circular input accepted")
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "circular")],
        capture_output=True,
        text=True,
        timeout=3,
    )
    assert result.returncode == 0 and result.stdout == "circular JSON refused\n"
