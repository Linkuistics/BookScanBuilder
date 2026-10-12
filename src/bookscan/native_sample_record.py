"""Restore retained source channels and resolved colour facts without conversion.

The caller supplies a verified placement and reads only retained digest-addressed
blobs under its existing ownership. This component neither opens historical
sources nor proves composition fidelity. ICC bytes may be malformed: keeping them
is distinct from authorizing a transform, which remains profiles.display's job.
"""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from typing import cast

from bookscan import placement, records, samples


@dataclass
class NativeSampleRecordError(Exception):
    message: str
    code: str = "INVALID_PROJECT"
    exit_code: int = 3

    @property
    def remediation(self) -> str:
        return (
            "Use the compatible BookScanBuilder assessment-v1 reader with bookscan baseline "
            "status PROJECT; for damaged saved content use bookscan baseline create PDF "
            "--workdir NEW with an intact supported input. Fresh import loses review facts. "
            "Without intact input or a verifiable saved state no recovery is available."
        )

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def _json(value: object) -> bytes:
    try:
        raw = json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        records.decode(b'{"value":' + raw + b"}")
        pending = [value]
        while pending:
            item = pending.pop()
            if type(item) is dict:
                data = cast(dict[object, object], item)
                if any(type(key) is not str for key in data):
                    raise ValueError("Non-string saved key.")
                pending.extend(data.values())
            elif type(item) is list:
                pending.extend(cast(list[object], item))
            elif item is not None and type(item) not in (str, bool, int, float):
                raise ValueError("Non-JSON saved value.")
        return raw
    except (ValueError, TypeError, RecursionError, records.RecordError) as error:
        raise NativeSampleRecordError("Invalid saved native JSON values.") from error


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(cast(dict[str, object], value)) != fields:
        raise NativeSampleRecordError("Unsupported saved native fields.")
    return cast(dict[str, object], value)


def _fractions(value: object) -> tuple[Fraction, ...]:
    if type(value) is not list:
        raise NativeSampleRecordError("Native rational values must be arrays.")
    result: list[Fraction] = []
    for item in cast(list[object], value):
        try:
            if type(item) is not str:
                raise ValueError("Rational must be text.")
            number = Fraction(item)
            if str(number) != item:
                raise ValueError("Noncanonical rational.")
            result.append(number)
        except (ValueError, ZeroDivisionError) as error:
            raise NativeSampleRecordError("Invalid native rational value.") from error
    return tuple(result)


def _metadata(value: object) -> bytes | None:
    if value is None:
        return None
    if type(value) is not str:
        raise NativeSampleRecordError("Native PDF metadata must be JSON text.")
    try:
        raw = value.encode("utf-8")
        records.decode(b'{"value":' + raw + b"}")
        return raw
    except (UnicodeError, records.RecordError) as error:
        raise NativeSampleRecordError("Invalid native PDF metadata JSON.") from error


def _digest(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise NativeSampleRecordError("Invalid native blob digest.")
    return value


def _blob(value: object, read: Callable[[str], bytes]) -> bytes | None:
    digest = _digest(value)
    if digest is None:
        return None
    try:
        raw = read(digest)
    except (KeyError, OSError) as error:
        raise NativeSampleRecordError("Required native blob is unavailable: " + digest) from error
    if type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != digest:
        raise NativeSampleRecordError("Native blob bytes differ from their saved digest.")
    return raw


def placement_record(value: placement.Placement) -> dict[str, object]:
    return {
        "path": list(value.path),
        "object_id": list(value.object_id),
        "kind": value.kind,
        "samples": list(value.samples),
        "bits_per_component": value.bits_per_component,
        "color_space": value.color_space,
        "matrix": [str(v) for v in value.matrix],
        "ppi": list(value.ppi),
        "above_300_ppi": value.above_baseline_resolution,
    }


COLOR_FIELDS = {
    "kind",
    "components",
    "metadata",
    "profile_sha256",
    "palette_sha256",
    "high",
    "base",
    "ranges",
}
SAMPLE_FIELDS = {
    "placement",
    "packed_sha256",
    "raw_sha256",
    "color_kind",
    "color_metadata",
    "profile_sha256",
    "decode",
    "filters",
    "decode_parameters",
    "interpolate",
    "matte",
    "color_key",
    "unavailable",
    "composition_verified",
}
DEVICE_COMPONENTS = {"/DeviceGray": 1, "/DeviceRGB": 3, "/DeviceCMYK": 4, "stencil": 1}


def _color(value: object, read: Callable[[str], bytes], *, base: bool = False) -> samples.Color:
    data = _object(value, COLOR_FIELDS)
    kind, count = data["kind"], data["components"]
    metadata = _metadata(data["metadata"])
    if (
        type(kind) is not str
        or type(count) is not int
        or count not in (1, 3, 4)
        or metadata is None
    ):
        raise NativeSampleRecordError("Invalid resolved native colour identity.")
    ranges = _fractions(data["ranges"])
    if kind in DEVICE_COMPONENTS:
        if (
            count != DEVICE_COMPONENTS[kind]
            or ranges
            or data["base"] is not None
            or data["high"] is not None
            or data["profile_sha256"] is not None
            or data["palette_sha256"] is not None
            or json.loads(metadata) != (None if kind == "stencil" else kind)
        ):
            raise NativeSampleRecordError("Device/stencil colour contradicts its metadata.")
        return samples.Color(kind, count, metadata)
    if kind == "/ICCBased":
        profile = _blob(data["profile_sha256"], read)
        if (
            profile is None
            or data["base"] is not None
            or data["high"] is not None
            or data["palette_sha256"] is not None
            or len(ranges) != count * 2
            or any(ranges[i] >= ranges[i + 1] for i in range(0, len(ranges), 2))
        ):
            raise NativeSampleRecordError("Incomplete resolved ICC channels/profile/ranges.")
        return samples.Color(kind, count, metadata, profile=profile, ranges=ranges)
    if kind == "/Indexed" and not base:
        palette = _blob(data["palette_sha256"], read)
        high = data["high"]
        resolved = _color(data["base"], read, base=True)
        if (
            count != 1
            or ranges
            or data["profile_sha256"] is not None
            or type(high) is not int
            or not 0 <= high <= 255
            or palette is None
            or len(palette) != (high + 1) * resolved.components
            or resolved.kind == "stencil"
        ):
            raise NativeSampleRecordError("Incomplete resolved Indexed base/palette.")
        return samples.Color(kind, count, metadata, palette=palette, high=high, base=resolved)
    raise NativeSampleRecordError("Unsupported resolved native colour kind.")


def restore(
    value: object, placed: placement.Placement, *, read_blob: Callable[[str], bytes]
) -> samples.Sample:
    """Restore exact retained bytes; checked placement is supplied by its owner.

    Legacy device/stencil records carry complete colour descriptions. Legacy
    ICC/Indexed records lack resolved dependencies and are refused rather than
    reconstructed using a different decoder or a guessed profile/palette.
    """
    _json(value)
    if type(value) is not dict:
        raise NativeSampleRecordError("Native sample must be an object.")
    fields = set(cast(dict[str, object], value))
    if fields not in (SAMPLE_FIELDS, SAMPLE_FIELDS | {"resolved_color"}):
        raise NativeSampleRecordError("Unsupported saved native sample fields.")
    data = cast(dict[str, object], value)
    if _json(data["placement"]) != _json(placement_record(placed)):
        raise NativeSampleRecordError("Native sample placement differs from verified placement.")
    if data["composition_verified"] is not False:
        raise NativeSampleRecordError("Native samples cannot claim complete composition truth.")
    color: samples.Color | None = None
    if data["color_kind"] is None:
        if any(data[key] is not None for key in ("color_metadata", "profile_sha256")) or (
            "resolved_color" in data and data["resolved_color"] is not None
        ):
            raise NativeSampleRecordError("Absent native colour retains contradictory fields.")
    else:
        descriptor: object = data.get("resolved_color")
        if "resolved_color" not in data:
            kind = data["color_kind"]
            if type(kind) is not str or kind not in DEVICE_COMPONENTS:
                raise NativeSampleRecordError("Legacy sample lacks required resolved colour facts.")
            descriptor = {
                "kind": kind,
                "components": DEVICE_COMPONENTS[kind],
                "metadata": data["color_metadata"],
                "profile_sha256": None,
                "palette_sha256": None,
                "high": None,
                "base": None,
                "ranges": [],
            }
        color = _color(descriptor, read_blob)
        if (
            data["color_kind"] != color.kind
            or data["color_metadata"] != color.metadata.decode("utf-8")
            or data["profile_sha256"]
            != (hashlib.sha256(color.profile).hexdigest() if color.profile is not None else None)
        ):
            raise NativeSampleRecordError("Resolved colour differs from original sample fields.")
    raw_digest = _digest(data["raw_sha256"])
    decode = _fractions(data["decode"]) if data["decode"] is not None else None
    matte = _fractions(data["matte"]) if data["matte"] is not None else None
    if decode is not None and (color is None or len(decode) != color.components * 2):
        raise NativeSampleRecordError("Decode differs from native channel count.")
    interpolate = data["interpolate"]
    if interpolate is not None and type(interpolate) is not bool:
        raise NativeSampleRecordError("Invalid native interpolation fact.")
    filters = data["filters"]
    if type(filters) is not list or any(
        type(v) is not str or not v.startswith("/") for v in cast(list[object], filters)
    ):
        raise NativeSampleRecordError("Invalid native filter names.")
    parameters = _metadata(data["decode_parameters"])
    key = data["color_key"]
    if key is not None:
        bits = placed.bits_per_component
        if (
            type(key) is not list
            or color is None
            or bits not in (1, 2, 4, 8, 16)
            or len(cast(list[object], key)) != color.components * 2
            or any(type(v) is not int for v in cast(list[object], key))
        ):
            raise NativeSampleRecordError("Invalid native colour-key channel ranges.")
        values = cast(list[int], key)
        assert bits is not None
        if any(not 0 <= values[i] <= values[i + 1] < 1 << bits for i in range(0, len(values), 2)):
            raise NativeSampleRecordError("Native colour-key range exceeds its sample depth.")
    unavailable = data["unavailable"]
    if unavailable is not None and type(unavailable) is not str:
        raise NativeSampleRecordError("Invalid native unavailability reason.")
    packed = _blob(data["packed_sha256"], read_blob)
    if (packed is None) != (unavailable is not None):
        raise NativeSampleRecordError("Native sample availability contradicts retained bytes.")
    if packed is not None:
        width, height = placed.samples
        bits = placed.bits_per_component
        if (
            color is None
            or decode is None
            or raw_digest is None
            or interpolate is None
            or bits not in (1, 2, 4, 8, 16)
            or width <= 0
            or height <= 0
            or (color.kind == "stencil" and bits != 1)
        ):
            raise NativeSampleRecordError("Available native sample lacks required decoding facts.")
        assert bits is not None
        if len(packed) != ((width * color.components * bits + 7) // 8) * height:
            raise NativeSampleRecordError("Native packed bytes differ from full channel grid.")
    return samples.Sample(
        placed,
        color,
        packed,
        raw_digest,
        decode,
        interpolate,
        tuple(cast(list[str], filters)),
        parameters,
        matte,
        tuple(cast(list[int], key)) if key is not None else None,
        unavailable,
    )


def record(subject: samples.Sample) -> dict[str, object]:
    """Include every resolved colour dependency, leaving its bytes in separate blobs."""
    blobs: dict[str, bytes] = {}

    def retain(raw: bytes | None) -> str | None:
        if raw is None:
            return None
        digest = hashlib.sha256(raw).hexdigest()
        blobs[digest] = raw
        return digest

    def color(value: samples.Color | None) -> dict[str, object] | None:
        if value is None:
            return None
        return {
            "kind": value.kind,
            "components": value.components,
            "metadata": value.metadata.decode("utf-8"),
            "profile_sha256": retain(value.profile),
            "palette_sha256": retain(value.palette),
            "high": value.high,
            "base": color(value.base),
            "ranges": [str(v) for v in value.ranges],
        }

    value: dict[str, object] = {
        "placement": placement_record(subject.placement),
        "packed_sha256": retain(subject.packed),
        "raw_sha256": subject.raw_sha256,
        "color_kind": subject.color.kind if subject.color else None,
        "color_metadata": subject.color.metadata.decode("utf-8") if subject.color else None,
        "profile_sha256": retain(subject.color.profile) if subject.color else None,
        "resolved_color": color(subject.color),
        "decode": [str(v) for v in subject.decode] if subject.decode is not None else None,
        "filters": list(subject.filters),
        "decode_parameters": subject.decode_parameters.decode("utf-8")
        if subject.decode_parameters is not None
        else None,
        "interpolate": subject.interpolate,
        "matte": [str(v) for v in subject.matte] if subject.matte is not None else None,
        "color_key": list(subject.color_key) if subject.color_key is not None else None,
        "unavailable": subject.unavailable,
        "composition_verified": subject.composition_verified,
    }
    restore(value, subject.placement, read_blob=blobs.__getitem__)
    return value
