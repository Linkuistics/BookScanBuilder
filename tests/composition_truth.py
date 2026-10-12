"""Independent, predeclared per-pixel channel bounds for construction fidelity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Truth:
    size: tuple[int, int]
    low: bytes
    high: bytes
    grey: bool = False


def compare(size: tuple[int, int], rgb: bytes, truth: Truth) -> dict[str, int]:
    assert size == truth.size, "pixel extent"
    length = size[0] * size[1] * 3
    assert len(rgb) == length, "RGB length"
    assert len(truth.low) == len(truth.high) == length, "truth length"
    assert all(lo <= hi for lo, hi in zip(truth.low, truth.high)), "inverted truth"
    exact = 0
    for start in range(0, length, 3):
        values = rgb[start : start + 3]
        if truth.grey:
            assert values[0] == values[1] == values[2], f"pixel {start // 3} grey neutrality"
        for channel, value in enumerate(values):
            i = start + channel
            assert truth.low[i] <= value <= truth.high[i], (
                f"pixel {start // 3} channel {channel}: {value} outside "
                f"[{truth.low[i]}, {truth.high[i]}]"
            )
        exact += truth.low[start : start + 3] == truth.high[start : start + 3]
    return {"exact_pixels": exact, "bounded_pixels": length // 3 - exact}
