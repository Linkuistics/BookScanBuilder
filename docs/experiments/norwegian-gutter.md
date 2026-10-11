# Norwegian gutter trial: source prerequisite slice

The full-canvas, unmasked extraction diagnostic is complete; the correction
trial remains **incomplete at independent acquisition** on both halves.
No rigid image, model, field, candidate, corrected-output measurement or human
comparison has been produced. The diagnostic's line counts cannot accept or
reject the held-out automatic candidate.

The hypothesis is unchanged: independently assess whether the existing automatic
vertical candidate improves each Norwegian page-20 gutter half beyond rigid
while preserving shape/detail and the verified Algorithm Design control.
Acquisition/coverage, default model rejection, application/copy, observed damage
or no useful improvement, below-uncertainty improvement and missing reaction
remain separate outcomes. No numerical acceptance threshold has been invented.

## Source and split freeze

Sources remain under `/Volumes/Glass/Book Conversion`; originals were only read.
Both are one-based PDF page 20. The source identities match the surveyed fixtures:
Norwegian printed 36–37 and Algorithm Design printed preface xx.

| Source | PDF SHA-256 | Complete RGB render |
| --- | --- | --- |
| `Processed Books/Norwegian - An Essential Grammar (Routledge)/Norwegian - An Essential Grammar (Routledge).pdf` | `a21736ada0c088ab9e4f89a264c303788ccf22c4ee647b5dfb5f076ea1b750d3` | 3591 × 2695 |
| `Processed Books/Algorithm Design/Algorithm Design.pdf` | `b9d6f1fd08560f06ec8653375a5866dbe1ba971d780dfecd1a0211fb2f66deab` | 2350 × 2721 |

Poppler 26.10.0 rendered complete default MediaBox RGB PNGs at 300 dpi, using
k4's rendering policy. This does not add original detail to Norwegian's
220-ppi grayscale JPEG. The inspected spread PNG hash is
`38c1b4450bd152a6be72f7a1021dacbb9406b2ed22ffea865a019f39340110d8`.

Codex manually chose x=1785 at the visible vertical gutter seam after inspecting
the unchanged complete spread and native gutter crop, before any fit. Retain
left columns [0,1785), right [1785,3591), both full-height [0,2695). In native
pixel-centre coordinates (x right, y down), left origin is (0,0), canvas
1785 × 2695; right origin is (1785,0), canvas 1806 × 2695. No gutter band,
margin, border or printed content was removed. Joining the halves reconstructs
every source RGB pixel exactly. This manual trial separation supplies no
production spread detector and no landscape single-page acceptance.

The [canvas record](../../experiments/norwegian_canvases.json) freezes origins,
dimensions, split method and upper/middle/lower native gutter crops. The fresh
control render matches k4's unchanged `control.png` pixel for pixel; this
rechecks render identity, not its independent baseline geometry or visual fidelity.

## Native unmasked diagnostic

Threshold 180, native `dewarpGetTextlineCenters`, native .8 longest-line filter
and existing native NUMA first-point rounding. The shared coordinate preflight
reproduces pinned Leptonica 1.87.0 `dewarp2.c` coverage arithmetic on each complete
canvas: minimum fifteen, at least four first points in each half-height, span
strictly greater than .50 of full height. Sampling 30/reduction 1/default model
checks remain the future fit policy; no fit was called in this slice.

| Input | Extracted / retained | Upper / lower | Rounded first-y range | Full-height span | Unmasked numerical result |
| --- | --- | --- | --- | --- | --- |
| Left, printed 36 | 36 / 15 | 6 / 9 | 198–2389 | .81298703 | Pass only on this diagnostic input |
| Right, printed 37 | 34 / 10 | 4 / 6 | 152–2286 | .79183674 | Fails fifteen-line minimum on this diagnostic input |
| Control | 40 / 35 | 17 / 18 | 304–2444 | .78647554 | Pass only on this diagnostic input |

All automatic centres and retained traces are saved, with exact native first-y
values and rounded integers. Automatic array indices are **not independently
verified physical text-line identities**. No line has been admitted as an
independent evaluation observation, no evaluation rectangle has been frozen,
and no analysis exclusion applied. Removing regions can change connected
components and the longest-line threshold; the unmasked counts are neither a
held-out upper bound nor a decisive masked prerequisite result. In particular,
the left's exact-minimum count licenses no fit, and the right's failure does
not establish failure after the eventual declared holdouts.

Positional, slope and curvature uncertainty, shared systematic bias, spatial
separation, gutter coverage and per-point physical-source verification remain
unmeasured. There is no transported-coordinate or automatic-guide evaluation
substitute. Both halves' first unresolved trial outcome is independent source
acquisition/verification; later unmasked count observations are retained above.
No missing field or invalid fit has been used to diagnose a sampler or two-axis
problem. Music and preparation are separate unresolved questions.

## Inspectable artifacts and verification

Open ordinary source files in `/private/tmp/bookscan-norwegian-k32-final`:
`spread.png`, `left.png`, `right.png`, `control.png`, and each half's
`gutter-upper`, `gutter-middle`, `gutter-lower` PNGs. Source-only full pages and
all six native gutter crops were inspected by Codex. Full text, printed page
numbers, outer borders and gutter shadow are retained. Automatic overlays are
labelled `*-automatic-overlay.png`; exclude them and the automatic lists from
fresh coordinate-free observation packets. No human source or output response
was requested or received in this prerequisite slice. The separate per-half
improvement/control/sampler questions await actual matched comparisons; absence
of a comparison is not an ambiguous approval or a concrete visual defect.

The [durable report](norwegian-preflight-report.json) holds per-case native
counts/rounding/extents, every command, output hash and before/after read-subject
map. Full extracted and retained coordinates are retained in its external
ordinary `preflight.json` and the linked lossless
[native JSON archive](norwegian-preflight-native.json.gz). Decompress that archive
with an ordinary gzip reader; its bytes exactly equal the recorded full JSON.
The report records both SHA-256 values. No lossy image recompression was used.

All instrument edits finished before the final run. Its fifteen read subjects
were individually digested before/after: both PDFs; the inspected spec;
Python instrument and shared coordinate wrapper; Taskfile; native Leptonica
library; Poppler executable; pinned native source; k4 control PNG and frozen
record; then the four new unchanged render/half PNGs before extraction.
Every subject remained stable, and current digests were rechecked afterward.
One writer ran each measurement sequentially. A second complete run at
`/private/tmp/bookscan-norwegian-k32-rerun` agrees on every extracted/retained
point and per-case result, each output-file digest and shared subject digest,
not merely counts. The [rerun record](norwegian-preflight-rerun.json) records
those per-item checks.

Reproduce with a new external directory:

```sh
task geometry:norwegian-preflight ARTIFACTS=/private/tmp/NEW-NORWEGIAN-PREFLIGHT
```

The recipe uses the retained canvas spec and `norwegian_preflight.py`, importing
`native` and `preflight` from `staff_coordinates.py`. It needs the exact two
source PDFs, installed Leptonica 1.87.0/Poppler, k4's unchanged control PNG and
k26's retained `dewarp2-1.87.0.c` at the spec's explicit external paths. These
are existing frozen evidence prerequisites; restore/reverify them through the
retained k4/staff recipes if disposable directories are removed. A missing
subject fails rather than silently substituting new evidence. The new recipe
passed twice after final edits; geometry setup/build, staff-check (four tests)
and prepare:check (231 tests, format/lint and strict pyright) passed. New Python
format/lint also passed. Existing wrapper bodies and recipes remain intact.

Tier 2 graph lookup found the exact existing C experiment and shared preflight
symbols; both-direction traces and exact snippets were read. Graph C/Python
`main` relationships conflate the same module name, so direct C source was
used for the actual API claim. Coverage metadata generation
`2026-10-11T09:39:23Z` reported no recorded issues for the evidence paths;
the newly formatted Python file had changed metadata and was read directly.
This is bounded evidence, not a whole-repository completeness claim.

## Remaining complete trial and consumer

`norwegian-gutter-k31` stays open. Its remaining prototype must acquire genuine
source baselines across upper/middle/lower and gutter/centre/outer ink regions,
record omitted/ambiguous columns, freeze whole-line/region holdouts before fitting,
and obtain fresh coordinate-free representative whole-trace repeats plus
per-point independent verification and measured systematic uncertainty. Re-run
exact native extraction/count/coverage/leakage on the masked full halves.
Unsupported halves stay usable/flagged; no trim, moved holdout, borrowed model,
forced validity, changed minimum, automatic evaluation marks or invented gap.

Only passed, independently verified prerequisites permit unchanged/rigid/actual
vertical comparisons. That complete comparison includes default model validity,
field/mapping/application/copy status, independent output re-marking, local
shape/faint-detail/clipping inspection, independently reverified control and
k4's nonidentity fractional native-sampler diagnostic. Obtain distinct human
responses for left, right and control/sampler at exact inspected paths. Each
half is classified independently using k31's ordered outcomes.

The fresh planner before `staff-acquisition-k27` must consume this committed
partial slice and the remaining child's actual result, including decisive
prerequisite failure or missing measurement/reaction. It preserves k27 → k28,
all unresolved music/page-140 and historical preparation/geometry responses,
the fixed representative cases, processor design and working accepted-image/
review/post-split assembly/aligned English OCR/export with earlier OCR and
collection-isolated sole-PDF input, default fidelity, optional appearance and
final root acceptance. This source slice settles none of those by proxy.
