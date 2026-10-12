"""Test-owned ruler construction/measurement; captures come from the actual viewer.

This checks pixel geometry, not colour fidelity or any PDF/renderer mechanism.
It never captures the screen, launches a viewer or changes viewer settings.
"""

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw

type Rectangle = tuple[int, int, int, int]
type Size = tuple[int, int]


@dataclass(frozen=True)
class Measurement:
    passed: bool
    capture_size: Size
    expected_framebuffer_size: Size
    content_region: Rectangle
    frame: Rectangle | None
    horizontal_scale: float | None
    vertical_scale: float | None
    horizontal_samples: int
    vertical_samples: int
    failures: tuple[str, ...]


def write_ruler(path: Path, backing_scale: float) -> None:
    """Write an unused PNG at the hypothesised density, without sampling."""
    if not math.isfinite(backing_scale) or backing_scale <= 0:
        raise ValueError("backing scale must be the measured finite positive screen scale")
    with Image.new("RGB", (640, 480), "white") as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle((64, 64, 575, 415), fill="red")
        draw.rectangle((65, 65, 574, 414), fill="white")
        for x in range(96, 544):
            draw.line((x, 96, x, 159), fill="black" if x % 2 == 0 else "white")
        for y in range(192, 384):
            draw.line((96, y, 159, y), fill="black" if y % 2 == 0 else "white")
        for x in range(192, 545, 32):
            draw.line((x, 240, x, 304), fill="black")
        # Pillow 12.3 PNG dpi is metadata: it does not establish viewer scale.
        # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#png
        with path.open("xb") as output:
            image.save(output, format="PNG", dpi=(72 * backing_scale, 72 * backing_scale))


def _pixel(data: bytes, width: int, x: int, y: int) -> tuple[int, int, int]:
    offset = (y * width + x) * 3
    return data[offset], data[offset + 1], data[offset + 2]


def _bands_match(data: bytes, width: int, region: Rectangle, horizontal: bool) -> bool:
    left, top, right, bottom = region
    for y in range(top, bottom):
        for x in range(left, right):
            channels = _pixel(data, width, x, y)
            dark = ((x - left) if horizontal else (y - top)) % 2 == 0
            # Predeclared classification permits lossy capture, never a colour-fidelity pass.
            if dark and max(channels) > 64 or not dark and min(channels) < 192:
                return False
    return True


def measure(path: Path, content_region: Rectangle, framebuffer_size: Size) -> Measurement:
    """Check a complete ruler against construction truth and independent window size."""
    with Image.open(path) as capture, capture.convert("RGB") as rgb:
        width, height = rgb.size
        data = rgb.tobytes()
    left, top, right, bottom = content_region
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError("content region must be a nonempty half-open rectangle inside the capture")
    if min(framebuffer_size) <= 0:
        raise ValueError("framebuffer size must be positive and measured independently")
    failures: list[str] = []
    if (width, height) != framebuffer_size:
        failures.append("capture dimensions differ from independently measured framebuffer window")
    frame_left, frame_top, frame_right, frame_bottom = width, height, -1, -1
    for y in range(top, bottom):
        for x in range(left, right):
            red, green, blue = _pixel(data, width, x, y)
            if red - green > 40 and red - blue > 40 and green < 240:
                frame_left, frame_top = min(frame_left, x), min(frame_top, y)
                frame_right, frame_bottom = max(frame_right, x), max(frame_bottom, y)
    frame: Rectangle | None = None
    horizontal_scale: float | None = None
    vertical_scale: float | None = None
    horizontal_samples = vertical_samples = 0
    if frame_right == -1:
        failures.append("no complete red construction ruler detected in the content region")
    else:
        frame = frame_left, frame_top, frame_right + 1, frame_bottom + 1
        horizontal_scale = (frame_right + 1 - frame_left) / 512
        vertical_scale = (frame_bottom + 1 - frame_top) / 352
        if (frame_right + 1 - frame_left, frame_bottom + 1 - frame_top) != (512, 352):
            failures.append("ruler frame is not 512 by 352 framebuffer pixels")
        else:
            horizontal = frame_left + 32, frame_top + 32, frame_left + 480, frame_top + 96
            vertical = frame_left + 32, frame_top + 128, frame_left + 96, frame_top + 320
            if _bands_match(data, width, horizontal, True):
                horizontal_samples = 448 * 64
            else:
                failures.append("horizontal one-pixel bands are scaled, blurred or changed")
            if _bands_match(data, width, vertical, False):
                vertical_samples = 64 * 192
            else:
                failures.append("vertical one-pixel bands are scaled, blurred or changed")
    return Measurement(
        not failures,
        (width, height),
        framebuffer_size,
        content_region,
        frame,
        horizontal_scale,
        vertical_scale,
        horizontal_samples,
        vertical_samples,
        tuple(failures),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Construct/measure a native-view ruler; never operates the viewer.",
        epilog=(
            "Exits: 0 generated/passed, 1 measurement/I/O failure, 2 invalid arguments. "
            "Read the native-view procedure before crediting a capture. No overwrite."
        ),
    )
    commands = parser.add_subparsers(dest="operation", required=True)
    generate = commands.add_parser(
        "generate",
        help="write an unused 640x480 PNG; supply the observed backing scale",
        epilog="Example: native_view_scale.py generate --output ruler.png --backing-scale 1",
    )
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--backing-scale", type=float, required=True)
    check = commands.add_parser(
        "measure",
        help="emit one JSON geometry result from original capture bytes",
        epilog=(
            "Example: native_view_scale.py measure capture.jpg --region 0 80 708 584 "
            "--framebuffer-size 708 584"
        ),
    )
    check.add_argument("capture", type=Path)
    check.add_argument("--region", type=int, nargs=4, required=True)
    check.add_argument("--framebuffer-size", type=int, nargs=2, required=True)
    args = parser.parse_args()
    try:
        if args.operation == "generate":
            output = Path(str(args.output))
            write_ruler(output, float(args.backing_scale))
            print(json.dumps({"output": str(output), "sha256": _digest(output)}))
            return 0
        capture = Path(str(args.capture))
        region = tuple(int(value) for value in args.region)
        size = tuple(int(value) for value in args.framebuffer_size)
        result = measure(capture, (region[0], region[1], region[2], region[3]), (size[0], size[1]))
        print(json.dumps({"capture_sha256": _digest(capture), **asdict(result)}))
        return 0 if result.passed else 1
    except (OSError, ValueError) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        print(
            "Use an unused output or complete original capture and measured region/size.",
            file=sys.stderr,
        )
        return 1


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
