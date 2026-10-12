"""Renderer-independent grid truth and the declared 2:1 native-detail comparator."""

from composition_truth import Truth


def truth(name: str) -> Truth:
    low, high = bytearray(), bytearray()
    for y in range(32):
        for x in range(64):
            if name == "type3-text":
                if y < 16:
                    value = (255, 0, 255) if x < 16 else (0, 255, 255)
                    if x >= 32:
                        value = (0, 255, 0)
                else:
                    ink = x < 16 or (16 <= x < 32 and (x < 20 or x >= 28 or y < 20 or y >= 28))
                    value = (0, 0, 0) if ink else (255, 255, 255)
            elif name in {"matte-white", "matte-black"}:
                alpha = 85 if (x // 8 + y // 8) % 2 == 0 else 170
                value = (alpha, 0, 255 - alpha)
            elif name == "screen-group":
                value = (255, 0, 255) if x < 32 else (0, 0, 255)
            elif name == "600-ppi-detail":
                # Two native samples fit each destination pixel. Do not promise
                # a resampling filter in the fine band or at macro boundaries.
                # Macro interiors (>=2 source pixels from each edge) stay exact.
                if x <= 32 or x in {47, 48}:
                    low.extend(b"\0" * 3)
                    high.extend(b"\xff" * 3)
                    continue
                value = (0, 0, 0) if x < 47 else (255, 255, 255)
            else:
                raise ValueError(name)
            low.extend(value)
            high.extend(value)
    return Truth((64, 32), bytes(low), bytes(high), name == "600-ppi-detail")


def detail_loss(
    size: tuple[int, int], rgb: bytes, native_size: tuple[int, int], native: bytes
) -> dict[str, int]:
    """Compare constant baseline texels at the aligned 2x source sample centres.

    This specific zero-order reconstruction supplies no perceptual or general
    interpolation bound. Differing adjacent source values cannot both equal
    their one baseline texel. A measured mismatch is intentional signed-ceiling
    loss only for this known-by-construction unfiltered grayscale source.
    """
    width, height = size
    nw, nh = native_size
    assert width > 0 and height > 0 and (nw, nh) == (2 * width, 2 * height), "2:1 mapping"
    assert len(rgb) == width * height * 3 and len(native) == nw * nh, "sample length"
    changed = 0
    for y in range(nh):
        for x in range(nw):
            i = ((y // 2) * width + x // 2) * 3
            changed += rgb[i : i + 3] != bytes([native[y * nw + x]]) * 3
    return {"native_pixels": nw * nh, "changed_native_pixels": changed}
