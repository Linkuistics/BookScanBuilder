# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["pillow==11.3.0", "numpy==2.2.6"]
# ///
"""Complete-canvas extraction diagnostics only; no fit or correction output."""

from __future__ import annotations

import argparse
import ctypes as ct
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw
from staff_coordinates import ROOT, digest, native, preflight

SPEC = ROOT / "experiments/norwegian_canvases.json"


def centres(path: Path) -> list[list[list[float]]]:
    lib = native()
    for name, result, args in (
        ("pixRead", ct.c_void_p, [ct.c_char_p]),
        ("pixConvertTo8", ct.c_void_p, [ct.c_void_p, ct.c_int]),
        ("pixThresholdToBinary", ct.c_void_p, [ct.c_void_p, ct.c_int]),
        ("dewarpGetTextlineCenters", ct.c_void_p, [ct.c_void_p, ct.c_int]),
    ):
        fn = getattr(lib, name)
        fn.restype, fn.argtypes = result, args
    pix = ct.c_void_p(lib.pixRead(str(path).encode()))
    gray = ct.c_void_p()
    binary = ct.c_void_p()
    traces = ct.c_void_p()
    try:
        if not pix.value:
            raise RuntimeError("Native PNG read failed")
        gray.value = lib.pixConvertTo8(pix, 0)
        if not gray.value:
            raise RuntimeError("Native grayscale conversion failed")
        binary.value = lib.pixThresholdToBinary(gray, 180)
        if not binary.value:
            raise RuntimeError("Native threshold failed")
        traces.value = lib.dewarpGetTextlineCenters(binary, 0)
        lines: list[list[list[float]]] = []
        if not traces.value:
            return lines
        for i in range(lib.ptaaGetCount(traces)):
            pta = ct.c_void_p(lib.ptaaGetPta(traces, i, 2))
            try:
                points: list[list[float]] = []
                for j in range(lib.ptaGetCount(pta)):
                    x, y = ct.c_float(), ct.c_float()
                    if lib.ptaGetPt(pta, j, ct.byref(x), ct.byref(y)):
                        raise RuntimeError("Native extracted-point read failed")
                    points.append([x.value, y.value])
                lines.append(points)
            finally:
                lib.ptaDestroy(ct.byref(pta))
        return lines
    finally:
        lib.ptaaDestroy(ct.byref(traces))
        lib.pixDestroy(ct.byref(binary))
        lib.pixDestroy(ct.byref(gray))
        lib.pixDestroy(ct.byref(pix))


def run(artifacts: Path, collection: Path) -> None:
    if artifacts.resolve().is_relative_to(collection.resolve()):
        raise ValueError("Artifacts must be outside the collection")
    spec = json.loads(SPEC.read_text())
    lib = native()
    renderer = shutil.which("pdftoppm")
    if not renderer:
        raise RuntimeError("pdftoppm is required")
    subjects = [
        Path(renderer),
        SPEC,
        Path(__file__),
        ROOT / "experiments/staff_coordinates.py",
        ROOT / "Taskfile.yml",
        Path(lib._name),
        Path(spec["pinned_native_source"]),
        Path(spec["historical_control"]),
        ROOT / "docs/experiments/page-geometry-frozen.json",
    ] + [collection / item["source"] for item in spec["sources"].values()]
    before = {str(p.resolve()): digest(p) for p in subjects}
    artifacts.mkdir(parents=True, exist_ok=False)
    commands = []
    for name, item in spec["sources"].items():
        source = collection / item["source"]
        if digest(source) != item["sha256"]:
            raise ValueError(f"Source identity changed: {name}")
        command = [
            "pdftoppm",
            "-f",
            "20",
            "-l",
            "20",
            "-singlefile",
            "-r",
            "300",
            "-png",
            str(source),
            str(artifacts / name),
        ]
        proc = subprocess.run(command, check=True, capture_output=True, text=True)
        commands.append({"argv": command, "stdout": proc.stdout, "stderr": proc.stderr})
        with Image.open(artifacts / f"{name}.png") as im:
            if list(im.size) != item["dimensions"] or im.mode != "RGB":
                raise ValueError(f"Unexpected full RGB canvas: {name}")
    with Image.open(artifacts / "spread.png") as spread:
        if digest(artifacts / "spread.png") != spec["spread_render_sha256"]:
            raise ValueError("Spread differs from inspected pre-output source render")
        x = spec["split_x"]
        left = spread.crop((0, 0, x, spread.height))
        right = spread.crop((x, 0, spread.width, spread.height))
        left.save(artifacts / "left.png")
        right.save(artifacts / "right.png")
        joined = Image.new("RGB", spread.size)
        joined.paste(left, (0, 0))
        joined.paste(right, (x, 0))
        if joined.tobytes() != spread.tobytes():
            raise ValueError("Split lost or changed source pixels")
    with Image.open(artifacts / "control.png") as control:
        with Image.open(spec["historical_control"]) as historical:
            control_matches = control.size == historical.size and (
                control.tobytes() == historical.tobytes()
            )
        if not control_matches:
            raise ValueError("Control differs from k4 unchanged RGB")
    subjects += [artifacts / f"{n}.png" for n in ("spread", "left", "right", "control")]
    before.update({str(p.resolve()): digest(p) for p in subjects[-4:]})
    results = {}
    for name in ("left", "right", "control"):
        path = artifacts / f"{name}.png"
        with Image.open(path) as im:
            lines = centres(path)
            gate = (
                preflight(lines, im.width, im.height)
                if lines
                else {
                    "passed": False,
                    "retained_count": 0,
                    "reason": "no extracted lines",
                }
            )
            results[name] = {"dimensions": list(im.size), "extracted": lines, "native_gate": gate}
            overlay = im.copy()
            draw = ImageDraw.Draw(overlay)
            for i, points in enumerate(gate.get("retained_points", [])):
                draw.line([tuple(p) for p in points], fill=(255, 0, 0), width=1)
                draw.text(tuple(points[0]), str(i), fill=(0, 0, 255))
            overlay.save(artifacts / f"{name}-automatic-overlay.png")
            for label, box in spec["crops"].get(name, {}).items():
                im.crop(tuple(box)).save(artifacts / f"{name}-{label}.png")
    outputs = {p.name: digest(p) for p in sorted(artifacts.iterdir()) if p.is_file()}
    after = {str(p.resolve()): digest(p) for p in subjects}
    if before != after:
        raise ValueError("A measurement subject changed")
    report = {
        "scope": "unmasked acquisition diagnostic, no physical identity or held-out acceptance",
        "independent_marks": None,
        "holdouts": None,
        "model": None,
        "application": None,
        "control_pixel_match_k4": control_matches,
        "split_recombines_exactly": True,
        "settings": {
            "threshold": 180,
            "longest_filter": 0.8,
            "minimum": 15,
            "sampling_if_future_fit": 30,
            "reduction_if_future_fit": 1,
        },
        "spec": spec,
        "commands": commands,
        "poppler": subprocess.run(["pdftoppm", "-v"], capture_output=True, text=True).stderr,
        "before": before,
        "after": after,
        "outputs": outputs,
        "results": results,
    }
    (artifacts / "preflight.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                n: {
                    k: v
                    for k, v in r["native_gate"].items()
                    if k not in ("retained_points", "first_y_float32", "first_y_native_integer")
                }
                for n, r in results.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--collection", type=Path, default=Path("/Volumes/Glass/Book Conversion"))
    args = parser.parse_args()
    run(args.artifacts, args.collection)
