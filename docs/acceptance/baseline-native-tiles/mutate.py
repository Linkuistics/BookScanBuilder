import hashlib, json, subprocess, sys
from pathlib import Path

target = Path("src/bookscan/native_tiles.py")
original = target.read_text()
digest = hashlib.sha256(original.encode()).hexdigest()
mutants = {
 "crop-x-shifted": ("rgb[((region.y + y) * width + region.x) * 3 :][:row]", "rgb[((region.y + y) * width + region.x + 1) * 3 :][:row]"),
 "crop-y-shifted": ("rgb[((region.y + y) * width + region.x) * 3 :][:row]", "rgb[((region.y + y + 1) * width + region.x) * 3 :][:row]"),
 "crop-row-too-narrow": ("row = region.width * 3", "row = (region.width - 1) * 3"),
 "stride-ignores-width": ("rgb[((region.y + y) * width + region.x) * 3 :][:row]", "rgb[((region.y + y) * region.width + region.x) * 3 :][:row]"),
 "tile-transposed": ('"RGB", (region.width, region.height), _region_bytes(rgb, size, region)', '"RGB", (region.height, region.width), _region_bytes(rgb, size, region)'),
 "density-ignores-scale": ("return 72.0 * scale", "return 72.0"),
 "bool-scale-accepted": ("if isinstance(scale, bool) or not isinstance(scale, int | float):", "if not isinstance(scale, int | float):"),
 "nonfinite-scale-accepted": ("if not math.isfinite(scale) or scale <= 0:", "if scale <= 0:"),
 "zero-scale-accepted": ("if not math.isfinite(scale) or scale <= 0:", "if not math.isfinite(scale):"),
 "region-bounds-right-unchecked": ("or region.x + region.width > width\n", "\n"),
 "region-bounds-bottom-unchecked": ("or region.y + region.height > height\n", "\n"),
 "region-empty-allowed": ("region.width <= 0\n        or region.height <= 0\n        or region.x < 0", "region.x < 0"),
 "buffer-length-unchecked": ("or len(rgb) != width * height * 3", ""),
 "verify-pixels-unchecked": ("if decoded != _region_bytes(rgb, size, region):", "if False:"),
 "verify-mode-unchecked": ('if image.mode != "RGB":', "if False:"),
 "verify-size-unchecked": ("if image.size != (region.width, region.height):", "if False:"),
 "ruler-bands-not-single-pixel": ("fill=\"black\" if x % 2 == 0 else \"white\")\n        for y", "fill=\"black\" if x % 4 < 2 else \"white\")\n        for y"),
 "ruler-frame-wrong-size": ("draw.rectangle((64, 64, 575, 415), fill=\"red\")", "draw.rectangle((64, 64, 574, 415), fill=\"red\")"),
}
results = {}
try:
    for name, (old, new) in mutants.items():
        assert original.count(old) == 1, (name, original.count(old))
        target.write_text(original.replace(old, new))
        run = subprocess.run(["uv", "run", "--locked", "pytest", "-q", "-x", "tests/test_native_tiles.py"], capture_output=True, text=True)
        results[name] = {"killed": run.returncode != 0, "tail": run.stdout.strip().splitlines()[-1] if run.stdout.strip() else ""}
        print(name, "KILLED" if run.returncode != 0 else "SURVIVED", flush=True)
finally:
    target.write_text(original)
assert hashlib.sha256(target.read_text().encode()).hexdigest() == digest
print("restored", digest[:12])
json.dump(results, sys.stdout, indent=1)
