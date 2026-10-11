# prepared-pdf-k14

**Reviews:** prepared-pdf-k10
**Creator:** run f9140e6a-5fb4-4ed7-beeb-46ecd50735ff

## Goal

Adversarially review the preparation implementation handoff created by
`prepared-pdf-k10`. Establish whether its task tree can deliver the smallest
complete working preparation increment without losing reviewed preservation,
publication or acceptance obligations.

## Context

Find the producer's committed diff by its stable handle. Its artifact is the
implementation leaf `prepared-pdf-k13` and the updated root brief; reconcile
them with the current tree rather than relying on positional paths.

Read `docs/specs/prepared-pdf.md` and `docs/adr/prepared-page-hints.md` as the
integrated design. `prepared-pdf-k12` repaired the design and records the user's
confirmation of single-quoted exclusions and ascending/descending ranges.
`docs/research/prepared-pdf-copy.md` and its bounded experiment explain what
dependency evidence exists and what command acceptance still needs to prove.
`Taskfile.yml` already owns experiment/diagram recipes.

## Done when

- Inspect the producer's actual diff and record actionable findings with
  specific evidence and impact, or explicitly record no actionable findings.
  This is inspection only; do not implement the command or rewrite its plan.
- Challenge increment boundaries and one-session feasibility: do selection,
  copying, gates, validation and publication truly need one complete command
  handoff, and are any smaller green independently useful stages possible under
  the agreed design? A horizontal adapter/setup/test-only cut is not a useful
  product handoff. If the session scope is impractical, state the concrete seam
  and green behaviour that would justify a different cut, rather than merely
  counting requirements or relaxing the approved public contract.
- Check traceability from every spec section/root preparation acceptance case
  into the implementation obligation and public verification seam. Focus on
  inherited/default seven-value geometry, nested streams/decoder globals,
  annotations/repetition/ownership, effective version/extensions and independent
  advisory markers; the old bounded fingerprint cannot prove runtime integrity.
- Challenge error/dry-run/publication coverage: first-error phases, identical
  source gates/raw warnings in both modes, source stability and output aliases,
  no-clobber races, commit-region signals, pre/post-commit cleanup/reporting and
  abrupt-kill outcomes. Verify fault checks can observe the promised state at
  bounded private seams while ordinary acceptance exercises the installed CLI.
- Check real-source order/roles, exact renders, canvas/raw-resource evidence,
  unchanged digests and measurement provenance. Distinguish automated checks
  from human visual approval. Confirm Taskfile integration remains reusable and
  collection-independent synthetic checks do not import runtime dependencies
  from geometry, OCR, diagrams or acceptance tools.
- Verify the order keeps this review and any required integration before
  `prepared-pdf-k13`, and preparation/product review before `page-geometry-k4`.
  The root must retain processor-isolated end-to-end verification and the
  optional-cleanup successor; preparation alone cannot finish this workstream.
- If findings warrant action, cut `integrate-review-planning` as the next live
  sibling before implementation. Its body carries this review's stable handle
  under `**Integrates:**`, not a transcribed finding checklist. If no findings
  warrant action, cut no integration and retire normally.

## Notes

The review concerns this planning artifact, not a fresh choice of preparation
syntax, library, hint container or geometry algorithm. Re-derive whether the
plan carries the integrated contract; do not treat the producer's claim of
completeness as evidence. No in-session reviewer is commissioned by this leaf.

## Findings

I inspected the producer commit `30f2fdd7` (`prepared-pdf-k10`): the new
the implementation leaf `prepared-pdf-k13` (cited below by its section headings, as
the file has no stable line anchors), the root-brief diff and the producer's
running log. I read them against `docs/specs/prepared-pdf.md` (`spec:N` is that
file's line N), the `prepared-pdf-k11` findings and `prepared-pdf-k12` decisions,
`docs/research/prepared-pdf-copy.md`, the root `Taskfile.yml` and the two sibling
leaves that consume preparation (`page-geometry-k4`, `corrected-book-k5`). I ran no
test, build, lint or format command and edited nothing outside this file. Two
tooling claims were checked against published documentation and are marked as
such. Findings are ranked most severe first.

### Traced and sound (no finding)

- **Traceability of the spec's dense obligations is complete by reference.** The
  preservation contract, gate tables, runtime-validation section, publication and
  commit-region rules and error phases are cited by the leaf as normative ("its
  full acceptance tables apply"), and its Done-when restates the hard ones
  concretely. I checked specifically: inherited/default seven-value geometry
  ("Apply exactly the inherited/default geometry"; "Separately verify all seven
  geometry values"), nested streams and `/JBIG2Globals` (raw traversal plus
  "Mutate nested bytes/DecodeParms/JBIG2Globals"), annotation ownership and
  repetition (repeated annotated page rejection; "annotation ownership" in
  runtime validation), numeric effective version/extensions with the tuple
  `min_version` ("Algorithm Design keeps 1.7/3"), and fresh independent markers
  per occurrence. The old bounded fingerprint is expressly demoted ("Their
  fingerprint is not the specified runtime projected-page comparator").
- **Every root preparation acceptance case and every spec fixture row appears in
  the leaf's table or Done-when**, including labelled K1–K4/C1–C2 order, the
  `6-4,1,4,!5` / `!2,!5-6` cases, the already-assembled sole-content case, the
  Algorithms-on-Strings explicit front/back and the repeated-annotated-page
  rejection in both modes.
- **Order and root retention are right.** On disk the order is
  `prepared-pdf-k14` → `prepared-pdf-k13` → `page-geometry-k4` →
  `corrected-book-k5` (positions at review time), so this
  review and any integration precede implementation, and implementation precedes
  geometry. `k13` assesses a `review-impl` before `page-geometry-k4` and states that
  preparation does not close the root; `page-geometry-k4` and `corrected-book-k5`
  remain live and `k5` still carries processor-isolated end-to-end acceptance and
  the optional-cleanup successor question, so retiring `k13` cannot close the
  workstream.
- **The Taskfile plan is coherent**: extend the existing file in place, retain the
  `prepare:copy-experiment` wrapper while a recipe calls it, run all new/changed
  and affected recipes, keep geometry/process recipes under distinct names.
  Nothing in `k13` requires D2, the diagram recipes or any geometry/OCR import.

### 1. One session is unlikely to fit `k13`, and the plan names no fallback seam

**Contract.** `k13` is the whole increment: parser and grammar, selection, the
complete static-PDF gate set with raw traversal, the recursive projected-page
comparator, version/extension handling, staged no-clobber publication with a
blocked commit region, a private fault-injection host, packaging, Taskfile
recipes, durable docs, and a real-fixture acceptance runner with 300-dpi renders,
all landing together. The brief reinforces this ("land together"; "No
adapter-only or test-only handoff earns its own leaf") and `k13`'s Notes say to
bring everything "to one complete green command in this same slice".

**Defect.** The producer's reason for one leaf (`k10` running log: "Parsing or
copying alone leaves no usable command") is right about *those* two cuts, but it
does not establish that no smaller green vertical cut exists, and the plan gives
an implementing session no sanctioned move if the whole does not fit. The
dependencies inside the leaf are not uniform, which is what makes a seam real:

- Phases 1–5 (grammar, source open/hash, document and page gates, raw traversal,
  bounds/exclusions, destination preconditions, stability recheck, JSON/human
  result, help, exit codes) need **no** staged file, `save()`, output reopen,
  signal masking or fault host. They are fully specified (`spec:142–174`) and are
  a complete public behaviour of their own: `--dry-run` resolves every real
  fixture and reports order and roles, or the first error.
- The write path (`spec:312–405`: stage → save → validate → recheck → commit, the
  commit-region signal rules, post-commit warnings, the comparator) adds a
  disjoint set of risk — irreversible filesystem state and signals — that needs a
  private subprocess host that does not yet exist, plus fixtures that are hard to
  build (a PDF that opens cleanly but warns only on raw stream read, a
  recovery-requiring file, an appearance-state annotation, a nested
  Form→Image with globals). The leaf does not say how those fixtures are
  produced; the experiment script only generates the labelled K1–K4/C1–C2
  documents.

An implementer that discovers mid-session that it will not fit meets a three-way
conflict: run long (the grove trap), cut a horizontal test/adapter sibling
(forbidden by the brief), or take a vertical cut the brief's wording suggests is
not allowed.

**Consequence.** An overrun lands as an unreviewable half-finished command or a
silently weakened gate ("Do not weaken reviewed gates to make the bounded sample
pass" is in the Notes for exactly this reason), because the only sanctioned
outcome is all-or-nothing.

**Smallest correction.** Do not pre-cut a speculative subtree; declare the one
real seam so the leaf can use `leaf-decompose` without violating the brief. The
seam and its green behaviour:

- **Child 1 — complete dry-run command.** Packaging and `uv run --locked bookscan
  prepare`; every grammar/arity/JSON/help/exit-code behaviour; phases 1–5
  including all source gates, raw traversal, source stability and
  destination/alias preconditions; `prepare:setup`, `prepare:run`,
  `prepare:check` for this behaviour; real-fixture order/role/`planned` results
  for every root acceptance case. Green and useful on its own: it is the spec's
  stated shell-loop use (validate a collection before writing) and it creates no
  file.
- **Child 2 — write path.** Copy/save, runtime comparator, markers, staged
  publication, commit region, fault host, `prepare:acceptance` renders and
  digests, docs, the `review-impl` assessment.

The other tempting cut — synthetic checks and command first, real-fixture
acceptance second — is **not** a valid seam: it is the test-only horizontal cut
the brief rejects, since the second half delivers no behaviour.

An integration that accepts this should amend the brief's "land together"
sentence to permit exactly this fallback and say what child 1 hands child 2 (the
shared source-projection module). It may equally decide that `k13` fits and
record why; what it should not leave is a leaf whose only sanctioned overrun
outcome is a broken product.

### 2. OS-signal and kill checks are specified against the `uv run` launcher, not the process that holds the state

**Contract.** `k13` requires public subprocess checks to invoke `uv run --locked
bookscan prepare`; its verification section says to "Use real public subprocesses
for parsing, copying, collisions and OS signals", to deliver SIGINT/SIGTERM
"before publication", and to "Kill during writing and after link before unlink:
the destination is absent or complete".

**Defect.**

- **(a) The signalled pid is ambiguous.** `uv run` is a launcher that spawns the
  Python process. uv's own signal policy is version- and TTY-dependent: it mostly
  relies on the terminal's process group for SIGINT, forwards SIGINT itself only
  in some non-interactive cases, and handles SIGTERM separately (uv
  `crates/uv/src/child.rs` comments and PR #11009, found by search and not
  re-read at source for the pinned uv version). A test that signals the launcher's
  pid may exercise uv rather than the command's handler, so the expected
  `INTERRUPTED`/130 or 143 may or may not occur.
- **(b) A SIGKILL to the launcher need not stop the writer.** The child can
  survive as an orphan, finish the write and publish. "Kill during writing: the
  destination is absent or complete" then passes vacuously, and "kill after link
  before unlink" may never observe the two-names state the spec permits.
- **(c) The commit-region cases cannot be public-subprocess cases at all.** A
  signal cannot be placed *inside* the blocked region or in the window after
  `link()` from outside the process. `spec:343–348` and the spec's test seam
  (`spec:490–499`) require those outcomes (exit 0, `written`, complete
  destination) and split the mechanism between "private subprocess host" and
  "public subprocess" in a way the leaf repeats rather than resolves.

**Consequence.** The leaf's most safety-critical acceptance (no partial
destination, correct exit on commit-region signals) can pass without observing the
promised state, which is the measurement-provenance failure the leaf elsewhere
guards against.

**Smallest correction.** State the signalled pid: exec the locked environment's
console script (or have the command report its own pid on a private channel) so
signals and kills reach the Python process; keep `uv run --locked` for ordinary
public invocations. State that the pending-cancellation, blocked-region and
post-link cases are driven by the private host at fixed hooks (the host signals
itself at the hook), and that kill-after-link observes both names present and a
complete destination. Assert that no writer process remains after a kill case.

### 3. `--help` content and dry-run side effects have no verifying obligation

**Contract.** `spec:62` and `spec:88–90` require `--help` to explain role
grouping, page grammar, failure/retry behaviour and examples and to carry the
single-quote rule for `!`. `spec:173–174` requires help to state dry-run's cost
and that `planned` reserves nothing. `spec:60` and `spec:168–173` require dry-run
to write no PDF **or temporary file**.

**Defect.** `k13` verifies "help precedence" only (standalone `--help` wins and
opens no inputs); the help content is in neither its Done-when nor its checks, and
the docs bullet covers durable setup/usage documentation, a different file.
Likewise "creates no PDF or temporary file" is stated as implementation, but no
check lists the destination directory before and after a dry-run, and no case
shows the limit the spec asks help to explain (a dry-run returning `planned`
followed by a write failing `WRITE_FAILED`/`PUBLISH_FAILED` against the same
sources, e.g. a read-only destination directory).

**Consequence.** Help is the only place the history-expansion hazard is
discoverable at the shell, and its absence would fail no listed check. A dry-run
that created and removed a private temporary file would pass.

**Smallest correction.** Add synthetic checks: help contains the three required
statements (substring level, not a snapshot); an exact destination-directory
listing before and after every dry-run case; one planned-then-write-failure case.

### 4. Argument forwarding through `prepare:run` is unverified for the spaced, `!`-bearing paths every real fixture uses

**Contract.** `k13` makes `prepare:run` forward "arguments to the installed
command"; the spec keeps direct shell invocation as the public seam. Every real
fixture path contains spaces (`Book Conversion`, `Fundamentals of Musical
Composition.pdf`) and the exclusion grammar needs single-quoted `!`.

**Defect.** Task exposes forwarded arguments as `.CLI_ARGS`, one string inserted
into the command text, and separately as `.CLI_ARGS_LIST`, a parsed list (Task
templating reference, taskfile.dev/reference/templating; I did not confirm quoting
behaviour by running it). Which one the recipe uses decides whether a quoted path
survives, and nothing in `k13` requires a check that a spaced path and `'all,!3'`
arrive intact through the recipe; the existing recipes interpolate only fixed
single-quoted variables.

**Consequence.** The recipe is the documented reusable entry point, so a quoting
bug would be rediscovered by the first user with a real path, as a silently wrong
argument rather than an error.

**Smallest correction.** Require one synthetic check running `task prepare:run --
--content '<path with spaces>.pdf' 'all,!3' … --dry-run --json` and comparing the
resolved `source` and page list with the direct invocation; use the list form (or
document the recipe as a convenience only) accordingly.

### 5. The synthetic/acceptance boundary for Poppler renders and for the experiment's helpers is unstated

**Contract.** The leaf requires matched 300-dpi Poppler comparisons for "every
real/synthetic page" and independent synthetic nested-Form and annotation render
fixtures; `spec:519–522` gives `prepare:check` only "formatting, lint/type checks
and synthetic public-command order/role/failure tests" and attaches the Poppler
availability check to setup "for acceptance". `k13`'s Context offers the
experiment's "reusable labelled-fixture/render mechanics".

**Defect.** The plan does not say which recipe runs synthetic renders. If
`prepare:check`, that recipe acquires a Poppler dependency the spec does not give
it; if only `prepare:acceptance`, synthetic visible fixtures need the
collection-rooted recipe, contradicting "Synthetic checks need no collection".
Separately, importing helpers from `experiments/prepared_pdf_copy.py` couples the
product's tests to a script whose retained report pins its digest; refactoring it
to extract fixtures invalidates that evidence, and the Taskfile digest recorded
there changes anyway once recipes are added (a documentation matter, not a defect
in the experiment).

**Consequence.** Low: an ambiguity an implementer will resolve one way or the
other, but the boundary this review was asked to check — collection-independent
checks that import no geometry/OCR/diagram/acceptance tooling — is exactly what a
wrong resolution breaks.

**Smallest correction.** State that `prepare:check` is collection-independent and
renders synthetic fixtures only if Poppler is a declared prerequisite of that
recipe (or move those renders to acceptance with a collection-free mode), and that
fixtures are generated by test-owned code rather than imported from
`experiments/`, which stays frozen with its report.

### 6. Human visual approval has no owner after `k13`

**Contract.** `k13` requires before/after paths at useful zoom, to "distinguish
automated equality from user visual approval", and permits recording "any
still-pending human visual acceptance". `spec:451–453` keeps human acceptance
explicit.

**Defect.** `k13` is AFK and may retire with approval pending. The next live
leaves are an assessed `review-impl` (a code review, not an appearance check) and
`page-geometry-k4`, which obtains a user reaction to *geometry*. Nothing names who
shows the preparation comparison to the user or where the answer is recorded, so
"pending" has no discharge.

**Consequence.** Preparation can be treated as accepted by the root's end-to-end
check without the visual judgment the agreed test seam requires.

**Smallest correction.** Name the owner: either `k13` stops and asks the user at
its end with the comparison paths (any session may), or the brief assigns the
preparation comparison to the same user session as `page-geometry-k4` and
`corrected-book-k5` checks that it was recorded.

### Nothing else found

The error/phase table, dry-run/write parity, source gates, version/extension rule,
no-clobber publication rules and root-brief ordering are carried faithfully; I
found no place where `k13` weakens or contradicts the integrated spec. The
`review-impl` decision, the optional-cleanup successor and the processor's
end-to-end check are correctly left lazy rather than pre-cut.

## Decisions (running log)

Findings 1 and 2 decide whether `prepared-pdf-k13` can be implemented honestly
in one session and whether its safety-critical acceptance can observe what it
claims, so the findings earn an integration. It is inserted at the slot of
`prepared-pdf-k13` (the first live sibling after this review) as an
`integrate-review-planning` leaf whose body names this review's handle rather
than its findings. No in-session reviewer was spent.
