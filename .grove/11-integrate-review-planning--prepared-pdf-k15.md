# prepared-pdf-k15

**Integrates:** prepared-pdf-k14

## Goal

Triage the findings of the planning review `prepared-pdf-k14` and apply the real
ones to the preparation implementation handoff before `prepared-pdf-k13` runs.
Check each finding against the artifacts rather than agreeing with it, and
classify it as a contract stated unclearly, a real issue, a visible trade-off or
noise raised for want of context.

## Context

- Read the findings from the review's own commit and its `## Findings` section,
  not from this body. The reviewed producer is `prepared-pdf-k10`; its artifact is
  the implementation leaf `prepared-pdf-k13` and the preparation increment's
  paragraphs in the root `_BRIEF.md`. Reconcile both with the current tree by
  handle, not position.
- `docs/specs/prepared-pdf.md` and `docs/adr/prepared-page-hints.md` are the
  integrated design and are not reopened here. `prepared-pdf-k12` already repaired
  that design; a finding that would change the public command, an error code or a
  preservation gate is a design question for a new design chain, not a repair in
  this leaf.
- The review checked two tooling claims (uv launcher signal forwarding, Task
  argument forwarding) from published documentation only. Confirm against the
  versions this repository pins or installs before the plan relies on either.
- Preparation's end-to-end consumers are `page-geometry-k4` and
  `corrected-book-k5`; keep their order and obligations intact.

## Done when

- Every finding in `prepared-pdf-k14` has a recorded classification in this leaf's
  running log, with the evidence that decided it.
- The real findings are applied to `prepared-pdf-k13` and, where the plan's
  sequencing or ownership changes, to the root brief. Where a finding changes what
  a later leaf must do, the obligation is written into that leaf's task file; no
  new future review or implementation chain is pre-created.
- The decomposition question the review raised about one-session feasibility is
  settled explicitly: either `prepared-pdf-k13` carries a declared fallback seam
  that keeps every handoff green and independently useful, or the log records why
  it fits. A horizontal adapter, setup or test-only cut is not an acceptable
  answer.
- `prepared-pdf-k13` can be implemented without its session inventing a
  verification boundary, a signalled process, a recipe-to-collection dependency or
  an owner for human visual acceptance.

## Notes

This session reshapes the plan only. It does not implement the command or edit
the spec, ADR, experiment or Taskfile. A finding that is real but requires the
preparation design to be rethought becomes a new design review chain beside this
leaf rather than an in-session redesign. Keep `prepared-pdf-k13` before
`page-geometry-k4`, and keep the root's processor-isolated end-to-end check and
optional-cleanup successor live. No driver is launched here.
