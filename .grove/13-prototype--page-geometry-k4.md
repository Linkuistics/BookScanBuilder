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

Read preparation's working-command comparisons and automated result at
`docs/acceptance/prepared-pdf.md`, supplied by `prepared-pdf-k13` or its completed
children. The historical dependency-copy experiment is not that product's visual
acceptance. This session also owns obtaining any pending preparation response;
keep it distinct from the geometry reaction.

Installed tools and versions are research observations, not this trial's
verification. Recheck the specific tools actually used. Prefer a small wrapper
around the installed Leptonica API over a new application or learned-model port.

## Done when

- Full-page 300 dpi lossless renders retain the complete visible PDF composition
  and margins. Source identities and SHA-256 digests match before and after.
  Record dimensions, DPI, tool versions and settings; upsampling adds no detail.
- Independently marked guides sample upper/middle/lower and left/centre/right
  geometry. Before viewing any deskewed or candidate output, the executing
  session marks the unchanged render (with the user's input if a printed line's
  intent is uncertain) and freezes a coordinate record: source/render digests,
  pixel origin/units, line IDs, fit/evaluation roles, sampled points, marker and
  method. Save it as a machine-readable file with a marked unchanged image;
  record its digest before and after evaluation. Matched crops include staff
  spacing, barlines, stems, dots, faint marks and glyph widths.
- Withhold whole physical evaluation lines, including their full visible
  extent, from the disposable fitting analysis mask. Keep the retained RGB
  render untouched. Save the exclusion mask and detected fitting lines; verify
  no evaluation line entered the automatic fit. If withholding leaves too few
  lines/coverage for a valid model, the held-out comparison is inconclusive.
  An optional full-input fit is a separate diagnostic, never held-out evidence;
  do not weaken model validity merely to finish the experiment.
- The unchanged render, rigid-deskew baseline and per-page vertical-only
  candidate are compared at the same scale. Horizontal correction, neighbouring
  model substitution, whitening, denoising and lossy recompression are off.
  Expose analysis mask, guides, model build/validity, field, displacement and
  sampler settings. A successful return with a copied image is reported as
  unsupported geometry, not correction.
- Assess held-out residual slope/curvature and local shape across the whole
  page. Check clipping, thin-detail loss, horizontal distances and barline
  geometry. Separately exercise the same sampler on the straight control with
  a declared smooth vertical diagnostic field. Before inspecting output, save
  its mapping convention and bounded parameters, chosen to give spatially
  varying non-zero displacement and fractional source coordinates at the named
  detail crops without clipping their content. Expose the actual field and
  source coordinates so identity/copy/bypass cannot count as a sampler test.
  Verify displacement still exercises a non-identity mapping after the native
  sampler's coordinate rounding; otherwise the diagnostic is inconclusive.
  Compare against the intended mapping and separate deliberate diagnostic
  deformation from added sampling damage. This diagnostic chooses no production
  field and does not establish the control's correction policy. Also check the
  real policy leaves the verified control unchanged.
- Give the user ordinary image files or a small comparison PDF with matched
  views and crops. Ask whether the candidate improves within-page geometry
  beyond rigid deskew without unacceptable shape/detail changes. Record the
  response, including rejection or inconclusive evidence, in the running log
  and a durable experiment note at `docs/experiments/page-geometry.md`.
- Present any pending preparation source/output comparisons from the working
  command at useful zoom: music/faint detail, colour, margins, complete
  spread/landscape canvas and both explicitly assigned cover pages. Ask whether
  their visible appearance and canvas are preserved; record the user's
  preparation acceptance, rejection or inconclusive response, the inspected
  comparison/report paths and any specific defect in this leaf's running log
  and `docs/acceptance/prepared-pdf.md`. Record this separately from geometry
  acceptance. If the working comparisons are missing or the response is
  unavailable, identify that exact gap for `corrected-book-k5`; automated pixel
  equality alone cannot turn it into approval. A preparation rejection remains
  explicit even when the geometry candidate is accepted.
- Include and verify root Taskfile tasks once setup/build, explicit fixture
  rendering and repeatable comparison commands are concrete. Keep human guide
  marking and visual acceptance explicit; a numeric residual is not approval.
  Store disposable renders separately from authoritative source PDFs.
  Use `geometry:` task names. Record every wrapper and fixture dependency the
  durable recipes call. Retain a reproducible experiment wrapper outside the
  disposable output directory, or remove/replace its recipes and verify the
  replacement when discarding it. A recipe calling a discarded wrapper cannot
  survive. Extend the shared Taskfile containing preparation's `prepare:`
  recipes; reconcile setup dependencies and run changed/new tasks and all
  existing tasks affected by that combination before relying on it.

## Notes

This leaf succeeds by delivering a reviewable experiment and the human reaction,
even if the candidate fails. Do not turn it into a full-book processor, OCR
pipeline or review application. No first test book or numerical quality
threshold has been approved; these are candidate source pages.

Reject the automatic candidate for this fixture when a properly executed
comparison demonstrates extraction/model failure, no improvement over rigid
deskew, worsened glyph/staff geometry, clipping, thin-detail loss or unintended
control degradation. Failure only after the holdout exclusion is inconclusive
about the full-input automatic candidate and cannot be treated as acceptance.
Missing independent evaluation coverage, a failed measurement/setup or an
ambiguous/unavailable human reaction is also inconclusive: name the missing
observation and what would resolve it. A better fitted staff alone cannot
establish successful scanner-feed correction.
Preserve originals and usable unchanged outputs on unsupported geometry.

`corrected-book-k5` owns the next cut. Supply enough evidence to distinguish
automatic guide extraction, geometry-family and sampling failures. If this trial
cannot fit one focused session, decompose at a reviewable experiment boundary
rather than quietly adding algorithms or the whole expanded fixture set.
