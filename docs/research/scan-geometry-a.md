# Correcting geometry in scanned book pages

Research for scan-geometry-k2, inspected 11 October 2026. This survey informs the
next correction trial; it does not select a production algorithm. No correction
method was run on a collection page during this research.

The cheapest useful first experiment is **Leptonica's per-page vertical
disparity model on two real pages**, compared with an unchanged render and rigid
deskew. It is already installed, exposes its model, and separates a binary
analysis image from the visible colour image. Music-line extraction, horizontal
shape preservation, and sampling quality remain reasons this experiment could
fail. A successful result would justify a broader trial; it would not establish
that scanner-feed distortion is solved.

## What was inspected

Paths below are relative to /Volumes/Glass/Book Conversion. Page numbers are
one-based PDF page numbers, not printed page numbers. Observations come from
full-page Poppler PNG renders, initially at up to 1800 pixels on the long edge;
the stronger music candidate was also rendered at 300 dpi. These are visual
observations, without measured line fits or ground-truth flat scans.

| Source | PDF pages inspected | Finding and role |
| --- | --- | --- |
| Raw Scans/Fundamentals of Musical Composition.pdf | 20, 40, 60, 100, 140, 180, 220 | Music, prose, thin rules, accidentals, slurs and show-through. Page 140, printed 126, has visibly sloping and curved staves across successive systems; it is a stronger trial candidate than the initial page 20. The short Ex.101 and longer Ex.102 systems supply different positions and lengths for checking residual geometry. |
| Raw Scans/Garbage Collection - Algortihms for Automatic Dynamic Memory Management.pdf | 30 | Prose, indented Pascal code, boxes and arrows on one page. Use to check that straightening text does not shear diagrams or change code indentation. |
| Needing Cleanup/Counterpoint in Composition.pdf | 20 | One printed page, two text columns, on a landscape canvas with scanner background. It must not be split into two book pages. |
| Processed Books/Norwegian - An Essential Grammar (Routledge)/Norwegian - An Essential Grammar (Routledge).pdf | 20 | Genuine spread, printed pages 36–37, with visible geometry change near the gutter. Independently assess each half. English parenthetical examples provide later OCR targets. |
| Processed Books/Algorithm Design/Algorithm Design.pdf | 20 | Printed preface page xx, apparently straight single-column text. Candidate already-correct control; verify its reference lines before accepting that designation. |
| Covers/SchoenbergComposition.pdf | 1 | Colour cover, sparse large lettering, coloured rules and scanner background. A fidelity and uncertain-geometry case, not a dense-text fitting fixture. |

Object inspection adds two important constraints. Music PDF page 20 contains an
851×1220 RGB JPEG at 150 ppi **and a separate 1288×1844 stencil at 300 ppi**.
Algorithm Design page 20 contains a 2159×2448 one-bit JBIG2 image at 300 ppi;
the Norwegian spread has a 2633×1976 grayscale JPEG at 220 ppi. These are the
observed PDF objects, not evidence of how they were originally scanned or
whether earlier compression was lossless. Taking only the first image object
would omit part of the music page's visible composition. Use a full-page render
as the trial's reference; preserve the original PDF as the authority.

Repeated pdftotext extraction of the three page-20 samples in Processed Books
and Needing Cleanup produced one byte each, with no meaningful text. This
establishes no useful extracted text on those pages, not an absence of OCR
throughout their books. Prior processing and folder names establish neither
correct geometry nor reliable OCR.

## Three different geometry problems

**Rigid skew** is one rotation applied to the whole page. Rotation and affine
or perspective transforms are useful baselines, but an affine transform maps
straight lines to straight lines and a homography also preserves straightness.
Neither can straighten a curved staff. A homography can change the apparent
angles of straight lines, so differing slopes alone do not prove a nonlinear
defect. Compare residual curvature as well as angles.
[OpenCV's transform reference](https://docs.opencv.org/4.13.0/da/d54/group__imgproc__transform.html)
documents the relevant transforms and sampling conventions.

**Rotation during scanner feed** is a changing acquisition geometry. A smooth
two-dimensional displacement field can represent changing line directions;
a sequence of independently rotated strips risks discontinuities at their
joins. This is a mathematical modelling inference, not a diagnosed acquisition
history for page 140. Text or staff horizontality constrains only part of the
mapping: many transformations straighten the same lines while changing widths,
vertical strokes or spacing. A vertical-only correction must therefore be
checked against barlines, glyph shape and horizontal distances.

**Bound-book gutter distortion** comes from the page surface and acquisition
geometry. Cylinder or sheet models have a physical rationale here. They are
not automatically appropriate for cut-up sheets moving during acquisition.
The Norwegian fixture and music fixture test different hypotheses; success on
one cannot stand in for the other. ScanTailor's own FAQ says dewarping cannot
handle both pages of a spread together and documents a case needing manual
adjustment. Split genuine spreads before evaluating single-page models.
[ScanTailor FAQ](https://github.com/scantailor/scantailor/wiki/FAQ)

## Practical approaches

| Approach | Varying geometry within a page | Practical place in this trial |
| --- | --- | --- |
| Rigid deskew, optionally perspective rectification | One global transform; no curved-line correction | Required baseline. It may be all an already-correct or simply tilted page needs. |
| Leptonica disparity model | Spatially varying vertical field, optional horizontal field | Preferred inexpensive candidate, with explicit per-page diagnostics. |
| ScanTailor Advanced | Nonlinear cylindrical surface mapping with automatic/manual guides | Useful manual comparison and gutter candidate; its geometry family is constrained. |
| Zucker/lmmx page-dewarp | Camera pose plus cubic sheet shape | Locally launchable gutter comparison; supplied renderer does not meet colour preservation. |
| DocGeoNet | Learned dense two-axis backward mapping | Broader representational capacity; a heavier, unverified local port. |
| A constrained line-guided remap | Field chosen from independent line constraints | Fallback prototype if library geometry is insufficient; an engineering hypothesis, not an existing automatic solution. |

For rigid deskew and a custom remap, the walk-away result is likewise ordinary
PNG/TIFF/PDF output. A plain matrix or coordinate field remains legible without
OpenCV, although re-rendering needs a compatible sampler and its settings.

### Leptonica: inspect the model, not just the output file

The model fits long line centres with quadratics, then fits disparity samples
in the other direction. It can represent line slope changing with page height,
not just one angle. Horizontal correction assumes nearly left/right-justified
line ends. The builder removes short lines and rejects inadequate line coverage;
those restrictions make sparse layouts and indented code important challenges.
[Leptonica 1.87.0 model builder](https://github.com/DanBloomberg/leptonica/blob/1.87.0/src/dewarp2.c)

The default minimum is 15 long lines. The multi-page machinery can substitute a
neighbouring page's valid model. For sheets whose feed motion may differ, that
substitution is an unjustified extrapolation: keep models local to each page
in the trial. The library also serializes its models.
[Leptonica configuration and serialization](https://github.com/DanBloomberg/leptonica/blob/1.87.0/src/dewarp1.c)

The single-page API analyzes a binarized copy but applies the field to the
supplied page image. It supports vertical-only use and checking for columns.
Critically, a failure to build a vertical model can return **zero and a copy of
the source**. Record model construction and validity, actual displacement and
output existence; process exit status alone is insufficient.
[Single-page API and validation](https://github.com/DanBloomberg/leptonica/blob/1.87.0/src/dewarp4.c)

Its native sampler accepts binary, gray and RGB images but rounds source
coordinates to integers. That creates a plausible thin-line aliasing risk;
it is not an observed failure on this collection. Preserve this sampler as a
comparison, and evaluate an interpolated RGB sampler only if the native result
damages detail. Coordinate signs must match: the vertical sampler reads source
row y minus the field value. It also exposes box transformation, which is not
enough to guarantee correct glyph placement after a nonlinear warp.
[Leptonica sampling and box mapping](https://github.com/DanBloomberg/leptonica/blob/1.87.0/src/dewarp3.c)

**Walk-away:** corrected PNG/TIFF images and reconstructed searchable PDFs
remain readable without Leptonica. A library-specific serialized model needs
the library or its documented reader; retain source references and ordinary
line/transform data if editability beyond the tool matters.

### ScanTailor Advanced: a useful manual comparison, not an unrestricted mesh

The inspected implementation uses two boundary curves, a homography through
their four endpoints, an arc-length mapping and transformations along surface
generators. Its nonlinear mapping goes beyond deskew. It remains a particular
surface family, not arbitrary scanner-motion recovery; that suitability must
be tested, even when a manual grid appears straight.
[Cylindrical surface implementation](https://github.com/ScanTailor-Advanced/scantailor-advanced/blob/5eaac1884cdcabb6514bd632114f688631bd8dbc/src/dewarping/CylindricalSurfaceDewarper.cpp)

Automatic tracing filters short/out-of-bounds/inconsistent curves and its
content-bound detection is explicitly sensitive to clutter and speckles.
Music and diagrams supplying unintended curves are therefore a fitting risk,
an inference requiring a trial, rather than a measured failure rate.
[Text-line tracer](https://github.com/ScanTailor-Advanced/scantailor-advanced/blob/5eaac1884cdcabb6514bd632114f688631bd8dbc/src/dewarping/TextLineTracer.cpp)
Colour output and illumination/binarization/despeckling are separate paths in
the output code. A fidelity comparison must disable unwanted appearance
changes and inspect margins; choosing dewarping alone is not evidence that
all other cleanup is off.
[Output implementation](https://github.com/ScanTailor-Advanced/scantailor-advanced/blob/5eaac1884cdcabb6514bd632114f688631bd8dbc/src/core/filters/output/OutputGenerator.cpp)

A maintained Mac packaging repository provides a Homebrew recipe and an
Apple Silicon build example. ScanTailor and its Qt stack were not installed or
built here; the recipe is feasibility evidence, not a verified installation.
[Mac packaging instructions](https://github.com/yb85/scantailor-advanced-osx)

**Walk-away:** exported TIFF/page images remain legible. The project and manual
grid need ScanTailor to edit; neither exports searchable PDF/OCR by itself in
the inspected workflow, so retain images and downstream PDFs as durable output.
[Project README](https://github.com/ScanTailor-Advanced/scantailor-advanced/blob/5eaac1884cdcabb6514bd632114f688631bd8dbc/README.md)

### page-dewarp: a small camera-sheet model with a fidelity trap

Zucker sweeps one cubic cross-section along the page and optimizes camera pose
and line positions. He explicitly reports horizontal compression where the
surface slope is large because the parameterization is not by arc length.
That documented limitation matters to music spacing and letter proportions.
Arbitrary feed variation is outside the stated physical model; this is an
inference about its assumptions, not a collection trial result.
[Author's method and limitations](https://mzucker.github.io/2016/08/15/page-dewarping.html)

The Python 3 continuation is available on PyPI, with CPU dependencies and
optional JAX acceleration. Version 0.3.4 successfully launched its CLI here in
an isolated uv environment on Python 3.12.15. This checked installation and
startup only.
[Current project](https://github.com/lmmx/page-dewarp)

The inspected remapping code converts the input to gray **before** checking
NO_BINARY. Disabling thresholding therefore still loses colour; the installed
0.3.4 class confirms that sequence. Its supplied output cannot be the visible
colour-preserving pipeline. Reusing only the estimated field with an RGB
renderer would be additional work.
[Remapping implementation](https://github.com/lmmx/page-dewarp/blob/a62c15c8c1fba0bc78ed1e00398fdedf3db93add/src/page_dewarp/dewarp.py)

The loader skips images with no spans, uses a line-detection fallback when too
few text spans exist, and has a fallback for negative estimated page dimensions
referencing issue 9. A written file and a small fitting loss do not establish
plausible page shape.
[Loader and fallback](https://github.com/lmmx/page-dewarp/blob/a62c15c8c1fba0bc78ed1e00398fdedf3db93add/src/page_dewarp/image.py),
[reported dimension failure](https://github.com/lmmx/page-dewarp/issues/9)

**Walk-away:** PNG/TIFF output remains readable, subject to those lost appearance
properties. JSON parameters are readable without the package, but re-rendering
still requires the projection model; JSON alone is not a complete corrected
image or PDF.

### DocGeoNet: a two-axis field, with untested acquisition assumptions

The authors train on Doc3D and supply pretrained weights and evaluation on
DocUNet/DIR300. Those sources do not establish performance on cut-up feed scans
or this music collection.
[Official repository](https://github.com/fh2019ustc/DocGeoNet)

The inspected inference script predicts a backward field from a 256×256 image,
upsamples/smooths that field and samples the original-resolution RGB image.
It does not simply export a 256-pixel page or synthesize replacement text.
The field resolution is nevertheless a limitation to test on abrupt local
changes. The script hardcodes CUDA in both checkpoint loading and model/input
placement. CPU/MPS execution requires a port and testing, not merely installing
PyTorch on this Mac. No such port, weight download, timing or fidelity trial was
performed here.
[Inference script](https://github.com/fh2019ustc/DocGeoNet/blob/ead1d371b3c6eefdc054b4d6e633e561c83ef80e/inference.py)

**Walk-away:** output PNGs and reconstructed PDFs are ordinary files. Repeating
the prediction needs code and weights; retain the estimated coordinate field
as well as images if independent re-rendering is required. It is a later
candidate if simpler geometry fails, not the smallest first trial.

## Failure cases and handling uncertainty

The following are trial obligations. Where evidence establishes only a model
assumption, the consequence is explicitly a risk to test.

| Content | Evidence and concern | What the experiment should inspect |
| --- | --- | --- |
| Music staves | The existing text-line/curve extractors are not an established music-aware detector. Their filtering and morphology can accept unintended rules or combine notation; this is an inference from the [Leptonica builder](https://github.com/DanBloomberg/leptonica/blob/1.87.0/src/dewarp2.c) and [ScanTailor tracer](https://github.com/ScanTailor-Advanced/scantailor-advanced/blob/5eaac1884cdcabb6514bd632114f688631bd8dbc/src/dewarping/TextLineTracer.cpp). | Trace overlays must follow individual staves, not slurs/beams. Check five-line spacing, accidentals, note stems, dots and vertical barlines. |
| Sparse pages | Minimum line counts and coverage checks can reject a model; [Leptonica defaults](https://github.com/DanBloomberg/leptonica/blob/1.87.0/src/dewarp1.c) and [page-dewarp's no-span branch](https://github.com/lmmx/page-dewarp/blob/a62c15c8c1fba0bc78ed1e00398fdedf3db93add/src/page_dewarp/image.py) make that concrete. | Preserve the page when unsupported. No automatic blank deletion; inspect extrapolation into large empty regions. |
| Columns and code | Column checking exists in the [Leptonica single-page API](https://github.com/DanBloomberg/leptonica/blob/1.87.0/src/dewarp4.c); justified-edge assumptions are unsuitable evidence for intentional indentation. | Keep horizontal correction off initially. Check each column independently, shared geometry across columns, and the code's indentation and glyph aspect ratios. |
| Diagrams | Line evidence does not encode whether a curve was deliberately printed. This is a modelling ambiguity illustrated by the inspected code/diagram page. | Exclude diagram curves from guides; check boxes, arrows and illustrated curves before and after. |
| Faint printing and colour | The [page-dewarp renderer](https://github.com/lmmx/page-dewarp/blob/a62c15c8c1fba0bc78ed1e00398fdedf3db93add/src/page_dewarp/dewarp.py) discards colour. OCRmyPDF documents artifacts from background removal and final cleanup. [Cookbook](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html) | Analyze a disposable mask; render from the retained visible image. Disable whitening, denoising, final cleanup and lossy recompression in the geometry comparison. |

Proposed review signals are unsupported regions, too few/inconsistent guides,
large corrections, disagreement between independent guides, nonpositive mapping
Jacobian or extreme local scale/shear, out-of-bounds content, and worsened
held-out lines. These are proposed safeguards, not calibrated confidence
scores. Better fitting residuals on the same lines used to estimate a field
can reward overfitting. Hold out lines and inspect an already-correct control.
Unknown or rejected geometry should leave the visible page unchanged and flag
it for review; acceptance of a manual adjustment must affect the final image
and its OCR, not only a preview.

## OCR must follow the accepted visible geometry

The constraint is geometric: OCR positions must describe the image finally
exported after split, crop, warp and review. Keeping old text boxes while moving
pixels breaks alignment. For a nonlinear field, transforming only rectangle
corners cannot establish where all glyphs lie. Re-recognizing the accepted
image is the simplest experiment; reuse of old OCR would need its own alignment
evidence. This is an interface constraint, not a selected pipeline interface.

OCRmyPDF's skip mode copies pages with text without processing; it cannot be a
blanket policy for previously processed pages needing new geometry. Redo mode
replaces detected invisible OCR while retaining visible text. Force mode
rasterizes everything, including visible text/vector content. These distinctions
must be evaluated against mixed PDF objects and actual changed page images;
no mode alone supplies the nonlinear correction.
[Existing-text modes](https://ocrmypdf.readthedocs.io/en/latest/advanced.html)

OCRmyPDF distinguishes cleaning its OCR input from altering the final visible
image; its cookbook also specifies its own preprocessing order. Avoid a later
untracked rotation/deskew of only the OCR working image. Tesseract can emit a
searchable image PDF and hOCR/TSV coordinates from the corrected image, enabling
a small alignment trial without choosing an OCR orchestration framework.
[OCRmyPDF preprocessing](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html),
[Tesseract outputs](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)

Test search and selection in the exported PDF, not just recognized strings:
English phrases at top/middle/bottom and near both lateral edges, word boxes
overlaid on the final render, then selection in a PDF viewer. Check points
versus pixels, DPI, PDF origin, page rotation and crop offsets. Any later review
edit invalidates positions for the affected page. Use lossless images in the
trial; OCRmyPDF's higher optimization levels permit lossy changes and its PDF/A
conversion can change image encoding.
[Optimization behavior](https://ocrmypdf.readthedocs.io/en/latest/optimizer.html)

The OCR walk-away check is straightforward: searchable PDFs remain usable in
ordinary PDF readers after Tesseract or OCRmyPDF is uninstalled; hOCR/TSV also
remain readable text. Keep the accepted images and sources as well.

## Smallest experiment that can reject the preferred candidate

The first bounded prototype needs two source pages, no full book processor or
review application:

1. Render Music Composition PDF page 140 and Algorithm Design PDF page 20 at
   300 dpi into lossless RGB/gray PNGs. Verify the control has straight,
   consistently aligned text before using it. Keep full visible content and
   generous margins; crop and appearance cleanup would confound this test.
2. Record independently marked staff/text reference lines across the upper,
   middle and lower page, including points at left, centre and right. Include
   vertical barlines and a few glyph/detail crops. Use separate lines for model
   fitting and evaluation. Save source identities, coordinates and settings.
3. Produce unchanged, rigid-deskew and Leptonica vertical-only results at the
   same pixel scale. Use one page model at a time, expose analyzed binary mask,
   detected guides, model validity, field and sampler. Do not count a copied
   page as correction. Begin with automatic extraction; if it fails on music,
   that rejects the automatic candidate for this fixture.
4. Compare held-out line curvature and slope at all three heights and widths,
   rather than averaging one page angle. Inspect barline perpendicularity,
   staff spacing, note stems, dots, faint marks, letter widths and page edges
   at matched magnification. A user comparison remains necessary. No numerical
   threshold has been agreed, so record pixel residuals and local scale without
   converting them into an invented acceptance score.
5. Reject this candidate if it cannot estimate reliable geometry, fails to
   improve residual within-page distortion over rigid deskew, produces stretched
   glyphs/diagram shapes, clips content, loses thin marks or introduces visible
   changes on the straight control. A bypassed control checks the decision
   policy, not the sampler; also examine what a forced candidate warp would do
   to the control in this diagnostic experiment.

This falsifies whether the existing automatic model is a useful first path.
It does not prove all line-guided models impossible if extraction fails. A
small follow-up may supply manually traced staff points to separate extraction
failure from model failure. If vertical-only geometry straightens staves but
leaves barlines or character widths wrong, the next question is a constrained
two-axis mapping; a prettier staff is insufficient evidence to proceed.
OpenCV remap can apply such an estimated field with explicit interpolation
and borders, but does not estimate the field or provide an acceptance policy.
[Remap API](https://docs.opencv.org/4.13.0/da/d54/group__imgproc__transform.html)

Only after that core test survives, extend the same settings and diagnostics
to the Norwegian spread's two manually separated halves, Garbage Collection
page 30, Counterpoint page 20, Music page 40 and the cover. That expansion
checks gutter distortion, diagrams/code, columns, prose/faint printing and
colour/sparse pages. It also checks an appropriate unchanged outcome for
unsupported covers. It precedes an algorithm commitment.

Then add a tiny searchable PDF from accepted images and verify the English
positions described above. Include a fixture with earlier OCR before adopting
an existing-text policy: the inspected one-byte samples do not exercise that
case. A final integration trial must receive one prepared PDF with assigned
covers, preserve assembly order, and work without collection-folder access.
Rendering source pages directly here is fixture discovery, not a change to
that agreed two-stage boundary.

## Local dependencies and reproducibility

Observed host: arm64, macOS 27.0.1 (26A434), Apple clang 21.0.0.

| Component | Direct local evidence | Smallest next requirement |
| --- | --- | --- |
| Poppler | Homebrew 26.10.0; renders, object listings and text extraction ran | Reuse installed pdfinfo/pdftoppm/pdfimages/pdftotext. |
| Leptonica | Homebrew and pkg-config report 1.87.0 | A small prototype wrapper around the C API; library availability is verified, compilation and correction are not. |
| Tesseract | Homebrew 5.5.3; eng, osd, snum listed | eng is available for the alignment experiment. OCR was not run here. |
| OpenCV for an alternate sampler | Installed as a dependency of the isolated page-dewarp environment | Pin the tested environment before comparing interpolation; no global OpenCV formula is needed for that environment. |
| page-dewarp | 0.3.4 CLI help and installed remapping source inspected under uv/Python 3.12.15 | No JAX/GPU is needed for initial startup; actual optimization timing remains unknown. |
| ScanTailor / OCRmyPDF | Not found as shell executables during the probe | Optional later installations. Mac recipes exist; neither is needed for the first geometry test. |
| DocGeoNet | Sources inspected, no local execution | Weights, pinned dependencies, explicit device port and local inference validation. |

The probe distinguishes missing shell commands from an exhaustive search of
applications/environments. No claim is made that the Mac has no other copy.

The verified render recipe, with input paths explicitly supplied, is:

```sh
pdftoppm -f 140 -l 140 -r 300 -singlefile -png \
  '/Volumes/Glass/Book Conversion/Raw Scans/Fundamentals of Musical Composition.pdf' \
  /tmp/music140
```

It produced a 1720×2459 PNG. Useful inspection recipes are pdfimages with
-f/-l/-list and pdftotext with -f/-l and a separate output path. Do not treat
150/220 ppi source images rendered at 300 dpi as newly acquired detail.
The CLI-only package check was:

```sh
uv run --no-project --python 3.12 --with 'page-dewarp==0.3.4' page-dewarp --help
```

A root Taskfile was suggested during requirements. Introduce and verify its
fixture/setup/check tasks when the prototype supplies concrete deterministic
commands; this survey does not introduce a speculative implementation recipe.

## Planning consequence and remaining silence

The next useful leaf is a bounded **visual prototype** of the two-page
comparison, with exported diagnostics and a user reaction. Its contract should
include unchanged controls, failed-model handling, colour/detail retention,
and the baseline comparison. Design the production correction/review interface
only after that evidence identifies which geometry and manual adjustments are
needed. There is no adopted research finding requiring an ADR yet.

Search covered the named tools' author documentation, source, failure reports
and Mac installation routes, with queries for varying scanner-feed skew,
dewarping music, sparse/column layouts and existing OCR. No primary source was
found in the examined corpus demonstrating scanner-feed rotation recovery on
these cut-up pages, a reliable automatic music-notation success rate, a
calibrated review threshold for mixed book pages, or a tested DocGeoNet Mac port.
Do not turn that silence into claims that no such solution exists.

Leptonica's older explanatory website could not be fetched reliably; versioned
source is the evidence here. A music-scanning forum result could not be reopened
and is not used to establish a failure claim. The package and GUI startup/build
status must remain distinct from correction quality. The rendered samples are
candidate fixtures, and neither their physical distortion cause nor complete
restorability has been established.

The source snapshots inspected were Leptonica 1.87.0; ScanTailor commit
5eaac1884cdcabb6514bd632114f688631bd8dbc; page-dewarp commit
a62c15c8c1fba0bc78ed1e00398fdedf3db93add plus installed PyPI 0.3.4; and
DocGeoNet commit ead1d371b3c6eefdc054b4d6e633e561c83ef80e. Pin tested code
and record sampler settings in the subsequent experiment.

Source PDFs were only read. SHA-256 identities below were recorded before the
detailed inspection and checked again afterwards. All six source digests matched.
Temporary renders and downloaded upstream sources are disposable research aids;
the page references and recipes above make this survey usable without them.

| Source PDF, abbreviated as in the inspection table | SHA-256 |
| --- | --- |
| Fundamentals of Musical Composition | 3235a842d619a18b11e2fbdb3b5b6666adeb223959cafd4b1d67f27f0dbfe780 |
| Garbage Collection | 70585aa07afad6217dec5e6ec446b6cd6ab906e9c6782b515e8d8c344f125bb6 |
| Counterpoint in Composition | ae16ae84cfa7e8d610c76fb80cf33a0bab0c8615a2b6a0fc7226a5da1c317224 |
| Norwegian grammar | a21736ada0c088ab9e4f89a264c303788ccf22c4ee647b5dfb5f076ea1b750d3 |
| Algorithm Design | b9d6f1fd08560f06ec8653375a5866dbe1ba971d780dfecd1a0211fb2f66deab |
| SchoenbergComposition cover | 55fef6822d156d48985e55570de77201687de81b84a11f4a2b76a125c1d8873f |
