# rotation-processor-k45

**Reviews:** rotation-processor-k41
**Creator:** run 661178c5-b32a-4682-94ae-e6432d482853

## Goal

Give the committed page/book geometry Design v2 an independent adversarial read
before its implementation planner. Deliver findings only: determine whether
the signed geometry-only contract is coherent, preserves every source occurrence
and retained image, states honest evidence limits and supplies independent public
and visual tests for its load-bearing lifecycle and book matching decisions.

## Context

- Read rotation-processor-k41's committed diff, actual reply/agreement record,
  `docs/specs/rotation-processor.md`, all editable/generated views under
  `docs/design/rotation-processor/` and `docs/adr/geometry-review-handoff.md`.
  Its immediately following planning consumer is rotation-processor-k44. Reconcile the actual
  current tree if the artifact moved. The review is inspection-only; fix nothing.
- Read the current root/live-consumer scope notes and complete k40/k42/k43,
  corrected-book-k21, staff-acquisition-k27 and corrected-book-k28 handoff.
  Latest human scope removes processor OCR/reordering and adds book geometry;
  the actual **“agreed”** signs v2 with scale preservation, not real outputs or
  within-page correction. Older inherited OCR/assembly clauses do not restore
  removed features. Preparation's shipped explicit assembly remains available.
- Read preparation spec/acceptance/hints, page-geometry/staff evidence, k31's
  whole Norwegian brief/results, k34/k37 repairs and k38/k39 responses wherever
  material to a claimed property. Failed addressing is no field/output or family
  rejection; source/output reactions and historical **“Not inspected yet”**
  remain separately owned. No new source study is commissioned by this review.

## Done when

- Re-derive requirements and challenge the actual artifact, rather than approve
  its wording or repeat the producer's bounded v1 reviewer. Scope findings to
  concrete severity, evidence/location, consequence and a checkable remedy;
  separate unsupported claims from optional improvements. Verify source/API
  claims against primary/exact installed evidence with graph coverage fallback.
- Challenge full-page rendering and unchanged RGB/physical-scale fidelity;
  estimator sign/evidence limitations and mandatory nonzero acceptance;
  expanded rotation, safe crop/border/split/provenance and blank/duplicate
  retention. Norwegian20 is a spread; Counterpoint20 is a single landscape page.
  Check old text omission and exact accepted-image/count/order export, all fixed
  cases/native-detail and meaningful fractional nonidentity/wrong-subject tests.
- Challenge side/group/logical-anchor rules with covers/front matter/blanks,
  missing pages, spread halves and parity breaks. Matching must preserve scale,
  source content and output order; guide mirroring never mirrors image pixels.
  Frames/anchors do not authorize cropping. Targets, integer translation/padding,
  no-clipping behavior, manual fallback and full/native/pair/group review must
  be independently testable, including wrong side/anchor/offset/canvas controls.
- Challenge immutable revision/asset checkpoints, single-writer and stale-action
  handling, split replacement and local/shared reference/target invalidation.
  Trace interruption/resume/export snapshot consistency, alias/no-clobber paths
  and pre/post publication signals. Processor project versus export report and
  optional hints must remain coherent under fresh import, metadata loss and
  external reordering; report data is no resume database or certificate.
- Check universal unverified within-page limitation versus recorded per-page
  triage/unflagged meaning. Synthetic independent truth, real numerical
  unavailable outcomes and actual human acceptance must remain distinct. No
  retired slice/export/score/design signature supplies missing representative,
  nonrigid or full-root acceptance. Preserve every k27/k28 evidence/response/
  completion obligation before k22/k23, source-only music protocol unchanged.
- Inspect the spec/ADR set as a minimum coherent current-state set and compare
  visual diagrams/manifest/served contract with canonical decisions. Detect
  lost public behavior/test seams or accidental planning/implementation drift.
- If actionable findings earn integration, cut `integrate-review-design` with
  bare slug `rotation-processor` immediately before rotation-processor-k44, as the final work
  act. Its body names this review's handle, not a copied findings checklist.
  If there are no actionable findings, cut nothing. Retire/commit normally;
  launch no driver and do not reopen the agreed design through an identical
  human-response loop.

## Notes

This external review is earned by revised page/book alignment and persisted
review/export semantics. The producer already spent its bounded in-session
reviewer on v1 and does not request another in-session reviewer. Findings belong
in this review artifact; actual integration decides which stand before planning.

## Findings

Reviewed artifact: commit `31b18570` (rotation-processor-k41). The canonical
`docs/specs/rotation-processor.md` is unchanged since then; `spec:N` below means
its line N there. Findings are stated as defects for triage, not as fixes.
Severity: **High** blocks a correct plan or makes an agreed claim false;
**Medium** leaves a load-bearing contract ambiguous enough that the planner
would have to invent it; **Low** is current-state hygiene or a cheap hardening.

### F1 — High: the baseline re-rasterises every page at 300 dpi, contradicting the no-resampling/no-substitution claims; downsampling and cost are unstated

- **Where:** spec:54–60 (complete MediaBox render “at the existing 300-dpi
  comparison policy”), spec:74–78, spec:92 (“Exactly zero retains pixels without
  resampling”), spec:266–278 (“Geometry export does not silently recolour,
  resample or substitute unedited images”).
- **Evidence:** `docs/research/scan-geometry-a.md:33–35` records the fixed cases'
  actual objects: Fundamentals music page has a 150-ppi RGB JPEG plus a 300-ppi
  stencil, Norwegian20 a 2633×1976 220-ppi grayscale JPEG, Algorithm Design20 a
  2159×2448 one-bit JBIG2 inside a 2350×2721 render. Every one becomes a 300-dpi
  lossless RGB raster that the export embeds instead of the source image object.
- **Consequence:** the no-resampling and no-substitution statements are true only
  relative to the rendered baseline. Relative to the input they are false for
  every page, edited or not. That bears on the root's “already-correct pages are
  not degraded” and “preserve the corrected page images”. Pages above 300 ppi
  would be downsampled at import, permanently losing detail. No fixed case
  exceeds 300 ppi, so the agreed seams cannot detect that loss. Storage cost is
  unstated: one Norwegian spread render is 3591×2695×3 ≈ 29 MB decoded,
  replacing a grayscale JPEG, and the project keeps baselines plus revisions.
  The preparation spec stated its measured memory/size costs; this spec states
  none.
- **Remedy (checkable):** state the import resolution policy relative to each
  page's native image resolution: for example, the maximum effective image ppi
  up to a stated ceiling, or fixed 300 dpi with a recorded downsampling triage
  reason. Say explicitly that the baseline is a re-rasterisation and what
  “unchanged” and “native” mean against it. Record the chosen representation and
  its rejected alternative. Add a >300-ppi source fixture, and a one-bit and a
  grayscale source fixture, with input-relative full-page/native comparisons.
  State measured, or explicitly unmeasured, project/export size and memory per
  page.

### F2 — High: “unavailable” is undefined against Leptonica's real failure signal, so an exactly-zero failure becomes an unflagged page

- **Where:** spec:84–95 and the triage list at spec:222–228.
- **Evidence:** Leptonica 1.87.0 `src/skew.c` (the installed version; primary
  source at the 1.87.0 tag). `pixFindSkewSweepAndSearchScorePivot` initialises
  angle and confidence to 0.0. When the maximum falls at the sweep edge it warns
  and returns 0 (success) with both outputs still 0.0. When the max score is
  below `MinValidMaxscore`, or the min score is below threshold, it zeroes the
  confidence, keeps the angle and still returns 0. An empty image returns 1. The
  default sweep range is ±7°.
- **Consequence:** two kinds of page can come back with status 0 and an angle
  of exactly 0.0: one tilted beyond the sweep, and one with no horizontal line
  structure (sideways or 90°). The spec's “exactly zero retains pixels” rule then
  leaves both unflagged, so the worst-rotated pages are the ones that pass
  silently. No triage reason covers orientation at all, whether 90° or 180°.
- **Remedy:** define “unavailable” as non-zero status *or* confidence = 0.
  That is the library's explicit invalid sentinel, not a tuned threshold. Let
  “exactly zero” mean only a valid zero estimate. State the ±7° range and
  orientation-blindness as limits. Add beyond-range, sideways/upside-down and
  blank fixtures to the spec:335 row, each with a wrong-subject control.

### F3 — High: what blocks export, and how a book-sized review is disposed of, is undefined, and the estimator evidence makes it the common case

- **Where:** spec:90–95, spec:230–235 (“Resolve flags by
  accept/reject/retain-unresolved…”), spec:301–306 (exit 6 for “pending
  undisposed changes … or missing current export acknowledgement”).
- **Evidence:** `docs/experiments/page-geometry-report.json` records −0.015625°
  (−1/64°) for the already-correct Algorithm Design control and 0.84375° for the
  music page. Real text pages will essentially always return a nonzero estimate,
  so essentially every page carries a review reason.
- **Consequence:** the spec doesn't say whether an undisposed nonzero-angle
  reason counts as a “pending undisposed change”, which blocks export with exit
  6, or is covered by the export acknowledgement as retained unresolved. Group
  operations exist only for placement; no scoped multi-page disposition of
  rotation proposals is defined. The planner must therefore choose between two
  outcomes. One is a per-page explicit decision on every page of a 300-page book
  before export, which turns the root's “review of flagged pages” into whole-book
  review. The other is an invented bulk acknowledgement that could rubber-stamp.
  Combined with F2, the few unflagged pages are disproportionately estimator
  failures.
- **Remedy:** define the per-page dispositions and exactly which block export.
  State whether “retain baseline” is the default disposition covered by the
  acknowledgement. Define any scoped bulk disposition (per group or selection)
  and the reason it records. State honestly that the nonzero trigger flags
  nearly every page. Add a public test: a multi-page fixture whose pages all
  carry nonzero estimates, checking that export is blocked or allowed exactly
  per the rule, with the recorded dispositions in the report.

### F4 — Medium: split, crop and rotation have no defined composition order or coordinate frame, and a full-height vertical split cannot separate a tilted gutter

- **Where:** spec:97–103 (“Compose crop/rotation from the immutable baseline”),
  spec:121–125 (“complete full-height source regions … deliberate gutter
  overlap”), spec:134–137.
- **Evidence:** the Norwegian trial used a vertical full-height partition at
  x=1785 of the unrotated render (`docs/experiments/norwegian-gutter.md:43–50`).
- **Consequence:** if a whole spread was fed skewed, its gutter is tilted in
  baseline coordinates. A vertical full-height partition then either cuts
  printed content into the other half, or, with overlap, leaves the facing
  page's material inside each half. Scanner borders are scanner-aligned while
  printed content is page-aligned, so whether a crop rectangle lives in the
  baseline frame or the rotated frame decides what it can remove. The spec says
  neither. The expanded white rotation corners interact with that same crop.
- **Remedy:** specify the transform pipeline, for example split region, then
  per-half rotation, then crop, and the frame each parameter lives in. Either
  allow a non-vertical split line, or name overlap plus a rotated-frame inner
  crop as the supported path. Add a synthetic skewed-spread fixture with a known
  gutter angle. It must show that no printed content is lost and that foreign
  gutter material is handled explicitly.

### F5 — Medium: the common-canvas contract is incomplete (padding appearance, canvas growth, unanchored members)

- **Where:** spec:182–196.
- **Consequence:** the fill for alignment padding is unspecified (rotation fill
  is white). On toned-paper scans, padding adds visible edge bands, a new
  visible region that sits beside the “no image banners” promise. Retained
  content includes rotation fill and any uncropped borders, and a clipping
  target must be enlarged. Group canvases therefore exceed the original paper
  size, and that growth is unstated. “Blank/sparse/unanchorable pages keep their
  current geometry” leaves open whether such a group member sits on the common
  canvas, and at what offset, or keeps its own canvas. Keeping its own canvas
  makes page sizes jump inside a matched group.
- **Remedy:** specify the padding fill policy, and require full and pair views
  to show padded regions. State the expected canvas growth. Define where
  unanchored members are placed, and add a test for it.

### F6 — Medium: the run/group/side model is implicit, and a duplicate occurrence inside a body run is uncovered

- **Where:** spec:143–164; test rows spec:339–340.
- **Consequence:** side alternation lives in a “declared consecutive body run”
  and layout in a “geometry group”, yet their relationship is not stated: can a
  group span runs? Does a chapter opener in its own group keep its run side for
  mirrored margins? Does a page outside every run have a side? Synonyms drift
  already (“geometry group”, “matching group” at spec:153 and in
  `book-alignment.d2`, “layout groups” in `diagrams.json`). The root requires
  duplicates to be retained. A duplicate inside a run shifts parity the opposite
  way from a missing page, and the alternating proposal gives it the wrong side,
  so its mirrored placement is wrong. Only missing pages and conflicting anchors
  are named as parity-break cases.
- **Remedy:** define the entities and their cardinality. One possible model: an
  occurrence or half has at most one run position, which supplies its side, and
  belongs to at most one group, which supplies canvas and reference; side does
  not depend on group. Pick one canonical group term. State how a duplicate is
  sided, for example a repeat of occurrence X takes X's side and does not
  advance parity. Add a duplicate-in-run fixture with a wrong-parity control,
  and a chapter-opener-in-separate-group-within-a-run case.

### F7 — Medium: the invalidation rule for local edits understates its dependents

- **Where:** lifecycle row spec:252 (“invalidate that page's dependent
  alignment”), spec:198–203.
- **Consequence:** a local edit on a group's *reference* page replaces the
  pixels its anchors were marked on, so every member placed against it is
  stale. The row names only “that page's” alignment. A local edit that enlarges
  a member, such as an expanded rotation canvas, can exceed the accepted group
  canvas, which must reopen the target rather than clip. What happens to an
  anchor after a new revision is unspecified: re-marked, or carried through the
  known rigid mapping. The failure test (spec:344) covers only shared-target
  invalidation.
- **Remedy:** make the row explicit for reference-page edits and canvas
  overflow, and state the anchor carry-over rule. Add two tests. A re-edited
  reference must invalidate all dependents while unrelated groups stay
  byte-identical. A member enlarged beyond the canvas must require target review,
  with no clipping.

### F8 — Medium: the persisted export convention is under-specified, though the ADR calls it hard to reverse

- **Where:** spec:280–289; `docs/adr/geometry-review-handoff.md`.
- **Consequence:** the container, key name, encoding, schema-version field and
  unknown-version reader behaviour of the “embedded readable review report” are
  unspecified (attachment, private dictionary or XMP?). “Preserve
  preparation-hint compatibility” doesn't say whether exported pages carry v1
  `/BookScanBuilder` page hints. If copied unchanged, `/SourceSHA256` and
  `/SourcePage` stop identifying the immediate source. `docs/specs/prepared-pdf.md`
  defines them as immediate-source provenance of “this assembly”. Two split
  halves would also share a `SourcePage` with no rule. The planner would end up
  inventing a user-PDF convention that the ADR itself justifies as persistent.
  Compare the preparation spec's exact field schema.
- **Remedy:** specify the report container, key, encoding and version, and that
  import ignores it. Decide the output page hints: omit them, or rewrite them
  with immediate-source values plus a split-half rule. Test re-import of an
  export, and of a metadata-stripped export: each must give fresh state, the
  universal limitation and no restored acceptance or sides.

### F9 — Medium: the server commands' lifecycle and exit contract are missing for shell iteration, and the writer lock's fate after a hard kill is unstated

- **Where:** spec:32–43, spec:237–244, spec:291–306.
- **Consequence:** `process` and `review` block on a foreground server. Neither
  the normal stop path (a UI “done”, or Ctrl-C) nor its exit status is defined.
  The cited convention maps a caught SIGINT to 130 (the shipped handler is at
  `src/bookscan/cli.py:153`), so an ordinary Ctrl-C stop would read as failure
  inside the user's shell loop. Nothing allows import and assessment to run
  unattended without serving. Whether writer exclusion survives a hard kill
  (lock file) or is released by the kernel is unspecified. A stale lock combined
  with “no unexposed recovery command” would block resume. The exit code for a
  lock conflict, which the spec:344 row exercises, is unmapped, as is `bookscan
  export` while a review server holds the project. So is whether export's freeze
  persists after a hard kill. “Outside the collection” (spec:291) cannot be
  checked by a processor that has no collection input.
- **Remedy:** define server termination and its exit statuses, kept distinct
  from export success. Make the lock released on process death, or name an
  explicit recovery path. Map lock-conflict and frozen-export cases to codes.
  Restate the collection clause as an aliasing check plus an acceptance
  obligation. Add tests: kill −9 the server, then resume; Ctrl-C stop status;
  export against a running review.

### F10 — Medium: the MediaBox baseline changes the visible extent of inputs cropped by CropBox, and input-geometry fixtures are missing

- **Where:** spec:54–60, spec:74–75.
- **Consequence:** viewers display the CropBox (ISO 32000-1 page boundaries).
  For an input whose CropBox is smaller than its MediaBox, as left by an earlier
  tool's crop, the “default retained” export reveals previously hidden material
  and changes an unedited page's size. That contradicts “already-correct pages
  are not degraded”. Preparation acceptance compares CropBox renders and adds
  MediaBox renders only where they differ (`docs/acceptance/prepared-pdf.md:81–82`).
  The spec claims to honour `/Rotate`, UserUnit and the original boxes, but no
  test seam carries a rotated, UserUnit≠1 or CropBox≠MediaBox input.
- **Remedy:** choose the default accepted extent explicitly: a CropBox
  baseline with the MediaBox remainder restorable, or MediaBox with a triage
  reason. Add synthetic box, rotation and UserUnit fixtures; preparation already
  owns a distinct-box synthetic.

### F11 — Medium: the current-state spec set and glossary contradict the agreed scope

- **Where:** `docs/specs/prepared-pdf.md:326` (“Post-split book-page order and
  exclusions remain the processor's responsibility”) and `:566` (OCR listed as
  later work here). Root `_BRIEF.md:395` (“The processor owns equivalent controls
  for halves created by spread splitting”). `CONTEXT.md:14` (“ready for geometry
  correction and OCR”) and `:47` (the developer adds the OCR text layer).
- **Consequence:** specs are a current-state set; a reader of the preparation
  spec gets the removed processor responsibility. The book-geometry vocabulary
  the spec relies on is absent from `CONTEXT.md`, with synonyms already drifting
  (see F6): occurrence, half, group, body run, side, anchor, reference frame,
  target canvas, parity break, baseline, accepted revision, triage reason,
  universal limitation, disposition, export acknowledgement and project.
- **Remedy:** edit those sentences in place, leaving the preparation behaviour
  unchanged. Fix the root line. Update the glossary entries and the dialogue,
  adding the core terms with the aliases to avoid.

### F12 — Low: the spec carries tree work-orders and history that will rot

- **Where:** spec:3–8 (narrates the scope change), spec:356–369 (“No new
  Norwegian study … commissioned here”, “A planner may allow …”, the
  Taskfile/digest procedure).
- **Consequence:** under the membership and behavioural rules, these belong in
  the briefs, which already carry them; in a current-state spec they outlive
  `.grove/` as stale instructions.
- **Remedy:** keep the behavioural seams and dispositions, and drop
  planning/process obligations from the spec.

### F13 — Low: the loopback review server has no request authentication

- **Where:** spec:38 and spec:36 (export “also available from review”).
- **Consequence:** state-changing actions over loopback HTTP can be reached by
  other local processes, and by web pages through cross-site requests or DNS
  rebinding. Export from the browser writes a new file, and how its destination
  is chosen is unspecified. Revision tokens prevent stale actions, not forged
  ones.
- **Remedy:** use an unguessable per-session token in the served URL and in
  every action, validate Host and Origin, and define how the export destination
  is chosen. Test that a tokenless or foreign-Origin request is rejected.

### F14 — Low: runtime tool dependencies and evidence versions are unstated

- **Where:** spec:318–322.
- **Consequence:** Poppler and Leptonica become runtime dependencies of the
  installed command; `pyproject.toml` declares only pikepdf. The spec doesn't
  say how the Python package reaches Leptonica (the experiment compiled C
  against Homebrew 1.87.0), how a missing or incompatible tool is reported, or
  that tool versions are recorded for the “Renderer/settings change” row. k41's
  Pillow paste evidence is from 11.3.0, the experiments' inline pin, but the
  product lock resolves Pillow 12.3.0 transitively (`uv.lock:120–121`).
- **Remedy:** at behaviour level, add a tool preflight with a named error and
  remedy, and record tool versions in the project. Require a direct Pillow pin,
  and re-verify the API against the locked version.

### Optional improvements (not defects)

- State the iteration path: fixing geometry after external reordering/OCR
  means re-editing the original project, re-exporting, then redoing the
  external passes, because a re-import is a fresh project.
- The `rotation-processor` slug no longer names the area (title: “Page and
  book geometry”). Rename only with full citation reconciliation (ADR link,
  render recipe, root pointers, design README).

### Checked and sound

- The served `contract.html` matches the canonical spec word for word.
- All four SVGs carry every label of their D2 sources.
- The three served reference copies are byte-identical to their canonical
  sources.
- The signed pre-signature spec (`b6c8…`, jj snapshot `ade6cde6`) differs from
  the canonical one only in status wording, the settled scale-policy sentence and
  the ADR pointer. No unsigned substantive change entered after “agreed”.
- `geometry-review-handoff` passes the ADR AND-test. The agreement record scopes
  the reply honestly. Numerical and visual dispositions stay separate.
- The spec keeps scale preserved, guide-only mirroring and frames that are not
  crop permissions consistently.
- The spec preserves every occurrence and its order with external
  removal/reordering, and keeps k27 → k28 → k22 → k23 ownership.

## Decisions (running log)

Bootstrap: loaded grove-review-design, the grove spine and `references/review.md`.
Resolved `rotation-processor-k45`, read the root brief (sole chain entry), glossary,
both ADRs, the k41 task/log/commit, the spec, all design views, the
preparation spec/acceptance, the k44 charter and the consumers' scope notes.
Spending no in-session reviewer: a review session is itself the adversarial read.

Evidence was taken from primary or recorded sources only. Leptonica behaviour comes
from 1.87.0 `src/skew.c` at its release tag, the installed version. Source
resolutions come from `docs/research/scan-geometry-a.md`. Estimator outputs come
from `docs/experiments/page-geometry-report.json`. Lock and dependency versions
come from `pyproject.toml` and `uv.lock`. The signed snapshot comes from the jj
evolog. No test, build, lint or render command was run. Graph coverage
(generation `2026-10-12T05:45:02Z`, best-effort) showed no recorded gap for the
relied-on tracked paths. `contract.html`'s partial line 1 and the untracked
D2/`uv.lock` paths were read directly.

The findings include actionable High items, so integration is earned.
Cut `integrate-review-design` with slug `rotation-processor` immediately before
rotation-processor-k44, as the final work act; its body names this handle only.
