# book-reconstruction-k3

## Goal

Plan the smallest independently useful increments for the personal two-stage
book reconstruction workflow, grounded in the settled requirements and the
correction-method evidence. Grow only the work that can now be stated precisely.

## Context

- `plan-k1` records the confirmed user decisions and inspected inputs.
- `scan-geometry-k2` precedes this leaf; read its survey at
  `docs/research/scan-geometry.md` before deciding the correction trial.
- The preparation stage merges explicitly chosen covers and content into one
  PDF. The main stage processes that single PDF without discovering content or
  covers across the collection folders. The user's shell supplies the batch
  orchestration.

## Done when

- The first independently useful increment and its concrete real-PDF acceptance
  cases are identified. Demonstrating within-page correction and image fidelity
  must precede treating a correction method as settled.
- Any unresolved design or visual-prototype questions needed before production
  implementation are expressed as bounded leaves in the appropriate order.
- The immediately actionable leaves have goals, inputs, completion conditions
  and the agreed test seams. Remaining work whose shape is still unknown stays
  in the brief rather than becoming a speculative full implementation tree.
- The plan preserves the explicit preparation/main-process boundary and a
  single-PDF main entry point, including tests that run without the source
  collection folders.
- The first implementation work includes a root Taskfile once reusable setup,
  fixture and verification commands are concrete; new tasks must be verified.

## Notes

This is a personal workflow on the current Mac, not a general application.
Choose the least interface and packaging work that serves the agreed review
controls. Native packaging and an application-level queue are not requirements.

Plan through vertical, demoable slices. The main uncertainty is geometry
quality on real scans, including music notation and spreads, not PDF merging
alone. Use the research to choose a cheap trial and the necessary agreement
point before building the complete workflow. No implementation language, image
correction algorithm, or review technology was selected by requirements.

English OCR enables search and selection while corrected page images remain
visible. Covers may include front and back pages. All three book folders remain
in scope as input sources even though the main processor only sees one prepared
PDF. Original files must remain untouched.
