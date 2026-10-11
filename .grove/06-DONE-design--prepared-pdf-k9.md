# prepared-pdf-k9

## Goal

Establish the smallest public command and preservation contract that assembles
explicit source/cover selections into one prepared PDF, independently usable
before correction exists. Deliver a spec and only the ADRs the decisions earn.

## Context

Use the confirmed requirements in `plan-k1` and this root brief's preparation
acceptance cases. This leaf was migrated from preparation's `prepared-pdf-k4`
at revision `1ada47bd`; its local successor is `prepared-pdf-k10`.
The representative objects in `docs/research/scan-geometry-a.md` show why taking
only the first image object does not preserve a PDF page's visible content.

## Done when

- The durable design at `docs/specs/prepared-pdf.md` specifies explicit content
  PDFs/page selections, default order, requested reordering/exclusion, explicit
  front/back roles, placement and the already-assembled/no-cover case.
- It specifies a composable single-book shell interface, clear selection errors,
  source/output collision handling, output-write failure behavior, and original
  preservation. Blank/duplicate detection never authorizes silent exclusion.
- Choose the least local language/library/tool combination that can preserve
  complete selected PDF pages. Check material framework/library decisions
  against current primary documentation or installed source rather than memory.
  No required processor, queue, GUI or native packaging.
- Document the single-PDF successor handoff. If cover roles/provenance are needed
  downstream, choose how they survive without a required sidecar or collection
  search. Do not settle the processor's correction or OCR implementation here.
- The design gives concrete expected order and fidelity checks for the root
  brief's real and labelled fixtures, a public command test seam, and a small
  verified dependency experiment if PDF copying assumptions need evidence.
- State the first implementation's concrete Taskfile needs, commands when
  established, and original-digest checks. Specify `prepare:` recipes extending
  the one shared root Taskfile, retaining existing recipes and dependency setup.
  Human fidelity comparisons remain explicit; deterministic fixture assertions
  do not substitute for them.

## Notes

This is design work: specify the public test seam and validate copying
assumptions with a bounded dependency experiment if needed. The implementation
will test the actual working public command. `prepared-pdf-k10` owns
implementation decomposition. Do not write a schema-only or library-only
shipping plan: the useful unit is a working
preparation command plus its verification and usage instructions. The separate
geometry prototype is not a prerequisite for preparation. Preparation controls
selected PDF pages; the processor owns exclusion/reordering of book pages
created by a spread split. Keep both stages in this workspace. If this design
earns a review, insert it before `prepared-pdf-k10` consumes the agreement.

## Decisions (running log)

The public seam is `bookscan prepare`, operating on repeated explicit
`--content`, `--front` and `--back` selections. Each selection accepts a quoted
PDF path and optional one-based page expression; omission means all pages.
Selections concatenate within each role in argument order, then assemble
front → content → back. Interior cover pages use a content selection. Explicit
page sequences and exclusions carry all reordering/removal decisions; neither
file discovery nor automatic blank/duplicate removal belongs here.

Use a dry-run at the same public seam to expose the complete resolved order
before writing. Normal operation never prompts, never overwrites an existing
destination, and publishes a validated complete PDF with a no-clobber operation.
The implementation must exercise collision and interruption behaviour through
that public seam, rather than treating the copying experiment as product tests.

Choose Python 3.12 with pikepdf 10.16.0, using its Mac wheel's qpdf 12.4.2.
The installed save implementation and current primary page-copy/save docs were
checked. Direct page-dictionary access keeps role assignment and provenance in
the same small preparation operation; qpdf plus shell would still need that
orchestration. Rendering/extracting images cannot satisfy complete-page
preservation. This local, reversible choice does not earn an ADR.

Store optional downstream role/provenance hints on destination pages in a
versioned private PDF dictionary. Each occurrence gets a fresh dictionary, so
duplicated pages can have different roles. Store the immediate source digest
and PDF-page number, with no required collection path or sidecar. The successor
must accept unmarked PDFs and must not use these hints as geometry exemptions.

The first copier accepts static page composition and rejects unsupported
document-wide rendering dependencies before publication. The inspected
Algorithm Design source has an empty AcroForm Fields array, so an empty form
dictionary alone is not grounds for rejection. Document metadata, tags and
bookmarks are distinct from the visual fidelity promise.

Direct inspection of both pages of `Covers/Algorithms on Strings, Trees, and
Sequence.pdf` found a title/front cover and a back cover with description and
barcode. Use explicit page-1 front/page-2 back assignments as the real multi-page
companion fixture; filenames and counts remain insufficient to assign roles.

Introduce the shared root Taskfile now that experiment and viewer recipes are
concrete. Its `prepare:` recipes keep the bounded copying wrapper and static
presentation runnable. The first working implementation extends this file with
setup/run/check/acceptance recipes and validates affected existing recipes.

The first complete experiment matched eight real-page and six labelled 300-dpi
renders and preserved all six source digests. Its image convenience accessor
omitted stencil XObjects from the per-stream inventory even though full-page
render comparisons included them. Direct `pdfimages` and page-resource checks
found one stencil on music page 40 and two on page 140. Replace that inventory
with direct Image XObject enumeration and rerun the frozen experiment; the
durable report must correspond to the final script, including these masks.

The final frozen experiment completed with exact 300-dpi RGB equality for all
eight real pages and six labelled occurrences, unchanged content/image/stencil
fingerprints, independent duplicate-page roles and unchanged source digests.
Retain its report and bounded limits in `docs/research/prepared-pdf-copy.md`.
The public command and its failures remain implementation acceptance work.

The landed spec is load-bearing for the successor's preservation and output
failure behaviour. It earns one scheduled design review before
`prepared-pdf-k10`; this session uses no in-session reviewer. The review should
try to disprove the document-wide rendering gates, marker semantics, CLI
selection grammar and no-clobber commit/cancellation contract.
