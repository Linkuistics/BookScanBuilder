# Native PNG tiles and packet pixel ruler (finite baseline, milestone 3)

Product module: `src/bookscan/native_tiles.py`. Tests: `tests/test_native_tiles.py`
(task `process:native-tiles-check`, 19 cases). Pure bytes: no project, packet
directory, renderer or viewer is consulted.

## What it fixes

- **Exact lossless tile.** `tile_png(rgb, size, region, backing_scale)` encodes exactly
  the region's baseline pixels as an 8-bit RGB PNG whose only chunks are IHDR, pHYs,
  IDAT and IEND (parsed byte by byte in the tests, CRCs checked). Every tile kind of a
  1700x900 baseline (full, right edge, bottom edge, corner) equals hand-indexed pixels,
  and the whole `partition()` reassembles to the baseline.
- **Density is metadata.** pHYs is `72 x backing_scale` dpi from a caller-supplied
  *measured* scale (1.0 -> 2835, 2.0 -> 5669 pixels per metre). Zero, negative, NaN,
  infinite, boolean and non-numeric scales are refused. The module makes no claim that a
  viewer shows one device pixel per project pixel; that stays with the ruler and an
  observed framebuffer measurement.
- **Deterministic.** Identical inputs give identical bytes, so tiles can be content
  addressed in a packet descriptor.
- **Ruler.** `ruler_png(scale)` is byte-identical to `tests/native_view_scale.write_ruler`,
  the construction the measurement instrument rejected a wrong zoom on and accepted
  Actual Size for (`docs/acceptance/baseline-native-probe`). The product therefore ships
  the validated ruler, not a lookalike.
- **Read-back.** `verify_tile_png()` decodes a tile and requires format, mode, size and
  pixels to equal the saved baseline region (`TileError` otherwise).

## Not done here

Packet layout/PDFs/headers, descriptor storage, the actual Preview/framebuffer
demonstration of a real packet tile, and any native-usability claim.

## Checks

`mutate.py` applies 18 single-edit guard mutations (crop offsets/stride/width/height,
transposition, density ignoring scale, scale validation, region bounds, buffer length,
verify pixel/mode/size, ruler band pitch and frame size). All 18 fail at least one test.
Three first-reading survivors were resolved: a redundant early scale check in
`ruler_png` (the encoder checks it) was removed; a bottom-edge bounds case and a
size-specific verify message were added to the tests.
