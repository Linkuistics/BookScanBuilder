# corrected-book-k25

**Integrates:** corrected-book-k24

## Goal

Triage the findings of the planning review `corrected-book-k24` and apply the
real ones to the staff-guide trial and corrected-book planning consumer before
`staff-guides-k20` runs. Check each finding against the artifacts rather than
agreeing with it, and classify it as a contract stated unclearly, a real issue, a
visible trade-off or noise raised for want of context.

## Context

- Read the findings from the review's own commit and its `## Findings` section,
  not from this body. The reviewed producer is `corrected-book-k5`; its artifacts
  are `staff-guides-k20`, `corrected-book-k21`, `appearance-cleanup-k22`,
  `workflow-acceptance-k23` and the root `_BRIEF.md`. Reconcile each with the
  current tree by handle, not position; this leaf's insertion renumbered them.
- The review leans on k4's frozen evidence (`docs/experiments/page-geometry.md`,
  its JSON report and coordinate record), the retained wrapper
  `experiments/page_geometry.c`, `docs/research/scan-geometry-a.md`, and the
  Leptonica 1.87.0 source k4 built against. The review read that source from a
  disposable path; re-establish a verifiable copy of the exact pinned version
  before treating any library-behaviour claim as settled.
- Nothing in the trial has run. `staff-guides-k20` is a prototype whose
  deliverable is a human reaction, so repairing its contract here costs far less
  than discovering the gap after a traced run and a presented comparison.
- Preparation, processor, appearance and acceptance obligations are traced clean
  by the review and are not reopened. Keep `staff-guides-k20`, then
  `corrected-book-k21`, `appearance-cleanup-k22` and `workflow-acceptance-k23`
  live and in that order.

## Done when

- Every finding in `corrected-book-k24` has a recorded classification in this
  leaf's running log, with the evidence that decided it. Findings that rest on a
  library or measurement claim are checked against the pinned source and the
  recorded data, not accepted from the review's account.
- The real findings are applied to the consuming leaves' own task files and, if
  sequencing or ownership changes, to the root brief. A finding that changes what
  a later leaf must do is written into that leaf's `Done when`; nothing is
  pre-created beyond the leaves the plan already holds.
- Where applying a finding requires choosing between a different fixture and a
  declared change to a validity rule, or between keeping and decoupling the order
  of the expanded trials, the integrating session puts that trade-off to the
  human with a recommendation and the evidence, and does not choose silently.
- The trial's possible outcomes are mutually exclusive and honest: invalid or
  copied output, insufficient guide coverage, measurement indistinguishable from
  trace uncertainty, and an unavailable or ambiguous visual response each lead to
  a named next step, and none of them justifies automatic expansion.
- Every root `Done when` obligation, original-digest check and shared Taskfile
  verification the review found carried by `workflow-acceptance-k23` is still
  carried after the edits.

## Notes

This session reshapes the plan only. It does not run the staff trial, modify the
wrapper, the Taskfile, the experiment note or any ADR, and it commissions no
technology beyond what the plan already names. Do not invent numerical
acceptance thresholds or install a larger model to resolve a finding. No driver
is launched here.

## Decisions (running log)

The findings were read from review commit
`249840d7ecbedf42bb570e3bbe26d2044c4d9a63`, against producer `198411a131ca`
and the current consuming leaves. Tier 2 graph project
`Users-antony-Development-BookScanBuilder` reported no recorded coverage gap or
metadata mismatch for the seventeen evidence paths at generation
`2026-10-11T06:07:10Z`. Markdown, configuration and JSON were read directly.
The C `main` snippet matches the wrapper; its outbound graph trace resolves
Python symbols sharing the qualified name, so that trace is not evidence about
the C library calls. The exact snippet/source supplies those calls instead.
No trial, product, Taskfile or ADR change is commissioned in this integration.

Finding 1 is a real issue in the prerequisite contract and its outcome labels.
The freshly fetched [Leptonica 1.87.0 source](https://github.com/DanBloomberg/leptonica/blob/1.87.0/src/dewarp2.c)
at `/private/tmp/bookscan-k25-leptonica-1.87.0-dewarp2.c` has SHA-256
`f92430cbd2eedced417d82c20cbfd15d60886294f40fb6f7d5806265e28f2853`, identical
to the review's retained source. Lines 195–235 apply the 0.8 longest-line
filter, fifteen-line configured minimum and coverage gate before fitting;
lines 1280–1322 require four first-point positions in each half and a span
strictly greater than 0.50 of image height. The prose comment says "at least"
50%, but the executable comparison is strict. Lines 300 onward accept supplied
traces without these upstream checks. The wrapper's C lines 30–46 and 66–67
extract automatically and build/check validity; it currently accepts no traces.
The correction must name/reproduce the upstream gates before that lower-level
entry, then retain the default downstream validity checks.

The unchanged music render was visually inspected and remeasured read-only,
with before/after SHA-256
`7811202f5745b0547a344fce650ce12c8343bd2721c0a09f05ab307e262be096` matching
the frozen report. Dense-dark-row bands place the four long systems roughly
at y 780–1820 on a 2459-pixel page; the short outer systems are visible and
agree with the frozen reference extents (x 250–970 and 250–1050 versus
250–1580 for long systems). This supports the review's approximate 42%
coverage diagnosis. It is not a completed dense-trace preflight: the trial
must compute exact retained counts/first-point extents with held-out units
removed. An inadequate layout is inconclusive for the model hypothesis,
not evidence of sampler damage or two-axis failure. The fixture versus
declared-policy-change choice has been put to the human and is pending.

Finding 2 is a contract stated unclearly. Whole-rule exclusion prevents sharing
points, but does not preserve k4's spatial separation from nearby staff rules.
The frozen guide record gives complete exclusion rectangles; pinned source
lines 326–349 fit each rule quadratically and later interpolate between rules.
Nearby physical rules are valid distinct guides, so a close held-out rule is
not literally a duplicate or proof of false support. It answers a narrower
local-interpolation question. For the declared coverage/extrapolation question,
exclude a whole staff/system and report nearest-fit distance and overlays;
retain upper/middle/lower evaluation units where feasible. Failure to support
that separation is a coverage gap, not a reason to shrink exclusions.

Finding 3 is a real issue. The frozen `comparison.json` records rigid residual
rises 2.6034, 1.5871, -2.4125 and -0.2182 pixels, with curvature ranges
0.6451, 1.2687, 0.7147 and 1.3383 pixels. The note's asserted ±1/±2-pixel
marking uncertainty has no independent repeatability measurement. It cannot
decide whether the traced candidate improves on rigid deskew. Require a
pre-output independent repeat pass on representative traces and independent
output marking, report uncertainty beside differences, and classify effects
indistinguishable from measured uncertainty as inconclusive with a precise
measurement-completion handoff. No new numerical acceptance threshold is set.

Finding 4(a) is a real tree-shape issue: k5's charter requires a fresh planner
after any commissioned evidence, but k21 repeats that obligation only in its
supported branch. Make the consumer mandatory after trials/completion on every
branch, ahead of appearance design. Finding 4(b) is a real trade-off: the
research's Norwegian gutter and music cases test different hypotheses, and
k4's prose control has a valid 32-line fit without establishing gutter success.
Keeping representative evidence behind music can stall that independent
question; decoupling requires a separately stated automatic prose/gutter
hypothesis, unchanged checks, independent reactions and retained music work.
The sequencing choice has been put to the human and is pending; neither
option grants production commitment or automatic expansion of music evidence.

Finding 5 is a contract stated unclearly, with a real session-size risk. The
frozen record has sparse reference points, explicitly unsuitable as dense fit
traces. Admit visually placed traces of genuine physical rules only in this
isolation trial, declaring density, obscured gaps and repeatability before
output. Seeded snapping/extraction must be a separately stated acquisition
experiment with its own extraction evidence, not called independent manual
tracing. If k20 exceeds one session, its complete first child delivers the
frozen guide/holdout/preflight evidence and acquisition feasibility; a remaining
prototype owns fitted comparisons and human reaction, and k21 remains after
the complete trial. No horizontal trace-input implementation leaf is cut.

The independent corrections are applied to k20's own Done when and fallback
notes, k21's Done when and the root's carried evidence contract. The separate
preparation response/repair, post-split assembly, accepted-image/OCR/export,
ordinary unmarked input, collection isolation, default fidelity, optional
appearance and final acceptance obligations are retained. k22 and k23 remain
byte-identical to the reviewed tree, as do every root Done when criterion,
the wrappers, experiment note, Taskfile and ADR. No new leaf is created.
Fresh `task prepare:check` passes Ruff formatting/lint, strict pyright and all
231 tests. Every one of the seventeen subjects in k4's recorded before/after
digest maps still matches individually, including original PDFs; the maps
agree, and the report remained unchanged during this read (SHA-256
`185abccab5b4909a73560e28bfabe162d418b21cfa7861c9bde048cbf739a36c`).

The human confirmed both recommended choices: choose a suitable music fixture
with unchanged validity rules and retain page 140 as an unsupported-layout
diagnostic; allow independent prose/gutter evidence after k20 regardless of
music support. Applied the fixture-selection requirement to k20's Context and
Done when, including same-page automatic diagnostics so changing fixture cannot
be mistaken for isolating acquisition on page 140. k21's Done when now permits
the separately stated existing-candidate Norwegian-gutter/prose-control question
while retaining unresolved music/preparation and every representative-case
acceptance obligation. The root brief carries both choices. This confirmation
settles the two previously pending trade-offs; it is not a visual response to
preparation or geometry, and grants neither production acceptance nor a change
to validity rules. The current k20 → k21 → k22 → k23 ordering remains intact;
no additional leaf or new correction technology is commissioned here.

Post-confirmation verification enumerated the tracked paths and compared each
current file with the review commit: only the four intended planning files
changed, with no added/deleted paths before retirement. The root Done when
section and the seven named protected artifacts (k22, k23, Taskfile, C wrapper,
guide record, experiment note and ADR) match exactly. Product code, tests and
dependencies therefore remain the version verified by `prepare:check`; all
seventeen frozen k4 subjects were checked again individually and match,
including originals, with the report unchanged during verification. The final
diff was read against every k25 completion condition. No in-session reviewer
was needed, no substantial redesign was applied, and no new work is cut.
Retirement leaves k20, k21, k22 and k23 live, so no ancestor closes and no ADR
promotion or review-creator line is needed. Both policy choices are settled;
the separate historical visual responses remain explicit downstream.
