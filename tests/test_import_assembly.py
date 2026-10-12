"""Complete assembly uses real private assets and source, never a partial roster.

The saved RGB constructions exercise storage/lineage, not native rendering or
source fidelity. Native execution is separately checked by the acceptance runner.
"""

import copy
import hashlib
from collections.abc import Iterable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pikepdf
import pytest
from test_analysis_record import literal as analysis_literal
from test_baseline_state import evidence as evidence
from test_baseline_state import owner as owner
from test_dependency_record import RENDERER
from test_dependency_record import literal as dependency_literal

from bookscan import (
    analysis_record,
    assessment,
    baseline_state,
    intake,
    ownership,
    project_header,
    render,
    samples,
    source_record,
    triage_record,
)
from bookscan.assets import AssetError
from bookscan.intake import ImportFailure, Snapshot
from bookscan.project_header import Stores


@pytest.fixture
def inputs(
    evidence: tuple[Stores, dict[str, Any]],  # noqa: F811
) -> tuple[Stores, Snapshot, list[assessment.AssessedPage], dict[str, Any]]:
    stores, data = evidence
    original = baseline_state.restore(stores, baseline_state.initial(stores, data))
    saved = source_record.restore(stores.owner, data["source"])
    subjects = [
        assessment.AssessedPage(
            saved.sha256,
            item.core.page,
            render.Raster(
                item.core.baseline.size,
                stores.images.read(item.core.baseline),
                item.render.diagnostics,
                item.render.command,
                copy.deepcopy(data["resource_binding"]),
            ),
            item.native,
            item.core.analysis,
            item.reasons,
        )
        for item in original.occurrences
    ]
    # Construction is complete. Remove only its known assets so assembly must
    # actually publish them; source/header/store identities remain unchanged.
    for directory in (stores.owner.path / "assets", stores.owner.path / "native-blobs"):
        for path in directory.iterdir():
            path.unlink()
    # Deliberate fixture deletion invalidates its import-creation evidence.
    # These tests own assembly, not rollback of the destroyed construction.
    stores.images.publications = None
    stores.native.publications = None
    return stores, saved, subjects, data


def assemble(
    inputs: tuple[Stores, Snapshot, list[assessment.AssessedPage], dict[str, Any]],
    subjects: Iterable[assessment.AssessedPage] | None = None,
    **options: Any,
) -> dict[str, object]:
    from bookscan import import_assembly

    stores, saved, pages, data = inputs
    return import_assembly.assemble(
        stores,
        saved,
        pages if subjects is None else subjects,
        dependencies=data["dependencies"],
        resource_binding=data["resource_binding"],
        fontconfig=data["fontconfig"],
        **options,
    )


def test_publishes_complete_duplicate_blank_roster_without_committing(
    inputs: tuple[Stores, Snapshot, list[assessment.AssessedPage], dict[str, Any]],
) -> None:
    stores, saved, _, data = inputs
    state = assemble(inputs)
    assert state["occurrences"] == data["occurrences"]
    assert state["source"] == data["source"]
    assert [page["id"] for page in cast(list[dict[str, object]], state["occurrences"])] == [
        "occ-000001",
        "occ-000002",
        "occ-000003",
    ]
    verified = baseline_state.restore(stores, state)
    assert len(verified.occurrences) == 3
    assert verified.image_revisions[0] == verified.image_revisions[1]
    assert len(list((stores.owner.path / "assets").iterdir())) == 2
    assert len(list((stores.owner.path / "native-blobs").iterdir())) == 1
    assert saved.sha256 == hashlib.sha256(saved.path.read_bytes()).hexdigest()
    assert not (stores.owner.path / "checkpoints" / "current").exists()
    assert state["review"] == {
        "dispositions": [],
        "inspections": [],
        "acknowledgements": [],
        "retries": [],
    }


@pytest.mark.parametrize("fault", ["short", "extra", "reorder", "foreign", "geometry", "rgb"])
def test_partial_or_wrong_subject_cannot_return_usable_state(
    inputs: tuple[Stores, Snapshot, list[assessment.AssessedPage], dict[str, Any]],
    fault: str,
) -> None:
    _, _, subjects, _ = inputs
    pages = list(subjects)
    if fault == "short":
        pages.pop()
    elif fault == "extra":
        pages.append(subjects[-1])
    elif fault == "reorder":
        pages.reverse()
    elif fault == "foreign":
        pages[1] = replace(pages[1], source_sha256="0" * 64)
    elif fault == "geometry":
        pages[1] = replace(pages[1], page=subjects[2].page)
    else:
        pages[1] = replace(pages[1], raster=replace(pages[1].raster, rgb=b"bad"))
    with pytest.raises((baseline_state.BaselineStateError, AssetError)) as error:
        assemble(inputs, pages)
    assert getattr(error.value, "code") == "INVALID_PROJECT"
    assert not (inputs[0].owner.path / "checkpoints" / "current").exists()


def test_metadata_is_frozen_before_lazy_native_subjects_execute(
    inputs: tuple[Stores, Snapshot, list[assessment.AssessedPage], dict[str, Any]],
) -> None:
    _, _, subjects, data = inputs
    expected = copy.deepcopy(data["dependencies"])

    def changing() -> Iterator[assessment.AssessedPage]:
        data["dependencies"].clear()
        data["resource_binding"]["files"].clear()
        yield from subjects

    state = assemble(inputs, changing())
    assert state["dependencies"] == expected
    assert len(cast(dict[str, list[object]], state["resource_binding"])["files"]) == 3


def test_producer_tuple_resource_facts_use_the_durable_json_meaning(
    inputs: tuple[Stores, Snapshot, list[assessment.AssessedPage], dict[str, Any]],
) -> None:
    pages = [
        replace(
            item,
            raster=replace(
                item.raster,
                resource_binding={
                    **cast(dict[str, object], item.raster.resource_binding),
                    "working_directory_identity": (1, 2),
                },
            ),
        )
        for item in inputs[2]
    ]
    state = assemble(inputs, pages)
    assert len(baseline_state.restore(inputs[0], state).occurrences) == 3


def test_packed_palette_and_recursive_icc_profile_survive_real_asset_reads(
    owner: ownership.Writer,  # noqa: F811
    tmp_path: Path,
) -> None:
    from bookscan import import_assembly

    packed, palette, profile = b"\0\1", b"\0\x80\xff\xff\x40\0", b"profile construction bytes"
    original = tmp_path / "Indexed ICC.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        page.obj.MediaBox = pikepdf.Array([0, 0, 2.4, 1.2])
        icc = pikepdf.Stream(pdf, profile)
        icc.N = 3
        image = pikepdf.Stream(pdf, packed)
        image.Type, image.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
        image.Width, image.Height, image.BitsPerComponent = 2, 1, 8
        image.ColorSpace = pikepdf.Array(
            [
                pikepdf.Name.Indexed,
                pikepdf.Array([pikepdf.Name.ICCBased, icc]),
                1,
                pikepdf.String(palette),
            ]
        )
        page.obj.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=image))
        page.obj.Contents = pikepdf.Stream(pdf, b"q 2.4 0 0 1.2 0 0 cm /Im Do Q")
        pdf.save(original, min_version="1.7")
    stores = project_header.Stores.provision(owner)
    saved = intake.snapshot(original, owner.path / "source.pdf")
    original.unlink()
    selected = saved.pages[0]
    size = selected.frame.pixels
    native = samples.collect(saved, selected)
    metadata, binding = dependency_literal()
    raw_analysis = analysis_literal()
    raw_analysis["regions"] = [[0, 0, *size]]
    estimate = analysis_record.restore(raw_analysis, size)
    raster = render.Raster(
        size,
        b"\x11\x22\x33" * (size[0] * size[1]),
        "",
        (
            RENDERER,
            "-f",
            "1",
            "-l",
            "1",
            "-singlefile",
            "-r",
            "300",
            "-W",
            "10",
            "-H",
            "5",
            "-png",
            "-antialias",
            "default",
            str(saved.path),
            "/historical/tmp/bookscan-render-a/page",
        ),
        binding,
    )
    subject = assessment.AssessedPage(
        saved.sha256,
        selected,
        raster,
        native,
        estimate,
        triage_record.derive(selected, estimate, native, ""),
    )
    state = import_assembly.assemble(
        stores,
        saved,
        [subject],
        dependencies=metadata,
        resource_binding=binding,
    )
    references = cast(list[dict[str, object]], state["native_blobs"])
    assert [item["sha256"] for item in references] == sorted(
        hashlib.sha256(raw).hexdigest() for raw in (packed, palette, profile)
    )
    verified = baseline_state.restore(stores, state).occurrences[0].native.images[0]
    assert verified.packed == packed
    assert verified.color is not None and verified.color.palette == palette
    assert verified.color.base is not None and verified.color.base.profile == profile
    assert not (owner.path / "checkpoints" / "current").exists()


def test_caller_ownership_stays_held_and_competing_acquisition_is_busy(
    inputs: tuple[Stores, Snapshot, list[assessment.AssessedPage], dict[str, Any]],
) -> None:
    stores, _, subjects, _ = inputs

    def contested() -> Iterator[assessment.AssessedPage]:
        with pytest.raises(ownership.OwnershipError) as error:
            ownership.Writer.acquire(stores.owner.path, stores.owner.identity)
        assert (error.value.code, error.value.exit_code) == ("PROJECT_BUSY", 4)
        yield from subjects

    state = assemble(inputs, contested())
    stores.owner.verify()
    assert baseline_state.restore(stores, state).project_id.startswith("project-")


@pytest.mark.parametrize("when", ["before", "during", "after"])
def test_selected_cancellation_keeps_identity_and_never_commits(
    inputs: tuple[Stores, Snapshot, list[assessment.AssessedPage], dict[str, Any]],
    when: str,
) -> None:
    stores, _, subjects, _ = inputs
    selected = RuntimeError("selected owner cancellation")
    stopped = when == "before"

    def check() -> None:
        if stopped:
            raise selected

    def interrupted() -> Iterator[assessment.AssessedPage]:
        nonlocal stopped
        if when == "during":
            yield subjects[0]
            stopped = True
            yield subjects[1]
        else:
            yield from subjects
            stopped = True

    with pytest.raises(RuntimeError) as error:
        assemble(inputs, interrupted(), check_cancel=check)
    assert error.value is selected
    stores.owner.verify()
    assert not (stores.owner.path / "checkpoints" / "current").exists()


def test_replaced_saved_source_is_refused_before_subjects_are_consumed(
    inputs: tuple[Stores, Snapshot, list[assessment.AssessedPage], dict[str, Any]],
) -> None:
    _, saved, _, _ = inputs
    saved.path.write_bytes(b"corrupt source")

    def forbidden() -> Iterator[assessment.AssessedPage]:
        raise AssertionError("native input consumed before source verification")
        yield  # pragma: no cover

    with pytest.raises((source_record.SourceRecordError, ImportFailure)) as error:
        assemble(inputs, forbidden())
    assert getattr(error.value, "code") == "INVALID_PROJECT"


@pytest.mark.parametrize("asset", ["rgb", "native"])
def test_end_of_iteration_asset_corruption_cannot_return_verified_initial_state(
    inputs: tuple[Stores, Snapshot, list[assessment.AssessedPage], dict[str, Any]],
    asset: str,
) -> None:
    stores, _, subjects, _ = inputs

    def corrupted() -> Iterator[assessment.AssessedPage]:
        yield from subjects
        directory = stores.owner.path / ("assets" if asset == "rgb" else "native-blobs")
        next(directory.iterdir()).write_bytes(b"wrong complete bytes")

    with pytest.raises(baseline_state.BaselineStateError) as error:
        assemble(inputs, corrupted())
    assert error.value.code == "INVALID_PROJECT"
    assert not (stores.owner.path / "checkpoints" / "current").exists()
