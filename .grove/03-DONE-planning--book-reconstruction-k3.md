# book-reconstruction-k3

## Goal

Plan the smallest independently useful increments for the personal two-stage
book reconstruction workflow, grounded in the settled requirements and the
correction-method evidence. Grow only the work that can now be stated precisely.

## Context

- `plan-k1` records the confirmed user decisions and inspected inputs.
- `scan-geometry-k2` precedes this leaf; read its survey at
  `docs/research/scan-geometry-a.md` before deciding the correction trial.
- The preparation stage merges explicitly chosen covers and content into one
  PDF. The main stage processes that single PDF without discovering content or
  covers across the collection folders. The user's shell supplies the batch
  orchestration.

## Done when

- The first independently useful increment and its concrete real-PDF acceptance
  cases are identified. Demonstrating within-page correction and image fidelity
  must precede treating a correction method as settled.
- Any unresolved design or visual-prototype questions needed before production
  implementation are expressed as bounded leaves in the appropriate order.
- The immediately actionable leaves have goals, inputs, completion conditions
  and the agreed test seams. Remaining work whose shape is still unknown stays
  in the brief rather than becoming a speculative full implementation tree.
- The plan preserves the explicit preparation/main-process boundary and a
  single-PDF main entry point, including tests that run without the source
  collection folders.
- The first implementation work includes a root Taskfile once reusable setup,
  fixture and verification commands are concrete; new tasks must be verified.

## Notes

This is a personal workflow on the current Mac, not a general application.
Choose the least interface and packaging work that serves the agreed review
controls. Native packaging and an application-level queue are not requirements.

Plan through vertical, demoable slices. The main uncertainty is geometry
quality on real scans, including music notation and spreads, not PDF merging
alone. Use the research to choose a cheap trial and the necessary agreement
point before building the complete workflow. No implementation language, image
correction algorithm, or review technology was selected by requirements.

English OCR enables search and selection while corrected page images remain
visible. Covers may include front and back pages. All three book folders remain
in scope as input sources even though the main processor only sees one prepared
PDF. Original files must remain untouched.

## Decisions (running log)

The first product increment is explicit PDF preparation: selecting content and
cover pages and exporting one prepared PDF is useful before correction exists.
It has its own jj workspace and grove at
`/Users/antony/Development/BookScanBuilder.prepare-pdf`. Its design and planning
are independent of geometry, and its implementation must stay usable without a
processor. The current grove commissions the geometry evidence first; the
successor product increment is a separate single-PDF processor grove, to be
created once the trial makes its correction and adjustment contract concrete.
Schema, rendering, accepted review edits and OCR stay together in that increment
because none alone delivers a usable corrected searchable book.

Optional whitening and noise-removal previews are a further independent working
increment after the default processor has an accepted-image/export seam. Keep
that successor grove distinct so choosing appearance-cleanup methods cannot
delay the useful default-correction handoff. The root still requires all three
increments before the end-to-end workflow can finish.

The next visual prototype compares Music Composition PDF page 140 against
Algorithm Design PDF page 20, using unchanged, rigid-deskew and per-page
Leptonica vertical-only results. It records actual model validity and
displacement, holds out evaluation guides, and preserves complete visible PDF
content. This is a candidate experiment, not an algorithm selection. A user's
visual reaction and the unchanged-control comparison determine the next trial.

The follow-on planning leaf owns the conditional expansion to the other real
fixtures and the processor-grove handoff. It must not interpret a failed model,
copied output, successful startup or one improved staff as general acceptance.
The fixed expanded fixture questions are carried in its body, while the unknown
choice of correction and review technology stays on the horizon.

The reusable Taskfile starts with concrete prototype commands and remains part
of the project. Preparation's first implementation also includes verified
setup, fixture and public-command checks; neither grove gets speculative setup
tasks or a separate test-only horizontal slice.

The increment boundaries and cross-workspace handoff earn an independent
planning review before the geometry prototype consumes this plan. Its review
must inspect both task trees, the preservation of the confirmed scope, and the
failure/continuation ordering; it must not assume candidate geometry succeeds.
