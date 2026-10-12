"""Restore saved placement, resolution and channel inventories without native I/O.

This checks retained consistency only. A matching complete placement roster does
not establish historical decoder behaviour or independent composition fidelity.
The checkpoint owner must bind the containing occurrence and all blob references.
"""

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from typing import cast

from bookscan import native_sample_record, placement, records, samples

FIELDS = {
    "resolution",
    "native_samples",
    "native_sample_concerns",
    "composition_unavailable",
    "composition_fidelity_verified",
}
PLACEMENT_FIELDS = {
    "path",
    "object_id",
    "kind",
    "samples",
    "bits_per_component",
    "color_space",
    "matrix",
    "ppi",
    "above_300_ppi",
}


@dataclass
class NativeInventoryRecordError(Exception):
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


def _json(value: object) -> None:
    try:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
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
    except (ValueError, TypeError, RecursionError, records.RecordError) as error:
        raise NativeInventoryRecordError("Invalid saved inventory JSON values.") from error


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(cast(dict[str, object], value)) != fields:
        raise NativeInventoryRecordError("Unsupported saved inventory fields.")
    return cast(dict[str, object], value)


def _array(value: object) -> list[object]:
    if type(value) is not list:
        raise NativeInventoryRecordError("Saved inventory values must be arrays.")
    return cast(list[object], value)


def _text(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise NativeInventoryRecordError("Saved inventory text must name its path or concern.")
    return value


def _strings(value: object) -> tuple[str, ...]:
    return tuple(_text(item) for item in _array(value))


def _pair(value: object, minimum: int) -> tuple[int, int]:
    items = _array(value)
    if len(items) != 2 or any(type(v) is not int or v < minimum for v in items):
        raise NativeInventoryRecordError("Invalid native object identity or sample dimensions.")
    return cast(tuple[int, int], tuple(items))


def _number(value: object) -> float:
    if type(value) not in (int, float):
        raise NativeInventoryRecordError("Native resolution must be finite positive numbers.")
    try:
        number = float(cast(int | float, value))
        if not math.isfinite(number) or number <= 0:
            raise ValueError("Nonpositive/nonfinite resolution.")
        return number
    except (ValueError, OverflowError) as error:
        raise NativeInventoryRecordError("Unrepresentable native resolution.") from error


def _placement(value: object) -> placement.Placement:
    data = _object(value, PLACEMENT_FIELDS)
    path = _strings(data["path"])
    kind, bits, color = data["kind"], data["bits_per_component"], data["color_space"]
    if (
        not path
        or type(kind) is not str
        or kind not in {"image", "inline", "stencil", "mask", "soft-mask"}
        or (bits is not None and (type(bits) is not int or bits not in (1, 2, 4, 8, 16)))
        or (color is not None and type(color) is not str)
    ):
        raise NativeInventoryRecordError("Invalid native placement identity/sample description.")
    object_id, size = _pair(data["object_id"], 0), _pair(data["samples"], 1)
    values = _array(data["matrix"])
    try:
        if len(values) != 6 or any(type(v) is not str for v in values):
            raise ValueError("Expected six rational strings.")
        matrix = cast(placement.Matrix, tuple(Fraction(cast(str, v)) for v in values))
        if [str(v) for v in matrix] != values:
            raise ValueError("Noncanonical rational.")
        a, b, c, d, _, _ = matrix
        if a * d == b * c:
            raise ValueError("Singular placement.")
        # Same physical definition as placement.Inventory.image: samples per
        # intrinsic axis divided by its length in the 300-dpi baseline frame.
        ppi = (
            size[0] * 300 / math.hypot(float(a), float(b)),
            size[1] * 300 / math.hypot(float(c), float(d)),
        )
        if any(not math.isfinite(v) or v <= 0 for v in ppi):
            raise ValueError("Unrepresentable ppi.")
    except (ValueError, ZeroDivisionError, OverflowError) as error:
        raise NativeInventoryRecordError("Invalid native physical placement.") from error
    saved_ppi = _array(data["ppi"])
    if len(saved_ppi) != 2 or tuple(_number(v) for v in saved_ppi) != ppi:
        raise NativeInventoryRecordError("Native resolution contradicts intrinsic grid/placement.")
    result = placement.Placement(
        path, object_id, kind, size, cast(int | None, bits), color, matrix, ppi
    )
    if type(data["above_300_ppi"]) is not bool or (
        data["above_300_ppi"] != result.above_baseline_resolution
    ):
        raise NativeInventoryRecordError("Native above-300 flag contradicts exact placement.")
    return result


def _resolution(value: object) -> placement.Analysis:
    data = _object(value, {"complete", "maximum_ppi", "placements", "concerns"})
    result = placement.Analysis(
        tuple(_placement(p) for p in _array(data["placements"])), _strings(data["concerns"])
    )
    if len({p.path for p in result.placements}) != len(result.placements):
        raise NativeInventoryRecordError("Native placement roster contains repeated paths.")
    if type(data["complete"]) is not bool or data["complete"] != result.complete:
        raise NativeInventoryRecordError("Native completeness contradicts recorded concerns.")
    maximum = data["maximum_ppi"]
    if (maximum is None) != (result.maximum_ppi is None) or (
        maximum is not None and _number(maximum) != result.maximum_ppi
    ):
        raise NativeInventoryRecordError("Native maximum resolution contradicts complete roster.")
    return result


def _inventory(
    data: dict[str, object], resolution: placement.Analysis, images: tuple[samples.Sample, ...]
) -> samples.Inventory:
    if len(images) != len(resolution.placements) or any(
        image.placement != placed
        for image, placed in zip(images, resolution.placements, strict=True)
    ):
        raise NativeInventoryRecordError("Native sample roster differs from ordered placements.")
    concerns = _strings(data["native_sample_concerns"])
    expected = tuple(
        "/".join(s.placement.path) + ": " + s.unavailable for s in images if s.unavailable
    )
    if concerns != expected or any(s.unavailable == "" for s in images):
        raise NativeInventoryRecordError("Native sample concerns contradict decoded availability.")
    if data["composition_fidelity_verified"] is not False:
        raise NativeInventoryRecordError(
            "Saved native inventory cannot claim composition fidelity."
        )
    return samples.Inventory(resolution, images, concerns, _text(data["composition_unavailable"]))


def restore(
    value: object,
    *,
    read_blob: Callable[[str], bytes],
    check_cancel: Callable[[], None] = lambda: None,
) -> samples.Inventory:
    """Read exact saved facts; caller binds blob reads to its verified ownership.

    No source reopening, decoder/CMM launch, lock reacquisition or write occurs.
    Even an unavailable sample retains its position in the complete ordered roster.
    """
    check_cancel()
    _json(value)
    data = _object(value, FIELDS)
    resolution = _resolution(data["resolution"])
    values = _array(data["native_samples"])
    if len(values) != len(resolution.placements):
        raise NativeInventoryRecordError("Native sample count differs from placement count.")

    owner_error: BaseException | None = None

    def checked() -> None:
        nonlocal owner_error
        try:
            check_cancel()
        except BaseException as error:
            # The nested blob reader classifies OSError/KeyError as unavailable
            # bytes. An owner-chosen cancellation of those types keeps its identity.
            owner_error = error
            raise

    def read(digest: str) -> bytes:
        checked()
        raw = read_blob(digest)
        checked()
        return raw

    images: list[samples.Sample] = []
    try:
        for item, placed in zip(values, resolution.placements, strict=True):
            checked()
            images.append(native_sample_record.restore(item, placed, read_blob=read))
    except native_sample_record.NativeSampleRecordError as error:
        if owner_error is not None:
            raise owner_error
        raise NativeInventoryRecordError(
            "Saved native sample could not verify: " + error.message
        ) from error
    result = _inventory(data, resolution, tuple(images))
    check_cancel()
    return result


def record(subject: samples.Inventory) -> dict[str, object]:
    """Serialize the existing five fields only after checking all roster claims."""
    value: dict[str, object] = {
        "resolution": {
            "complete": subject.resolution.complete,
            "maximum_ppi": subject.resolution.maximum_ppi,
            "placements": [
                native_sample_record.placement_record(p) for p in subject.resolution.placements
            ],
            "concerns": list(subject.resolution.concerns),
        },
        "native_samples": [native_sample_record.record(image) for image in subject.images],
        "native_sample_concerns": list(subject.concerns),
        "composition_unavailable": subject.composition_unavailable,
        "composition_fidelity_verified": False,
    }
    _json(value)
    _inventory(value, _resolution(value["resolution"]), subject.images)
    return value
