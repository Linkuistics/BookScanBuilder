# corrected-book-k30

**Integrates:** corrected-book-k29

## Goal

Triage the findings of the planning review `corrected-book-k29` and apply the
real ones to the source-acquisition repair and its fresh planning consumer
before `staff-acquisition-k27` runs. Check each finding against the artifacts
rather than agreeing with it, and classify it as a contract stated unclearly, a
real issue, a visible trade-off or noise raised for want of context.

## Context

- Read the findings from the review's own commit and its `## Findings` section,
  not from this body. The reviewed producer is `corrected-book-k21`; its
  artifacts are `staff-acquisition-k27`, `corrected-book-k28` and the root
  `_BRIEF.md`, with `appearance-cleanup-k22` and `workflow-acceptance-k23` as
  later consumers. Reconcile each with the current tree by handle, not position;
  this leaf's insertion renumbered them.
- The review leans on the frozen k26 record and report, `docs/experiments/
  staff-guides.md`, `experiments/staff_coordinates.py` and its tests, the C
  wrapper `experiments/page_geometry.c`, and the Leptonica 1.87.0 source pinned
  by the record's `frozen_hashes`. Re-establish a verifiable copy of that exact
  source before settling any library-behaviour claim; the review read a
  disposable path.
- Nothing in the repair has run. `staff-acquisition-k27` is a prototype whose
  deliverable includes a human reaction, so repairing its contract here costs far
  less than discovering a gap after dense marking and a presented overlay.
- Keep `staff-acquisition-k27`, then `corrected-book-k28`,
  `appearance-cleanup-k22` and `workflow-acceptance-k23` live and in that order,
  unless a finding puts a human-approved sibling ahead of them.

## Done when

- Every finding in `corrected-book-k29` has a recorded classification in this
  leaf's running log, with the evidence that decided it. Findings that rest on a
  library, instrument or recorded-measurement claim are checked against the
  pinned source, the code and the recorded data, not accepted from the review.
- The real findings are applied to the consuming leaves' own task files and, if
  sequencing or ownership changes, to the root brief. A finding that changes what
  a later leaf must do is written into that leaf's `Done when`; nothing is
  pre-created beyond the leaves the plan already holds, except where a
  human-confirmed sequencing choice requires one.
- Where applying a finding requires choosing between orderings or between
  changing a human-confirmed policy and keeping it, the integrating session puts
  the trade-off to the human with a recommendation and the evidence, and does not
  choose silently.
- The repair's possible outcomes remain mutually exclusive and honest: invalid
  acquisition, insufficient separation/coverage, unresolved measurement or
  instrument evidence, an unavailable source or historical reaction, and
  admissible evidence each lead to a named next step, and none grants a fit,
  repeat, expansion, interpolation, two-axis model, music acceptance or
  preparation approval.
- Every inherited obligation (fixed representative cases, processor design
  before production, working accepted-image/review/post-split assembly/OCR/export
  ownership, earlier-OCR and actual English alignment, ordinary sole-PDF input,
  collection isolation, default fidelity, optional appearance, final root
  acceptance, shared Taskfile verification and original digests) is still carried
  after the edits.

## Notes

This session reshapes the plan only. It does not mark the staff, run the
instrument against a new record, modify the wrapper, the Taskfile, the frozen
records, an experiment note or an ADR, and commissions no technology the plan
does not already name. Do not invent numerical acceptance thresholds. No driver
is launched here.
