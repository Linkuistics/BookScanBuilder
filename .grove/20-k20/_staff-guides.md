# staff-guides-k20 — brief


## Goal

Determine whether independently traced music staff lines can supply a valid
per-page vertical model that improves held-out geometry beyond rigid deskew
without damaging notation or RGB detail. Isolate the demonstrated automatic
extraction failure; deliver a bounded two-page comparison and human reaction,
not a production processor or an automatic music detector.



## Context

- `page-geometry-k4`, `corrected-book-k5`, `docs/experiments/page-geometry.md`
  and its frozen JSON report/coordinate records; `docs/research/scan-geometry-a.md`.
- Music source: `/Volumes/Glass/Book Conversion/Raw Scans/Fundamentals of
  Musical Composition.pdf`, full-page RGB 300 dpi. Select one suitable music
  fixture through the preflight below. Page 140 (printed 126) remains the
  historical extraction/unsupported-layout diagnostic, not the required fitting
  fixture. Control: `Processed Books/Algorithm Design/Algorithm Design.pdf`,
  PDF page 20, relative to that collection. Recheck identities and suitability.
- `docs/acceptance/prepared-pdf.md` and current k19-all comparisons. Separate
  pending geometry/preparation views are
  `/private/tmp/bookscan-geometry-k4-final/geometry-review.pdf` and
  `preparation-review.pdf`. If disposable files disappeared, reproduce the
  exact views through retained recipes before seeking judgment.
- Existing `geometry:` recipes and retained experiment wrappers are the
  reproducibility seam. Check the installed builder's actual trace-input path
  before modifying it; do not infer an API from memory.

## Done when

- Before fitting or viewing new outputs, deliver a coordinate-only preflight
  on the complete unchanged render. The user confirmed in `corrected-book-k25`
  that fixture selection must preserve the validity rules. Inspect the previously
  surveyed music pages 20, 40, 60, 100, 180 and 220 for suitability, then select
  ONE page that can supply long fitting rules and separated held-out units under
  these rules; record exact PDF/printed page, dimensions and source/render hashes.
  This is bounded fixture selection, not six correction trials. Retain page 140
  as an unsupported-layout diagnostic; its short outer systems leave roughly
  42% vertical coverage after longest-line filtering. Do not relax a gate to fit
  it. If no suitable fixture is found in this inspected set, report that bounded
  selection gap to k21 without claiming the whole book unsuitable.
  Verify the trace-input entry against pinned Leptonica 1.87.0 source: the
  existing wrapper has no such input, and
  `dewarpFindVertDisparity` omits the builder's prerequisite gates. Name the
  entry used and reproduce the builder's 0.8 longest-line filtering, configured
  fifteen-long-line minimum and coverage test for supplied fitting traces.
  With whole held-out units removed, report unique retained counts, first-point
  positions, counts in each page half (at least four each), and vertical span
  divided by full image height (strictly greater than 0.50). Preserve the
  library's coordinate/rounding semantics and default downstream model checks.
  Retain the coordinate lists and separation overlay even if preflight fails.
  A failed prerequisite or trace seam infeasible within the bounded trial is
  inconclusive for this hypothesis, with the exact coverage/acquisition/
  instrument gap handed to `corrected-book-k21`; do not build a forced real fit
  or require a warp review
  to establish a prerequisite failure. A full-input diagnostic cannot substitute
  for the held-out preflight.
- State and test this hypothesis: the existing vertical family may be usable
  when genuine staff traces replace the failed text-line extractor. Keep the
  existing model family, vertical-only application, default validity checks,
  fifteen-long-line minimum and native RGB sampler. Changing guide acquisition
  is the independent variable. No neighbouring model, two-axis field, alternate
  interpolation, appearance cleanup, crop or lossy recompression is added.
  On the selected fixture retain the existing automatic extractor's diagnostics
  under the same settings and holdout exclusions as the manual candidate. Compare
  acquisition on that page; historical failure on page 140 is not a matched
  automatic baseline for a different page. Manual success there cannot establish
  correction on page 140 or repair of automatic music extraction.
- On unchanged complete renders, independently trace individual physical staff
  rules across upper/middle/lower and left/centre/right content, distinguishing
  notation beams/slurs from rules. Freeze source/render digests, pixel origin,
  units, dense trace points, uncertainty, marker/method and fit/evaluation roles
  BEFORE viewing the new outputs. Give the selected page new physical line/unit
  identities and the same pre-output freeze. Original page-140 manual
  blue reference points are diagnostics, not already adequate dense fit traces.
  Admit visually placed dense points on genuine physical rules; declare sampling
  density and handling of obscured segments without inventing observations
  through notation. Independently repeat a representative subset across page
  bands and fitting/evaluation roles without showing the first marks, before
  output, and retain both passes to measure positional/slope/curvature
  repeatability. Seeded pixel snapping or automatic extraction is a different
  acquisition experiment, not independent manual traces; commission it only
  through a fresh planning question with its own extraction evidence.
- Hold out complete staffs or systems, including every physical rule in the
  chosen unit over its whole extent and a declared exclusion zone. Keep units
  in upper/middle/lower bands where the fixture permits; record any missing band
  as a coverage limitation. Supply only fitting traces outside these zones;
  retain their nearest distances to each held-out unit, lists and overlays.
  Close-rule interpolation alone cannot establish separated-region performance.
  No duplicate traces, borrowed evaluation points, cropped canvas, shortened
  long rules, weakened holdouts, lowered minimum or forced-valid fit may
  manufacture support. Choose roles and check counts/coverage before output;
  inadequate separated holdouts are an inconclusive coverage result, not a
  reason to move holdouts after viewing output. A full-input fit is diagnostic.
- Compare unchanged, rigid deskew and traced candidate at matched scale. Retain
  raw traces, model status, actual field/mapping and settings in ordinary files.
  Measure held-out slope/curvature and local scale/shear, and independently
  inspect output staff/barline positions and native RGB crops. Separate
  transported source-guide residuals from independently marked output evidence.
  Check five-line spacing, barlines, stems, dots, accidentals, glyph widths,
  faint marks, borders, content clipping and extrapolation between systems.
  Report differences from rigid deskew alongside measured trace/output-marking
  uncertainty and repeatability; source-guide transport is not independent
  output ground truth. An indistinguishable difference is inconclusive for
  improvement, not support or rejection. Do not invent an agreed numerical
  acceptance threshold.
- Keep the verified control unchanged under the declared trial policy. Retain
  the predeclared nonzero fractional-coordinate forced sampler diagnostic from
  k4 and its actual nonidentity rounded mappings at upper/middle/lower crops;
  an identity/copy is insufficient. Report deliberate diagnostic deformation
  separately from additional detail damage. Recheck mapping arithmetic when
  the wrapper changes; matching mapping alone does not grant visual approval.
- Classify the traced result by the first applicable outcome below, recording
  later observations separately rather than merging causes:
  - Failed guide/separation prerequisites or an infeasible trace-input seam:
    inconclusive coverage/acquisition/instrument question, handed to k21 for
    precise completion or a suitable fixture; no model-quality conclusion.
  - With prerequisites met, builder/default model checks fail: reject this
    configured fit, record the actual check and hand k21 a model-failure
    question. This supplies no sampler or two-axis evidence.
  - A valid fit cannot be applied or produces a fallback copy: inconclusive
    application/instrument question, requiring bounded seam repair/recomparison
    under the same settings. Record statuses and actual mapping so a copied
    image cannot masquerade as correction.
  - A valid applied comparison shows independently observed shape/detail damage,
    clipping, control degradation or an explicit adverse traced-view reaction;
    alternatively, adequate measurement establishes no useful improvement:
    reject for that specific quality failure and hand k21 its supported next
    question. A valid intentionally identity result is not a fallback copy and
    establishes no improvement on a distorted fixture.
  - With no independently established quality defect, a valid applied
    comparison's improvement cannot be distinguished from measured uncertainty:
    inconclusive measurement question, handed to k21 for precise repeatability/
    measurement completion; no automatic expansion.
  - Technical support with an unavailable/ambiguous traced-result reaction:
    inconclusive visual question, handed to k21 for the exact inspected-view
    response; silence grants nothing.
  - Only adequate prerequisites, a valid applied model, improvement resolved
    against measured uncertainty, intact independent shape/detail/control checks
    and an explicit favourable traced-result reaction support further trial.
  Invalidity/application failure is not an uncertainty-only comparison; no
  copied or unsupported output supports expansion. Preserve the unchanged usable
  image. Record extraction, coverage, model, sampling, measurement and human
  gaps separately without claiming all line-guided correction failed.
- Present full-page/native-detail ordinary images or a small matched PDF and
  obtain the user's reaction to the traced result. Also retain/ask the prior
  geometry question: do k4's music/rigid/control-sampler views support rejecting
  its automatic extractor without a render/detail concern? Record inspected
  views, acceptance/rejection/ambiguity and concrete defects in a durable
  experiment note and this running log. Missing response remains explicit and
  passes to `corrected-book-k21`; it does not justify expanded trials by default.
- Independently ask the preparation question if still unresolved: do the
  current working-command pairs preserve music/faint marks, colour, margins,
  the complete Norwegian spread and Counterpoint landscape canvas, Algorithm
  Design and both assigned Strings covers? Record the response and views in
  `docs/acceptance/prepared-pdf.md` and this log, separately from geometry.
  Preserve any rejection/defect or unavailable response for `corrected-book-k21`;
  do not repair preparation inline or infer assent from equality or silence.
- Keep originals untouched and disposable artifacts outside the collection.
  Finish every instrument edit before the frozen run; digest every read subject
  before/after and verify per-item records, with one writer. Extend verified
  `geometry:` tasks only for concrete recipes, retaining all called wrappers.
  Run new/changed and affected existing tasks, including shared preparation
  checks when dependencies/Taskfile change. A bounded trial may retire with
  rejected/inconclusive evidence and an explicit handoff; no root acceptance
  or production commitment follows from that retirement.

## Notes

Automatic k4 music fits had four held-out and one full-input long lines, both
invalid and unchanged copies. The control's valid fit supplies no music result;
its forced sampler matches declared integer mapping but has no human fidelity
approval. This evidence earns exactly the staff-trace question. If the traced
result later justifies sampler or two-axis work, let the fresh planning consumer
cut that specific hypothesis. Do not commission the expanded set here.

If this work exceeds one session, decompose at the complete coordinate-only
evidence seam: the first child freezes admissible acquisition, repeatability,
whole-unit holdouts, exact preflight and its inspected source overlays; the
remaining prototype owns the trace-input comparison and human reactions.
State the unresolved gap and keep that child and `corrected-book-k21` live in
order. Do not create a standalone adapter, tracing UI or setup-only child, and
do not call coordinate evidence a completed corrected-image trial. An infeasible
preflight may itself be the bounded inconclusive result consumed by k21.

## Decomposition and bounded outcome

`staff-coordinates-k26` delivers the complete source-acquisition diagnostic
boundary. Its first dense visual pass failed native source verification:
occluded/outside-rule observations and 4–6-pixel representative discrepancies
make its coordinates inadmissible. Exact native numerical gates pass only on
those rejected records. This triggers the first ordered outcome, inconclusive
acquisition; it is not a model or sampler rejection. No real fit was forced,
and no correction-only child was cut after that prerequisite failure.

The bounded trial can close on that expressly allowed failure branch. Its
durable result is `docs/experiments/staff-guides.md`, with source overlays,
first/final coordinate records and exact native diagnostic reports. `k21`
owns the precise source-marking/repeatability completion before a fresh frozen
preflight, then the still-unperformed matched fit/output comparison if justified.
Both historical visual questions were answered “Not inspected yet” and remain
unresolved; the new source-overlay question has no recorded response. These
obligations are promoted to the root brief and k21 before retirement; neither
completion of k26 nor node closure grants an accepted correction or music
expansion. Root appearance/processor/acceptance work stays live.
