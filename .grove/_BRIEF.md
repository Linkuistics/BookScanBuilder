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
