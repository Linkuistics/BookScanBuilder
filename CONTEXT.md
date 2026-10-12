# BookScanBuilder

Terms for reconstructing a book PDF from scans while preserving its visual
content.

## Language

**Source PDF**:
A PDF supplied for a book conversion, whether it contains raw scans,
previously processed scans, or cover scans.

**Prepared PDF**:
A single PDF containing the book content and chosen cover pages in their
assembly order, ready for page/book geometry processing. Reordering and OCR
follow geometry export in separate tools.

**Raw scan**:
An original scan of a book page or cover, before BookScanBuilder's corrections.

**Page image**:
The scanned visual content of a page, which remains visible in the output PDF
after geometric correction.

**Cover scan**:
A raw scan of a book cover, potentially supplied separately from the page scans.

**Book page**:
One printed page of the original book.

**PDF page**:
One page in an input or output PDF; an input PDF page can contain one book page
or a spread scan.

**Spread scan**:
A raw scan containing two facing book pages in one PDF page.

**OCR text layer**:
Text associated with the page image to support searching and selecting text in
the PDF without replacing the visible page image; supplied by an external OCR
pass after this processor's image-only export.

**Occurrence**:
One input PDF page at its source position, with a stable identity even when its
content duplicates another page. Every occurrence is retained in output order.

**Half**:
One active book-page identity derived from a confirmed spread occurrence, with
its own source-region mapping, geometry, side and disposition.

**Baseline**:
The complete immutable 300-dpi MediaBox RGB render of an occurrence. It replaces
the input's image/vector/text representation; unchanged baseline pixels do not
prove unchanged source fidelity or CropBox-visible extent.

**Native detail**:
A view displaying one project-image pixel per screen pixel. A source-native
view is separately labelled with the source resolution; it may exceed 300 ppi.

**Accepted revision**:
A durable immutable image/placement checkpoint. Initial baseline retention is
accepted state, without implying human inspection or corrected geometry.

**Project**:
Processor-owned saved PDF snapshot, baselines, accepted revisions, book geometry
and review records. Resume uses it; a geometry export report cannot recreate it.

**Review revision / checkpoint revision**:
The identity of the current image, assessment and inspection/disposition facts /
the identity of a durable checkpoint, including acknowledgements and retry outcomes.
Recording acknowledgement advances its checkpoint without changing the review
revision or export snapshot it names.

**View receipt**:
A generated reference to an immutable packet's project, occurrence, displayed
image/review revision and view-region coverage. A recorded action validates it
against the saved descriptor/current state; possession alone implies no inspection.
One receipt permits one normalized request plus identical durable retries;
conflicting reuse is distinct from staleness. New actions check external packet
integrity after durable replay lookup. Each new packet has a distinct opaque
issuance/receipt identity, even when its displayed snapshot is unchanged.

**Body run**:
An ordered selection declaring logical side progression. An active identity has
at most one run position. Blank pages advance parity; explicitly marked repeats
retain the repeated identity's side without advancing logical parity.

**Side**:
Explicit left, right or unknown book-page placement. Run anchors can propose
sides; PDF ordinal and geometry-group membership cannot determine them.

**Geometry group**:
Pages intended to share a canvas/reference layout. An active identity belongs to
at most one group, independently of its body run; a group may span runs. Use this
term instead of “matching group” or “layout group”. Membership is no proof of
accepted matching or a common exported canvas for an unpositioned member.

**Parity break**:
An explicit side override/reanchor for a missing page, repeat or conflicting
sequence, preserving all images and order.

**Anchor / reference frame**:
A reviewed visual registration mark / content frame on a named image revision.
A reference page or pair supplies shared placement guides. These guide alignment
without authorising a crop or mirroring image pixels.

**Target canvas**:
The geometry group's proposed common physical output rectangle, with reviewed
integer translation and white padding at preserved page scale. It must fit the
complete retained image rectangle or be enlarged/rejected.

**Triage reason / universal limitation**:
A recorded page-specific trigger / the statement carried by every page that
within-page geometry remains unverified. Unflagged means no recorded trigger,
not distortion-free. Unverified orientation and import fidelity are reasons too.

**Disposition**:
Accept, reject or retain-unresolved for a named reason/proposal/revision. Default
baseline-retained/unresolved records no human inspection or proposal acceptance.

**Export acknowledgement / geometry review report**:
An explicit choice to export an exact saved snapshot with its limitations /
the optional versioned JSON attachment describing that snapshot. Neither grants
geometry certification or restores review state on reimport.

**Export snapshot digest**:
Identity of the ordered current image/mapping/review/limitation snapshot, excluding
acknowledgement and retry/checkpoint bookkeeping. Summary receipt, effective
acknowledgement, report `snapshot_id` and export result name this same digest;
it is neither the review revision nor the checkpoint revision.

## Example dialogue

**User:** The page turns while it passes through the scanner. I also have a
separate cover scan.

**Developer:** First we combine the source PDFs into one prepared PDF, with the
cover pages in their chosen positions. Then we review page geometry and book
alignment and export the retained page images. You can reorder pages and add
searchable OCR in separate tools afterward.
