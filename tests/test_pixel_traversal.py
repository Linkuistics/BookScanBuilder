"""Literal cache sequences catch lost pixels, wrong reuse and arithmetic links."""

import importlib
import struct
from typing import Any

import pytest


def reader() -> Any:
    return importlib.import_module("pixel_traversal").verify_pixels


MATRIX = ["1", "0", "0", "0", "1", "0", "0", "0", "1"]


def row(index: int, codes: tuple[int, int, int], hit: bool) -> list[int]:
    # Literal zero/one inputs and outputs: no CMM or oracle supplies expectations.
    words = [c * 257 for c in codes]
    bits = [0x3F800000 if c else 0 for c in codes]
    stages = [0] * 18 if hit else bits * 6
    return [
        index,
        *codes,
        *words,
        *stages,
        *words,
        *codes,
        int(not hit),
        3 * int(not hit),
        int(hit),
    ]


def data() -> bytes:
    return b"".join(
        struct.pack("<34I", *r)
        for r in [
            row(0, (0, 0, 0), True),
            row(1, (255, 255, 255), False),
            row(2, (255, 255, 255), True),
            row(3, (255, 0, 0), False),
        ]
    )


def test_literal_seed_hit_miss_reuse_and_colour_change() -> None:
    result = reader()(data(), MATRIX, (0, 0, 0), (0, 0, 0), 4)
    assert (result["pixels"], result["misses"], result["hits"], result["stage_calls"]) == (
        4,
        2,
        2,
        6,
    )
    assert (
        result["rgb_sha256"] == "95a5d648d3e1c7f09319e337f164f9480af3ddc4be118bb8c8ccfd72c7fbf098"
    )


@pytest.mark.parametrize("column", [0, 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 32, 33])
def test_wrong_miss_association_stage_word_output_and_counters(column: int) -> None:
    wrong = bytearray(data())
    value = struct.unpack_from("<I", wrong, 136 + column * 4)[0]
    struct.pack_into("<I", wrong, 136 + column * 4, value ^ (0x3F800000 if 7 <= column < 25 else 2))
    with pytest.raises(ValueError):
        reader()(bytes(wrong), MATRIX, (0, 0, 0), (0, 0, 0), 4)


@pytest.mark.parametrize("column", [7, 10, 16, 22, 25, 28, 31, 32, 33])
def test_wrong_cache_hit_is_rejected(column: int) -> None:
    wrong = bytearray(data())
    value = struct.unpack_from("<I", wrong, 2 * 136 + column * 4)[0]
    struct.pack_into("<I", wrong, 2 * 136 + column * 4, value ^ 2)
    with pytest.raises(ValueError):
        reader()(bytes(wrong), MATRIX, (0, 0, 0), (0, 0, 0), 4)


@pytest.mark.parametrize("wrong", [b"", data()[:-1], data()[:-136], data() + data()[:136]])
def test_missing_extra_or_partial_pixel_is_rejected(wrong: bytes) -> None:
    with pytest.raises(ValueError):
        reader()(wrong, MATRIX, (0, 0, 0), (0, 0, 0), 4)


def test_each_call_resets_its_cache_seed() -> None:
    # A call ending in white does not seed the next call with white.
    white = struct.pack("<34I", *row(0, (255, 255, 255), False))
    assert reader()(white, MATRIX, (0, 0, 0), (0, 0, 0), 1)["misses"] == 1
    wrong = struct.pack("<34I", *row(0, (255, 255, 255), True))
    with pytest.raises(ValueError):
        reader()(wrong, MATRIX, (0, 0, 0), (0, 0, 0), 1)


def test_seed_output_is_independently_checked() -> None:
    with pytest.raises(ValueError):
        reader()(data(), MATRIX, (0, 0, 0), (2, 0, 0), 4)


@pytest.mark.parametrize("seed", [(1, 0, 0), (65536, 0, 0), (-1, 0, 0)])
def test_unverified_seed_input_domain_fails(seed: tuple[int, int, int]) -> None:
    with pytest.raises(ValueError):
        reader()(data(), MATRIX, seed, (0, 0, 0), 4)


def test_nonidentity_matrix_must_change_red_output() -> None:
    wrong = ["0", "1", "0", "1", "0", "0", "0", "0", "1"]
    with pytest.raises(ValueError):
        reader()(data(), wrong, (0, 0, 0), (0, 0, 0), 4)


def header() -> str:
    return (
        "pixels-v1 42 8 1 500 600 25 262169 4 1 0 0 4 4\n"
        "worker 109824 1000\n/library\n"
        "input 81344 1000\n/library\n"
        "output 88276 1000\n/library\n"
        "seed" + " 0" * 32 + "\ncomplete 4 restored 1\n"
    )


def bound(text: str) -> Any:
    module = importlib.import_module("pixel_traversal")
    from target_observation import Event

    event = Event(8, "transform", 700, 800, 500, 25, 262169, 1, 8448, 2190)
    return module.verify_header(text, event, 42, 1, 600, "/library", 1000)


def test_call_header_binds_identity_native_worker_formats_seed_and_complete_count() -> None:
    assert bound(header())["pixels"] == 4


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("pixels-v1 42", "pixels-v1 43"),
        ("42 8 1", "42 7 1"),
        ("8 1 500", "8 2 500"),
        ("500 600", "501 600"),
        ("500 600", "500 601"),
        ("25 262169", "26 262169"),
        ("4 1 0 0 4 4", "4 1 1 0 4 4"),
        ("4 1 0 0 4 4", "4 2 0 0 4 4"),
        ("109824", "109828"),
        ("81344", "81348"),
        ("88276", "88280"),
        ("/library", "/foreign"),
        ("seed 0", "seed 1"),
        ("complete 4 restored 1", "complete 4 restored 0"),
        ("complete 4", "complete 3"),
    ],
)
def test_wrong_native_call_binding_is_rejected(old: str, new: str) -> None:
    with pytest.raises(ValueError):
        bound(header().replace(old, new))


def test_complete_source_conversion_and_framebuffer_association() -> None:
    module = importlib.import_module("pixel_traversal")
    assert module.verify_image_binding(
        b"\0\0\0\xff\xff\xff",
        b"\0\0\0\xff\xff\xff",
        b"\0\0\0\xfe\xfe\xfe",
        "RGB",
        (2, 1),
        b"\0\0\0\xfe\xfe\xfe",
        expected_size=(2, 1),
    )


@pytest.mark.parametrize("failure", ["source", "input", "output", "mode", "size", "rgb"])
def test_wrong_or_erased_complete_framebuffer_binding(failure: str) -> None:
    module = importlib.import_module("pixel_traversal")
    source = b"\0\0\0\xff\xff\xff"
    output = b"\0\0\0\xfe\xfe\xfe"
    with pytest.raises(ValueError):
        module.verify_image_binding(
            b"\xff" * 6 if failure == "source" else source,
            source[::-1] if failure == "input" else source,
            output[:3] if failure == "output" else output,
            "RGBA" if failure == "mode" else "RGB",
            (1, 2) if failure == "size" else (2, 1),
            b"\xff" * 6 if failure == "rgb" else output,
            expected_size=(2, 1),
        )
