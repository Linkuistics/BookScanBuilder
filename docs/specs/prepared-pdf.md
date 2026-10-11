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
| `--dry-run` | Validate sources, selections and destination; report the complete resolved order; write no PDF or temporary file. |
| `--json` | Emit one versioned JSON result on stdout, including structured errors. |
| `--help` | Explain role grouping, page grammar, failure/retry behaviour and common examples; exit 0 without opening inputs. |

Examples of the public interface (specified here; not yet implemented):

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
Quote expressions containing `!` for shells with history expansion.

Empty expressions/tokens, zero, negative or non-integer numbers, open-ended
ranges, `!all`, out-of-bounds endpoints (including exclusions), and a selection
resolving to zero pages are errors. The command never silently clamps ranges.
Remove an unwanted entire selection argument rather than supplying an empty one.

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
context. Never mix a human result into JSON stdout. A traceback is not a normal
selection diagnostic. An uncatchable kill cannot promise a result object.

| Exit | Meaning | Representative stable error codes |
| --- | --- | --- |
| 0 | Valid plan or complete published PDF | — |
| 2 | Invocation or page selection error | `INVALID_SELECTION`, `PAGE_OUT_OF_RANGE`, `EMPTY_SELECTION`, `CONTENT_REQUIRED` |
| 3 | Unreadable, unsupported or changing source | `SOURCE_NOT_FOUND`, `SOURCE_UNREADABLE`, `SOURCE_UNSUPPORTED`, `SOURCE_CHANGED` |
| 4 | Destination precondition/collision | `SOURCE_OUTPUT_COLLISION`, `OUTPUT_EXISTS`, `OUTPUT_DIRECTORY_INVALID` |
| 5 | Copy, validation or output I/O failure | `COPY_FAILED`, `OUTPUT_INVALID`, `WRITE_FAILED`, `PUBLISH_FAILED` |
| 130 / 143 | Caught interrupt / termination before publication | `INTERRUPTED` |

For an invalid selection, name the input, expression, invalid token and available
page count, and suggest a valid range. Missing/unreadable sources name the path
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
Flate recompression disabled. Use at least the highest source PDF version, with
numeric version comparison. Carry compatible source extension declarations into
the output, taking the highest base-version/extension-level pair for each
prefix; reject extension definitions the copier cannot reconcile. Do not remove
resources as an optimization in this first increment.

The first supported domain is static book/cover PDF pages. The fresh document
does not promise source bookmarks, printed page labels, tags/accessibility
structure, attachments, forms, scripts, signatures, archival conformance or
document metadata. These are not substitutes for visible-page fidelity.
Drop copied structure-parent markers when their document structure is not
transferred; do not claim that a reordered assembly remains a tagged PDF.

Before copying, reject encrypted PDFs (including empty-password encryption),
sources requiring recovery, XFA, non-empty interactive form fields, selected
widget annotations, document optional-content configuration, and document output
intents. Page annotations without a self-contained normal appearance stream are
also unsupported, except invisible link annotations. Copy self-contained static
annotation appearances intact; hyperlink navigation itself is outside the
contract. Empty form dictionaries, such as the inspected Algorithm Design
source's empty Fields array, are acceptable. Unknown features or parser warnings
that make preservation uncertain must produce an actionable error before
publication. No arbitrary PDF can be assumed safe merely because it opens.
The implementation must cover these gates and their visible consequences; the
copying experiment does not establish support for every PDF feature.

## Embedded page roles

The preparation command writes a fresh private `/BookScanBuilder` dictionary on
each **destination page**. Version 1 contains `/Version` (integer 1), `/Role`
(PDF text string `front`, `content` or `back`), `/SourceSHA256` (64 lowercase hex
characters identifying the immediate source bytes), and `/SourcePage` (positive
one-based PDF page integer). It includes no required filename, collection path
or external identifier. Assign a new dictionary to each copied page; never
mutate a nested dictionary shared with a source or another occurrence.
Explicit arguments replace any older preparation marker on that destination
page. Provenance describes this assembly, not a full transformation history.

These markers are inert hints for a later processor and travel inside the PDF;
no mandatory sidecar exists. Ordinary PDF readers can display the prepared PDF
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

Write a unique private temporary file in the destination directory. Reopen it
without recovery, check parser diagnostics, page count, resolved roles,
effective boxes/rotation and expected copied content/resource integrity. Flush
and fsync the completed file. At publication use an atomic **no-clobber** link
from the temporary file to the requested destination; link success is the
commit point. This handles another process creating the output between the
initial existence check and publication. Never use a replacing rename, truncate
the destination or fall back to a non-atomic copy.

Before the commit point, any caught write/copy/validation/cancellation error
removes this run's temporary file and leaves the destination absent or its
previous occupant unchanged. A hard kill may leave an identifiable private
temporary file, which a later run must not indiscriminately delete. After a
successful link, remove the temporary name; cleanup failure is a warning about
an extra name for a complete file, not a failed PDF write. Cancellation after
the commit point may leave the complete valid destination. No partially written
destination is permitted. A filesystem unable to provide the required link
semantics fails explicitly; power-loss durability is not claimed. Sources stay
unchanged in every branch.

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
object graphs or a write protocol. The copy adapter hides PDF representation;
the publication boundary hides temporary-file and no-clobber mechanics.
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
is earned: these choices are local, visible and reversible.

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
| Algorithm Design PDF page 20, no cover | Exactly one complete existing page, including its JBIG2 stream and canvas. No folder-based exemption or appearance change. |
| Distinct cover K1–K4 and content C1–C2; front K1, content C2,K3,C1, back K4 | Exactly K1,C2,K3,C1,K4, with roles front,content,content,content,back; K2 omitted. Reverse/range/exclusion variants must match the grammar. |
| Same labelled source page assigned both front and back | Two occurrences with independent correct markers; no role mutation of the earlier occurrence or source. |
| Inspected two-page Algorithms on Strings, Trees, and Sequence cover | Explicit page 1 front and page 2 back around labelled content; order 1,C1,C2,2. Assignment is a fixture decision, not a filename/page-count inference. Inspect both renders as part of acceptance. |
| Already-assembled labelled PDF as sole content, no covers/PAGES | Same complete page count, order and visible composition; it can be handed directly to later processing. |
| Inherited boxes/resources, rotation, UserUnit, static annotation and existing text fixtures | Effective geometry and all visible drawing/text/annotation appearances survive; existing text remains extractable. |

For each real selection compare source and corresponding output **full-page
renders at 300 dpi with identical Poppler settings**, pixel dimensions and
decoded RGB pixels. Check MediaBox and CropBox separately so clipped comparisons
cannot hide canvas changes; also render MediaBox where CropBox differs. Check
page count/order and raw compressed image/mask hashes, including relevant shared
decoder resources. Exact matched pixels are expected for static copying. Check
music detail, colours, margins and whole spread/canvas visually at useful zoom;
neither a low-resolution score nor a clean syntax check establishes fidelity.
Source SHA-256 must be unchanged after successes and failures.

Failure acceptance covers every invalid-expression category, missing/unreadable
and zero-page inputs, unsupported visual dependencies, malformed/recovery inputs,
all destination alias types, an occupied destination with sentinel bytes, and
an output created concurrently before publication. Exercise permission errors,
write failure, validation failure, no-link filesystems, SIGINT/SIGTERM before
publication and SIGKILL during writing. Confirm no partial destination, correct
exit/result diagnostics when catchable, unchanged originals and untouched prior
output. Use a controlled writer/publication adapter inside a subprocess test
host to induce bounded faults; use actual public subprocess invocations for
parsing, normal copying, collisions and OS signals. Post-commit cancellation
accepts only a complete valid destination. Repeating a successful command must
fail as `OUTPUT_EXISTS` without changing that PDF.

## Reusable development commands

Extend the single root Taskfile with `prepare:` names and shared dependency
setup in place. The current design introduces verified bounded experiment and
diagram recipes: `task prepare:copy-experiment ARTIFACTS=/tmp/NEW-DIRECTORY`,
`task prepare:design-render`, and `task prepare:design-serve`. The experiment
requires an unused output directory outside the collection; `COLLECTION` can
override the explicit fixture root. The diagram build requires D2 0.9.0; neither
D2 nor the viewer belongs to the preparation runtime.

The first working implementation adds these concrete responsibilities together
with the command and usage instructions:

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
