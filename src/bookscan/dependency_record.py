"""Read historical preflight metadata without reopening tools or rerunning controls.

Checked metadata binds saved build inputs, control meanings and static graphs to
named digests. It does not prove execution, actual resource use, retained helper
bytes, native decoding accuracy or page fidelity. The checkpoint owner must bind
these facts to occurrence/discovery records and verify all referenced assets.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from bookscan import analysis_record, dependencies, linked_record, native_setup, records, skew
from bookscan.occurrence_record import OccurrenceRecordError
from bookscan.resource_record import ResourceRecordError


class DependencyRecordError(OccurrenceRecordError):
    """Unsupported or contradictory saved historical dependency metadata."""


@dataclass(frozen=True)
class ToolIdentity:
    path: str
    sha256: str
    version: str


@dataclass(frozen=True)
class BuildInputs:
    source_sha256: str
    platform: str
    machine: str
    python_libraries: tuple[tuple[str, str], ...]
    compiler: ToolIdentity
    compiler_driver: tuple[str, str]
    pkg_config: ToolIdentity
    poppler: ToolIdentity
    leptonica: ToolIdentity
    headers: tuple[tuple[str, str], ...]
    pkg_flags: tuple[str, ...]
    flags: tuple[str, ...]


@dataclass(frozen=True)
class HelperFacts:
    inputs: BuildInputs
    build_identity: str
    binary_sha256: str
    controls: tuple[tuple[str, skew.Estimate], ...]
    protocol_controls: tuple[tuple[str, skew.Estimate], ...]


@dataclass(frozen=True)
class DependencyFacts:
    renderer: Path
    helper: HelperFacts
    linked: tuple[tuple[str, linked_record.LinkedDependencies], ...]
    pillow_features: tuple[tuple[str, str | None], ...]


def _json(value: object) -> None:
    try:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        records.decode(raw)
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
        raise DependencyRecordError("Invalid historical dependency JSON values.") from error


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(cast(dict[str, object], value)) != fields:
        raise DependencyRecordError("Unsupported saved dependency fields.")
    return cast(dict[str, object], value)


def _text(value: object) -> str:
    if type(value) is not str or not value or "\0" in value:
        raise DependencyRecordError("Invalid saved dependency text.")
    return value


def _path(value: object) -> str:
    text = _text(value)
    path = Path(text)
    if not path.is_absolute() or str(path) != text or ".." in path.parts:
        raise DependencyRecordError("Invalid canonical historical dependency path.")
    return text


def _digest(value: object) -> str:
    text = _text(value)
    if re.fullmatch("[0-9a-f]{64}", text) is None:
        raise DependencyRecordError("Invalid saved dependency digest.")
    return text


def _strings(value: object) -> tuple[str, ...]:
    if type(value) is not list:
        raise DependencyRecordError("Saved build flags require an array.")
    return tuple(_text(item) for item in cast(list[object], value))


def _tool(value: object, *, compiler: bool = False) -> ToolIdentity:
    fields = {"path", "sha256", "version"}
    if compiler:
        fields |= {"driver_path", "driver_sha256"}
    data = _object(value, fields)
    return ToolIdentity(_path(data["path"]), _digest(data["sha256"]), _text(data["version"]))


def _inputs(value: object) -> BuildInputs:
    data = _object(
        value,
        {
            "source_sha256",
            "platform",
            "machine",
            "python_libraries",
            "compiler",
            "pkg_config",
            "poppler",
            "leptonica",
            "headers",
            "pkg_flags",
            "flags",
            "settings",
        },
    )
    libraries = _object(data["python_libraries"], {"Pillow", "pikepdf"})
    settings = _object(data["settings"], set(skew.SETTINGS))
    machine = _text(data["machine"])
    flags = _strings(data["flags"])
    if (
        libraries != {"Pillow": "12.3.0", "pikepdf": "10.16.0"}
        or machine not in {"arm64", "x86_64"}
        or flags != tuple(native_setup.FLAGS)
        or any(
            type(settings[key]) is not type(want) or settings[key] != want
            for key, want in skew.SETTINGS.items()
        )
    ):
        raise DependencyRecordError("Unsupported historical library/build/settings policy.")
    compiler = _tool(data["compiler"], compiler=True)
    compiler_data = cast(dict[str, object], data["compiler"])
    poppler, leptonica = _tool(data["poppler"]), _tool(data["leptonica"])
    if poppler.version != "26.10.0" or leptonica.version != "1.87.0":
        raise DependencyRecordError("Unsupported historical native versions.")
    if type(data["headers"]) is not dict or not data["headers"]:
        raise DependencyRecordError("Saved native build requires header identities.")
    headers = cast(dict[str, object], data["headers"])
    return BuildInputs(
        _digest(data["source_sha256"]),
        _text(data["platform"]),
        machine,
        tuple((key, _text(libraries[key])) for key in sorted(libraries)),
        compiler,
        (_path(compiler_data["driver_path"]), _digest(compiler_data["driver_sha256"])),
        _tool(data["pkg_config"]),
        poppler,
        leptonica,
        tuple(sorted((_path(key), _digest(item)) for key, item in headers.items())),
        _strings(data["pkg_flags"]),
        flags,
    )


def _helper(value: object) -> HelperFacts:
    data = _object(value, {"inputs", "build_identity", "binary_sha256", "controls"})
    inputs = _inputs(data["inputs"])
    build = _digest(data["build_identity"])
    # Preserve the existing native build's JSON digest encoding, including spaces.
    # https://docs.python.org/3.12/library/json.html#json.dumps
    if hashlib.sha256(json.dumps(data["inputs"], sort_keys=True).encode()).hexdigest() != build:
        raise DependencyRecordError("Saved native build digest differs from its inputs.")
    controls = _object(
        data["controls"],
        {
            "clockwise",
            "counterclockwise",
            "upright",
            "blank",
            "near-edge",
            "beyond-edge",
            "private-protocol-controls",
        },
    )
    native = {
        key: analysis_record.restore(controls[key], (1200, 900))
        for key in controls
        if key != "private-protocol-controls"
    }
    for key, source in (("clockwise", 2.0), ("counterclockwise", -2.0), ("upright", 0.0)):
        item = native[key]
        if (
            not item.available
            or item.angle_degrees is None
            or abs(item.angle_degrees + source) > 0.125
        ):
            raise DependencyRecordError("Saved native sign control failed its declared bound.")
    blank, near, beyond = (native[key] for key in ("blank", "near-edge", "beyond-edge"))
    if (
        blank.available
        or blank.score_ratio != 0
        or near.available
        or near.native_status != 0
        or near.score_ratio != 0
        or "skew-range-edge" not in near.reasons
        or beyond.available
        or "skew-range-edge" not in beyond.reasons
    ):
        raise DependencyRecordError("Saved native sentinel/edge control contradicts preflight.")
    protocol = _object(
        controls["private-protocol-controls"],
        {
            "valid-zero",
            "zero-confidence",
            "nonzero-status",
            "nonfinite-angle",
            "nonfinite-ratio",
        },
    )
    expected = (
        ("valid-zero", 0, 0.0, 10.0),
        ("zero-confidence", 0, 0.0, 0.0),
        ("nonzero-status", 1, 0.0, 10.0),
        ("nonfinite-angle", 0, None, 10.0),
        ("nonfinite-ratio", 0, 0.0, None),
    )
    checked: list[tuple[str, skew.Estimate]] = []
    for key, status, angle, ratio in expected:
        item = analysis_record.restore(protocol[key], (1200, 900))
        if (item.native_status, item.angle_degrees, item.score_ratio, item.diagnostics) != (
            status,
            angle,
            ratio,
            "private protocol control",
        ):
            raise DependencyRecordError("Saved private protocol control differs from its input.")
        checked.append((key, item))
    return HelperFacts(
        inputs, build, _digest(data["binary_sha256"]), tuple(sorted(native.items())), tuple(checked)
    )


def restore(value: object, binding: object) -> DependencyFacts:
    """Check closed historical metadata against a separately saved named inventory.

    Neither saved tool hashes nor these consistency checks attest historical
    execution. The helper preflight has no binary path or retained-byte reference;
    this reader returns its digest only. No current package/host/cache is consulted.
    Optional Fontconfig guards and discovery require their own owning readers.
    """
    try:
        _json(value)
        data = _object(
            value,
            {
                "helper",
                "renderer",
                "linked",
                "pillow_features",
                "runtime_resources_verified",
                "limitation",
            },
        )
        if (
            data["runtime_resources_verified"] is not False
            or data["limitation"] != dependencies.LIMITATION
        ):
            raise DependencyRecordError("Saved static preflight cannot grant runtime verification.")
        helper = _helper(data["helper"])
        renderer = _object(data["renderer"], {"path", "version"})
        path = _path(renderer["path"])
        if renderer["version"] != "26.10.0":
            raise DependencyRecordError("Unsupported historical renderer version.")
        graphs = _object(data["linked"], {"pdftocairo", "PIL._imaging", "pikepdf._core"})
        linked = tuple((key, linked_record.restore(graphs[key], binding)) for key in sorted(graphs))
        by_name = dict(linked)
        cairo, pillow, pdf = (
            by_name[key] for key in ("pdftocairo", "PIL._imaging", "pikepdf._core")
        )
        if (
            cairo.root != path
            or cairo.executable_context != path
            or pillow.executable_context != pdf.executable_context
            or not re.fullmatch(r"_imaging\.[^/]+\.so", Path(pillow.root).name)
            or not re.fullmatch(r"_core\.[^/]+\.so", Path(pdf.root).name)
            or any(
                item.architecture != helper.inputs.machine or item.os_build != cairo.os_build
                for _, item in linked
            )
        ):
            raise DependencyRecordError("Historical renderer/codec graph associations disagree.")
        files: dict[str, linked_record.LinkedFile] = {}
        for _, graph in linked:
            for item in graph.files:
                if item.path in files and files[item.path] != item:
                    raise DependencyRecordError(
                        "Historical native graphs disagree on a shared file."
                    )
                files[item.path] = item
        if type(data["pillow_features"]) is not dict:
            raise DependencyRecordError("Saved Pillow features require an object.")
        features = cast(dict[str, object], data["pillow_features"])
        return DependencyFacts(
            Path(path),
            helper,
            linked,
            tuple(
                sorted(
                    (_text(key), None if item is None else _text(item))
                    for key, item in features.items()
                )
            ),
        )
    except (
        OccurrenceRecordError,
        ResourceRecordError,
        analysis_record.AnalysisRecordError,
    ) as error:
        raise DependencyRecordError(
            "Saved dependency metadata could not verify: " + error.message
        ) from error
