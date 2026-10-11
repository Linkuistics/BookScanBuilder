# prepared-pdf-k12

**Integrates:** prepared-pdf-k11

## Goal

Triage the findings of the design review `prepared-pdf-k11` and apply the real ones to
preparation's design before `prepared-pdf-k10` plans the working implementation from it.
Check each finding against the artifacts instead of simply agreeing with it. Classify each
as a contract stated unclearly, a real issue, a visible trade-off, or noise.

## Context

- Read the findings from the review's own commit and its `## Findings` section, not from
  this body. The reviewed producer is `prepared-pdf-k9`. Its artifact is
  `docs/specs/prepared-pdf.md`, with the copying evidence in
  `docs/research/prepared-pdf-copy.md`, its report and `experiments/prepared_pdf_copy.py`,
  and the views under `docs/design/prepared-pdf/`.
- The review's collection evidence came from disposable read-only probes. Re-derive any
  count the spec will rely on. Open sources read-only and keep derived files outside
  `/Volumes/Glass/Book Conversion`.
- Library behaviour cited by the review (pikepdf 10.16.0 `save`/`atomic_overwrite`, and
  qpdf's handling of repeated pages) should be confirmed against installed source or
  current primary documentation before the spec relies on it.

## Done when

- Every finding in `prepared-pdf-k11` has a recorded classification in this leaf's running
  log, with the evidence that decided it.
- The real findings are applied to the spec, research note, design views and their
  rendered output as each requires. The ADR set is reworked only if the ADR test is met.
- Any choice that changes the user's public command grammar is either confirmed with the
  user or recorded as an explicit open question for `prepared-pdf-k10`.
- Any change to the experiment, the Taskfile or the views is rerun or rerendered through
  its existing `prepare:` recipe before the spec cites it.
- `prepared-pdf-k10` can cut its implementation without having to invent a public error,
  dry-run, gate, validation or publication contract that is still unsettled.

## Notes

A finding that is real but requires the preparation design to be rethought, rather than
repaired, becomes a new design review chain beside this leaf, not an in-session redesign.
Keep the preparation/processor boundary: one prepared PDF in, no collection discovery,
no geometry, cleanup or OCR in preparation. Do not implement the command here.
