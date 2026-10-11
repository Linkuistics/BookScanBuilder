# prepared-preview-k16

## Goal

Deliver the declared complete dry-run preview of preparation: validate real
explicit PDF selections and report their full order/roles without any output I/O.

## Context

Read the complete parent charter and integrated spec. The temporary packaged
module is invoked by `prepare:plan`, requires `--dry-run`, and shares parsing,
reporting, immutable selection/projection and source-lifetime operation with the
writing successor. No `bookscan` console entry or `prepare:run` exists yet.

## Done when

- Python 3.12/pikepdf 10.16.0 are locked; setup and collection/Poppler-independent
  format/lint/strict-type/synthetic checks run through the root Taskfile.
- All spec phases 1–5 and the source stability recheck work, with every document,
  page, annotation, reachable-object, version/extension and warning gate; retained
  projection/geometry never mutate source objects.
- Preview help/JSON/error precedence, bounds/exclusions, role grouping,
  destination aliases, source changes and caught interruption/result-delivery
  errors pass public/private checks. Tests trap creation and copying/saving,
  compare exact directory listings, and check actual Task forwarding.
- Every root real fixture and synthetic order/gate case has preview evidence,
  frozen script/recipe/lock/fixture/source digests and per-item commands/results.
  Clear usage docs describe preview limits without claiming PDF or visual acceptance.
- Cut the complete writing successor under this node before retirement; carry
  every remaining parent obligation and require shared gates/projection reuse.

## Notes

Keep the historical experiment/report frozen. Follow test-first implementation.
No geometry or processor implementation belongs here. Assess review for the
complete node/product after writing; the live writing child keeps this node open.

## Decisions (running log)

Use `src/bookscan/` for private parsing/selections, result reporting, read-only
PDF projection and the lifetime-owning preparation operation. Test-owned fixture
builders and public subprocess checks live in `tests/`; an explicit real-preview
runner records evidence. The reviewed design replaces a new brainstorming cycle.

The read-only adapter freezes scalar values, raw stream bytes and explicit node
references into immutable projections; inherited/default geometry is normalized
without modifying sources. The eventual pair comparator can ignore object
numbers and sharing while preserving cycles. ISO 32000-1 Table 30 supplies the
standard page-key classification; the version-matched pikepdf 10.16.0 docs
confirm stream ownership, no-recovery opening and raw-stream access.

Byte-authored fixtures are required for malformed extension declarations: the
pinned writer normalizes several intentionally bad declarations, so a normal
save cannot create those controls. The warning/recovery specimens demonstrate
the intended library observations before testing the preview's rejection. The
private lifetime hook supplies controlled source changes and an acknowledged
barrier for real SIGINT/SIGTERM to the host PID; both return INTERRUPTED with
130/143. File/temporary/copy/save/reopen/link traps supplement exact directory
listings rather than letting create-then-delete count as zero writes.

The first real-preview run completed, but subsequent instrument edits make its
report historical only. Do not use it as final evidence: complete every script
edit and rerun in a new artifact directory, digesting every script, recipe,
manifest/lock, fixture and real source before/after. The retained final report
is preview evidence only; writing/render/human acceptance remains the successor's.

Final `task prepare:check COLLECTION=/tmp/bookscan-unavailable-collection` passes
Ruff formatting/lint, strict pyright and 112 tests. Setup and actual preview
forwarding recipes passed. The frozen final preview-acceptance run is
`/private/tmp/bookscan-prepared-preview-k16-v2/report.json`, retained at
`docs/acceptance/prepared-preview-report.json`: all ten individually asserted
cases passed, every source/script/recipe/manifest/lock/fixture digest matched
before/after and still matched on retention, and each preview left its destination
directory unchanged. Algorithm Design retains effective 1.7 and ADBE level 3.
Observed Python 3.12.15, pikepdf 10.16.0/qpdf 12.4.2, uv 0.13.0 and Task 3.54.0.
The experiment/diagram recipes use independent tools or `--no-project`, so setup
does not affect them; their wrappers and frozen report are retained unchanged.

Tier 2 graph verification uses project
`Users-antony-Development-BookScanBuilder`; generation `2026-10-11T04:38:26Z`
records no coverage gap and matching metadata for product/test paths. The
operation's exact snippet and both direct call directions confirm that the
preview and evidence runner consume the same lifetime-owning operation. The
lockfile is not graph-tracked and was read directly; graph coverage remains a
best-effort signal, supplemented by executable/source evidence.

The preview cannot satisfy the node's complete prepared-PDF Done when, so the
node and root remain open. Hand the shared parser/results/selections, immutable
projections and source-lifetime operation to a complete writing child, ahead of
geometry. Product/node adversarial review is assessed when the writer lands;
this session used no in-session reviewer and created no speculative review.

A final frozen check run also retained its exact Task command, stdout/stderr and
before/after product/test/recipe/manifest/lock digests at
`/private/tmp/bookscan-prepared-preview-k16-v2/check.json`; they match, with 112
passing tests and clean Ruff/strict type checks. The complete writing successor
is `prepared-pdf-k17`; the root brief records the activated boundary and keeps
geometry behind it. Only the preview child retires; no ancestor closes yet.
