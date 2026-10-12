# BookScanBuilder — brief

## Goal

Provide a personal workflow on the current Mac that reconstructs corrected book
PDFs from the user's scanned collection and optional separate cover PDFs.
Preserve the corrected page images as the visible content. Focus this tool on
geometry within each page and consistent book geometry: page alignment/matching
and explicit odd/even or left/right treatment. Page reordering and OCR are
separate third-party operations after geometry export.

Process one book at a time in two stages that can be run from the shell:
prepare one PDF by merging the chosen covers and content, then process that
single PDF. The user will use the shell to iterate over the collection.

## Current scope clarification

In `rotation-processor-k41` the human stated: “We don't need to worry in this
tool about re-ordering pages, because we can do that in a separate third-party
tool. We can also do the OCR entirely as a separate pass. The difficult part
that this tool needs to focus on is the geometry of each page, and the geometry
of the book i.e. page alignment matching, odd/even pages etc.”

This current instruction governs conflicting OCR/processor-reordering language
in the historical decomposition and records below. Keep the shipped preparation
command and its past evidence unchanged, but commission no processor reordering
or OCR work. Preserve every input occurrence and order, expanding confirmed
spreads only. The revised design must establish book-side/group assignment,
alignment references, common canvas/margin and scale policy with their public/
visual acceptance. Existing local/nonrigid evidence and pending human judgments
remain required; the narrowed scope is no acceptance of geometry or Draft v1.

## Done when

- Book PDFs from `Raw Scans`, `Processed Books`, and `Needing Cleanup`, with
  separate covers when supplied, can be prepared into one PDF per book.
- The main processing entry point accepts that one PDF and performs geometry
  correction, supported cleanup, review and image-only export without searching collection folders for
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
- Geometry processing preserves every input occurrence and source order,
  expanding genuine spreads in declared reading order. Blanks and duplicates
  are never silently deleted; subsequent reordering/removal and OCR are external.
  The shipped preparation command retains its explicit cover/content assembly.
- Book geometry supports reviewed page alignment/matching, a shared canvas and
  explicit odd/even or left/right assignments without assuming PDF index equals
  printed-page parity. Cover/front-matter/blank and parity-break cases remain
  inspectable. Matching preserves content and the agreed scale policy.
- The exported PDF retains accepted visible page images, contains no stale
  earlier text layer and is usable as the input to separate reordering/OCR tools.
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
| Page and book geometry with review/export | One sole PDF processed through supported rigid rotation, safe borders/splitting, any-page review and book-side alignment/matching, with accepted image-only export; unresolved local distortion stays explicit | The human agreed k41's v2 geometry-only design and scale-preserving alignment. Earned design review precedes its fresh implementation planner. Its own public/visual acceptance includes alignment/odd-even cases. Representation/review/export land together. This is no within-page or full-root acceptance. |
| Complete corrected book geometry | The same review/export seam extended through demonstrated within-page correction and independent full representative and book-alignment acceptance | Preparation and the supported intermediate seam remain inputs. k27 then k28 stay live; k28 owns justified nonrigid evidence/design/completion before appearance. No Norwegian study is commissioned by the scope clarification, and flags never satisfy correction. |
| Optional appearance cleanup | Preview and selectively apply whitening/noise removal while preserving accepted page/book geometry and image-only export | k22 follows accepted complete default geometry, then cuts its planner before k23. OCR and reordering remain external. |

The user chose one workspace and one Grove tree for the earlier working
increments. This plan carries that choice forward to the intermediate stage
considered under k39's permission; k39 records no separate workspace/tree answer.
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
k39 has since settled both choices with explicit “yes” and “agreed”; see Geometry
policy and source-response completion below for the current disposition. The
current consuming chain carries those replies and their limits; another
measurement trial cannot supply a human reply.
No policy option waives processor design, useful default acceptance, within-page
geometry, representative cases or final integrated root acceptance.

## On the horizon

The production nonrigid correction field and its confidence policy depend on
independent evidence and the user's reaction to the real-page trial. Their
implementation decomposition cannot yet be stated honestly. The complete
intermediate rotation/review/adjustment/export design is now the precise
`rotation-processor-k41` agreement question; its implementation is not assumed.
Concrete whitening/noise-removal mechanisms still need appearance evidence, but their
precisely known preview/fidelity design question is now `appearance-cleanup-k22`
after the working default accepted-image/export seam. No method is chosen here.

## Pointers

- `docs/specs/rotation-processor.md` — agreed v2 page/book geometry design,
  with scale-preserving alignment, external OCR/reordering and its public/visual
  test seams. The human replied “agreed”; no working-product acceptance follows.
- `docs/adr/geometry-review-handoff.md` — processor-owned resumable project
  and optional exported report semantics, preserving preparation-hint meaning.

- `docs/adr/finite-baseline-commands.md` — permanent finite names and blocking
  browser names, preserving shell-loop termination through browser completion.
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
entry point with one assembled PDF, through per-page correction, book alignment,
supported cleanup, review decisions and image-only export. The main process must work without access to the source
collection folders; it receives their prepared PDF rather than discovering
inputs itself.

Check geometry across the page, including text and staff lines; fine-detail
retention; genuine spread splitting and preserved order; shared canvas and
odd/even or left/right alignment; application of review adjustments; unchanged originals;
and preservation of already-correct pages. Combine repeatable fixture checks
with the user's visual judgment of before/after geometry samples. A numerical
score alone does not establish visual acceptance.

## Preparation acceptance cases

Preparation accepts explicitly selected source PDFs/pages, preserves content
order by default and permits deliberate reordering/exclusion at PDF-page
granularity. Cover roles and placement are explicit, including multi-page
covers and the already-assembled/no-cover case; page count or filename cannot
decide roles. The geometry processor preserves every half created by confirmed
spread splitting in declared reading order; external tools own later removal
and reordering. Preparation preserves each complete selected PDF page's
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
| `Raw Scans/Garbage Collection - Algortihms for Automatic Dynamic Memory Management.pdf`, page 30 | Preserve the complete page, code indentation, glyph widths and boxes/arrows for the processor's independent fixed-case geometry/detail acceptance. |
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

The agreed k41 design selects the Python/PDF geometry dependency approach and
shell/local-browser review, with scale-preserving book placement. A production
nonrigid correction method and its measured support remain unresolved. The first
test book has not been explicitly chosen by the user; the inspected examples
are fixtures, not approved correction results.

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
requirements completion, before k27. In k39 the human replied “yes” to recording
numerical evidence separately from pending visual review. Numerical source
evidence admissibility and source-view reaction now have independent dispositions:
missing review does not veto otherwise verified numerical evidence, and no
numerical result implies visual approval. k35's failed controls and all physical/
systematic evidence requirements remain unchanged. The human also replied
“agreed” to considering a rigid-plus-flagged intermediate working processor
while nonrigid evidence continues. The fresh planner may consider its design
before demonstrated nonrigid correction, with design agreement and the complete
useful review/adjustment/post-split assembly/aligned-OCR/export handoff and its
own acceptance still required. No method or technology is selected, and all
within-page/fixed-case/final root obligations remain live. k39 re-presented the
existing unchanged left/right source and A/B/C control views at their verified
identities. Both source replies are unavailable separately, with no human
inspected path, defect or approval; neither is an actual “Not inspected yet”.
Real-anchor and correction reactions remain unperformed. Historical geometry/
preparation responses remain with k27 then k28, separately “Not inspected yet”.

No new Norwegian instrument study, retry or production method is commissioned.
A genuinely changed selected-cell/readout observation still needs a separately
justified human choice, then fresh exact-format blind addressing controls and
the complete physical/source-systematic/masked-native evidence contract; known-
centre success cannot bound real shared baseline bias. A reply to a source view
cannot erase k35's failed numerical controls or grant correction approval.

This completed response handoff inserts `geometry-policy-k40`, a fresh planning
consumer before k27. It consumes the actual answers and full k38/k31/k21/k28
obligations,
without automatically repeating a trial or the same missing-response question.
The handoff order is k39 → k40 → k27 → k28 → k22 → k23.
Every unresolved conditional Norwegian comparison/control/nonidentity sampler,
independent measurement/reaction, music20/music140/fixture-pool, preparation,
fixed-case, processor-design/default-product/OCR/appearance and root acceptance
criterion remains live. Neither policy option supplies representative evidence,
chooses production technology or closes within-page geometry/root acceptance.

## Intermediate processor design handoff

**Current applicability:** k41's latest human scope correction governs this
handoff. Its revised design is page/book geometry with review and image-only
export; processor reordering and OCR are external. The descriptions below record
the earlier commission and review repairs, not permission to restore the removed
features. The revised agreement and working acceptance must include explicit
book-side/group/parity semantics and alignment/matching without content loss.
Within-page correction and all independent evidence/response obligations remain.

The human has now replied **“agreed”** to the published v2 geometry-only design
and scale-preserving matching policy. Its public/full/native/pair/group seam is
the agreed design contract; implementation and actual product acceptance remain
outstanding. k41 finishes that artifact, earns its external design review and
cuts its fresh implementation planner before k27 as the last work act. Review
integration, if actionable findings earn it, must precede that planner. k27 then
k28 retain their source/nonrigid roles and k28 owns every complete-default gap
before appearance/final acceptance. No OCR/reordering subtree is commissioned.

`geometry-policy-k40` commissions `rotation-processor-k41` before k27: design
the smallest complete supported-rotation/flagged-unknown/review/any-page-edit/
post-split-assembly/aligned-English-OCR/export workflow, with its own public and
visual acceptance and human design agreement before implementation planning.
This changes the next question from another source study to a useful product
design. It selects no method, technology or interface and grants no correction
approval. Unknown within-page distortion cannot become an unflagged “correct”
classification merely because measurement is unavailable. The intermediate
accepted-image representation and working review/reader/export stay together.
All fixed cases are assessed independently for its actual rotation/preservation
claims while their unresolved nonrigid acceptance remains with k28.

`geometry-policy-k43` clarifies the design charter: distinguish the universal
unverified within-page limitation from recorded per-page triage and the limited
meaning of unflagged. The design answers review-state persistence/resume/re-run
invalidation and what review/export convey without changing the ordinary
sole-PDF input boundary. Numerical rotation/sampling claims need independent
known-by-construction controls, including upright/small-angle and local-variation
cases and wrong-subject failures; a correcting estimator is no truth oracle.
Real-page numerical claims need a validated independent instrument or remain
numerically unavailable beside separate visual evidence. No new study or
threshold is chosen here. Garbage Collection30 remains an explicit preparation
and final-acceptance companion alongside every inherited fixed case.

k41 cuts its fresh implementation planner lazily before k27 from the actual
agreed design, assessing any design review before that consumer. Agreement
requires an actual verbatim human reply scoped to the spec/version, shape and
test seams; k39's policy permission is no signature. A drafted but unsigned k41
stays live for the human, cutting no implementation planner and retiring no
unagreed design. A genuinely different missing evidence question may earn its
own completion/fresh-planning handoff on every outcome; an unavailable signature
alone earns no identical response/planning loop. The agreed-design planner
chooses complete working slices, preserves k27 → k28, and keeps the full default
correction increment before k22/k23. k27's music source protocol is unchanged;
k28 consumes the intermediate agreement and actual working successors rather
than duplicating its initial design. It still owns the exact within-page
evidence/completion and later geometry-design agreement. The current root Done
when retains full within-page/book geometry under the human's geometry-only
scope. Appearance requires accepted complete default correction, not
the intermediate export alone; final k23 still verifies all root criteria.
Working-slice charters must state reaction-pending retirement boundaries and
precise missing-acceptance ownership. Numerical pass/fail/unavailable and human
visual accepted/pending/rejected stay separate, with actual inspected paths and
scoped replies. A retired technical slice or numerical pass supplies no missing
visual acceptance; k28 retains it before k22/k23. k28's locally scoped inherited
production bullets govern full nonrigid acceptance/design extension, while k41
owns the initial intermediate design.

This planning cut earns an external `review-planning` of k40 before k41, focused
on the completeness of the useful intermediate boundary, honest unknown/flagged
geometry and preservation of every inherited evidence/product dependency.
Integration is cut lazily from actual findings immediately before its consumer.
No in-session reviewer, future design review, implementation subtree, Norwegian
study or repeated identical response completion is pre-created. The current
handoff is k40 → its planning review/any earned integration → k41 → its lazy
planning/working successors → k27 → k28 → actual within-page/default-completion
successors → k22 → its appearance successors → k23, in the same workspace/tree.
Numerical source admissibility and source reactions stay separate under “yes”;
both Norwegian source replies remain unavailable, real-anchor/output reactions
unperformed, and historical geometry/preparation separately “Not inspected yet”.
No intermediate design/export or flag closes those obligations by proxy.

The agreed-design handoff is now concrete: rotation-processor-k41 → rotation-processor-k45
(earned design review) → rotation-processor-k46 (integrated clarifications) → rotation-processor-k44
(fresh implementation planner) → k47 → k48 → k49 → k50 → k27 → k28 → complete-default successors →
k22 → k23. The planner consumes the reviewed v2 spec/ADR and preserves all
page/book public and visual seams, separate numerical/reaction ownership and
the outstanding full within-page/default acceptance. Integration, if earned,
lands immediately before that planner; k44's concrete cuts and earned planning
review are described below. OCR/reordering remain external. Stable handles govern
references; k44 adds explicit missing-acceptance ownership to its consumers below.

k46 retains the signed 300-dpi MediaBox RGB baseline and exposes source-relative
downsampling/colour/extent limitations; unchanged baseline bytes or an export
acknowledgement cannot pass failed preservation by proxy. Coordinate composition,
run/group/repeat parity, padding/unpositioned members, reference/overflow
invalidation, unresolved dispositions, report schema/hint omission and authenticated
server/lock/stop semantics are now explicit at the same public/full/native/pair/
group seams. k44 consumes those repaired cases and actual unresolved outcomes.
No new signature, source study, production geometry acceptance or root closure
is inferred; full within-page/default acceptance remains k28's before k22/k23.

## Reviewed-design working slices from k44

The agreed v2 design and k46 clarifications retain four stage owners in this
existing workspace/tree. k52 decomposes the oversized first owner into two
complete useful handoffs. k53 now retains its whole baseline handoff as a node,
with baseline-delivery-k56 permitting finite-review staging and
baseline-delivery-k59 approving its concrete interface/test seams and finite-owner
session exception before k54. This carries
forward the human's earlier
one-tree choice; it attributes no new workspace answer to k39 or k41. Each
stage must stay green and demonstrable without its successor. The dependency is
behaviour, not module location. The complete browser commands remain `bookscan
process PDF --workdir PROJECT`, `bookscan review PROJECT` and finite `bookscan
export PROJECT --output PDF`, with authenticated review and normal Stop. The
approved permanent finite baseline command family precedes browser completion;
its duration never changes or silently aliases process/review.

| Stage / owner | Independent useful handoff | Scope deliberately left to successor |
| --- | --- | --- |
| `page-review-k47`: `baseline-review-k53` then `page-orientation-k54` | k53 delivers full-page RGB import/assessment, source/full/native any-page inspection, durable dispositions/acknowledgement, resume/Stop and unchanged-baseline image-only export. k54 adds exact right-angle preview/accept/discard/revert, saved revisions and their resume/export. k47 closes only after both. | Orientation edits are visibly unsupported until k54. Fractional rotations, crops, splitting and book placement remain unsupported until their owners; every occurrence stays whole. Skew suggestions are assessment records, never applied edits. |
| `rigid-pages-k48` | Accept/adjust/reject fractional rigid proposals and restorable four-edge crops through the same resume/export reader | No spread expansion or group placement yet. Ambiguous/curved geometry remains retained/unresolved. |
| `spread-pages-k49` | Confirm genuine spreads, edit each complete half independently and export expanded order/provenance | Book-side matching follows; single landscape pages remain single. |
| `book-placement-k50` | Explicit side/body-run/group review, integer placement and common canvas with full/native/pair/group acceptance/resume/export | Full within-page correction and full-default representative acceptance remain k28's. |

baseline-review-k55 found no substantiated smaller browser-first baseline handoff
among its examined cuts. baseline-delivery-k56 obtained “Permit the temporary finite
reviewer staging”. In baseline-delivery-k59 the human then replied verbatim “yes”
to the concrete protocol/test-seam proposal and the specific finite-owner-only
multi-session delivery exception. The current spec and finite-baseline-commands
ADR now define permanent finite commands, exact view/revision receipts, separate
inspection/reason disposition/scoped acknowledgement, transaction/lock/signal/export
lifecycle and private/public compatibility. The saved-project/report and
preparation-hint ADR meanings are unchanged.

k59's Agreed first-handoff and browser ownership map retains all twelve original
k53 criteria. Its Agreed delivery inventory specifies the remaining renderer/
analyzer/helper, project/packet/actions/export and independent/public/fault/six-case
work. One complete finite F implementation owner may stay live across focused
sessions, with internal unfinished milestones and no partial retirement or
horizontal/acceptance-only child. This explicit exception changes cadence only:
ordinary static PDF, complete 300-dpi RGB, every-page assessment, fidelity/safety,
six-case packets and compatibility remain required. No measured one-session fit,
input restriction, image or product/visual acceptance follows.

The actual agreed design earns review before its fresh implementation planner.
That planner must cut both complete working F and complete browser B ownership
inside k53 before k54. B retains co-located views/actions, authenticated Stop,
foreground readiness/terminal/export events, lifetime lock/live export freeze,
predecessor/command-schema compatibility and actual browser/denied-read acceptance;
it assesses its own size and cannot borrow F's exception. Original k53/k47 closure
stays intact; finite retirement or planning cannot close either. k28 retains every
missing real truth/reaction/defect remedy and complete-default/nonrigid obligation.
An actual real signed-resolution loss still earns immediate policy work before
image-edit dependents. The design reply accepts none of those missing outcomes.

baseline-delivery-k61's concrete plan assigns F to baseline-finite-k63 and B to
baseline-browser-k64, both inside k53 before k54 with an earned planning review
before F. k53's Working increments/ownership map and their complete charters
bind every original criterion. F alone has the explicit same-live-owner/session
continuation exception, with internal unfinished milestones and task-owned jj
retirement/sealing only on full delivery. B consumes F's actual completed core,
verifies that reuse/its own size and owns real browser/server/live export/Stop,
compatibility/native/isolation/six-case acceptance. It receives no cadence waiver.
No milestone/horizontal/acceptance-only child, new tree/workspace, source study
or repeated answered F question follows. k53 closes only on complete F+B, k47
still requires k54 and the full later product/response/default obligations remain.
Original Goal/Done when and all downstream contracts/order are unchanged.

The k47 node is earned by k51's concrete session-size finding, not speculative
infrastructure work. No integration is pre-created. A stage that truly outgrows its
session decomposes lazily at a complete narrower public handoff, keeping the
remaining concrete work before its consumer. It cannot split storage, rendering,
UI or verification into dead horizontal children. A new state is usable in its
reader, any-page/group controls as applicable, resume and export in the same leaf.
An implementation's earned review/integration runs before the next stage; it is
cut only from the actual completed artifact. k44's earned planning review runs
before k47. No in-session review competes with that scheduled review.

### Contract inherited by all four working charters

Read the complete current `docs/specs/rotation-processor.md`, the ADRs cited above,
k41/k45/k46 and k44, and the actual preceding stage's artifact/acceptance rather
than assuming that a retired task passed. The following obligations bind every
cut through its root brief, with feature-specific checks added by the leaf.

- Extend the installed Python/pikepdf command without changing preparation's
  public contract or frozen experiments. Verify the exact pinned Poppler,
  Leptonica, Pillow and pikepdf APIs before relying on them. Add a direct product
  Pillow pin and packaged, version-checked estimator bridge; an experiment
  executable or its fit path is not a runtime dependency. Before serving import
  or resume, dependency failures are named with a locked-setup remedy. Persist
  versions/settings and freeze accepted assets across toolchain changes.
- Keep source/support gates consistent with preparation's static-page domain,
  but independently verify rendering of full MediaBox composition, effective
  rotation/UserUnit, static appearances, images/stencils/masks and vector/text.
  Record original boxes, effective image ppi, pixel/physical dimensions, decoder
  warnings and extent/fidelity concerns. Fixed 300-dpi lossless RGB re-rendering
  replaces source representations. Input-relative source-native detail above
  300 ppi, colour conversion and CropBox-visible extent are separate comparisons;
  an acknowledgement or unchanged baseline is no preservation-test pass.
- Retain every source occurrence/order, blank and duplicate. Assess all pages,
  covers and already-processed scans; hints grant no exemption or source reopen.
  Universal within-page unverified, orientation unverified and page-specific
  triage are distinct. Unflagged is only absence of a recorded trigger. No
  deadband, calibrated confidence, automatic nonzero rotation, free warp, scale
  normalization, appearance cleanup, OCR or reorder/removal UI is commissioned.
- Initial baseline retention means unresolved/uninspected accepted state. Every
  preview/disposition/accepted revision names stable IDs and its displayed
  revision. Accept is durable; discard/revert are inspectable. No bulk rotation
  acceptance. Pending drafts block export (6); retained baseline/unresolved
  assessment reasons do not. A current scoped snapshot acknowledgement, with
  explicit unresolved IDs/reasons and separate inspection scope, permits usable
  unresolved export. Edits invalidate acknowledgement and relevant dependencies.
- One kernel-released project writer lock, transactional checkpoints and
  completely published content-addressed lossless assets own resume. Reject
  stale actions, competing writers (`PROJECT_BUSY`, 4), corrupt/missing assets
  and live frozen-export commits (`EXPORT_IN_PROGRESS`, 6) actionably. Crash
  recovery never accepts a private partial image/export or permanent freeze.
  Closing a tab differs from authenticated Stop review (0); SIGINT/SIGTERM
  return 130/143 with durable state preserved, and Stop waits for export's
  separate outcome. Token, exact Host/Origin and explicit confirmed destination
  checks apply to all state-changing browser actions.
- Export rebuilds from frozen accepted RGB images at recorded physical scale,
  with no old hidden selectable text/resources. Validate decoded image bytes,
  identity, count/order and page transforms before atomic no-clobber publication.
  Report Subject limitation and the exact version-1 UTF-8 JSON attachment from
  the spec; unsupported stage fields are explicit null/empty/unresolved, never
  fabricated acceptance. Omit preparation hints. New import of unmarked,
  metadata-stripped, malformed/unknown-version or externally reordered exports
  always starts fresh with unknown sides and unverified geometry. A project
  is the resume artifact; the report is never one.
- Exercise source/project/output path, case, symlink and hard-link aliases,
  occupied destinations (including dangling links), concurrent occupation,
  actual writer interruption and no-link failures. Observe the installed writer
  PID at private stage/checkpoint/publication barriers, signal/kill and reap it;
  observing a uv/Task launcher is insufficient. Check both sides of link commit,
  cleanup/result-delivery failures, unchanged sources/previous output, no partial
  destination, exact mapped exits/remedies and recoverable project state.
- A full installed-command test prepares labelled/real selections outside the
  collection, then runs process → real browser actions → Stop → review resume →
  export. Also accept an ordinary unmarked already-assembled sole PDF. Run
  processing with collection reads genuinely denied and observe a read-denied
  control from the same boundary; merely changing COLLECTION is no isolation.
  Use a test-owned browser driver for real UI actions and a denied-read boundary
  around the actual processor. If the host cannot demonstrate either, keep that
  verification as concrete unfinished work before the next product consumer.
  Controlled internal faults supplement these public tests; no public fault flags.
- Extend root Taskfile shared locked setup and `process:` run/review/export/check/
  acceptance recipes only as they acquire working implementations. Preserve or
  reconcile existing preparation/geometry wrappers and recipes. Run all new,
  changed and affected recipes, `prepare:check`, `geometry:staff-check`, and
  synthetic preparation acceptance; run affected real preparation comparisons
  too when their subjects change. Finish all edits first, digest every script,
  manifest, lock, fixture, normative input, library/tool and other read subject
  before/after with one writer, then compare reruns per item. Keep derived
  artifacts outside the read-only collection and retain ordinary durable evidence.

### k52 clarifications inherited by every implementation

The first complete public handoff is k53, then k54 introduces edited-image state.
Both share k47's original closure criteria. Baseline retention is accepted state
without human inspection; k53 supports durable unresolved dispositions and export
acknowledgement but no edited-image revision/accept/revert controls. Those enter
with k54's reader/resume/export. Every-page advisory skew assessment and the
estimator bridge stay in k53; deferring them would alter the signed import scope.

k53 owns the explicit installed command-contract acceptance: help/examples/errors/
saved-state/stage limitations without opening an input, human diagnostics on
stderr, versioned --json JSON Lines on process/review, ready only after completed
import/assessment, terminal events distinct from export publication, and one
finite-export result. Record/test the concrete vocabulary/schema for shell loops,
normal authenticated Stop (0), signals (130/143), rejected actions and separate
publication/stop outcomes. k54/k48/k49/k50 extend that vocabulary compatibly and
rerun it; preparation's existing finite result stays compatible.

k53 owns effective-resolution analysis through pinned pikepdf content parsing:
track graphics-state q/Q/cm and image placement through nested form matrices/
resources, inline images, stencils/masks and supported static annotation appearances;
combine placement with effective page rotation/UserUnit and intrinsic sample sizes
for horizontal/vertical physical ppi. Independently constructed CTMs/extents/ppi
and wrong-placement controls verify this analyzer, not its own calculations.
Verify exact pinned parsing/decoding APIs before use. Every contributing placement
must be accounted for or the affected resolution assessment is explicitly
unavailable with an import-fidelity reason; no partial scan grants a <=300-ppi
pass. pdfimages output may aid diagnostics but is no unverified sole oracle.

k53 also owns a product-packaged C helper/Leptonica bridge and direct Pillow pin.
Package its source with the product, independently of experiments; process:setup
builds it into a named product cache with compiler/pkg-config/library identity and
source/build digests. The installed command preflights helper protocol, linked
Leptonica version/status/angle/ratio and known input/sign/sentinel controls before
serving. Record/check supported Poppler/Leptonica versions explicitly: Homebrew
packages are not pinned by uv sync --locked. Missing/incompatible/unbuilt tools
return DEPENDENCY_UNAVAILABLE (5) with the actual setup/install remedy; never
compile silently during import or depend on an experiment executable/fit path.
Verify exact installed ABI/API and renderer/sampler semantics before relying on
the mechanism. Tool changes freeze accepted assets as the spec requires.

Before comparison outputs, k53 declares a source-native comparator independent of
Poppler: decoded contributing image samples/masks/colour metadata and independently
checked physical placements, with analytic known-channel/edge/feature construction
truth for controlled compositions. A second Poppler render is no fidelity oracle.
For <=300-ppi one-bit/grayscale/RGB cases, justify pixel-phase/grid/interpolation
and colour bounds independently before outputs, test aligned and misaligned source
grids, and require erased-fine-feature, wrong-image/placement/colour controls to
fail. Exact unfiltered grid-aligned constructions allow exact comparisons;
nonaligned grids require prejustified feature/coverage bounds, never a tolerance
chosen to fit the baseline. Complex colour/mask/vector/composite regions without
validated independent truth remain unavailable with the specific missing oracle,
not passed by image-object extraction or unchanged export bytes. Synthetic required
mechanisms must pass; real numerical truth may remain unavailable beside separate
actual/pending visual evidence. Assess source-relative detail/colour at every
resolution, even when no >300-ppi reason triggers automatically.

Persist private project format/capability versions distinct from the public report.
k54/k48/k49/k50 own preceding-stage frozen-project resume and interruption tests:
accepted/baseline digests, IDs/order, physical scale, mappings, dispositions and
scoped acknowledgement retain their meanings; newly supported operations are
inactive until explicit use. Transactional additive upgrades preserve the original
recoverable state and never regenerate accepted pixels. Unknown/unsupported private
formats fail INVALID_PROJECT (3) with a named compatible-reader/verified-recovery
or explicit new-import remedy, without modifying that project. Retain a frozen
project per completed handoff as the next stage's fixture. Public version-1 JSON
report meanings and optional unsupported fields remain as agreed, and reimport
never resumes from a report.

### Independent acceptance and retirement ownership

Each stage supplies a current durable acceptance note and ordinary full-page/
native view manifest, tied to source, baseline, accepted and output digests,
settings and exact commands. Keep the distinction between independent numerical
passed/failed/unavailable and human visual accepted/pending/rejected. Actual human
inspection records exact paths and verbatim scoped replies; no reply is pending/
unavailable, never inferred acceptance or a fabricated “Not inspected yet”.

Every stage independently assesses the six fixed cases against its offered
operations and input fidelity: Norwegian20 both gutters (whole-spread detail
until k49); Garbage Collection30 glyph widths/indentation/boxes/arrows;
Counterpoint20 one landscape page/both columns; Fundamentals40 faint prose and
any music; SchoenbergComposition cover1 colour/sparse rules; Algorithm Design20
already-processed preservation. k48 adds its nonidentity fractional companion,
which later stages rerun. Music140 remains an unsupported-layout diagnostic and
music20 the source-acquisition candidate; neither replaces any fixed case.
k50 adds real adjacent pair/group full/native comparisons for book placement.
The estimator/detector or its rerun supplies no real ground truth; real numerical
improvement stays unavailable without an independently validated instrument.

For offered numerical mechanisms use known-by-construction truth with controls
seen to fail first on a deliberately wrong subject. k53 covers import geometry,
native-source fidelity and retained export; k54 adds exact orientation, together
closing k47. k48 adds known upright/tiny/noisy/rigid
angles, curved/local variation and fractional RGB mapping; k49 adds source-region/
split/crop retention; k50 adds independently known side/anchor/offset/canvas and
parity. Aggregate geometry cannot hide regional worsening. Numeric tolerances
need an independent justification stated before outputs, never detector tuning,
historical visual estimates or a confidence ratio treated as probability.

A technical implementation may retire with pending human reactions only when
its complete supported public handoff, independent executable controls, fixed-case
packets and separate dispositions are delivered. Failed safety/preservation or
an unavailable required public/synthetic verification is incomplete implementation
work, requiring precise repair/decomposition before that consumer; do not relabel
it pending visual review. A real unsupported geometry outcome may be usable and
unresolved without falsely passing correction. Verified source-relative losses
remain failed preservation for that fixture, even when visibly flagged. Each
fixed case records fidelity as passed, failed (signed >300-ppi resolution
limitation), failed (defect), or unavailable (named missing independent truth),
independently of its human visual disposition. Only the signed resolution ceiling
may supply that limitation classification; colour-conversion, decoder, incorrect
placement or <=300-ppi erased-feature defects block technical retirement and
require repair before the next consumer. A real fixed-case signed resolution
failure requires a precise human policy question immediately before image-edit
dependents: the discovering slice inserts a requirements leaf before its next
live dependent (k54 after k53; k48 after k54), not merely a note for k28. Recommend
retaining the signed 300-dpi representation for this inspectable intermediate
only with explicit limitation, failed fixture preservation and full-default remedy
still live; offer evidence of whether a representation change is required instead.
Any agreed change earns its own design/review/planning chain before k48 and
remaining affected dependents. Pending/unanswered policy cannot be consumed as
authorization. Synthetic intentional >300-ppi loss alone tests the signed limit
and commissions no speculative policy leaf. No actual fixed-case loss is inferred
by this plan. k28 consumes the actual policy outcome and owns remaining
preservation/real-truth/visual/default work; an export acknowledgement never waives it.

The next stage consumes prior missing reactions/defects and adds its own; k28 is
the live owner of ALL missing intermediate import/rigid/split/book/preservation
reactions or defect-specific repairs, plus full representative/nonrigid acceptance
before k22/k23. Pending replies do not veto separately admissible numerical
evidence under k39's “yes”, and numeric success does not accept the product.
No response-only or test-only stage is pre-grown. Any justified evidence/response
completion gets its own fresh planner on every outcome; an identical unanswered
response is not an automatic relaunch loop. Implementations judge their actual
artifacts for earned review before the next live consumer.

k27 retains its exact source-only music protocol and separately owns the existing
historical geometry/preparation questions; its body/gates remain unchanged.
k28 consumes k44 and all actual working/review successors, then owns full
within-page evidence/design extension/completion and accepted book geometry
before appearance. k31's conditional per-half unchanged/rigid/vertical/default-
validity/field/application/fallback-copy, independent source/output marks,
held-out/systematic uncertainty, control/nonidentity-sampler/detail and separate
actual reactions remain unperformed. Both fixed-grid addressing attempts failed
before marks or masked extraction; this rejects neither all instruments nor the
vertical family. No automatic dense music marking, forced fit, addressing retry,
holdout/gate rescue, tuning or new Norwegian study is authorized. Both Norwegian
source replies remain unavailable, real-anchor/output reactions unperformed and
historical geometry/preparation separately “Not inspected yet”. k28 must retain
each named gap before k22; k23 still verifies the complete root after appearance.
