# Prepared PDF copying experiment

A bounded dependency experiment on 11 October 2026 supports the
[preparation design](../specs/prepared-pdf.md)'s whole-page copying choice.
It is not the preparation command or its acceptance suite. No geometry, cleanup
or OCR was performed. The authoritative per-item data is
[the retained report](prepared-pdf-copy-report.json).

## Reproduce

Run `task prepare:copy-experiment ARTIFACTS=/tmp/NEW-DIRECTORY`.
Choose an unused directory outside the source collection. The Taskfile pins
pikepdf 10.16.0 on Python 3.12; this run used Python 3.12.15, bundled qpdf 12.4.2
and Poppler 26.10.0 on this Mac. `COLLECTION` defaults to
`/Volumes/Glass/Book Conversion` and can specify another explicit fixture root.
The wrapper is [prepared_pdf_copy.py](../../experiments/prepared_pdf_copy.py).

The completed run's artifacts are at
`/private/tmp/bookscan-prepared-pdf-k9-stencils`: `copied.pdf`, the labelled
source/output PDFs, matched source/copy PNGs and `report.json`. Temporary images
are disposable; no source PDF or derived page image is committed here.
The retained report includes the final script digest and each source's before
and after digest. The script asserts its own digest is unchanged during the
run and checks each item, rather than trusting matching totals.

## Method and results

Open each source read-only without recovery, append its complete selected pages
to a new pikepdf document, and write fresh destination-page role dictionaries.
Save with stream decode level `none`, compression/recompression and normalization
disabled, and a numerically chosen minimum PDF version. Reopen without recovery.
Compare decoded content-stream hashes, effective MediaBox/CropBox/rotation/
UserUnit, direct Image XObject raw bytes/filter/dimensions/stencil flags and
annotation counts. Check each copied role and source PDF-page number.

Render both complete corresponding PDF pages with `pdftoppm` using 300 dpi,
CropBox, PNG and otherwise identical settings. Compare decoded RGB pixels and
dimensions exactly. All selected real pages have the same effective CropBox
and MediaBox; the synthetic case separately exercises a smaller inherited
CropBox. MediaBox and CropBox values also compare directly.

Paths in this table are relative to the explicit collection root; numbers are
one-based PDF pages. Output position describes this mixed copying probe, not
an actual invocation of the future role-grouping command.

| Probe position | Source PDF and page | Render size | Direct image/stencil objects | Result |
| --- | --- | --- | --- | --- |
| 1 | `Covers/SchoenbergComposition.pdf` 1 | 2480 × 3505 | 1 image | Exact RGB and page fingerprints |
| 2 | `Raw Scans/Fundamentals of Musical Composition.pdf` 40 | 1692 × 2443 | 1 image + 1 stencil | Exact RGB and page fingerprints |
| 3 | `Raw Scans/Fundamentals of Musical Composition.pdf` 140 | 1720 × 2459 | 1 image + 2 stencils | Exact RGB and page fingerprints |
| 4 | `Processed Books/Norwegian - An Essential Grammar (Routledge)/Norwegian - An Essential Grammar (Routledge).pdf` 20 | 3591 × 2695 | 1 image | One unchanged complete spread PDF page |
| 5 | `Needing Cleanup/Counterpoint in Composition.pdf` 20 | 3509 × 2480 | 1 image | One unchanged landscape-canvas PDF page |
| 6 | `Processed Books/Algorithm Design/Algorithm Design.pdf` 20 | 2350 × 2721 | 1 image, JBIG2 | Exact RGB and page fingerprints |
| 7 | `Covers/Algorithms on Strings, Trees, and Sequence.pdf` 1 | 2480 × 3505 | 1 image | Exact RGB and page fingerprints |
| 8 | `Covers/Algorithms on Strings, Trees, and Sequence.pdf` 2 | 2480 × 3505 | 1 image | Exact RGB and page fingerprints |

Both pages of the last cover source were inspected visually: page 1 is the
title/front cover; page 2 has the back-cover description and barcode. This makes
explicit page-1 front/page-2 back assignments useful companion fixtures. The
command still cannot infer a role from a filename or page count.

The labelled fixture has four cover pages K1–K4 and two content pages C1–C2.
The copied sequence was **K1,C2,K3,C1,K4,K1**, confirmed by `pdftotext` and
per-page rendering. K2 is omitted; K3 is interior content; the final K1 deliberately
repeats the first page under a different role. First/last K1 retain separate
front/back dictionaries and distinct destination-page object identities.
Inherited page resources, MediaBox, CropBox and 90° rotation survive copying;
UserUnit 1.25 survives as well. All six labelled render pairs match exactly.

All six distinct real-source PDF digests matched before and after the final
run. For the five overlapping sources, they also match the earlier geometry
survey's recorded digests. The report records the additional two-page cover's
digest. Originals were only read.

## What the experiment caught

The initial report writer could not serialize pikepdf's decimal coordinates.
The final report encodes those decimal values as exact strings and rejects
unexpected types. After that fix, a completed run matched all renders, but the
image convenience accessor's inventory omitted stencil XObjects. Direct
`pdfimages` and page-resource inspection exposed that mismatch. The final run
enumerates direct Image XObjects, including ImageMask stencils, and repeats
every item comparison with a frozen final script. Only that final report is
retained as current evidence.

This is another reason to copy complete pages: an image helper's result is not
the page's complete visible composition. The music page-140 inventory includes
even the small 80 × 12 stencil. Pixel comparisons already included these masks;
the stronger stream inventory now checks them explicitly as well.

## Publication check and limits

A separate bounded standard-library smoke check in a fresh local temporary
directory confirmed that `os.link` publishes a new target and raises
`FileExistsError` for an occupied file or dangling symlink, leaving those entries
unchanged. Python's [link API](https://docs.python.org/3.12/library/os.html#os.link)
and [flush/fsync contract](https://docs.python.org/3.12/library/os.html#os.fsync)
were checked. This supports the chosen mechanism on the tested Mac filesystem;
it does not establish crash recovery, power-loss durability, foreign-volume
support or the future command's error handling.

The copying probe covers static real pages and one labelled inherited-geometry
fixture. It does not test the CLI grammar, role grouping, exclusion parsing,
already-assembled public invocation, output alias checks, source-change races,
signals, write/validation failures, unsupported document features, annotation
appearances, nested image resource inventories or arbitrary PDFs. The first
implementation owns these cases through the agreed public-command seam.
Direct XObject fingerprints are deliberately bounded; full-page renders include
all drawing visible under the tested settings but prove no untested viewer mode.

The dependency run establishes copying fidelity on these fixtures, not human
acceptance of a working preparation product or any correction method. The
implementation's visual comparisons and the user's judgment remain required.

## Primary implementation references

Pikepdf's [page-copy documentation](https://pikepdf.readthedocs.io/en/stable/topics/pages.html)
describes whole-page append/extend and the limits of document-level metadata
transfer. Its [save API](https://pikepdf.readthedocs.io/en/stable/api/main.html#pikepdf.Pdf.save)
describes the stream controls. The installed 10.16.0 `_methods.py` was inspected
for save-to-file/stream behaviour and its default atomic replacement wrapper:
the preparation operation needs its own no-clobber publication policy.
The [qpdf page-selection documentation](https://qpdf.readthedocs.io/en/stable/cli.html#page-selection)
also distinguishes page copying from complete document metadata migration.

These findings are adopted in the spec's preservation, ownership and publication
contracts. They do not choose the processor's renderer, correction algorithm,
OCR engine or review interface.
