"""Exercise the combined reader against real saved source/store/history bytes.

Constructed RGB is a storage subject, not independent renderer/fidelity truth.
Saved placements must agree with the private PDF, and every other payload must
survive its owning reader. No estimator or renderer is used on restart.
"""

import copy
import hashlib
import json
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pikepdf
import pytest
from test_analysis_record import literal as analysis_literal
from test_fontconfig_record import literal as guarded_literal

from bookscan import (
    analysis_record,
    assessment,
    intake,
    ownership,
    project_header,
    records,
    render,
    resources,
    samples,
    source_record,
    triage_record,
)

RENDERER = Path("/historical/Poppler/pdftocairo")
PACKED = bytes([0, 64, 255, 128, 192, 32])


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    project = tmp_path / "Saved café project"
    project.mkdir()
    with ownership.Writer.acquire(project, ownership.provision(project)) as held:
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
        page.obj.Rotate, page.obj.UserUnit = 90, 2
        image = pikepdf.Stream(pdf, PACKED)
        image.Type, image.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
        image.Width, image.Height, image.BitsPerComponent = 2, 1, 8
        image.ColorSpace = pikepdf.Name.DeviceRGB
        page.obj.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=image))
        page.obj.Contents = pikepdf.Stream(pdf, b"q 2.4 0 0 1.2 0 0 cm /Im Do Q")
        pdf.pages.append(page)  # pyright: ignore[reportUnknownMemberType]
        blank = pdf.add_blank_page(page_size=(72, 36))
        blank.obj.MediaBox = pikepdf.Array([0, 0, 2.4, 1.2])
        pdf.save(original, min_version="1.7", compress_streams=False)
    saved = intake.snapshot(original, owner.path / "source.pdf")
    stores = project_header.Stores.provision(owner)
    values: list[dict[str, object]] = []
    baselines: list[dict[str, object]] = []
    for page in saved.pages:
        size = page.frame.pixels
        rgb = b"\x11\x22\x33" * (size[0] * size[1])
        baseline = stores.images.publish(rgb, size)
        native = samples.collect(saved, page)
        if page.source_page != 3:
            assert native.images[0].packed == PACKED
        raw_analysis = analysis_literal()
        raw_analysis["regions"] = [[0, 0, *size]]
        estimate = analysis_record.restore(raw_analysis, size)
        command = (
            str(RENDERER),
            "-f",
            str(page.source_page),
            "-l",
            str(page.source_page),
            "-singlefile",
            "-r",
            format(page.geometry.user_unit * 300, "f"),
            "-W",
            str(size[0]),
            "-H",
            str(size[1]),
            "-png",
            "-antialias",
            "default",
            str(saved.path),
            "/historical/tmp/bookscan-render-a/page",
        )
        raster = render.Raster(size, rgb, "decoder café", command)
        values.append(
            assessment.AssessedPage(
                saved.sha256,
                page,
                raster,
                native,
                estimate,
                triage_record.derive(page, estimate, native, raster.diagnostics),
            ).to_dict()
        )
        baselines.append(baseline.record())
    reference = stores.native.publish(PACKED)
    result: dict[str, object] = {
        "source": source_record.record(owner, saved),
        "occurrences": values,
        "baselines": baselines,
        "native_blobs": [reference.record()],
    }
    original.unlink()
    return stores, result


def verify(stores: project_header.Stores, state: dict[str, object]):
    from bookscan import assessed_record

    return assessed_record.restore(
        stores,
        state["source"],
        state["occurrences"],
        state["baselines"],
        state["native_blobs"],
        RENDERER,
    )


def first(state: dict[str, object]) -> dict[str, object]:
    return cast(list[dict[str, object]], state["occurrences"])[0]


def test_all_payloads_bind_without_original_or_native_launch(
    state: tuple[project_header.Stores, dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stores, value = state

    def denied(*args: object, **kwargs: object) -> None:
        raise PermissionError("native launch denied")

    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(samples, "collect", denied)
    with pytest.raises(PermissionError, match="native launch denied"):
        subprocess.Popen(["forbidden"])
    result = verify(stores, records.decode(json.dumps(value).encode()))
    assert [item.core.id for item in result] == ["occ-000001", "occ-000002", "occ-000003"]
    assert result[0].core.baseline == result[1].core.baseline
    assert result[0].core.page.frame.pixels == (10, 20)
    assert result[2].core.page.frame.pixels == (10, 5)
    assert result[0].native.images[0].packed == PACKED
    assert result[2].native.images == ()
    assert result[0].render.command[7] == "600"
    assert result[0].resources is None and result[0].scope is None
    assert [r.id for r in result[0].reasons] == [
        "orientation-unverified",
        "skew-nonzero",
        "import-fidelity",
        "extent-change",
        "decoder-warning",
    ]
    cast(dict[str, object], first(value)["render"])["diagnostics"] = "changed"
    assert result[0].render.diagnostics == "decoder café"


FAULTS = (
    "render-density",
    "render-source",
    "render-page",
    "reason-missing",
    "reason-domain",
    "reason-details",
    "reason-accepted",
    "native-missing",
    "native-maximum",
    "native-order",
    "native-source-path",
    "native-source-matrix",
    "native-blob-missing",
    "native-blob-extra",
    "native-blob-duplicate",
    "native-blob-length",
    "native-blob-tuple",
    "resources-unknown",
    "resources-scope",
    "resources-renderer",
    "claim-fidelity",
    "claim-inspection",
    "core-order",
    "core-analysis",
    "core-asset",
    "source-geometry",
)


def mutate(value: dict[str, object], fault: str, stores: project_header.Stores) -> None:
    page = first(value)
    command = cast(list[object], cast(dict[str, object], page["render"])["command"])
    reasons = cast(list[dict[str, object]], page["triage_reasons"])
    native = cast(list[dict[str, object]], page["native_samples"])
    resolution = cast(dict[str, object], page["resolution"])
    refs = cast(list[dict[str, object]], value["native_blobs"])
    if fault.startswith("render-"):
        command[{"render-density": 7, "render-source": 15, "render-page": 2}[fault]] = "wrong"
    elif fault == "reason-missing":
        reasons.pop()
    elif fault.startswith("reason-"):
        key, changed = {
            "reason-domain": ("allowed_decisions", ["reject"]),
            "reason-details": ("details", ["invented"]),
            "reason-accepted": ("disposition", "accepted"),
        }[fault]
        reasons[0][key] = changed
    elif fault == "native-missing":
        native.clear()
    elif fault == "native-maximum":
        resolution["maximum_ppi"] = 1.0
    elif fault == "native-order":
        cast(list[object], value["occurrences"])[0], cast(list[object], value["occurrences"])[2] = (
            cast(list[object], value["occurrences"])[2],
            page,
        )
    elif fault in ("native-source-path", "native-source-matrix"):
        for placed in [
            cast(dict[str, object], native[0]["placement"]),
            cast(list[dict[str, object]], resolution["placements"])[0],
        ]:
            if fault == "native-source-path":
                cast(list[str], placed["path"])[1] = "2"
            else:
                cast(list[str], placed["matrix"])[4] = "100"
    elif fault == "native-blob-missing":
        refs.clear()
    elif fault == "native-blob-extra":
        refs.append(stores.native.publish(b"unreferenced").record())
        refs.sort(key=lambda item: str(item["sha256"]))
    elif fault == "native-blob-duplicate":
        refs.append(copy.deepcopy(refs[0]))
    elif fault == "native-blob-length":
        refs[0]["byte_size"] = 1
    elif fault == "native-blob-tuple":
        value["native_blobs"] = tuple(refs)
    elif fault.startswith("resources-"):
        binding = resources.ResourceBinding.capture([], environment={}).record()
        if fault == "resources-scope":
            binding["fontconfig_scope_guard"] = {"version": 99}
        elif fault == "resources-unknown":
            binding["unchecked"] = True
        cast(dict[str, object], page["render"])["resource_binding"] = binding
    elif fault == "claim-fidelity":
        page["composition_fidelity_verified"] = True
    elif fault == "claim-inspection":
        page["inspected"] = True
    elif fault == "core-order":
        cast(list[object], value["baselines"]).reverse()
    elif fault == "core-analysis":
        cast(dict[str, object], page["analysis"])["available"] = False
    elif fault == "core-asset":
        page["rgb_sha256"] = "0" * 64
    elif fault == "source-geometry":
        cast(dict[str, object], page["geometry"])["rotate"] = 0
    else:
        raise AssertionError(fault)


@pytest.mark.parametrize("fault", FAULTS)
def test_one_wrong_payload_cannot_hide_behind_valid_core_or_other_pages(
    state: tuple[project_header.Stores, dict[str, object]],
    fault: str,
) -> None:
    from bookscan import assessed_record

    stores, value = state
    before = list((stores.owner.path / "checkpoints").iterdir())
    mutate(value, fault, stores)
    with pytest.raises(assessed_record.AssessedRecordError) as caught:
        verify(stores, value)
    assert caught.value.code == "INVALID_PROJECT" and caught.value.exit_code == 3
    assert "Fresh import loses review facts" in caught.value.remediation
    assert list((stores.owner.path / "checkpoints").iterdir()) == before


@pytest.mark.parametrize("target", ["native", "rgb", "source"])
def test_saved_byte_corruption_is_refused(
    state: tuple[project_header.Stores, dict[str, object]],
    target: str,
) -> None:
    from bookscan import assessed_record

    stores, value = state
    if target == "native":
        path = stores.owner.path / "native-blobs" / (hashlib.sha256(PACKED).hexdigest() + ".bin")
    elif target == "source":
        path = stores.owner.path / "source.pdf"
    else:
        path = next((stores.owner.path / "assets").iterdir())
    assert path.is_file()
    path.write_bytes(b"corrupt")
    with pytest.raises(assessed_record.AssessedRecordError):
        verify(stores, value)


@pytest.mark.parametrize(
    "fault", ["valid", *(fault for fault in FAULTS if fault != "native-blob-tuple")]
)
def test_resume_checks_all_occurrence_payloads_in_every_predecessor(
    state: tuple[project_header.Stores, dict[str, object]],
    fault: str,
) -> None:
    from bookscan import assessed_record

    stores, good = state
    prior = copy.deepcopy(good)
    if fault != "valid":
        mutate(prior, fault, stores)
    previous = stores.checkpoints.commit(
        prior, expected=None, verify_state=lambda _: None
    ).checkpoint
    stores.checkpoints.commit(good, expected=previous, verify_state=lambda _: None)
    path = stores.owner.path
    stores.owner.close()
    before = {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()}

    def check(held: project_header.Stores, value: dict[str, object]) -> None:
        verify(held, value)

    if fault != "valid":
        with pytest.raises(assessed_record.AssessedRecordError):
            with project_header.resume(path, verify_state=check):
                pytest.fail("Corrupt predecessor payload accepted")
    else:
        with project_header.resume(path, verify_state=check) as (restored, current):
            assert current.revision == 2
            assert verify(restored, current.state)[0].native.images[0].packed == PACKED
    assert {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()} == before


@pytest.mark.parametrize(
    "selected", [OSError("selected"), KeyError("selected"), KeyboardInterrupt()]
)
def test_cancel_keeps_selected_identity(
    state: tuple[project_header.Stores, dict[str, object]],
    selected: BaseException,
) -> None:
    from bookscan import assessed_record

    stores, value = state

    def cancel() -> None:
        raise selected

    with pytest.raises(type(selected)) as caught:
        assessed_record.restore(
            stores,
            value["source"],
            value["occurrences"],
            value["baselines"],
            value["native_blobs"],
            RENDERER,
            check_cancel=cancel,
        )
    assert caught.value is selected


@pytest.mark.parametrize("guarded", [False, True])
def test_historical_named_resources_and_guard_are_checked_without_host_reopening(
    state: tuple[project_header.Stores, dict[str, object]],
    guarded: bool,
) -> None:
    stores, value = state
    binding = (
        guarded_literal()
        if guarded
        else resources.ResourceBinding.capture([], environment={}).record()
    )
    files = cast(list[dict[str, object]], binding["files"])
    files.append(
        {
            "path": str(RENDERER),
            "resolved": str(RENDERER),
            "device": 1,
            "inode": 2,
            "size": 8,
            "sha256": hashlib.sha256(b"historic").hexdigest(),
        }
    )
    files.sort(key=lambda item: str(item["path"]))
    cast(dict[str, object], first(value)["render"])["resource_binding"] = binding
    result = verify(stores, value)
    assert result[0].resources is not None
    assert result[0].scope is not None if guarded else result[0].scope is None
    assert result[1].resources is None
    assert not RENDERER.exists()


@pytest.mark.parametrize("target", ["native", "assets", "source"])
def test_replacement_during_verification_is_rejected(
    state: tuple[project_header.Stores, dict[str, object]],
    target: str,
) -> None:
    from bookscan import assessed_record

    stores, value = state
    path = (
        stores.owner.path
        / {"native": "native-blobs", "assets": "assets", "source": "source.pdf"}[target]
    )
    done = False

    def replace() -> None:
        nonlocal done
        if not done:
            done = True
            path.rename(path.with_name(path.name + "-old"))
            if target == "source":
                path.write_bytes(path.with_name(path.name + "-old").read_bytes())
            else:
                path.mkdir()

    with pytest.raises(assessed_record.AssessedRecordError):
        assessed_record.restore(
            stores,
            value["source"],
            value["occurrences"],
            value["baselines"],
            value["native_blobs"],
            RENDERER,
            check_cancel=replace,
        )


@pytest.mark.parametrize(
    "selected", [OSError("selected"), KeyError("selected"), RuntimeError("selected")]
)
def test_cancellation_inside_native_read_is_not_reclassified_as_corruption(
    state: tuple[project_header.Stores, dict[str, object]],
    selected: BaseException,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import assessed_record, native_blobs

    stores, value = state
    armed = False
    original_read = native_blobs.Blobs.read

    def read(
        self: native_blobs.Blobs,
        ref: native_blobs.Blob,
        *,
        check_cancel: Callable[[], None] = lambda: None,
    ) -> bytes:
        nonlocal armed
        armed = True
        return original_read(self, ref, check_cancel=check_cancel)

    def cancel() -> None:
        if armed:
            raise selected

    monkeypatch.setattr(native_blobs.Blobs, "read", read)
    with pytest.raises(type(selected)) as caught:
        assessed_record.restore(
            stores,
            value["source"],
            value["occurrences"],
            value["baselines"],
            value["native_blobs"],
            RENDERER,
            check_cancel=cancel,
        )
    assert armed and caught.value is selected
