# rotation-processor-k41

## Goal

Establish the design agreement for one useful sole-PDF processor that corrects
rigid rotation where supported, preserves and flags unresolved within-page
distortion, supports review/adjustment and post-split assembly, and exports
accepted visible images with aligned English OCR. Deliver a spec and only
earned ADRs, before implementation planning. This intermediate working increment
does not satisfy the root's within-page correction criterion.

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
- Design flagged-page review and adjustment of ANY page, including one that was
  not flagged, with matched original/current full-page and native-detail views,
  explicit acceptance/reversion and final export reflecting accepted edits.
  State the actual supported adjustment operations and their limitations rather
  than implying unproved automatic nonrigid correction. Define accepted-image
  identity/versioning and invalidation at the behaviour level. Its representation,
  working reader, review controls and export belong to the same useful handoff;
  no schema-only, OCR-engine-only, display-adapter-only or test-only stage.
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
  missing evidence/response question prevents agreement, externalise only that
  question with a fresh planner on EVERY outcome before product consumers;
  do not retire an unagreed design as an implementation-ready handoff or repeat
  identical unanswered questions on an automatic response/planning loop.

## Notes

This is a genuine new agreement point permitted by k39, not permission to build
a narrow deskew command that omits review, any-page adjustment, assembly or OCR.
The smallest useful product increment includes their complete path to export.
No node or future production/review chain is pre-grown. Evidence gathering must
serve this design's exact remaining uncertainty and fit one focused session;
tree-sized evidence is externalised rather than quietly becoming a new geometry
trial here. Product contracts state supported behaviour and limitations in the
project's language, without exposing implementation mechanics to the user.
