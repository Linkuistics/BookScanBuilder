"""Tests for actual-transform formatter binding and exhaustive integer truth."""

import importlib

import pytest
from target_observation import Event


def event() -> Event:
    return Event(3, "transform", 11, 12, 13, 262169, 262169, 1, 8448, 2190)


def record() -> bytes:
    head = b"formatter-v1 42 3 13 262169 262169 8448 2190\nfunctions 101 102\n"
    incoming = bytearray()
    for v in range(256):
        for x in (v, 255 - v, (v * 73) % 256):
            incoming.extend((x * 257).to_bytes(2, "big"))
    outgoing = bytes(
        (x + 128) // 257 for v in range(65536) for x in (v, 65535 - v, (v * 73) % 65536)
    )
    return head + incoming + outgoing


def test_complete_actual_formatter_truth() -> None:
    module = importlib.import_module("transform_formatters")
    result = module.verify_formatter(record(), event(), 42)
    assert result["input_codes_per_channel"] == 256
    assert result["output_codes_per_channel"] == 65536
    assert result["max_output_error_in_8bit_units"] == "128/257"
    assert result["cmm_pipeline_verified"] is False


@pytest.mark.parametrize(
    "field,value", [(1, "43"), (2, "4"), (3, "14"), (4, "25"), (5, "25"), (6, "0"), (7, "2180")]
)
def test_rejects_foreign_transform_binding(field: int, value: str) -> None:
    module = importlib.import_module("transform_formatters")
    header, rest = record().split(b"\n", 1)
    fields = header.decode().split()
    fields[field] = value
    with pytest.raises(ValueError, match="binding"):
        module.verify_formatter(" ".join(fields).encode() + b"\n" + rest, event(), 42)


@pytest.mark.parametrize("index", [0, 1, 3, 256 * 6, 256 * 6 + 128 * 3, -1])
def test_rejects_channel_or_rounding_error(index: int) -> None:
    module = importlib.import_module("transform_formatters")
    head, functions, payload = record().split(b"\n", 2)
    wrong = bytearray(payload)
    wrong[index] ^= 1
    with pytest.raises(ValueError, match="truth"):
        module.verify_formatter(head + b"\n" + functions + b"\n" + wrong, event(), 42)


@pytest.mark.parametrize("kind", ["missing", "truncated", "extra", "null-input", "null-output"])
def test_rejects_incomplete_or_unavailable_formatter(kind: str) -> None:
    module = importlib.import_module("transform_formatters")
    data = record()
    wrong = {
        "missing": b"",
        "truncated": data[:-1],
        "extra": data + b"x",
        "null-input": data.replace(b"functions 101 102", b"functions 0 102"),
        "null-output": data.replace(b"functions 101 102", b"functions 101 0"),
    }[kind]
    with pytest.raises(ValueError):
        module.verify_formatter(wrong, event(), 42)
