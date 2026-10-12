# Page and book geometry

**Design v2 geometry and finite baseline interface — agreed.** The replies and their scopes are
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

Start one book from the shell. The finite baseline workflow supplies ordinary-
viewer packets, saved reason/inspection records and acknowledged unchanged-image
export; browser review supplies the complete co-located page/book interface.
Both use the same project and resume without reopening the original collection.
The project saves partial review, geometry choices, page-side/group assignments
and accepted images as their supported operations become available.

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
ready event. The finite baseline workflow is a complete review/resume/export
interface; no importer-only handoff is offered. Each server start creates
an unguessable session token, supplied in its local URL and every action. Validate
the loopback Host and exact server Origin, reject tokenless/foreign-origin actions,
and serve no cross-origin state-changing endpoint. The browser export control
requires an explicit user-entered destination and confirmation; it never derives
a destination from the source or a remote request. Stop is authenticated too.

Browser review keeps exact identities, full/native comparisons and actions
together for supported page/book edits. The finite unchanged-baseline workflow
uses generated receipt-bound views and explicit shell actions. Its names remain
finite after browser support arrives; process/review are blocking from their
first release and never alias finite operations. The retained-name decision and
its trade-off are recorded in [finite-baseline-commands](../adr/finite-baseline-commands.md).
A native Mac app adds packaging/framework scope without changing this personal
shell workflow. The complete interface includes shell and local-browser review.

## Finite baseline review

The finite workflow imports/assesses one ordinary static sole PDF, exposes every
occurrence through matched full/native/source-native packets, records durable
unresolved review facts, resumes without its original and exports exact acknowledged
unchanged-baseline images. It introduces no orientation/crop/split/group edit state,
applies no estimate and implies no geometry or source-fidelity acceptance. Browser
completion retains the same project meanings and public export contract. The
following command, lifecycle, compatibility and test seams are agreed.
Review integration clarifies their existing meanings below. The human also
approved the three concrete public repairs under
[Integrated public protocol repairs](#integrated-public-protocol-repairs), with
that separate reply recorded under Agreement. They bind reason domains,
top-level result/help grammar and distinct single-use receipt issuance.

### Commands and user workflow

All baseline commands are noninteractive finite operations: no server, prompt,
pager or automatic application launch. They may take time to render/validate;
completion means return to the shell. `prepare` keeps its existing grammar,
help, finite schema version 1 and publication semantics unchanged.

| Command | Concrete behaviour |
| --- | --- |
| `bookscan baseline create PDF --workdir PROJECT` | Create an unused project, freeze/validate one sole static PDF, render every complete page and assess every occurrence. Commit one complete usable baseline checkpoint; print the project path. |
| `bookscan baseline status PROJECT` | Verify/resume the saved checkpoint without the original; print the complete ordered roster, limitations, dispositions and inspection scope. `--output DIR` also publishes a new summary packet for acknowledgement. |
| `bookscan baseline views PROJECT --page ID --output DIR` | Publish a comparison packet for one stable occurrence. `--all` replaces `--page` to publish every identity, never only flagged pages. Print the packet's index PDF path. |
| `bookscan baseline disposition PROJECT --receipt FILE --reason ID --decision reject\|retain-unresolved --note TEXT` | Record one reason disposition against the displayed image and review revision. Reject dismisses that assessment suggestion; it does not clear the underlying unverified limitation or change pixels. |
| `bookscan baseline inspected PROJECT --receipt FILE --scope full\|native\|source-native --viewer TEXT --scale TEXT --note TEXT` | Record actual inspection of the packet's specified page/view scope and the actual viewer/scale used. Native receipts name covered tile regions; full inspection is not full native inspection. Never infer this act from opening a file. |
| `bookscan baseline acknowledge PROJECT --receipt FILE --all\|--page ID --note TEXT` | A summary receipt displays the complete current export snapshot and all unresolved IDs/reasons, with inspection scope separately displayed. Explicitly acknowledge all identities or a named selection against that exact snapshot. Repeat `--page` for a selection. |
| `bookscan export PROJECT --output PDF` | Lock, verify, require a current acknowledgement, freeze the complete roster, rebuild/validate and publish one exact image-only PDF without overwrite. |

`--json` is available on all operations. On new top-level/baseline/export routes,
standalone `--help` before `--`, not consumed as an option value, has precedence
over other arguments, reads no input/project/dependency/cache and exits 0;
`--help --json` prints human help as the explicit JSON-result exception. Preparation
keeps its existing all-token help behaviour. An unknown subcommand without help
exits 2 with nearest valid examples. Paths with
spaces are quoted. Stable IDs returned by status/packets are accepted unchanged;
ordinal-only actions and manual hash assembly are unavailable. `--page`/`--all`
are mutually exclusive and one is required. A packet destination is an unused
directory in an existing parent, outside the project/source; no overwrite option.

The user starts with create, then status and the packet index in Preview or
another ordinary PDF viewer. The ordered roster links each occurrence's full
comparison, native tile index and any source-native material. Each packet prints
the exact disposition/inspection command with its receipt path; the user supplies
the decision/note. After decisions, status with `--output` creates a new summary
packet, showing inspected regions separately from unresolved/uninspected pages.
The user explicitly acknowledges that summary, then exports. An all-uninspected
book may be acknowledged, but the summary and report say so. Required product
fidelity checks and representative acceptance are independent of this choice.

Example shape (IDs are illustrative values returned by the working command):

```sh
bookscan baseline create 'Prepared book.pdf' --workdir 'Book project'
bookscan baseline views 'Book project' --page occ-000020 --output 'Page 20 views'
bookscan baseline disposition 'Book project' --receipt 'Page 20 views/receipts/full.json' --reason skew-nonzero --decision reject --note 'Retain this baseline; no rotation accepted'
bookscan baseline views 'Book project' --page occ-000020 --output 'Page 20 refreshed'
bookscan baseline inspected 'Book project' --receipt 'Page 20 refreshed/receipts/native-001.json' --scope native --viewer 'Viewer used' --scale '1:1 verified with supplied ruler' --note 'Inspected the labelled gutter region'
bookscan baseline status 'Book project' --output 'Export summary'
bookscan baseline acknowledge 'Book project' --receipt 'Export summary/receipt.json' --all --note 'Export unchanged pages with the displayed unresolved limitations'
bookscan export 'Book project' --output 'Baseline book.pdf' --json
```

After any action that changes review facts, regenerate the summary. A page packet
from an earlier review checkpoint must also be refreshed before a subsequent
action. This conservative rule adds packet refreshes; it prevents actions silently
using review facts that changed since display. The packet index offers a complete
native-view roster, not a selection of convenient crops. Inspecting one tile never
attributes inspection to its neighbours.

The refresh cost is per recorded action, across the whole project. For the
3591x2695 Norwegian baseline, 768-pixel tiling makes 20 regions. Recording them
separately needs 19 new page packets after the first; each contains the complete
roster, full comparison and 60 source/baseline/current native panels. After each
refresh, inspect the covered view actually named by the new receipt before
recording it. Prior viewing does not attest an unseen refreshed packet. An
`--all` packet similarly becomes stale after the first review-fact action on any
page. This is the signed conservative global-revision trade-off, with its cost
now explicit; no batching or per-page currency is approved. Actual navigation,
refresh cost and native usability still require F's demonstration. A failed
demonstration earns a scoped boundary question, not assumed usability.

Each receipt permits one normalized action request. An identical durable retry
is allowed; different operation/values on a used receipt return
`INVALID_RECEIPT`/6 with context `receipt-used`, without mutation. The remedy is
a newly issued view/summary receipt, not a claim that the snapshot changed.
For selection union, publish summary A and acknowledge the first selection;
publish summary B for the same unchanged snapshot and acknowledge the remaining
selection with B's receipt. Their saved scopes coexist. Every packet issuance,
including an unchanged summary, creates distinct opaque packet/receipt IDs as
specified under Integrated public protocol repairs.

### Matched packets and revision identity

Every packet has a version-1 manifest, all-page roster, PDF bookmarks/internal
links, immutable view receipts and complete asset digests. A single-page packet
includes its page plus the complete roster/limitations; `--all` adds every page's
views. Every visible page/tile header names project ID, source snapshot digest,
one-based source PDF page, occurrence ID, image revision, review revision, view
kind, box, region and sampling/display scale. Duplicates have different occurrence
IDs even if their decoded RGB asset is shared. Baseline and current are labelled
identical; there are no unused edited-image states.

Full comparisons put the saved source's MediaBox view, baseline and current at
the same physical frame and labelled display scale, with the effective original
CropBox boundary as a guide. Guides and headers live only in the packet, never in
exported pixels. Include a separate saved source PDF link, with explicit guidance
that an ordinary viewer may default to CropBox; do not call its zoom a 300-dpi
native comparison. Distinct/reversed boxes, Rotate and UserUnit apply to the
mapping, not a guessed raster bounding box. Source-render identity/settings are
recorded; the rendering used to present it is **not** the independent fidelity oracle.

Native packets partition the whole baseline pixel rectangle into labelled,
gap-free regions (maximum 768 by 768 pixels, edge tiles smaller). Each region has
adjacent source/baseline/current panels with the same mapping. At 100% *packet
view scale* each project pixel occupies one PDF display point; the header tells
the user to verify the pixel ruler and disable fit-to-page scaling. A PDF viewer's
percentage does not establish one framebuffer pixel per project pixel on a Retina
display. Also supply lossless PNG tiles and a pixel ruler for a viewer's actual
1:1 pixel mode. Native inspection must name the actual viewer/scale and regions;
until the implementation demonstrates true 1:1 presentation on this Mac, native
usability is unfinished acceptance, not asserted from the PDF's construction.

F's initial implementation hypothesis is lossless PNG tiles in Preview's
actual-size display, with PNG density derived from the measured display backing
scale rather than an assumed 72/96-dpi tag. This is a hypothesis to test, not a
verified Preview API/setting or a guarantee that metadata controls device pixels.
Use the supplied pixel ruler and an observed framebuffer measurement to verify
one device pixel per project pixel, on the actual display/viewer configuration;
record that configuration and the exact covered regions. If this mechanism fails,
record its measured scale and the specific missing viewer mechanism, then present
a scoped boundary question with a demonstrable ordinary-viewer alternative or
an explicit interface-change recommendation. Keep F live at that named blocker;
do not repeat unchanged trials indefinitely, weaken native meaning, retire it or
classify missing required native usability as pending human reaction.

Source-native panels preserve decoded contributing samples/masks with their own
effective horizontal/vertical ppi, placement, sample dimensions, colour metadata
and labelled source region. Show above-300-ppi detail separately without shrinking
it and calling it preserved. A composite/vector/colour region without validated
independent native truth is explicitly unavailable with its missing oracle, beside
the ordinary source/full views; it is never represented by the largest image alone.
No page becomes unsupported merely because its numerical fidelity truth is missing.

Receipts identify the packet, saved project, source/asset digests, occurrence,
displayed image/review revision, view kind and exact region coverage. Summary
receipts additionally name the ordered export-snapshot digest, unresolved roster
and inspection/disposition digest. The project stores an immutable content-
addressed packet descriptor, including receipt/header identities and file digests,
before external packet publication. Descriptors are presentation records outside
the review checkpoint: issuing them does not change review facts or invalidate
acknowledgement. A descriptor without a completely published matching packet is
unusable. Each issuance has a fresh opaque packet ID, including identical
views/summaries at one unchanged snapshot; receipt IDs bind that issuance and
coverage, and issuance identity is included in the content-addressed descriptor.
No request-key option or manual ID construction is exposed.
The owning command verifies the receipt and referenced packet files
against that project-owned descriptor and the current revision for a new action;
missing, tampered, foreign or stale receipts cannot mutate state. Receipts are
local identity evidence, not proof that a human inspected the view. The complete
unresolved export scope is always shown, even when a user records a narrower
inspection or a note about a named selection.

Receipt authenticity means the receipt JSON itself matches its immutable saved
descriptor and the owning project/source/receipt identity. After that check,
look up durable replay before checking current revision or external view files.
For a new action, verify every file digest listed in the packet descriptor,
including manifest, roster, receipts, PDFs and PNGs; a missing/changed file
returns `INVALID_RECEIPT`/6. Work from the immutable packet: Preview markup or
another viewer's autosave invalidates new actions; annotate a separate copy.
An authentic identical committed retry still returns its original result when
external views were edited/deleted or review facts advanced. Replay never records
new inspection or makes an old acknowledgement current.

### Saved states and transactional ownership

The project owns one immutable verified source PDF, content-addressed lossless
RGB baselines, per-occurrence geometry/analysis/provenance and immutable review
checkpoints. Occurrence IDs encode initial order within a separately identified
project; the image revision identifies its asset and physical mapping, the review
revision identifies current review facts, and the export-snapshot digest excludes
the acknowledgement itself. Checkpoint revision advances on every committed
action; review revision advances only on disposition/inspection/analysis/roster/
image changes. Acknowledgement binds the current review revision and snapshot
digest without changing either. Dispositions/inspection/analysis/roster/image
changes invalidate acknowledgement;
packet creation, status reads and exports do not. An identical repeated action
with the same receipt/values returns the original committed result; a conflicting
receipt reuse or stale uncommitted request returns 6. No new IDs or history are
inferred from the public report.

Acknowledgement requires exactly one scope form: --all or one/more --page IDs.
Each saved record names the exact same snapshot, selected IDs and their complete
unresolved reasons plus universal limitation and note. Several selection records
may cover one snapshot without invalidating one another. Export requires their
union to cover every exported identity's retained unresolved reasons and universal
limitation; a missing ID/reason returns ACKNOWLEDGEMENT_REQUIRED/6 with that scope.
The public version-1 acknowledgement object reports the effective complete scope
and separate inspection scope; an optional scopes array preserves individual
notes without changing required field meanings. Narrow inspection never supplies
missing export acknowledgement, and partial acknowledgement never drops pages.

The normalized request identity (operation, receipt ID and all supplied semantic
values) and its committed outcome are stored atomically with the resulting
checkpoint. Under the writer lock, check that durable retry record **before**
current-revision validation: an identical committed replay returns its original
result without mutation, even after restart or later review changes. Reuse of its
receipt with conflicting values returns INVALID_RECEIPT/6 (`receipt-used`);
an uncommitted request against a stale revision returns STALE_ACTION/6.
A kill before checkpoint commit leaves no successful retry
record. This ordering is part of the stale-action/retry acceptance seam.

Every command opening a project takes the same nonblocking kernel writer lock,
including verified reads/packet generation, to keep one snapshot coherent. A
busy project returns 4; ownership is the OS-held lock, never a PID/marker alone.
The lock pathname/inode is retained rather than deleted/recreated on Stop/death;
project arguments resolve to one canonical project identity, including a symlinked
parent such as `/tmp` and filesystem case aliases. They acquire the same lock;
output aliases and replaced internal lock/store entries are rejected. Require
open-file-description ownership: opening/closing another descriptor during an
identity check cannot release the owning lock. The owning descriptor is not
inherited by any renderer/helper child; caught signals terminate/reap owned
children before exit. A killed/reaped writer releases ownership even with an
orphan child still alive. The implementation must verify the actual native
mechanism on this Mac; no syscall is established by this design text.
After death and reap, another command can take ownership and verify the last
committed checkpoint. There is no permanent export freeze on disk.

Create first reserves an unused project directory; a competing creator cannot
replace it. It assembles in private names within that reservation. Publish all
snapshot/assets completely, verify digests/metadata/decodability, then commit the
initial checkpoint through one atomic current-checkpoint pointer change. Before
that commit, no baseline is saved. A caught failure removes only this run's owned
reservation/private names where safe; a kill may leave an identifiable incomplete
directory. Retrying create at an occupied directory returns 4; review/status says
`INVALID_PROJECT`/3 and recommends `bookscan baseline create PDF --workdir NEW`
with an intact supported input and a new unused directory,
without treating partially imported pages as saved or offering silent continuation.

Subsequent actions publish an immutable checkpoint only after its assets are
complete. A signal/failure before pointer commit leaves the preceding checkpoint
authoritative; after commit that new checkpoint is authoritative even if reporting
fails. Signals may wait for an indivisible native operation, then return 130/143
for create/actions/read operations, with a `committed` fact in the result when
deliverable. Unlike an exported PDF, a project checkpoint does not turn a signal
into a successful shell iteration. Already selected errors keep their exit.
SIGKILL may prevent reporting; verified status/resume reveals the committed state.
Private orphan assets are not referenced or promoted; cleanup touches only known
owned names, never indiscriminately all temporary files. No power-loss guarantee.

View/summary packets are built privately beside their unused destination and
become visible only by a no-replace atomic directory publication supported and
verified on this Mac/filesystem. Never use replacing rename or a file-by-file
visible copy. Unsupported directory publication returns 5; concurrent/occupied/
dangling destinations return 4. A packet published just before a project action
remains a complete but stale packet. Resume never consumes packet assets as state.

For views and status-with-output, the packet command's commit boundary is
successful atomic directory publication, not descriptor persistence. A descriptor
alone means committed false; complete publication means committed true even when
a later signal returns 130/143 or result delivery fails. Block/defer caught signals
only across the publication/outcome-recording region. Report packet publication
separately from review-checkpoint commitment; status without output commits nothing.

Export holds ownership throughout verification, freeze, image embedding, staged
validation and no-clobber link publication. It uses the exact acknowledged roster,
RGB and physical mapping; no source graph/text is copied. Validate decoded bytes,
dimensions/transform, count/order/IDs, exact Subject, version-1 report and absent
preparation hints. Unsupported halves/runs/groups/anchors/placements are explicit
null/empty, sides unknown. Keep the existing public report's meanings and optional
reader rules under the [handoff ADR](../adr/geometry-review-handoff.md).

Before the output link, cancellation returns 130/143 and preserves prior output;
link success is the publication commit. After it, cleanup/signals/result-delivery
failure retain complete `written`/0 with named warnings, as preparation already
does. A killed published output stays complete and occupied; inspect it before a
retry, which returns 4. Signal deferral around link/outcome recording is bounded.
Output aliases to source snapshot/assets/project and original source identity,
including path/case/symlink/hard-link aliases, are rejected before generic occupation.
The processor does not discover the collection to police it.

### Protocol, errors and help

Except for the explicit human-help exception, finite JSON stdout is exactly one
object: `schema` =
`BookScanBuilderCommandResult`, `schema_version` = 1, `operation`, `status`
(`created`, `verified`, `views-written`, `recorded`, `acknowledged`, `written`,
`error`), `exit_code`, nullable `project_id`, `review_revision`, `snapshot_id`, `output`,
`committed`, and `warnings`. Successful status includes the complete ordered
`pages` roster; other results return affected IDs/receipt paths rather than
repeating it. Errors add `code`, `message`, `remediation`, affected IDs and context.
Each warning has code/message/remediation. Signals use status error with the
committed fact; post-link export retains written. No stdout progress or prompts;
human diagnostics/progress are stderr. Serialize before delivery; delivery failure
is best-effort stderr, never rollback of a committed state or second JSON object.

Results also state `replayed` and `current_review_revision`. An identical durable
replay returns the historical operation result with replayed true and the current
revision separately, so delivery never suggests that an old acknowledgement is
still current; export independently validates current complete coverage.

| Exit | Codes and concrete remedy |
| --- | --- |
| 2 | `INVALID_ARGUMENT`, `COMMAND_UNAVAILABLE`: show valid syntax; process/review are unavailable until the browser extension, with baseline examples. |
| 3 | `SOURCE_NOT_FOUND`, `SOURCE_UNREADABLE`, `SOURCE_EMPTY`, `SOURCE_UNSUPPORTED`, `SOURCE_CHANGED`: identify path/feature/page and supply a stable supported static PDF. `INVALID_PROJECT`: name the missing/corrupt asset/checkpoint or unsupported format/capability. For reader incompatibility, name the installed compatible reader/version and `bookscan baseline status PROJECT` (or its advertised review command for edited state). For unverifiable saved content or incomplete create, use `bookscan baseline create PDF --workdir NEW` with an intact supported input; fresh import loses the old review facts. If neither an intact input nor a complete verifiable saved state exists, state that no recovery is available. Never recommend an unexposed command or hand-edited pointer. |
| 4 | `SOURCE_OUTPUT_COLLISION`, `PROJECT_OUTPUT_COLLISION`, `OUTPUT_EXISTS`, `OUTPUT_DIRECTORY_INVALID`, `PROJECT_EXISTS`, `PROJECT_BUSY`: choose an unused valid destination; inspect existing output; finish current finite operation or Stop the live browser and retry. |
| 5 | `DEPENDENCY_UNAVAILABLE`, `RENDER_FAILED`, `ASSESSMENT_FAILED`, `WRITE_FAILED`, `OUTPUT_INVALID`, `PUBLISH_FAILED`, `RESULT_DELIVERY_FAILED`: identify component/version/phase and actual setup or I/O remedy. Individual invalid estimator results are saved unavailable assessment, not ASSESSMENT_FAILED. |
| 6 | `INVALID_RECEIPT`, `STALE_ACTION`, `ACKNOWLEDGEMENT_REQUIRED`, `BASELINE_ONLY`, `REVIEW_REQUIRED`, `EXPORT_IN_PROGRESS`: refresh a packet/summary, acknowledge exact current state, or use browser review for an edited project; wait for live export. |
| 130/143 | `INTERRUPTED`: committed flag/phase and verify saved status or destination before retry. |

First-error order: invocation/help; input/private-format readability; lock; full
saved snapshot/assets and receipt/descriptor authenticity; durable retry lookup
(return identical committed outcome, reject conflicting receipt reuse); for a
new action, displayed-revision currency then complete external packet-file
integrity; source/dependency preflight when needed;
state/acknowledgement checks; destination aliases then occupation; processing,
checkpoint/publication; result delivery. Input PDF support precedes dependency
preflight; dependencies must pass before accepted import. Resume preflights
supported tool identities/protocol before review, but never regenerates accepted
pixels. Report missing helper/compiler/cache and use `process:setup`; no silent
compile at runtime. Version-aware packaged helper self-test includes sign,
status-zero/confidence-zero, nonfinite and known sentinel controls. Direct Pillow
pin and exact installed Poppler/Leptonica/Pillow/pikepdf checks remain implementation
work. API availability is verified against the actual selected versions then.
The exact top-level operation values, help exception and CommandResult evolution
rules are part of Integrated public protocol repairs below.

Help gives two ordinary/space-containing examples per operation, finite/blocking
semantics, exact exits/remedies, no input reads, unchanged-baseline/stage limits,
1:1 viewer instructions, saved versus inspected meaning, separate acknowledgement,
signal/kill/retry outcomes and no-clobber destinations. No `--force`, input
restriction, hidden headless mode or public fault flags are added.

### Private compatibility and browser command transition

Private header: format `BookScanBuilderProject`, format version 1, monotonic
checkpoint revision and required capabilities initially `baseline-rgb-v1`,
`assessment-v1`, `review-records-v1`, `snapshot-ack-v1`. Asset and manifest digests
are verified before use. These versions are distinct from report version 1,
packet/receipt version 1 and command-result version 1. Unknown required capability
or unsupported format fails INVALID_PROJECT/3 before modifying anything. Extra
optional data may be ignored only when explicitly declared nonsemantic; unknown
meaning cannot silently become acceptance.

The browser extension reads the frozen finite-project fixture unchanged. Merely
opening it adds no required capability and changes no image/ID/order/scale/review/
acknowledgement meaning. An additive upgrade publishes a new validated checkpoint,
retains the recoverable predecessor and never regenerates pixels; interrupted
upgrade resumes either complete version through a compatible reader's normal
verified status/review operation. A predecessor includes its full referenced
verified assets, not checkpoint metadata alone. Retention supports transactional
resume; it exposes no manual rollback/recover command or older-reader bypass of
capability checks. If the current state cannot verify, use the explicit compatible-
reader/new-import remedies above without modifying the damaged project.
Before a new semantic feature is used,
record its capability atomically with the new state; old readers fail actionably
rather than omit it. A baseline command encountering edited/split/group state
returns BASELINE_ONLY/6 before mutation; generic export handles supported current
state. An older installed reader with unsupported capabilities returns 3.

`baseline` names survive as an explicit unchanged-baseline workflow. This lasting
public surface is the cost of avoiding incompatible command reuse; browser support
owns its continued contract/regression acceptance. `export` remains finite and uses
the same result schema. `process PDF --workdir PROJECT` and `review PROJECT` are
reserved for blocking foreground servers from their first release. Before that,
they return COMMAND_UNAVAILABLE/2; they never alias finite create/status. At browser
release help names the two paths and shows Stop for shell loops. No implicit switch,
deprecation or version-dependent optional mode changes a command's duration.

Browser `--json` uses separate `BookScanBuilderReviewEvent`, schema version 1:
`event` (`ready`, `action-result`, `export-result`, `terminal`), run/session ID,
monotonic sequence, project/review/snapshot identity as applicable. Ready occurs
once, after complete import/assessment or verified resume, and supplies the local
URL and supported capabilities. Action-result names action/affected IDs and saved
revision/error; export-result embeds the finite command-result record and means
publication success/failure only. Terminal is last, names `stop`, `signal`, or
`error`, exit code and committed project state. It never means exported. Fatal
pre-ready failures have one terminal and no ready; SIGKILL/broken delivery can
truncate the stream. No additional progress vocabulary on stdout.

Browser action envelope version 1 names action (`disposition`, `inspected`,
`acknowledge`, `export`, `stop` initially), request ID and displayed project/review/
image identity, named reason/region/scope, note and destination/confirmation where
applicable. It uses the same state operation boundary as finite receipts, with
HTTP session authentication replacing receipt-file validation. Later supported
actions are additive, advertised in capabilities; unknown actions fail 2. Existing
fields and meanings never change within a schema version. Optional event/result
fields and advertised event types may be added only with explicit reader rules;
clients ignore unknown optional fields/types, but require terminal and never infer
success from an unknown record. A breaking protocol gets a new explicit supported
schema version and incompatible readers fail before mutation, not reinterpretation.

### Complete working browser extension

One complete subsequent working handoff owns any-page roster and matched full/
native/source-native inspection co-located with revision-scoped actions, saved
resume and acknowledged image-only export. Current remains baseline until an image-edit extension is explicitly supported.
The server binds loopback, holds the same kernel lock for its lifetime and creates
an unguessable per-session token. Validate exact bound loopback Host including port,
exact Origin and token for all mutations, including export/Stop; reject missing/
foreign values without mutation or server termination. No cross-origin mutation.
Serve only allowed project views, never arbitrary local files. The browser takes
an explicit destination and a separate confirmation naming that exact destination
and snapshot; it does not derive an output from source or a remote request.

Browser export retains server ownership and freezes actions until its separate
result. Commits during freeze return EXPORT_IN_PROGRESS/6; status can display that
state, with no mixed snapshot. Authenticated Stop queues behind the publication
outcome, then completes checkpoints, discards drafts if later supported and emits
terminal stop/0. Closing a tab changes no server state. SIGINT/SIGTERM exits 130/143
after safe cleanup regardless of an earlier export's separate written/0 outcome.
Kill/reap releases ownership; resume verifies the last checkpoint, treats private
exports as private and preserves complete occupied published output. No persistent
freeze, borrowed lock or unauthenticated Stop.

Its working acceptance includes real test-owned browser navigation/actions on
flagged and unflagged IDs, native-scale verification, Stop/tab closure/security,
live frozen actions/export/signals/kill/resume, predecessor-project read/upgrade,
and installed prepare -> process -> inspect/disposition/acknowledge/export -> Stop
-> review -> finite export under demonstrated collection-read denial. The finite
command contract is rerun at browser release; its old scripts still terminate.
Browser review is a complete working handoff before orientation edits; its acceptance cannot be postponed to an unrelated edit extension.

### Acceptance seams retained in the finite handoff

Highest public seam: the installed commands with real saved assets and ordinary
viewer navigation/scale observations. A single responsible operation boundary
accepts private substitutes for rendering, storage, publication and controlled
barriers; those faults supplement real tools/processes rather than exposing
transaction protocol to callers. Browser actions later drive that same boundary.
No new plugin framework, test-only product mode or source-study mechanism.

Before comparison outputs, declare an independent native/analytic truth manifest:
decoded contributing samples/masks/colour metadata and independently constructed
placements/boxes/Rotate/UserUnit. Exact grid-aligned unfiltered construction uses
exact pixels/channel values; misaligned grids require predeclared phase/coverage/
feature and colour bounds justified by the construction and conversion, not the
renderer output. Complex real regions lacking validated truth stay unavailable
with their precise missing oracle. Same-renderer source/baseline equality and exact
export bytes never pass source fidelity. Each oracle is observed rejecting the
wrong image/box/unit/CTM/placement/order/colour/erased-feature subject for that
mechanism, while unrelated checks remain green. Declare before generated outputs,
freeze all read subjects before/after, one writer, and compare reruns itemwise.

Required synthetic constructions include mixed vector/image/text, nested forms,
inline images, one-bit/grayscale/RGB, stencils/masks, static appearances, distinct
and reversed boxes, Rotate/UserUnit, aligned/misaligned <=300-ppi and >300-ppi fine
detail, blanks/duplicates/order and earlier selectable text. The analyzer accounts
for every contributing placement or records affected resolution unavailable, not
a <=300-ppi pass from a partial scan. Test baseline physical mapping and exact
lossless export/report/hints/fresh import; right-angle edits require their separate supported extension.

Installed writer-PID barriers observe asset-complete/checkpoint pre/post-commit,
packet pre/post-publication and export pre/post-link/cleanup/result delivery. Signal
and SIGKILL the actual installed writer, reap it, then verify source/prior output,
destination visibility and last committed state/lock ownership. Include source/
project/output path/case/symlink/hard-link aliases, replaced lock identity,
dangling/occupied/concurrently occupied destinations, unsupported no-replace/link,
corrupt/missing snapshot/assets, stale/tampered/foreign receipts, ack invalidation,
busy actions and additive upgrade interruption. Genuine EPIPE and cleanup failures
are distinct outcomes. Internal deterministic fault seams are not substitutes for
these actual installed-process observations.

The existing retry/lock/remedy seams include these counterexamples: an identical
committed action after later review changes and after external packet edits/deletion
replays, while a new action against altered views fails 6; conflicting receipt reuse
fails 6 without a checkpoint; two independently issued summaries cover one unchanged
snapshot by selection union with distinct issuance; summary/acknowledgement/
report/export results agree on snapshot identity; killed incomplete create and corrupt
shared assets give an executable new-import remedy with review-fact loss explicit.
Kill/reap the installed writer with a renderer/helper child alive and verify immediate
lock reacquisition; another lock-file descriptor's close cannot release ownership.
Open through a symlinked parent/case alias, then attempt internal entry replacement:
the first reaches the same project, the second is rejected. These exercise the
promised replay, exclusion, canonical identity and resume behaviours; they supply
no native API or product result here.

Installed preparation -> finite create -> actual packet inspection/navigation ->
disposition -> scoped inspection -> current acknowledgement -> saved resume after
original deletion/unavailability -> export is verified with collection reads
genuinely denied. Observe a denied-read control from that same boundary; setting
a different COLLECTION string is insufficient. Also use an ordinary unmarked
multi-page sole PDF. Help is tested with input/tool reads denied; JSON/exit/remedy,
packet header-to-receipt identity and exact native scale are checked at the public
surface. Missing required public/synthetic verification is unfinished work.

Keep six actual source/full/native/resource packets separately: Norwegian20 both
gutters (whole spread), Garbage Collection30 glyphs/indentation/boxes/arrows,
Counterpoint20 one landscape page/both columns, Fundamentals40 faint prose/music,
SchoenbergComposition cover1 colour/sparse rules and Algorithm Design20 already-
processed preservation. Each retains digests, commands/settings, dimensions/stored
bytes/export size/peak memory, native truth or exact missing truth, numerical
passed/failed-signed-resolution/failed-defect/unavailable and actual/pending scoped
human view paths/verbatim reactions. Required defects/public/synthetic failures
block completion of the supported technical handoff. An actual real signed-resolution
loss requires an immediate scoped human policy decision before dependent image edits.
Complete-default correction still owns missing real truth/reactions/defect remedies
and nonrigid acceptance before appearance and final acceptance. No export or design
agreement supplies a missing geometry, preparation or fine-detail result.

### Integrated public protocol repairs

**The human approved Q1–Q3 as written in the presented repair section.** Their
separate scoped reply and proposal digest are recorded under Agreement. These
bounded repairs retain permanent finite names, global review currency and the
finite-owner delivery exception, with no new workflow or recovery operation.

**Q1 — reason domains.** Use the following version-1 emitted reason IDs.
Reasons are scoped by occurrence; table entries are stable kinds, with recorded
measurement/warning/concern details and dispositions retained in status/packets/
report. No threshold or ranking is introduced.

| Reason ID | Meaning / emission | Finite decisions |
| --- | --- | --- |
| `skew-nonzero` | Valid advisory estimator result with exactly nonzero angle | `reject`, `retain-unresolved` |
| `assessment-unavailable` | Nonzero estimator status, zero confidence or nonfinite numeric output | `retain-unresolved` |
| `orientation-unverified` | Every occurrence; no finite operation here can clear it | `retain-unresolved` |
| `import-fidelity` | Above-300-ppi contributing detail, unavailable complete resolution analysis or recorded source-detail/colour concern | `retain-unresolved` |
| `extent-change` | Effective MediaBox and CropBox display regions differ | `retain-unresolved` |
| `skew-range-edge` | Recorded estimator sweep-edge warning; keep the configured sweep/settings | `retain-unresolved` |
| `decoder-warning` | A supported import's recorded PDF/decoder warning | `retain-unresolved` |
| `canvas-warning` | A recorded unexpected-canvas warning; no new size threshold | `retain-unresolved` |

Reject dismisses only the `skew-nonzero` suggestion. It removes that suggestion
from retained-unresolved coverage but never removes universal/orientation/fidelity/
extent/other limitation coverage or implies corrected pixels. `retain-unresolved`
keeps the reason and note in export coverage. A decision outside the named reason's
domain, or an unknown/absent reason, returns `INVALID_ARGUMENT`/2 with the reason,
allowed decisions and exact valid command, before any checkpoint. Record new
observations in retained-unresolved notes on a named current limitation; this
finite grammar adds no arbitrary reason-creation operation. Check: attempts to
reject extent/orientation/import-fidelity/assessment-unavailable fail without
state change; the next summary/acknowledgement/report still includes them.
Allowing reject labels on limitations while keeping their unresolved export
coverage was rejected because the label would obscure what remains unverified.

**Q2 — top-level result/help grammar.** Use CommandResult version 1 for
top-level/unknown-command and pre-browser COMMAND_UNAVAILABLE errors under
`--json`; `operation` is null there. Recognised finite operations use exactly
`baseline.create`, `baseline.status`, `baseline.views`, `baseline.disposition`,
`baseline.inspected`, `baseline.acknowledge` and `export`, including their own
argument errors. Those records include `exit_code`; unavailable identity/output
fields are null, `committed` and `replayed` are false for invocation errors,
`current_review_revision` is null, and `warnings` is an array. Successful operations
retain the existing result/status fields and errors retain code/message/remediation.
Preparation keeps its unchanged version-1 record without `schema` and is routed
to its unchanged parser/help only after explicit `prepare` selection.

For the new top-level/baseline/export grammar, recognise help only as a standalone
`--help` token not consumed as an option value and before `--`; a note/viewer/scale
value equal to `--help` is data. Help reads nothing and exits 0. `--help --json`
prints human help to stdout as an explicit exception to the one-JSON-result rule;
no new help schema/status. Preparation keeps its existing all-token help behaviour.
Recognise `--json` by the same standalone-option rule on new routes. Version-1
CommandResult statuses remain the seven listed values; new error codes may be
added only inside the existing exit classes, and readers use `exit_code` when an
error code is unknown, never infer success from an unknown status. Optional fields
may be ignored; changed required meanings/statuses require a new explicit schema
version. The alternative is to retain all-token help and define a separate JSON
help record, but that makes literal note values surprising and adds another schema.
The approved rule is standalone-token help with human output, including under
`--help --json`, on the new routes.

Check the installed new routes for `bookscan --json bseline status P`, unavailable
`bookscan --json process X --workdir Y`, `--help --json` with denied input/tool reads,
and a valid receipt action with `--note '--help'`; the last records that note rather
than showing help. Rerun preparation's existing help/result cases unchanged.

**Q3 — distinct issuance with single-use receipts.** Issue a fresh opaque
packet issuance ID at each views/status-with-output publication, even for identical
project/review/snapshot content. Each immutable receipt ID binds that issuance
and its view/summary coverage. The content-addressed descriptor includes issuance
identity, so independently issued unchanged summaries do not collide. No manual
ID construction, new request-key option, batch action or currency exception.
Reusing receipt A with a different selection is INVALID_RECEIPT/6 (`receipt-used`);
publish summary B and use its new receipt. Identical replay with A returns its
old result before currency/external-file checks. Check two commands covering one
snapshot with independently issued receipts and reject a conflicting reuse without
a checkpoint. The alternative is to make reuse legal for different normalized
requests, changing the conflicting-receipt rule. The approved repair preserves
single-use with explicit distinct issuance.

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
concern remains unresolved in the finite baseline handoff: rejecting an estimator
suggestion or recording inspection/acknowledgement does not dispose of it. Only
the later supported reviewed/restorable crop addresses extent, and independent
source-fidelity evidence/remedy addresses import fidelity; neither grants a
preservation-test pass by disposition. The approved finite reason-domain grammar
is specified in Q1 above. An export acknowledgement cannot turn a degraded
import into a preservation-test pass.
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
| Asset/snapshot mismatch | Stop the affected operation. Name the missing/corrupt item and the compatible-reader or explicit new-import command/remedy above; fresh import loses review facts. No command restores missing bytes from checkpoint metadata. |
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
| `source_sha256`, `snapshot_id` | Input source snapshot digest and the exact acknowledged export-snapshot digest, excluding acknowledgement/retry/checkpoint metadata. The latter is identical in the summary receipt, effective acknowledgement, report and export result; it is neither image, review nor checkpoint revision. No collection path is required. |
| `limitation`, `toolchain` | Universal limitation text; renderer/estimator/sampler/library versions and render/analysis settings. |
| `pages` | Array in exported order; every entry has stable `id`, one-based `source_pdf_page`, nullable `half`, baseline `source_region`, `image_revision`, decoded `image_sha256`, pixel/physical canvas dimensions, page-edit mappings, nullable geometry-group/run IDs, side/repeat/anchors/reference/target/placement records, triage reasons and their dispositions. No acceptance is inferred from absent fields. |
| `acknowledgement` | The same export-snapshot digest as report `snapshot_id`, affected unresolved IDs/reasons and explicit acknowledgement, with inspection scope recorded separately. |

`review_revision` is not a required version-1 report field. If included as an
optional audit field, it names review facts separately and never substitutes for
the export-snapshot digest. Saved checkpoint advances on acknowledgement/retry
bookkeeping cannot change that digest or invalidate another same-snapshot scope.

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

### Finite baseline interface and test seams

The human replied verbatim **“yes”** to approval of the presented finite
interface/test-seam proposal and the separate delivery-cadence exception for its
complete finite implementation owner. The presented proposal SHA-256 was
`84658bf583232bada49d72b88407e05cd18323219a647c8f8ee1119fc45ce3fa`,
at `http://127.0.0.1:8772/baseline-delivery.html#current-decision`, with the
delivery diagram at `http://127.0.0.1:8772/#diagram-baseline-delivery`.
The finite contract is incorporated into this current spec without a second
parallel proposal. Agreement covers permanent finite baseline names, exact
packet/receipt revision identity, separate inspection/dispositions/scoped
acknowledgement, checkpoint/lock/signal/publication lifecycle, private-project
and public-protocol compatibility, browser completion and the retained
independent/public/fault/six-case seams. The finite owner may span sessions,
retaining every required check and retiring only on complete delivery; that
cadence permission supplies no corresponding browser-owner exception or scope
waiver. Delivery ownership remains in the task briefs. This reply grants no
product, native-view fidelity, geometry or preparation visual acceptance.

Review integration exposes the signed global refresh cost and clarifies replay/
receipt reuse, executable resume/new-import remedies, report identity and kernel
ownership/native-display obligations. The human separately replied verbatim
**"Approve Q1–Q3 as written (Recommended)"** to the concrete public repairs:
Q1 reason IDs and finite decision domains with disallowed choices exiting 2;
Q2 top-level CommandResult/standalone help parsing/human help under `--help --json`
with unchanged preparation; Q3 distinct single-use packet/receipt issuance for
same-snapshot selection acknowledgement union. The exact presented section was
SHA-256 `445778df14127d9c7ae7fcc1834c12047ddec9d7cb96d803cde30d1345d86da2`,
at `http://127.0.0.1:8773/contract.html#open-integration-questions`, now incorporated
under Integrated public protocol repairs. This reply approves those public
details, not a product/native-view/fidelity/geometry/preparation result or a change
to the already agreed global refresh rule and finite-only cadence exception.

### Geometry Design v2

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
