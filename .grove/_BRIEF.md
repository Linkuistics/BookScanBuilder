# BookScanBuilder — brief

## Goal

Provide a personal workflow on the current Mac that reconstructs corrected book
PDFs from the user's scanned collection and optional separate cover PDFs.
Preserve the corrected page images as the visible content and add an English
OCR text layer for searching and selecting text.

Process one book at a time in two stages that can be run from the shell:
prepare one PDF by merging the chosen covers and content, then process that
single PDF. The user will use the shell to iterate over the collection.

## Done when

- Book PDFs from `Raw Scans`, `Processed Books`, and `Needing Cleanup`, with
  separate covers when supplied, can be prepared into one PDF per book.
- The main processing entry point accepts that one PDF and performs correction,
  cleanup, OCR, review and export without searching collection folders for
  content or cover scans. A PDF whose covers are already assembled is also a
  valid single-PDF input.
- Geometry correction addresses distortion that varies within a page, including
  the reported rotation during scanner feed. Assess previously processed pages
  as well; a prior pass does not prove that their geometry is correct.
- Genuine spread scans become one book page per output PDF page. A single book
  page on a larger landscape canvas remains a single book page.
- Default visual cleanup corrects geometry and removes scanner borders while
  preserving colour, faint text, illustrations and music notation. Paper
  whitening and noise removal are optional and previewable.
- Automatic processing is followed by review of flagged pages, with adjustment
  of any page available before export. Review changes appear in the final PDF.
- Assembly preserves source order by default, supports reordering and
  user-controlled exclusion of blanks or duplicates, and supports inserting
  cover pages. Preparation supplies these controls for selected PDF pages;
  the processor supplies exclusion/reordering for the book pages created by
  splitting a spread, before final OCR/export. Front and back covers have
  explicit roles and placement.
- The output retains visible page images and has an English OCR text layer
  whose search and selection positions align with the corrected images.
- Originals remain untouched, and already-correct pages are not degraded.
- The agreed test seam and visual comparisons demonstrate these behaviours on
  representative real inputs.

## Decomposition

The user confirmed the bootstrap requirements in `plan-k1`, including the
two-stage preparation/processing boundary.

- `scan-geometry-k2` surveys practical correction approaches and their failure
  cases, providing the evidence needed to choose a small real-page trial.
- `book-reconstruction-k3` uses that evidence to identify the smallest useful
  increments and cut the next design/prototype/implementation work as needed.

Geometry correction on real scans is the principal unresolved technical
question; its quality must be demonstrated before a method is treated as
settled. One focused survey is sufficient at this point; its job is to inform
the trial, not to promise an algorithm's success.

## Working increments

| Increment | Useful handoff | Dependency and ownership |
| --- | --- | --- |
| Explicit PDF preparation | One prepared PDF, with selected content order and explicit front/back covers, usable by ordinary PDF tools | First independently useful increment in this tree. `prepared-pdf-k9` and `prepared-pdf-k12` supply the integrated design; `prepared-pdf-k10` cuts `prepared-pdf-k13`, the complete command and its verification, ahead of geometry. No correction service is needed. |
| Corrected searchable book | One prepared PDF processed through accepted geometry, border removal, post-split assembly decisions, review adjustments and aligned English OCR into an exported PDF | Depends on working preparation's public contract and demonstrated geometry. `norwegian-measurement-k35` delivers a bounded per-half blind-addressing control failure; `norwegian-measurement-k38` consumes it and commissions human policy/source-response completion `geometry-policy-k39` before source-only `staff-acquisition-k27`, preserving `corrected-book-k28` after music acquisition. k39 cuts a fresh planner from actual responses before k27; k28 consumes that chain before cutting justified evidence/design/working processor slices ahead of appearance. The corrected-image schema and its working reader/export path belong to this same increment. |
| Optional appearance cleanup | Preview and selectively apply whitening or noise removal while keeping the working default processor and its accepted-image/OCR alignment | `appearance-cleanup-k22` owns the precise successor design question after the default processor works, then cuts its planning consumer before `workflow-acceptance-k23`. Compare faint print, music, illustration and colour before choosing a cleanup method. |

The user chose one workspace and one Grove tree for all three increments.
Preparation design/planning run first, and insert their implementation and
required reviews before geometry; preparation is useful without correction.
`page-geometry-k4` is a throwaway two-page comparison with a user reaction,
not a production increment or a settled algorithm. `corrected-book-k5` then
checks that result, commissions the precisely specified expanded fixtures or a
bounded repair trial, and shapes the next processor work. It must keep enough
live work here to check the root's end-to-end Done when against the integrated
increments; completion of a prototype or preparation does not close this root.

Preparation's useful PDF handoff includes selection/roles, copying and source
gates, runtime validation, safe publication, packaging, Taskfile integration and
public-command acceptance. Prefer one complete implementation leaf. If
`prepared-pdf-k13` exceeds one session, its declared fallback permits decomposition
into a complete dry-run preview and the complete writing command, each with its
own verification/docs. The preview validates real selections through every source
gate and reports planned order/roles; it shares the source-projection operation
with the writing child. Its temporary `prepare:plan` runner explicitly requires
dry-run, and the public `bookscan prepare`/`prepare:run` install only with working
writes. This keeps the public write/error contract intact. The preview creates
no PDF and cannot satisfy preparation's handoff; the writing child stays live
ahead of geometry until all preparation acceptance is complete. No horizontal
adapter/setup/test-only or real-acceptance-only cut earns a leaf.
A planning review of `prepared-pdf-k10` runs before `prepared-pdf-k13`; actionable
findings integrate before implementation. The finished implementation assesses
its need for a product review and inserts required review/integration before
`page-geometry-k4`. No speculative subtree or future review chain is pre-created.

Preparation's unstarted task contracts came from producer revision `1ada47bd`:
its old `prepared-pdf-k4` and `prepared-pdf-k5` are now local `prepared-pdf-k9`
and `prepared-pdf-k10`. The producer history is retained by the local bookmark
`archive/prepared-pdf-plan`. Its old on-disk checkout is historical context,
not an active Grove; continue all work here. `stage-handoff-k8` was abandoned
with the separate-workspace plan. No cross-tree corrective handoff or product
landing is required, and no driver is launched by this integration.

Each increment extends the same root Taskfile: `prepare:`, `geometry:` and
`process:` recipes have distinct names, while shared setup/dependencies are
reconciled in place. Run new/changed tasks and existing tasks affected by each
addition before relying on the combined file. The experiment must retain
wrappers its lasting recipes call, or remove/replace and verify those recipes
when discarding the wrapper. Processor acceptance owns the final check from
working preparation through one-PDF processing/export, with the collection
unavailable to the processor.

Preparation's `prepare:check` needs neither the collection nor Poppler.
`prepare:acceptance` owns synthetic/real renders; its synthetic-only mode must
work with the collection unavailable. Product fixtures are test-owned and do not
import the historical experiment. The actual `prepare:run` recipe verifies
spaced-path/exclusion forwarding against direct command output. Signal and kill
acceptance targets the installed writer PID with observed private barriers,
not a uv/Task launcher; ordinary subprocess checks retain the locked uv entry.

`prepared-pdf-k13` supplies automated evidence and comparison paths in
`docs/acceptance/prepared-pdf.md`. If preparation visual approval is pending,
`page-geometry-k4` presents those working-command comparisons alongside its
geometry trial, asks for a separate preparation response and records it there
and in its own running log. `corrected-book-k5` checks that response and retains
precise repair/missing-comparison work before processor acceptance when needed.
Pixel equality and code review do not settle the user's visual judgment.

`page-geometry-k4` now supplies the frozen two-page experiment in
`docs/experiments/page-geometry.md`: automatic music extraction failed on both
held-out and full input. Its separate geometry/preparation review PDFs were
presented, but the human responses were unavailable. `corrected-book-k5`
commissions the bounded `staff-guides-k20` follow-up and hands those exact visual
questions to it and `corrected-book-k21`; neither preparation nor geometry has
recorded human visual approval. Technical rejection of the automatic extractor
does not reject the vertical family or establish a sampler defect. Independent
staff traces are the only new trial commissioned.

Integration `corrected-book-k25` repairs that trial's evidence contract: the
coordinate-only preflight reproduces longest-line filtering, unique-line count
and exact library coverage checks after whole-staff/system exclusions; nearby
rules do not substitute for spatially separated evaluation. Dense manual traces
and an independent repeat pass establish measured uncertainty before outputs.
Prerequisite failure, invalid model, application/fallback copy, unresolved
measurement and unavailable visual reaction carry different named next steps;
none grants music expansion. Every further trial or completion, on any outcome
branch, retains a fresh planning consumer ahead of appearance design. The
coordinate/preflight evidence is the complete fallback slice if the trial
needs decomposition; corrected-image comparison and human reactions remain
owned by the complete prototype. These repairs grant neither human visual
approval nor a production method.

The user confirmed k25's two policy choices: k20 selects one suitable music
page from the already surveyed set that passes unchanged validity/coverage
checks, retaining page 140 as the historical unsupported-layout diagnostic.
Its manual/automatic acquisition comparison uses that same selected fixture.
After consuming k20, k21 may commission separately stated automatic
prose/gutter evidence on Norwegian page 20 and the verified prose control even
when music is rejected or inconclusive. That independent question does not
expand or accept the music core; its fresh planning consumer retains unresolved
music/preparation work. Each representative case still needs independent
evidence and human judgment before production commitment. The current live
leaf order and the default-processor/appearance/final-acceptance dependencies
remain the same; no additional trial is pre-created by this permission.

The ordering initially left by k21's retirement was its planning review, source-only
`staff-acquisition-k27`, fresh `corrected-book-k28` planning, optional-appearance
design, and final integrated workflow acceptance. The fresh planner inserts
justified trials/completion, processor design agreement and working
implementation before appearance design. That design inserts its
evidence/planning/implementation before final acceptance. No production leaves
are invented ahead of geometry/adjustment evidence. `workflow-acceptance-k23`
owns the root-wide product check through collection-isolated public processing,
post-split decisions, review edits, aligned OCR and optional appearance; each
default-processor slice still verifies its useful handoff before optional work.
Missing scope must be cut before root closure, not declared satisfied by a
retired trial or a design. This plan earns an external planning review before
its consumers run; integrations, if required, are cut lazily by that review.

`staff-guides-k20` decomposed to `staff-coordinates-k26` and closes on its
expressly allowed inconclusive-acquisition branch. The source-only result in
`docs/experiments/staff-guides.md` rejects the initial dense visual coordinates:
occluded/outside-rule points and 4–6-pixel representative discrepancies exceed
the stated uncertainty. Native count/coverage gates pass only on inadmissible
diagnostic coordinates; no model/correction or matched page-20 automatic
comparison was generated. Page 20 / printed 6 remains a candidate whose genuine
source tracing and repeatability need precise completion. k21 owns that named
question before a fresh pre-output freeze/native preflight, and retains the
unperformed output/control/sampler/visual comparison and a fresh planning
consumer after any commissioned completion. This neither rejects the vertical
family nor licenses music expansion. The user explicitly answered “Not
inspected yet” separately for historical geometry and preparation views;
their visual responses remain unresolved. k21 consumes that result through the
repair and fresh planning work below; k22 and k23 remain ordered consumers.

`corrected-book-k21` commissions `staff-acquisition-k27` as a complete
source-only repair, followed on every outcome by `corrected-book-k28` before
appearance. The change under test is exact native-patch manual observation
instead of wide-strip estimates: fresh genuine rule-centre marks, a blind repeat
of representative whole traces, measured uncertainty, unchanged A/E/H whole-
staff exclusions and exact native count/rounding/coverage gates. The rejected
records stay frozen. No real fit or corrected output follows within that repair,
even on success. Invalid/ambiguous acquisition, insufficient coverage,
unresolved measurement/instrument or an unavailable source-view reaction have
precise consumer questions; numerical gate success is not physical-source or
model acceptance. The repair also re-presents the historical geometry and
preparation questions separately and retains any missing answers or defects.

k28 reads the complete k21 contract and inserts the next justified completion
or complete matched automatic/manual comparison on page 20, including the
missing output/control/sampler/reaction evidence. It now consumes the independent
automatic Norwegian-gutter result commissioned by k30 as k31, regardless of
music status; that trial cannot accept music or preparation. No unconditional
manual retry, music expansion, interpolation or
two-axis change follows from this acquisition failure. Every further trial or
response completion gets a fresh planner before appearance. The fixed real
representative cases and the default processor's accepted-image/review/post-
split assembly/aligned-OCR/export increment remain outstanding; k22 and k23
cannot consume assumed products. This successor plan earns review before k27.

Integration `corrected-book-k30` repairs that plan before acquisition. k27 first
records unchanged automatic acquisition diagnostics through an extraction-only
path and genuine manual endpoint/native-gate evidence; automatic prerequisite
success changes the question for k28 and stops the dense manual pass, without
claiming model validity. The repair retains the T/B/D/I fit roster and complete
A/E/H exclusions. Dense first marking and whole-trace repeats receive stripped
coordinate-free packets in fresh contexts; every eligible observation has an
independent native-source verification record. Same-context agreement and
sampled human inspection cannot calibrate the other points. Known-centre
validation remains labelled separately and proves no real-page accuracy.
Recorded rise/curvature and systematic uncertainty accompany repeatability;
repeatable-but-too-coarse evidence cannot earn a trial. A point invalidated after
freeze voids the attempt rather than becoming an omitted column. First-pass
child completion never classifies the overall acquisition; concrete remaining
repeat/preflight/reaction work stays live before k28. Roster changes need a
separate declared question, and leaving the six-page surveyed fixture pool
needs a fresh human decision; visual nonselection did not exhaust its gates.
k28 carries these outcome questions and the complete inherited processor,
appearance and root acceptance contract. k22/k23 read k28 and its actual cut
successors, rather than nonexistent k21 descendants. No visual approval,
production method or corrected result is established by these plan repairs.

The human approved k30's recommendation to run the independent Norwegian-gutter
trial before music acquisition. The sequence established by k30 was k31, its fresh
planning consumer cut lazily by k31 before k27, then k27 → k28 → k22 → k23.
k31 asks whether the unchanged automatic vertical candidate improves both
manually separated Norwegian page-20 / printed-36–37 halves beyond rigid,
with independent measurement/reactions and verified Algorithm Design control/
native-sampler evidence. Each half has its own prerequisite/model/application/
quality/measurement/reaction outcome; one half or the control cannot accept
another. Unsupported halves stay usable/flagged with no borrowed/forced model.
That fresh planner preserves k27/k28's relative order and carries every unresolved
music/preparation/representative/product/appearance/root-acceptance obligation.
k28 consumes the independent result without automatically commissioning it again.
This sequencing approval changes no method, validity rule or visual disposition.

`norwegian-gutter-k31` closes with k33's bounded inconclusive instrument/
measurement outcome on each half, recorded in `docs/experiments/norwegian-gutter.md`.
The source/canvas/crop freeze holds; fresh coordinate-free observers identify
text but admit no verified native baseline coordinates or quantified systematic
uncertainty through view_image. Unmasked counts remain diagnostics; no masked
gate, model, rigid/candidate comparison, output measurement or control/sampler
revalidation exists. The source/instrument human reply is unavailable, and
correction/detail reaction questions remain unperformed without matched views.
k34 consumes this precise result before k27 → k28. Its changed observation is
whether pixel-addressed native patches with explicit glyph anchors can furnish
blind repeats and per-point verification with measured systematic limits;
it must decide that complete evidence question rather than repeat the same
viewer trial. All unperformed k31 comparison/control/sampler/reaction obligations
and every unresolved music/preparation/fixed-case/default-product/appearance/
root-acceptance obligation remain with k34 and the ordered consumers.

`norwegian-gutter-k34` commissions `norwegian-measurement-k35`, a complete
source-only instrument/measurement question: can pixel-addressed native patches
with explicit physical non-descending glyph anchors supply fresh whole-line
repeats, independent per-point verification and defensible shared systematic
limits across actual gutter/centre/outer ink in both unchanged halves? It keeps
the x=1785 split/full canvases, predeclares physical lines/ambiguity/exclusions
before masked extraction and retains exact unchanged native gates. Repeatability
and known-centre addressing controls cannot establish real baseline accuracy.
No rigid/model/field/correction is generated, even on acquisition success.
Failure or too-coarse/systematically unresolved evidence receives its exact
next question; no forced validity, gate/holdout rescue or same-viewer retry.
This is evidence within the default increment, not another product stage.

`norwegian-gutter-k37` integrates k36's review before k35. Require an exact-format
blind known-centre addressing check and coordinate-free physical holdout/region
declaration, freeze and unchanged masked-native feasibility before dense marks.
Stop a failed half without classifying the other or spending its dense pass.
The archive constrains removal of unchanged traces (right at most ten; left
loses the minimum on removal of a retained trace), but pinned extraction includes
vertical filtering/component recovery and a relative length threshold: it does
not prove general masked impossibility. No gate-driven holdout search or rescue
is permitted. k35 records glyph/font/style contrasts and positional coverage,
220-ppi JPEG sampling versus the 300-dpi render, compression/resampling and
unresolved common bias separately from repeatability. Internal contrasts and
synthetic addressing success cannot certify real baseline accuracy. k28 and
actual successors carry these dispositions; k22/k23 consume that current chain.

The resulting order is k34's planning review and k37 integration, k35, its fresh
planner cut on every outcome before k27, then k27 → k28 → k22 → k23. k27/k28 retain their
relative order. k28 consumes k31/k34 and k35's actual completion and planner,
without recommissioning the old Norwegian trial. All conditional masked-fit/
rigid/output/control/nonidentity-sampler/independent-measurement and separate
human comparison obligations remain unperformed until explicitly justified
and delivered. Every unresolved music/preparation/fixed-case/design/default-
product/appearance/root obligation stays with these consumers. No production
decision, source approval, historical response or corrected result is inferred.

k37 put two policy recommendations to the human: separate numerical source
admissibility from an unavailable source reaction, and allow consideration of a
rigid-plus-flagged intermediate processor while nonrigid evidence continues.
Absent an explicit reply, source-reaction ranking and demonstrated-geometry
prerequisites remain unchanged. k35's fresh planner and k28 carry the precise
unanswered choices; another measurement trial cannot supply a human reply.
No policy option waives processor design, useful default acceptance, within-page
geometry, representative cases or final integrated root acceptance.

## On the horizon

The production correction field, automatic confidence policy and manual
adjustment controls depend on the user's reaction to the real-page trial.
Their implementation decomposition cannot yet be stated honestly. Concrete
whitening/noise-removal mechanisms still need appearance evidence, but their
precisely known preview/fidelity design question is now `appearance-cleanup-k22`
after the working default accepted-image/export seam. No method is chosen here.

## Pointers

- `CONTEXT.md` — the project's terminology.
- `docs/specs/prepared-pdf.md` — preparation's public command, preservation and
  single-PDF handoff contract; its dependency evidence and visual companion are
  linked there. Design review runs before implementation planning consumes it.
- `docs/adr/prepared-page-hints.md` — persisted advisory roles/provenance and
  their sole-PDF, optional-reader compatibility decision.
- `plan-k1` — the bootstrap requirements and running decision log.
- `/Volumes/Glass/Book Conversion` — the input collection; exact inspected
  examples and PDF page numbers are recorded in `plan-k1`.

## Test seams

Agreed with the user: use representative source PDFs from all three book folders
and separate covers. Check preparation at its public entry point for cover-role
placement and preservation of content order. Then exercise the main processing
entry point with one assembled PDF, through correction, cleanup, OCR, review
decisions and export. The main process must work without access to the source
collection folders; it receives their prepared PDF rather than discovering
inputs itself.

Check geometry across the page, including text and staff lines; fine-detail
retention; spread splitting and assembly order; alignment of English search
and text selection; application of review adjustments; unchanged originals;
and preservation of already-correct pages. Combine repeatable fixture checks
with the user's visual judgment of before/after geometry samples. A numerical
score alone does not establish visual acceptance.

## Preparation acceptance cases

Preparation accepts explicitly selected source PDFs/pages, preserves content
order by default and permits deliberate reordering/exclusion at PDF-page
granularity. Cover roles and placement are explicit, including multi-page
covers and the already-assembled/no-cover case; page count or filename cannot
decide roles. The processor owns equivalent controls for halves created by
spread splitting. Preparation preserves each complete selected PDF page's
visible content and canvas, with no spread classification, warping, appearance
cleanup or OCR. Selection errors must be actionable; source/output collisions
and failed/interrupted writes cannot corrupt originals.

Paths below are relative to `/Volumes/Glass/Book Conversion`; page numbers are
one-based PDF pages. The preparation design specifies the public command test
seam and may validate copying assumptions with a bounded dependency experiment.
The implementation exercises the working command with these cases.

| Input case | Acceptance |
| --- | --- |
| `Raw Scans/Fundamentals of Musical Composition.pdf`, pages 40 and 140, with `Covers/SchoenbergComposition.pdf`, page 1 explicitly assigned front | Front then selected content order; mixed visible PDF objects and music marks remain intact, with no geometry/appearance change. |
| `Processed Books/Norwegian - An Essential Grammar (Routledge)/Norwegian - An Essential Grammar (Routledge).pdf`, page 20 | Preserve the complete spread PDF page for later processor classification/splitting. |
| `Needing Cleanup/Counterpoint in Composition.pdf`, page 20 | Preserve the single printed page and landscape canvas as one PDF page. |
| `Processed Books/Algorithm Design/Algorithm Design.pdf`, page 20 | Preserve complete existing content; folder membership grants no correction exemption later. |
| Distinctly labelled four-page cover fixture plus content fixture | Explicit front/back/interior/omitted selections and reordering yield the requested order. Choose an available real multi-page cover PDF by direct inspection as a companion case. |
| Already-assembled input without a separate cover | Valid preparation use and valid single-PDF successor input without rediscovering covers. |

Check page counts, full-page visible render comparisons and source digests
before/after. Exercise invalid selections, output collisions and interrupted/
failed writes at the public command seam. Keep copied fixtures and derived
outputs outside the source collection. Synthetic order labels establish exact
order; real-PDF comparisons establish fidelity. If role/provenance data is
needed downstream, retain it with a handoff whose sole required input is the
prepared PDF, with no mandatory sidecar or collection discovery.

## Notes

An app or process is acceptable. Native application packaging, other operating
systems, other users, and an application-level multi-book queue are not required.
English is the OCR target; other visible languages and all non-text content
remain in the page images.

Some cover PDFs contain several pages, potentially including front and back
covers. Page count or filename alone does not establish each cover page's role.
The preparation/assembly flow must permit explicit assignment. Optional review
adjustments after processing must still be reflected in the export; no later
step may need to rediscover separate cover files.

No correction algorithm, implementation language or review-interface technology
has been selected. The first test book has not been explicitly chosen by the
user; the inspected examples are candidate fixtures rather than approved
correction results.

There was no project Taskfile at bootstrap. Adding a root `Taskfile.yml` was
suggested; introduce it when deterministic development commands are concrete,
wrap existing tools where appropriate, and verify its tasks before relying on
them.

## Preparation implementation and visual handoff

`prepared-pdf-k13` delivers the complete installed `bookscan prepare` command:
`prepared-preview-k16` established the shared read-only planning/gate operation,
and `prepared-pdf-k17` completed writing, runtime comparison, safe publication,
packaging, Task integration and synthetic/real/all acceptance. The temporary
preview module/recipes are retired; use the public command for dry-run and writes.
The complete contract remains `docs/specs/prepared-pdf.md`; retained per-item
reports and full-page/native-zoom comparison paths are in
`docs/acceptance/prepared-pdf.md` (all-v2 artifacts at
`/private/tmp/bookscan-prepared-k17-all-v2`).

The completed subsystem earns an external `review-impl` before geometry; any
required integration is cut lazily by that review before consumers. Human
preparation visual approval remains pending, explicitly owned by
`page-geometry-k4` separately from its geometry response and checked by
`corrected-book-k5`. Preparation completion closes neither the geometry trial,
the default processor, optional appearance cleanup nor this root's full
collection-isolated end-to-end acceptance. Those obligations stay live.

Integration `prepared-pdf-k19` repairs caught-signal validation codes, resource
acquisition/cleanup ownership and result serialization, accepts reversed
rectangle corners while preserving their original coordinates, pins negative
numeric PAGES to `INVALID_SELECTION`, checks both Poppler tools and removes the
retired preview API/test callbacks. Signals are recorded and checked at safe
operation boundaries; cancellation can wait for the current operation, and an
already chosen error/finalized plan keeps its result during delivery. The spec,
help and README also record the accepted retained-byte memory cost and resource
duplication per output page. Latest frozen synthetic/real/all evidence and
comparison paths are in `docs/acceptance/prepared-pdf.md`, using
`/private/tmp/bookscan-prepared-k19-all` for current human comparisons. The
producer reports remain historical and unchanged; preparation visual approval
still belongs separately to `page-geometry-k4` and is checked by
`corrected-book-k5`.

## Norwegian prerequisite decomposition and bounded closure

`norwegian-gutter-k31` decomposed at its allowed complete inspectable
prerequisite boundary. `norwegian-preflight-k32` freezes the full RGB source,
manual seam canvases and unmasked native extraction diagnostics in
`docs/experiments/norwegian-gutter.md`; it generates no rigid/model/corrected
output and supplies no independent marks or held-out acceptance. The remaining
child k33 closed only the admitted bounded inconclusive source-instrument branch,
without independent numerical marks or a correction. k34 consumes both committed
results and commissions k35's precise changed source-measurement question.
All unperformed independent acquisition/holdout/masked-prerequisite and conditional
complete output/control/sampler/measurement/reaction work remains with k35's fresh
planner and actual cut successors, before k27 → k28. No partial count licensed production or closed k31;
its bounded instrument result, rather than count success, justified closure.

`norwegian-measurement-k35` closes its admitted early instrument outcome for each
half: the fixed 16× labelled-grid/view_image method fails every blind known-cell
readback in left/right/verifier contexts, even when they agree. Its ordinary
native/grid controls, raw reports, error intervals and canonical verification
are linked from `docs/experiments/norwegian-measurement.md`. Source/canvas identities
and full split recombination hold; real marks/rosters/holdouts/masked extraction/
systematic limits and all correction work remain unperformed. Each half's human
source/instrument reply is unavailable; real-anchor/output reactions remain
unperformed without views. This rejects only that attempted observation method,
not every addressed instrument or the vertical family. `norwegian-measurement-k38`
decides only a genuinely changed selected-cell/readout observation or precise
human policy/response completion; another instrument study needs a separately
justified human choice. No same-grid retry, baseline bias bound, model or
production acceptance follows. k27 → k28 → k22 → k23 and every inherited
music/preparation/fixed-case/default-product/appearance/root obligation stay live.

## Geometry policy and source-response completion

`norwegian-measurement-k38` consumes all nine failed k35 readbacks without
extending their scope. It chooses `geometry-policy-k39`, a focused human
requirements completion, before k27. The two k37 policy questions were
re-presented during k38; absent an actual reply, their current reaction ranking
and demonstrated-geometry prerequisites remain in force. k39 checks for later
answers before re-asking and records explicit choices or an explicit deferral;
silence alone leaves its policy work live rather than spawning another
unavailable-response/planning loop. It separately obtains or records unavailable
left/right reactions to the existing unchanged source/control views. Real-anchor
and correction reactions remain unperformed. Historical geometry/preparation
responses remain with k27 then k28, separately “Not inspected yet”.

No new Norwegian instrument study, retry or production method is commissioned.
A genuinely changed selected-cell/readout observation still needs a separately
justified human choice, then fresh exact-format blind addressing controls and
the complete physical/source-systematic/masked-native evidence contract; known-
centre success cannot bound real shared baseline bias. A reply to a source view
cannot erase k35's failed numerical controls or grant correction approval.

On every actual completed response handoff, k39 cuts a fresh planning consumer
before k27. It consumes the actual answers and full k38/k31/k21/k28 obligations,
without automatically repeating a trial or the same missing-response question.
The relative order remains k39 → its fresh planner → k27 → k28 → k22 → k23.
Every unresolved conditional Norwegian comparison/control/nonidentity sampler,
independent measurement/reaction, music20/music140/fixture-pool, preparation,
fixed-case, processor-design/default-product/OCR/appearance and root acceptance
criterion remains live. Neither policy option supplies representative evidence,
chooses production technology or closes within-page geometry/root acceptance.
