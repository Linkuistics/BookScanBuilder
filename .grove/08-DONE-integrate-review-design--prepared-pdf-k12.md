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

## Decisions (running log)

The findings were read from `5d0a8e1d`, the commit retiring `prepared-pdf-k11`,
and checked against producer `2973d3e3` and the current artifacts. This session
repairs the contract and dependency evidence; it does not implement preparation.

- **Finding 5 — real issue.** Installed pikepdf 10.16.0 `Pdf.save` dispatches
  paths through `_io.atomic_overwrite`; a pre-created path takes a second
  temporary file and replacing rename. Specify an exclusively created,
  dot-prefixed `.bookscan-prepare-<random>.tmp` stream, with no PDF suffix and
  final mode `0666 & ~umask` set before publication. The caller owns that stream.
- **Finding 7 — contract stated unclearly (content), real trade-off (container),
  real issue (missing ADR test).** `content` says only that this invocation did
  not assign front/back; it does not classify a book page. Keep the versioned
  top-level marker as an inert, advisory interchange convention. `/PieceInfo`
  has a modification-date convention, but the processor cannot rely on arbitrary
  editors maintaining that convention; hints must be reviewed regardless.
  Persisted PDFs plus a separate consumer make reversal costly, the private
  container is non-obvious, and sidecar/PieceInfo alternatives exist: all three
  ADR conditions hold. Record `prepared-page-hints` and cite it from the spec
  and root brief.
- **Finding 11 — contract stated unclearly.** The zsh manual explicitly permits
  history expansion inside double quotes and suppresses it inside single quotes.
  Specify single quotes in the spec/help. Ask the user about retaining the
  proposed grammar; absent an answer, leave its confirmation explicitly with
  `prepared-pdf-k10` rather than choosing a new public syntax here.
- **Finding 10 — real issue, with a visible support trade-off.** A read-only
  pikepdf 10.16.0/qpdf 12.4.2 two-occurrence probe produces distinct page objects
  but the same indirect annotation object. Reject repetition of an annotated
  source page in this increment, including invisible links, before either
  dry-run or copying; test repetition and annotations together. This avoids
  promising annotation reconstruction without evidence.
- **Finding 8 — real issue.** The real Algorithm Design source declares ADBE
  base 1.7/level 3. The old probe omitted it, and a constructed catalog `/Version`
  override leaves pikepdf's `pdf_version` property at the header version.
  Explicitly compute the numeric maximum of header/catalog versions. Keep
  dictionary-valued extension declarations and check them after saving;
  reject array-valued declarations in this bounded increment. Update and rerun
  the experiment before citing its expanded evidence.
- **Finding 1 — contract stated unclearly.** The old “unknown feature” and
  “self-contained” clauses provided no test oracle. ISO 32000-1 tables 28/30
  identify catalog/page keys, §7.3.8 identifies external stream data and §12.5
  defines annotations. Replace the clauses with explicit document/page/reachable
  gates, a binary raw-traversal warning policy, one-stream static appearances,
  and an exact invisible-link rule. Keep metadata/private keys from becoming a
  guessed strict allowlist. Bound support to static PDF 1.0–1.7 and the observed
  ADBE 1.7/levels 1–3; unsupported versions/extensions are an explicit trade-off.
  Re-run the six-source inventory; do not import the review's whole-collection
  counts into the support claim.
- **Finding 2 — contract stated unclearly.** Dry-run performs all source gates,
  selected-graph raw reads, digests/stability checks and destination preconditions,
  writing nothing. It cannot validate an output that does not exist or reserve a
  destination. State the remaining copy/save/validation/I/O/race failures in help.
- **Finding 3 — real issue.** Link success fixes `written`/exit 0. Defer SIGINT
  and SIGTERM over the final cancellation check, link and commit-state recording;
  catch post-commit signals as warnings. Cleanup and stdout/EPIPE failures do not
  turn a published PDF into `INTERRUPTED`. Broken stdout cannot carry its own JSON
  warning; stderr is best effort. Add both dry-run and post-commit view branches.
- **Finding 4 — contract stated unclearly.** Define the complete error set,
  one-first-error phase order and early JSON detection for parser failures.
  Zero-page source is `SOURCE_EMPTY`/3; concurrent occupation is
  `OUTPUT_EXISTS`/4; private-file permission failure is `WRITE_FAILED`/5.
  Required-output/arity/unknown-option/singleton failures are `INVALID_ARGUMENT`/2.
- **Finding 6 — real issue.** The direct-image experiment fingerprint is not a
  runtime validation contract and omits nested dictionaries/globals. Specify
  recursive source-projection/output graph equality including raw streams and
  decoder dictionaries, with cycles and rebuilt/discarded entries accounted for.
  The copy adapter validates a stream lent by a staged publication handle;
  the operation orders stage/save/validate/source-recheck/commit. Expand the
  bounded fingerprint only enough to expose nested/raw resources, without
  pretending the probe implements the command's full comparator.
- **Finding 9 — real issue.** Render equality cannot prove Bleed/Trim/Art boxes
  or UserUnit. ISO 32000-1 table 30 makes the three optional boxes page-local
  with CropBox defaults. Specify all five boxes plus Rotate/UserUnit in runtime
  and command acceptance, and extend the synthetic probe with distinct values.
- The expanded probe's first run failed its new extension assertion: assigning
  `/Extensions` then saving with `min_version="1.7"` writes no declaration.
  A two-case BytesIO reproduction isolates the writer control; the documented
  `min_version=("1.7", 3)` retains ADBE level 3. Specify that control and rerun
  with a fresh output directory. Previously failing TrimBox and decoder-global
  mutation checks now distinguish the altered values; retain full recipe
  evidence before claiming the expanded probe is complete.
- ISO 32000-1 §12.5.2 also confirms finding 10's format constraint: one
  annotation dictionary belongs to one page's Annots array. This removes the
  review's “plausible” qualifier for the PDF 1.x domain supported here.
- Verification completed through `task prepare:copy-experiment
  ARTIFACTS=/tmp/bookscan-prepared-pdf-k12-verified`: eight real and six labelled
  page comparisons matched exactly; all six real sources and both generated
  label sources retained their before/after digests. Script and Taskfile digests
  match the retained report. Each real item's source/page/role/render result
  matches the prior retained report; new geometry/resource checks and ADBE 1.7/3
  assertions pass. Ruff E/F/I checks pass. This is dependency evidence, not
  public-command acceptance or user visual approval of a preparation product.
- `task prepare:design-render` regenerated both SVGs. The served assembly and
  publication deep links were inspected in Chrome after correcting D2's
  semicolon-as-statement-separator rendering; both graphs are readable and show
  their intended connected branches. The default serve port was occupied, so
  the existing recipe was exercised with `DESIGN_PORT=8771`.
- The user answered **“Keep the proposed grammar”** before retirement.
  Confirm single-quoted `!` exclusions and ascending/descending ranges in the
  spec and `prepared-pdf-k10`; remove the interim open question. No public error,
  gate, dry-run, validation or publication policy is left for planning to invent.
  The repairs do not require a new producer/review chain; no in-session reviewer
  was used. The root still has live preparation planning, geometry and processor
  work, so this retirement closes no ancestor node.
