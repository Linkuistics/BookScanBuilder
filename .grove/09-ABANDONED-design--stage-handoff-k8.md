# stage-handoff-k8

## Goal

Establish a small, reviewable delivery and landing contract for preparation's
product artifacts and durable documents in the end-to-end workspace. Define
the combined development-task contract and processor base without combining
the workspaces' task trees or choosing processor technology.

## Context

Main review `book-reconstruction-k6` at revision `4dbf2ff2`, especially findings
1 and 2, and the integration running log in `book-reconstruction-k7`.
Preparation lives at `/Users/antony/Development/BookScanBuilder.prepare-pdf`;
its reviewed producer is `1ada47bd`. Read its current brief, corrective
handoff and design contract if available. Keys/handles alone are ambiguous
between these workspaces. The scoped preparation contract and end-to-end root
must both survive integration.

## Done when

- Deliver a durable handoff agreement in `docs/specs/stage-handoff.md` naming
  preparation's delivery owner, the receiving root's landing/verification
  work, and the evidence required before a processor workspace is based on
  the result. The agreement does not require the preparation product to be
  implemented while this design runs.
- Establish the jj operation from installed help/source or a bounded disposable
  experiment, considering that a task commit includes `.grove/` changes and
  the two root briefs and local keys diverge. Define a product/durable-document
  path boundary, collision reconciliation, source and receiving revision
  records, original preservation and rollback. Do not rewrite the other
  workspace's active change or import its task tree. A proposed path-scoped
  restore from the review is a candidate, not a mandated solution.
- State how the receiving landing obtains and reconciles root Taskfile recipes
  and dependency files. Preserve `geometry:` experiment tasks and their live
  wrappers; agree preparation's distinct names, shared setup/dependency handling
  and which combined tasks must run on the receiving revision before use.
  Handle experiment-wrapper retirement without dangling recipes. Verify any
  mechanics introduced here; do not create speculative product setup commands.
- Specify the preparation public-command smoke/fidelity check and the isolated
  one-prepared-PDF processor acceptance handoff. One PDF remains the sole
  required processor input. Name the owning execution leaf to be commissioned
  by `corrected-book-k5`; its body will identify the actual delivered revisions
  when they exist.
- Before relying on preparation's plan, confirm its corrective handoff against
  main review `4dbf2ff2` was completed there. If it is unavailable, identify
  the exact missing prerequisite and retain a consumer rather than treating
  the other tree's completion as locally scheduled work.
- Commission an independent `review-design` before `corrected-book-k5` consumes
  this agreement. Insert that review ahead of the consumer; its findings, if
  actionable, must be integrated there before the consumer runs. Do not launch
  another grove driver from this session.

## Notes

This is a bounded handoff design, not an implementation or a redesign of PDF
preparation. No production correction algorithm, interface technology or jj
landing mechanism was selected by planning integration. A local Grove walk
cannot schedule another tree: state cross-tree readiness checks explicitly.
