# Prepared PDF

## Problem

A book's content and cover scans may be in several source PDFs. Preparation
must assemble the user's chosen PDF pages into one ordinary PDF before any
geometry correction or OCR exists. The source page is the preservation unit:
one scanned music page can contain an image and a separate stencil, while a
landscape page can contain either a spread or one book page on a larger canvas.

This design implements the confirmed preparation/processing boundary and the
agreed public-command test seam. Its visual companion is
[Assembly → Explicit roles become one prepared PDF](../design/prepared-pdf/README.md).
The copying evidence and exact real-source identifiers are in
[the dependency experiment](../research/prepared-pdf-copy.md).

## Assembly and handoff

The single-book entry point is **`bookscan prepare`**. It accepts only explicit
source PDF paths and selections. It does not discover collection files.
It produces exactly one prepared PDF. Assembly order is:

1. All front selections, in the order front arguments were supplied.
2. All content selections, in the order content arguments were supplied.
3. All back selections, in the order back arguments were supplied.

Each selection retains its resolved PDF-page order. At least one content
selection and one selected content page are required. Front/back selections
are optional and may contain several pages or sources. Grouping by role applies
regardless of where those role arguments appear on the command line. Printed
page numbers, filenames, folder membership and cover page counts decide no role.

To insert an interior cover page, select it as content between the desired
content selections. To move pages between source PDFs, repeat content selections
in the intended order. Unselected pages are omitted by the user's explicit
selection. Repeated selections deliberately create repeated pages; there is no
implicit deduplication, blank removal, or spread detection.

An already-assembled PDF is valid with one content selection and no covers.
With no explicit page expression, every PDF page is copied in its existing
order. A content selection can contain cover images without role metadata;
the later processor must accept that PDF.

## Command contract

Each repeatable `--content`, `--front` or `--back` argument takes a path and
optionally a page expression. One or two values belong to that argument until
the next option; more values are an error. Paths with spaces must be quoted.
Use an absolute path or a `./` prefix for a filename beginning with `-`.
There are no positional inputs. `--output PATH` is required and names a new
PDF in an existing directory. Standard input/output PDF streams are deferred:
a seekable output file makes complete validation and safe publication possible.

| Option | Behaviour |
| --- | --- |
| `--content PDF [PAGES]` | Repeatable content selection; default all pages. |
| `--front PDF [PAGES]` | Repeatable explicitly assigned front selection. |
| `--back PDF [PAGES]` | Repeatable explicitly assigned back selection. |
| `--output PDF` | Required new destination; no overwrite option. |
| `--dry-run` | Run all source preservation checks and destination preconditions; report the complete resolved order; write no PDF or temporary file. |
| `--json` | Emit one versioned JSON result on stdout, including structured errors. |
| `--help` | Explain role grouping, page grammar, failure/retry behaviour and common examples; exit 0 without opening inputs. |

Examples of the installed public interface:

```sh
bookscan prepare --content 'Book.pdf' --output 'Prepared.pdf'
bookscan prepare --front 'Covers.pdf' 1 --content 'Book.pdf' 'all,!3,!9-10' --back 'Covers.pdf' 4 --output 'Prepared.pdf'
bookscan prepare --front 'Covers.pdf' 1 --content 'Book.pdf' 2 --content 'Covers.pdf' 3 --content 'Book.pdf' 1 --back 'Covers.pdf' 4 --output 'Prepared.pdf' --dry-run --json
```

The last example resolves to cover 1, book 2, cover 3, book 1, cover 4.
Cover 2 is intentionally omitted. No role is inferred for cover 3: the caller
explicitly chooses it as content.

### Page expressions

Numbers are one-based **PDF pages**, not printed labels. Tokens are comma
separated, with no whitespace. A positive token is `all`, an integer `N`, or
an inclusive `A-B` range; ascending and descending ranges are allowed.
Positive tokens expand left to right, including repetitions. Exclusion tokens
are `!N` or `!A-B`; their union removes every occurrence of those pages after
the positive sequence has been expanded. With exclusions only, the initial
sequence is all pages. Omitting PAGES is equivalent to `all`.

For a six-page source, `6-4,1,4,!5` resolves to `6,4,1,4`; `!2,!5-6` resolves
to `1,3,4`. Exclusions do not authorize removal from any other selection.
Single-quote expressions containing `!`, for example `'all,!3'`. Double quotes
do not suppress history expansion in interactive zsh or bash. Include this rule
in `--help`; zsh documents it in [history expansion](https://zsh.sourceforge.io/Doc/Release/Expansion.html#History-Expansion).

Empty expressions/tokens, zero, negative or non-integer numbers, open-ended
ranges, `!all`, out-of-bounds endpoints (including exclusions), and a selection
resolving to zero pages are errors. The command never silently clamps ranges.
Remove an unwanted entire selection argument rather than supplying an empty one.

The user confirmed this grammar during `prepared-pdf-k12`: retain single-quoted
`!` exclusions and ascending/descending ranges. `prepared-pdf-k10` can plan
against these expressions without a further public-syntax decision.

### Output and errors

Normal success prints only the absolute destination path and newline on stdout.
A human dry-run prints the numbered resolved order and total. Diagnostics go
to stderr; there are no prompts, pagers, colour requirements or progress spinners.
Shell loops use the exit code and quoted paths.

In JSON mode stdout contains exactly one object, with `schema_version: 1`,
`status` (`planned`, `written` or `error`), and the absolute `output` when it
can be resolved. Successful records include `page_count`; planned records also
include the complete `pages` array, without truncation. Each planned item has
`output_page`, `source` (absolute explicit input path), `source_page` and `role`
(`front`, `content`, `back`). Written records do not repeat that large array.
Errors include `code`, `message`, `remediation`, and relevant source/selection
context. Results include a `warnings` array (empty normally), whose items have
`code`, `message` and `remediation`. Never mix a human result into JSON stdout.
A traceback is not a normal diagnostic. Recognize a standalone `--json` token
before full argument parsing, so invocation failures use JSON too. `--help`
as a standalone token takes precedence over other arguments and uses human
help without opening inputs. Neither an uncatchable kill nor a broken stdout
can promise delivery of a result object.

| Exit | Meaning | Complete stable error codes |
| --- | --- | --- |
| 0 | Valid plan or complete published PDF | — |
| 2 | Invocation or page selection error | `INVALID_ARGUMENT`, `INVALID_SELECTION`, `PAGE_OUT_OF_RANGE`, `EMPTY_SELECTION`, `CONTENT_REQUIRED` |
| 3 | Unreadable, unsupported, empty or changing source | `SOURCE_NOT_FOUND`, `SOURCE_UNREADABLE`, `SOURCE_EMPTY`, `SOURCE_UNSUPPORTED`, `SOURCE_CHANGED` |
| 4 | Destination precondition/collision | `SOURCE_OUTPUT_COLLISION`, `OUTPUT_EXISTS`, `OUTPUT_DIRECTORY_INVALID` |
| 5 | Copy, validation or output I/O failure | `COPY_FAILED`, `OUTPUT_INVALID`, `WRITE_FAILED`, `PUBLISH_FAILED`, `RESULT_DELIVERY_FAILED` |
| 130 / 143 | Caught interrupt / termination before publication | `INTERRUPTED` |

`INVALID_ARGUMENT` covers unknown options, missing option values or output,
extra values/positionals, and repeated singleton options (`--output`,
`--dry-run`, `--json`). No content arguments is `CONTENT_REQUIRED`.
Malformed page tokens are `INVALID_SELECTION`; a valid token outside the source
page count is `PAGE_OUT_OF_RANGE`; a valid expression excluding everything is
`EMPTY_SELECTION`. A zero-page PDF is `SOURCE_EMPTY`. Encryption, malformed PDF
syntax, recovery requirements, preservation gates and source parser warnings
are `SOURCE_UNSUPPORTED`; filesystem read failures are `SOURCE_UNREADABLE`.
`SOURCE_CHANGED` covers identity, metadata or digest disagreement.

Report the first error only, using this phase order:

1. Parse invocation/arity left to right, then check missing output before missing
   content. This fixes precedence even when neither required argument is present.
2. Check all page-expression token syntax without opening sources.
3. Open/hash distinct sources in their first command-line occurrence order;
   check readability, nonzero count and document gates.
4. Resolve bounds/exclusions in command-line selection order, then traverse and
   gate selected pages in resolved front/content/back output order.
5. Check destination parent/type and source identities; source collision wins
   over occupied destination regardless of input order.
6. Copy/save, validate the staged output, recheck source stability, then publish.

Within a phase use argument order, page order, then sorted PDF dictionary keys
for reproducible first-error context. A syntax error therefore precedes a missing
source, which precedes an occupied output. A nonexistent/non-directory parent is
`OUTPUT_DIRECTORY_INVALID`; a parent permission failure when creating the private
file is `WRITE_FAILED`. Destination occupation found initially or at `link()` is
`OUTPUT_EXISTS` (exit 4); other link failures are `PUBLISH_FAILED` (exit 5).
Copy-adapter failures are `COPY_FAILED`; reopen/representation mismatches are
`OUTPUT_INVALID`; temporary-file creation/save/flush/fsync/mode failures are
`WRITE_FAILED`. Failure to emit/flush a dry-run result is
`RESULT_DELIVERY_FAILED`/5, with best-effort stderr and no PDF; after publication
the same code is a warning with exit 0. Failed delivery of an existing error
retains that original exit code. These codes do not depend on library exception wording.

Dry-run executes phases 1–5, including source hashes, every gate below and raw
stream traversal for lazy parser warnings, followed by the same source stability
recheck. It performs no copy, save, runtime output validation or write-permission
trial. `planned` means those checks passed for the observed sources/destination;
it is no reservation or promise that a subsequent write will succeed. With
stable sources, write adds only copy/save/validation/publication and filesystem
I/O failures. Explain both its cost and that limit in help.

For an invalid selection, name the input, expression and invalid token.
Token-syntax errors precede opening sources, so describe the expected grammar
and mark page count unavailable; range/resolution errors include the opened
source's page count and suggest a valid range. Missing/unreadable sources name the path
and remedy. Unsupported rendering features name the feature and ask for a
static-page PDF produced separately for inspection; preparation never silently
flattens or repairs it. Existing-output errors suggest inspecting that PDF or
choosing a new destination. There is no automatic retry. After any ambiguous
interruption, inspect the destination: a retry against an existing file fails
without changing it.

## Preservation contract

For accepted sources, copy complete selected PDF pages into a new document:
all drawing streams and reachable resources, raster images and masks, fonts,
vector drawing, colour spaces, transparency and existing text remain associated
with the same page. Retain effective MediaBox, CropBox, other page boxes,
rotation and UserUnit, including inherited attributes. Preparation neither
renders pages into replacement images nor resamples/re-encodes their images.
It does not crop scanner borders, split spreads, warp geometry, clean appearance,
add OCR, or replace existing text. The same selected page may appear more than
once with independently assigned role dictionaries.

Preservation means unchanged full-page visible appearance and canvas at matched
render settings, not byte-identical PDFs or stable object numbers. Save settings
must leave content normalization and lossy image optimization off; preserve
existing stream encoding with decode level `none`, compression disabled and
Flate recompression disabled. The effective source version is the numeric maximum
of the file header and catalog `/Version` (when present), not pikepdf's header-only
`pdf_version` property. Use at least the highest effective version of all explicit
sources. Version syntax is `major.minor`, compared as two integers. This bounded
increment accepts PDF 1.0–1.7; newer versions require a support extension.
Carry accepted `/Extensions` declarations and assert their presence on reopen.
For each prefix choose the numeric maximum `(BaseVersion major, minor,
ExtensionLevel)`; equal pairs must have identical remaining dictionary entries.
The supported declaration is `/ADBE` with `/BaseVersion /1.7`, integer
`/ExtensionLevel` 1–3, and no other entries. Other prefixes/levels, malformed
declarations and array-valued entries are `SOURCE_UNSUPPORTED`. This deliberately
bounds extension support rather than claiming PDF 2.0 extension reconciliation.
Algorithm Design's ADBE 1.7/3 is an explicit acceptance assertion.
Pass the accepted ADBE extension level in pikepdf's `min_version=(version, level)`
save control; assigning `/Extensions` alone is insufficient because the pinned
writer removes that declaration when given only a version string.
Do not remove drawing resources as an optimization in this first increment.

The first supported domain is static book/cover PDF pages. The fresh document
does not promise source bookmarks, printed page labels, tags/accessibility
structure, attachments, forms, scripts, signatures, archival conformance or
document metadata. These are not substitutes for visible-page fidelity.
Drop copied structure-parent markers when their document structure is not
transferred; do not claim that a reordered assembly remains a tagged PDF.

### Source preservation gates

The following tables are the gate, not a heuristic about whether a feature seems
uncertain. Apply them identically to dry-run and write. They describe passive
static page rendering under ISO 32000-1; executing actions and interactive viewer
states are outside the supported domain. A fresh catalog contains `/Type`,
`/Pages`, the chosen version/extension declarations and writer-required entries.

| Document feature | Outcome |
| --- | --- |
| Encryption, including an empty password; malformed syntax or recovery requirement | Reject. Open with `attempt_recovery=False`; no repair/recovery fallback. |
| `/Type`, `/Pages` | Require a valid catalog/page tree and at least one PDF page; construct a fresh destination tree. |
| `/Version`, `/Extensions` | Validate and carry according to the version rule above. |
| `/OCProperties`, `/OutputIntents`, or `/NeedsRendering true` | Reject, even when page-copying otherwise succeeds. |
| `/AcroForm` | Accept only a dictionary with an empty `/Fields` array, no `/XFA`, and no true `/NeedAppearances`; omit it from the fresh catalog. Missing `/Fields` or a wrong type is rejected. |
| Every other catalog key | Omit; these provide no required passive page rendering in the supported standard subset. This includes `/PageList`, `/PieceInfo`, `/StructTreeRoot`, `/OpenAction`, `/AA`, `/Names`, `/Outlines`, `/PageLabels`, `/ViewerPreferences`, `/Metadata` and attachment/navigation/signature metadata. Private viewer behaviours are not supported. |

| Selected page / reachable feature | Outcome |
| --- | --- |
| Effective `/Resources`, `/MediaBox`, `/CropBox`, `/Rotate` | Materialize inherited values on the copied page. Only these attributes inherit. |
| `/BleedBox`, `/TrimBox`, `/ArtBox`, `/UserUnit` | Retain page-local values; defaults are CropBox for each optional box, 1 for UserUnit. |
| `/Contents`, `/Group`, `/BoxColorInfo` | Preserve their complete embedded object graphs. Ordinary drawing resources include nested Form/Image XObjects, masks, fonts, colour spaces, patterns, shadings, transparency and decoder resources. |
| `/Annots` | Apply the annotation rules below. |
| `/Parent`, `/Type` | Rebuild for the destination page tree; type remains `/Page`. |
| `/StructParents`, `/Metadata`, `/PieceInfo`, `/LastModified`, `/Thumb`, `/B`, `/Dur`, `/Trans`, `/AA`, `/Tabs`, `/PresSteps`, `/VP`, `/AF`, `/ID`, `/PZ`, `/TemplateInstantiated`, old `/BookScanBuilder`, and other private page keys | Omit. None is a drawing/canvas dependency in this supported passive-page contract; thumbnail, presentation, viewport, actions, tags and product-private data are not transferred. |
| `/SeparationInfo`, page `/OutputIntents`, or any other standard page key not classified above | Reject. A standard rendering feature cannot silently fall into the private-key rule. The implementation uses the ISO 32000-1 page-key table, not a guessed allowlist of collection keys. |
| Stream `/F`, `/FFilter`, `/FDecodeParms`, XObject `/Ref`, `/OPI`, or `/OC` anywhere in the retained rendering graph | Reject external stream data, reference/alternate external rendering, and optional-content dependencies. Read stream bytes only after checking these keys. |
| References to a different `/Type /Page` in the retained graph; form/widget/media annotations | Reject; copying must not depend on an unselected page or document interaction. |
| Other objects/keys inside supported embedded drawing resources | Retain and compare recursively. This is whole-object copying, not reinterpreting drawing operators. Drop `/StructParent` from rendering dictionaries when its parent structure is omitted. |

An accepted annotation is either a static markup (`/Stamp`, `/FreeText`, `/Line`,
`/Square`, `/Circle`, `/Polygon`, `/PolyLine`, `/Ink`, `/Highlight`, `/Underline`,
`/Squiggly`, `/StrikeOut`) with `/AP /N` a single Form XObject stream, or an
invisible `/Link` as defined here. Static appearances require their own embedded
`/Resources` dictionary, valid `/BBox`/optional `/Matrix`, and the same reachable
object gates as page drawing. Reject appearance-state dictionaries, `/AP /R`
or `/D`, `/AS`, optional content, actions, popups/reply relationships and other
annotation subtypes. Preserve static annotation drawing dictionaries and flags;
give each annotation one owning output page and update an existing `/P` to that
page. An invisible link has no `/AP`, explicit `/Border [0 0 0]`, and absent
`/BS` or an explicit zero `/BS /W`; remove that annotation because navigation
is outside the contract. A border-bearing or default-border link is rejected.
Reject any selection plan that repeats an annotated source page, even an
invisible-link-only page; cloning repeated annotations is deferred.

Any qpdf warning from source opening or traversal is `SOURCE_UNSUPPORTED`.
Traverse every dictionary/array and read every raw stream in the retained graph,
including nested resources and `/DecodeParms /JBIG2Globals`; use a visited set
for cycles. Inspect catalog gates and annotation entries before projecting out
discarded keys. Do not use `check_pdf_syntax()` as the warning gate: it tries to
decode streams and can report missing JBIG2 decoder support, which is different
from a warning during lossless raw traversal. Any output reopen/traversal warning
is `OUTPUT_INVALID`; a save/copy warning before reopen is `COPY_FAILED`.
The [pikepdf syntax-check API](https://pikepdf.readthedocs.io/en/stable/api/main.html#pikepdf.Pdf.check_pdf_syntax)
states that distinction. The experiment's bounded evidence does not establish
support for every combination of these accepted features.

## Embedded page roles

The persisted hint-container decision and rejected alternatives are recorded in
[prepared-page-hints](../adr/prepared-page-hints.md).
The preparation command writes a fresh private `/BookScanBuilder` dictionary on
each **destination page**. Version 1 contains `/Version` (integer 1), `/Role`
(PDF text string `front`, `content` or `back`), `/SourceSHA256` (64 lowercase hex
characters identifying the immediate source bytes), and `/SourcePage` (positive
one-based PDF page integer). It includes no required filename, collection path
or external identifier. Assign a new dictionary to each copied page; never
mutate a nested dictionary shared with a source or another occurrence.
Explicit arguments replace any older preparation marker on that destination
page. Provenance describes this assembly, not a full transformation history.

These markers are inert hints for a later processor and travel inside the PDF.
`content` means only "not explicitly selected as front or back in this assembly".
It conveys no cover/book-page classification, including for interior covers or
already-assembled input. All roles describe selections, not detected page types.
No mandatory sidecar exists. Ordinary PDF readers can display the prepared PDF
without knowing the marker. The processor must accept ordinary unmarked PDFs,
treat absent/unknown/malformed markers as unavailable hints, and never reopen a
source by digest or path. Moving a page with its dictionary moves its role;
third-party tools may discard private data. Hints do not exempt covers or
previously processed content from geometry assessment or later review.
Post-split book-page order and exclusions remain the processor's responsibility.
This does not choose the processor's correction, OCR or review implementation.

## Originals and output publication

Sources are opened read-only and never saved back. Before writing, resolve all
paths, expand and validate every selection, check destination parent/type, and
compare the destination against every input's canonical path and filesystem
identity. Reject same-path, symlink, hard-link and case aliases to a source.
Reject any existing destination entry, including dangling symlinks and
directories. A source collision takes precedence over a generic exists error.
Compute each distinct source's SHA-256 once before copying and again before
publication; also check file identity/size/modification metadata and the path's
identity. A changed source aborts the assembly. No exclusive lock against other
programs is promised; callers keep sources stable during the operation.

Create a private `.bookscan-prepare-<random>.tmp` file in the destination
directory, with `O_CREAT|O_EXCL`, mode 0600 and an unpredictable per-run name.
It is dot-prefixed and has no `.pdf` suffix, so `*.pdf` loops do not ingest
interrupted work. Pass its seekable binary file object to pikepdf; never save by
path or let pikepdf create a second temporary file. The publication adapter
returns a staged handle owning that stream, name and destination. The operation
asks the copy adapter to validate the staged stream (below), then asks the
publication adapter to commit it; callers never manage that protocol.

After validation and the source stability recheck, flush, set the intended final
mode `0666 & ~startup_umask` with `fchmod`, and fsync the completed file. Failure
of any step is `WRITE_FAILED` before publication. At publication use an atomic
**no-clobber** link
from the temporary file to the requested destination; link success is the
commit point. This handles another process creating the output between the
initial existence check and publication. Never use a replacing rename, truncate
the destination or fall back to a non-atomic copy.

On this Mac, block/defer SIGINT and SIGTERM across the final pending-cancellation
check, `link()` and recording its successful return as committed. Restore signal
delivery only after that state is recorded. A signal pending before this region
aborts; a signal arriving inside it is handled after the link outcome is known.
This closes Python's between-bytecodes interruption window. The blocking region
is short and includes no copying, hashing or fsync.

Before the commit point, any caught write/copy/validation/cancellation error
attempts to remove only this run's temporary file and leaves the destination
absent or its
previous occupant unchanged. A hard kill may leave an identifiable private
temporary file, which a later run must not indiscriminately delete. After a
successful link, remove the temporary name; cleanup failure is a warning about
an extra name for a complete file. If pre-commit cleanup also fails, retain the
original error/exit and add `TEMP_CLEANUP_FAILED` with the exact temporary path.
After the commit point the result is always `written`, exit 0. A caught signal,
temporary-name cleanup failure or stdout write/flush failure is respectively
`POST_COMMIT_SIGNAL`, `TEMP_CLEANUP_FAILED` or `RESULT_DELIVERY_FAILED` in
`warnings` and best-effort stderr. Signals in this phase do not raise a pre-commit
cancellation. A failed stdout cannot deliver its own warning in JSON; keep exit
0 and try stderr rather than claim `INTERRUPTED` or `WRITE_FAILED`. Fully serialize
the result before emitting it; a broken pipe can still truncate delivery.
SIGKILL can prevent all reporting on either side of the commit point. No partially
written
destination is permitted. A filesystem unable to provide the required link
semantics fails explicitly; power-loss durability is not claimed. Sources stay
unchanged in every branch.

### Runtime validation and its owner

The copy adapter reopens the staged stream without recovery, checks every
warning, exact page count/order and the fresh marker values, and verifies the
chosen effective version and merged extension declarations. For every output
occurrence compare a source/output pair of the retained page object graphs,
starting from the source projection defined by the gate table. Do not mutate
source objects to form that projection.

Compare PDF object types and scalar values (numbers numerically, strings by
bytes, names exactly), dictionary key sets/values in sorted order, ordered arrays,
and every stream's raw encoded bytes plus its dictionary. Ignore object numbers
and direct-versus-indirect storage; use a visited source/output object-pair set
to terminate cycles. Do not require sharing to be identical across occurrences.
Stream `/Length` is derived from the raw bytes, not compared as a reference.
Keep `/Filter`, `/DecodeParms`, `/JBIG2Globals`, masks, nested Form resources,
fonts and colour/transparency dictionaries in the comparison.

At the page root, omit rebuilt `/Parent`, validate `/Type /Page` separately,
omit the fresh `/BookScanBuilder` marker from the graph comparison, and project
out exactly the table's discarded keys. Omit annotation `/P` from graph equality
but separately verify it names its owning output page when present; require
annotation dictionaries to be indirect and referenced by only one output page.
Remove structure-parent markers and invisible links in both projected graphs.
Compare effective **MediaBox, CropBox, BleedBox, TrimBox, ArtBox, Rotate and
UserUnit** directly, with only the inheritance/default rules in the table.
Require finite four-number boxes of positive extent, rotation an integer
multiple of 90, and finite positive UserUnit; source violations are
`SOURCE_UNSUPPORTED`. Do not infer this geometry from render dimensions.

A mismatch, unsupported output construct, marker alias between occurrences,
or output parser warning is `OUTPUT_INVALID`. This verifies copying/storage
integrity, not rendering correctness of arbitrary PDF features. Poppler remains
an acceptance dependency; matched real/synthetic renders test the adapter's
supported domain independently of its runtime comparator.

## Ownership and tool choice

Use Python **3.12**, standard-library CLI/path/hash/file operations, and
**pikepdf 10.16.0** for whole-page PDF copying. The tested macOS wheel contains
qpdf **12.4.2**. Pin the direct dependency and lock the implementation environment
with uv. Poppler is a verification dependency, not a preparation runtime
dependency. The bounded experiment checked Python 3.12.15 on this Mac.

The command owns parsing and reporting; a pure selection calculation produces
an ordered immutable list of `(source, PDF page, role)`. One preparation operation
owns open source lifetimes, full-page copying, destination markers, preservation
gates and publication. Callers supply selections and a destination, not PDF
object graphs or a write protocol. The copy adapter hides PDF representation,
including source projection and runtime comparison. A staged publication handle
hides temporary-file creation, permissions and no-clobber mechanics while
lending a stream to that adapter. The operation owns stage → save → validate →
source recheck → commit ordering.
Small private boundaries permit controlled I/O faults in tests without adding
public fault-injection flags or an extensible plugin system.

| Alternative | Trade-off and decision |
| --- | --- |
| qpdf CLI plus a shell wrapper | Strong whole-page operations, but selection validation, hash/provenance data and per-page roles still need orchestration. Shell argument handling and PDF-JSON editing add caller/maintenance burden. |
| Python + pikepdf | Chosen: the same small operation controls validated selections, copied page dictionaries and safe publication. One compiled wheel adds a dependency; pin and verify it. |
| Render/extract images and rebuild | Rejected: changes the preservation unit, risks missing masks/vector objects, and introduces sampling before geometry. |

Pikepdf's current [page-copy documentation](https://pikepdf.readthedocs.io/en/stable/topics/pages.html)
describes page copying into a fresh PDF and its document-metadata limits.
The installed save implementation and
[save API](https://pikepdf.readthedocs.io/en/stable/api/main.html#pikepdf.Pdf.save)
were checked for the selected controls; its default file save can replace a
destination, so the command must own no-clobber publication. Qpdf's
[page-selection limits](https://qpdf.readthedocs.io/en/stable/cli.html#page-selection)
support the rejected shell approach's assessment. Reconsider the adapter if
supported real pages fail matched rendering, a required document-wide rendering
feature appears, or the pinned Mac wheel becomes unavailable. No separate ADR
is earned by the toolchain choice: it is local and reversible. The persisted
hint convention has its separate ADR, cited above.

## Test seams

Exercise the working **public `bookscan prepare` process**, not just a selector
or page-copy library. The already-agreed fixture seam combines synthetic exact
order assertions, real full-page comparisons and human inspection. Dry-run and
write must resolve the same page order. Move prepared outputs and copied test
fixtures outside the source collection; freeze every run's inputs/scripts and
record their digests before and after. Human visual acceptance remains explicit.

| Fixture / request | Required output and fidelity |
| --- | --- |
| Fundamentals pages 40,140 + SchoenbergComposition cover page 1 assigned front | Exactly cover 1, music 40, music 140. Preserve all page objects, colour and music/stencil detail. |
| Norwegian grammar PDF page 20, no cover | Exactly one unchanged complete spread PDF page; no preparation split. |
| Counterpoint PDF page 20, no cover | Exactly one unchanged single printed page and its landscape canvas. |
| Algorithm Design PDF page 20, no cover | Exactly one complete existing page, including its JBIG2 stream, DecodeParms/JBIG2Globals and canvas; output declares ADBE base 1.7/extension level 3. No folder-based exemption or appearance change. |
| Distinct cover K1–K4 and content C1–C2; front K1, content C2,K3,C1, back K4 | Exactly K1,C2,K3,C1,K4, with roles front,content,content,content,back; K2 omitted. Reverse/range/exclusion variants must match the grammar. |
| Same labelled source page assigned both front and back | Two occurrences with independent correct markers; no role mutation of the earlier occurrence or source. |
| Inspected two-page Algorithms on Strings, Trees, and Sequence cover | Explicit page 1 front and page 2 back around labelled content; order 1,C1,C2,2. Assignment is a fixture decision, not a filename/page-count inference. Inspect both renders as part of acceptance. |
| Already-assembled labelled PDF as sole content, no covers/PAGES | Same complete page count, order and visible composition; it can be handed directly to later processing. |
| Inherited boxes/resources, rotation, UserUnit, static annotation and existing text fixtures | Effective geometry and all visible drawing/text/annotation appearances survive; existing text remains extractable. |
| Same annotated source page requested twice, including across roles | `SOURCE_UNSUPPORTED` in both dry-run and write; no output/temporary file, unchanged source. |
| Nested Form → Image with masks/DecodeParms/globals; distinct Bleed/Trim/Art boxes; catalog Version override | Graph comparison reaches nested streams and decoder dictionaries; mutation of any retained byte/value fails validation. All seven geometry values and effective version survive. |

For each real selection compare source and corresponding output **full-page
renders at 300 dpi with identical Poppler settings**, pixel dimensions and
decoded RGB pixels. Check MediaBox and CropBox separately so clipped comparisons
cannot hide canvas changes; also render MediaBox where CropBox differs. Check
page count/order and raw compressed image/mask hashes, including relevant shared
decoder resources. Exact matched pixels are expected for static copying. Check
music detail, colours, margins and whole spread/canvas visually at useful zoom;
neither a low-resolution score nor a clean syntax check establishes fidelity.
Compare effective values of all five boxes, Rotate and UserUnit directly on every
corresponding source/output page. Include fixtures with each optional box distinct
and omit them in companion cases to check defaulting. Source SHA-256 must be
unchanged after successes and failures.

Failure acceptance asserts the exact code/exit and first-error phase above for
invocation/arity/singleton errors and compound failures. It covers every
invalid-expression category, missing/unreadable
and zero-page inputs, unsupported visual dependencies, malformed/recovery inputs,
all destination alias types, an occupied destination with sentinel bytes, and
an output created concurrently before publication. Exercise permission errors,
write failure, validation failure, no-link filesystems, SIGINT/SIGTERM before
publication and SIGKILL during writing. Confirm no partial destination, correct
exit/result diagnostics when catchable, unchanged originals and untouched prior
output. Use a controlled writer/publication adapter inside a subprocess test
host to induce bounded faults; use actual public subprocess invocations for
parsing, normal copying, collisions and OS signals. Run every source gate in
dry-run and write, including late raw-traversal warnings, appearance-state
annotations, border-bearing links, external streams and repeated annotated pages.
Faults in nested streams/DecodeParms/globals and each geometry value must be
detected by runtime validation. Check private name/mode, stream saving, and a
kill after link but before unlink. Catchable signals inside the blocked commit
region and after link must yield exit 0/`written` with a complete destination;
EPIPE during success reporting must preserve exit 0 and that PDF. Post-commit
cleanup failures retain success and their warning. Repeating a successful command must
fail as `OUTPUT_EXISTS` without changing that PDF.

## Reusable development commands

Extend the single root Taskfile with `prepare:` names and shared dependency
setup in place. The current design introduces verified bounded experiment and
diagram recipes: `task prepare:copy-experiment ARTIFACTS=/tmp/NEW-DIRECTORY`,
`task prepare:design-render`, and `task prepare:design-serve`. The experiment
requires an unused output directory outside the collection; `COLLECTION` can
override the explicit fixture root. The diagram build requires D2 0.9.0; neither
D2 nor the viewer belongs to the preparation runtime.

The working implementation provides these responsibilities together with the
command and usage instructions:

| Recipe | Required reusable work |
| --- | --- |
| `prepare:setup` | Sync the locked uv/Python environment; check Poppler availability for acceptance. Reconcile shared setup rather than replacing geometry/process dependencies later. |
| `prepare:run` | Run the installed `bookscan prepare` with Task's forwarded arguments; direct shell invocation remains the public seam. |
| `prepare:check` | Formatting, lint/type checks and synthetic public-command order/role/failure tests. |
| `prepare:acceptance` | Explicit real-fixture selection, render comparison and original-digest verification in a caller-selected artifact directory. Produce comparison paths for human inspection. |

Once packaging exists, use `uv run --locked bookscan prepare` behind the run
recipe and the same entry point for subprocess acceptance. Exact synthetic-test
and acceptance runner commands belong to the working implementation, not an
invented test harness here. Run each new/changed task and affected existing task
before relying on the combined file. Retain any experiment wrapper a lasting
recipe still calls, or replace/remove its recipe and verify the replacement.

## Scope boundary

Preparation is independently useful with ordinary PDF readers. Geometry,
border removal, spread classification/splitting, OCR and review controls are
later work. This design supplies their sole required PDF input and optional
role hints. Native packaging, a GUI, a multi-book queue, collection discovery,
appearance cleanup and general interactive-PDF editing are unnecessary for this
increment. Shell loops may call the single-book command repeatedly.

## Implementation and evidence

The installed locked command is `uv run --locked bookscan prepare`; use
`task prepare:run -- …` for individually shell-quoted Task forwarding.
The temporary preview module/recipes have been retired. `prepare:check` runs
format/lint/strict types and collection/Poppler-independent public and private
fault tests. `prepare:acceptance MODE=synthetic|real|all ARTIFACTS=…` records
per-page 300-dpi RGB, geometry, encoded-resource and source-digest comparisons;
real/all use an explicit `COLLECTION`, while synthetic never opens it.
Reproduction and pending human visual acceptance are recorded in
[the acceptance note](../acceptance/prepared-pdf.md).

The adapter reconstructs the gated immutable graph inside the live-source
operation. For zero-byte filtered streams, qpdf 12.4.2 elides their encoding
dictionaries on save; a standard incremental revision inside the same private
stream restores those dictionaries before independent runtime validation.
A fresh qpdf document has a PDF 1.3 floor, so source versions 1.0–1.2 produce
1.3 outputs; all other versions and accepted ADBE levels use the chosen numeric
maximum. Both behaviours are tested without relaxing graph equality or source
gates. The historical dependency experiment/report and preview report remain
separate evidence from the complete public command.
