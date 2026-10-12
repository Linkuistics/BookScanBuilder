# rotation-processor-k46

**Integrates:** rotation-processor-k45

## Goal

Triage rotation-processor-k45's findings against the agreed page/book geometry
Design v2. Apply the real ones to the spec, ADR set, design views and glossary
before its implementation planner (rotation-processor-k44) consumes them.

## Context

- Read the findings from rotation-processor-k45's own committed review leaf and
  commit, then re-derive each against the current tree. Each finding cites
  `docs/specs/rotation-processor.md` at commit `31b18570`, so confirm the lines
  have not moved.
- The producer is rotation-processor-k41: its spec, `docs/adr/geometry-review-handoff.md`,
  `docs/design/rotation-processor/` (edit the Markdown/D2 sources and regenerate
  through the existing render recipe) and the actual verbatim **“agreed”** scope
  recorded in its running log and the spec's Agreement section.

## Done when

- Every finding is classified with its reason: a contract stated unclearly,
  valid and actionable, a visible accepted trade-off, or noise. A rejected
  finding is recorded with evidence, not silently dropped.
- Accepted fixes land in place in the current-state spec/ADR/glossary set and
  the regenerated visual document, with their citations reconciled.
- Decide whether a change alters the signed product shape, scale policy or test
  seams, beyond a clarification of what was agreed. If it does, present that
  specific change to the human and record the verbatim scoped reply before the
  planner runs. Silence, or an unavailable reply, is no agreement. Do not re-open
  the agreed design through an identical response loop.
- Verify affected recipes and checks after edits, with the frozen-subject
  discipline the root brief requires.

## Notes

The review's finding list is its own; this charter deliberately does not copy
it. A substantial redesign surfaced here externalises as its own producer
review chain beside this leaf rather than growing this session. OCR and
reordering stay external, and within-page/full-default acceptance stays with
k28 and its successors.
