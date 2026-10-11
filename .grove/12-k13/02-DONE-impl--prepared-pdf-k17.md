# prepared-pdf-k17

## Goal

Finish the complete PDF-producing preparation command from the verified preview,
install `bookscan prepare`, and satisfy the parent node's entire charter before
geometry consumes a prepared PDF.

## Context

- Read all of `docs/specs/prepared-pdf.md` and the parent node's full Done when.
  Every write, preservation, runtime-validation, fault and render acceptance
  obligation remains binding; this leaf is not merely a copying adapter.
- `prepared-preview-k16` delivers phases 1–5 and stability checking, locked
  packaging, test-owned fixtures and preview evidence. Its commit is found by
  handle; `README.md` and `docs/acceptance/prepared-pdf.md` describe the exact
  current boundary. The retained preview report establishes planning only.
- Reuse the shared parser/reporting/selections, read-only PDF gates, immutable
  graph/geometry projection and source-lifetime operation. Extend the operation
  while its sources remain open; do not write from a closed/cached preview Plan
  or duplicate source gates. Callers must still supply selections/destination,
  never PDF graphs or a write protocol. Every invocation reopens/hashes sources.
- Immutable snapshots store scalar values, encoded bytes and explicit node
  references. Comparison must track source/output node pairs and ignore storage
  identities/sharing; annotation owner references, markers, seven geometry
  values, versions/extensions and warnings have separate required checks.
- The historical experiment/report are frozen. Product fixtures are under tests;
  malformed extensions use byte-authored fixtures because the writer repairs
  some invalid declarations on save. Existing qpdf-warning/recovery controls
  demonstrate their library observations. Current setup does not pin uv/Task;
  repeat actual recipe forwarding after tooling/recipe changes.

## Done when

- Install the public console entry and `prepare:run` only with complete normal
  writing, all specified help/JSON/errors and dry-run/write parity. Retire the
  temporary preview module/recipe or route it through the complete command and
  verify it. Public ordinary checks use `uv run --locked bookscan prepare`;
  signal/kill checks launch the synced console script directly and record its PID.
- Implement retained-page copying, all lossless stream save controls, independent
  fresh hints, numeric header/catalog version and merged ADBE tuple save controls.
  Reopen without recovery; recursively compare every retained type/scalar/key/
  array/raw stream through cycles, including masks/DecodeParms/JBIG2Globals.
  Check annotation ownership/indirection, marker non-aliasing, page count/order,
  all seven geometry values, effective version/extensions and every warning.
- The operation owns stage→save→validate→source recheck→commit; its private
  staged handle lends one seekable stream. Implement exclusive unpredictable
  mode-0600 dot-prefixed temporary names, final startup-umask mode, flush/fchmod/
  fsync, atomic no-clobber link, signal-blocked final cancellation/link/state
  region, pre-commit cleanup and all post-commit success/warning rules. No
  replacing rename/copy fallback or public fault flags.
- Run all parent-specified public/private fault checks: planned-then-stage-fails,
  copy/save/reopen/mismatch/source-change/permission/mode/flush/fsync/link/race,
  cleanup/delivery, real pre-region/in-region/post-link signals, writing and
  after-link SIGKILL with observed barriers, complete destination/two-name
  evidence and no surviving writer. Preserve sentinels/original digests.
- Verify every source gate in both dry-run and writes, and every nested graph,
  geometry/dictionary/marker mutation against the runtime comparator. Extend
  the same collection/Poppler-independent `prepare:check`; no test-only successor.
- Deliver `prepare:acceptance` synthetic/real/all modes and every matched 300-dpi
  render/geometry/raw-resource assertion in the parent. Synthetic requires no
  collection; real/all use an explicit root and unused external artifact
  directory. Freeze/digest all measurement inputs and record per-item results.
- Run new/changed and affected tasks, including actual spaced-path/exclusion
  forwarding through `prepare:run`. Update usage/spec implementation wording
  only after public command verification. Record full-page and useful-zoom
  comparisons in the acceptance note and hand them to `page-geometry-k4` for
  its separate preparation response; `corrected-book-k5` owns disposition.
- Assess an earned product/node `review-impl` after the artifact exists. If
  required, insert it at the root before `page-geometry-k4`, naming the completed
  `prepared-pdf-k13` producer (and this implementing leaf for its diff), so
  retiring this child can close the implementation node and name the creator
  run on that external review. Do not add an in-session reviewer beside it.
  Review creates integration lazily before consumers. Reconcile the complete
  node/root contracts; keep geometry/processor/optional-cleanup work live.

## Notes

This is the second and final declared implementation handoff, including its
own checks/docs/real acceptance. No adapter-only or real-acceptance-only child
satisfies it. Do not weaken gates to make the samples pass. No geometry, OCR,
cleanup or GUI belongs here. Human visual acceptance remains explicitly pending
until the assigned consumer records it. No driver is launched.

## Decisions (running log)

The integrated design and reviewed parent charter already settle the public
behaviour and ownership; implement them inline without another design approval
or a competing reviewer. Tier 2 graph generation `2026-10-11T04:41:50Z` has no
recorded gaps on existing evidence paths; missing proposed paths are new files.

Implementation sequence: first failing public write/order tests; then reconstruct
retained page snapshots into a fresh PDF while sources remain open, compare
source/output node pairs independently of sharing, and validate markers,
annotation owners, geometry and versions. Add the private staged stream and
signal-protected no-clobber publication; exercise faults and observed OS-signal
windows. Finally run frozen synthetic/real 300-dpi acceptance, reconcile usage
and consumer handoffs, and assess an external product review before retirement.

Reconstruction uses the already gated immutable encoded graph rather than
mutating copied source dictionaries: this excludes discarded keys by
construction and preserves nested raw stream bytes/cycles. Every write creates
its snapshot inside the source-lifetime operation, never from a closed preview
plan. Official pikepdf 10.16.0 save source and API were fetched; preserve decode
level none, disable compression/recompression/normalization, and supply tuple
min_version when an accepted ADBE level is present.

The pinned writer elides `/Filter` on zero-byte encoded streams despite decode
level none and disabled compression. Reproduced both reconstructed and foreign
stream copying; do not relax source gates or the comparator. Preserve the full
encoded dictionary through a temporary randomly named reachable dictionary,
then restore the affected zero-byte objects in a standard ISO 32000-1 §7.5.6
incremental revision inside the same private stream. Validation independently
reopens the final bytes and checks the exact graph. Empty-form, static-appearance
and discarded-key acceptance now write successfully. This extra serialization
path earns particular scrutiny in the external product review.

Real signal instrumentation showed that checking sigpending after blocking
misclassifies a signal arriving inside the region. Snapshot pending cancellation
before blocking; then protect link and the committed-state assignment. Tests
observe pending/pre-region, immediately-after-block, before-link, committed and
cleanup windows against the installed writer PID. No public fault flags are added.

Numeric source-version tests found qpdf's fresh-document PDF 1.3 floor; verified
it in the pinned QPDF.cc source. Choose max(1.3, all effective source versions),
which satisfies the spec's at-least rule and validates the chosen exact output.
Real EPIPE checks also caught interpreter shutdown replacing an existing source
error exit with 120; track delivery failure for every result and redirect broken
stdout before shutdown, preserving original errors, dry-run exit 5 and written
exit 0. Private mode checks cover startup umasks 027/077/777, and real flush faults
exercise the completed stream's flush method rather than bypassing publication.

The initial real render exercise matched every required page, but an instrument
edit during that run invalidated its digest measurement. Discard it as evidence;
finish edits, then rerun all modes with frozen inputs and retain only matched
before/after subject digests. No source fixture or historical report was edited.


Final verification: `task prepare:check` passed 199 tests plus Ruff format/lint
and strict pyright. Locked setup and actual public help/Task forwarding passed.
Frozen synthetic, real and all acceptance modes passed separately; before/after
subjects still matched at retention, and every per-item observation agreed
between separate modes and the combined run. All covers/music/spread/landscape/
JBIG2 fixtures matched exact 300-dpi pixels, seven geometry values and encoded
resources. Reports are retained in `docs/acceptance/prepared-pdf-*-report.json`;
full-page/native-detail paths and pending user response are in the acceptance
note and `page-geometry-k4`. Historical experiment/report and preview report
remain byte-unchanged; the lock also stays unchanged because scripts add no
new dependency.

The finished preparation subsystem is a load-bearing handoff with irreversible
publication and an additional encoded-empty stream serialization seam, so it
earns an external `review-impl` at the root before `page-geometry-k4`, reviewing
`prepared-pdf-k13` with this child's diff. No in-session reviewer was spent.
The complete parent Done when is delivered by its two children; source gates,
full writes, runtime/fault verification, all acceptance modes, reusable tasks,
usage/spec wording and explicit visual-response ownership are reconciled.
Promote the completed command/evidence/review handoff to the root brief. Close
`prepared-pdf-k13`; root geometry/processor/optional-cleanup obligations remain
live. No ADR convention changed and no driver is launched.
