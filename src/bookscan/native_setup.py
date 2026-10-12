"""Explicit product helper build and read-only runtime preflight, independent of experiments."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.resources
import json
import math
import os
import platform
import re
import shlex
import shutil
import signal
import subprocess
import tempfile
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from PIL import Image

from bookscan import analysis_workspace
from bookscan.skew import (
    LEPTONICA,
    SETTINGS,
    AssessmentFailed,
    Estimate,
    NativeError,
    json_object,
    parse_estimate,
)

FLAGS = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-O2"]
ENTRY = re.compile(r"native-([0-9a-f]{64})-[0-9a-f]{32}")


def default_cache() -> Path:
    return Path.home() / "Library" / "Caches" / "BookScanBuilder" / "skew-v1"


def digest(path: Path, *, check_cancel: Callable[[], None] = lambda: None) -> str:
    check_cancel()
    with path.open("rb") as stream:
        hasher = hashlib.sha256()
        while data := stream.read(1024 * 1024):
            check_cancel()
            hasher.update(data)
        check_cancel()
        return hasher.hexdigest()


def source_bytes() -> bytes:
    return importlib.resources.files("bookscan").joinpath("native/skew.c").read_bytes()


def execute(
    argv: list[str],
    *,
    check_cancel: Callable[[], None] = lambda: None,
    timeout: float = 120,
    environment: Mapping[str, str] | None = None,
    directory: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Reap owned children on every exception; callbacks allow the writer's signal policy."""
    check_cancel()
    try:
        child = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            # Explicit env replaces inheritance; values are copied before launch.
            # https://docs.python.org/3.12/library/subprocess.html#subprocess.Popen
            env=None if environment is None else dict(environment),
            cwd=directory,
            close_fds=True,
            start_new_session=True,
        )
    except OSError as error:
        raise NativeError(f"Cannot start {argv[0]}: {error}") from error
    try:
        # communicate drains both pipes and reaps the actual child, never a launcher.
        remaining = timeout
        while True:
            check_cancel()
            try:
                stdout, stderr = child.communicate(timeout=min(0.1, remaining))
                break
            except subprocess.TimeoutExpired:
                remaining -= 0.1
                if remaining <= 0:
                    raise NativeError(f"Native operation timed out: {argv[0]}") from None
        check_cancel()
        return subprocess.CompletedProcess(argv, child.returncode, stdout, stderr)
    except BaseException:
        # Cleanup only, then propagate the caller's cancellation/error unchanged.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.communicate()
        raise


def checked(argv: list[str], *, check_cancel: Callable[[], None] = lambda: None) -> str:
    result = execute(argv, check_cancel=check_cancel)
    if result.returncode != 0:
        raise NativeError(f"{argv[0]} exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout.strip()


def tool(name: str) -> Path:
    executable = shutil.which(name)
    if executable is None:
        raise NativeError(
            f"Missing {name}. Install Homebrew poppler/leptonica/pkgconf "
            "and Xcode command-line tools."
        )
    return Path(executable).resolve(strict=True)


def inputs(*, check_cancel: Callable[[], None] = lambda: None) -> dict[str, object]:
    """Exact currently supported native release; setup fails on unverified upgrades."""
    check_cancel()
    if platform.system() != "Darwin":
        raise NativeError("This native helper build is verified on macOS only.")
    versions = {name: importlib.metadata.version(name) for name in ("Pillow", "pikepdf")}
    if versions != {"Pillow": "12.3.0", "pikepdf": "10.16.0"}:
        raise NativeError(
            f"Unsupported Python PDF/image library versions: {versions}; uv sync --locked."
        )
    compiler, pkg, renderer = (tool(name) for name in ("clang", "pkg-config", "pdftoppm"))
    lept = checked([str(pkg), "--modversion", "lept"], check_cancel=check_cancel)
    if lept != "1.87.0":
        raise NativeError(f"Unsupported Leptonica {lept}; verified version is 1.87.0.")
    rendered_version = execute([str(renderer), "-v"], check_cancel=check_cancel)
    renderer_text = rendered_version.stdout + rendered_version.stderr
    if (
        rendered_version.returncode != 0
        or not renderer_text.splitlines()
        or renderer_text.splitlines()[0] != "pdftoppm version 26.10.0"
    ):
        raise NativeError(
            f"Unsupported Poppler; verified pdftoppm is 26.10.0: {renderer_text.strip()}"
        )
    driver = Path(
        checked([str(compiler), "-print-prog-name=clang"], check_cancel=check_cancel)
    ).resolve(strict=True)
    include = Path(checked([str(pkg), "--variable=includedir", "lept"], check_cancel=check_cancel))
    library = (
        Path(checked([str(pkg), "--variable=libdir", "lept"], check_cancel=check_cancel))
        / "libleptonica.dylib"
    ).resolve(strict=True)
    headers = {
        str(path): digest(path, check_cancel=check_cancel) for path in sorted(include.glob("*.h"))
    }
    if not headers:
        raise NativeError(f"Missing Leptonica headers in {include}.")
    result: dict[str, object] = {
        "source_sha256": hashlib.sha256(source_bytes()).hexdigest(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python_libraries": versions,
        "compiler": {
            "path": str(compiler),
            "sha256": digest(compiler, check_cancel=check_cancel),
            "driver_path": str(driver),
            "driver_sha256": digest(driver, check_cancel=check_cancel),
            "version": checked([str(compiler), "--version"], check_cancel=check_cancel),
        },
        "pkg_config": {
            "path": str(pkg),
            "sha256": digest(pkg, check_cancel=check_cancel),
            "version": checked([str(pkg), "--version"], check_cancel=check_cancel),
        },
        "poppler": {
            "path": str(renderer),
            "sha256": digest(renderer, check_cancel=check_cancel),
            "version": "26.10.0",
        },
        "leptonica": {
            "version": lept,
            "path": str(library),
            "sha256": digest(library, check_cancel=check_cancel),
        },
        "headers": headers,
        "pkg_flags": shlex.split(
            checked([str(pkg), "--cflags", "--libs", "lept"], check_cancel=check_cancel)
        ),
        "flags": FLAGS,
        "settings": dict(SETTINGS),
    }
    check_cancel()
    return result


@dataclass(frozen=True)
class Helper:
    binary: Path
    manifest: dict[str, object]


def _regular(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise NativeError(f"Missing/replaced native cache file: {path}.")


def load_cache(cache: Path, *, check_cancel: Callable[[], None] = lambda: None) -> Helper:
    check_cancel()
    try:
        pointer = cache / "current.json"
        _regular(pointer)
        entry_name = json_object(pointer.read_text()).get("entry")
        if not isinstance(entry_name, str) or (match := ENTRY.fullmatch(entry_name)) is None:
            raise NativeError("Invalid native cache pointer; run task process:setup.")
        entry = cache / entry_name
        if entry.is_symlink() or not entry.is_dir():
            raise NativeError(f"Missing/replaced native build directory: {entry}.")
        binary, manifest_path = entry / "skew", entry / "build.json"
        _regular(binary)
        _regular(manifest_path)
        manifest = json_object(manifest_path.read_text())
        check_cancel()
        if (
            manifest.get("schema") != "BookScanBuilderNativeBuild"
            or type(manifest.get("version")) is not int
            or manifest["version"] != 1
            or manifest.get("build_identity") != match[1]
            or not isinstance(manifest.get("inputs"), dict)
            or hashlib.sha256(json.dumps(manifest["inputs"], sort_keys=True).encode()).hexdigest()
            != manifest["build_identity"]
            or manifest.get("binary_sha256") != digest(binary, check_cancel=check_cancel)
            or not os.access(binary, os.X_OK)
        ):
            raise NativeError(f"Incomplete/changed native helper build: {entry}.")
        check_cancel()
        return Helper(binary, manifest)
    except (OSError, UnicodeError) as error:
        raise NativeError(f"Cannot read native cache {cache}: {error}") from error


def _identity(binary: Path, *, check_cancel: Callable[[], None] = lambda: None) -> None:
    data = json_object(checked([str(binary), "--identity"], check_cancel=check_cancel))
    if (
        data.get("schema") != "BookScanBuilderSkewIdentity"
        or type(data.get("version")) is not int
        or data["version"] != 1
        or data.get("leptonica") != LEPTONICA
        or data.get("headers") != "1.87.0"
    ):
        raise NativeError("Native helper linked/header identity or protocol is incompatible.")


def assess(
    binary: Path,
    baseline: Image.Image,
    directory: Path,
    *,
    check_cancel: Callable[[], None] = lambda: None,
) -> Estimate:
    check_cancel()
    with analysis_workspace.image(baseline, directory) as workspace:
        image_path = workspace.path
        before = digest(image_path, check_cancel=check_cancel)
        result = execute([str(binary), "analyze", str(image_path)], check_cancel=check_cancel)
        workspace.verify()
        if result.returncode != 0:
            raise AssessmentFailed(f"Estimator exited {result.returncode}: {result.stderr.strip()}")
        if digest(image_path, check_cancel=check_cancel) != before:
            raise AssessmentFailed("Native estimator modified its disposable analysis image.")
        estimate = parse_estimate(result.stdout, result.stderr, baseline.size)
        check_cancel()
        return estimate


def _control_image(degrees: float) -> Image.Image:
    """Analytic rows, not a renderer or rotation sampler: y grows downward."""
    image = Image.new("RGB", (1200, 900), "white")
    slope = math.tan(math.radians(degrees))
    for row in range(24):
        for x in range(100, 1100):
            if (x // 12) % 3 == 0:
                continue
            y = 140 + row * 24 + round((x - 600) * slope)
            image.paste((0, 0, 0), (x, y, x + 1, y + 5 + (x // 12) % 4))
    return image


def self_test(
    binary: Path, *, check_cancel: Callable[[], None] = lambda: None
) -> dict[str, object]:
    _identity(binary, check_cancel=check_cancel)
    outcomes: dict[str, object] = {}
    # Declared before outputs: 0.125 degrees exceeds 2-pixel/1000-pixel phase
    # uncertainty (~0.115 degrees) plus the pinned 0.01 search step. This is only
    # an API/sign sanity check of analytic rows, never real-page estimator accuracy.
    with tempfile.TemporaryDirectory(prefix="bookscan-native-controls-") as temporary:
        for name, source_angle in (
            ("clockwise", 2.0),
            ("counterclockwise", -2.0),
            ("upright", 0.0),
        ):
            check_cancel()
            with _control_image(source_angle) as image:
                estimate = assess(binary, image, Path(temporary), check_cancel=check_cancel)
            if (
                not estimate.available
                or estimate.angle_degrees is None
                or abs(estimate.angle_degrees + source_angle) > 0.125
            ):
                raise NativeError(
                    f"Native sign/input control failed: {name}; {estimate.to_dict()}."
                )
            outcomes[name] = estimate.to_dict()
        with Image.new("RGB", (1200, 900), "white") as blank:
            estimate = assess(binary, blank, Path(temporary), check_cancel=check_cancel)
        if estimate.available or estimate.score_ratio != 0:
            raise NativeError(f"Native blank sentinel control failed: {estimate.to_dict()}.")
        outcomes["blank"] = estimate.to_dict()
        for name, degrees in (("near-edge", 6.5), ("beyond-edge", 8.0)):
            check_cancel()
            with _control_image(degrees) as image:
                estimate = assess(binary, image, Path(temporary), check_cancel=check_cancel)
            if estimate.available or "skew-range-edge" not in estimate.reasons:
                raise NativeError(f"Native sweep-edge sentinel failed: {name}.")
            if name == "near-edge" and (estimate.native_status != 0 or estimate.score_ratio != 0):
                raise NativeError("Native status-zero/confidence-zero control failed.")
            outcomes[name] = estimate.to_dict()
    # Explicit private protocol controls supplement the native inputs above.
    # Nonfinite native numbers are serialized as null by the bridge; no public
    # fault mode and no claim that a real page naturally returned nonfinite data.
    protocol_controls: dict[str, object] = {}
    for name, status, angle, ratio, available in (
        ("valid-zero", 0, 0.0, 10.0, True),
        ("zero-confidence", 0, 0.0, 0.0, False),
        ("nonzero-status", 1, 0.0, 10.0, False),
        ("nonfinite-angle", 0, None, 10.0, False),
        ("nonfinite-ratio", 0, 0.0, None, False),
    ):
        check_cancel()
        raw = json.dumps(
            {
                "schema": "BookScanBuilderSkew",
                "version": 1,
                "leptonica": LEPTONICA,
                "width": 1200,
                "height": 900,
                "status": status,
                "angle_degrees": angle,
                "score_ratio": ratio,
            }
        )
        estimate = parse_estimate(raw, "private protocol control", (1200, 900))
        if estimate.available != available:
            raise NativeError(f"Native protocol sentinel classification failed: {name}.")
        protocol_controls[name] = estimate.to_dict()
    outcomes["private-protocol-controls"] = protocol_controls
    check_cancel()
    return outcomes


def build(cache: Path) -> Helper:
    try:
        subjects = inputs()
        identity = hashlib.sha256(json.dumps(subjects, sort_keys=True).encode()).hexdigest()
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".build-", dir=cache) as temporary:
            stage = Path(temporary)
            source = stage / "skew.c"
            source.write_bytes(source_bytes())
            compiler = cast(dict[str, object], subjects["compiler"])["path"]
            pkg_flags = cast(list[str], subjects["pkg_flags"])
            argv = [str(compiler), *FLAGS, str(source), *pkg_flags, "-o", str(stage / "skew")]
            checked(argv)
            controls = self_test(stage / "skew")
            # Refuse a build whose observed source/header/compiler/library changed.
            if subjects != inputs():
                raise NativeError("Native build subjects changed while compiling; retry setup.")
            manifest: dict[str, object] = {
                "schema": "BookScanBuilderNativeBuild",
                "version": 1,
                "inputs": subjects,
                "build_identity": identity,
                "binary_sha256": digest(stage / "skew"),
                "controls": controls,
                "command": argv,
            }
            (stage / "build.json").write_text(
                json.dumps(manifest, indent=2, allow_nan=False) + "\n"
            )
            entry_name = f"native-{identity}-{uuid.uuid4().hex}"
            stage.rename(cache / entry_name)
            # All cache assets are complete before its pointer is replaced. Existing
            # build directories stay intact; no project or accepted image is touched.
            with tempfile.NamedTemporaryFile(
                mode="w", prefix=".pointer-", dir=cache, delete=False
            ) as out:
                pointer = Path(out.name)
                out.write(json.dumps({"entry": entry_name}) + "\n")
            try:
                pointer.replace(cache / "current.json")
            finally:
                pointer.unlink(missing_ok=True)
        return load_cache(cache)
    except (OSError, importlib.metadata.PackageNotFoundError) as error:
        raise NativeError(f"Cannot build native helper: {error}") from error


def preflight(cache: Path, *, check_cancel: Callable[[], None] = lambda: None) -> dict[str, object]:
    helper = load_cache(cache, check_cancel=check_cancel)
    try:
        subjects = inputs(check_cancel=check_cancel)
    except (OSError, importlib.metadata.PackageNotFoundError) as error:
        raise NativeError(f"Cannot verify native dependency identities: {error}") from error
    if helper.manifest["inputs"] != subjects:
        raise NativeError("Native build/tool/source identities changed; run task process:setup.")
    controls = self_test(helper.binary, check_cancel=check_cancel)
    check_cancel()
    return {
        "inputs": subjects,
        "build_identity": helper.manifest["build_identity"],
        "binary_sha256": helper.manifest["binary_sha256"],
        "controls": controls,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build/check the packaged advisory estimator; no PDF import or project writes.",
        epilog="Examples: task process:setup; task process:preflight. "
        "Failure exits 5; setup is explicit.",
    )
    parser.add_argument("--cache", type=Path, default=default_cache())
    parser.add_argument(
        "--check", action="store_true", help="verify without building or cache mutation"
    )
    args = parser.parse_args()
    try:
        result = preflight(args.cache) if args.check else build(args.cache).manifest
    except NativeError as error:
        print(
            json.dumps(
                {
                    "code": error.code,
                    "exit_code": 5,
                    "message": str(error),
                    "remediation": error.remediation,
                }
            )
        )
        return 5
    print(json.dumps(result, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
