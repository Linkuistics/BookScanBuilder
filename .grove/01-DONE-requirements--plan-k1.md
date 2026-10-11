# plan-k1

## Goal

Establish the requirements for reconstructing corrected, searchable book PDFs
from the user's scanned book collection.

## Context

This is the fresh grove's bootstrap leaf. The user's description is the source
of requirements. The user selected preparation followed by single-PDF
processing. No correction algorithm, implementation language or review-interface
technology has been selected.

## Done when

- The input, correction, review, assembly and output requirements are settled
  with the user, with concrete acceptance scenarios.
- The user has agreed the seams through which the work will be tested.
- The user confirms a shared understanding, and the next work is described
  precisely enough for a fresh session to proceed.

## Notes

The correction method, input formats and review workflow have interdependent
answers. Use the full requirements interview, one question at a time. Record
answers as they settle; do not commit decisions or grow the tree before the user
confirms shared understanding.

## Decisions (running log)

The user has many books that were cut up and scanned on "Glass/Book Conversion".
Pages can rotate while moving through the scanner, so the distortion varies
within a page. Correcting only a single rotation angle for the whole page does
not capture the stated problem.

The required deliverable is a properly aligned, corrected PDF of the book,
assembled from raw page scans and, often, separate cover scans. Its visible
content must remain the scanned pages. OCR adds searchable, selectable text;
it must not replace the visible scan with newly typeset text.

The user confirmed that the existing page scans and separate cover scans are
PDFs. Direct PDF input is required; an image-file import path is not yet required.

The user agreed to automatic processing followed by review. The tool should
correct pages and add OCR automatically, flag uncertain pages for review, and
let the user adjust any page before exporting the book PDF. Reviewing every page
manually is not a prerequisite for export.

The user wants an app or process that runs on this machine, solely for personal
use. Local execution on the current Mac is required. A native app is not a
requirement; the interface and packaging should serve the correction and review
workflow rather than a general-purpose product or other users.

The scans are available locally under `/Volumes/Glass/Book Conversion`.
The collection has `Raw Scans`, `Covers`, `Needing Cleanup`, and
`Processed Books` folders. "Glass/Book Conversion" denotes this input location,
not a scanner model or a scanning service.

Initial direct inspection used `pdfinfo` and page renders of
`Raw Scans/Fundamentals of Musical Composition.pdf` (PDF pages 20 and 40;
238 pages total),
`Raw Scans/Garbage Collection - Algortihms for Automatic Dynamic Memory Management.pdf`
(PDF page 30; 402 pages total), and `Covers/SchoenbergComposition.pdf`
(one PDF page). These samples include music notation, prose, code, a diagram,
and a colour cover with surrounding scanner background. They establish input
variety, not the achievable quality of any correction method.

The user explicitly expanded the input scope to `Processed Books` and
`Needing Cleanup` as well as `Raw Scans`. PDFs in those folders must also be
processed and have geometry adjusted as necessary. A folder's name or a prior
processing pass must not be treated as evidence that its geometry is already
correct. Existing OCR and prior corrections in these inputs need to be examined
when establishing the processing requirements.

Direct inspection of PDF page 20 from
`Needing Cleanup/Counterpoint in Composition.pdf`,
`Processed Books/Norwegian - An Essential Grammar (Routledge)/Norwegian - An Essential Grammar (Routledge).pdf`,
and `Processed Books/Algorithm Design/Algorithm Design.pdf` showed further
input cases: a landscape PDF canvas with a single printed page and scanner
background, a two-page spread with distortion near the gutter, and an already
processed single-page image. `pdftotext` produced only one character for each
sampled page, rather than meaningful extracted text. These are page-specific
observations, not conclusions about all pages or all PDFs in those folders.

The user confirmed that spread scans should be split into one book page per
output PDF page. Each book page can then be corrected and OCR'd independently.
The requirement covers mixed inputs: not every landscape PDF page is a spread,
as the inspected Counterpoint page shows, so layout detection and review must
distinguish a spread from a single book page on a larger canvas.

The user agreed to geometry correction and scanner-border removal as the
default visual cleanup, preserving colour and fine detail. Paper whitening and
noise removal are optional and must be previewable so faint text, illustration
detail and music notation can be protected.

The user requires searchable OCR for English only and does not expect to search
other languages. Initial OCR acceptance should therefore test English search
and text selection. Non-English material remains part of the visible page image;
multilingual OCR configuration is not required for this workstream.

The user agreed to assembly controls that preserve source order by default,
allow insertion of cover pages and reordering of pages, and allow the user to
exclude blanks or duplicates. Removal of an apparent blank or duplicate is a
user-controlled assembly decision, rather than grounds for silent deletion.

The user clarified that cover PDFs can include both front and back covers.
Assembly must let the user assign cover-page roles and place a front cover
before the contents and a back cover after them, instead of prepending all
pages from a cover PDF. Direct metadata inspection also found one-page,
two-page and four-page cover PDFs; page count alone does not establish the role
of each cover page.

The user wants to process one book at a time and use the shell to process the
set later. The processing entry point must therefore be usable from the shell
for a single book and composable in an ordinary shell loop. An application-level
multi-book queue is not required. Review remains per book, as already agreed.

The user agreed to testing through the single-book command using representative
inputs from `Raw Scans`, `Processed Books`, `Needing Cleanup`, and `Covers`.
Acceptance must check straight text and staff lines across the page with fine
detail retained; correct spread splitting and chosen assembly order; English
search and selection aligned with the visible text; review adjustments present
in the export; unchanged originals; and no degradation of already-correct
pages. Geometry quality also requires the user's visual judgment of before/after
samples. This agreement establishes the test seam, not that any algorithm has
already achieved those outcomes.

The user confirmed shared understanding of the consolidated scope, with an
explicit change to the process boundary: first merge chosen cover scans into
the content, then process a single assembled PDF. Preparation handles the
explicit source PDFs and cover-page placement; the main process accepts one
PDF and must not search across collection folders to find content or covers.
The collection folders define which books are in scope, not a dependency of
the main processor. The agreed test seam follows this boundary: check
preparation/assembly separately and exercise correction, cleanup, OCR, review
and export through the single-PDF processing entry point.
