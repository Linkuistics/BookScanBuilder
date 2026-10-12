# Page and book geometry

**Design v2 — agreed, with review clarifications.** The reply and its scope are
recorded under [Agreement](#agreement).
[The editable visual discussion](../design/rotation-processor/README.md) presents
the geometry-only design, including page alignment and explicit side assignment.

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

“Stop review” in the browser durably completes any in-flight accepted checkpoint,
discards unsaved previews, stops the server and exits 0. It does not export or
accept unresolved geometry. If export is in progress, Stop review waits for its
separate publication/failure result before stopping. A caught SIGINT/SIGTERM exits
130/143 after safe checkpoint cleanup; use Stop review for a successful shell-loop iteration.
Closing the tab does not stop the server. Import/assessment completes before the
ready event; no unattended import-only mode is offered. Each server start creates
an unguessable session token, supplied in its local URL and every action. Validate
the loopback Host and exact server Origin, reject tokenless/foreign-origin actions,
and serve no cross-origin state-changing endpoint. The browser export control
requires an explicit user-entered destination and confirmation; it never derives
a destination from the source or a remote request. Stop is authenticated too.

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
This re-rasterises the complete PDF composition; source image objects, colour
spaces, compression and vector/text representations are replaced by lossless RGB
pixels. The fixed import resolution is 300 dpi, not a native-image pass-through.
Record the effective horizontal/vertical ppi of contributing images, including
stencils/masks and transformed placements. Effective ppi above 300, or an
unavailable resolution assessment, adds an import-fidelity reason: downsampling
may lose source detail. Higher rendering resolution cannot invent missing detail.
Show source-relative full-page and native-detail comparisons, including source
image detail above 300 ppi; baseline equality cannot prove input fidelity.

The signed MediaBox policy preserves recoverable source content but may reveal
material hidden by a smaller CropBox and change the default visible page size.
Show both extents, add an extent-change reason whenever their effective display
regions differ, and permit an explicitly reviewed/restorable crop to the original
CropBox. No default-retained claim implies equality with a CropBox-based viewer.
Honour `/Rotate` and UserUnit in both display guides and physical dimensions.

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
means no accepted geometric change after import, not input-byte preservation,
human inspection or certified geometry. “Native detail” of a project image means
one displayed pixel per baseline/accepted pixel; source-native comparisons are
labelled separately with their own resolution. An import-fidelity or extent
concern remains unresolved unless explicitly disposed of, and an export
acknowledgement cannot turn a degraded import into a preservation-test pass.
Preserve colour, faint print, music and illustrations; RGB conversion is explicit
and matched source/render/native comparisons must check its fidelity. No default
whitening, denoising or lossy image recompression is added.

Production project/export size and peak memory are currently unmeasured. A
decoded RGB image alone needs width × height × 3 bytes; the 3591×2695 Norwegian
comparison raster is about 29 MB before renderer/sampler/store overhead. The
project retains its PDF snapshot, full baselines and accepted revisions, so
storage and working memory can substantially exceed compressed one-bit or
grayscale inputs. Lossless compression and identical-asset reuse do not supply
a bound on peak memory. Acceptance records per-page dimensions, stored bytes,
export size and observed peak memory; resource failure is explicit, with no
silent lower-resolution fallback.

## Page geometry

### Rotation, local distortion and fallback

Use the installed Leptonica global skew estimator on a disposable analysis copy
as a suggestion, recording status, signed angle, projection-score ratio, regions
and settings. Never binarise the retained visible RGB. The ratio is not calibrated
probability, local distortion detection or real-page ground truth. Sparse text,
music, diagram rules, borders and differing columns can mislead it.

Design v2 requires explicit acceptance of nonzero rotation. An estimate is
unavailable if status is nonzero, confidence is zero, or either numeric output
is non-finite. The zero-confidence invalid sentinel can accompany status zero;
a zero angle is usable only after these validity checks. Nonzero or unavailable
estimates are review reasons; the user accepts, adjusts or rejects a preview.
A valid exactly-zero estimate retains baseline pixels without further resampling.
No unsupported deadband,
confidence threshold, ranking or accuracy promise follows from library defaults.
Calibration that would enable unattended application needs its own evidence and
agreement. Automate assessment/previews while making applied choices explicit.

The selected default sweep is ±7° about upright. It supplies no 90°/180°
orientation classification and no reliable beyond-range correction. Every page
retains an orientation-unverified reason until orientation is explicitly reviewed;
a valid skew angle does not clear it. Manual right-angle orientation is available.
Range-edge warnings and unavailable measurements remain explicit. These limits
come from [Leptonica 1.87.0's primary skew implementation](https://raw.githubusercontent.com/DanBloomberg/leptonica/1.87.0/src/skew.c),
not from a tuned confidence policy. Nonzero estimates can create a large review
queue, including tiny suggestions on already-correct pages; no prevalence or
small-queue claim is established by the existing examples.

The coordinate pipeline is immutable full baseline → source region (whole page
or confirmed half) → orientation/rigid rotation on an expanded canvas → accepted
crop in that rotated canvas → book translation/padding. Coordinates are pixel
edges from the top-left, x right/y down; source regions and crop rectangles have
integer, half-open bounds. Record the source-region offset, rotation mapping,
expanded-canvas origin and crop offset so every output region maps back to source.
Crop controls show that rotated frame alongside its mapped original discarded
bands; changing angle invalidates the old crop preview and requires review.
Compose the mapping from the immutable baseline, sampling fractional rotation
once rather than successively sampling previews. Right angles permute pixels
exactly; fractional preview rotation
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

The supported split uses full-height vertical regions in baseline coordinates.
For a tilted gutter, choose a reviewed overlap wide enough to retain each page's
content, then independently rotate each half and review an inner crop in its
rotated frame. Facing-page material and repeated gutter pixels are visible in
full/native views and the source mapping; they are explicitly cropped or retained
unresolved, never silently assigned away. A gutter/content division that cannot
be separated safely by this path stays whole or unresolved. Oblique partitioning
is not supplied by the vertical split contract.

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

An occurrence is one input PDF page in source order, including repeated content;
confirmed splitting replaces its active book-page identity with two half IDs.
Each active identity has at most one body-run position and at most one geometry
group. A body run is an ordered selection declaring logical side progression;
a geometry group declares intended common canvas/reference placement. They are
independent: a group may span runs, and a chapter opener may use a separate group
while retaining its run side. Each identity has one explicit left/right/unknown
side; outside a run it can be assigned individually. Unknown side cannot receive
a mirrored-margin proposal.

Geometry groups identify pages intended to share a layout. The user chooses their
members without changing output membership/order. A body run declares a left/right
starting side or logical page-number anchor where known. The interface may suggest
assignments but never treats PDF ordinal, filename, cover role or inferred printed numbers
as authoritative parity. “Odd/even” is a layout convention explicitly mapped to
left/right, not an assumption about source indices.

Covers, front matter, foldouts and other different layouts can remain standalone
or belong to separate groups; they receive page-geometry assessment regardless.
Within a declared consecutive body run, present alternating sides for confirmation.
A physical blank page in that run consumes a side; excluding a cover from the
geometry group does not remove it from the PDF. Show the entire side sequence
before applying matching. An unknown/missing page or conflicting anchor permits
an explicit parity break/reanchor from a chosen occurrence, preserving every image
and order. Never repair parity by silently inserting/deleting/reordering pages.

A duplicate occurrence inside a run is retained. The user can explicitly mark
it as a repeat of an earlier active identity in that run: it takes that identity's
side and does not advance logical parity. This relation is advisory user input,
not automatic image-duplicate detection. The next ordinary page advances from
the last non-repeat position. Removing/changing a repeat relation reopens the
affected side sequence. An unclassified duplicate needs individual side override
and explicit reanchoring, not a guessed deletion. Conflicting repeats/anchors
require correction or unknown sides with an unresolved reason.

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

Match through reviewed horizontal/vertical translation and white RGB padding on
the common canvas, preserving the page's scale under the agreed policy. Outer/bottom
margins follow actual content extents; matching inner/top placement does not
assert equal content width/height. Exact integer-pixel shifts require no
interpolation. Fractional placement, if offered, needs explicit sampling policy
and independent fidelity evidence; it is not needed for the first supported
alignment controls.

Padding adds visible white bands on toned-paper scans; full and pair views show
the added regions distinctly as guides without altering exported image pixels.
The retained rectangle includes uncropped scanner borders and rotation fill.
Preserving that rectangle at reviewed offsets can enlarge the common physical
canvas beyond original paper dimensions; show both dimensions and all added bands.

Preview the target canvas, anchors, inner/outer/top/bottom margins and displacement
for every affected page. A target that would clip any retained image content must
be enlarged or rejected; a smaller canvas requires a separately accepted page
crop. Never trim content merely to make dimensions match. Apply a group proposal
only after reviewing its affected pages, with individual adjustment/rejection and
reversion available. Blank/sparse/unanchorable pages keep their current geometry
until explicitly positioned; another page's detected frame cannot certify them.
An unpositioned group member exports its current local canvas, with a retained
unresolved placement reason and a visible size mismatch in the group overview.
It joins the common canvas only after explicit manual integer placement with
content-fit review. Group membership expresses intent, not completed matching.

Local correction precedes the alignment preview. A later accepted local/nonrigid
edit invalidates that image's anchors and alignment; re-mark anchors on the new
revision, then regenerate and accept placement. Do not silently transport old
marks, even through a known rigid mapping. If the edited image is a reference,
invalidate every placement dependent on it, including other group members.
If a member's retained rectangle no longer fits the target, mark that target
invalid, require enlargement/rejection review and never clip. Group-target changes
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
angle, unverified orientation, import-fidelity/extent concerns, uncertain split/crop,
unavailable/conflicting side or anchor, clipping risk, alignment proposal or an
actual user-observed geometry/detail concern.
Unflagged means only no recorded trigger, never distortion-free or certified.
No invented ranking/threshold promises a small queue.

A preview is a draft. Accept creates a saved immutable image/placement revision;
discard returns to the last accepted one; revert is another explicit accepted
transition to the relevant baseline. Per-page and group operations name their
scope. Resolve flags by accept/reject/retain-unresolved with a reason. Initial
assessment records baseline-retained/unresolved against each trigger, without
attributing inspection. Rejecting a proposed rotation retains the last accepted
pixels and records rejection; accepting it names the displayed revision and scope.
Draft edits are never exported: explicitly accept or discard them first. Stale
accepted placements cannot be exported; regenerate them, or explicitly remove
that placement and retain the current local image as unresolved.

The final acknowledgement may cover a named selection or the whole export's
retained unresolved pages with a recorded reason. It lists IDs, dispositions,
import/geometry/placement concerns and the universal limitation. It accepts no
rotation proposals and implies no inspected page. No bulk rotation acceptance is
offered. Thus an all-nonzero book can export its unchanged baselines after draft
discard and snapshot acknowledgement; applying any rotation still needs explicit
acceptance. Usable unresolved pages may be exported; that choice does not settle
representative product acceptance or root geometry.

The processor owns a generated project, not a required input sidecar: verified
PDF snapshot, full baselines, immutable accepted images, edit/disposition/split
records, group/reference/side/anchor/target records and default output roster.
Use a transactional local store and content-addressed lossless assets. Publish an
asset completely before its checkpoint; only durable checkpoints resume. One
writer owns the project, and browser actions carry the revision they displayed.
Reject stale actions/competing writers actionably. Unsaved previews may be lost;
“saved” is shown only after a durable checkpoint.

Writer exclusion is an operating-system lock on the project, released on process
death; existence of a marker file is not ownership. Review holds it for its whole
server lifetime, so a competing review or shell export returns `PROJECT_BUSY` (4)
with Stop review/retry guidance. Review's own export uses its existing ownership.
Export freeze is a live-owner constraint, not a persisted permanent lock. After
a hard kill, resume the last durable checkpoint, verify assets and classify any
private export artifact; never promote it merely because it exists. An output
already published remains complete and occupied. Browser commits during live
export return `EXPORT_IN_PROGRESS` (6), and completion/failure clears that freeze.

| Event | Required lifecycle |
| --- | --- |
| Browser/server interruption | Resume committed choices/assets, including partly reviewed groups; never promote a private partial image to accepted. |
| Same PDF, new project | Fresh assessment with no implicit migrated acceptance. Existing project paths require explicit resume, never reset. |
| Source changes/disappears after snapshot | Resume the verified snapshot. Changed bytes require a new import; filenames/ordinals do not migrate choices. |
| Asset/snapshot mismatch | Stop the affected operation and offer verified recovery/start-new guidance, rather than claim accepted state. |
| Accepted local crop/rotation/nonrigid edit | Invalidate replaced-image anchors/dispositions and its placement. A reference edit invalidates every dependent placement; member overflow invalidates the target. Re-mark/regenerate/review; unrelated groups remain unchanged. |
| Shared target/reference or side sequence changes | Invalidate affected member alignment proposals; require scoped review/acceptance again. No page order mutation. |
| Undo/change split | Confirm superseded parent/child choices, replace affected topology and side/alignment dependencies; preserve other source occurrences. |
| Renderer/settings change | Freeze existing accepted pixels. Explicit reprocessing creates new proposals/revisions, not silent reinterpretation. |
| Export | Freeze the accepted image/placement roster and block commits until publication/failure. No mixed-revision PDF. |

The final screen shows retained/edited/unresolved pages and geometry groups,
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
pixels; padding/translation preserves the retained baseline/accepted region
exactly under the supported integer placement policy. Export adds no further
recolouring or sampling. This guarantee is relative to the imported RGB baseline,
not the source PDF's native image objects or pre-import rendering/colour spaces.

Expose the universal limitation in document Subject and an embedded readable
review report listing source occurrence/half, accepted revisions, page geometry,
group/side/anchors/target/alignment, triage and dispositions. Add no warning pages
or image banners. Report loss in a third-party editor does not alter the images;
a fresh import always starts with the universal limitation. The versioned report
is an export snapshot, not a resume database or certificate. Geometry exports
omit page-level `/BookScanBuilder` preparation hints instead of copying stale
immediate-source provenance. Import still accepts ordinary PDFs and version-1
preparation hints under their unchanged advisory meaning. Split/alignment lineage
lives only in the geometry report/project. The persisted lifecycle
decision and rejected alternatives are recorded in
[geometry-review-handoff](../adr/geometry-review-handoff.md).

The report is a document-level embedded-file attachment named
`BookScanBuilder-geometry-review.json`, keyed by that name in the PDF
`/Names` → `/EmbeddedFiles` name tree, with MIME type `application/json`.
Encode one UTF-8 JSON object without a BOM; do not attach original PDFs or the
editable project. The [selected PDF library's attachment API](https://pikepdf.readthedocs.io/en/latest/topics/attachments.html)
supports this ordinary viewer-readable container. Required version-1 fields:

| Field | Meaning |
| --- | --- |
| `format`, `version` | `BookScanBuilderGeometryReview` and integer `1`. |
| `source_sha256`, `snapshot_id` | Input snapshot digest and the exact acknowledged accepted project revision. No collection path is required. |
| `limitation`, `toolchain` | Universal limitation text; renderer/estimator/sampler/library versions and render/analysis settings. |
| `pages` | Array in exported order; every entry has stable `id`, one-based `source_pdf_page`, nullable `half`, baseline `source_region`, `image_revision`, decoded `image_sha256`, pixel/physical canvas dimensions, page-edit mappings, nullable geometry-group/run IDs, side/repeat/anchors/reference/target/placement records, triage reasons and their dispositions. No acceptance is inferred from absent fields. |
| `acknowledgement` | Exact snapshot ID, affected unresolved IDs/reasons and explicit acknowledgement, with inspection scope recorded separately. |

A report-only reader ignores unknown additional fields; unknown version, malformed
or absent reports are unavailable optional information. Processor import does not
consume report dispositions, sides or acceptance at any version: reimporting an
export, with or without its metadata, creates fresh baselines/assessment and the
universal limitation. After external reordering/OCR, further edits use the
original project and require re-export plus repeating those external passes.

Originals stay read-only. Require an unused project directory; callers keep
projects/derived artifacts outside their source collection. The sole-PDF processor
does not discover or know that collection's root. Check source/project/output
aliases by path, case, symlink or hard link. Never replace an occupied destination.
Stage export privately beside the
destination, validate/recheck the complete snapshot, then reuse the existing
atomic no-clobber publication semantics. Pre-commit failure/cancellation keeps
previous output absent/unchanged and review state recoverable. Post-commit
signals/reporting failures preserve a complete published PDF with warnings.
Hard kills can leave identifiable private artifacts; power-loss durability and
indiscriminate orphan cleanup are not promised.

Use the existing error convention for invocation (2), unreadable/unsupported or
invalid project (3), destination conflict (4), processing/validation/I/O (5) and
caught pre-publication signals (130/143). Pending undisposed changes, invalid
matching targets still used by the export roster or missing current export
acknowledgement return a named review-required condition (6) with affected
IDs/remedy. A geometric concern is
not an unsupported PDF. No unexposed recovery command or implicit reset is needed.
Here “pending undisposed changes” means draft edits or invalidated placements,
not baseline-retained unresolved assessment reasons. Codes 4 and 6 also cover
`PROJECT_BUSY` and `EXPORT_IN_PROGRESS` as above. Clean server stop is 0;
authentication/origin failure rejects the HTTP action without mutating the project
or terminating an otherwise healthy server. Export's publication outcome is
reported separately from a later server stop/signal.

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

Before import or resume starts serving, preflight the renderer, estimator binding
and RGB sampler against the project's supported versions. Missing/incompatible
tools return `DEPENDENCY_UNAVAILABLE` (5), naming the tool/version and installation
or locked-setup remedy, without creating accepted state. The estimator is reached
through a packaged native bridge exposing Leptonica's installed version, status,
angle and score ratio, not an unversioned experimental executable. Record Poppler,
Leptonica, Pillow and pikepdf versions plus analysis/render settings in each project
and exported snapshot. A changed toolchain follows the renderer/settings lifecycle
rule; resume must not silently reinterpret accepted images. Pillow needs a direct
product pin when the processor is implemented: the current lock resolves 12.3.0,
whereas historical experiment evidence used 11.3.0. Verify the actual selected
version's rotate/transpose/crop/paste semantics and independent sampler fidelity;
a signature-compatible API alone does not establish image quality.

## Agreed public and visual test seams

Exercise installed preparation where applicable, then the real public process,
page/book review controls and image-only export, including ordinary unmarked
sole-PDF input with the source collection genuinely unavailable. Observe a
control that is denied read access in that same boundary; a changed collection
string alone is insufficient. Controlled internal faults supplement public
commands and actual writer signal/kill observations.

| Case | Independent required outcome |
| --- | --- |
| Known upright/tiny-angle/noisy/rigid, beyond-±7°, sideways/upside-down and blank fixtures | Construction supplies angle/orientation independently. Check status-zero/confidence-zero as unavailable, valid zero separately, and orientation-unverified retention until review. No unaccepted sampling; accepted rotation retains all regions/content against justified measured limits. Wrong page/orientation/angle controls must fail the corresponding oracle. |
| Input-relative import fidelity | Include >300-ppi detail, one-bit and grayscale compositions. Compare source full/native renders to the RGB baseline, expose downsampling/RGB changes and record resource costs. A known erased fine feature must fail preservation even if baseline/export bytes match. |
| Distinct boxes, `/Rotate` and UserUnit≠1 | Independent effective pixel/physical extents and orientation; show CropBox-hidden MediaBox material, extent-change reason, and reviewed/restorable CropBox crop. Wrong box/rotation/unit controls must fail. |
| Known curved/local-angle-variation fixtures | Global rotation/alignment cannot be credited as local correction; check regions independently so aggregate improvement hides no worsening. |
| Nonidentity fractional RGB sampling | Independent coordinate/sampler oracle, edge/canvas/colour/faint/music checks and native detail. Identity/copy is insufficient. Reject wrong angle/image/region/mapping controls for the stated mechanism first. |
| Known translated left/right page pair | Independent source anchors and declared sides predict common top/inner placement and mirrored margins. Retained native pixels, scale and all source content survive. Wrong side/anchor/offset/canvas controls must fail independently. |
| Covers/front matter/blank, missing page and duplicate-in-run sequence | PDF index differs from logical parity. Blank consumes a side; an explicitly marked repeat retains its earlier side without advancing parity. Chapter opener in a separate geometry group keeps its run side; groups may span runs. Wrong duplicate-parity control must fail; all images/order survive. |
| Different layouts, toned paper and unanchorable member | Preview white padding and any enlarged canvas, including retained borders/rotation fill. An unpositioned member retains its own canvas with an unresolved mismatch; manual placement joins the common canvas only after fit review. No borrowed frame, forced scale or clipping. |
| Any-page and group review | Real accepted edit, discard and revert on flagged and unflagged pages; matched full/native/pair/group views, partial resume, stale-action rejection and final accepted geometry. |
| Spread, tilted gutter and blank/duplicate halves | Independent known gutter/source labels exercise vertical overlap → per-half rotation → rotated-frame crop. Preserve own-page content, expose/crop or explicitly retain foreign material, verify every coordinate mapping and split replacement. Landscape single page stays single; all halves/default order remain. |
| Earlier OCR/text fixture | Visible source lettering survives full rendering; fresh output contains exact accepted images and no stale old selectable text. This is text omission, not OCR recognition/alignment acceptance. |
| All-nonzero multi-page review/export | Pending drafts block with 6; discard retains baseline/unresolved reasons. Missing/stale acknowledgement blocks with 6; current scoped acknowledgement exports exact baselines and recorded dispositions without accepting rotation or implying inspection. Explicit accepted rotation changes only its named revision. |
| Reference edit and member overflow | Re-edit a reference: every dependent placement/anchor is stale, unrelated groups byte-identical. Enlarge a member beyond the target: target review is required, with no clipping and no silent anchor transport. |
| Report and reimport | Validate named UTF-8 JSON attachment/version/snapshot fields and absence of output preparation hints. Reimport ordinary, metadata-stripped, unknown-version and reordered exports: fresh state, unknown sides and universal limitation, with no restored acceptance. |
| Server/security/dependencies | Normal Stop review is 0, Ctrl-C is 130; kill −9 then resume has no stale ownership/freeze. Shell export against review returns 4; live frozen commits return 6. Reject tokenless/foreign-Origin/wrong-Host actions and unconfirmed destination writes. Missing/incompatible tools give named remedy; version changes preserve accepted assets. |
| Failure/publication | Corrupt assets, target/reference invalidation, split replacement, lock conflict, interruption and occupied destination preserve committed review/originals/prior output. |

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
no missing acceptance. Full within-page and book-geometry acceptance still
precedes optional appearance and complete-product acceptance. Source-relative
preservation failures and unresolved numerical/visual judgments remain explicit;
neither default retention nor export acknowledgement waives them.

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

Review clarifications retain the signed fixed 300-dpi MediaBox RGB import,
explicit nonzero-rotation acceptance, geometry-only shell/browser controls,
preserved-scale alignment and the same public/full/native/pair/group seams.
They expose import/extent costs and unresolved outcomes, define coordinates,
parity/dispositions/dependencies, and specify report/server safety. Additional
fixture cases test those existing seams. The original reply is not represented
as a new signature or acceptance of these clarified limitations or real outputs.
