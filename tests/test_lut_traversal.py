"""Independent input truth and rejecting controls for actual full-LUT traces."""

import importlib
import struct
from types import ModuleType

import pytest
from source_gamma import truth
from target_observation import Event

IDENTITY = ["1", "0", "0", "0", "1", "0", "0", "0", "1"]
EVENT = Event(7, "transform", 88, 99, 101, 262169, 262169, 1, 8448, 2190)
OFFSETS = {"__LUTeval16": 100, "_EvaluateCurves": 200, "_EvaluateMatrix": 300}


def module() -> ModuleType:
    return importlib.import_module("lut_traversal")


def binding() -> str:
    return (
        "traversal-v1 42 7 101 555 256\n"
        "lut16 65636 65536 555\n/native/lcms.dylib\n"
        "stage 0 111 1668707188 3 3 65736 65536 333 222\n/native/lcms.dylib\n"
        "stage 1 222 1835103334 3 3 65836 65536 444 444\n/native/lcms.dylib\n"
        "stage 2 444 1668707188 3 3 65736 65536 666 0\n/native/lcms.dylib\n"
        "calls 256 768 restored 1 abi 16 24\n"
    )


def bind(text: str) -> dict[str, object]:
    return module().verify_binding(text, EVENT, 42, 555, OFFSETS, "/native/lcms.dylib")


def rows() -> list[list[int]]:
    grid = truth(255)
    result: list[list[int]] = []
    for index in range(256):
        codes = [index, 255 - index, index * 73 % 256]
        x = [grid[c][0] for c in codes]
        y = [grid[c][1] for c in codes]
        # Literal zero output words/bytes: no target arithmetic claim is supplied.
        result.append(
            [
                index,
                *codes,
                *[c * 257 for c in codes],
                *x,
                *y,
                *y,
                *y,
                *y,
                *y,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ]
        )
    return result


def encode(values: list[list[int]]) -> bytes:
    return b"".join(struct.pack("<34I", *row) for row in values)


def test_full_chain_links_independent_source_matrix_truth_and_restoration() -> None:
    assert bind(binding())["pipeline_probe_traversal_observed"] is True
    result = module().verify_vectors(encode(rows()), IDENTITY)
    assert result["vectors"] == 256
    assert result["arithmetic"]["source_stage_correctly_rounded"] is True
    assert result["complete_cmm_precision_verified"] is False
    assert result["renderer_pixel_traversal_observed"] is False


@pytest.mark.parametrize("column", [0, 1, 4, 7, 10, 13, 16, 19, 28, 31])
def test_altered_input_order_stage_link_arithmetic_or_output_is_rejected(column: int) -> None:
    data = rows()
    data[17][column] ^= 0x3F800000 if column == 16 else 1
    with pytest.raises(ValueError):
        module().verify_vectors(encode(data), IDENTITY)


@pytest.mark.parametrize("change", ["missing", "extra", "nonfinite", "word", "byte"])
def test_incomplete_or_out_of_domain_vectors_are_rejected(change: str) -> None:
    data = rows()
    if change == "missing":
        data.pop()
    elif change == "extra":
        data.append(data[0])
    else:
        data[0][{"nonfinite": 22, "word": 25, "byte": 28}[change]] = {
            "nonfinite": 0x7FC00000,
            "word": 65536,
            "byte": 256,
        }[change]
    with pytest.raises(ValueError):
        module().verify_vectors(encode(data), IDENTITY)


@pytest.mark.parametrize(
    "old,new",
    [
        ("42 7", "43 7"),
        ("7 101", "7 102"),
        ("101 555", "101 556"),
        ("555 256", "555 255"),
        ("65636", "65637"),
        ("lut16", "lutFloat"),
        ("65536 555", "65536 556"),
        ("stage 0", "stage 1"),
        ("333 222", "333 444"),
        ("666 0", "666 111"),
        ("stage 2 444", "stage 2 111"),
        ("65736", "65737"),
        ("65836", "65837"),
        ("/native/lcms.dylib", "/foreign/lcms.dylib"),
        ("256 768", "255 768"),
        ("restored 1", "restored 0"),
        ("abi 16 24", "abi 24 32"),
    ],
)
def test_foreign_binding_bypassed_stage_and_failed_restoration_fail(old: str, new: str) -> None:
    with pytest.raises(ValueError):
        bind(binding().replace(old, new))


def test_missing_native_pipeline_instructions_are_rejected() -> None:
    with pytest.raises(ValueError, match="ABI"):
        module().verify_abi("_cmsPipelineEval16:\n0000 ldp x2, x3, [x2, #0x18]\n")


@pytest.mark.parametrize("column,expected", [(10, "source-stage"), (16, "matrix-stage")])
def test_linked_but_arithmetically_wrong_stages_fail_the_independent_oracle(
    column: int, expected: str
) -> None:
    data = rows()
    data[17][column] ^= 0x3F800000 if column == 16 else 1
    data[17][column + 3] = data[17][column]
    with pytest.raises(ValueError, match=expected):
        module().verify_vectors(encode(data), IDENTITY)


DISPATCHER = "module-v1 42 7 evaluator 65936 65536\n/native/lcms.dylib\n"


def test_actual_cached_dispatcher_is_bound_instead_of_inferred_from_flags() -> None:
    assert (
        module().verify_transform_dispatch(
            DISPATCHER, EVENT, 42, {"_CachedXFORM": 400}, "/native/lcms.dylib"
        )
        == 400
    )


@pytest.mark.parametrize(
    "old,new",
    [
        ("42 7", "43 7"),
        ("65936", "65940"),
        ("65536", "65540"),
        ("/native/lcms.dylib", "/foreign/lcms.dylib"),
    ],
)
def test_wrong_cached_dispatcher_binding_is_rejected(old: str, new: str) -> None:
    with pytest.raises(ValueError, match="dispatcher"):
        module().verify_transform_dispatch(
            DISPATCHER.replace(old, new), EVENT, 42, {"_CachedXFORM": 400}, "/native/lcms.dylib"
        )
