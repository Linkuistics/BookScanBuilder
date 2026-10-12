# rotation-processor-k52

**Integrates:** rotation-processor-k51

## Goal

Triage rotation-processor-k51's findings against the committed plan from
rotation-processor-k44 and apply the real ones to the planned subtree before its
first implementation (page-review-k47) runs. Reshape tree and charters only; this
session changes no product, spec, ADR, experiment or evidence.

## Context

- Read the findings from rotation-processor-k51's own committed review leaf and
  commit, then re-derive each against the tree as it now stands. The review cites
  line numbers at commit `d3eaea10`; filenames there carry positions that this
  integration's insert shifted, so resolve every task by its stable handle.
- The producer is rotation-processor-k44: its four charters
  (page-review-k47, rigid-pages-k48, spread-pages-k49, book-placement-k50), the
  root brief's *Reviewed-design working slices* contract, and the consumer clauses
  it added to corrected-book-k28, appearance-cleanup-k22 and
  workflow-acceptance-k23. The agreed v2 spec and both ADRs are read-only inputs.

## Done when

- Every finding is classified with its reason: a contract stated unclearly, a
  real issue, a visible accepted trade-off, or noise raised for want of context.
  A rejected finding is recorded with evidence rather than dropped.
- Accepted fixes land in place in the root contract and the affected charters,
  without removing any original criterion, protocol or consumer ownership. Where a
  finding requires a stage to be cut narrower, the cut names its complete public
  handoff and keeps the remaining concrete work before its consumer; it creates no
  schema-, renderer-, display- or test-only leaf.
- Decide whether any change alters the agreed v2 design, scale policy or test
  seams beyond clarification. If so, state it as a precise human question with a
  recommendation and evidence rather than silently editing the spec.
- Verify the tree afterwards: handles resolve in the declared order, k27's body
  and the root Done when are unchanged, and no root/consumer criterion was lost.

## Notes

The finding list is the review's own; this charter deliberately does not copy it.
Substantial redesign externalises as its own review chain beside this leaf. No
in-session reviewer beyond the one narrow allowance, no driver, no Norwegian study
and no identical response loop. Within-page and full-default acceptance stay with
corrected-book-k28 before appearance-cleanup-k22 and workflow-acceptance-k23.

## Decisions (running log)

Bootstrap loaded the mandated kind first, then the Grove spine/integration
procedure, resolved k52 and read its root brief/glossary, cited ADRs, reviewed
v2 spec and current producer/consumer charters. Review findings are from k51's
commit `fd66d878`, against producer `d3eaea10`; the working change was empty.
The before-edit tracked digest map and exact root Done when are frozen outside
the repository at `/private/tmp/bookscan-k52-before.json`. Use the existing
Taskfile; no product, spec, ADR, experiment or evidence edits, driver or reviewer.

F1 is a real issue. The first charter combines first-time importer/store/server/
export/acceptance with orientation transitions, and its fallback repeats that
same handoff. Decompose k47 now into complete baseline inspection/assessment/
resume/acknowledged export, followed by exact orientation preview/accept/discard/
revert through that working seam. Preserve the complete original k47 criteria
in its node brief; closure requires both children. Baseline retention remains
accepted state without human approval, but creates no edited-image revision.
Keep estimator assessment and its bridge in the first child: moving them to k48
would weaken the agreed every-page assessment/dependency contract. k48 still owns
fractional sampling; both children precede it and judge actual artifacts for lazy
reviews before their next consumer. This is a repair of staging, not redesign.

F2 is a contract stated unclearly. The inherited complete spec already binds
readiness, terminal/export results, help and --json, but the first slice does not
name executable command-contract acceptance. Assign it to baseline review and
retain compatible events in every extension; preserve preparation's finite result.

F3 is a real issue in sequencing, with a visible accepted trade-off in the signed
fixed 300-dpi RGB representation. Preserve that policy. Classify each fixed-case
fidelity result by mechanism; defects block technical retirement, and real signed
resolution loss earns a precise policy question immediately before dependent
image-edit work, not merely at k28 after all stages. Cut that work only from an
actual failed fixed case. Synthetic intentional downsampling demonstrates the
limitation without itself reopening the signature. Unavailable real truth and
human responses remain owned by k28; neither is a pass. No policy is changed here.

F4 is a contract stated unclearly: the spec's one-bit/grayscale/fine-feature seam
already reaches <=300 ppi, but the charter lacks an independent comparator and
pre-output pass rule. Assign native decoded image/placement evidence independent
of Poppler, known analytic construction controls, separately justified grid/colour
bounds and explicit unsupported/unavailable cases to baseline review. A same-
renderer rerun or exact retained baseline cannot prove source fidelity.

F5 is a real issue. Each later stage must read the preceding stage's frozen
project without changing accepted pixels, IDs, mappings, dispositions or scoped
acknowledgement. Persist private format/capability versions; transactional additive
upgrade is allowed, silent reinterpretation is not. Unknown/unsupported projects
fail INVALID_PROJECT (3) with a concrete compatible-reader/recovery remedy. Keep
the public report at version 1 with its agreed meanings and optional fields.

F6 is a real issue in mechanism ownership. Baseline review owns a pikepdf content/
placement analyzer with independent known-CTM/nested-form/stencil/mask/appearance
controls and unavailable resolution where analysis is incomplete. It also owns
a product-packaged C Leptonica helper built by process:setup, with explicit
compiler/pkg-config/library/tool version checks, source/build digests and runtime
ABI/version/status/angle/ratio preflight. uv's lock alone does not pin system
libraries. Implementation verifies pinned parser/native APIs before relying on
them; no experimental executable or fit path is a runtime dependency.

F7 is a contract stated unclearly. k48's four-edge crop owns the explicitly
reviewed/restorable original-CropBox action and mapped discarded-band inspection;
baseline/orientation review shows guides and unresolved extent reasons until then.
Every finding is accepted to the extent above; none licenses a broader redesign,
new representation, source study or inferred visual approval. The agreed v2,
scale policy and public/full/native/pair/group seams remain read-only inputs.

Applied the repaired plan in place: k47 is a node containing baseline-review-k53
then page-orientation-k54; k48/k49/k50 and k27 -> k28 -> k22 -> k23 retain order.
The complete original k47 Done when is preserved as node closure; new children
own their concrete public handoffs/acceptance. Root and consumers now name the
actual cuts, command events, source-native comparison, pre-dependent fidelity
policy, private-format compatibility, native-helper/ppi mechanisms and k48's
restorable CropBox action. No substantial redesign or new agreement is required
for these implementation/staging clarifications; a future verified fixed-case
representation failure remains an explicit human question, not answered here.

Tier 2 graph verification used project Users-antony-Development-BookScanBuilder,
coverage generation 2026-10-12T06:59:44Z (metadata match, best-effort, no recorded
gap on relied-on cli/pdf/config/spec/ADR paths). Exact cli.main confirms routing
is preparation-only today; the planned command events are new acceptance work.
Exact pdf.document_info confirms support gates, not renderer/ppi fidelity. Broad
exact-symbol search returned 14 rows without pagination. An initial file-filtered
query returned none; it was not treated as absence and the successful unfiltered
lookup supplies the positive evidence. Trace labels contain heuristic resolutions,
so the source snippets, not those labels, support the material claims. Markdown
tree/contracts were read directly; no product or experiment check was run because
this integration changes only planning artifacts.

Verification compared exact source sections and tracked digests with the frozen
pre-edit subjects: root Done when, k27's complete body and k47's original Done
when are unchanged; k28/k22/k23 retain every original line in order; all tracked
files outside .grove are unchanged. Both child brief chains resolve root -> k47.
The final live order is k53 -> k54 -> k48 -> k49 -> k50 -> k27 -> k28 -> k22 -> k23
after this integration retires. No parent closes: the root and k47 have concrete
live work, and this session finishes neither of them. Coverage on current planning
paths has no recorded gap (generation 2026-10-12T07:04:12Z); this log was changed
since that metadata snapshot and read directly. No runtime success, source-native
fidelity, actual fixed-case loss or human output approval is claimed.
