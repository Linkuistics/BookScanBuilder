# prepared-pdf-k10

## Goal

Cut the smallest complete working preparation implementation from the agreed
design. Keep the product usable at every handoff and preserve its independence
from correction, OCR and review technology.

## Context

Read the design delivered by `prepared-pdf-k9`, including
`docs/specs/prepared-pdf.md` and its cited ADRs. The root brief supplies the
fixed acceptance fixtures and public-command seam.
This leaf was migrated from preparation's `prepared-pdf-k5` at `1ada47bd`.
`prepared-pdf-k12` repairs the reviewed gate, error, dry-run, validation and
publication contracts. The user confirmed the spec's page-expression grammar
(single-quoted `!` exclusions and ascending/descending ranges) during that
integration. Use the
integrated spec and `prepared-page-hints` ADR as current design inputs.

## Done when

- Cut the immediately actionable implementation leaf with concrete inputs,
  expected page order/roles, fidelity and failure outcomes. Keep page copying,
  selections, public entry point and its verification together wherever a
  smaller cut would leave no useful working command.
- Its first implementation includes a root Taskfile once setup/fixture/check
  recipes are concrete. Extend the existing shared file with `prepare:` recipes
  and reconcile setup dependencies in place. Run every introduced/changed task
  and existing tasks affected by the combination before relying on the file.
  Use existing tool mechanisms instead of duplicate scripts.
- Preserve full visible PDF pages from all three book folders, explicit cover
  roles, no-cover/already-assembled input, user-controlled exclusions and
  unchanged originals. Include real-PDF render/digest comparisons and labelled
  deterministic role/order cases through the public seam.
- Commission further slices only if each is independently useful and remains
  green. Unknown work stays in the brief; do not grow a speculative subsystem
  tree or add a separate test-only horizontal leaf.
- Keep any earned review/integration ahead of work consuming its artifact.
  Insert the preparation implementation, further required slices and any earned
  review/integration ahead of `page-geometry-k4`, so this tree completes the
  first useful product before geometry and processor work. Commit product,
  durable docs and task retirement in this workspace; no branch landing or
  separate product grove is needed. Retain the root's end-to-end verification.

## Notes

Preparation can finish and be used before a correction algorithm succeeds. It
does not split landscape pages, change visible geometry/appearance, add OCR or
discover a collection. The processor's final isolated-input test belongs to
its own increment; preparation must provide a PDF that can be supplied to it.
Preparation's reordering/exclusion operates on unsplit PDF pages. Processor
design owns equivalent user controls for split book pages. No driver is
launched here.

## Decisions (running log)

Preparation has one independently useful implementation boundary: the complete
`bookscan prepare` command with selection/role calculation, lossless copying,
source gates, runtime validation, advisory markers and no-clobber publication.
Parsing or copying alone leaves no usable command satisfying the agreed design.
Keep packaging, shared Taskfile integration, synthetic/fault verification and
real-fixture acceptance with that implementation; cut no horizontal setup,
adapter or test-only siblings and create no node for work that is one artifact.
The root already records the dependency-ordered preparation, corrected-book and
optional-cleanup increments in the single tree the user chose.

The preparation implementation must precede `page-geometry-k4`. Its dense
preservation and publication acceptance obligations earn a `review-planning`
leaf for this handoff, inserted before implementation. That review consumes
this producer's committed task tree and the integrated design, and cuts an
integration only for findings worth acting on. Implementation decides whether
its finished product earns `review-impl`, inserting any required review before
geometry; no future implementation review or integration is pre-created here.
