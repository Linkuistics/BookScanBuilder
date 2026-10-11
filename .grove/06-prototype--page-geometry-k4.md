# page-geometry-k4

## Goal

Build a cheap two-page visual comparison that can reject automatic Leptonica
vertical dewarping for these scans. Obtain the user's reaction to geometry and
fidelity before choosing production correction or review technology.

## Context

Read `docs/research/scan-geometry-a.md`, especially the proposed experiment,
model-failure semantics, PDF object composition and sampling risks. Source paths
below are relative to `/Volumes/Glass/Book Conversion`; page numbers are
one-based PDF page numbers:

- `Raw Scans/Fundamentals of Musical Composition.pdf`, page 140 (printed 126):
  Ex.101 and Ex.102 give different staff lengths and positions, with note stems,
  accidentals, slurs and vertical barlines as fidelity checks.
- `Processed Books/Algorithm Design/Algorithm Design.pdf`, page 20 (preface xx):
  candidate straight-page control. Verify independent reference lines before
  calling it already correct. If unsuitable, name and verify a replacement;
  folder membership is not evidence of straightness.

Installed tools and versions are research observations, not this trial's
verification. Recheck the specific tools actually used. Prefer a small wrapper
around the installed Leptonica API over a new application or learned-model port.

## Done when

- Full-page 300 dpi lossless renders retain the complete visible PDF composition
  and margins. Source identities and SHA-256 digests match before and after.
  Record dimensions, DPI, tool versions and settings; upsampling adds no detail.
- Independently marked guides sample upper/middle/lower and left/centre/right
  geometry. Evaluation lines are distinct from fitted lines. Matched crops
  include staff spacing, barlines, stems, dots, faint marks and glyph widths.
- The unchanged render, rigid-deskew baseline and per-page vertical-only
  candidate are compared at the same scale. Horizontal correction, neighbouring
  model substitution, whitening, denoising and lossy recompression are off.
  Expose analysis mask, guides, model build/validity, field, displacement and
  sampler settings. A successful return with a copied image is reported as
  unsupported geometry, not correction.
- Assess held-out residual slope/curvature and local shape across the whole
  page. Check clipping, thin-detail loss, horizontal distances and barline
  geometry. Examine a forced candidate warp on the verified straight control
  as a diagnostic as well as the decision to leave it unchanged.
- Give the user ordinary image files or a small comparison PDF with matched
  views and crops. Ask whether the candidate improves within-page geometry
  beyond rigid deskew without unacceptable shape/detail changes. Record the
  response, including rejection or inconclusive evidence, in the running log
  and a durable experiment note at `docs/experiments/page-geometry.md`.
- Include and verify root Taskfile tasks once setup/build, explicit fixture
  rendering and repeatable comparison commands are concrete. Keep human guide
  marking and visual acceptance explicit; a numeric residual is not approval.
  Store disposable renders separately from authoritative source PDFs.

## Notes

This leaf succeeds by delivering a reviewable experiment and the human reaction,
even if the candidate fails. Do not turn it into a full-book processor, OCR
pipeline or review application. No first test book or numerical quality
threshold has been approved; these are candidate source pages.

Reject or mark inconclusive if model extraction/validity fails, within-page
residuals do not improve beyond rigid deskew, glyph or staff geometry worsens,
content clips, thin marks disappear, or the control is visibly degraded. A
better fitted staff alone cannot establish successful scanner-feed correction.
Preserve originals and usable unchanged outputs on unsupported geometry.

`corrected-book-k5` owns the next cut. Supply enough evidence to distinguish
automatic guide extraction, geometry-family and sampling failures. If this trial
cannot fit one focused session, decompose at a reviewable experiment boundary
rather than quietly adding algorithms or the whole expanded fixture set.
