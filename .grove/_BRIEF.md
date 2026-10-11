# BookScanBuilder — brief

## Goal

Provide a personal workflow on the current Mac that reconstructs corrected book
PDFs from the user's scanned collection and optional separate cover PDFs.
Preserve the corrected page images as the visible content and add an English
OCR text layer for searching and selecting text.

Process one book at a time in two stages that can be run from the shell:
prepare one PDF by merging the chosen covers and content, then process that
single PDF. The user will use the shell to iterate over the collection.

## Done when

- Book PDFs from `Raw Scans`, `Processed Books`, and `Needing Cleanup`, with
  separate covers when supplied, can be prepared into one PDF per book.
- The main processing entry point accepts that one PDF and performs correction,
  cleanup, OCR, review and export without searching collection folders for
  content or cover scans. A PDF whose covers are already assembled is also a
  valid single-PDF input.
- Geometry correction addresses distortion that varies within a page, including
  the reported rotation during scanner feed. Assess previously processed pages
  as well; a prior pass does not prove that their geometry is correct.
- Genuine spread scans become one book page per output PDF page. A single book
  page on a larger landscape canvas remains a single book page.
- Default visual cleanup corrects geometry and removes scanner borders while
  preserving colour, faint text, illustrations and music notation. Paper
  whitening and noise removal are optional and previewable.
- Automatic processing is followed by review of flagged pages, with adjustment
  of any page available before export. Review changes appear in the final PDF.
- Assembly preserves source order by default, supports reordering and
  user-controlled exclusion of blanks or duplicates, and supports inserting
  cover pages. Front and back covers have explicit roles and placement.
- The output retains visible page images and has an English OCR text layer
  whose search and selection positions align with the corrected images.
- Originals remain untouched, and already-correct pages are not degraded.
- The agreed test seam and visual comparisons demonstrate these behaviours on
  representative real inputs.

## Decomposition

The user confirmed the bootstrap requirements in `plan-k1`, including the
two-stage preparation/processing boundary.

- `scan-geometry-k2` surveys practical correction approaches and their failure
  cases, providing the evidence needed to choose a small real-page trial.
- `book-reconstruction-k3` uses that evidence to identify the smallest useful
  increments and cut the next design/prototype/implementation work as needed.

Geometry correction on real scans is the principal unresolved technical
question; its quality must be demonstrated before a method is treated as
settled. One focused survey is sufficient at this point; its job is to inform
the trial, not to promise an algorithm's success.

## Working increments

| Increment | Useful handoff | Dependency and grove |
| --- | --- | --- |
| Explicit PDF preparation | One prepared PDF, with selected content order and explicit front/back covers, usable by ordinary PDF tools | Independent product increment. Separate jj workspace and grove: `/Users/antony/Development/BookScanBuilder.prepare-pdf`. Read its root brief for the scoped design and planning leaves. |
| Corrected searchable book | One prepared PDF processed through accepted geometry, border removal, review adjustments and aligned English OCR into an exported PDF | Depends on preparation's public contract and demonstrated geometry. `corrected-book-k5` creates a separate processor grove when the trial evidence is sufficient. The corrected-image schema and its working reader/export path belong to this same increment. |
| Optional appearance cleanup | Preview and selectively apply whitening or noise removal while keeping the working default processor and its accepted-image/OCR alignment | A separate successor grove after the default processor works. Its design must compare faint print, music, illustration and colour before choosing a cleanup method. |

This grove currently supplies the bounded geometry evidence and the handoff
plan. `page-geometry-k4` is a throwaway two-page comparison with a user reaction,
not a production increment or a settled algorithm. `corrected-book-k5` then
checks that result, commissions the precisely specified expanded fixtures or a
bounded repair trial, and shapes the next processor grove. It must keep enough
live work here to check the root's end-to-end Done when against the integrated
increments; completion of a prototype or sibling grove does not close this root.

Product groves are sequential at integration: land the preparation contract,
then build a single-PDF processor against it. Preparation design can proceed
without waiting for the geometry trial. No background drivers are launched by
this planning session. When bringing stage results together, integrate product
artifacts and durable documents through jj; keep each grove's task tree local
to its workspace rather than merging unrelated `.grove/` histories.

## On the horizon

The production correction field, automatic confidence policy and manual
adjustment controls depend on the user's reaction to the real-page trial.
Their implementation decomposition cannot yet be stated honestly. Optional
whitening and noise-removal mechanisms need appearance evidence; the precisely
known preview/fidelity design question belongs to a successor appearance grove
after the default processor supplies a working accepted-image/export seam.
`corrected-book-k5` carries that handoff obligation. No method is chosen here.

## Pointers

- `CONTEXT.md` — the project's terminology.
- `plan-k1` — the bootstrap requirements and running decision log.
- `/Volumes/Glass/Book Conversion` — the input collection; exact inspected
  examples and PDF page numbers are recorded in `plan-k1`.

## Test seams

Agreed with the user: use representative source PDFs from all three book folders
and separate covers. Check preparation at its public entry point for cover-role
placement and preservation of content order. Then exercise the main processing
entry point with one assembled PDF, through correction, cleanup, OCR, review
decisions and export. The main process must work without access to the source
collection folders; it receives their prepared PDF rather than discovering
inputs itself.

Check geometry across the page, including text and staff lines; fine-detail
retention; spread splitting and assembly order; alignment of English search
and text selection; application of review adjustments; unchanged originals;
and preservation of already-correct pages. Combine repeatable fixture checks
with the user's visual judgment of before/after geometry samples. A numerical
score alone does not establish visual acceptance.

## Notes

An app or process is acceptable. Native application packaging, other operating
systems, other users, and an application-level multi-book queue are not required.
English is the OCR target; other visible languages and all non-text content
remain in the page images.

Some cover PDFs contain several pages, potentially including front and back
covers. Page count or filename alone does not establish each cover page's role.
The preparation/assembly flow must permit explicit assignment. Optional review
adjustments after processing must still be reflected in the export; no later
step may need to rediscover separate cover files.

No correction algorithm, implementation language or review-interface technology
has been selected. The first test book has not been explicitly chosen by the
user; the inspected examples are candidate fixtures rather than approved
correction results.

There was no project Taskfile at bootstrap. Adding a root `Taskfile.yml` was
suggested; introduce it when deterministic development commands are concrete,
wrap existing tools where appropriate, and verify its tasks before relying on
them.
