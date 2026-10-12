# rotation-processor-k52

**Integrates:** rotation-processor-k51

## Goal

Triage rotation-processor-k51's findings against the committed plan from
rotation-processor-k44 and apply the real ones to the planned subtree before its
first implementation (page-review-k47) runs. Reshape tree and charters only; this
session changes no product, spec, ADR, experiment or evidence.

## Context

- Read the findings from rotation-processor-k51's own committed review leaf and
  commit, then re-derive each against the tree as it now stands. The review cites
  line numbers at commit `d3eaea10`; filenames there carry positions that this
  integration's insert shifted, so resolve every task by its stable handle.
- The producer is rotation-processor-k44: its four charters
  (page-review-k47, rigid-pages-k48, spread-pages-k49, book-placement-k50), the
  root brief's *Reviewed-design working slices* contract, and the consumer clauses
  it added to corrected-book-k28, appearance-cleanup-k22 and
  workflow-acceptance-k23. The agreed v2 spec and both ADRs are read-only inputs.

## Done when

- Every finding is classified with its reason: a contract stated unclearly, a
  real issue, a visible accepted trade-off, or noise raised for want of context.
  A rejected finding is recorded with evidence rather than dropped.
- Accepted fixes land in place in the root contract and the affected charters,
  without removing any original criterion, protocol or consumer ownership. Where a
  finding requires a stage to be cut narrower, the cut names its complete public
  handoff and keeps the remaining concrete work before its consumer; it creates no
  schema-, renderer-, display- or test-only leaf.
- Decide whether any change alters the agreed v2 design, scale policy or test
  seams beyond clarification. If so, state it as a precise human question with a
  recommendation and evidence rather than silently editing the spec.
- Verify the tree afterwards: handles resolve in the declared order, k27's body
  and the root Done when are unchanged, and no root/consumer criterion was lost.

## Notes

The finding list is the review's own; this charter deliberately does not copy it.
Substantial redesign externalises as its own review chain beside this leaf. No
in-session reviewer beyond the one narrow allowance, no driver, no Norwegian study
and no identical response loop. Within-page and full-default acceptance stay with
corrected-book-k28 before appearance-cleanup-k22 and workflow-acceptance-k23.
