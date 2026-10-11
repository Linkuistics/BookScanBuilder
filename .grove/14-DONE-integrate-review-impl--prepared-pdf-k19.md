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

## Decisions (running log)

- Bootstrap: mandate `prepared-pdf-k19`, review commit `ddb2595c`, producer
  `750cc07b`; the working copy was empty. Tier 2 graph/source verification used
  generation `2026-10-11T05:21:47Z`; all evidence paths had no recorded coverage
  gap and matching metadata. The root brief, glossary and integrated spec/ADR
  supply the existing design and authorization for bounded repairs.
- Finding 1 is a real defect: `copying.validate` converts every domain error
  other than `OUTPUT_INVALID`, including asynchronous `INTERRUPTED`. Convert
  only `SOURCE_UNSUPPORTED`; add real installed-writer SIGINT/SIGTERM probes
  within validation, source rechecking, final fsync and dry-run traversal.
- Finding 2 is a real defect: the raising handler survives beyond the guarded
  computation; stage acquisition has an ownership gap, and cleanup can itself
  be interrupted. Keep asynchronous cancellation for long normal work, record
  signals while acquiring/assigning and cleaning up owned resources, then check
  deferred cancellation before continuing. Once an error is selected, preserve
  its original exit through cleanup/reporting. Serialize inside the catch scope;
  freeze the result for delivery so later signals cannot raise or append a
  second JSON object. Document this reporting boundary explicitly. Tests must
  exercise real signals at the former gaps and repeated cancellation in cleanup.
- Findings 3 and 4 are visible accepted trade-offs, derived from `Node.raw`,
  the occurrence projections and per-page reconstruction. Both dry-run and write
  retain encoded bytes; copying deliberately duplicates cross-page resources.
  Record the review's bounded measurements as measurements of its fixtures,
  not a universal multiplier or whole-book forecast. Lazy snapshots/shared
  copying would rethink this adapter and are unnecessary for this Mac's bounded
  increment; do not redesign it under an integration leaf.
- Finding 5 is a real defect against positive rectangle extent: `box` tests
  ordered coordinates instead of nonzero width/height. Accept either diagonal
  orientation and preserve its original coordinates. For defaulted boxes,
  report the originating MediaBox/CropBox key while keeping sorted gate order.
  Add command-level reversed/degenerate rectangle cases and matched renders.
- Finding 6 is an unclear contract with a diagnostic defect: numeric negative
  PAGES after a role's path will be consumed as an expression and rejected as
  `INVALID_SELECTION` before sources open. Unknown options still fail invocation
  parsing. Pin the tests to that code and document the lexical exception.
- Finding 7 is a real setup defect by direct Taskfile/acceptance inspection:
  add the missing `pdftotext` check and run the setup recipe.
- Finding 8 is valid maintenance work: remove the unreachable parser preview
  flag, operation preview flag, `plan` wrapper and test-only `before_recheck`
  callback. Tests use the real dry-run request or instrument `Source.recheck`
  privately. The existing no-write traps protect this change.
- Retained producer reports remain frozen. New acceptance will use an unused
  external directory and a new report; the acceptance note will explicitly limit
  the old signal claims and distinguish historical subjects from this repair.
  Human visual approval remains owned by `page-geometry-k4`.
- Signal repair refinement: the new tests reproduced 12 signal failures (both
  signals at validation, acquisition, serialization, error cleanup and repeated
  cleanup) and seven selection/rectangle failures. An arbitrary-bytecode
  raising handler can also interrupt the entry into an exception handler itself;
  local masks would leave that lifetime gap. Use the review's record-only
  alternative with explicit source/page and pre-publication checkpoints.
  Cancellation may wait for the current hash/copy/validation/fsync operation;
  cleanup and chosen-error reporting retain their original result. This bounded
  control change preserves the existing masked hard-link commit protocol.
- Regression verification: the record-only repair passed all 20 new real-signal
  cases; the full `task prepare:check` passed 231 tests, Ruff format/lint and
  strict pyright. `task prepare:setup` synced the lock and found both `pdftoppm`
  and `pdftotext`. The reversed-corner rejection fixture was corrected to a
  genuinely zero-width rectangle; all three corner orientations are now checked
  at the public writer for MediaBox, CropBox and TrimBox. Private hooks pause once
  inside validation so cancellation can reach its boundary before the separate
  repeated-cleanup barrier. No implementation/instrument edits occur during the
  new frozen acceptance runs.
- Frozen acceptance completed in synthetic, real and all modes at
  `/private/tmp/bookscan-prepared-k19-{synthetic,real,all}`: 9/24, 5/10 and
  14/34 cases/pages. Each retained 38 real signal/kill observations and passing
  fault/validation JUnit results. The synthetic Task recipe was supplied a
  nonexistent collection setting and passed with no collection argument.
  All before/after subjects were rehashed against current files after completion;
  matching pages and all signal/kill outcomes agree item by item across modes.
  New reports are `docs/acceptance/prepared-pdf-k19-*-report.json` with SHA256
  synthetic `d6327a83570ae376d14ecfdafaba2433b4b876a436ec7a9d0893d198b039fdd9`,
  real `6bacb46276b22da38dc72a6db9b615f9b8e9737de29643537f92bbdc881b9dce`,
  all `c776f483ca65030526376329410fc504b2f450b8a1df164308922757b3cbf5a2`.
  All four producer/preview reports are byte-identical to `ddb2595c`. The
  acceptance note now limits their original signal claim and points future
  visual inspection at the current comparisons. No human approval is inferred.
- Retirement check: all eight findings are classified and closed through bounded
  code repairs or explicitly accepted spec/help limits. Role-hint semantics and
  their ADR remain current. No competing reviewer or redesign chain was needed.
  The root still has live geometry/progress-planning work (`page-geometry-k4`,
  `corrected-book-k5`), so this retirement closes no ancestor. No live review names
  this integration as its producer; no Creator line is due. Seal this focused
  repair and its DONE rename before signalling dispatch.
