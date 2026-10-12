"""Historical preflight consistency cannot confer execution or source fidelity.

Literal input/control truth and coherent rehashes expose omitted semantic checks.
No old executable, compiler, helper cache or native library is read on restore.
"""

import copy
import hashlib
import json
import subprocess
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest
from test_analysis_record import literal as analysis_literal
from test_assessed_record import owner as owner
from test_assessed_record import state as build_assessed_fixture
from test_dependencies import commands
from test_resource_record import SHA, file
from test_resource_record import literal as binding_literal

from bookscan import dependencies, records
from bookscan.ownership import Writer
from bookscan.project_header import Stores

RENDERER = "/historical/pdftocairo"
ROOTS = {
    "pdftocairo": RENDERER,
    "PIL._imaging": "/historical/_imaging.cpython-312-darwin.so",
    "pikepdf._core": "/historical/_core.cpython-312-darwin.so",
}


@pytest.fixture(name="assessed_state")
def assessment_context(owner: Writer, tmp_path: Path) -> tuple[Stores, dict[str, object]]:  # noqa: F811
    build = cast(
        Callable[[Writer, Path], tuple[Stores, dict[str, object]]],
        getattr(build_assessed_fixture, "__wrapped__"),
    )
    return build(owner, tmp_path)


def estimate(
    angle: float | None,
    ratio: float | None,
    status: int = 0,
    *,
    diagnostics: str = "",
) -> dict[str, object]:
    value = analysis_literal()
    available = status == 0 and angle is not None and ratio is not None and ratio != 0
    value.update(
        native_status=status,
        angle_degrees=angle,
        score_ratio=ratio,
        invalid_numeric=[
            name + ":nonfinite"
            for name, number in (("angle_degrees", angle), ("score_ratio", ratio))
            if number is None
        ],
        available=available,
        diagnostics=diagnostics,
        reasons=(
            (["skew-nonzero"] if angle != 0 else []) if available else ["assessment-unavailable"]
        )
        + (["skew-range-edge"] if angle is not None and abs(angle) > 6 else []),
    )
    return value


def rehash(value: dict[str, object]) -> None:
    helper = cast(dict[str, object], value["helper"])
    helper["build_identity"] = hashlib.sha256(
        json.dumps(helper["inputs"], sort_keys=True).encode()
    ).hexdigest()


def literal() -> tuple[dict[str, object], dict[str, object]]:
    inputs: dict[str, object] = {
        "source_sha256": SHA,
        "platform": "macOS-26.0-arm64-arm-64bit",
        "machine": "arm64",
        "python_libraries": {"Pillow": "12.3.0", "pikepdf": "10.16.0"},
        "compiler": {
            "path": "/historical/clang",
            "sha256": SHA,
            "driver_path": "/historical/clang-driver",
            "driver_sha256": SHA,
            "version": "Apple clang version 17\nTarget: arm64-apple-darwin",
        },
        "pkg_config": {"path": "/historical/pkg-config", "sha256": SHA, "version": "2.5.1"},
        "poppler": {"path": "/historical/pdftoppm", "sha256": SHA, "version": "26.10.0"},
        "leptonica": {
            "path": "/historical/libleptonica.6.dylib",
            "sha256": SHA,
            "version": "1.87.0",
        },
        "headers": {"/historical/include/allheaders.h": SHA},
        "pkg_flags": ["-I/historical/include", "-L/historical", "-lleptonica"],
        "flags": ["-std=c11", "-Wall", "-Wextra", "-Werror", "-O2"],
        "settings": analysis_literal()["settings"],
    }
    controls: dict[str, object] = {
        "clockwise": estimate(-2.0, 10.0),
        "counterclockwise": estimate(2.0, 10.0),
        "upright": estimate(0.0, 10.0),
        "blank": estimate(0.0, 0.0),
        "near-edge": estimate(-6.5, 0.0),
        "beyond-edge": estimate(-7.0, 0.0),
        "private-protocol-controls": {
            "valid-zero": estimate(0.0, 10.0, diagnostics="private protocol control"),
            "zero-confidence": estimate(0.0, 0.0, diagnostics="private protocol control"),
            "nonzero-status": estimate(0.0, 10.0, 1, diagnostics="private protocol control"),
            "nonfinite-angle": estimate(None, 10.0, diagnostics="private protocol control"),
            "nonfinite-ratio": estimate(0.0, None, diagnostics="private protocol control"),
        },
    }
    linked: dict[str, object] = {}
    for key, path in ROOTS.items():
        linked[key] = {
            "root": path,
            "executable_context": path if key == "pdftocairo" else "/historical/python",
            "architecture": "arm64",
            "os_build": "26A434",
            "files": {
                path: {
                    "sha256": SHA,
                    "load_commands": commands(
                        Path(path), ("LC_LOAD_DYLIB", "/usr/lib/libSystem.B.dylib")
                    ),
                    "references": [
                        {
                            "kind": "LC_LOAD_DYLIB",
                            "reference": "/usr/lib/libSystem.B.dylib",
                            "identity": "OS shared-cache reference; disk bytes not claimed",
                        }
                    ],
                }
            },
            "system_references": ["/usr/lib/libSystem.B.dylib"],
            "runtime_resources_verified": False,
            "limitation": dependencies.LIMITATION,
        }
    binding = binding_literal()
    binding["directories"] = []
    binding["files"] = [{**file(), "path": p, "resolved": p} for p in sorted(ROOTS.values())]
    value: dict[str, object] = {
        "helper": {
            "inputs": inputs,
            "build_identity": "",
            "binary_sha256": SHA,
            "controls": controls,
        },
        "renderer": {"path": RENDERER, "version": "26.10.0"},
        "linked": linked,
        "pillow_features": {"jpg": "9f", "littlecms2": "2.17", "zlib": "1.3.1", "xcb": None},
        "runtime_resources_verified": False,
        "limitation": dependencies.LIMITATION,
    }
    rehash(value)
    return value, binding


def test_historical_facts_are_detached_without_any_file_or_native_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import dependency_record

    value, binding = literal()

    def denied(*args: object, **kwargs: object) -> object:
        raise PermissionError("historical I/O denied")

    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(Path, "stat", denied)
    monkeypatch.setattr(Path, "resolve", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    with pytest.raises(PermissionError):
        Path(RENDERER).stat()
    result = dependency_record.restore(records.decode(json.dumps(value).encode()), binding)
    assert result.renderer == Path(RENDERER)
    assert result.helper.binary_sha256 == SHA
    assert result.helper.inputs.leptonica.path == "/historical/libleptonica.6.dylib"
    assert dict(result.helper.inputs.python_libraries) == {"Pillow": "12.3.0", "pikepdf": "10.16.0"}
    assert dict(result.helper.controls)["clockwise"].angle_degrees == -2.0
    assert dict(result.helper.protocol_controls)["nonfinite-angle"].angle_degrees is None
    assert result.linked[0][1].os_build == "26A434"
    assert dict(result.pillow_features)["xcb"] is None
    value["linked"] = {}
    assert len(result.linked) == 3
    with pytest.raises(FrozenInstanceError):
        result.renderer = Path("/wrong")  # type: ignore[misc]
    assert not hasattr(result.helper, "binary") and not hasattr(
        result, "runtime_resources_verified"
    )


FAULTS = (
    "outer-extra",
    "outer-missing",
    "runtime",
    "limitation",
    "renderer-version",
    "renderer-path",
    "helper-extra",
    "build-digest",
    "binary-digest",
    "inputs-extra",
    "machine",
    "platform",
    "pillow-version",
    "pikepdf-version",
    "leptonica-version",
    "poppler-version",
    "flags",
    "settings",
    "settings-type",
    "headers-empty",
    "header-path",
    "header-digest",
    "pkg-flags",
    "tool-path",
    "tool-digest",
    "driver-digest",
    "tool-version",
    "source-digest",
    "control-missing",
    "control-extra",
    "control-sign",
    "control-bound",
    "control-region",
    "blank",
    "near-status",
    "beyond-edge",
    "protocol-missing",
    "protocol-measurement",
    "protocol-diagnostics",
    "codec-type",
    "codec-name",
    "linked-missing",
    "linked-extra",
    "linked-architecture",
    "linked-build",
    "linked-renderer",
    "linked-context",
    "linked-codec",
    "binding-digest",
    "binding-missing",
    "tuple",
    "nan",
    "surrogate",
    "nonstring-key",
)


def mutate(value: dict[str, object], binding: dict[str, object], fault: str) -> None:
    helper = cast(dict[str, object], value["helper"])
    inputs = cast(dict[str, object], helper["inputs"])
    controls = cast(dict[str, dict[str, object]], helper["controls"])
    linked = cast(dict[str, dict[str, object]], value["linked"])
    if fault == "outer-extra":
        value["accepted"] = True
    elif fault == "outer-missing":
        del value["limitation"]
    elif fault == "runtime":
        value["runtime_resources_verified"] = 0
    elif fault == "limitation":
        value["limitation"] = "verified"
    elif fault.startswith("renderer-"):
        cast(dict[str, object], value["renderer"])[fault.removeprefix("renderer-")] = "wrong"
    elif fault == "helper-extra":
        helper["binary"] = "/invented/skew"
    elif fault == "build-digest":
        helper["build_identity"] = "0" * 64
    elif fault == "binary-digest":
        helper["binary_sha256"] = "wrong"
    elif fault == "inputs-extra":
        inputs["accepted"] = True
    elif fault == "machine":
        inputs["machine"] = "ppc"
    elif fault == "platform":
        inputs["platform"] = ""
    elif fault in ("pillow-version", "pikepdf-version"):
        cast(dict[str, object], inputs["python_libraries"])[
            "Pillow" if fault.startswith("pillow") else "pikepdf"
        ] = "future"
    elif fault in ("leptonica-version", "poppler-version"):
        cast(dict[str, object], inputs[fault.split("-")[0]])["version"] = "future"
    elif fault == "flags":
        inputs["flags"] = ["-O0"]
    elif fault.startswith("settings"):
        cast(dict[str, object], inputs["settings"])["sweep_reduction"] = (
            4.0 if fault.endswith("type") else 1
        )
    elif fault == "headers-empty":
        inputs["headers"] = {}
    elif fault.startswith("header-"):
        inputs["headers"] = {
            "../header" if fault == "header-path" else "/header": "wrong"
            if fault == "header-digest"
            else SHA
        }
    elif fault == "pkg-flags":
        inputs["pkg_flags"] = [1]
    elif fault in ("tool-path", "tool-digest", "tool-version", "driver-digest"):
        cast(dict[str, object], inputs["compiler"])[
            {
                "tool-path": "path",
                "tool-digest": "sha256",
                "tool-version": "version",
                "driver-digest": "driver_sha256",
            }[fault]
        ] = ""
    elif fault == "source-digest":
        inputs["source_sha256"] = "wrong"
    elif fault == "control-missing":
        del controls["upright"]
    elif fault == "control-extra":
        controls["invented"] = controls["upright"]
    elif fault in ("control-sign", "control-bound"):
        controls["clockwise"] = estimate(2.0 if fault == "control-sign" else -1.874, 10.0)
    elif fault == "control-region":
        controls["upright"]["regions"] = [[0, 0, 10, 10]]
    elif fault == "blank":
        controls["blank"] = estimate(0.0, 10.0)
    elif fault == "near-status":
        controls["near-edge"] = estimate(-6.5, 0.0, 1)
    elif fault == "beyond-edge":
        controls["beyond-edge"] = estimate(0.0, 0.0)
    elif fault == "protocol-missing":
        del controls["private-protocol-controls"]["nonfinite-angle"]
    elif fault == "protocol-measurement":
        controls["private-protocol-controls"]["valid-zero"] = estimate(
            0.1, 10.0, diagnostics="private protocol control"
        )
    elif fault == "protocol-diagnostics":
        cast(dict[str, object], controls["private-protocol-controls"]["valid-zero"])[
            "diagnostics"
        ] = "native"
    elif fault == "codec-type":
        cast(dict[str, object], value["pillow_features"])["jpg"] = True
    elif fault == "codec-name":
        cast(dict[str, object], value["pillow_features"])[""] = "1"
    elif fault == "linked-missing":
        del linked["PIL._imaging"]
    elif fault == "linked-extra":
        linked["foreign"] = linked["pdftocairo"]
    elif fault == "linked-architecture":
        linked["pdftocairo"]["architecture"] = "x86_64"
    elif fault == "linked-build":
        linked["PIL._imaging"]["os_build"] = "other"
    elif fault == "linked-renderer":
        cast(dict[str, object], value["renderer"])["path"] = ROOTS["PIL._imaging"]
    elif fault == "linked-context":
        linked["pikepdf._core"]["executable_context"] = "/foreign/python"
    elif fault == "linked-codec":
        linked["PIL._imaging"], linked["pikepdf._core"] = (
            linked["pikepdf._core"],
            linked["PIL._imaging"],
        )
    elif fault == "binding-digest":
        cast(list[dict[str, object]], binding["files"])[0]["sha256"] = "0" * 64
    elif fault == "binding-missing":
        binding["files"] = []
    elif fault == "tuple":
        inputs["pkg_flags"] = tuple(cast(list[object], inputs["pkg_flags"]))
    elif fault == "nan":
        inputs["platform"] = float("nan")
    elif fault == "surrogate":
        inputs["platform"] = "\ud800"
    elif fault == "nonstring-key":
        cast(dict[object, object], inputs["headers"])[1] = SHA
    else:
        raise AssertionError(fault)
    if fault not in ("build-digest", "nan", "nonstring-key"):
        rehash(value)


@pytest.mark.parametrize("fault", FAULTS)
def test_coherent_rehash_does_not_waive_saved_semantics(fault: str) -> None:
    from bookscan import dependency_record

    value, binding = literal()
    mutate(value, binding, fault)
    before = copy.deepcopy((value, binding))
    with pytest.raises(dependency_record.DependencyRecordError) as caught:
        dependency_record.restore(value, binding)
    assert caught.value.code == "INVALID_PROJECT" and caught.value.exit_code == 3
    assert "Fresh import loses review facts" in caught.value.remediation
    if fault != "nan":
        assert (value, binding) == before


@pytest.mark.parametrize("angle", [-2.125, -1.875])
def test_declared_native_sign_tolerance_includes_boundary(angle: float) -> None:
    from bookscan import dependency_record

    value, binding = literal()
    cast(dict[str, object], cast(dict[str, object], value["helper"])["controls"])["clockwise"] = (
        estimate(angle, 10.0)
    )
    assert (
        dict(dependency_record.restore(value, binding).helper.controls)["clockwise"].angle_degrees
        == angle
    )


@pytest.mark.parametrize(
    "fault", ["valid", "build-digest", "control-sign", "linked-context", "binding-digest"]
)
def test_saved_history_checks_dependency_context_before_occurrences(
    assessed_state: tuple[Stores, dict[str, object]],
    fault: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import assessed_record, dependency_record, ownership, project_header

    stores, value = assessed_state
    metadata, binding = literal()
    value.update(dependencies=metadata, resource_binding=binding)
    for occurrence in cast(list[dict[str, object]], value["occurrences"]):
        cast(list[str], cast(dict[str, object], occurrence["render"])["command"])[0] = RENDERER
    prior = copy.deepcopy(value)
    if fault != "valid":
        mutate(
            cast(dict[str, object], prior["dependencies"]),
            cast(dict[str, object], prior["resource_binding"]),
            fault,
        )
    previous = stores.checkpoints.commit(
        prior, expected=None, verify_state=lambda _: None
    ).checkpoint
    stores.checkpoints.commit(value, expected=previous, verify_state=lambda _: None)
    path = stores.owner.path
    stores.owner.close()
    before = {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()}

    def verify(held: Stores, payload: dict[str, object]) -> None:
        context = dependency_record.restore(payload["dependencies"], payload["resource_binding"])
        assessed_record.restore(
            held,
            payload["source"],
            payload["occurrences"],
            payload["baselines"],
            payload["native_blobs"],
            context.renderer,
        )

    def denied(*args: object, **kwargs: object) -> object:
        raise PermissionError("native launch denied on restart")

    monkeypatch.setattr(subprocess, "Popen", denied)
    if fault == "valid":
        with project_header.resume(path, verify_state=verify) as (_, current):
            assert current.revision == 2
    else:
        with pytest.raises(dependency_record.DependencyRecordError):
            with project_header.resume(path, verify_state=verify):
                pytest.fail("Corrupt historical dependency context accepted")
    assert {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()} == before
    with ownership.Writer.acquire(path, stores.header.lock):
        pass  # Failure and successful resume both release their single acquisition.
