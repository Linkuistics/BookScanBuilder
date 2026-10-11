# prepared-pdf-k19

**Integrates:** prepared-pdf-k18

## Goal

Triage the findings of the implementation review `prepared-pdf-k18` and apply the
real ones to the preparation command before `page-geometry-k4` consumes it. Check
each finding against the code, the spec and the retained evidence rather than
agreeing with it, and classify it as a real defect, a visible trade-off that
needs a recorded decision, a contract stated unclearly, or noise raised for want
of context.

## Context

- Read the findings from the review's own commit and its `## Findings` section,
  not from this body. The reviewed producer is the preparation node
  `prepared-pdf-k13`; its final implementing leaf is `prepared-pdf-k17`, whose
  commit follows preview `587afb92`. Reconcile the findings' `file:line`
  coordinates, which are against the producer commit, with the working tree
  before changing anything: this leaf runs after the review and any intervening
  edit moves them.
- `docs/specs/prepared-pdf.md` and `docs/adr/prepared-page-hints.md` are the
  integrated design. A finding that would change a public error code, a
  preservation gate or the support domain is a design decision to record
  explicitly, not a silent repair.
- The review ran scratch probes against the committed product rather than the
  test suite, and did not re-run `task prepare:check`. Re-run the checks this
  leaf changes, plus the affected existing ones, with real signals where a
  finding concerns signals; a fix covered only by a mock does not close it.
- Human visual approval remains pending and is owned by `page-geometry-k4`;
  `corrected-book-k5` checks its disposition. Neither belongs here.

## Done when

- Every finding in `prepared-pdf-k18` has a recorded classification in this
  leaf's running log, with the evidence that decided it.
- Real defects are fixed with a regression check at the seam where they were
  found. Where the fix changes a retained acceptance claim, the acceptance note
  and any affected retained report are corrected or explicitly superseded by a
  new frozen run, not left standing.
- Findings classified as trade-offs or unclear contracts end in a recorded
  decision (spec, help text, or ADR if it clears that bar) instead of silence.
- The producer's retained evidence is not rewritten; changes are new, frozen
  and digested.

## Notes

This is triage, not a work list. The review's own severity ranking is the
reviewer's view; the integrating session decides. Keep geometry, OCR and
cleanup out of scope, and do not add a competing in-session reviewer beside the
scheduled chain.
