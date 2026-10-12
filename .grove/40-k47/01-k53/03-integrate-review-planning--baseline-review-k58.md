# baseline-review-k58

**Integrates:** baseline-review-k57

## Goal
Triage baseline-review-k57's findings against the committed baseline-review-k55
plan and apply the real ones to the planning artifacts, so that
baseline-delivery-k56 asks the human a complete, answerable question about the
changed baseline boundary.

## Context
- Read the findings from baseline-review-k57's own committed review leaf and
  commit, then re-derive each against the current tree. Its line references are
  to the tree at k55's commit; k56's filename position has since shifted by one
  at this insert, so resolve tasks by handle.
- The producer is baseline-review-k55: its Boundary assessment, Preserved closure
  coverage, the k53/k47/root Decomposition paragraphs and k56's charter. The
  agreed v2 spec, both ADRs and k46's F9 disposition govern; none is edited here
  unless a finding is genuinely real against them.
- Nothing here answers k56's question, asks the human, or authorises the finite
  interim. A repaired charter is still only a proposal.

## Done when
- Every finding is classified with its reason: a contract stated unclearly,
  valid and actionable, a visible accepted trade-off, or noise. A rejected
  finding is recorded with evidence, not silently dropped.
- Accepted repairs land in place in k56's charter and in whichever brief states
  the affected fact, with citations reconciled by handle; no copy of the
  reviewer's finding list becomes a charter or a second planner.
- Check that k53's and k47's original Goal/Done when, the root Done when, k27's
  source-only body and the k54 -> k48 -> k49 -> k50 -> k27 -> k28 -> k22 -> k23
  order are unchanged, and that no spec, ADR, Taskfile or product file is edited
  without a finding that earns it.
- Decide whether any repair changes the signed product shape or the question the
  human must answer beyond clarifying it. If so, k56 presents that specific
  change and records the verbatim scoped reply; no signature is inferred and no
  identical response or planning loop is created.

## Notes
The review's finding list is its own; this charter deliberately does not copy it.
Substantial redesign of the interim interface is the changed-boundary design's
work, after an actual reply, and is externalised rather than grown here. No
in-session reviewer, driver or product work.
