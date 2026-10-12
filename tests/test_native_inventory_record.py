"""Saved resolution cannot omit placements, misstate ppi or detach retained samples.

Expectations use literal two-pixel construction truth. The reader checks saved
consistency, not historical decoder use or independent composition fidelity.
"""

import copy
import hashlib
import subprocess
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from typing import Any

import pytest
from test_native_sample_record import PACKED
from test_native_sample_record import literal as sample_literal

from bookscan import checkpoints, native_blobs, ownership, samples

MISSING = "Independent complete-page colour/vector/text/mask/clipping/blending oracle unavailable."


def literal() -> dict[str, Any]:
    image = sample_literal()
    return {
        "resolution": {
            "complete": True,
            "maximum_ppi": 300.0,
            "placements": [copy.deepcopy(image["placement"])],
            "concerns": [],
        },
        "native_samples": [image],
        "native_sample_concerns": [],
        "composition_unavailable": MISSING,
        "composition_fidelity_verified": False,
    }


def restore(value: object, **kwargs: Any) -> samples.Inventory:
    from bookscan import native_inventory_record

    return native_inventory_record.restore(
        value, read_blob={hashlib.sha256(PACKED).hexdigest(): PACKED}.__getitem__, **kwargs
    )


def test_literal_resolution_and_channels_restore_without_historical_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise PermissionError("historical I/O denied")

    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    with pytest.raises(PermissionError):
        Path("historical.pdf").open()
    with pytest.raises(PermissionError):
        subprocess.Popen(["forbidden"])
    value = literal()
    result = restore(value)
    placed = result.resolution.placements[0]
    assert placed.matrix == (F(2), F(0), F(0), F(-1), F(3), F(4))
    assert placed.ppi == (300.0, 300.0) and not placed.above_baseline_resolution
    assert result.resolution.complete and result.resolution.maximum_ppi == 300.0
    assert list(result.images[0].pixels()) == [(0, 64, 255), (128, 192, 32)]
    assert result.samples_available and result.composition_unavailable == MISSING
    assert not result.images[0].composition_verified
    value["resolution"]["placements"][0]["path"][0] = "changed"
    assert placed.path == ("page", "1", "2", "/Im")


def test_partial_resolution_and_unavailable_samples_keep_separate_concerns() -> None:
    value = literal()
    value["resolution"].update(complete=False, maximum_ppi=None, concerns=["page/3: shading"])
    value["native_samples"][0].update(packed_sha256=None, unavailable="unsupported decoder")
    value["native_sample_concerns"] = ["page/1/2//Im: unsupported decoder"]
    result = restore(value)
    assert not result.resolution.complete and result.resolution.maximum_ppi is None
    assert result.resolution.concerns == ("page/3: shading",)
    assert result.concerns == ("page/1/2//Im: unsupported decoder",)
    assert result.images[0].packed is None and not result.samples_available


def test_empty_image_roster_never_claims_a_numeric_resolution_or_fidelity() -> None:
    value = literal()
    value["resolution"].update(placements=[], maximum_ppi=None)
    value["native_samples"] = []
    result = restore(value)
    assert result.resolution.complete and result.resolution.maximum_ppi is None
    assert result.images == () and result.composition_unavailable == MISSING


def test_exact_above_300_survives_float_rounding_at_the_signed_boundary() -> None:
    value = literal()
    for placed in (value["resolution"]["placements"][0], value["native_samples"][0]["placement"]):
        placed["matrix"][0] = "200000000000000000000/100000000000000000001"
        placed["above_300_ppi"] = True
    result = restore(value)
    assert result.resolution.maximum_ppi == 300.0
    assert result.resolution.import_fidelity


FAULTS = (
    "extra",
    "missing",
    "tuple",
    "surrogate",
    "resolution-extra",
    "resolution-missing",
    "complete-int",
    "complete-lie",
    "maximum-lie",
    "maximum-bool",
    "maximum-nan",
    "partial-maximum",
    "empty-maximum",
    "concern-type",
    "empty-concern",
    "placements-tuple",
    "placement-extra",
    "placement-missing",
    "path-type",
    "path-empty",
    "path-empty-part",
    "object-short",
    "object-bool",
    "object-negative",
    "kind-unknown",
    "size-bool",
    "size-zero",
    "bpc-bool",
    "bpc-unsupported",
    "color-bool",
    "matrix-short",
    "matrix-number",
    "matrix-noncanonical",
    "matrix-zero-denominator",
    "matrix-singular",
    "matrix-overflow",
    "ppi-short",
    "ppi-bool",
    "ppi-zero",
    "ppi-lie",
    "above-int",
    "above-lie",
    "samples-missing",
    "samples-extra",
    "samples-swap",
    "placement-duplicate",
    "sample-placement",
    "lost-sample-concern",
    "invented-sample-concern",
    "sample-concern-tuple",
    "false-composition",
    "composition-int",
    "missing-oracle",
    "oracle-type",
    "bytes-corrupt",
)


@pytest.mark.parametrize("fault", FAULTS)
def test_hash_valid_but_semantically_inconsistent_inventory_is_refused(fault: str) -> None:
    from bookscan import native_inventory_record

    value = literal()
    resolution = value["resolution"]
    placed = resolution["placements"][0]
    if fault == "extra":
        value["accepted"] = True
    elif fault == "missing":
        del value["native_samples"]
    elif fault == "tuple":
        value["native_samples"] = tuple(value["native_samples"])
    elif fault == "surrogate":
        value["composition_unavailable"] = "\ud800"
    elif fault == "resolution-extra":
        resolution["accepted"] = True
    elif fault == "resolution-missing":
        del resolution["placements"]
    elif fault == "complete-int":
        resolution["complete"] = 1
    elif fault == "complete-lie":
        resolution["concerns"] = ["omitted image path"]
    elif fault == "maximum-lie":
        resolution["maximum_ppi"] = 299.0
    elif fault == "maximum-bool":
        resolution["maximum_ppi"] = True
    elif fault == "maximum-nan":
        resolution["maximum_ppi"] = float("nan")
    elif fault == "partial-maximum":
        resolution.update(complete=False, concerns=["unknown path"])
    elif fault == "empty-maximum":
        resolution["placements"] = []
        value["native_samples"] = []
    elif fault == "concern-type":
        resolution["concerns"] = [False]
    elif fault == "empty-concern":
        resolution.update(complete=False, maximum_ppi=None, concerns=[""])
    elif fault == "placements-tuple":
        resolution["placements"] = tuple(resolution["placements"])
    elif fault == "placement-extra":
        placed["accepted"] = True
    elif fault == "placement-missing":
        del placed["matrix"]
    elif fault == "path-type":
        placed["path"] = "page/1/2/Im"
    elif fault == "path-empty":
        placed["path"] = []
    elif fault == "path-empty-part":
        placed["path"] = ["page", ""]
    elif fault == "object-short":
        placed["object_id"] = [7]
    elif fault == "object-bool":
        placed["object_id"] = [True, 0]
    elif fault == "object-negative":
        placed["object_id"] = [-1, 0]
    elif fault == "kind-unknown":
        placed["kind"] = "vector"
    elif fault == "size-bool":
        placed["samples"][0] = True
    elif fault == "size-zero":
        placed["samples"][0] = 0
    elif fault == "bpc-bool":
        placed["bits_per_component"] = True
    elif fault == "bpc-unsupported":
        placed["bits_per_component"] = 3
    elif fault == "color-bool":
        placed["color_space"] = False
    elif fault == "matrix-short":
        placed["matrix"].pop()
    elif fault == "matrix-number":
        placed["matrix"][0] = 2
    elif fault == "matrix-noncanonical":
        placed["matrix"][0] = "4/2"
    elif fault == "matrix-zero-denominator":
        placed["matrix"][0] = "1/0"
    elif fault == "matrix-singular":
        placed["matrix"][3] = "0"
    elif fault == "matrix-overflow":
        placed["matrix"][0] = str(10**400)
    elif fault == "ppi-short":
        placed["ppi"].pop()
    elif fault == "ppi-bool":
        placed["ppi"][0] = True
    elif fault == "ppi-zero":
        placed["ppi"][0] = 0.0
    elif fault == "ppi-lie":
        placed["ppi"][0] = 600.0
    elif fault == "above-int":
        placed["above_300_ppi"] = 0
    elif fault == "above-lie":
        placed["above_300_ppi"] = True
    elif fault == "samples-missing":
        value["native_samples"] = []
    elif fault == "samples-extra":
        value["native_samples"] *= 2
    elif fault == "samples-swap":
        other = copy.deepcopy(value["native_samples"][0])
        other["placement"]["path"][-1] = "/Other"
        resolution["placements"].append(copy.deepcopy(other["placement"]))
        value["native_samples"] = [other, value["native_samples"][0]]
    elif fault == "placement-duplicate":
        resolution["placements"] *= 2
        value["native_samples"] *= 2
    elif fault == "sample-placement":
        value["native_samples"][0]["placement"]["matrix"][4] = "99"
    elif fault == "lost-sample-concern":
        value["native_samples"][0].update(packed_sha256=None, unavailable="unsupported decoder")
    elif fault == "invented-sample-concern":
        value["native_sample_concerns"] = ["invented"]
    elif fault == "sample-concern-tuple":
        value["native_sample_concerns"] = ()
    elif fault == "false-composition":
        value["composition_fidelity_verified"] = True
    elif fault == "composition-int":
        value["composition_fidelity_verified"] = 0
    elif fault == "missing-oracle":
        value["composition_unavailable"] = ""
    elif fault == "oracle-type":
        value["composition_unavailable"] = False
    elif fault == "bytes-corrupt":
        value["native_samples"][0]["packed_sha256"] = "b" * 64
    with pytest.raises(native_inventory_record.NativeInventoryRecordError) as caught:
        restore(value)
    assert caught.value.code == "INVALID_PROJECT" and caught.value.exit_code == 3
    assert "Fresh import loses review facts" in caught.value.remediation


def test_reader_preserves_cancellation_identity_before_and_during_blob_reads() -> None:
    from bookscan import native_inventory_record

    sentinel = RuntimeError("owner cancelled")
    calls = 0

    def cancelled() -> None:
        nonlocal calls
        calls += 1
        raise sentinel

    with pytest.raises(RuntimeError) as caught:
        restore(literal(), check_cancel=cancelled)
    assert caught.value is sentinel and calls == 1

    def read(digest: str) -> bytes:
        raise sentinel

    with pytest.raises(RuntimeError) as caught:
        native_inventory_record.restore(literal(), read_blob=read)
    assert caught.value is sentinel


def test_writer_refuses_inventory_that_drops_a_sample_or_its_concern() -> None:
    from bookscan import native_inventory_record

    subject = restore(literal())
    assert native_inventory_record.record(subject) == literal() | {
        "native_samples": [
            dict(
                literal()["native_samples"][0],
                resolved_color={
                    "kind": "/DeviceRGB",
                    "components": 3,
                    "metadata": '"/DeviceRGB"',
                    "profile_sha256": None,
                    "palette_sha256": None,
                    "high": None,
                    "base": None,
                    "ranges": [],
                },
            )
        ]
    }
    with pytest.raises(native_inventory_record.NativeInventoryRecordError):
        native_inventory_record.record(replace(subject, images=()))
    unavailable = replace(subject.images[0], packed=None, unavailable="unsupported decoder")
    with pytest.raises(native_inventory_record.NativeInventoryRecordError):
        native_inventory_record.record(replace(subject, images=(unavailable,)))


@pytest.mark.parametrize(
    ("error_type", "at"), [(OSError, 3), (KeyError, 3), (OSError, 4), (KeyError, 4)]
)
def test_owner_cancellation_is_not_reclassified_as_a_missing_blob(
    error_type: type[Exception], at: int
) -> None:
    sentinel = error_type("owner cancelled")
    calls = 0

    def cancelled() -> None:
        nonlocal calls
        calls += 1
        if calls == at:
            raise sentinel

    with pytest.raises(error_type) as caught:
        restore(literal(), check_cancel=cancelled)
    assert caught.value is sentinel and calls == at


def test_bad_predecessor_inventory_cannot_hide_behind_valid_current(tmp_path: Path) -> None:
    from bookscan import native_inventory_record

    project = tmp_path / "saved project"
    project.mkdir()
    lock = ownership.provision(project)
    with ownership.Writer.acquire(project, lock) as held:
        store = native_blobs.Blobs.provision(held)
        reference = store.publish(PACKED)
        history = checkpoints.Checkpoints.provision(held)
        bad = literal()
        bad["resolution"]["maximum_ppi"] = 1.0
        previous = history.commit(
            {"inventory": bad}, expected=None, verify_state=lambda _: None
        ).checkpoint
        history.commit({"inventory": literal()}, expected=previous, verify_state=lambda _: None)
        identity, history_identity = store.identity, history.identity
    before = {p.name: p.read_bytes() for p in (project / "checkpoints").iterdir()}
    with ownership.Writer.acquire(project, lock) as held:
        store = native_blobs.Blobs(held, identity)
        history = checkpoints.Checkpoints(held, history_identity)

        def verify(state: dict[str, object]) -> None:
            native_inventory_record.restore(
                state["inventory"], read_blob=lambda _: store.read(reference)
            )

        with pytest.raises(native_inventory_record.NativeInventoryRecordError):
            history.load(verify_state=verify)
    assert {p.name: p.read_bytes() for p in (project / "checkpoints").iterdir()} == before


def test_assessment_writer_uses_inventory_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_assessment import native, source

    from bookscan import assessment, native_inventory_record

    saved = source(tmp_path)
    native(monkeypatch)
    subject = assessment.assess_page(
        saved, saved.pages[0], Path("renderer"), Path("helper"), tmp_path
    )
    record = subject.to_dict()
    restore({key: record[key] for key in literal()})
    wrong = replace(subject, native=replace(subject.native, concerns=("invented",)))
    with pytest.raises(native_inventory_record.NativeInventoryRecordError):
        wrong.to_dict()
