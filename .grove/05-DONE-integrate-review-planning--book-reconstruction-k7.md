# book-reconstruction-k7

**Integrates:** book-reconstruction-k6

## Goal

Triage the findings of the planning review `book-reconstruction-k6` and apply the real ones
to the planned subtree before `page-geometry-k4` consumes it. Verify each finding against the
artifacts rather than agreeing with it, and classify it as a contract stated unclearly, a real
issue, a visible trade-off or noise.

## Context

- Read the findings from the review's own commit and its `## Findings` section, not from this
  body. The reviewed producer is `book-reconstruction-k3`, which has two commits: `c9959370a702`
  here and `1ada47bd20fe` in `/Users/antony/Development/BookScanBuilder.prepare-pdf`.
- This session runs in the main workspace. The user subsequently authorized
  consolidating preparation into this tree; the running log records that change
  and the source-to-local handle mapping. Preserve the preparation history.
- A finding that is real but demands the plan be rethought becomes a new producer review chain
  beside the leaf, not an in-session redesign.

## Done when

- Every finding in `book-reconstruction-k6` has a recorded classification in this leaf's
  running log, with the evidence that decided it.
- The changes the real findings call for are made in the consolidated tree, without
  choosing a correction algorithm, interface technology or landing mechanism the evidence
  does not yet support, and without launching drivers.
- `page-geometry-k4` and `corrected-book-k5` remain consistent with the root brief after the
  changes, and no live leaf that consumes this plan is left depending on an unresolved finding.

## Notes

Keep the preparation/processor boundary: one prepared PDF in, no collection-folder discovery.
This leaf reshapes the plan; it does not run the experiment or implement preparation.

## Decisions (running log)

The review is read from `4dbf2ff2`, whose `## Findings` contains eight findings.
Main-tree evidence is the current briefs/tasks, `plan-k1`'s confirmed assembly
and split requirements, and the experiment in `docs/research/scan-geometry-a.md`.
The graph generation `2026-10-11T02:56:03Z` records no coverage issue for those
paths; the markdown was read directly. Preparation is not a listed graph
project, so its brief and both live tasks were read directly. Its working copy
was empty at `35ace6fb`, above producer commit `1ada47bd`.

Finding 7 is a real issue: `references/commit.md` gives one task one focused
commit, and no Grove procedure inspected supplies a cross-workspace corrective
commit route. Before any preparation edit, the user approved creating a
dedicated `integrate-review-planning` correction leaf before preparation's
`prepared-pdf-k4`, sealed in its own jj commit. That later session owns the
preparation-side repairs; this session owns the corrective handoff and main
repairs, and launches no drivers. The cross-tree reference must name the main
workspace and review revision as well as the handle, since keys are local.

Finding 1 is a real issue, with an over-specific proposed remedy: both briefs
promise landing via jj, but neither owns the landing, its source revision,
product-path boundary or processor base. Full-commit integration would include
the different `.grove/` histories; that does not make a path-scoped restore the
only possible solution. A new bounded design leaf before `corrected-book-k5`
will establish the landing contract and commission its review; the receiving
root will retain an explicit execution/verification leaf before the processor
is based on landed preparation. The prep correction must make its producer's
delivery obligations agree. No landing command is selected by this triage.

Finding 2 is a real issue: both `page-geometry-k4` and preparation's
`prepared-pdf-k5` create the same root Taskfile, with no composition or combined
verification owner. The handoff design must choose a composition rule, preserve
each concrete recipe/dependency, and make the receiving landing verify all
combined tasks. The prototype will use `geometry:` task names and declare the
fate of every wrapper its surviving tasks call; discarded wrappers must have
their tasks removed or replaced and verified. Prep's correction owns its
matching task naming and delivery instructions. No speculative Taskfile is
created here.

Finding 3 is a contract stated unclearly: the research and prototype require
independent held-out lines, but the automatic analysis sees the whole page.
Human annotations alone do not withhold a physical line from that fit. Repair
the prototype to freeze source-coordinate guides before derived outputs,
exclude whole evaluation lines from disposable analysis input, save the mask
and inspect detected fit lines for overlap. If exclusion prevents a valid
model, report the held-out experiment as inconclusive and retain any full-input
fit only as a clearly labelled diagnostic; do not lower validity requirements
or call it held-out success.

Finding 4 is a real issue: a straight control's invalid or identity field
cannot establish sampler fidelity. Require a separate declared smooth vertical
diagnostic field with non-zero, spatially varying displacement and fractional
source coordinates at detail crops. The prototype chooses and records bounded
parameters before seeing results, exposes actual displacement and checks them
against the intended mapping. This deliberately warped control tests sampling,
not a geometry acceptance policy; distinguish intended deformation from
sampling damage. It selects no production correction field.

Finding 5 is a contract stated unclearly: the prototype conflates rejection
and inconclusive evidence and the consumer supplies no inconclusive branch.
An observed failure of the candidate's automatic model, geometry or fidelity
rejects that candidate for the fixture; missing independent evidence or an
ambiguous/unavailable user reaction is inconclusive. The latter must identify
what observation is missing, commission only its bounded completion (or ask
the user the specific unresolved comparison), and retain a fresh planning
consumer. Neither outcome permits unearned expansion or production commitment.

Finding 6 is a real issue: `plan-k1` promises user-controlled assembly and one
book page per output page. Preparation preserves unsplit PDF pages, so only
the processor can control newly created halves. Make processor design own
post-split book-page exclusion/reordering before final OCR/export; require a
half-blank and half-duplicate/order fixture. Prep's correction must state its
PDF-page-level scope and this successor ownership. Keep the one-PDF boundary.

Finding 8 is a contract stated unclearly: preparation's brief says its design
tests through a public command, while `prepared-pdf-k4` permits only design
and a bounded dependency experiment and `prepared-pdf-k5` commissions the
working command. The prep correction must make the brief say the design
specifies the public test seam and may validate copying assumptions; the
implementation exercises the actual command. Do not build that command here.

The authorized preparation insertion was attempted before any preparation
edit. `grove-llm leaf-insert prepared-pdf-k4 prepared-pdf --kind
integrate-review-planning`, run with preparation as cwd, refused: "wrong working
tree ... session belongs to /Users/antony/Development/BookScanBuilder". No prep
file changed. Do not remove launch controls or hand-edit around that guard.
At that point the user-approved route needed a separate preparation-workspace
session to create and seal the handoff. This leaf was kept live pending that
handoff; the user's later consolidation decision below removes that condition.

At that stage main repairs were applied to the root brief, `page-geometry-k4`
and `corrected-book-k5`. New `stage-handoff-k8` sat after the prototype and before
the processor planning consumer; it owns the precisely known landing and
Taskfile-composition questions and requires a design review ahead of that
consumer. This externalised mechanism selection rather than redesigning it
in triage; main work did not assume completion of the prep corrections.

The user then asked why a separate workspace was needed and said "proceed"
with the recommendation to keep preparation, geometry and processor tasks in
one workspace. This supersedes the approved cross-workspace corrective handoff
and its unresolved guard. Import the two unstarted preparation task contracts
with new local keys, preserving their historical source at `1ada47bd` instead
of merging colliding task histories. Repair preparation's scoped requirements
in the receiving brief and local leaves before they run. The user-authorized
consolidation rejects the separate-workspace landing design, so prune
`stage-handoff-k8`; its historical body remains readable. One shared Taskfile
will be extended and its combined recipes verified in place. Preparation
design/planning precede geometry; their implementation cuts must be inserted
before the geometry/processor consumers. Processor and optional-appearance
work will also stay in this root. Forget the clean preparation jj workspace
registration after preserving its producer with a local archive bookmark;
leave its on-disk copy untouched. No driver is launched.

The migration is made: preparation's design is local `prepared-pdf-k9`, its
planning is `prepared-pdf-k10`, and both precede `page-geometry-k4`. Their
original contracts were copied from the clean preparation checkout and then
repaired locally: design specifies tests rather than building a command,
preparation controls unsplit PDF pages, and its planning inserts implementation
and review ahead of consumers. The root now holds every preparation fixture
and failure/preservation requirement from the old scoped brief. This repairs
findings 6 and 8 in the contracts that will actually execute.

Findings 1 and 7 are resolved by the user-selected single-workspace route:
local product commits and the existing root verification own stage integration,
with no cross-tree correction, branch landing or processor base selection.
Finding 2 is repaired by one shared Taskfile, distinct concrete recipe names
and verification of additions plus affected existing recipes, stated in both
preparation tasks, the prototype, the processor planner and the root. The
experiment-wrapper disposition remains explicit. No production technology or
correction algorithm was chosen by consolidation.

`archive/prepared-pdf-plan` preserves producer revision `1ada47bd` in the jj
repository. The clean `prepare-pdf` workspace registration was forgotten;
its files remain on disk as historical context. The user-authorized
`stage-handoff-k8` prune preserves the abandoned plan's body. No prep-side tree
verb, teardown or driver was run. All live continuation now belongs to this
workspace and the root retains the full preparation, geometry, spread,
post-split assembly, review/OCR, optional-appearance and final-export scope.
