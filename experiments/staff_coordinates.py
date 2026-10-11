# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["pillow==11.3.0", "numpy==2.2.6"]
# ///
"""Coordinate-only staff trial; never fits or makes a correction image."""

from __future__ import annotations

import argparse
import ctypes as ct
import ctypes.util
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
RECORD = ROOT / "experiments/staff_coordinates.json"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def native() -> ct.CDLL:
    name = ctypes.util.find_library("leptonica")
    if not name:
        libdir = Path(
            subprocess.run(
                ["pkg-config", "--variable=libdir", "lept"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        candidates = [libdir / "libleptonica.dylib", libdir / "libleptonica.so"]
        name = next((str(p) for p in candidates if p.is_file()), None)
    if not name:
        raise RuntimeError("Leptonica 1.87.0 shared library is required")
    lib = ct.CDLL(name)
    signatures = {
        "getLeptonicaVersion": (ct.c_char_p, []),
        "pixCreate": (ct.c_void_p, [ct.c_int, ct.c_int, ct.c_int]),
        "pixDestroy": (None, [ct.POINTER(ct.c_void_p)]),
        "ptaaCreate": (ct.c_void_p, [ct.c_int]),
        "ptaCreate": (ct.c_void_p, [ct.c_int]),
        "ptaAddPt": (ct.c_int, [ct.c_void_p, ct.c_float, ct.c_float]),
        "ptaaAddPta": (ct.c_int, [ct.c_void_p, ct.c_void_p, ct.c_int]),
        "ptaaGetCount": (ct.c_int, [ct.c_void_p]),
        "ptaaGetPta": (ct.c_void_p, [ct.c_void_p, ct.c_int, ct.c_int]),
        "ptaGetCount": (ct.c_int, [ct.c_void_p]),
        "ptaGetPt": (
            ct.c_int,
            [ct.c_void_p, ct.c_int, ct.POINTER(ct.c_float), ct.POINTER(ct.c_float)],
        ),
        "ptaaDestroy": (None, [ct.POINTER(ct.c_void_p)]),
        "ptaDestroy": (None, [ct.POINTER(ct.c_void_p)]),
        "dewarpRemoveShortLines": (ct.c_void_p, [ct.c_void_p, ct.c_void_p, ct.c_float, ct.c_int]),
        "numaCreate": (ct.c_void_p, [ct.c_int]),
        "numaAddNumber": (ct.c_int, [ct.c_void_p, ct.c_float]),
        "numaGetIValue": (ct.c_int, [ct.c_void_p, ct.c_int, ct.POINTER(ct.c_int)]),
        "numaDestroy": (None, [ct.POINTER(ct.c_void_p)]),
    }
    for symbol, (result, args) in signatures.items():
        fn = getattr(lib, symbol)
        fn.restype, fn.argtypes = result, args
    if lib.getLeptonicaVersion().decode() != "leptonica-1.87.0":
        raise RuntimeError("This instrument requires pinned Leptonica 1.87.0")
    return lib


def preflight(lines: list[list[list[float]]], width: int, height: int) -> dict[str, object]:
    """Use native .8 longest filtering and native NUMA rounding, without a fit.

    Coverage arithmetic reproduces dewarp2.c's private coverage function.
    Input uniqueness/physical exclusions are checked separately by run().
    """
    if not lines or width <= 0 or height <= 0 or any(len(p) < 2 for p in lines):
        raise ValueError("Need nonempty traces with at least two points and a full canvas")
    lib = native()
    pix = ct.c_void_p(lib.pixCreate(width, height, 1))
    ptaa = ct.c_void_p(lib.ptaaCreate(len(lines)))
    retained = ct.c_void_p()
    na = ct.c_void_p()
    try:
        for points in lines:
            pta = lib.ptaCreate(len(points))
            for x, y in points:
                if not (0 <= x < width and 0 <= y < height):
                    raise ValueError("Point is outside the unchanged full canvas")
                if lib.ptaAddPt(pta, x, y):
                    raise RuntimeError("Native point insertion failed")
            if lib.ptaaAddPta(ptaa, pta, 0):  # L_INSERT; transfers ownership
                raise RuntimeError("Native trace insertion failed")
        retained.value = lib.dewarpRemoveShortLines(pix, ptaa, 0.8, 0)
        if not retained.value:
            raise RuntimeError("Native longest-line filter failed")
        kept: list[list[list[float]]] = []
        for i in range(lib.ptaaGetCount(retained)):
            pta = ct.c_void_p(lib.ptaaGetPta(retained, i, 2))  # L_CLONE
            try:
                points = []
                for j in range(lib.ptaGetCount(pta)):
                    x, y = ct.c_float(), ct.c_float()
                    if lib.ptaGetPt(pta, j, ct.byref(x), ct.byref(y)):
                        raise RuntimeError("Native point read failed")
                    points.append([x.value, y.value])
                kept.append(points)
            finally:
                lib.ptaDestroy(ct.byref(pta))
        na.value = lib.numaCreate(len(kept))
        first_y = sorted(p[0][1] for p in kept)
        rounded = []
        for i, y in enumerate(first_y):
            lib.numaAddNumber(na, y)
            value = ct.c_int()
            lib.numaGetIValue(na, i, ct.byref(value))
            rounded.append(value.value)
        ntop = sum(y < 0.5 * height for y in rounded)
        fraction = ct.c_float(
            ct.c_float(rounded[-1] - rounded[0]).value / ct.c_float(height).value
        ).value
        return {
            "retained_count": len(kept),
            "retained_points": kept,
            "first_y_float32": first_y,
            "first_y_native_integer": rounded,
            "top_count": ntop,
            "bottom_count": len(kept) - ntop,
            "vertical_span_fraction_float32": fraction,
            "passed": len(kept) >= 15 and ntop >= 4 and len(kept) - ntop >= 4 and fraction > 0.50,
        }
    finally:
        lib.numaDestroy(ct.byref(na))
        lib.ptaaDestroy(ct.byref(retained))
        lib.ptaaDestroy(ct.byref(ptaa))
        lib.pixDestroy(ct.byref(pix))


def shape(points: list[list[float]]) -> dict[str, float]:
    array = np.asarray(points, dtype=np.float64)
    x, y = array[:, 0], array[:, 1]
    linear = np.polyfit(x, y, 1)
    residual = y - np.polyval(linear, x)
    return {
        "rise_pixels": float(linear[0] * (x.max() - x.min())),
        "curvature_peak_to_peak_pixels": float(np.ptp(residual)),
    }


def source_views(artifacts: Path) -> None:
    """Recreate exactly the observed source displays, never new observations."""
    record = json.loads(RECORD.read_text())
    source = Path(record["source"])
    if artifacts.resolve().is_relative_to(source.parent.parent.resolve()):
        raise ValueError("Source displays must be outside the collection")
    artifacts.mkdir(parents=True, exist_ok=True)
    before = digest(source)
    if before != record["source_sha256"]:
        raise ValueError("Original source identity differs")
    render = artifacts / "page-20.png"
    if not render.exists():
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                "20",
                "-l",
                "20",
                "-r",
                "300",
                "-singlefile",
                "-png",
                str(source),
                str(render.with_suffix("")),
            ],
            check=True,
        )
    code = artifacts / "dewarp2-1.87.0.c"
    if not code.exists():
        with urllib.request.urlopen(
            "https://raw.githubusercontent.com/DanBloomberg/leptonica/1.87.0/src/dewarp2.c",
            timeout=30,
        ) as response:
            code.write_bytes(response.read())
    for name, expected in record["frozen_hashes"].items():
        if digest(artifacts / name) != expected:
            raise ValueError(f"Source display prerequisite differs: {name}")
    image = Image.open(render).convert("RGB")
    for name, lo, hi in [
        ("T", 265, 345),
        ("B", 395, 460),
        ("A", 645, 720),
        ("D", 985, 1055),
        ("E", 1235, 1310),
        ("H", 1870, 1950),
        ("I", 2025, 2110),
    ]:
        view = image.crop((155, lo, 1605, hi)).resize((2900, (hi - lo) * 2))
        draw = ImageDraw.Draw(view)
        for x in range(200, 1601, 100):
            draw.line(((x - 155) * 2, 0, (x - 155) * 2, view.height), fill=(160, 200, 255))
            draw.text(((x - 155) * 2 + 2, 2), str(x), fill=(0, 0, 220))
        for y in range((lo // 10 + 1) * 10, hi, 10):
            draw.line((0, (y - lo) * 2, view.width, (y - lo) * 2), fill=(160, 200, 255))
            draw.text((2, (y - lo) * 2 + 2), str(y), fill=(0, 0, 220))
        view.save(artifacts / f"staff-{name}.png")
    xs = [172, 260, 360, 460, 560, 660, 760, 860, 960, 1060, 1160, 1260, 1360, 1460, 1568]
    for name, lo in [("T", 290), ("A", 674), ("D", 1011), ("E", 1264), ("H", 1898), ("I", 2053)]:
        sheet = Image.new("RGB", (1200, 420), "white")
        draw = ImageDraw.Draw(sheet)
        for i, x in enumerate(xs):
            xoff, yoff = (i % 5) * 240, (i // 5) * 140
            patch = image.crop((x - 16, lo, x + 16, lo + 22)).resize(
                (128, 88), Image.Resampling.NEAREST
            )
            sheet.paste(patch, (xoff + 65, yoff + 23))
            draw.text((xoff + 70, yoff + 4), f"x={x}", fill="black")
            draw.line((xoff + 129, yoff + 23, xoff + 129, yoff + 111), fill=(0, 150, 220))
            for y in range(lo, lo + 22, 2):
                sy = yoff + 23 + (y - lo) * 4
                draw.text((xoff + 25, sy - 4), str(y), fill=(0, 0, 200))
                draw.line((xoff + 62, sy, xoff + 68, sy), fill=(0, 0, 200))
        sheet.save(artifacts / f"repeat-{name}.png")
    for name, expected in record["observation_view_hashes"].items():
        if digest(artifacts / name) != expected:
            raise ValueError(f"Recreated display differs: {name}")
    if digest(source) != before:
        raise RuntimeError("Original changed during display reproduction")
    print("Observed source displays reproduced; original unchanged; no new marking or fit")


def run(artifacts: Path) -> None:
    record: dict[str, Any] = json.loads(RECORD.read_text())
    render = artifacts / "page-20.png"
    subjects = [
        RECORD,
        Path(__file__),
        ROOT / "Taskfile.yml",
        Path(record["source"]),
        render,
        artifacts / "dewarp2-1.87.0.c",
        ROOT / "docs/experiments/staff-coordinates-first-pass.json",
        ROOT / "experiments/test_staff_coordinates.py",
        Path(native()._name),
    ]
    subjects.extend(artifacts / name for name in record["observation_view_hashes"])
    collection = Path(record["source"]).parent.parent.resolve()
    if artifacts.resolve().is_relative_to(collection):
        raise ValueError("Disposable artifacts must be outside the source collection")
    before = {str(p): digest(p) for p in subjects}
    for path, expected in record["frozen_hashes"].items():
        if digest(artifacts / path) != expected:
            raise ValueError(f"Frozen subject differs: {path}")
    for path, expected in record["observation_view_hashes"].items():
        if digest(artifacts / path) != expected:
            raise ValueError(f"Observed source view differs: {path}")
    if digest(Path(record["source"])) != record["source_sha256"]:
        raise ValueError("Original source identity differs")
    image = Image.open(render).convert("RGB")
    width, height = image.size
    if [width, height] != record["dimensions"]:
        raise ValueError("Full unchanged canvas differs")
    lines = record["lines"]
    ids = [line["id"] for line in lines]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate physical rule identity")
    all_points = [line["points"] for line in lines]
    if len({json.dumps(p) for p in all_points}) != len(all_points):
        raise ValueError("Duplicate coordinate trace")
    units = {unit["id"]: unit for unit in record["units"]}
    fitting = [line for line in lines if units[line["unit"]]["role"] == "fit"]
    evaluation = [line for line in lines if units[line["unit"]]["role"] == "evaluation"]
    distances: dict[str, object] = {}
    for unit in units.values():
        if unit["role"] != "evaluation":
            continue
        x0, y0, x1, y1 = unit["exclusion"]
        own = [line for line in evaluation if line["unit"] == unit["id"]]
        if len(own) != 5 or {line["rule"] for line in own} != set(range(1, 6)):
            raise ValueError("Evaluation must retain all five physical rules")
        for line in fitting:
            for x, y in line["points"]:
                if x0 <= x <= x1 and y0 <= y <= y1:
                    raise ValueError("Fitting trace enters a whole-unit exclusion")
        # Vertical separation between complete traced polylines, conservative
        # extrema over all observed points, not a claim about every page pixel.
        eval_min = min(p[1] for line in own for p in line["points"])
        eval_max = max(p[1] for line in own for p in line["points"])
        by_line = {}
        for line in fitting:
            lo, hi = min(p[1] for p in line["points"]), max(p[1] for p in line["points"])
            by_line[line["id"]] = max(lo - eval_max, eval_min - hi, 0.0)
        distances[unit["id"]] = {
            "each_fit_rule_pixels": by_line,
            "nearest_pixels": min(by_line.values()),
        }
    pre = preflight([line["points"] for line in fitting], width, height)
    retained_ids = []
    for points in pre["retained_points"]:
        matches = [line["id"] for line in fitting if line["points"] == points]
        if len(matches) != 1:
            raise ValueError("Native retained trace cannot be uniquely identified")
        retained_ids.append(matches[0])
    pre["retained_ids"] = retained_ids
    repeats = []
    for repeat in record["repeat_pass"]:
        original = next(line for line in lines if line["id"] == repeat["id"])
        original_by_x = {p[0]: p for p in original["points"]}
        if any(p[0] not in original_by_x for p in repeat["points"]):
            raise ValueError("Repeat points must use common declared observation columns")
        pairs = [(original_by_x[q[0]], q) for q in repeat["points"]]
        delta = np.asarray([q[1] - p[1] for p, q in pairs])
        a, b = shape([p for p, _ in pairs]), shape(repeat["points"])
        repeats.append(
            {
                "id": repeat["id"],
                "role": units[original["unit"]]["role"],
                "max_abs_delta_pixels": float(np.max(np.abs(delta))),
                "rms_delta_pixels": float(np.sqrt(np.mean(delta**2))),
                "first_shape": a,
                "repeat_shape": b,
                "rise_difference_pixels": b["rise_pixels"] - a["rise_pixels"],
                "curvature_difference_pixels": b["curvature_peak_to_peak_pixels"]
                - a["curvature_peak_to_peak_pixels"],
            }
        )
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    for unit in units.values():
        if unit["role"] == "evaluation":
            draw.rectangle(unit["exclusion"], outline="magenta", width=3)
    for line in lines:
        color = "blue" if units[line["unit"]]["role"] == "fit" else "red"
        points = [tuple(p) for p in line["points"]]
        # Connecting segments show trace identity, not invented observations.
        draw.line(points, fill=color, width=1)
        for x, y in points:
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), outline=color)
        draw.text((points[0][0] + 4, points[0][1] - 12), line["id"], fill=color)
    overlay.save(artifacts / "separation-overlay.png")
    for band, (lo, hi) in record["detail_bands"].items():
        overlay.crop((150, lo, 1605, hi)).save(artifacts / f"{band}-overlay.png")
    after = {str(p): digest(p) for p in subjects}
    if before != after:
        raise RuntimeError("An instrument/read subject changed during preflight")
    admissible = record["acquisition_admissible"]
    result = {
        "kind": "coordinate-only acquisition diagnostic; no model or correction generated",
        "acquisition_admissible": admissible,
        "outcome": "inconclusive acquisition" if not admissible else "preflight only",
        "acquisition_failure": record.get("acquisition_failure"),
        "preflight": pre,
        "nearest_fit_distances": distances,
        "repeatability": repeats,
        "subjects_before": before,
        "subjects_after": after,
        "record_sha256": digest(RECORD),
        "outputs": {
            n: digest(artifacts / n)
            for n in ["separation-overlay.png"]
            + [f"{band}-overlay.png" for band in record["detail_bands"]]
        },
    }
    (artifacts / "coordinate-report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "native_coordinate_gates_passed": pre["passed"],
                "acquisition_admissible": admissible,
                "guides_eligible_for_fit": bool(admissible and pre["passed"]),
                "retained": pre["retained_count"],
                "report": str(artifacts / "coordinate-report.json"),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument(
        "--source-views",
        action="store_true",
        help="Reproduce observed unmarked displays before preflight; never mark or fit",
    )
    args = parser.parse_args()
    if args.source_views:
        source_views(args.artifacts)
    else:
        run(args.artifacts)
