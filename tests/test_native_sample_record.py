"""Saved native channels cannot detach bytes, colour, Decode or placement.

Literal expectations are independent of the writer. Removing digest/shape/binding
checks must expose corrupt records. Reading never invokes a renderer or CMM.
"""

import copy
import hashlib
import subprocess
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction as F
from pathlib import Path
from typing import Any

import pytest

from bookscan import placement, samples

PACKED = bytes([0, 64, 255, 128, 192, 32])
PROFILE = b"Retained malformed ICC bytes, not conversion truth"
PALETTE = bytes([0, 64, 255, 128, 192, 32])


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def placed() -> placement.Placement:
    return placement.Placement(
        ("page", "1", "2", "/Im"),
        (7, 0),
        "image",
        (2, 1),
        8,
        "/DeviceRGB",
        (F(2), F(0), F(0), F(-1), F(3), F(4)),
        (300.0, 300.0),
    )


def literal() -> dict[str, Any]:
    return {
        "placement": {
            "path": ["page", "1", "2", "/Im"],
            "object_id": [7, 0],
            "kind": "image",
            "samples": [2, 1],
            "bits_per_component": 8,
            "color_space": "/DeviceRGB",
            "matrix": ["2", "0", "0", "-1", "3", "4"],
            "ppi": [300.0, 300.0],
            "above_300_ppi": False,
        },
        "packed_sha256": sha(PACKED),
        "raw_sha256": "a" * 64,
        "color_kind": "/DeviceRGB",
        "color_metadata": '"/DeviceRGB"',
        "profile_sha256": None,
        "decode": ["1", "0", "0", "1", "-1/2", "3/2"],
        "filters": ["/FlateDecode"],
        "decode_parameters": '{"/Predictor": 1}',
        "interpolate": False,
        "matte": ["1/2", "1/4", "3/4"],
        "color_key": [0, 0, 64, 64, 255, 255],
        "unavailable": None,
        "composition_verified": False,
    }


def color(kind: str = "/DeviceRGB") -> dict[str, Any]:
    return {
        "kind": kind,
        "components": 3,
        "metadata": '"/DeviceRGB"',
        "profile_sha256": None,
        "palette_sha256": None,
        "high": None,
        "base": None,
        "ranges": [],
    }


def indexed() -> tuple[dict[str, Any], placement.Placement, dict[str, bytes]]:
    value = literal()
    value["placement"].update(bits_per_component=2, color_space="/Indexed")
    value.update(
        packed_sha256=sha(b"\x10"),
        color_kind="/Indexed",
        color_metadata="null",
        decode=["0", "3"],
        matte=None,
        color_key=None,
    )
    base = color("/ICCBased")
    base.update(metadata="null", profile_sha256=sha(PROFILE), ranges=["-1/2", "3/2"] * 3)
    value["resolved_color"] = {
        "kind": "/Indexed",
        "components": 1,
        "metadata": "null",
        "profile_sha256": None,
        "palette_sha256": sha(PALETTE),
        "high": 1,
        "base": base,
        "ranges": [],
    }
    return (
        value,
        replace(placed(), bits_per_component=2, color_space="/Indexed"),
        {
            sha(b"\x10"): b"\x10",
            sha(PROFILE): PROFILE,
            sha(PALETTE): PALETTE,
        },
    )


def restore(value: dict[str, Any], blobs: dict[str, bytes] | None = None) -> samples.Sample:
    from bookscan import native_sample_record

    return native_sample_record.restore(
        value, placed(), read_blob=(blobs or {sha(PACKED): PACKED}).__getitem__
    )


def test_legacy_device_record_restores_exact_channels_without_io(monkeypatch: pytest.MonkeyPatch):
    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Historical files/native conversion must not be used")

    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    value = literal()
    result = restore(value)
    assert list(result.pixels()) == [(0, 64, 255), (128, 192, 32)]
    assert result.decode == (F(1), F(0), F(0), F(1), F(-1, 2), F(3, 2))
    assert result.matte == (F(1, 2), F(1, 4), F(3, 4))
    assert result.color_key == (0, 0, 64, 64, 255, 255)
    assert result.filters == ("/FlateDecode",) and result.decode_parameters == b'{"/Predictor": 1}'
    assert result.unavailable is None and not result.composition_verified
    value["decode"][0] = "0"
    assert result.decode is not None and result.decode[0] == F(1)
    with pytest.raises(FrozenInstanceError):
        result.raw_sha256 = "b" * 64  # type: ignore[misc]


def test_indexed_base_profile_palette_and_padding_survive_without_conversion():
    from bookscan import native_sample_record

    value, position, blobs = indexed()
    result = native_sample_record.restore(value, position, read_blob=blobs.__getitem__)
    assert list(result.pixels()) == [(0,), (1,)]
    assert result.packed == b"\x10" and result.color is not None
    assert result.color.palette == PALETTE and result.color.high == 1
    assert result.color.base is not None and result.color.base.profile == PROFILE
    assert result.color.base.ranges == (F(-1, 2), F(3, 2)) * 3
    assert not result.composition_verified


def test_writer_retains_resolved_base_bytes_instead_of_metadata_only():
    from bookscan import native_sample_record

    value, position, blobs = indexed()
    subject = samples.Sample(
        position,
        samples.Color(
            "/Indexed",
            1,
            b"null",
            palette=PALETTE,
            high=1,
            base=samples.Color(
                "/ICCBased", 3, b"null", profile=PROFILE, ranges=(F(-1, 2), F(3, 2)) * 3
            ),
        ),
        b"\x10",
        "a" * 64,
        (F(0), F(3)),
        False,
        ("/FlateDecode",),
        b'{"/Predictor": 1}',
        None,
        None,
        None,
    )
    assert native_sample_record.record(subject) == value
    result = native_sample_record.restore(value, position, read_blob=blobs.__getitem__)
    assert result == subject


FAULTS = (
    "extra",
    "missing",
    "placed",
    "bool-dimension",
    "float-matrix",
    "ppi",
    "above",
    "packed-digest",
    "packed-length",
    "raw-digest",
    "color-kind",
    "metadata",
    "profile-on-device",
    "decode-length",
    "decode-zero-denominator",
    "decode-noncanonical",
    "decode-number",
    "filter-type",
    "params-json",
    "params-duplicate",
    "interpolate",
    "matte-number",
    "key-length",
    "key-range",
    "key-bool",
    "unavailable-with-packed",
    "success-no-packed",
    "composition",
    "composition-int",
    "nan",
    "surrogate",
    "tuple",
)


@pytest.mark.parametrize("fault", FAULTS)
def test_contradictory_record_is_refused(fault: str):
    from bookscan import native_sample_record

    value, blobs = literal(), {sha(PACKED): PACKED}
    if fault == "extra":
        value["accepted"] = True
    elif fault == "missing":
        del value["decode"]
    elif fault == "placed":
        value["placement"]["path"][-1] = "/Other"
    elif fault == "bool-dimension":
        value["placement"]["samples"][1] = True
    elif fault == "float-matrix":
        value["placement"]["matrix"][0] = 2.0
    elif fault == "ppi":
        value["placement"]["ppi"][0] = 600.0
    elif fault == "above":
        value["placement"]["above_300_ppi"] = True
    elif fault == "packed-digest":
        blobs[sha(PACKED)] = PACKED[::-1]
    elif fault == "packed-length":
        value["packed_sha256"] = sha(PACKED[:-1])
        blobs[sha(PACKED[:-1])] = PACKED[:-1]
    elif fault == "raw-digest":
        value["raw_sha256"] = "A" * 64
    elif fault == "color-kind":
        value["color_kind"] = "/DeviceGray"
    elif fault == "metadata":
        value["color_metadata"] = '"/DeviceGray"'
    elif fault == "profile-on-device":
        value["profile_sha256"] = sha(PROFILE)
    elif fault == "decode-length":
        value["decode"].pop()
    elif fault == "decode-zero-denominator":
        value["decode"][0] = "1/0"
    elif fault == "decode-noncanonical":
        value["decode"][0] = "2/2"
    elif fault == "decode-number":
        value["decode"][0] = 1
    elif fault == "filter-type":
        value["filters"] = [False]
    elif fault == "params-json":
        value["decode_parameters"] = "{broken"
    elif fault == "params-duplicate":
        value["decode_parameters"] = '{"x":1,"x":2}'
    elif fault == "interpolate":
        value["interpolate"] = 0
    elif fault == "matte-number":
        value["matte"] = [0.5]
    elif fault == "key-length":
        value["color_key"].pop()
    elif fault == "key-range":
        value["color_key"][1] = 256
    elif fault == "key-bool":
        value["color_key"][0] = False
    elif fault == "unavailable-with-packed":
        value["unavailable"] = "missing codec"
    elif fault == "success-no-packed":
        value["packed_sha256"] = None
    elif fault == "composition":
        value["composition_verified"] = True
    elif fault == "composition-int":
        value["composition_verified"] = 0
    elif fault == "nan":
        value["placement"]["ppi"][0] = float("nan")
    elif fault == "surrogate":
        value["unavailable"] = "\ud800"
    elif fault == "tuple":
        value["decode"] = tuple(value["decode"])
    with pytest.raises(native_sample_record.NativeSampleRecordError) as caught:
        restore(value, blobs)
    assert caught.value.code == "INVALID_PROJECT" and caught.value.exit_code == 3


@pytest.mark.parametrize(
    "fault", ["base", "high", "palette", "profile", "ranges", "components", "binding", "legacy"]
)
def test_indexed_colour_cannot_drop_or_substitute_required_bytes(fault: str):
    from bookscan import native_sample_record

    value, position, blobs = indexed()
    descriptor = value["resolved_color"]
    if fault == "base":
        descriptor["base"] = copy.deepcopy(descriptor)
    elif fault == "high":
        descriptor["high"] = 2
    elif fault == "palette":
        blobs[sha(PALETTE)] = b"wrong"
    elif fault == "profile":
        blobs[sha(PROFILE)] = PROFILE + b"wrong"
    elif fault == "ranges":
        descriptor["base"]["ranges"] = ["1", "0"] * 3
    elif fault == "components":
        descriptor["components"] = True
    elif fault == "binding":
        descriptor["metadata"] = '"other metadata"'
    elif fault == "legacy":
        del value["resolved_color"]
    with pytest.raises(native_sample_record.NativeSampleRecordError):
        native_sample_record.restore(value, position, read_blob=blobs.__getitem__)


def test_unavailable_partial_record_preserves_reason_without_inventing_channels():
    value = literal()
    value.update(
        packed_sha256=None,
        unavailable="unsupported channels",
        color_kind=None,
        color_metadata=None,
        profile_sha256=None,
        decode=None,
        interpolate=None,
        matte=None,
        color_key=None,
    )
    result = restore(value)
    assert result.packed is None and result.color is None
    assert result.unavailable == "unsupported channels" and not result.composition_verified


def test_blob_reader_cancellation_is_not_reclassified():
    from bookscan import native_sample_record

    selected = RuntimeError("owner cancelled")

    def cancelled(digest: str) -> bytes:
        raise selected

    with pytest.raises(RuntimeError) as caught:
        native_sample_record.restore(literal(), placed(), read_blob=cancelled)
    assert caught.value is selected


def test_assessment_serialization_includes_resolved_profile_references():
    from decimal import Decimal

    from bookscan import assessment, native_sample_record, render
    from bookscan.intake import Frame, Geometry, Page
    from bookscan.skew import Estimate

    value, position, blobs = indexed()
    subject = native_sample_record.restore(value, position, read_blob=blobs.__getitem__)
    box = (Decimal(0), Decimal(0), Decimal("0.48"), Decimal("0.24"))
    geometry = Geometry((box,) * 5, 0, Decimal(1))
    page = Page(
        1,
        geometry,
        Frame(
            (2, 1),
            (Decimal("0.48"), Decimal("0.24")),
            (F(25, 6), F(0), F(0), F(-25, 6), F(0), F(1)),
            False,
        ),
        None,
    )
    inventory = samples.Inventory(placement.Analysis((position,), ()), (subject,), ())
    estimate = Estimate(1, 0.0, 0.0, (), (0, 0, 2, 1), "test", False, ("assessment-unavailable",))
    raster = render.Raster((2, 1), PACKED, "", ())
    result = assessment.AssessedPage(
        "b" * 64,
        page,
        raster,
        inventory,
        estimate,
        assessment.triage_record.derive(page, estimate, inventory, ""),
    )
    assert result.to_dict()["native_samples"] == [value]


@pytest.mark.parametrize(
    "bits,packed,want",
    [
        (1, b"\xa0\x60", [(1,), (0,), (1,), (0,), (1,), (1,)]),
        (2, b"\x18\xe4", [(0,), (1,), (2,), (3,), (2,), (1,)]),
        (4, b"\x12\x30\xab\xc0", [(1,), (2,), (3,), (10,), (11,), (12,)]),
        (
            16,
            b"\x00\x01\x00\x02\x00\x03\xff\xff\x80\x00\x00\x00",
            [(1,), (2,), (3,), (65535,), (32768,), (0,)],
        ),
    ],
)
def test_retained_rows_keep_msb_order_and_padding(bits: int, packed: bytes, want: list[tuple[int]]):
    from bookscan import native_sample_record

    position = replace(placed(), samples=(3, 2), bits_per_component=bits, color_space="/DeviceGray")
    subject = samples.Sample(
        position,
        samples.Color("/DeviceGray", 1, b'"/DeviceGray"'),
        packed,
        "a" * 64,
        (F(1), F(0)),
        False,
        (),
        None,
        None,
        None,
        None,
    )
    value = native_sample_record.record(subject)
    result = native_sample_record.restore(
        value, position, read_blob={sha(packed): packed}.__getitem__
    )
    assert list(result.pixels()) == want
    assert result.decode == (F(1), F(0)) and result.packed == packed


def test_stencil_retains_bits_without_inventing_paint_colour():
    from bookscan import native_sample_record

    position = replace(placed(), bits_per_component=1, kind="stencil", color_space=None)
    subject = samples.Sample(
        position,
        samples.Color("stencil", 1, b"null"),
        b"\x80",
        "a" * 64,
        (F(0), F(1)),
        False,
        (),
        None,
        None,
        None,
        None,
    )
    value = native_sample_record.record(subject)
    result = native_sample_record.restore(
        value, position, read_blob={sha(b"\x80"): b"\x80"}.__getitem__
    )
    assert list(result.pixels()) == [(1,), (0,)]
    assert result.color is not None and result.color.kind == "stencil"
    assert not result.composition_verified


def test_actual_source_decoding_restores_after_all_pdf_paths_disappear(tmp_path: Path):
    import pikepdf

    from bookscan import intake, native_sample_record

    source = tmp_path / "Colour samples.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        profile = pikepdf.Stream(pdf, PROFILE)
        profile.N = 3
        base = pikepdf.Array([pikepdf.Name.ICCBased, profile])
        image = pikepdf.Stream(pdf, b"\x10")
        image.Type, image.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
        image.Width, image.Height, image.BitsPerComponent = 2, 1, 2
        image.ColorSpace = pikepdf.Array([pikepdf.Name.Indexed, base, 1, pikepdf.String(PALETTE)])
        page.obj.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=image))
        page.obj.Contents = pikepdf.Stream(pdf, b"q 72 0 0 36 0 0 cm /Im Do Q")
        pdf.save(source)
    saved = intake.snapshot(source, tmp_path / "snapshot.pdf")
    subject = samples.collect(saved, saved.pages[0]).images[0]
    value = native_sample_record.record(subject)
    source.unlink()
    saved.path.unlink()
    result = native_sample_record.restore(
        value,
        subject.placement,
        read_blob={
            sha(PROFILE): PROFILE,
            sha(PALETTE): PALETTE,
            sha(b"\x10"): b"\x10",
        }.__getitem__,
    )
    assert result == subject
    assert result.color is not None and result.color.base is not None
    assert result.color.base.profile == PROFILE and result.color.palette == PALETTE


@pytest.mark.parametrize("bad_predecessor", [False, True])
def test_hash_valid_predecessor_binds_native_bytes_on_restart(
    tmp_path: Path, bad_predecessor: bool, monkeypatch: pytest.MonkeyPatch
):
    from bookscan import native_sample_record, ownership, project_header

    path = tmp_path / "Project"
    path.mkdir()
    good: dict[str, object] = {"sample": literal()}
    bad = copy.deepcopy(good)
    sample = bad["sample"]
    assert isinstance(sample, dict)
    sample["packed_sha256"] = "b" * 64
    with ownership.Writer.acquire(path, ownership.provision(path)) as owner:
        stores = project_header.Stores.provision(owner)
        previous = stores.checkpoints.commit(
            bad if bad_predecessor else good, expected=None, verify_state=lambda _: None
        ).checkpoint
        stores.checkpoints.commit(good, expected=previous, verify_state=lambda _: None)
    before = {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()}

    def verify(images: object, value: dict[str, object]) -> None:
        native_sample_record.restore(
            value["sample"], placed(), read_blob={sha(PACKED): PACKED}.__getitem__
        )

    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("Native launch is forbidden on saved reads")

    monkeypatch.setattr(subprocess, "Popen", denied)
    if bad_predecessor:
        with pytest.raises(native_sample_record.NativeSampleRecordError):
            with project_header.resume(
                path, verify_state=lambda stores, state: verify(stores.images, state)
            ):
                pytest.fail("Corrupt predecessor sample accepted")
    else:
        with project_header.resume(
            path, verify_state=lambda stores, state: verify(stores.images, state)
        ) as (_, current):
            assert current.revision == 2 and current.state == good
    assert {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()} == before
