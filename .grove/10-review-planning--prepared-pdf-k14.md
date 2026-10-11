# prepared-pdf-k14

**Reviews:** prepared-pdf-k10
**Creator:** run f9140e6a-5fb4-4ed7-beeb-46ecd50735ff

## Goal

Adversarially review the preparation implementation handoff created by
`prepared-pdf-k10`. Establish whether its task tree can deliver the smallest
complete working preparation increment without losing reviewed preservation,
publication or acceptance obligations.

## Context

Find the producer's committed diff by its stable handle. Its artifact is the
implementation leaf `prepared-pdf-k13` and the updated root brief; reconcile
them with the current tree rather than relying on positional paths.

Read `docs/specs/prepared-pdf.md` and `docs/adr/prepared-page-hints.md` as the
integrated design. `prepared-pdf-k12` repaired the design and records the user's
confirmation of single-quoted exclusions and ascending/descending ranges.
`docs/research/prepared-pdf-copy.md` and its bounded experiment explain what
dependency evidence exists and what command acceptance still needs to prove.
`Taskfile.yml` already owns experiment/diagram recipes.

## Done when

- Inspect the producer's actual diff and record actionable findings with
  specific evidence and impact, or explicitly record no actionable findings.
  This is inspection only; do not implement the command or rewrite its plan.
- Challenge increment boundaries and one-session feasibility: do selection,
  copying, gates, validation and publication truly need one complete command
  handoff, and are any smaller green independently useful stages possible under
  the agreed design? A horizontal adapter/setup/test-only cut is not a useful
  product handoff. If the session scope is impractical, state the concrete seam
  and green behaviour that would justify a different cut, rather than merely
  counting requirements or relaxing the approved public contract.
- Check traceability from every spec section/root preparation acceptance case
  into the implementation obligation and public verification seam. Focus on
  inherited/default seven-value geometry, nested streams/decoder globals,
  annotations/repetition/ownership, effective version/extensions and independent
  advisory markers; the old bounded fingerprint cannot prove runtime integrity.
- Challenge error/dry-run/publication coverage: first-error phases, identical
  source gates/raw warnings in both modes, source stability and output aliases,
  no-clobber races, commit-region signals, pre/post-commit cleanup/reporting and
  abrupt-kill outcomes. Verify fault checks can observe the promised state at
  bounded private seams while ordinary acceptance exercises the installed CLI.
- Check real-source order/roles, exact renders, canvas/raw-resource evidence,
  unchanged digests and measurement provenance. Distinguish automated checks
  from human visual approval. Confirm Taskfile integration remains reusable and
  collection-independent synthetic checks do not import runtime dependencies
  from geometry, OCR, diagrams or acceptance tools.
- Verify the order keeps this review and any required integration before
  `prepared-pdf-k13`, and preparation/product review before `page-geometry-k4`.
  The root must retain processor-isolated end-to-end verification and the
  optional-cleanup successor; preparation alone cannot finish this workstream.
- If findings warrant action, cut `integrate-review-planning` as the next live
  sibling before implementation. Its body carries this review's stable handle
  under `**Integrates:**`, not a transcribed finding checklist. If no findings
  warrant action, cut no integration and retire normally.

## Notes

The review concerns this planning artifact, not a fresh choice of preparation
syntax, library, hint container or geometry algorithm. Re-derive whether the
plan carries the integrated contract; do not treat the producer's claim of
completeness as evidence. No in-session reviewer is commissioned by this leaf.
