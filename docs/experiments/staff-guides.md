# Staff-guide acquisition trial

The bounded trial is **inconclusive because guide acquisition failed**. The
first manual pass does not provide admissible dense physical-rule traces:
native source checks expose obscured/outside-rule points and centre discrepancies
up to 6 pixels. No vertical model, rigid comparison, corrected image or new
sampler result was generated. This says nothing about the vertical model family,
automatic extraction on the selected page, or native RGB sampler quality.

The next question is precise: can a fresh manual marking pass on the unchanged
selected page provide genuine unobscured dense observations, a repeat pass
without first marks, and adequate measured uncertainty with the same whole-staff
holdouts and unchanged native prerequisites? Resolve that acquisition question
before fitting. Do not relabel snapping or automatic extraction as manual tracing.

## Bounded fixture selection

Inspected complete Poppler RGB/PNG renders at 300 dpi for the six permitted
pages of `Raw Scans/Fundamentals of Musical Composition.pdf`, relative to
`/Volumes/Glass/Book Conversion`. Originals remained untouched.

| PDF / printed page | Full canvas | Source observation |
| --- | --- | --- |
| 20 / 6 | 1702 × 2440 | Candidate: long music rules across upper/middle/lower content. Actual suitability still needs admissible coordinates. |
| 40 / 26 | 1692 × 2443 | Prose; no music-rule trial. |
| 60 / 46 | 1705 × 2438 | Upper/middle grand staffs, shorter lower system; not selected. |
| 100 / 86 | 1703 × 2440 | Prose; no music-rule trial. |
| 180 / 166 | 1713 × 2450 | Music concentrated in upper/middle content; not selected. |
| 220 / 206 | 1699 × 2445 | Prose; no music-rule trial. |

These are bounded visual selection observations, not exhaustive preflights or
six correction trials. Page 140 remains the historical unsupported-layout /
automatic-extraction diagnostic; switching candidate does not repair that page.
The source PDF SHA-256 remains
`3235a842d619a18b11e2fbdb3b5b6666adeb223959cafd4b1d67f27f0dbfe780`.
The [selection manifest](staff-coordinate-selection.json) retains every inspected
render identity, hash, dimension and observation.

## Rejected coordinate evidence

The [initial first-pass record](staff-coordinates-first-pass.json) was written
before source repeat checks and before any model/correction output. It retains
the initially stated uncertainty and marking description verbatim; the final
[coordinate record](../../experiments/staff_coordinates.json) corrects the
display-method description and explicitly marks acquisition inadmissible.

The pass visually placed 433 points on 35 physical-rule identities, numbered
top to bottom, with top-left pixel-centre origin and native pixel units. Nominal
100-pixel column spacing and recorded omitted columns were intended to avoid
notation. Twenty rules were assigned fit and fifteen evaluation. Each evaluation
unit contains all five rules of a full staff: Ex.4 a–b (upper), Ex.5 (middle),
and Ex.7 f–i (lower), with full-width exclusion rectangles. The opening grand
staff, Ex.4 continuation/d and Ex.7 j–k supplied the diagnostic fitting records.
Other staffs were not traced or counted.

Inspection used the unchanged complete page, 2× bicubic grid displays and then
unmarked 4× nearest-neighbour source patches. The repeat pass did not display
first-pass marks or coordinate lists. It was performed by the same observer;
memory and shared systematic bias cannot be ruled out. Only unobscured common
columns were compared. These are **failure-detecting spot checks**, not adequate
repeatability calibration for a fitted comparison. Some first-pass x=172 and
end-bar positions do not permit a genuine rule-centre observation; additional
points lie on stems/notation. Connecting overlay segments are display aids,
not observations through those gaps.

| Third physical rule | Role / band | Max absolute spot-check difference | RMS difference |
| --- | --- | --- | --- |
| opening treble T | fit / upper | 1.0 px | 0.456 px |
| Ex.4 a–b A | evaluation / upper | 4.0 px | 3.454 px |
| Ex.4 continuation/d D | fit / middle | 6.0 px | 5.621 px |
| Ex.5 E | evaluation / middle | 4.0 px | 4.000 px |
| Ex.7 f–i H | evaluation / lower | 1.5 px | 1.072 px |
| Ex.7 j–k I | fit / lower | 2.5 px | 2.222 px |

The initial provisional ±3-pixel uncertainty is therefore unsupported. Rise and
curvature differences for matching observation columns are retained in the
[report](staff-coordinate-report.json); these diagnose marking inconsistency,
not source geometry or corrected-output improvement. No acceptance threshold
was agreed or invented. Reject this coordinate set for fitting rather than
increasing an uncertainty number to admit it.

## Exact native gates, applied only to diagnostic coordinates

Checked [pinned Leptonica 1.87.0 source](https://github.com/DanBloomberg/leptonica/blob/1.87.0/src/dewarp2.c).
The existing C wrapper automatically extracts guides and has no supplied-trace
entry. The later supplied-trace entry would be `dewarpFindVertDisparity` after
reproducing the builder's prerequisites, followed by unchanged default validity
checks; that entry itself does not perform those prerequisite gates.

The coordinate-only instrument calls native `dewarpRemoveShortLines` with 0.8
and native NUMA integer rounding. Its coverage arithmetic reproduces the private
coverage check. On these **inadmissible diagnostic coordinates**, it retains
20 unique coordinate records, 15 first points in the top half and 5 in the bottom,
with rounded first heights 273–2088 and float32 span fraction
0.7438524365 of the full 2440-pixel canvas. All survive longest-line filtering.
The report retains each identity, coordinate list and rounded first position.
Neither this gate pass nor unique IDs proves points lie on physical rules.

Diagnostic nearest vertical distances from each complete evaluation staff to
the recorded fitting polylines are 208 / 203 / 104 pixels for upper / middle /
lower units. Every per-fit-rule distance and exclusion is retained. Invalid
source marks prevent interpreting those values as validated separation evidence.
`acquisition_admissible=false` and `guides_eligible_for_fit=false` take precedence
over the numerical gate pass. No builder/default-model rejection or application
failure was observed: those stages were never entered.

## Ordinary source views and reproduction

Open `/private/tmp/bookscan-staff-k20-selection/separation-overlay.png` and its
`upper-overlay.png`, `middle-overlay.png`, `lower-overlay.png`. Blue/red identify
the rejected fit/evaluation records; magenta boxes identify whole-staff holdouts.
Full source, unmarked `staff-*.png` grids and `repeat-*.png` source patches remain
alongside them. These overlays are source acquisition diagnostics, not corrections.
Full-page and all three native overlays were inspected by the agent and confirm
that wide-strip approximations cannot be used as dense fit traces.

```sh
task geometry:staff-check
# A disposable external directory; these recipes reject the source collection.
task geometry:staff-views ARTIFACTS=/private/tmp/NEW-STAFF-DIRECTORY
task geometry:staff-preflight ARTIFACTS=/private/tmp/NEW-STAFF-DIRECTORY
```

The views recipe reproduces page 20 and the exact previously observed displays;
it does not make new marks. The preflight recipe never fits a model. Pinned
source/render/display hashes must agree. The completed instrument was frozen
before final runs in the original directory and
`/private/tmp/bookscan-staff-k26-reproduced`. Every retained rule, rounded gate
value, exclusion/distance, spot-check record and output image hash agreed
item by item between runs. Both before/after maps agree for each read subject:
original PDF, render, pinned source, shared library, coordinate/first-pass
records, wrapper, boundary tests, Taskfile and all observed source displays.
The report names their exact paths and digests. No writer edited an instrument
during either final run. The source-view regeneration also rechecked the
original source before/after and reproduced every display hash.

`geometry:staff-check` passes four native gate-boundary checks (strict span,
native rounding, below/at longest-line threshold), plus Ruff format/lint.
Existing `geometry:setup` and `geometry:build` pass. Shared `prepare:check`
passes Ruff, strict pyright and all 231 tests. Product dependencies and correction
wrapper are unchanged. Retained wrappers back every added recipe.

## Human disposition and planning handoff

The user explicitly answered **“Not inspected yet”** separately for historical
`geometry-review.pdf` and `preparation-review.pdf` in
`/private/tmp/bookscan-geometry-k4-final`. Neither response grants acceptance or
reports a defect. Preparation's disposition is recorded separately in
[its acceptance note](../acceptance/prepared-pdf.md). The source-overlay
acquisition-repair question was also presented; its response remains pending
at this evidence boundary.

`corrected-book-k21` must consume this **inconclusive acquisition** result.
It owns the decision to commission precise manual-marking/repeatability completion
on page 20 at unchanged settings, or a separately stated acquisition hypothesis.
Retain exact whole-staff holdouts; remove obscured/outside-rule observations;
measure repeatability and systematic-error limitations before a fresh pre-output
freeze and exact preflight. Passing native gates on this rejected record is not
permission to run a real fit. A matched automatic baseline on page 20 has not
been run; k4's page-140 failure cannot substitute for it.

Once admissible guides exist, the remaining original hypothesis still needs
the matched automatic/manual diagnostics, unchanged vertical family/default
validity, actual mapping/application evidence, rigid baseline, independent
output marks with uncertainty, detail/shape/control checks and explicit traced
view reaction. The verified control and forced sampler diagnostic require the
original declared checks; this source-only slice supplies no new control or
sampler evidence. No music expansion or production commitment follows. Retain
the separate pending historical geometry/preparation responses and a fresh
planning consumer after any commissioned completion, ahead of appearance design.
