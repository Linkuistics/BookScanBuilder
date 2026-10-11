# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["pillow==11.3.0", "numpy==2.2.6"]
# ///
"""Reproduce the bounded, disposable page-geometry-k4 experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
GUIDES = ROOT / "experiments/page_geometry_guides.json"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout + result.stderr


def subjects(collection: Path) -> list[Path]:
    guides = json.loads(GUIDES.read_text())
    return [
        Path(__file__).resolve(),
        GUIDES,
        ROOT / "experiments/page_geometry.c",
        ROOT / "Taskfile.yml",
        *[collection / guides[name]["source"] for name in ("music", "control")],
    ]


def render(output: Path, collection: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    guides = json.loads(GUIDES.read_text())
    before = {str(p): digest(p) for p in subjects(collection)}
    commands = []
    for name in ("music", "control"):
        spec = guides[name]
        source = collection / spec["source"]
        if digest(source) != spec["source_sha256"]:
            raise ValueError(f"Source differs from marked fixture: {source}")
        command = [
            "pdftoppm",
            "-f",
            str(spec["page"]),
            "-l",
            str(spec["page"]),
            "-singlefile",
            "-r",
            "300",
            "-png",
            str(source),
            str(output / name),
        ]
        commands.append({"argv": command, "log": run(command)})
        with Image.open(output / f"{name}.png") as image:
            if list(image.size) != spec["dimensions"]:
                raise ValueError(f"Unexpected fixture dimensions: {name}, {image.size}")
    after = {str(p): digest(p) for p in subjects(collection)}
    if before != after:
        raise ValueError("A rendering subject changed during measurement")
    save(
        output / "render.json",
        {
            "before": before,
            "after": after,
            "commands": commands,
            "poppler": run(["pdftoppm", "-v"]),
            "dpi": 300,
            "canvas": "full default MediaBox, no crop, scale, cleanup or object extraction",
            "upsampling": (
                "Music has mixed PDF objects, including 150-ppi colour and 300-ppi stencil; "
                "300-dpi rendering adds no original detail"
            ),
        },
    )


def mark(output: Path) -> None:
    if (output / "frozen.json").exists():
        raise ValueError("Already frozen; choose a fresh artifact directory")
    specs: dict[str, Any] = json.loads(GUIDES.read_text())
    freeze: dict[str, Any] = {
        "guide_sha256": digest(GUIDES),
        "guide_record": specs,
        "render_report_sha256": digest(output / "render.json"),
        "pages": {},
    }
    for name in ("music", "control"):
        with Image.open(output / f"{name}.png") as image:
            rgb = image.convert("RGB")
        annotation = rgb.copy()
        draw = ImageDraw.Draw(annotation)
        analysis = rgb.convert("L")
        mask = Image.new("L", rgb.size, 0)
        md = ImageDraw.Draw(mask)
        ad = ImageDraw.Draw(analysis)
        for line in specs[name]["lines"]:
            points = [tuple(point) for point in line["points"]]
            colour = "red" if line["role"] == "evaluation" else "blue"
            draw.line(points, fill=colour, width=2)
            for x, y in points:
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), outline=colour, width=2)
            draw.text(points[0], line["id"], fill=colour)
            if line["role"] == "evaluation":
                box = tuple(line["exclude"])
                md.rectangle(box, fill=255)
                ad.rectangle(box, fill=255)
                if not all(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in points):
                    raise ValueError("Holdout does not include marked points")
        for vertical in specs[name].get("verticals", []):
            draw.line([tuple(p) for p in vertical["points"]], fill="green", width=2)
        for label, box in specs[name]["crops"].items():
            draw.rectangle(tuple(box), outline="purple", width=2)
            draw.text(tuple(box[:2]), label, fill="purple")
        annotation.save(output / f"{name}-marked.png")
        analysis.save(output / f"{name}-analysis.png")
        mask.save(output / f"{name}-exclusion.png")
        freeze["pages"][name] = {
            "source_sha256": specs[name]["source_sha256"],
            "dimensions": list(rgb.size),
            "files": {
                suffix: digest(output / f"{name}{suffix}.png")
                for suffix in ("", "-marked", "-analysis", "-exclusion")
            },
        }
    save(output / "frozen.json", freeze)
    (output / "frozen.sha256").write_text(digest(output / "frozen.json") + "\n")
    print("Frozen unchanged reference guides:", digest(output / "frozen.json"))


def residual(points: list[list[float]]) -> dict[str, float]:
    a = np.asarray(points, dtype=float)
    x, y = a[:, 0], a[:, 1]
    slope, intercept = np.polyfit(x, y, 1)
    errors = y - (slope * x + intercept)
    return {
        "slope_degrees": math.degrees(math.atan(float(slope))),
        "end_to_end_rise_pixels": float(y[-1] - y[0]),
        "curvature_peak_to_peak_pixels": float(np.ptp(errors)),
        "rms_to_straight_line_pixels": float(np.sqrt(np.mean(errors**2))),
    }


def mapped(points: list[list[float]], field: np.ndarray) -> list[list[float]]:
    # Invert the declared backward field independently, at each marked x.
    result = []
    rows = np.arange(field.shape[0], dtype=float)
    for x, y in points:
        source_y = rows - field[:, round(x)]
        if np.any(np.diff(source_y) <= 0):
            raise ValueError("Non-monotone vertical map at evaluation guide")
        result.append([x, float(np.interp(y, source_y, rows))])
    return result


def compare(output: Path, collection: Path, binary: Path) -> None:
    frozen = output / "frozen.json"
    freeze_hash = digest(frozen)
    if freeze_hash != (output / "frozen.sha256").read_text().strip():
        raise ValueError("Frozen coordinate record changed")
    freeze = json.loads(frozen.read_text())
    if freeze["guide_sha256"] != digest(GUIDES):
        raise ValueError("Authoritative guides changed after freeze")
    if freeze["render_report_sha256"] != digest(output / "render.json"):
        raise ValueError("Rendering provenance changed")
    for name, record in freeze["pages"].items():
        for suffix, expected in record["files"].items():
            if digest(output / f"{name}{suffix}.png") != expected:
                raise ValueError("A frozen input image changed")
    measured = subjects(collection) + [binary, frozen, output / "frozen.sha256"]
    measured += [
        output / f"{name}{suffix}.png"
        for name in ("music", "control")
        for suffix in ("", "-marked", "-analysis", "-exclusion")
    ]
    before = {str(p): digest(p) for p in measured}
    specs = freeze["guide_record"]
    report: dict[str, Any] = {
        "before": before,
        "frozen_sha256_before": freeze_hash,
        "settings": {
            "threshold": 180,
            "sampling": 30,
            "reduction": 1,
            "minlines": 15,
            "short_line_fraction": 0.8,
            "horizontal": False,
            "neighbours": False,
            "white_outside": 255,
        },
        "pages": {},
        "logs": {},
    }
    for name in ("music", "control"):
        target = output / f"{name}-fit"
        target.mkdir()
        command = [
            str(binary),
            str(output / f"{name}.png"),
            str(output / f"{name}-analysis.png"),
            str(target),
            "fit",
        ]
        report["logs"][name] = {"argv": command, "log": run(command)}
        status = json.loads((target / "status.json").read_text())
        detected = json.loads((target / "fitting-lines.json").read_text())
        with Image.open(output / f"{name}-exclusion.png") as im:
            exclusion = np.asarray(im)
        violations = []
        for index, line in enumerate(detected):
            for x, y in line:
                if exclusion[round(y), round(x)]:
                    violations.append([index, x, y])
        report["pages"][name] = {
            "status": status,
            "holdout_fit_violations": violations,
            "lines": [],
            "verticals": [],
        }
        if violations:
            raise ValueError("Detected fitting line entered evaluation exclusion")
        with Image.open(output / f"{name}.png") as im:
            source = np.asarray(im.convert("RGB"))
        field = None
        if status["vvalid"] and status["apply_return"] == 0:
            field = np.fromfile(target / "field.bin", dtype="=f4").reshape(source.shape[:2])
            report["pages"][name]["field_range_pixels"] = [float(field.min()), float(field.max())]
            lo, hi = float(field.min()), float(field.max())
            Image.fromarray(np.uint8((field - lo) / max(hi - lo, 1e-6) * 255)).save(
                target / "field-view.png"
            )
        angle = math.radians(status["angle_degrees"])
        w, h = status["width"], status["height"]
        for line in specs[name]["lines"]:
            if line["role"] != "evaluation":
                continue
            points = line["points"]
            rigid = [
                [
                    (x - w / 2) * math.cos(angle) - (y - h / 2) * math.sin(angle) + w / 2,
                    (x - w / 2) * math.sin(angle) + (y - h / 2) * math.cos(angle) + h / 2,
                ]
                for x, y in points
            ]
            item = {
                "id": line["id"],
                "unchanged": residual(points),
                "rigid": residual(rigid),
                "candidate": residual(mapped(points, field)) if field is not None else None,
                "candidate_points": mapped(points, field) if field is not None else None,
            }
            report["pages"][name]["lines"].append(item)
        if field is not None:
            for vertical in specs[name].get("verticals", []):
                report["pages"][name]["verticals"].append(
                    {
                        "id": vertical["id"],
                        "before": vertical["points"],
                        "after": mapped(vertical["points"], field),
                    }
                )
        fitting_overlay = Image.fromarray(source)
        draw = ImageDraw.Draw(fitting_overlay)
        for line in detected:
            draw.line([tuple(p) for p in line], fill="blue", width=2)
        fitting_overlay.save(target / "fitting-overlay.png")
        for label, box in specs[name]["crops"].items():
            for variant, path in (
                ("unchanged", output / f"{name}.png"),
                ("rigid", target / "rigid.png"),
                ("candidate", target / "candidate.png"),
            ):
                with Image.open(path) as image:
                    image.crop(tuple(box)).save(target / f"{label}-{variant}.png")
        if name == "control":
            shutil.copyfile(output / "control.png", output / "control-policy.png")
            report["pages"][name]["trial_policy_pixels_unchanged"] = digest(
                output / "control.png"
            ) == digest(output / "control-policy.png")
    # If withholding invalidates music's fit, distinguish that limitation from
    # failure on the full input. This has no held-out evaluation claim.
    if not report["pages"]["music"]["status"]["vvalid"]:
        target = output / "music-full-input-diagnostic"
        target.mkdir()
        report["logs"]["full_input_diagnostic"] = run(
            [str(binary), str(output / "music.png"), str(output / "music.png"), str(target), "fit"]
        )
        report["music_full_input_diagnostic"] = {
            "status": json.loads((target / "status.json").read_text()),
            "held_out_evidence": False,
            "purpose": (
                "Distinguish holdout-induced model failure from full-input extraction failure"
            ),
        }
    target = output / "control-diagnostic"
    target.mkdir()
    report["logs"]["diagnostic"] = run(
        [
            str(binary),
            str(output / "control.png"),
            str(output / "control-analysis.png"),
            str(target),
            "diagnostic",
        ]
    )
    with Image.open(output / "control.png") as im:
        source = np.asarray(im.convert("RGB"))
    with Image.open(target / "candidate.png") as im:
        native = np.asarray(im.convert("RGB"))
    h, w = source.shape[:2]
    field = np.fromfile(target / "field.bin", dtype="=f4").reshape(h, w)
    rows, cols = np.indices((h, w))
    formula = 2.25 * np.sin(2 * np.pi * cols / (w - 1)) * np.sin(np.pi * rows / (h - 1))
    # C evaluates (int row - float field) in float32, then adds double 0.5.
    # A float64 subtraction crosses a few half-row boundaries differently.
    coordinates = rows.astype(np.float32) - field
    rounded = np.trunc(coordinates.astype(np.float64) + 0.5).astype(int)
    valid = (rounded >= 0) & (rounded < h)
    expected = np.full_like(source, 255)
    expected[valid] = source[rounded[valid], cols[valid]]
    diagnostic: dict[str, Any] = {
        "declared_parameters": specs["control"]["diagnostic"],
        "formula_max_error_pixels": float(np.max(np.abs(formula - field))),
        "native_vs_independent_sampler_mismatched_channels": int(
            np.count_nonzero(native != expected)
        ),
        "nonidentity_rounded_coordinates": int(np.count_nonzero(rounded != rows)),
        "out_of_bounds_pixels": int(np.count_nonzero(~valid)),
        "crops": {},
    }
    for label, box in specs["control"]["crops"].items():
        x0, y0, x1, y1 = box
        region = np.s_[y0:y1, x0:x1]
        nonidentity = int(np.count_nonzero(rounded[region] != rows[region]))
        diagnostic["crops"][label] = {
            "nonidentity_rounded_coordinates": nonidentity,
            "fractional_coordinates": int(
                np.count_nonzero(np.abs(coordinates[region] - np.rint(coordinates[region])) > 0.001)
            ),
            "displacement_range": [float(field[region].min()), float(field[region].max())],
            "centre_mapping": [
                int(cols[region][0, 0]),
                int(rows[region][0, 0]),
                float(coordinates[region][0, 0]),
                int(rounded[region][0, 0]),
            ],
        }
        if label != "edge" and not nonidentity:
            raise ValueError("Diagnostic detail crop bypasses rounded sampler")
        Image.fromarray(source[region]).save(target / f"{label}-unchanged.png")
        Image.fromarray(native[region]).save(target / f"{label}-diagnostic.png")
    # Ordinary viewable field image; binary field retains exact float32 values.
    Image.fromarray(np.uint8((field + 2.25) / 4.5 * 255)).save(target / "field-view.png")
    if diagnostic["native_vs_independent_sampler_mismatched_channels"]:
        raise ValueError("Native sampler differs from intended mapping")
    report["diagnostic"] = diagnostic
    after = {str(p): digest(p) for p in measured}
    report["after"] = after
    report["frozen_sha256_after"] = digest(frozen)
    if before != after:
        raise ValueError("A measurement subject changed")
    report["limitations"] = [
        "Residuals transport frozen source points through the fields; "
        "not re-marked output ground truth.",
        "Control is approximately straight at marker precision, not a certified flat original.",
        "Holdout masks can make automatic fitting inconclusive. "
        "No full-input evidence is silently substituted.",
        "Sampler agreement proves declared integer-row mapping, "
        "not absence of visual sampling damage.",
        "No numerical score is human acceptance. Inspect native crops, complete pages and borders.",
    ]
    save(output / "comparison.json", report)
    print(
        json.dumps(
            {
                "pages": {n: p["status"] for n, p in report["pages"].items()},
                "diagnostic": diagnostic,
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("render", "mark", "compare"))
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--collection", type=Path, default=Path("/Volumes/Glass/Book Conversion"))
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()
    if args.operation == "render":
        render(args.artifacts, args.collection)
    elif args.operation == "mark":
        mark(args.artifacts)
    else:
        if args.binary is None:
            parser.error("compare requires --binary (run task geometry:build)")
        compare(args.artifacts, args.collection, args.binary.resolve())


if __name__ == "__main__":
    main()
