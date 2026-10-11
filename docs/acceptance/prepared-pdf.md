# Prepared PDF acceptance

The complete installed `bookscan prepare` command assembles explicitly chosen
whole PDF pages and publishes one independently validated ordinary PDF. Geometry,
OCR and the user's visual response remain separate downstream work.

## Reproduce

```sh
task prepare:setup
task prepare:check
# Each artifact directory must be unused and outside the collection.
task prepare:acceptance MODE=synthetic ARTIFACTS=/tmp/NEW-SYNTHETIC-DIRECTORY
task prepare:acceptance MODE=real ARTIFACTS=/tmp/NEW-REAL-DIRECTORY 'COLLECTION=/Volumes/Glass/Book Conversion'
task prepare:acceptance MODE=all ARTIFACTS=/tmp/NEW-ALL-DIRECTORY 'COLLECTION=/Volumes/Glass/Book Conversion'
```

`prepare:check` passed 199 tests, Ruff formatting/lint and strict pyright.
It requires neither Poppler nor collection access. Tests exercise the installed
locked public command for parsing/order/roles, copying, aliases, occupation,
retry and actual spaced-path/exclusion forwarding through `prepare:run`.
Source-gate failures repeat in dry-run and write. Destination listings include
dotfiles; private dry-run traps prohibit staging/copy/save/reopen/link, so a
create-then-delete implementation cannot pass.

Private faults cover staging denial after a valid plan, copy/save/reopen/graph
mismatch, source identity/metadata/digest/path changes, final mode, actual stream
flush, fsync, link support, concurrent occupation, warnings, cleanup and result
delivery. Mutation tests reach nested stream bytes, masks, soft masks,
DecodeParms/JBIG2Globals, scalar types/keys, all seven geometry values, page
count/type/version, annotation ownership/indirection and marker values/aliasing.
Pair comparison permits different node sharing and storage identities.

The signal/kill checks directly launch `.venv/bin/bookscan`, record its PID and
acknowledge private barriers through a test-owned channel. They exercise actual
SIGINT/SIGTERM during writing, pre-region/pending cancellation, immediately after
blocking, before link, after link, committed-before-unblock and cleanup.
Pre-commit signals yield `INTERRUPTED`/130 or 143; in-region/post-link signals
retain `written`/0 and `POST_COMMIT_SIGNAL`. Kill observations prove absent
destination during writing, or two names for the same complete file after link,
both before SIGKILL and after the writer is reaped. Test cleanup follows those
observations. Real EPIPE checks retain the original source error, dry-run failure
or post-commit success exit. Startup umasks 027/077/777 verify exact private 0600
and final `0666 & ~umask` modes. No product fault flags or background writer exist.

## Frozen runs and comparisons

Final synthetic artifacts: `/private/tmp/bookscan-prepared-k17-synthetic-v2`.
The recipe was run with `COLLECTION=/tmp/unavailable-collection`; that value is
not passed to the synthetic runner, which never resolves/opens a collection.
Real and all artifacts use the explicit `/Volumes/Glass/Book Conversion` root
and the external directories `/private/tmp/bookscan-prepared-k17-real-v2` and
`/private/tmp/bookscan-prepared-k17-all-v2`.

Each report freezes/digests product and test scripts, Taskfile, manifest/lock,
normative spec/ADR, generated source fixtures and selected real source PDFs
before and after measurement. It retains each public command, complete planned
order, written result, effective geometry, encoded stream/resource hashes,
matched Poppler commands, decoded RGB hashes/dimensions, native pixel crops,
text extraction and tool versions. Its fault JUnit file and 18 per-PID barrier/
signal/kill records retain individual outcomes. The initial real-v1 exercise
was discarded because an instrument edit changed a subject during measurement;
no totals from it are acceptance evidence.

Synthetic cases are interleaved K1,C2,K3,C1,K4; repeated K1 in independent roles;
descending/repeated/excluded selections; exclusions-only; already assembled
input; nested Form/image/stencil/soft-mask/decoder resources and visible static
appearance; distinct and default optional boxes; and an empty encoded stream.
Real cases are Fundamentals 40/140 with SchoenbergComposition 1 front, Norwegian
20, Counterpoint 20, Algorithm Design 20, and explicitly assigned Algorithms on
Strings cover 1 front/2 back around labelled C1,C2. Algorithm Design must retain
JBIG2 globals and ADBE base 1.7/extension level 3.

Every corresponding page has matched 300-dpi CropBox renders. MediaBox renders
are also compared where its geometry differs. Full-page decoded RGB pixels and
dimensions, all five boxes/Rotate/UserUnit and all retained encoded stream hashes
must agree exactly; labelled text extraction independently verifies order.
No source changes are permitted. Output appearance is not reconstructed from
raster images, and the source spread/landscape canvases remain one PDF page.

For human inspection, under the **all-v2** directory use:

| Comparison | Full page and useful native 300-dpi detail |
| --- | --- |
| Schoenberg front/colour | `music-page-1-cropbox/before.png` and `after.png`; `before-centre.png`/`after-centre.png` |
| Fundamentals page 40/music and faint marks | `music-page-2-cropbox/before.png`/`after.png`; `before-detail.png`/`after-detail.png` |
| Fundamentals page 140/staff, stems, slurs and margins | `music-page-3-cropbox/before.png`/`after.png`; `before-detail.png`/`after-detail.png` and `before-margin.png`/`after-margin.png` |
| Complete Norwegian spread | `norwegian-page-1-cropbox/before.png`/`after.png`; centre/detail pairs |
| Counterpoint single page on landscape canvas | `counterpoint-page-1-cropbox/before.png`/`after.png`; margin pair |
| Algorithm Design existing page/JBIG2 | `algorithm-page-1-cropbox/before.png`/`after.png`; centre/detail pairs |
| Algorithms on Strings explicit front/back | `strings-page-1-cropbox/before.png`/`after.png` and `strings-page-4-cropbox/before.png`/`after.png`; centre pairs |
| Synthetic nested static appearance/distinct boxes | `nested-static-page-1-cropbox` and `nested-static-page-1-mediabox`, each with before/after full-page, centre, detail and margin pairs |

PNG crops retain native pixels without resampling. The inspected provisional
music detail pair retains the source's thin stencil drawing, faint paper marks
and staff-line distortion; preservation is not geometry correction.

Final retained reports: [synthetic](prepared-pdf-synthetic-report.json),
[real](prepared-pdf-real-report.json), and [all](prepared-pdf-all-report.json).
All three runs completed with matching before/after subject digests, rechecked
against the current files before retention. The synthetic and real runs were
compared with the all run **item by item** (geometry, raw resources, roles/order,
render dimensions and RGB hashes); every item agreed. The all run covers 13
cases/31 corresponding pages. Each run retains 18 observed signal/kill cases and
its per-test fault/validation JUnit outcomes.

Actual tools: Python 3.12.15, pikepdf 10.16.0/qpdf 12.4.2, uv 0.13.0,
Task 3.54.0 and Poppler 26.10.0. uv and Task executables are observed versions,
not pinned by this project's setup. Actual `prepare:run` spaced-path and
single-quoted exclusion forwarding passed against direct JSON invocation after
the recipe changes. Setup synced the locked package and found the acceptance
renderer; no historical experiment/diagram recipe changed.

## Human response and review

Human visual approval is **pending**. `page-geometry-k4` must present the final
working-command comparisons, obtain a separate preparation acceptance,
rejection or inconclusive response and record the inspected paths/defects here
and in its running log. `corrected-book-k5` checks that disposition and retains
precise repair/missing-comparison work before processor acceptance. Pixel
equality and code review cannot substitute for the user's response.

The preparation subsystem earns an external `review-impl` before geometry. Its
special scrutiny includes immutable graph reconstruction, the encoded-empty
stream incremental revision, pair/cycle equality, annotation ownership,
source-lifetime rechecks and atomic signal/commit semantics. Review creates an
integration step lazily when actionable findings exist.

The historical dependency experiment/report are frozen. Their earlier Taskfile
digest describes that recipe's historical run. The retained
[preview report](prepared-preview-report.json) belongs to producer `587afb92`;
its temporary module/recipes/runner are retired. Preview establishes planning,
while the retained complete-command reports establish writing/render acceptance.
