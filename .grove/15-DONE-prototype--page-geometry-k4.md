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

## Completed preparation comparisons

`prepared-pdf-k13`/`prepared-pdf-k17` supply the complete command's frozen
synthetic/real/all reports in `docs/acceptance/prepared-pdf.md`. Use the all-v2
full-page and native 300-dpi zoom pairs under
`/private/tmp/bookscan-prepared-k17-all-v2`, especially music pages 2/3,
Norwegian's complete spread, Counterpoint's landscape canvas, and Strings
cover pages 1/4. Exact pixel equality is automated evidence; obtain and record
the separate preparation-specific visual response as already chartered above.
An external implementation review precedes this trial and creates integration
lazily if needed. Keep any rejection/inconclusive response for `corrected-book-k5`.

## Decisions (running log)

The existing charter is the experiment design: use installed Leptonica 1.87.0
through a small C wrapper, preserve full-page Poppler 26.10.0 RGB PNG renders at
300 dpi, and keep the wrapper separate from product code. No horizontal field,
cleanup, neighbouring model or learned port is included. Rigid skew is estimated
from the same held-out analysis mask. No production algorithm is selected.

Independent coordinates are being frozen in
`experiments/page_geometry_guides.json` before any candidate or deskew output is
generated. Holdouts conservatively erase complete rectangular bands around each
physical evaluation line, including its full visible extent; the RGB reference
remains untouched. The control's three independent baseline rows differ by
roughly 0–2 pixels across their sampled widths, consistent with an approximately
straight page at render/marking precision, not proof of perfect geometry. Its
trial policy will retain the unchanged image; a separately declared smooth
+/-2.25 pixel diagnostic field exercises the native sampler.

The first evaluation attempt (`/private/tmp/bookscan-geometry-k4-v2`) caught an
instrument defect: the independent sampler used float64 subtraction instead of
the native C float32 intermediate. Eleven RGB pixels straddled different
half-row boundaries. A one-variable diagnostic reproduced eleven mismatches
with float64 and zero with float32. Correct the checker, explicitly record that
arithmetic convention, and rerun all subjects frozen; v2 is not final evidence.
No guide points, field amplitude or detail crops are tuned after viewing output.
The holdout's four long music fitting lines are insufficient for the unchanged
minimum of fifteen. Add a separately labelled full-input diagnostic to determine
whether that failure is induced solely by exclusion; never treat it as held-out
validation or lower the required line count.

Final frozen experiment at `/private/tmp/bookscan-geometry-k4-final` completed
with matching before/after subjects and coordinate digests. The frozen record is
`4d718063df70d4ac59cfdb36fe471acda11ee9ef0d4022d070e31110fb928cb2`.
All independent points, crop boxes, source/render/marked/mask hashes agree with
the original pre-output v2 freeze; only the diagnostic's arithmetic declaration
was clarified. The held-out music fit found four long lines; full-input diagnostic
found one. Both failed the unchanged minimum of fifteen and produced exact RGB
copies. Recommend rejecting this automatic extractor for this fixture; the
held-out geometry comparison alone is inconclusive, and this does not reject
all line-guided or vertical-field methods. Control fit built a valid model with
32 long lines but supplies no music result. The trial control policy keeps an
exact unchanged copy. The forced diagnostic agrees with an independent sampler
at every RGB channel, has 4,145,240 nonidentity integer-row mappings, nonzero
fractional coordinates in all named detail crops and no out-of-bounds reads.
This verifies the integer sampler convention, not absence of sampling damage.

Presented separate lossless PDFs `geometry-review.pdf` (12 pages) and
`preparation-review.pdf` (16 pages) in that final directory. Their decoded RGB
streams were rechecked against every source PNG; preparation uses the current
`/private/tmp/bookscan-prepared-k19-all` working-command comparisons. Asked for
separate geometry and preparation reactions, recommending automatic-extractor
rejection and preservation acceptance only if the visual pairs agree.

All new geometry tasks ran successfully, the experiment passes Ruff, and shared
`prepare:setup`/`prepare:check` passed (231 tests, Ruff and strict pyright). Neither
preparation implementation nor its existing task commands were changed. The
retained C/Python/JSON wrappers are all dependencies of the new recipes; renders,
binary and convenience review PDFs remain disposable outside the collection.

No reply arrived to either visual question during the review window. Record
both human dispositions as inconclusive because the response is unavailable,
not acceptance, human rejection or permission inferred from silence. The exact
views/questions and recommendations are retained in the experiment and
preparation acceptance notes, and explicitly handed to `corrected-book-k5`.
That live consumer already owns missing/inconclusive-response completion, so
no duplicate speculative leaf is needed. The bounded trial can end on its
technical extraction-failure evidence plus that explicit human-evidence gap,
as its charter permits; root acceptance and production choices remain open.
The root still has live `corrected-book-k5`; no parent node closes in this cascade.
The throwaway experiment does not earn a separate product review chain.
