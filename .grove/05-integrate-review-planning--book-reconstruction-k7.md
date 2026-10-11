# book-reconstruction-k7

**Integrates:** book-reconstruction-k6

## Goal

Triage the findings of the planning review `book-reconstruction-k6` and apply the real ones
to the planned subtree before `page-geometry-k4` consumes it. Verify each finding against the
artifacts rather than agreeing with it, and classify it as a contract stated unclearly, a real
issue, a visible trade-off or noise.

## Context

- Read the findings from the review's own commit and its `## Findings` section, not from this
  body. The reviewed producer is `book-reconstruction-k3`, which has two commits: `c9959370a702`
  here and `1ada47bd20fe` in `/Users/antony/Development/BookScanBuilder.prepare-pdf`.
- This session runs in the main workspace. The preparation tree is a different jj working
  copy with its own key namespace, so a change to its files is not part of this task's commit.
  Decide, and record in the running log, how a change that belongs in that tree is made before
  making it; if the route is not clear from the grove's own rules, stop and hand the question
  to the human with a recommendation and the evidence for it.
- A finding that is real but demands the plan be rethought becomes a new producer review chain
  beside the leaf, not an in-session redesign.

## Done when

- Every finding in `book-reconstruction-k6` has a recorded classification in this leaf's
  running log, with the evidence that decided it.
- The changes the real findings call for are made in the tree that owns each file, without
  choosing a correction algorithm, interface technology or landing mechanism the evidence
  does not yet support, and without launching drivers.
- `page-geometry-k4` and `corrected-book-k5` remain consistent with the root brief after the
  changes, and no live leaf that consumes this plan is left depending on an unresolved finding.

## Notes

Keep the preparation/processor boundary: one prepared PDF in, no collection-folder discovery.
This leaf reshapes the plan; it does not run the experiment or implement preparation.
