# Prepared page hints

Persist versioned, advisory assembly roles and immediate-source provenance in a
private page-level `/BookScanBuilder` dictionary. Readers accept an ordinary
unmarked PDF and treat every marker as a reviewable hint; `content` records only
the absence of an explicit front/back assignment in that assembly. The field
schema and reader behaviour are specified in [Prepared PDF](../specs/prepared-pdf.md#embedded-page-roles).

This convention binds preparation and geometry import and persists in prepared PDFs,
so changing its meaning requires continued reader compatibility. The
[copying evidence](../research/prepared-pdf-copy.md) demonstrates independent
roles on repeated unannotated pages and identifies the page-piece convention.
A required sidecar would break the sole-PDF handoff. The standard `/PieceInfo` container
([ISO 32000-1, §14.5](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf))
adds a page/modification-date convention that arbitrary PDF editors need not
maintain, and it does not establish trustworthy cover classification. Choose
the simpler inert dictionary with explicit versioning and optional consumption;
no timestamp or source digest grants an exemption from geometry review.
Reconsider the container if a required interoperability consumer needs
page-piece data, retaining support for existing version-1 hints.
Geometry export omits these assembly hints; its separate
[review report](geometry-review-handoff.md) records transformed/split lineage
without redefining version-1 immediate-source provenance.
