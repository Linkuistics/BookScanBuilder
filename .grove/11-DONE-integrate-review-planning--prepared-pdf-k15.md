# prepared-pdf-k15

**Integrates:** prepared-pdf-k14

## Goal

Triage the findings of the planning review `prepared-pdf-k14` and apply the real
ones to the preparation implementation handoff before `prepared-pdf-k13` runs.
Check each finding against the artifacts rather than agreeing with it, and
classify it as a contract stated unclearly, a real issue, a visible trade-off or
noise raised for want of context.

## Context

- Read the findings from the review's own commit and its `## Findings` section,
  not from this body. The reviewed producer is `prepared-pdf-k10`; its artifact is
  the implementation leaf `prepared-pdf-k13` and the preparation increment's
  paragraphs in the root `_BRIEF.md`. Reconcile both with the current tree by
  handle, not position.
- `docs/specs/prepared-pdf.md` and `docs/adr/prepared-page-hints.md` are the
  integrated design and are not reopened here. `prepared-pdf-k12` already repaired
  that design; a finding that would change the public command, an error code or a
  preservation gate is a design question for a new design chain, not a repair in
  this leaf.
- The review checked two tooling claims (uv launcher signal forwarding, Task
  argument forwarding) from published documentation only. Confirm against the
  versions this repository pins or installs before the plan relies on either.
- Preparation's end-to-end consumers are `page-geometry-k4` and
  `corrected-book-k5`; keep their order and obligations intact.

## Done when

- Every finding in `prepared-pdf-k14` has a recorded classification in this leaf's
  running log, with the evidence that decided it.
- The real findings are applied to `prepared-pdf-k13` and, where the plan's
  sequencing or ownership changes, to the root brief. Where a finding changes what
  a later leaf must do, the obligation is written into that leaf's task file; no
  new future review or implementation chain is pre-created.
- The decomposition question the review raised about one-session feasibility is
  settled explicitly: either `prepared-pdf-k13` carries a declared fallback seam
  that keeps every handoff green and independently useful, or the log records why
  it fits. A horizontal adapter, setup or test-only cut is not an acceptable
  answer.
- `prepared-pdf-k13` can be implemented without its session inventing a
  verification boundary, a signalled process, a recipe-to-collection dependency or
  an owner for human visual acceptance.

## Notes

This session reshapes the plan only. It does not implement the command or edit
the spec, ADR, experiment or Taskfile. A finding that is real but requires the
preparation design to be rethought becomes a new design review chain beside this
leaf rather than an in-session redesign. Keep `prepared-pdf-k13` before
`page-geometry-k4`, and keep the root's processor-isolated end-to-end check and
optional-cleanup successor live. No driver is launched here.

## Decisions (running log)

Read `prepared-pdf-k14`'s findings from review commit `dff8975ec90f`, then
checked the current implementation leaf, brief, consumers and integrated design.
The graph project is `Users-antony-Development-BookScanBuilder`; Tier 2 coverage
generation `2026-10-11T04:15:54Z` reports no recorded issue and matching metadata
for the eleven evidence paths. These are markdown/configuration artifacts, read
directly; coverage is best-effort rather than evidence of code completeness.

**Finding 1 — real issue, repaired with a declared fallback.** The existing
all-at-once handoff has no escape from a session that cannot finish its gates,
recursive comparator and publication/fault machinery. Spec phases 1–5 plus
stability recheck are a complete useful planner without staging or output
validation. Permit that vertical seam without cutting children speculatively.
If needed, `prepared-pdf-k13` decomposes into a complete dry-run preview and then
the complete writing command, both with their own verification and documentation.
The first hands over the shared parser/reporting, source gates and immutable
source projection; the second adds copying/comparison/publication and complete
render acceptance. The review's suggested early installation of `bookscan
prepare` needs qualification: its normal write invocation already has a fixed
contract, with no “not implemented” code. Use a temporary explicitly dry-run
preview runner/`prepare:plan` recipe instead; install the public console command
and `prepare:run` only with working writes. The preview is independently useful
for real-source planning, but is neither complete preparation nor a PDF handoff.
Keep both children before geometry and keep the node's full Done when intact.

**Finding 2 — real issue; the review's universal launcher-failure implication
is narrowed by observation.** The inspected Taskfile and plan pin Python/pikepdf
but no uv or Task executable version; installed versions are uv 0.13.0
(Homebrew 2026-10-09) and Task 3.54.0.
A bounded non-TTY probe launched `uv run --no-project --offline
/usr/bin/python3` in an isolated process group with a child readiness/PID
channel. Signalling the launcher with SIGINT or SIGTERM reached the child
handler in this configuration. SIGKILL killed the launcher while the child
remained alive; the probe then killed that child and reaped its launcher.
Thus the kill target is demonstrably wrong, and catchable forwarding here does
not establish TTY or future-version behaviour. The
[uv signal documentation](https://docs.astral.sh/uv/concepts/projects/run/#signal-handling)
describes a retained launcher and conditional forwarding; fetching the exact
0.13.0 `child.rs` path failed, so no source-level claim about that version is
made. Ordinary acceptance keeps `uv run --locked`; signal/kill acceptance
directly launches the synced environment's console script and records its PID.
Private host hooks coordinate exact writing/commit/cleanup windows. Require
observed barriers, state assertions, process exit and no surviving writer.

**Finding 3 — contract stated unclearly, verification repaired.** The spec
requires help content and zero dry-run writes; the implementation leaf states
the behaviours but checks only help precedence. Add targeted help-content
assertions, directory snapshots for public dry-runs, and a private-host trap
that rejects any staging/temporary-file creation (snapshots alone cannot detect
create-then-delete). A stable-source dry-run followed by an injected staged-file
creation failure proves `planned` does not promise writable storage. The first
fallback child owns the no-write/help checks; the writing child owns the
planned-then-write-failure case.

**Finding 4 — contract stated unclearly; a broken template is not reproduced.**
The current root Taskfile has no `prepare:run` yet. On installed Task 3.54.0,
a scratch Taskfile using `.CLI_ARGS` and another using individually shell-quoted
`.CLI_ARGS_LIST` each delivered exactly seven arguments: `--content`,
`/tmp/Book Conversion/Spaced input.pdf`, `all,!3`, `--output`,
`/tmp/Prepared Book.pdf`, `--dry-run`, `--json`. This confirms both forms for
the reported case, not arbitrary inputs or a recipe not yet written. The
[versioned Task reference](https://taskfile.dev/docs/reference/templating#cli)
documents the string/list forms and `shellQuote`. Require the actual recipe's
resolved JSON source/page/role result to equal direct invocation, using generated
spaced-path fixtures and exclusions. Do not mandate an unnecessary template
replacement; list interpolation, if chosen, must quote each element. Record
actual tool versions and repeat this check after recipe/tool changes.

**Finding 5 — contract stated unclearly, boundary repaired.** The spec assigns
Poppler to acceptance, while the leaf says every synthetic page is rendered
without assigning those renders a recipe. Keep `prepare:check` collection- and
Poppler-independent; run synthetic renders in a collection-free mode of
`prepare:acceptance`, and real renders in its explicit-collection mode. Both
retain per-item render/geometry/resource assertions and frozen inputs.
Test-owned fixture builders live outside `experiments/`; the historical probe
and report stay unchanged and are not imported by product checks. Its recorded
Taskfile digest describes that historical run, not the later extended recipe.
No rerun of the probe is necessary merely to add unrelated recipes.

**Finding 6 — real issue, consumer ownership repaired.** Preparation's AFK
implementation can provide automated equality and comparison paths while the
user's visual response is still pending. `page-geometry-k4`, already a human
comparison session, presents the working command's preparation comparisons
separately from geometry and records acceptance, rejection or an inconclusive
response in its log and preparation's durable acceptance note.
`corrected-book-k5` checks that response, commissions a precise repair or missing
comparison before processor acceptance when necessary, and carries the obligation
into any successor planning consumer. Neither code review nor pixel equality
substitutes for the user's judgment. The root's isolated end-to-end check and
optional-cleanup successor remain live.
