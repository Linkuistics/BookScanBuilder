"""Saved references refuse malformed meaning before any asset-file access."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from bookscan import assets, ownership


def reference() -> assets.RGBAsset:
    rgb = hashlib.sha256(b"abc").hexdigest()
    identity = hashlib.sha256(f"BookScanBuilderRGB:1\n1 1\n{rgb}\n".encode()).hexdigest()
    return assets.RGBAsset(identity, (1, 1), rgb, "b" * 64, 69)


def record() -> dict[str, object]:
    ref = reference()
    return {
        "format": "BookScanBuilderRGBAsset",
        "version": 1,
        "id": ref.id,
        "size": [1, 1],
        "rgb_sha256": ref.rgb_sha256,
        "png_sha256": ref.png_sha256,
        "png_size": ref.png_size,
    }


def test_literal_record_and_json_roundtrip() -> None:
    expected = record()
    assert reference().record() == expected
    assert assets.RGBAsset.from_record(json.loads(json.dumps(expected))) == reference()


@pytest.mark.parametrize("field", list(record()))
def test_missing_required_field_refused(field: str) -> None:
    wrong = record()
    del wrong[field]
    with pytest.raises(assets.AssetError) as error:
        assets.RGBAsset.from_record(wrong)
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)


@pytest.mark.parametrize("wrong", [None, [], "record", 1, True])
def test_nonobject_record_refused(wrong: object) -> None:
    with pytest.raises(assets.AssetError, match="INVALID_PROJECT"):
        assets.RGBAsset.from_record(wrong)


@pytest.mark.parametrize(
    "field,value",
    [
        ("format", "BookScanBuilderProject"),
        ("version", 2),
        ("version", True),
        ("version", 1.0),
        ("version", "1"),
        ("size", None),
        ("size", [1]),
        ("size", [1, 1, 1]),
        ("size", [True, 1]),
        ("size", [1.0, 1]),
        ("size", [0, 1]),
        ("size", [-1, 1]),
        ("size", ["1", 1]),
        ("size", [2, 1]),
        ("size", {"width": 1, "height": 1}),
        ("png_size", True),
        ("png_size", 1.0),
        ("png_size", "69"),
        ("png_size", 0),
        ("png_size", -1),
        ("id", None),
        ("id", 7),
        ("id", "../escape"),
        ("rgb_sha256", None),
        ("rgb_sha256", []),
        ("rgb_sha256", "a" * 64),
        ("png_sha256", False),
        ("png_sha256", "B" * 64),
        ("png_sha256", "b" * 63),
        ("png_sha256", "b" * 64 + "\n"),
        ("semantic_extension", True),
    ],
)
def test_malformed_or_unknown_meaning_refused(field: str, value: object) -> None:
    wrong = record()
    wrong[field] = value
    with pytest.raises(assets.AssetError) as error:
        assets.RGBAsset.from_record(wrong)
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)


@pytest.mark.parametrize(
    "field,value", [("size", None), ("size", 1), ("id", None), ("png_sha256", [])]
)
def test_direct_forgery_is_domain_error(field: str, value: object) -> None:
    wrong = replace(reference(), **{field: value})
    with pytest.raises(assets.AssetError, match="INVALID_PROJECT"):
        wrong.verify()
    with pytest.raises(assets.AssetError, match="INVALID_PROJECT"):
        wrong.record()


def test_roundtrip_reads_saved_pixels_after_owner_reopen(tmp_path: Path) -> None:
    project = tmp_path / "Saved project"
    project.mkdir()
    identity = ownership.provision(project)
    with ownership.Writer.acquire(project, identity) as owner:
        store = assets.Assets.provision(owner)
        directory = store.identity
        saved = json.dumps(store.publish(b"abc", (1, 1)).record()).encode("utf-8")
    with ownership.Writer.acquire(project, identity) as owner:
        reopened = assets.Assets(owner, directory)
        assert reopened.read(assets.RGBAsset.from_json(saved)) == b"abc"


def test_record_output_does_not_share_mutable_size() -> None:
    ref = reference()
    output = ref.record()
    cast(list[int], output["size"])[0] = 2
    assert ref.size == (1, 1) and ref.record() == record()


def test_serialized_reference_reads_saved_pixels(tmp_path: Path) -> None:
    project = tmp_path / "Serialized project"
    project.mkdir()
    identity = ownership.provision(project)
    with ownership.Writer.acquire(project, identity) as owner:
        store = assets.Assets.provision(owner)
        directory = store.identity
        saved = json.dumps(store.publish(b"abc", (1, 1)).record()).encode("utf-8")
    with ownership.Writer.acquire(project, identity) as owner:
        store = assets.Assets(owner, directory)
        assert store.read(assets.RGBAsset.from_json(saved)) == b"abc"


@pytest.mark.parametrize("field", list(record()))
def test_serialized_duplicate_reference_refused(field: str) -> None:
    # Prepending an invalid value must not allow the later valid value to win.
    raw = ("{" + json.dumps(field) + ":null," + json.dumps(record())[1:]).encode()
    with pytest.raises(assets.AssetError) as error:
        assets.RGBAsset.from_json(raw)
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)


def test_serialized_unknown_semantic_field_still_refused() -> None:
    wrong = record() | {"ignored_semantics": True}
    with pytest.raises(assets.AssetError, match="INVALID_PROJECT"):
        assets.RGBAsset.from_json(json.dumps(wrong).encode())
