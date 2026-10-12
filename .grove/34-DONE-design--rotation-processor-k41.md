# rotation-processor-k41

## Goal

Establish the design agreement for a sole-PDF geometry processor: supported
per-page correction, safe spread/border handling, review/adjustment and book-wide
page alignment with explicit odd/even or left/right assignments. Export accepted
visible page images for separate third-party reordering and OCR. Deliver a spec
and only earned ADRs before implementation planning. The supported-rotation
increment still does not satisfy the root's within-page correction criterion.

## Current human scope — governs inherited wording below

The human's latest instruction removes processor page reordering and OCR from
this tool, and adds book geometry (page alignment/matching and odd/even pages).
Older assembly/reordering/aligned-OCR completion clauses below are historical
requirements and are no longer implementation or acceptance obligations. Preserve
all input occurrences and default order except genuine spread expansion; external
tools own subsequent reordering and OCR. Geometric edits export an image-only PDF,
with previous text layers omitted rather than left stale. Preparation's shipped
explicit assembly command remains available unchanged.

This design must now agree the alignment reference, common canvas/margins,
explicit page-side assignment and parity discontinuities, supported translation
and any scale policy, matched page-pair/group review, preservation/fallback and
their independent public/visual tests. Do not infer book sides from PDF ordinal,
cover roles or filenames. Covers/front matter/blanks require explicit matching
group and side semantics. No silent content loss, page removal, forced fitting
or geometric certification follows from a matching score or unflagged status.
The human has now replied **“agreed”** to revised v2 and scale-preserving matching;
the running log records the presented contract and actual reply scope. Draft v1's
unanswered agreement question was withdrawn by this change of scope.

## Context

- Read `geometry-policy-k40`'s committed plan and its actual review/integration,
  the complete `geometry-policy-k39` replies and `norwegian-measurement-k38`.
  The human answered “yes” to separating numerical admissibility from visual
  source review and “agreed” to considering a rotation-plus-flagged processor
  while nonrigid evidence continues. These are settled policies, not a chosen
  method, interface, language or accepted output. Synthesise them; do not
  re-interview either policy.
- Read the full `corrected-book-k21`, `staff-acquisition-k27` and
  `corrected-book-k28` contracts and k25/k30's confirmed choices. k27 then k28
  remain live in their relative order. k27 is source-only music acquisition;
  neither its observation protocol nor its outcome is replaced by this design.
  k28 owns within-page evidence/completion and full default acceptance, consuming
  this design and the actual intermediate working successors rather than
  commissioning the same initial processor design again.
- Read k31's full Norwegian brief/results, k34/k37's evidence repairs and
  `docs/experiments/norwegian-measurement.md`, including raw observers,
  packet/key/controls/canonical verification. Each half failed the fixed 16×
  grid addressing attempt before real marks/holdouts/masked extraction. There
  is no Norwegian field or corrected-output result. Source replies remain
  unavailable separately; real-anchor/output reactions are unperformed.
  This result rejects neither every instrument nor the vertical family.
- Preparation's shipped public contract is `docs/specs/prepared-pdf.md`;
  `docs/acceptance/prepared-pdf.md` and the prepared-page-hints ADR bind the
  ordinary sole-PDF handoff. Historical geometry/preparation views and their
  separate actual “Not inspected yet” replies remain owned by k27 then k28.
  Inspect `docs/experiments/page-geometry.md` and staff evidence when evaluating
  actual rendering/sampling assumptions. Existing wrappers are experiments,
  not a demonstrated production processor.
- Read current `appearance-cleanup-k22` and `workflow-acceptance-k23` contracts.
  They require the complete accepted default correction increment and final
  root criteria, not merely this intermediate export. Use the current workspace,
  tree and shared Taskfile; launch no driver.

## Done when

- Answer this exact design question: what smallest complete workflow lets the
  user turn one prepared or already-assembled PDF into a rotation-corrected,
  reviewed, searchable book while keeping unresolved distortion explicit and
  preserving a coherent path to later within-page correction? Agree the product
  shape and public/visual test seams with the human before implementation
  planning. Prefer the root's agreed preparation → sole-PDF processing/export
  seam. Present the design through the design skill's editable visual document,
  synthesising settled requirements and recording only genuinely new choices.
  Choose methods/technology from verified local or primary-source evidence,
  including exact installed APIs where material, rather than library memory.
- Record the actual human design reply verbatim, with the specific spec/version,
  product shape and public/visual test seams it covers. k39's “agreed” permits
  considering this increment; it does not sign this design. A coherent draft,
  internal review, elapsed response window, silence or an ambiguous/unavailable
  reply is no agreement or rejection. A drafted but unsigned design stays live
  for the human; cut no implementation planner and do not retire it as agreed.
- Specify complete full-page rendering, assessment of covers and previously
  processed pages, genuine spread detection/splitting and safe scanner-border
  removal/crop/rotation with content retained. Counterpoint20 is one landscape
  book page with both columns; Norwegian20 is a genuine spread. Shape, folder
  membership and advisory roles cannot decide those classifications. Define
  inspectable ambiguous/unsupported outcomes and manual review controls so an
  uncertain split/crop/angle cannot silently discard content or fail the book.
  Preserve colour, faint print, music, illustrations and already-correct pages.
- Specify the supported rigid-rotation decision and its confidence/evidence
  limits, plus unchanged/usable flagged fallback. Rigid tilt removal does not
  resolve within-page curvature or rotation variation. Define what is assessed,
  what is unknown and why a page is flagged; unmeasured nonrigidity cannot be
  treated as absence of distortion or a certified automatic “correct” status.
  Do not promise detection accuracy or invent thresholds without evidence.
  The accepted-image seam must admit later evidence-supported nonrigid edits
  without changing review/assembly/OCR semantics. Flags alone grant no correction
  or representative acceptance.
- Separate the universal limitation of unverified within-page geometry from
  per-page triage reasons and their recorded signals/observations. Explain what
  an unflagged page may claim: absence of a recorded triage trigger is no
  geometric certification. State which signals exist and their limitations;
  any ranking/threshold needs evidence, and triage ranking is no verification.
  Specify how the universal limitation and per-page dispositions remain
  inspectable through review and final handoff, including what the exported PDF
  and any review record convey. Do not assume either a whole-book review queue
  or verified nonrigidity merely from the word “flagged”.
- Design flagged-page review and adjustment of ANY page, including one that was
  not flagged, with matched original/current full-page and native-detail views,
  explicit acceptance/reversion and final export reflecting accepted edits.
  State the actual supported adjustment operations and their limitations rather
  than implying unproved automatic nonrigid correction. Define accepted-image
  identity/versioning and invalidation at the behaviour level. Its representation,
  working reader, review controls and export belong to the same useful handoff;
  no schema-only, OCR-engine-only, display-adapter-only or test-only stage.
- Answer the review-state lifecycle: where accepted/reverted edits, triage,
  split provenance and assembly decisions live; whether/how partial review
  persists and resumes; and what interruption, reprocessing the same PDF or
  changed source/image versions invalidates. Distinguish processor-owned state
  from the sole-PDF input boundary: an ordinary PDF needs no supplied sidecar
  or source rediscovery. Decide what state, if any, is embedded in exported PDFs
  and its compatibility/loss behaviour against the prepared-page-hints ADR.
  Choose only earned durable records for the resulting design decisions.
- Preserve default input order and post-split half provenance; let the user
  explicitly move/exclude any created book page, including blank/duplicate halves,
  before final OCR/export. Flags never delete pages. Require a genuine spread
  with a blank half and duplicated half, checking both the unchanged default
  roster and explicit exclusion/movement, retained geometry and final order.
  Preparation's unsplit PDF-page selections do not satisfy this processor scope.
- Specify final English OCR over accepted visible images and explicit handling
  of earlier OCR/old text. Demonstrate a tiny actual-English searchable/selection
  fixture and an earlier-OCR fixture at the proposed seam; historically empty
  text pages do not qualify. Prevent silent OCR rotation, recolouring or replacing
  images, stale/duplicate text after edits and mismatched positions/order after
  split/movement/exclusion. A later accepted geometry or appearance edit must
  invalidate/regenerate affected OCR while unchanged accepted images remain
  visually identical in the exported PDF. Any bounded dependency experiment is
  design evidence, not an implementation subtree or substitute product acceptance.
- Accept an ordinary unmarked already-assembled or prepared sole PDF, with
  optional advisory roles only, no mandatory sidecar and no discovery/reopening
  of source or cover folders through hints. Specify preservation of originals,
  safe destination/collision/failure/interruption behaviour and actionable
  unsupported outcomes. Require observed collection-isolated public acceptance
  from working preparation through final export; an unavailable COLLECTION
  string alone is not an access boundary.
- Define this intermediate increment's own public and visual acceptance:
  supported rotation improvement, unchanged/flagged unsupported cases, border/
  split fidelity, actual review edits including an unflagged page, post-split
  decisions and aligned English search/selection. Assess ALL fixed cases
  independently for this increment's actual claims: both Norwegian20 gutters;
  Garbage Collection30 indentation/glyphs/boxes/arrows; Counterpoint20 landscape/
  both columns; Fundamentals40 prose/faint/music; SchoenbergComposition cover1
  colour/sparse rules; Algorithm Design20 preservation. Preserve original
  music140's unsupported-layout diagnostic and music20's separate candidate.
  Require full-page/native detail, colour/faint/music fidelity and relevant
  fractional nonidentity sampling evidence; identity/copy proves no sampler
  fidelity. Separate human inspected-path/reply/defect records from numerical
  evidence, with missing approval retained honestly. Intermediate preservation
  or rotation acceptance does not accept a case's unresolved nonrigid geometry.
- Define the independent basis of each numerical rotation/preservation claim.
  Use known-by-construction rotation and sampling fixtures with an independent
  oracle, including upright/zero-angle, small-angle/noise and deliberately
  curved-line/local-angle-variation controls. The correcting estimator or its
  rerun cannot be its own ground truth. Verify controls reject deliberately
  wrong angle/image/region subjects before crediting their clean results.
  Check that estimator noise does not cause unsupported rotation/resampling of
  already-correct pages, and that a global angle's aggregate improvement cannot
  conceal a worsened region; state fallback/review and evidence limits. Retain
  full-page/native detail and nonidentity sampler checks. Real-page numerical
  improvement needs an independently validated instrument and justified limits;
  otherwise record numerical truth unavailable and obtain the separate visual
  judgment. k35's failed viewer neither calibrates angle nor rules out every
  independent instrument. This charter commissions no new real-page study.
- Define independent product dispositions for each stated claim/case: numerical
  acceptance passed/failed/unavailable and human visual accepted/pending/rejected,
  recording actual inspected views and verbatim scoped replies. Numerical success
  grants no visual acceptance. Require the later planner to state whether a
  working slice may retire at a technically complete but reaction-pending
  boundary, and, if allowed, precisely who owns missing acceptance before product
  consumers. A pending/rejected reaction never becomes accepted intermediate or
  full-default work by retirement, export or flagging. Retain the missing scope
  with k28 and successors before k22/k23; no identical response/planning loop.
- Preserve k31's complete conditional per-half unchanged/rigid/actual automatic
  vertical comparison, default validity/field/application/copy, independent
  source/output measurement beyond rigid with defensible positional/slope/
  curvature/systematic limits, native shape/detail/clipping, independently
  reverified Algorithm Design control and k4 fractional nonidentity RGB sampler,
  and separate left/right/control reactions. All remain unperformed. Commission
  no Norwegian study, same-grid retry or identical unavailable-response loop.
  A new study requires a separately justified explicit human choice of a genuinely
  changed selected-cell/readout observation, falsifier and exact-format blind
  controls for initial/repeat/verifier classes. All k40/k28 physical identities,
  frozen whole-line/region holdouts, unchanged masked-native gates/settings and
  shared real-baseline uncertainty still bind. No borrowed/forced model, holdout/
  gate/width/fixture rescue or plausible error bound is permitted. Alternative
  interpolation needs observed native damage; a two-axis hypothesis needs
  observed width/barline failure after a valid applied vertical result.
- Keep k27 then k28 live. Preserve music20 T/B/D/I fit and complete A/E/H
  whole-staff holdouts, automatic extraction-only diagnostics and genuine
  endpoints/native prerequisites before dense marks. Automatic physical
  prerequisite success stops the dense manual pass and changes k28's question
  without accepting a model. Fresh stripped contexts, blind whole-trace repeats,
  every eligible point's independent source verification, rise/curvature and
  repeatability/systematic limits and invalid-after-freeze stop still bind.
  Known-centre text controls do not calibrate real staff error. Roster changes
  need their own declared question; selection remains in the six-page pool
  20/40/60/100/180/220 unless the human chooses otherwise. First-pass child
  completion cannot classify overall acquisition or authorize correction.
- Carry historical geometry and preparation response completion separately with
  k27 then k28 at their exact existing k4/current-k19 views/questions. Both actual
  replies remain “Not inspected yet”; no defect or approval is inferred. Later
  rejection earns defect-specific repair/recomparison with a fresh planner.
  Exact missing views are reproduced only through verified recipes/manifests.
  A source, geometry or intermediate-product response does not accept preparation.
  A missing Norwegian source reply neither vetoes independently verified numerical
  evidence nor supplies permission for another study.
- Retain within-page correction, every fixed-case geometry/reaction and full
  default acceptance with k28 and actual justified successors BEFORE k22. The
  human must not have to infer that a completed intermediate design or export
  satisfies those criteria. Later correction extends/revises this coherent
  design with its own evidence/agreement before implementation. Optional
  whitening/noise preview/apply/revert follows accepted complete default export;
  k22 cuts its planning/working successors before k23. k23 stays live for the
  whole-root public integrated acceptance. Missing scope is inserted before
  those consumers, never closed by flags, a retired trial or policy permission.
- Reconcile shared Taskfile/setup and retained preparation/geometry recipes;
  any design evidence or later working slice verifies new/changed/affected
  recipes plus preparation/native checks. Finish edits before measurement,
  digest every read subject before/after with one writer, compare reruns item
  by item, keep originals read-only and artifacts outside the collection.
- Once a coherent design agreement exists, as the last work act insert its
  fresh implementation-planning consumer before k27, carrying the agreed spec,
  actual evidence/limitations, own intermediate acceptance and all unresolved
  k40/k28 obligations. No implementation leaves are cut by this design session.
  That planner decides only complete working slices and preserves k27 → k28
  before k22/k23. Assess an earned design review lazily before its planning
  consumer; actionable integration precedes that consumer. If a precisely
  different missing evidence question prevents agreement, externalise only that
  question with a fresh planner on EVERY outcome before product consumers.
  An unavailable/ambiguous signature alone leaves this design live for the human,
  with no new planner or repeated identical response question. Do not retire an
  unagreed design as an implementation-ready handoff. A changed evidence result
  returns to design agreement before implementation planning, never around it.

## Notes

This is a genuine new agreement point permitted by k39, not permission to build
a narrow deskew command that omits review, any-page adjustment, assembly or OCR.
The smallest useful product increment includes their complete path to export.
No node or future production/review chain is pre-grown. Evidence gathering must
serve this design's exact remaining uncertainty and fit one focused session;
tree-sized evidence is externalised rather than quietly becoming a new geometry
trial here. Product contracts state supported behaviour and limitations in the
project's language, without exposing implementation mechanics to the user.

## Decisions (running log)

Bootstrap adopted this mandated design leaf in the stated jj workspace, starting
with an empty change at parent `148e8678`. Loaded grove-design first, then its
shared spine, visual-discussion procedure and software-interface design guidance.
Read the glossary, root brief, preparation contract/acceptance/hints ADR and the
complete k40/k42/k43, k39/k38, k21/k27/k28, k25/k30, k31/k34/k37 and current
k22/k23 contracts. The Taskfile already owns reusable development work.

Carry the actual “yes” and “agreed” policy replies without re-asking them.
Neither signs this design. Separate every page's unverified within-page
geometry limitation from recorded triage triggers, and separate numerical
evidence from human visual disposition. Both Norwegian halves retain failed
fixed-grid addressing; real acquisition/masked gates/field/output remain
unperformed. Their source replies remain unavailable independently. Historical
geometry and preparation remain separately “Not inspected yet” with k27 then
k28. This design commissions no real-page measurement study or music protocol
change. k28 still owns within-page evidence/design/full-default acceptance
before k22/k23.

Local evidence confirms Tesseract 5.5.3 with English data, Leptonica 1.87.0,
Poppler and D2 0.9.0 are installed. The exact pikepdf 10.16.0 overlay source
was read; default placement uses TrimBox and may scale, so export must explicitly
match physical page dimensions and validate placement rather than trust defaults.
The selected bounded dependency question is whether text-only English OCR can
be merged into a fresh accepted-image PDF with unchanged visible RGB, actual
selection positions and no copied earlier text. This is design evidence only.
Leptonica's score ratio is not calibrated probability or nonrigidity evidence;
no automatic angle/confidence threshold is settled.

The one allowed in-session reviewer challenged the saved-state/OCR/export
contract in fresh context. Its two medium findings are valid/actionable: stale
OCR could either regenerate or refuse with no recovery command, and a new
no-text concern could be rediscovered endlessly without a durable disposition.
Re-read the exact clauses and fix them: export is the regeneration operation;
new OCR concerns stop publication, checkpoint result/reason under export's
ownership, unlock and return review-required. Acknowledgements are scoped to
the exact image/config/result, so unchanged acknowledged no-text does not loop.
These lifecycle changes warrant an earned external design review before the
implementation planner if the human agrees the design; spend no second
in-session reviewer and pre-grow no chain while the signature is pending.

Draft v1 proposes a shell-started local browser project, durable partial review,
any-page matched original/current controls, explicit acceptance of angle/split/
crop proposals, reversible post-split assembly and fresh image-preserving English
OCR/export. Unflagged means only no recorded trigger. No automatic nonzero
rotation threshold or nonrigid detector is selected. Acknowledged unresolved
pages remain usable; final export carries the universal limitation and readable
dispositions without inserting warning pages. These are proposals awaiting the
specific human signature, not settled product choices or representative acceptance.

The bounded English experiment passes two synthetic accepted images (original
and explicit crop), actual English extraction/ink-region selection overlap,
no earlier stale text, exact embedded RGB and exact matched renders. Canonical
and rerun agree item by item with all 181 read subjects unchanged in each run.
Wrong shifted selection subjects are rejected by the same oracle. This is no
real OCR, rotation/sampler, public/UI or visual acceptance. Rechecked the full
k35 control/key/canonical data: all nine misses, unique native minima and every
display cell centre hold; only current Taskfile differs from its historical
subject map, intentionally through added design recipes. No frozen record,
source observation, Norwegian study or music acquisition was changed.

Final verification: process:design-check, geometry:staff-check (four tests) and
prepare:check (231 tests, Ruff and strict pyright with zero errors) pass with
unchanged before/after subjects; current subjects still match those maps.
Design rendering/serving passed, and the actual Chrome page rendered all three
SVG views with the proposed/current-change markers. A fresh review deep link
reached its view; the corrected version view shows export freeze before OCR
and durable concern return. The generated full contract exposes the complete
public/visual seams. Pixel/native fixture checks and source code inspection
remain separate from that presentation check. Only this task and Taskfile
change among existing parent paths; root and all other task contracts remain
byte-identical. No implementation, dependency manifest or frozen evidence edit.

Tier 2 graph verification uses project
`Users-antony-Development-BookScanBuilder`, final coverage generation
`2026-10-12T00:24:18Z`. Relevant exact cli/publication searches, complete
both-direction one-hop traces and snippets support only their stated reuse
claims; the cli trace's unrelated inferred acceptance edges are not adopted.
Coverage checked every relied-on repository path. SVG/PNG exclusions and
untracked D2/PDF/gzip/lock metadata were handled by direct byte/source reads,
control raster verification, PDF image/text inspection and archive decompression.
The generated contract's reported partial range is line 1's HTML/style wrapper,
read directly and checked in the browser. Coverage is best-effort, not proof
of completeness.

Presented Draft v1's editable discussion at `http://127.0.0.1:8770/#discussion`
and full contract at `/contract.html`; the spec SHA-256 is
`56fc47681843b4bf43812de8f18a5d679eeab87535b9c558ea91033d37e4ff82`.
Asked: “Do you agree to Draft v1 at http://127.0.0.1:8770/contract.html:
shell-started local browser review with saved progress, explicitly accepted
geometry changes, post-split assembly, image-preserving English OCR/export,
and its public/full-page/native-detail test seams? Within-page correction and
full-default acceptance remain outstanding.” Suggested answers are agreement,
design changes, or later review with this design live. No actual reply has yet
arrived; the human signature remains pending. Do not infer it from preselection,
elapsed time, internal review or k39. Cut no planner/review tree and retire no
leaf while this is unsigned. The described jj change remains open for this
same design task; no sealing commit or exit signal is due at this boundary.

The human replied to Draft v1 with a scope correction, verbatim: “We don't need
to worry in this tool about re-ordering pages, because we can do that in a
separate third-party tool. We can also do the OCR entirely as a separate pass.
The difficult part that this tool needs to focus on is the geometry of each
page, and the geometry of the book i.e. page alignment matching, odd/even pages
etc.” This is not approval of Draft v1. Remove reordering/OCR from the current
tool contract and add book geometry, reconciling the root and live consumers.
Retain earlier decisions/evidence as history only; this explicit human instruction
governs conflicting old requirements. Preparation's already shipped features,
the nonrigid evidence obligations and the source-only music protocol are unchanged.
Asked the new alignment trade-off: match placement/mirrored margins while
preserving scale (recommended), or also support matching content scale.
Revise the visual document and spec together; no implementation planner or
retirement is authorised by the scope correction alone.

Draft v2 now describes page/book geometry, not the former searchable/assembly
product. Reconciled the root goal/Done when/increments/test seams and the current
live consumers with explicit latest-scope precedence over historical OCR/
reordering clauses. Added side/group/parity-break, reference-anchor/common-canvas/
mirrored-margin and alignment-invalidation requirements. The root's within-page
criterion, all fixed cases and independent numerical/visual dispositions remain.
All other existing parent files, including shipped preparation, product/tests/
dependencies and frozen experiments, are byte-identical. Removed only this
unsealed draft's newly created OCR experiment/reports/fixtures/recipes; they no
longer earn current artifacts. Their earlier bounded result remains history in
this log and the external run directories, not a geometry acceptance claim.

Proposed alignment preserves native page scale and uses reviewed translation/
padding against declared top/inner anchors and left/right group targets. Printed
numbering and PDF ordinal are distinct; covers/front matter/physical blanks and
parity breaks are explicit, with every source occurrence/order retained. Source
frames are registration aids, not crop permissions. Local/reference/side/topology
changes invalidate dependent placement, while unrelated accepted pages remain.
The scale-matching clarification has no actual reply yet, so preservation remains
a stated proposal, not an inferred human choice. Draft v2's spec SHA-256 is
`b6c8458e0c42cfc2d1431ed49e1613b02c6e2b31ac5176a958ab47869e563caf`.

Read installed Pillow 11.3.0's exact paste semantics for integer, same-mode,
unmasked placement; modes/masks can convert/blend and must not silently enter
that contract. This is API evidence, not observed real-page alignment fidelity.
No new source study, detector calibration or correction output was generated.
The bounded in-session reviewer allowance was already spent on Draft v1;
material revised geometry/alignment state needs its earned external design review
before a planner once an actual revised agreement exists. No second reviewer or
unsigned review/planning tree is created.

Verified the four revised geometry views through the reusable render recipe.
The new view initially failed because `left`/`right` are reserved D2 edge keys;
reproduced the exact failure, changed only those node identifiers and confirmed
the complete build passes. Reloaded the actual Chrome document (its earlier
in-memory manifest still displayed v1 until reload); Draft v2's book alignment
view renders and its outline/changed links match the current sources. HTML's
partial first-line wrapper was read directly; untracked D2/SVG and uv.lock paths
use direct source/byte/render verification. Coverage remains best-effort at
reported generation `2026-10-12T00:24:18Z`, not completeness evidence.
Fresh geometry:staff-check (four tests) and prepare:check (231 tests, Ruff,
strict pyright zero errors) pass with frozen stable read-subject maps at
`/private/tmp/bookscan-k41-v2-checks.json`. No product code was changed.

The human's scope correction is recorded and implemented in the design/contracts;
it is neither the pending scale choice nor a signature for Draft v2. Leave this
design live for that discussion, with no planner, retirement, sealing commit
or exit signal. k27 then k28 and the remaining geometry/appearance/root acceptance
ownership stay live in the current tree.

The human replied verbatim **“agreed”** to the presented Draft v2 at
`http://127.0.0.1:8770/contract.html#book-geometry`, after its geometry-only
scope and preserved-scale matching were stated. Record this against the complete
published v2 contract (pre-signature SHA-256
`b6c8458e0c42cfc2d1431ed49e1613b02c6e2b31ac5176a958ab47869e563caf`):
sole-PDF shell/local-browser page and book geometry, explicit side/group/parity
and top/inner alignment at preserved scale, saved any-page/group review and
image-only export, with the documented public/full/native/pair/group test seams.
Reordering/removal and OCR remain external; automatic scale normalization is
not commissioned. No inspected-output path or actual geometry acceptance is
attributed to this reply. It signs the design, not a nonexistent working product,
nonrigid result or historical preparation/geometry comparison.

Settle scale preservation in the current spec and visual document, remove their
pending-signature language and retain the actual reply/scope. The exported
geometry report/project boundary earns one ADR because its persisted meaning
binds later readers and must survive metadata loss/external reordering honestly.
Technology choices and default alignment operations are local/reversible and
earn no additional ADR. Finish the coherent artifacts before cutting the earned
design review and implementation-planning consumer as the final work act.

Design v2 and its one earned persisted-handoff ADR are coherent and complete for
this design leaf. The canonical agreed spec SHA-256 is
`54c226c15e1a1c127bc372eab3efb59c3dcdb02a5555f2b67dcc5604dda44028`;
the pre-signature hash above identifies what the human saw. The agreement/status,
scale-preservation settlement and ADR pointer do not attribute new product/output
acceptance. Canonical local links exist, all served reference copies match their
canonical sources, SVGs parse and the reusable render replay is byte-stable.
Reloaded the actual browser: agreed Design v2, all four SVG images loaded, and
the updated book-alignment diagram visibly states preserved scale. The design
document remains open; it is documentation, not a working processor.

Final `process:design-render`, `geometry:staff-check` (four tests) and
`prepare:check` (231 tests, Ruff and strict pyright zero errors) all pass.
Every one of 139 frozen read subjects is byte-identical before/after those checks;
the full maps/results are `/private/tmp/bookscan-k41-agreed-checks.json` and
artifact/link checks are `/private/tmp/bookscan-k41-agreed-artifacts.json`.
Compared every one of the parent's 121 tracked files directly: only this leaf,
the root/four live consumers and Taskfile changed. Product source/tests/locked
dependencies, shipped preparation and frozen evidence are byte-identical.
Coverage was checked for all 138 repository paths at best-effort generation
`2026-10-12T05:34:52Z` (the API's 128-path cap required two batches).
`/private/tmp/bookscan-k41-agreed-coverage.json` retains the reports. HTML's
partial first-line wrapper and metadata-changed served copies were read/checked
directly; D2/SVG/PNG/archive/uv.lock untracked/excluded graph paths use direct
source/byte/render/native/archive fallback already performed. No completeness
or real geometry acceptance is inferred from clean coverage.

The remaining work is precise and earns two final cuts: an external design
review of revised page/book alignment and saved project/export semantics, then
a fresh implementation planner before k27. Their prepared charters preserve
scale, all independent fixed-case/public/visual seams, conditional Norwegian
evidence and source/reaction ownership, unchanged music acquisition and the
full-default boundary before appearance/root acceptance. No implementation
subtree or integration is pre-created; the review alone earns an integration
immediately before the planner if actual actionable findings warrant it.
All applicable design completion criteria are met under the human's corrected
scope. OCR/reordering clauses superseded above are not missing design work.
No ancestor closes: these successors and k27/k28/k22/k23 remain live at the root.
Cut the two handoffs now as the last work act, then retire, name the finishing
run on the review and seal this focused jj change before signalling exit.

As the final work act, inserted rotation-processor-k44 immediately before k27,
then rotation-processor-k45 immediately before that planner. Wrote their complete
charters from the finished design; the review names rotation-processor-k41 and
the finishing run from this session’s own environment. The order is k41 →
rotation-processor-k45 → any earned integration → rotation-processor-k44 → k27 → k28 →
complete-default successors → k22 → k23. Both renumbers preserve each shifted
consumer body byte-for-byte. Root ownership now names the actual stable handles.
