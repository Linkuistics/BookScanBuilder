# prepared-pdf-k9

## Goal

Establish the smallest public command and preservation contract that assembles
explicit source/cover selections into one prepared PDF, independently usable
before correction exists. Deliver a spec and only the ADRs the decisions earn.

## Context

Use the confirmed requirements in `plan-k1` and this root brief's preparation
acceptance cases. This leaf was migrated from preparation's `prepared-pdf-k4`
at revision `1ada47bd`; its local successor is `prepared-pdf-k10`.
The representative objects in `docs/research/scan-geometry-a.md` show why taking
only the first image object does not preserve a PDF page's visible content.

## Done when

- The durable design at `docs/specs/prepared-pdf.md` specifies explicit content
  PDFs/page selections, default order, requested reordering/exclusion, explicit
  front/back roles, placement and the already-assembled/no-cover case.
- It specifies a composable single-book shell interface, clear selection errors,
  source/output collision handling, output-write failure behavior, and original
  preservation. Blank/duplicate detection never authorizes silent exclusion.
- Choose the least local language/library/tool combination that can preserve
  complete selected PDF pages. Check material framework/library decisions
  against current primary documentation or installed source rather than memory.
  No required processor, queue, GUI or native packaging.
- Document the single-PDF successor handoff. If cover roles/provenance are needed
  downstream, choose how they survive without a required sidecar or collection
  search. Do not settle the processor's correction or OCR implementation here.
- The design gives concrete expected order and fidelity checks for the root
  brief's real and labelled fixtures, a public command test seam, and a small
  verified dependency experiment if PDF copying assumptions need evidence.
- State the first implementation's concrete Taskfile needs, commands when
  established, and original-digest checks. Specify `prepare:` recipes extending
  the one shared root Taskfile, retaining existing recipes and dependency setup.
  Human fidelity comparisons remain explicit; deterministic fixture assertions
  do not substitute for them.

## Notes

This is design work: specify the public test seam and validate copying
assumptions with a bounded dependency experiment if needed. The implementation
will test the actual working public command. `prepared-pdf-k10` owns
implementation decomposition. Do not write a schema-only or library-only
shipping plan: the useful unit is a working
preparation command plus its verification and usage instructions. The separate
geometry prototype is not a prerequisite for preparation. Preparation controls
selected PDF pages; the processor owns exclusion/reordering of book pages
created by a spread split. Keep both stages in this workspace. If this design
earns a review, insert it before `prepared-pdf-k10` consumes the agreement.
