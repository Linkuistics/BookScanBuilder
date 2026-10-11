# BookScanBuilder

Terms for reconstructing a book PDF from scans while preserving its visual
content.

## Language

**Source PDF**:
A PDF supplied for a book conversion, whether it contains raw scans,
previously processed scans, or cover scans.

**Prepared PDF**:
A single PDF containing the book content and chosen cover pages in their
assembly order, ready for geometry correction and OCR.

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
the PDF without replacing the visible page image.

## Example dialogue

**User:** The page turns while it passes through the scanner. I also have a
separate cover scan.

**Developer:** First we combine the source PDFs into one prepared PDF, with the
cover pages in their chosen positions. Then we correct its page images and add
the OCR text layer for searching and selecting text.
