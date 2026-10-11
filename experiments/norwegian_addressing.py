# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["pillow==11.3.0"]
# ///
"""Fixed-format blind raster-address controls; never baseline ground truth."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SCALE = 16
MARGIN = 64


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grid(patch: Image.Image, output: Path, title: str) -> None:
    """Show each original cell at fixed integer zoom with offset-labelled axes."""
    width, height = patch.size
    result = Image.new("RGB", (width * SCALE + 2 * MARGIN, height * SCALE + 2 * MARGIN), "white")
    result.paste(
        patch.resize((width * SCALE, height * SCALE), Image.Resampling.NEAREST), (MARGIN, MARGIN)
    )
    draw = ImageDraw.Draw(result)
    font = ImageFont.load_default(size=14)
    draw.text((4, 4), title, fill="black", font=font)
    for x in range(width + 1):
        xpos = MARGIN + x * SCALE
        draw.line((xpos, MARGIN, xpos, MARGIN + height * SCALE), fill=(180, 210, 230))
        if x < width and x % 4 == 0:
            draw.text((xpos + 2, MARGIN - 22), str(x), fill="black", font=font)
    for y in range(height + 1):
        ypos = MARGIN + y * SCALE
        draw.line((MARGIN, ypos, MARGIN + width * SCALE, ypos), fill=(180, 210, 230))
        if y < height:
            draw.text((MARGIN - 28, ypos + 1), str(y), fill="black", font=font)
    result.save(output)


def run(artifacts: Path) -> None:
    artifacts.mkdir(parents=True, exist_ok=False)
    subjects = [Path(__file__), ROOT / "Taskfile.yml"]
    before = {str(p): digest(p) for p in subjects}
    # This answer key stays supervisory. Observer packets contain only PNGs and public metadata.
    fixtures = [
        ("A", (315, 180), (0, 0), (7, 3)),
        ("B", (955, 1190), (0, 0), (18, 11)),
        ("C", (210, 2240), (1785, 0), (29, 6)),
    ]
    items = []
    for name, origin, spread_origin, target in fixtures:
        patch = Image.new("RGB", (32, 16), "white")
        x, y = target
        # A tiny blurred asymmetric feature; only one cell has minimum intensity.
        for dx, dy, value in [(-1, 0, 110), (1, 0, 155), (0, -1, 90), (0, 1, 180), (0, 0, 0)]:
            patch.putpixel((x + dx, y + dy), (value, value, value))
        patch.save(artifacts / f"{name}-native.png")
        grid(patch, artifacts / f"{name}-grid.png", f"{name}: patch offsets; 16x nearest-neighbour")
        items.append(
            {
                "id": name,
                "half_origin": origin,
                "spread_origin": spread_origin,
                "target_offset": target,
                "target_native": [origin[0] + x, origin[1] + y],
                "target_spread": [origin[0] + x + spread_origin[0], origin[1] + y],
                "native_sha256": digest(artifacts / f"{name}-native.png"),
                "grid_sha256": digest(artifacts / f"{name}-grid.png"),
            }
        )
    public = {
        "scale": SCALE,
        "patch_dimensions": [32, 16],
        "grid_margin": MARGIN,
        "addressing": (
            "integer source pixel centres, x right/y down; "
            "add patch offset to half origin, then spread origin"
        ),
        "items": [{k: v for k, v in item.items() if not k.startswith("target")} for item in items],
    }
    (artifacts / "packet.json").write_text(json.dumps(public, indent=2) + "\n")
    after = {str(p): digest(p) for p in subjects}
    if before != after:
        raise ValueError("Control instrument changed during generation")
    (artifacts / "answer-key.json").write_text(
        json.dumps({"items": items, "before": before, "after": after}, indent=2) + "\n"
    )
    print(json.dumps(public))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    run(parser.parse_args().artifacts)
