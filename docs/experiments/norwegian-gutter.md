# Norwegian gutter trial: inconclusive independent measurement

The full-canvas, unmasked extraction diagnostic is complete. k33's fresh source
observers leave each half **inconclusive at independent measurement** with the
available image viewer. This is the bounded instrument/measurement outcome,
not a masked extraction rejection or evidence against the vertical candidate.
No rigid image, model, field, candidate, corrected-output measurement or human
comparison has been produced. The diagnostic's line counts cannot accept or
reject the held-out automatic candidate.

k35 subsequently tested a fixed pixel-labelled patch format with blind
known-cell controls. All nine joint readbacks failed, so each half stops at
instrument addressing before real marks or masked extraction. Its complete
bounded result, unchanged source checks, separate unavailable human reactions
and mandatory fresh-planning handoff are in
[Norwegian source measurement](norwegian-measurement.md). This rejects that
specific grid/viewer observation attempt, not every instrument or the vertical
family. The k32/k33 evidence below remains historical and unchanged.

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

## k33 source observation and instrument outcome

Two fresh coordinate-free contexts independently inspected their assigned
unchanged half and three native gutter crops with `view_image(detail=original)`.
The packets included dimensions/origins and the observation contract, excluding
automatic traces/overlays, previous marks and conclusions. Each observer was
isolated from the other half's observations. These were source observers, not
artifact reviewers or numerical repeat passes.

| Half | Physical source observations | First applicable outcome |
| --- | --- | --- |
| Left / printed 36 | Upper endings “new” and “fired”; middle heading ending “compound verbs can”; lower “Can you give me”, “He translated the” and concluding paragraph. Section d contains separate text columns, not a continuous baseline across the whitespace. | Inconclusive acquisition/measurement: no independently verified numerical baseline trace or measured uncertainty. |
| Right / printed 37 | Upper “Examples:” and “et innbetalt”; middle “FUNCTION:” and “et sovende”; lower “Example:”, “skinnende” and “Examples:”. Gutter margin contains blank paper before the text. | Inconclusive acquisition/measurement: no independently verified numerical baseline trace or measured uncertainty. |

Each attempted to follow non-descending glyph bottoms in an upper native crop.
Neither admitted a coordinate: the displayed bitmap has no pixel cursor/readout
or recorded point selection, and the full-page presentation is reduced in size.
Existing gutter crops show short beginnings/endings and blank margin, with some
lines clipped by the display crop; they do not expose centre/outer ink at equal
detail. This is crop-packet coverage, **not clipping of the frozen half canvas**.
Blurred edges, rounded glyph overshoot, descenders and italics add ambiguity to
what constitutes a baseline. Positional, slope and curvature uncertainty and
shared systematic error remain unquantified; repeat viewing cannot certify them.
Blank gutter columns supply no physical text point. No whole numerical trace,
blind numerical repeat, per-point verifier or evaluation rectangle was frozen.

This finding is limited to the actual `view_image` observation and packets. It
does not establish that native marking is impossible through a pixel-addressed
patch display or human annotation tool, nor that all useful instruments are
unavailable. Both halves reach k31's first acquisition/instrument/measurement
outcome before masked extraction. No gate or model was relaxed, and no automatic
centre was relabelled as an evaluation mark. No rigid/candidate/control output,
field, application, fallback copy or output-quality claim was generated in k33.

The [source-observer record](norwegian-source-observers.md) retains the exact
observations, trace attempts, instrument limitations and digest provenance.
First observer hashes were after initial viewing and are labelled that way;
they cannot retroactively freeze the first view. A subsequent upper-crop view
on each half was bracketed by matching hashes. All eight image hashes match
k32's frozen outputs. The separate [integrity check](norwegian-k33-integrity.json)
rechecks 23 subjects before/after, including both original PDFs, unchanged
spread/halves/control, six gutter crops, source spec, retained instruments,
Taskfile, pinned renderer/library/native source and k4 control/freeze. Split
pixels, every crop's native pixel contents and historical control pixels match.
That check proves source identity, not measurement calibration or source flatness.

The source/instrument result was presented for a human reaction at
`/private/tmp/bookscan-norwegian-k32-final/left.png` and `right.png`, explicitly
separate from correction-quality approval. The per-half beyond-rigid questions
and control/forced-sampler detail question cannot yet be answered because the
matched trial comparisons were not generated. Historical geometry/preparation
responses stay separate. Human response disposition is recorded below.

No human reply arrived during this session's source/instrument response window.
For both halves that response is unavailable, not “Not inspected yet” (which
would require that actual reply), assent or a reported source defect. Left and
right beyond-rigid improvement responses and the control/forced-sampler detail
response are **unperformed: no matched trial view exists**. No inspected path
has been claimed on the human's behalf. Their absence is a later observation;
each half's first outcome remains the acquisition/measurement gap above.

Fresh `geometry:staff-check` passed format/lint and four native boundary tests;
`prepare:check` passed format/lint, strict pyright and 231 tests. No reusable
recipe or instrument changed; existing geometry wrappers/tasks remain intact.

## Unperformed complete comparison and fresh consumer

The bounded k31 instrument outcome supplies no corrected comparison. Any newly
commissioned measurement completion must acquire genuine
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

The already-live `norwegian-gutter-k34` planner before `staff-acquisition-k27`
consumes k32 and k33's committed inconclusive instrument result. The precise
changed observation is whether pixel-addressed native patches with recorded
non-descending glyph anchors can support fresh whole-line repeats and independent
per-point source verification with positional/slope/curvature and systematic
uncertainty across real gutter/centre/outer ink. Rejection includes ambiguous
anchors, unverified points, insufficient spatial coverage or systematic limits
that obscure the source nonrigidity; repeatability alone is insufficient. k34
decides this question, rather than commissioning the same viewer trial again.
Any instrument completion must include inspectable real-source acquisition and
its measured validity, not an adapter-only slice. A numerical acquisition pass
still needs all conditional masked-fit/output/control/sampler/measurement and
separate per-half visual responses above. It preserves k27 → k28,
all unresolved music/page-140 and historical preparation/geometry responses,
the fixed representative cases, processor design and working accepted-image/
review/post-split assembly/aligned English OCR/export with earlier OCR and
collection-isolated sole-PDF input, default fidelity, optional appearance and
final root acceptance. This source slice settles none of those by proxy.
