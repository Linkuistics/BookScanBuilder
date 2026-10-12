# rotation-processor-k46

**Integrates:** rotation-processor-k45

## Goal

Triage rotation-processor-k45's findings against the agreed page/book geometry
Design v2. Apply the real ones to the spec, ADR set, design views and glossary
before its implementation planner (rotation-processor-k44) consumes them.

## Context

- Read the findings from rotation-processor-k45's own committed review leaf and
  commit, then re-derive each against the current tree. Each finding cites
  `docs/specs/rotation-processor.md` at commit `31b18570`, so confirm the lines
  have not moved.
- The producer is rotation-processor-k41: its spec, `docs/adr/geometry-review-handoff.md`,
  `docs/design/rotation-processor/` (edit the Markdown/D2 sources and regenerate
  through the existing render recipe) and the actual verbatim **“agreed”** scope
  recorded in its running log and the spec's Agreement section.

## Done when

- Every finding is classified with its reason: a contract stated unclearly,
  valid and actionable, a visible accepted trade-off, or noise. A rejected
  finding is recorded with evidence, not silently dropped.
- Accepted fixes land in place in the current-state spec/ADR/glossary set and
  the regenerated visual document, with their citations reconciled.
- Decide whether a change alters the signed product shape, scale policy or test
  seams, beyond a clarification of what was agreed. If it does, present that
  specific change to the human and record the verbatim scoped reply before the
  planner runs. Silence, or an unavailable reply, is no agreement. Do not re-open
  the agreed design through an identical response loop.
- Verify affected recipes and checks after edits, with the frozen-subject
  discipline the root brief requires.

## Notes

The review's finding list is its own; this charter deliberately does not copy
it. A substantial redesign surfaced here externalises as its own producer
review chain beside this leaf rather than growing this session. OCR and
reordering stay external, and within-page/full-default acceptance stays with
k28 and its successors.

## Decisions (running log)

Bootstrap read the mandated integration skill first, then the Grove spine/family,
glossary, root brief, cited ADRs and this task. Review findings were read from
rotation-processor-k45's own commit `84413368`; the reviewed spec is still exactly
the producer's `31b18570` artifact. Use jj and the existing Taskfile. No producer,
implementation or new source study is commissioned by this integration.

F1 is a contract stated unclearly plus a visible representation trade-off. Keep
the signed complete 300-dpi MediaBox RGB baseline, rather than silently changing
resolution or introducing image extraction. Explicitly distinguish input fidelity
from baseline pixel retention, flag effective image resolutions above 300 ppi or
unknown resolution, and require input-relative source/detail comparisons. Such
loss cannot pass preservation acceptance merely through an export acknowledgement.
RGB storage/memory costs are unmeasured production costs, with a decoded-pixel
lower bound stated. No new ADR: this reversible renderer choice fails the AND-test.

F2 is valid/actionable for the confidence-zero sentinel; the 1.87.0 primary source
confirms status zero alone is insufficient. Orientation blindness is a visible
trade-off, not a promise that every sideways/upside-down page produces zero.
Add independent orientation/range/blank cases and an orientation-unverified reason.

F3 is a contract stated unclearly. Assessment leaves the baseline accepted and
its reasons retained unresolved without implying inspection. Draft/stale changes
block export until explicitly discarded or regenerated; snapshot acknowledgement
permits retained unresolved pixels, never bulk acceptance of rotation. The claim
that nearly every page is flagged is noise: two recorded examples cannot estimate
book-wide prevalence. Warn honestly that every nonzero estimate triggers review
and that no small queue is promised.

F4 is a contract stated unclearly. Keep the existing full-height vertical split,
allow recorded overlap, rotate each source region, then crop in its expanded
rotated frame, then place on the book canvas. Source-region/rotation/crop mappings
are recorded. Tilted gutters need reviewed overlap and per-half inner crops;
unsupported divisions remain whole/unresolved. No new oblique-split mechanism.

F5 and F6 are contracts stated unclearly. White padding is explicit/previewable;
uncropped borders/rotation fill can grow the canvas. Unpositioned members retain
their own canvas with an unresolved placement reason until individually placed.
Define independent body runs, sides and geometry groups (one run/group at most
per active book-page identity); a group may span runs. Explicit duplicate siding
and reanchoring preserve every occurrence and avoid advancing logical parity.

F7 is valid/actionable: a reference-image edit invalidates every dependent
placement, a member overflow reopens target review, and replaced-image anchors
must be re-marked rather than silently carried. Add both independent fault cases.

F8 is valid/actionable. Specify a version-1 UTF-8 JSON document attachment and
its minimum fields in the existing spec/ADR. Geometry exports omit preparation
page hints; their immediate-source semantics remain unchanged. Import ignores the
report and starts fresh, including after metadata loss. No new persistent meaning
or resume database is introduced.

F9 is a contract stated unclearly. Retain foreground process/review commands,
define normal UI stop (0), caught signals (130/143), kernel-released single-writer
locking and named lock/export conflicts. Do not add an unattended/headless command
as an optional enhancement. Collection separation is a caller/acceptance duty;
runtime verifies aliases rather than discovering a collection.

F10 is a visible accepted trade-off stated unclearly: keep the signed MediaBox
baseline, show the original CropBox boundary and flag changed visible extent for
explicit disposition/acknowledgement. Add boxes/Rotate/UserUnit cases at the same
public/full/native seam; export cannot imply input-view preservation on them.

F11 is valid/actionable current-state drift. Repair preparation's downstream
scope statements, the root's half-page responsibility and the glossary without
changing shipped preparation behaviour or frozen historical evidence.
F12 is valid/actionable hygiene: remove Grove work-orders from the durable spec,
retaining its behavioural acceptance and honest numerical/visual dispositions.
F13 is valid/actionable local-server hardening: per-session action authentication,
Host/Origin validation and an explicit user-chosen export destination.
F14 is valid/actionable: require tool preflight/version records and a direct
Pillow pin when implementing; check the current locked API without changing
product dependencies in this design-only session.

These repairs clarify the signed geometry-only shell/browser shape, retained
baseline, explicit nonzero acceptance, scale preservation and existing public/
full/native/pair/group seams. Added cases challenge those same seams. No renewed
signature or substantial redesign is needed; adaptive resolution, CropBox-default
import, unattended application, headless commands and renaming are not adopted.
The optional iteration note is useful clarification; retain the stable slug.

Spent the one narrow fresh-context reviewer on the signed-default/product-shape
comparison only, without this log or my conclusions. It independently compared
the current spec with `31b18570` and reported no concrete change requiring a fresh
signature or direct contradiction in that scope. No second reviewer is needed.
Final inline reading preserves the original independent accepted-rotation
content/limits check, uses the canonical geometry-group term, and makes Stop
review wait for in-flight export's separate result. Removing invalid placement
allows retained-local export; an invalid target blocks only if the roster uses it.
These are mechanical consistency repairs, not a new design or review cycle.

Verification is complete for this documentation integration. `task
process:design-render` regenerated all four diagrams, the contract and reference
copies. `task process:design-serve DESIGN_PORT=8771` served all 14 requested
files with HTTP 200 and exact local bytes; that temporary server was stopped.
Canonical Markdown/rendered contract equality, all SVG node labels, three
byte-identical references and local link/fragment targets passed. A deliberately
wrong contract control was rejected. The final render after mechanical wording
repairs changed only the spec/contract relative to the prior completed check;
all SVGs/references and product/native subjects matched item by item.

`task prepare:check` passed Ruff formatting/lint, strict Pyright and 231 tests.
`task geometry:staff-check` passed formatting/lint and four native gate tests.
No production/experimental source, Taskfile or lock dependency was changed.
The locked Pillow 12.3.0 rotate/transpose/crop/paste API was inspected directly;
this is API evidence, not sampler/real-page fidelity acceptance. Render input
digests (13 files) and check-subject digests (49 files) were identical before/after
each completed run, including Taskfile/locks, copied canonical inputs, design
sources/assets and source/test/experiment subjects. Records are retained under
`/private/tmp/bookscan-k46-{render,check}-before.json`/`-after.json`,
`bookscan-k46-artifacts.json`, `bookscan-k46-served.json`,
`bookscan-k46-final-render-{before,after}.json` and `bookscan-k46-final-checks.json`.

Graph verification used project `Users-antony-Development-BookScanBuilder`,
generation `2026-10-12T05:59:17Z`, with exact-path coverage for relied-on artifacts
and source symbols. Metadata is best-effort, not completeness. D2/uv.lock freshness
was untracked, SVGs deliberately excluded and contract.html partial at line 1;
all were read/parsed/compared directly. Exact installed CLI/wrapper snippets and
Leptonica 1.87.0 primary skew source confirmed the bounded API/sentinel claims.

All F1–F14 findings have classified reasons above. Spec/ADRs/glossary and generated
views are reconciled in place; no slug was renamed or citation deleted. The root
now carries the concrete k46 → k44 handoff and preservation limitations. All
within-page/source/visual/default-product obligations remain with k27/k28 and
their actual successors before appearance/final acceptance. No substantial
redesign or additional tree leaf was earned. Retire this leaf and seal its
focused commit; its parent is the root with live consumers, so no node closes.
