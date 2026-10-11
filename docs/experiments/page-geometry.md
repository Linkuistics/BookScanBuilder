# Two-page geometry trial

The automatic Leptonica 1.87.0 text-line extractor **cannot produce a valid
vertical model for this music fixture with these settings**. The held-out fit
found four long lines and the separately labelled full-input diagnostic found
one; both fell below the unchanged minimum of fifteen. Both candidate PNGs are
exact unchanged RGB copies, not corrections. Recommend rejecting this automatic
candidate for the fixture. The held-out test by itself is inconclusive about the
full-input candidate; the separate full-input failure supplies the extraction
failure evidence. No production algorithm, review technology or first test book
is selected, and failure establishes nothing against all line-guided methods.

The human geometry and preparation responses were requested but were unavailable
during this session. Their visual dispositions are **inconclusive**, separately;
automatic copying/sampler checks cannot establish either approval.

## Evidence and ordinary comparisons

Artifacts live outside the authoritative collection at
`/private/tmp/bookscan-geometry-k4-final`. Open `geometry-review.pdf` (12 pages)
and `preparation-review.pdf` (16 pages). These convenience PDFs embed native RGB
pixels with lossless compression; their manifests verify each decoded image
stream against its PNG. All columns have the same pixel scale. Original complete
PNG pages, native crops and masks are also ordinary image files in that directory.
No source file was rewritten. Preparation pairs come from the current working
command's `/private/tmp/bookscan-prepared-k19-all` acceptance run, not the
historical dependency-copy experiment.

Durable machine-readable evidence:

- [Final comparison report](page-geometry-report.json): commands, library logs,
  model status, detected-fit exclusion check, per-line residuals, actual field
  ranges, diagnostic source coordinates, settings and before/after subjects.
- [Final frozen coordinate record](page-geometry-frozen.json): unchanged render
  and annotation/mask digests, source identities, guide roles and coordinates.
- [Initial pre-output record](page-geometry-initial-guides.json): proves the
  independent marking preceded any deskew/candidate inspection. Every guide
  point, crop and image/mask digest agrees with the final freeze. Only the
  diagnostic arithmetic description was clarified after the checker defect.
- [Retained manual coordinates](../../experiments/page_geometry_guides.json).

The final frozen record's SHA-256 is
`4d718063df70d4ac59cfdb36fe471acda11ee9ef0d4022d070e31110fb928cb2`
before and after evaluation. All measured subjects were rehashed afterward and
matched: C/Python wrappers, coordinate JSON, Taskfile, compiled binary, original
PDFs, frozen record/hash and unchanged/marked/analysis/exclusion PNGs. The report
retains every individual path and digest. There was one writer and no instrument
edit during this measurement. Earlier v2 failed the independent sampler check;
it is not the final measurement. v3 succeeded before the final lint-only edit,
and final was rerun with the finished instrument. No guide or diagnostic field
parameter was tuned after output inspection.

## Inputs and guide marking

Full-page Poppler 26.10.0 renders, default MediaBox at 300 dpi, PNG/RGB:

| Source, relative to `/Volumes/Glass/Book Conversion` | PDF page | Pixels | SHA-256 |
| --- | --- | --- | --- |
| `Raw Scans/Fundamentals of Musical Composition.pdf` | 140, printed 126 | 1720 × 2459 | `3235a842d619a18b11e2fbdb3b5b6666adeb223959cafd4b1d67f27f0dbfe780` |
| `Processed Books/Algorithm Design/Algorithm Design.pdf` | 20, printed xx | 2350 × 2721 | `b9d6f1fd08560f06ec8653375a5866dbe1ba971d780dfecd1a0211fb2f66deab` |

Source and output digest records agree before/after. Whole-page rendering retains
music's mixed colour-image/stencil composition; selecting only an image object
would not. Rendering the colour image at 300 dpi adds no original detail to its
150-ppi data. No whitening, denoising, cropping, horizontal correction or lossy
recompression was applied to the trial image.

Codex identified printed staff rules and text baselines on unchanged full-page
and native crops, then marked independent points before generating any output.
The JSON records marker/method, top-left pixel-centre origin, native pixel units,
line identities, points, fit/evaluation roles, physical exclusions, vertical
barlines and crops. Red marks are evaluation, blue are fit references, green
are vertical references and purple are crop boxes. Evaluation samples span
upper/middle/lower and left/centre/right content; margins remain visible.
Music point uncertainty is roughly ±1 pixel on unobscured rules, ±2 near notation.
Control word-patch modal bottom rows exclude descenders; their sampled baselines
vary by 0–1.5 pixels, so this is an approximately straight control at marking
precision, not a certified flat source.

Every evaluation line's full visible extent is covered by a conservative
rectangular exclusion in the disposable grayscale fitting image. Nearby rules
can be removed too. The retained RGB page is untouched. `*-exclusion.png`,
`*-analysis.png`, `*-fit/binary.png`, `fitting-lines.json` and
`fitting-overlay.png` expose this separation. No detected fitting point entered
an evaluation exclusion on either page. Model fitting uses those same automatic
centres and 0.8 longest-line filtering. Manual blue references are diagnostics,
not a replacement manual estimator.

## Model, geometry and sampler findings

A per-page model uses binary threshold 180, sampling 30, reduction 1, minimum
15 long lines and default model-validity tests. No neighbouring page exists.
`useboth=0` disables horizontal application; the library builder can still
compute an unused horizontal array. No validity rule was weakened. `model.dew`
and exact `field.fpix`/native float32 `field.bin` are retained when available.
The wrapper saves the actual field before the library minimizes it.

| Page/run | Long lines | Vertical build / validity | Interpretation |
| --- | --- | --- | --- |
| Music held-out | 4 | failed / invalid | Unsupported; candidate is unchanged copy. |
| Music full-input diagnostic | 1 | failed / invalid | Extraction failure also occurs without exclusions; no held-out claim. |
| Control held-out | 32 | built / valid | Field ranges −0.509 to +4.848 pixels; no music evidence. |

The rigid baseline estimates skew on the same masked binary image and applies
Leptonica RGB area-map rotation with white fill, same dimensions. Music rotation
is +0.84375°; control is −0.015625°. Marked staff slopes range from −0.628° to
−0.941° before deskew and +0.215° to −0.097° afterward. Thus a global angle does
not make every marked rule horizontal. Curvature peak-to-peak is about 0.6–1.3
pixels, close to marking uncertainty; these observations do not diagnose the
acquisition mechanism or prove a required nonlinear family.

Residuals transport the frozen source points through the declared fields; they
are **not independently re-marked output ground truth**. Because music has no
valid field, there is no held-out music improvement, displacement or local-shape
claim. Its copies retain identical staff spacing, barlines, stems, dots, faint
marks, glyph widths, margins and pixels. The rigid output retains the printed
content inside its generous margins, but moves scanner borders and creates
white corner wedges on the fixed canvas. Review both full page and crops for
rotation sampling damage; that is not a successful automatic warp.

The control's valid fit changes very little in the sampled content and slightly
increases the lower marked curvature residual (0.45 to 0.83 pixels). That is
within marker uncertainty, not evidence for mandatory correction. The declared
trial policy keeps the verified control exactly unchanged, byte for byte. No
production confidence threshold or control policy was derived.

A separate **forced sampler diagnostic** on the control uses the predeclared
smooth field `d = 2.25 sin(2πx/(w−1)) sin(πy/(h−1))` and reads source `(x,y−d)`.
It is deliberate deformation, not a fitted correction. The native RGB sampler
uses integer rows from C `trunc(float32(y−d) + double(0.5))` with white outside.
[Leptonica's sampler source](https://github.com/DanBloomberg/leptonica/blob/1.87.0/src/dewarp3.c)
was checked against the installed version's observed pixel output. The diagnostic
alone explicitly injects a valid model/field; it does not relax real-fit validity.
A square full field prevents its recreation through the native size check.

The actual field agrees with the analytic field to 1.2×10⁻⁷ pixels. An independent
RGB sampler reproduces every native output channel exactly. There are 4,145,240
nonidentity rounded mappings; upper/middle/lower detail crops exercise 21,811,
44,604 and 64,800 nonidentity coordinates respectively, alongside fractional
source coordinates. No diagnostic read falls outside the image. Exact field,
source-coordinate examples and range per crop are in the report. The edge crop's
small displacement rounds to identity and is explicitly not a sampler-detail
control. Pixel-row rounding is visible in the diagnostic: geometry deliberately
shifts by 1–2 rows and can step between adjacent columns. Agreement with the
intended mapping establishes implementation semantics, not freedom from
thin-detail damage. Human inspection of the diagnostic crops remains required.

## Reproduce and retained dependencies

```sh
task geometry:setup
task geometry:build
# Must be a new external directory, not a source collection directory.
task geometry:render ARTIFACTS=/private/tmp/NEW-GEOMETRY-DIRECTORY
task geometry:mark ARTIFACTS=/private/tmp/NEW-GEOMETRY-DIRECTORY
# Inspect unchanged marked PNGs and freeze BEFORE viewing any output.
task geometry:compare ARTIFACTS=/private/tmp/NEW-GEOMETRY-DIRECTORY
```

The recipes retain `experiments/page_geometry.c`, `page_geometry.py` and
`page_geometry_guides.json`. The explicit fixture paths above are required;
changed source hashes/dimensions fail rather than silently reusing coordinates.
New fixtures require human/agent marking of the unchanged render and a fresh
freeze. `geometry:mark` applies the already recorded human/agent coordinates;
it does not establish them automatically. Delete disposable runs/binaries as
needed; rebuild through the retained recipe. Recipes call no discarded wrapper.
Convenience review PDFs were assembled separately from these PNGs; the repeatable
comparison's authoritative handoff is the ordinary full-page/crop PNGs and JSON.

Observed tools: Leptonica 1.87.0, Poppler 26.10.0, Apple clang 21.0.0, Python
3.12.15, Pillow 11.3.0, NumPy 2.2.6, uv 0.13.0 and Task 3.54.0. Script metadata
pins its two dependencies; product dependencies were not expanded. All five
geometry tasks passed. Shared `prepare:setup` and `prepare:check` passed with
231 tests, Ruff and strict pyright; existing preparation recipes are unchanged.

## Human response and successor

Geometry and preparation reactions were requested separately using the two
PDFs above; no reply arrived during the review window. This is an unavailable
human response, not assent or rejection. The technical recommendation is
extraction rejection, with the held-out model-quality question explicitly
inconclusive. Preparation approval remains pending even though its matched
pixels agree. The exact unanswered questions are whether the geometry views
support rejecting this automatic extractor without a render/detail concern,
and whether preparation preserved the presented music/faint detail, colour,
margins, spread/landscape canvases and both assigned cover pages. A response to
each, with inspected view and any defect, resolves the respective human gap.

`corrected-book-k5` should obtain the separate visual reactions, retain any
reported defects and decide the smallest next trial. The precisely unresolved
technical question is whether music-aware or manually supplied independent staff
traces can furnish a valid, adequately covered vertical field with held-out
improvement while retaining barlines/notation shape and detail. An expanded
fixture set or a two-axis field belongs to that successor's planning decision;
this failed extractor does not itself justify a new algorithm or a processor.
