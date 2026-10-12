# Page and book geometry

**Design v2 — agreed.** The human replied “agreed” to the presented v2 design.
The reply and its scope are recorded under [Agreement](#agreement).
The human removed processor
reordering and OCR from scope and added book geometry: page alignment/matching
and odd/even treatment. [The editable visual discussion](../design/rotation-processor/README.md)
presents this current design.

## Purpose and boundary

Turn one prepared or already-assembled PDF into a reviewed geometry-corrected
PDF, preserving its visible page images. Focus on geometry within each page and
consistent placement of pages in the book. Reordering, removal of unwanted
pages and OCR happen in separate third-party tools. This processor preserves
all input occurrences and order, expanding confirmed genuine spreads only.
The shipped preparation command remains available for explicit initial assembly.

The initial supported increment offers rigid rotation, safe border/crop/split
controls and book alignment, with any-page review and image-only export. It
cannot yet certify or automatically correct unmeasured within-page curvature or
scanner-feed variation. Those difficult corrections remain required for the
complete default product, through their own evidence and design agreement.
A usable intermediate export is not acceptance of that unresolved geometry.

## Product shape and alternatives

Start one book from the shell and review it in a local browser. The project
saves partial review, geometry choices, page-side/group assignments and accepted
images. Resume without reopening the original collection.

| Public command contract | Result |
| --- | --- |
| `bookscan process PDF --workdir PROJECT` | Import one read-only PDF into a new saved project, assess complete pages and serve local review. |
| `bookscan review PROJECT` | Resume page and book geometry review with matched views and the same controls. |
| `bookscan export PROJECT --output PDF` | Publish a new ordinary image-only PDF containing the accepted geometry in preserved order. Also available from review. |

Process/review run a foreground loopback server; readiness and terminal events
are distinct from export success. Human diagnostics/progress use stderr;
`--json` emits versioned JSON Lines for server events and one result for finite
export. Help explains examples, saved state, limitations and errors without
opening inputs. No daemon, application multi-book queue, native packaging,
processor reordering UI or OCR engine is included.

Local browser review is recommended over command-only edits plus external
viewers: it keeps exact page identities, full/native comparisons and explicit
acceptance together, at the cost of a local server and saved-project format.
A native Mac app adds packaging/framework scope without changing this personal
shell workflow. The agreed interface uses the shell and local browser.

## Complete-page import and assessment

Validate a supported static-page PDF, open it read-only, freeze its identity and
make a verified private project snapshot. Use complete MediaBox RGB rendering
at the existing 300-dpi comparison policy, respecting effective rotation and
physical units. Include text, stencils, vectors, masks, colour and supported
static annotation appearances; extracting the largest image is insufficient.
Keep the original CropBox as an inspectable reference, not a destructive crop.
Record pixel/physical dimensions, original boxes, orientation and render policy.
A higher render resolution does not invent detail in lower-resolution sources.

Use the shipped preparation static-page support domain as the initial input
boundary; its copying evidence does not prove renderer fidelity. Reject encrypted,
recovery-required, unsupported interactive/external/optional-content dependencies
with a named feature/page and remedy. Surface decoder warnings and unexpected
canvases. Once rendering succeeds, unsupported geometry is a usable retained
page with a reason, not a whole-book failure.

Assess every page, including covers, sparse images and previously processed
pages. Read optional preparation roles according to
[prepared-page-hints](../adr/prepared-page-hints.md). They are advisory, grant no
geometry exemption and never cause source discovery/reopening.

The initial accepted image is the complete rendered baseline. “Default retained”
means no accepted geometric change, not human inspection or certified geometry.
Preserve colour, faint print, music and illustrations; RGB conversion is explicit
and matched source/render/native comparisons must check its fidelity. No default
whitening, denoising or lossy image recompression is added.

## Page geometry

### Rotation, local distortion and fallback

Use the installed Leptonica global skew estimator on a disposable analysis copy
as a suggestion, recording status, signed angle, projection-score ratio, regions
and settings. Never binarise the retained visible RGB. The ratio is not calibrated
probability, local distortion detection or real-page ground truth. Sparse text,
music, diagram rules, borders and differing columns can mislead it.

Design v2 requires explicit acceptance of nonzero rotation. Nonzero or unavailable
estimates are review reasons; the user accepts, adjusts or rejects a preview.
Exactly zero retains pixels without resampling. No unsupported deadband,
confidence threshold, ranking or accuracy promise follows from library defaults.
Calibration that would enable unattended application needs its own evidence and
agreement. Automate assessment/previews while making applied choices explicit.

Compose crop/rotation from the immutable baseline rather than repeatedly sampling
intermediates. Right angles permute pixels exactly; fractional preview rotation
uses bicubic RGB interpolation, white fill and an expanded canvas retaining
all source content. Verify sign conversion, fractional nonidentity mappings,
colour/faint/native-detail fidelity and edges independently before accepting that
sampler for the product. The fixed-canvas historical wrapper is not the production
contract. Unsupported or harmful proposals remain unchanged/reverted and explicit.

Rigid tilt removal does not remove within-page curvature or changing local angle.
A global improvement cannot conceal a worsened region. Known conflicting local
observations require reject/revert or retain-unresolved with an inspected reason.
Later evidence-supported nonrigid edits produce new accepted images at the same
review/book-alignment/export seam; no existing family is accepted or universally
rejected by the failed source-observation attempts.

### Genuine spreads and scanner borders

Potential-spread evidence must identify separate printed-page boundaries or page
furniture and an inspectable gutter/content division. A valley, two columns,
aspect ratio, folder or role alone cannot classify a spread. No universal detector
or classification threshold is demonstrated. Suggestions require explicit one-
page/spread classification and boundary acceptance. Uncertainty retains the whole
page until a user decision; any page can be classified manually.

Norwegian20 is the genuine-spread reference; Counterpoint20 remains one landscape
book page with both columns. Confirmed halves retain complete full-height source
regions without a gap, with any deliberate gutter overlap recorded. Preserve
input order with declared left-then-right reading order at the original occurrence.
Keep blank/duplicate halves; external tools own later removal/reordering.

Scanner-border candidates record edge-connected dark material, proposed removed
bands and content near the boundary. Darkness is not proof of scanner identity.
Show the exact discarded bands and full original at native detail. Accept a crop
only after content-retention review; ambiguous material stays unchanged. Support
all four crop edges, restoration and independent half-page adjustment. Do not
silently remove faint printing, edge artwork or distorted gutter material.

First splitting, changing a split or undoing it names the accepted parent/child
geometry choices it supersedes and asks for that explicit replacement. Derive new
halves from the complete immutable source occurrence, never a clipped parent.
No hidden child or stale crop survives in the final roster.

## Book geometry

### Page sides, groups and parity

Geometry groups identify pages intended to share a layout. The user chooses their
members without changing output membership/order, and declares a left/right anchor
or logical page-number anchor where known. The interface may suggest assignments
but never treats PDF ordinal, filename, cover role or inferred printed numbers
as authoritative parity. “Odd/even” is a layout convention explicitly mapped to
left/right, not an assumption about source indices.

Covers, front matter, foldouts and other different layouts can remain standalone
or belong to separate groups; they receive page-geometry assessment regardless.
Within a declared consecutive body run, present alternating sides for confirmation.
A physical blank page in that run consumes a side; excluding a cover from the
matching group does not remove it from the PDF. Show the entire side sequence
before applying matching. An unknown/missing page or conflicting anchor permits
an explicit parity break/reanchor from a chosen occurrence, preserving every image
and order. Never repair parity by silently inserting/deleting/reordering pages.

Split halves have independent book-page identities and sides; a genuine facing
spread can propose left/right based on its confirmed layout. Keep that physical
side evidence distinct from the book's logical numbering. A side/group change
invalidates dependent alignment proposals and requires their review, not unrelated
page-geometry edits. Reimport after external reordering is a new project: exported
side data describes its original export snapshot, not a trusted new page sequence.

### Alignment target and scale policy

**Agreed scale policy:** match placement and mirrored margins while preserving
each page's scale. Scale normalization is outside this design. A later extension
would require an explicit uniform-scaling policy, sampling acceptance and revised
agreement; anisotropic text/music stretching is not implied by “matching.”

For each group choose a target physical canvas and a reference page or reference
left/right pair. Mark a reviewable printed-content frame or named visual anchors
on the reference and candidate pages. Default proposal: match the top anchor and
inner content edge, with mirrored binding margins for left/right pages. Frames
are registration aids, not crop instructions; headers, footers, page numbers,
illustrations and material outside a frame remain visible. Different chapter,
prose/music or sparse layouts may need separate groups/anchors. A detector may
suggest a frame with recorded regions; it is not a proved content boundary.

Match through reviewed horizontal/vertical translation and padding on the common
canvas, preserving the page's scale under the agreed policy. Outer/bottom
margins follow actual content extents; matching inner/top placement does not
assert equal content width/height. Exact integer-pixel shifts require no
interpolation. Fractional placement, if offered, needs explicit sampling policy
and independent fidelity evidence; it is not needed for the first supported
alignment controls.

Preview the target canvas, anchors, inner/outer/top/bottom margins and displacement
for every affected page. A target that would clip any retained image content must
be enlarged or rejected; a smaller canvas requires a separately accepted page
crop. Never trim content merely to make dimensions match. Apply a group proposal
only after reviewing its affected pages, with individual adjustment/rejection and
reversion available. Blank/sparse/unanchorable pages keep their current geometry
until explicitly positioned; another page's detected frame cannot certify them.

Local correction precedes the alignment preview. A later accepted local/nonrigid
edit invalidates the affected book alignment, because its anchors/canvas may have
changed; regenerate the proposal and accept it again. Group-target changes
invalidate all member alignments. Changes to one page's anchor affect that page;
changing a shared reference affects every dependent proposal. Unrelated accepted
pages remain byte-identical.

### Review surfaces

Keep an all-page roster and a triage filter, matched original/current full-page
and native-detail views, a left/right comparison view with mirrored guide lines,
and a group overview exposing inconsistent tops, margins, canvas sizes and sides.
These views use stable occurrence/half IDs rather than current ordinal alone.
For pair comparisons, make scale and any mirroring of guide coordinates explicit;
never mirror the actual book image to fake a match.

The user can adjust any page, flagged or not: rigid angle/orientation, crop,
spread/boundary, group/side/anchor assignment and supported alignment translation.
No reordering, page exclusion, OCR, freehand warp or unproved automatic nonrigid
correction is presented. Separate “page correction” from “book placement” so a
matching adjustment cannot be mistaken for straightened local geometry.

## Honest states and saved review

Every page carries “Within-page geometry unverified; rigid rotation and book
alignment do not correct curvature or scanner-feed variation.” That universal
limitation is separate from triage. Specific reasons record nonzero/unavailable
angle, uncertain split/crop, unavailable/conflicting side or anchor, clipping
risk, alignment proposal or an actual user-observed geometry/detail concern.
Unflagged means only no recorded trigger, never distortion-free or certified.
No invented ranking/threshold promises a small queue.

A preview is a draft. Accept creates a saved immutable image/placement revision;
discard returns to the last accepted one; revert is another explicit accepted
transition to the relevant baseline. Per-page and group operations name their
scope. Resolve flags by accept/reject/retain-unresolved with a reason. Usable
unresolved pages may be exported after explicit acknowledgement; that export
choice does not settle representative product acceptance or root geometry.

The processor owns a generated project, not a required input sidecar: verified
PDF snapshot, full baselines, immutable accepted images, edit/disposition/split
records, group/reference/side/anchor/target records and default output roster.
Use a transactional local store and content-addressed lossless assets. Publish an
asset completely before its checkpoint; only durable checkpoints resume. One
writer owns the project, and browser actions carry the revision they displayed.
Reject stale actions/competing writers actionably. Unsaved previews may be lost;
“saved” is shown only after a durable checkpoint.

| Event | Required lifecycle |
| --- | --- |
| Browser/server interruption | Resume committed choices/assets, including partly reviewed groups; never promote a private partial image to accepted. |
| Same PDF, new project | Fresh assessment with no implicit migrated acceptance. Existing project paths require explicit resume, never reset. |
| Source changes/disappears after snapshot | Resume the verified snapshot. Changed bytes require a new import; filenames/ordinals do not migrate choices. |
| Asset/snapshot mismatch | Stop the affected operation and offer verified recovery/start-new guidance, rather than claim accepted state. |
| Accepted local crop/rotation/nonrigid edit | New page-image revision; invalidate that page's dependent alignment and geometry dispositions tied to replaced pixels. |
| Shared target/reference or side sequence changes | Invalidate affected member alignment proposals; require scoped review/acceptance again. No page order mutation. |
| Undo/change split | Confirm superseded parent/child choices, replace affected topology and side/alignment dependencies; preserve other source occurrences. |
| Renderer/settings change | Freeze existing accepted pixels. Explicit reprocessing creates new proposals/revisions, not silent reinterpretation. |
| Export | Freeze the accepted image/placement roster and block commits until publication/failure. No mixed-revision PDF. |

The final screen shows retained/edited/unresolved pages and matching groups,
side assignments and any parity breaks. Export acknowledgement refers to that
exact accepted snapshot and universal limitation; an affected change requires
renewed acknowledgement. Processor state is a single useful review/export
handoff, not a schema-only/display-only stage.

## Geometry PDF export

Rebuild an ordinary PDF from losslessly embedded accepted RGB images at their
recorded canvas/physical scale, one book page per output PDF page. Use unchanged
input/default split order with all occurrences present. Copy no earlier hidden
text/OCR or source text-resource graph into this fresh output. Visible source
lettering remains in the image, but previous searchability is deliberately lost;
run the separate OCR pass after geometry and any external reordering. This tool
neither chooses an OCR engine nor guarantees another tool's image fidelity.

Validate decoded image bytes, page/canvas transforms, count/order and accepted
revision identity before publication. A zero/unchanged edit retains baseline
pixels; padding/translation preserves the native source region exactly under the
supported integer placement policy. Geometry export does not silently recolour,
resample or substitute unedited images.

Expose the universal limitation in document Subject and an embedded readable
review report listing source occurrence/half, accepted revisions, page geometry,
group/side/anchors/target/alignment, triage and dispositions. Add no warning pages
or image banners. Report loss in a third-party editor does not alter the images;
a fresh import always starts with the universal limitation. The versioned report
is an export snapshot, not a resume database or certificate. Unknown/lost metadata
is optional. Preserve preparation-hint compatibility, with split/alignment
provenance separate from that dictionary's meaning. The persisted lifecycle
decision and rejected alternatives are recorded in
[geometry-review-handoff](../adr/geometry-review-handoff.md).

Originals stay read-only. Require an unused project directory outside the
collection; reject source/project/output aliases by path, case, symlink or hard
link. Never replace an occupied destination. Stage export privately beside the
destination, validate/recheck the complete snapshot, then reuse the existing
atomic no-clobber publication semantics. Pre-commit failure/cancellation keeps
previous output absent/unchanged and review state recoverable. Post-commit
signals/reporting failures preserve a complete published PDF with warnings.
Hard kills can leave identifiable private artifacts; power-loss durability and
indiscriminate orphan cleanup are not promised.

Use the existing error convention for invocation (2), unreadable/unsupported or
invalid project (3), destination conflict (4), processing/validation/I/O (5) and
caught pre-publication signals (130/143). Pending undisposed changes, invalid
matching targets or missing current export acknowledgement return a named
review-required condition (6) with affected IDs/remedy. A geometric concern is
not an unsupported PDF. No unexposed recovery command or implicit reset is needed.

## Ownership and verified technology

Extend the current Python/pikepdf package: complete-page import/assessment;
project and page/book geometry operations; local matched-view presentation;
and frozen image export/publication. Public callers supply one PDF/project and
destination, never resource graphs, geometry-cache keys or transaction protocols.
The composition point can substitute controlled renderer/storage/publication
outcomes for fault tests. These are responsibility boundaries, not horizontal
implementation leaves or a plugin framework.

Use Poppler full-page rendering, Leptonica angle suggestions and Pillow RGB
geometry as the selected dependency approach. Exact installed angle signs, rotation/canvas
semantics and pikepdf placement/publication assumptions must be verified when
implementation pins them. The existing source/native experiments support only
their recorded bounded claims; they are not a production processor.

## Agreed public and visual test seams

Exercise installed preparation where applicable, then the real public process,
page/book review controls and image-only export, including ordinary unmarked
sole-PDF input with the source collection genuinely unavailable. Observe a
control that is denied read access in that same boundary; a changed collection
string alone is insufficient. Controlled internal faults supplement public
commands and actual writer signal/kill observations.

| Case | Independent required outcome |
| --- | --- |
| Known upright/tiny-angle/noisy/rigid fixtures | Construction supplies angle and coordinates independently of the estimator. No unaccepted resampling; accepted rotation retains all regions and content against justified measured limits. |
| Known curved/local-angle-variation fixtures | Global rotation/alignment cannot be credited as local correction; check regions independently so aggregate improvement hides no worsening. |
| Nonidentity fractional RGB sampling | Independent coordinate/sampler oracle, edge/canvas/colour/faint/music checks and native detail. Identity/copy is insufficient. Reject wrong angle/image/region/mapping controls for the stated mechanism first. |
| Known translated left/right page pair | Independent source anchors and declared sides predict common top/inner placement and mirrored margins. Retained native pixels, scale and all source content survive. Wrong side/anchor/offset/canvas controls must fail independently. |
| Covers/front matter/blank and missing-page sequence | PDF index differs from logical parity; explicit groups/anchors and parity break preserve all images/order. Blank consumes a side only in its declared run. No silent parity repair. |
| Different content layouts and unanchorable page | Separate groups/reference frames and usable unchanged/manual placement; no borrowed frame, forced scale or clipping. |
| Any-page and group review | Real accepted edit, discard and revert on flagged and unflagged pages; matched full/native/pair/group views, partial resume, stale-action rejection and final accepted geometry. |
| Spread and blank/duplicate halves | Genuine split versus landscape single page, complete provenance/partition, all halves/default order retained without processor removal/reordering. |
| Earlier OCR/text fixture | Visible source lettering survives full rendering; fresh output contains exact accepted images and no stale old selectable text. This is text omission, not OCR recognition/alignment acceptance. |
| Failure/publication | Corrupt assets, shared-target invalidation, split replacement, lock conflict, interruption and occupied destination preserve committed review/originals/prior output. |

Assess all fixed real cases independently: both Norwegian20 gutters;
Garbage Collection30 indentation/glyphs/boxes/arrows; Counterpoint20 single
landscape page/both columns; Fundamentals40 faint prose and any music detail;
SchoenbergComposition cover1 colour/sparse rules; Algorithm Design20 already-
processed preservation and nonidentity sampler companion. Preserve music140's
unsupported-layout diagnostic separately from music20's acquisition candidate.
Add adjacent/group book-page comparisons without replacing those fixed cases.
Alignment numerical truth needs independent known anchors/regions and justified
limits; a detector's own output/rerun is no oracle for real pages.

Record numerical passed/failed/unavailable separately from human visual accepted/
pending/rejected, with actual inspected full/native/pair/group views and verbatim
scoped replies. A retired technical slice, export or alignment score supplies
no missing acceptance. A planner may allow a reaction-pending technical boundary
only with precise retained ownership before product consumers. Full within-page
and book-geometry acceptance still precedes optional appearance and final root
acceptance. No new Norwegian study, failed-grid retry, forced model, gate/holdout
rescue or music acquisition change is commissioned here.

Use and reconcile the shared Taskfile and locked setup. Retain required existing
preparation/geometry recipes. Finish edits before measurements; digest every read
subject before/after with one writer and compare reruns per item. Verify affected
recipes, preparation and native checks. Keep originals read-only and artifacts
outside the collection.

## Agreement

The human replied verbatim **“agreed”** to the presented v2 design and stated
scale-preserving matching policy. This agreement covers the geometry-only
shell/local-browser workflow, supported page/book controls, saved review and
image-only export, and the public/full-page/native/pair/group test seams above.
OCR/reordering remain external, and scale normalization is not commissioned.
The presented pre-signature spec SHA-256 was
`b6c8458e0c42cfc2d1431ed49e1613b02c6e2b31ac5176a958ab47869e563caf`;
the editable views and contract were presented at
`http://127.0.0.1:8770/#diagram-book-alignment` and
`http://127.0.0.1:8770/contract.html#book-geometry`.
No actual output-view inspection is attributed to that reply. This is a design
agreement, not acceptance of a working product, nonrigid result or historical
preparation/geometry comparison. The agreed design undergoes its earned review
before implementation planning; production verification remains outstanding.
