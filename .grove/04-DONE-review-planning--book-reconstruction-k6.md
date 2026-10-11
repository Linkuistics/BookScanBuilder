# book-reconstruction-k6

**Reviews:** book-reconstruction-k3

## Goal

Adversarially inspect the working-increment plan and both task trees before
downstream sessions consume them. Report material findings without fixes.

## Context

Read the producer commit named `book-reconstruction-k3`, the confirmed
requirements in `plan-k1`, and `docs/research/scan-geometry-a.md`. This producer
also created a separate preparation workspace at
`/Users/antony/Development/BookScanBuilder.prepare-pdf`; inspect its scoped root
brief and the preparation-side commit with the same producer handle. Each
workspace has its own tree/key namespace: `prepared-pdf-k4` there is distinct
from `page-geometry-k4` here. The shared terminal bootstrap leaves came from the
same parent, rather than separate requirements interviews.

## Done when

- Check that preparation is independently usable, its command preserves full
  PDF content and explicit cover roles, and the proposed processor still
  requires only one prepared PDF without collection-folder discovery.
- Check the trial's diagnostic model-failure handling, held-out geometry,
  sampler/control tests and required human reaction against the actual research.
  A copied output, successful return or improved fitted staff is not acceptance.
- Check that unsuccessful/inconclusive trials and the expanded fixture sequence
  lead to precise fresh-context work; that a premature producer closure cannot
  strand the root's correction, spread, review/OCR and optional-cleanup scope;
  and that no production algorithm or interface was chosen without evidence.
- Check the separate-grove dependency and product-integration handoff, including
  how Taskfile changes and durable docs are combined while task trees stay local.
  Flag any unsafe or ambiguous assumption in the two-workspace plan.
- Record each real finding with its contract, location and consequence. If
  findings warrant integration, cut it where it will run before
  `page-geometry-k4`; its body names this review's handle rather than repeating
  the findings as obligations. If there are no actionable findings, retire
  without an integration leaf.

## Notes

Review the artifact and its contracts, not the producer's preference for its
chosen decomposition. Do not run the visual experiment or implement preparation.

## Findings

Read-only inspection of the producer commits for `book-reconstruction-k3`: `c9959370a702`
(this workspace) and `1ada47bd20fe` (`/Users/antony/Development/BookScanBuilder.prepare-pdf`),
the confirmed requirements in `plan-k1`, and `docs/research/scan-geometry-a.md`. Nothing was
run, built or edited outside this file. "Main" below is this workspace's tree, "prep" the
preparation workspace's tree. Findings are ranked most severe first; **Where** names the
workspace the contract lives in, because that decides who can change it.

### 1. The landing of preparation into the processor line has no mechanism and no owner

**Contract.** Main `_BRIEF.md` ("Product groves are sequential at integration…", line 72) and
prep `_BRIEF.md` (last *Done when* bullet, line 30; prep `prepared-pdf-k5` line 32) promise that
product artifacts and durable docs integrate "via jj" while each `.grove/` stays local.

**Location.** Main `_BRIEF.md` lines 72–78; prep `_BRIEF.md` lines 30–32; prep
`05-planning--prepared-pdf-k5.md` line 32; `corrected-book-k5` lines 13–16.

**Consequence.** As written this is not executable, for two reasons the plan does not mention.
(a) Grove's one-focused-commit-per-task rule puts every `.grove/` rename and edit in the same
commit as the product artifact, so no prep task commit can be rebased, cherry-picked or merged
without dragging its `.grove/` changes. (b) The two lines already collide: both fork from
`850069574aea`, both rewrite `.grove/_BRIEF.md` (main +33 lines, prep a full scoped rewrite),
both carry identical `03-DONE-…k3`, and they hold different leaves at positions 04/05 with
overlapping keys `-k4`/`-k5`. A commit-level integration therefore yields a conflicted root
brief and a tree Grove's verbs refuse as malformed, or, if resolved carelessly, replaces the
end-to-end charter with the preparation-scoped one. A rewrite of one workspace's ancestors from
the other also leaves that workspace's working copy stale. Nothing states the allowed
operation (a path-scoped restore of an allowlist of product paths, excluding `.grove/`), which
revision is recorded as landed, or which session performs and verifies it. No leaf in either
tree is chartered to perform the landing; the prep grove can finish and tear down, and main's
`corrected-book-k5` can run, with the handoff owned by nobody. The processor workspace's base
revision is likewise unspecified, so its first prepared-PDF test has nothing defined to run
against. The two groves' ordering is by operator discretion only; `pick` cannot sequence across
trees.

**Where.** Both workspaces.

### 2. Two groves each author the root `Taskfile.yml` with no combination rule

**Contract.** `page-geometry-k4` (line 51) adds root Taskfile tasks; prep brief (line 27) and
`prepared-pdf-k5` (line 21) have the preparation implementation add "a root Taskfile".

**Consequence.** Both workspaces start from a tree with no Taskfile, so the second to land
meets an add/add conflict on the same path, plus likely name clashes on the obvious recipe
names (setup, fixtures, check) and a shared setup dependency set. Each file is verified only in
isolation; the combined file is never verified, which the Taskfile discipline says must precede
reliance. The prototype is also a throwaway kind, yet its Taskfile tasks outlive it
(`corrected-book-k5` line 49 preserves them) while the disposition of the wrapper source those
tasks call is not stated. `task` itself is installed (go-task 3.54.0), so this is a combination
gap rather than a missing dependency.

**Where.** Both workspaces (`page-geometry-k4` in main; `prepared-pdf-k5` and the prep brief).

### 3. "Held-out" evaluation lines are not operationalised, so the improvement claim can be circular

**Contract.** `page-geometry-k4` lines 33–35 and 42–44 require independently marked guides,
"evaluation lines distinct from fitted lines" and held-out residuals; the research (step 2 and
the overfitting note) requires separate lines for fitting and evaluation.

**Consequence.** Leptonica chooses its fitting lines itself from the whole analysis image, so a
human-marked staff is held out only if the same physical staff is withheld from the analysis
mask. The leaf does not say to mask it, does not say what happens when masking leaves fewer
lines than the model's minimum (the research gives a default of 15) on a page whose systems are
few, and does not require the guides to be recorded before any candidate or baseline output is
seen, nor name a capture method, format or who marks. Without these, "improves beyond rigid
deskew on held-out lines" can be satisfied by the very lines the fit used, and
`corrected-book-k5` consumes that claim to classify the core result. The opposite reading
makes the leaf unfinishable with no stated fallback.

**Where.** Main.

### 4. The straight-control "forced warp" has no defined non-zero field

**Contract.** `page-geometry-k4` lines 44–45: "Examine a forced candidate warp on the verified
straight control as a diagnostic"; the research says a bypassed control tests the decision
policy, not the sampler.

**Consequence.** On a genuinely straight page the candidate's own model is expected to be
invalid or near identity. An identity or near-zero field through an integer-coordinate sampler
reproduces the pixels, so the control reads clean and the nondegradation check passes without
exercising the sampler. The leaf does not say which field is applied (the music page's, a
declared synthetic field, or the control's own), nor that it must be non-trivial, nor how its
magnitude is chosen. `corrected-book-k5` row "Verified Algorithm Design page-20 control"
re-uses this as the continuing fidelity check.

**Where.** Main.

### 5. A failed or inconclusive core has no defined continuation in `corrected-book-k5`

**Contract.** `corrected-book-k5` line 20 classifies the core as supported, rejected or
inconclusive; lines 23 and 26 give a consequence only for "survives" and "fails".
`page-geometry-k4` line 63 says "reject **or** mark inconclusive" for model-validity failure,
non-improvement, clipping and thin-detail loss alike, without a rule for choosing.

**Consequence.** Most failure conditions in the prototype may be filed either way, and the
planning leaf that consumes them has an outcome with no instruction. An inconclusive core (an
ambiguous reaction, an extraction failure that cannot be told from a model failure, a mildly
degraded control) is not "survives", so the expanded trial at the same settings is unjustified,
and by definition its evidence "justifies no specific next question", so the repair-trial
branch cannot be applied either. The session must guess, or retire with only the root-retention
bullet keeping the tree alive. It also leaves open whether an inconclusive result re-runs
`page-geometry-k4` at a narrower scope or goes back to the user.

**Where.** Main (both leaves).

### 6. Exclusion and reordering at book-page granularity after a spread split is owned by nobody

**Contract.** Root *Done when* ("supports reordering and user-controlled exclusion of blanks or
duplicates"); `plan-k1` assembly controls; prep brief line 16 gives these at PDF-page level, and
prep states that preparation does not split spreads.

**Consequence.** A genuine spread page whose right half is blank, or a half that duplicates a
page elsewhere, cannot be excluded or moved during preparation because the halves exist only
after the processor's split. No processor requirement in the brief's increment table or in
`corrected-book-k5` lists post-split exclusion or reordering; review adjustment is described
only for geometry. The requirement is silently satisfied at the wrong granularity, or left to
ordinary PDF tools after export without being recorded as a visible trade-off. Rated plausible
rather than certain because the user's boundary change may be read to place all assembly in
preparation; the plan should say which reading it adopts.

**Where.** Main (processor shaping in `corrected-book-k5`) and prep brief (scope statement).

### 7. There is no route for correcting the preparation tree from this workspace's review

**Contract.** This review's *Done when* directs an integration leaf in main before
`page-geometry-k4`; the integration reads findings from the review's commit.

**Consequence.** Findings 1, 2, 6 and 8 touch prep `_BRIEF.md`, `04-design--prepared-pdf-k4.md`
or `05-planning--prepared-pdf-k5.md`. Those files live in a different jj working copy. An
integrating session started here that edits them by absolute path writes into the other
workspace's `@` outside the integration's own commit and outside Grove's commit boundary, and
may be snapshotted into whatever prep session is open. The prep tree has no review or
integration leaf of its own for the commit `1ada47bd20fe`. The review is therefore anchored in
main while some of its fixes belong in prep, with no stated rule for where the corrective leaf
runs, and the cross-tree `**Integrates:**` handle would not appear in the prep tree.

**Where.** Both workspaces; consequence lands on the integration cut from this review.

### 8. The prep root brief overstates what the design leaf does

**Contract.** Prep `_BRIEF.md` line 38 says `prepared-pdf-k4` "tests PDF preservation through
the public interface"; its own body (*Notes*) says "This is design work" with a small verified
dependency experiment, and `prepared-pdf-k5` owns the working command.

**Consequence.** The public command does not exist while the design runs. A session reading the
brief chain first may build the command inside the design leaf, collapsing the
design/implementation boundary and the review that boundary earns, or may be unable to satisfy
a test through an interface not yet built. A contract stated unclearly rather than a defect in
the decomposition.

**Where.** Prep.

### Checked, no finding

- **Independent usability of preparation.** No correction service, GUI or processor is
  required; originals, collision and failed-write handling are in its *Done when*; the real
  fixtures cover all three book folders plus separate covers and an already-assembled input.
- **Explicit cover roles; single prepared PDF input.** Role is by assignment, not filename or
  page count; the successor handoff forbids a mandatory sidecar and collection discovery, and
  both the main *Test seams* and `corrected-book-k5` (final prepared-PDF run without
  collection access) preserve a one-PDF processor.
- **Model-failure handling in the trial.** Copied-output returns are reported as unsupported
  geometry, neighbouring-model substitution is off, model construction, validity and actual
  displacement are exposed, and the native-sampler/interpolation question is conditioned on
  demonstrated damage, matching the research.
- **Human reaction.** The ordinary comparison with a stated question, recorded rejection or
  inconclusive result and a durable experiment note matches the research's "user comparison
  remains necessary" and no invented threshold.
- **Fixture sequence.** Every expanded case in `corrected-book-k5` traces to a research row
  with its distinguishing question; the page numbers, printed pages and source identities agree
  with the research and its digest table.
- **Premature closure of the root.** Correction, spread, review/OCR and optional-cleanup scope
  are carried in `corrected-book-k5`'s *Done when* and by the root brief that every successor
  reads (its "must keep enough live work here" sentence), and `finish` waits on explicit human
  confirmation. Not rated a defect; `corrected-book-k5` remains a single point carrying
  several obligations, which a planning session may decompose.
- **No algorithm or interface chosen without evidence.** The Leptonica wrapper is a preference
  for a trial, explicitly not a selection, and the review technology, language and OCR mode
  remain open in the brief.

## Decisions (running log)

Eight findings warrant integration, so `book-reconstruction-k7` (`integrate-review-planning`)
was cut at the slot of `page-geometry-k4`, the first live sibling after this review, ahead of
the geometry prototype that consumes the plan. Its body names this review's handle and carries
no finding text. No leaf was cut in the preparation tree: that is another workspace's working
copy, and writing into it from this review would fall outside this task's commit. Finding 7
asks the integration to settle that route.
