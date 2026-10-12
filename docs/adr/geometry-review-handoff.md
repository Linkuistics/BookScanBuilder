# Geometry review handoff

Keep resumable geometry review state in a processor-owned generated project.
Export an ordinary image-only PDF with a versioned readable disposition snapshot
and the universal limitation of unverified within-page geometry. A fresh import
starts new review state; it never restores acceptance, page-side assignments or
alignment from exported metadata. The version-1 UTF-8 JSON report uses the
document-level embedded-file attachment `BookScanBuilder-geometry-review.json`;
unknown/malformed/lost reports remain optional unavailable information. The
report `snapshot_id` and its acknowledgement name the same exact export-snapshot
digest as the summary receipt/export result, excluding acknowledgement and retry/
checkpoint bookkeeping; neither image nor review/checkpoint revision replaces it.
Geometry export omits preparation page hints, avoiding stale immediate-source
provenance.
Import still accepts those hints under their separate
[advisory meaning](prepared-page-hints.md). The public lifecycle is specified in
[Page and book geometry](../specs/rotation-processor.md#geometry-pdf-export).

External reordering can make a saved side sequence stale, and ordinary PDF tools
can discard private metadata. Treating an export report as a resume database or
geometry certificate would turn those losses/changes into silent false acceptance.
An ordinary document attachment makes the disposition snapshot independently
readable without private page-dictionary interpretation; copying preparation
hints onto transformed/split pages was rejected because their source semantics
describe the preparation assembly, not geometry lineage.
The report convention persists in user PDFs, so retain version-aware optional
reading and safe handling of unknown/lost reports. Embedding the complete project
in every output was rejected because it couples an ordinary handoff to original
snapshots, editable assets and state migrations; a required input sidecar would
break the sole-PDF boundary. Reconsider portable project packaging only if an
actual editable-project consumer requires it, without changing the meaning of
existing exported snapshots or trusting them as current review state.
