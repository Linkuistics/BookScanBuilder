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
