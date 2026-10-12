# Geometry review handoff

Keep resumable geometry review state in a processor-owned generated project.
Export an ordinary image-only PDF with a versioned readable disposition snapshot
and the universal limitation of unverified within-page geometry. A fresh import
starts new review state; it never restores acceptance, page-side assignments or
alignment from exported metadata. Preparation hints retain their separate
[advisory meaning](prepared-page-hints.md). The public lifecycle is specified in
[Page and book geometry](../specs/rotation-processor.md#geometry-pdf-export).

External reordering can make a saved side sequence stale, and ordinary PDF tools
can discard private metadata. Treating an export report as a resume database or
geometry certificate would turn those losses/changes into silent false acceptance.
The report convention persists in user PDFs, so retain version-aware optional
reading and safe handling of unknown/lost reports. Embedding the complete project
in every output was rejected because it couples an ordinary handoff to original
snapshots, editable assets and state migrations; a required input sidecar would
break the sole-PDF boundary. Reconsider portable project packaging only if an
actual editable-project consumer requires it, without changing the meaning of
existing exported snapshots or trusting them as current review state.
