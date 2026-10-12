# page-straightening-k67

## Goal
Ship a first cut of a standalone tool that corrects non-constant skew (changing
local line angle across one scanned page) for a single page image, with a
before/after measure so a reader can see whether it helped. Iterative delivery:
a working, honest first cut now; broader cases and coverage follow as GitHub issues.
Raised by the user 2026-10-15 as the next delivery after the baseline first cut.

## Context
- Cut during k63 at the user's direction; sequenced after k63's first cut and ahead
  of the browser leaf k64. The user may reorder; nothing here depends on k64.
- The tool is **single page image in, one image out**, as its own command. It is
  not inside a baseline project and does not touch review state. PDF wrapping and
  project integration are later issues.
- Target defects, **both, one at a time** (user's answer): (1) feed variation:
  line angle changes across the page, as in Fundamentals of Musical Composition
  p.20 (long staff rules); (2) gutter curl on prose, as in the Norwegian pages.
  Start with whichever shows a measurable improvement first and state plainly which
  case the tool does not handle.
- Read before designing: docs/specs/rotation-processor.md (lines ~14-24 and ~760-775
  and ~915-930: rigid tilt does not fix within-page curvature; nonrigid is
  "required for the complete default product" but needs its own evidence), and
  docs/research/scan-geometry-a.md ("Three different geometry problems",
  Leptonica dewarp, ScanTailor, page-dewarp and its colour/horizontal-compression
  trap). docs/experiments/staff-guides.md records why the last measurement
  attempt was inconclusive: manual rule traces were not admissible (centre
  discrepancies up to 6 px), so nothing was fitted and no model family is ruled
  out. Do not relabel snapping or automatic extraction as manual truth.
- Reuse what exists and is pinned: Poppler/Leptonica/Pillow in the packaged helper,
  the exact-RGB render path and native sampler checks. Do not use page-dewarp's
  renderer for output (it discards colour).

## Done when
- A documented command takes one page image and writes a corrected image, never
  overwriting its input, with deterministic output for the same input and settings.
- It reports a before/after measure of line straightness (for example residual
  line slope/curvature of detected lines) on the same page, and leaves the page
  unchanged and says so when the measure does not improve or lines are too few.
- At least one real page from the corpus shows a measured improvement on one of the
  two target defects, with the exact input, settings, output and measure recorded;
  the other defect is stated as not yet handled or handled, with evidence.
- Colour and fine detail are preserved by the sampler used; sparse pages and music
  staves are called out as limitations rather than silently attempted.
- One end-to-end test runs the command on a synthetic page with known feed
  variation and checks the measure improves; the existing suite stays green; a
  Taskfile recipe runs it; a README section gives usage and known limitations.

## Notes
Deferred and expected as GitHub issues: the second defect if only one is delivered,
PDF in/out, integration with baseline review/export and book alignment, music-aware
line detection, held-out whole-staff validation, large-scale corpus evaluation.
