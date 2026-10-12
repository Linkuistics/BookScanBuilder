"""Verify actual formatter bytes against exhaustive independent integer truth.

The opaque transform and function addresses authenticate binding only. They say
nothing about the intermediate CMM evaluator, profile fidelity or calibration.
"""

import hashlib
import re

from target_observation import Event


def verify_formatter(data: bytes, event: Event, pid: int) -> dict[str, object]:
    parts = data.split(b"\n", 2)
    if len(parts) != 3:
        raise ValueError("Missing formatter binding")
    header, functions, payload = parts
    expected = (
        f"formatter-v1 {pid} {event.sequence} {event.transform_handle} "
        f"{event.input_format} {event.output_format} {event.flags} {event.cmm_version}"
    ).encode()
    if (
        pid <= 0
        or event.kind != "transform"
        or event.input_format not in (262169, 25)
        or (event.output_format, event.flags, event.cmm_version) != (262169, 8448, 2190)
        or header != expected
    ):
        raise ValueError("Foreign/unsupported formatter binding")
    match = re.fullmatch(rb"functions ([1-9][0-9]*) ([1-9][0-9]*)", functions)
    if match is None:
        raise ValueError("Missing actual formatter functions")
    if len(payload) != 256 * 6 + 65536 * 3:
        raise ValueError("Missing/extra formatter codes")
    incoming, outgoing = payload[: 256 * 6], payload[256 * 6 :]
    for value in range(256):
        for channel, sample in enumerate((value, 255 - value, (value * 73) % 256)):
            offset = value * 6 + channel * 2
            if int.from_bytes(incoming[offset : offset + 2], "big") != sample * 257:
                raise ValueError("Input formatter channel/quantization truth mismatch")
    for value in range(65536):
        for channel, sample in enumerate((value, 65535 - value, (value * 73) % 65536)):
            if outgoing[value * 3 + channel] != (sample + 128) // 257:
                raise ValueError("Output formatter channel/rounding truth mismatch")
    return {
        "input_format": event.input_format,
        "output_format": event.output_format,
        "original_flags": event.flags,
        "input_codes_per_channel": 256,
        "output_codes_per_channel": 65536,
        "input_sha256": hashlib.sha256(incoming).hexdigest(),
        "output_sha256": hashlib.sha256(outgoing).hexdigest(),
        "input_mapping": "v*257, exact integer expansion",
        "output_mapping": "(v+128)//257, nearest integer",
        "max_output_error_in_8bit_units": "128/257",
        "max_output_error_normalized": "128/65535",
        "cmm_pipeline_verified": False,
    }
