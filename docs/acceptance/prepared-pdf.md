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

After integration `prepared-pdf-k19`, `prepare:check` passed 231 tests, Ruff
formatting/lint and strict pyright. The producer's original run passed 199 tests.
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
The repaired checks additionally observe validation, write/dry-run source
rechecking, final fsync, dry-run traversal, the interval after `os.open`, plan
serialization, chosen-error serialization/cleanup and repeated cancellation
during cleanup. Pre-commit cancellation checks yield `INTERRUPTED`/130 or 143;
an already chosen error keeps its original exit through later signals, and
signals after plan finalization keep that delivered result. Cancellation waits
for the current operation to return. In-region/post-link signals
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

Historical producer reports: [synthetic](prepared-pdf-synthetic-report.json),
[real](prepared-pdf-real-report.json), and [all](prepared-pdf-all-report.json).
All three runs completed with matching before/after subject digests, rechecked
against the producer's files before retention. The synthetic and real runs were
compared with the all run **item by item** (geometry, raw resources, roles/order,
render dimensions and RGB hashes); every item agreed. The all run covers 13
cases/31 corresponding pages. Each run retains 18 observed signal/kill cases and
its per-test fault/validation JUnit outcomes.

Those producer reports remain unchanged. Their 18 signal/kill observations
establish the listed barriers, not a general guarantee for every pre-commit
bytecode. Review `prepared-pdf-k18` reproduced misreported validation signals,
tracebacks during serialization and private-file leaks at acquisition/repeated
cleanup; the original broad signal claim is superseded by the repair and its
new observations. Historical render comparisons remain evidence for their
unchanged page content; their subject digests describe producer `750cc07b`,
not the current repair.

Actual tools: Python 3.12.15, pikepdf 10.16.0/qpdf 12.4.2, uv 0.13.0,
Task 3.54.0 and Poppler 26.10.0. uv and Task executables are observed versions,
not pinned by this project's setup. Actual `prepare:run` spaced-path and
single-quoted exclusion forwarding passed against direct JSON invocation after
the recipe changes. Setup synced the locked package and found the acceptance
renderer; no historical experiment/diagram recipe changed.

## Integration verification

Integration `prepared-pdf-k19` retained new frozen reports:
[synthetic](prepared-pdf-k19-synthetic-report.json),
[real](prepared-pdf-k19-real-report.json), and
[all](prepared-pdf-k19-all-report.json). Synthetic ran with a nonexistent
collection setting and no collection argument. The runs cover 9 cases/24 pages,
5 cases/10 pages and their union of 14 cases/34 pages respectively. Each retains
38 individually observed signal/kill records and 90 passing fault/validation
test outcomes. Every run's before/after subject digests match and were rehashed
against the files before retention. Corresponding geometry, encoded streams,
roles/order, extracted labels, render dimensions/RGB and all 38 signal/kill
outcomes agree **item by item** across modes. No instrument edits occurred during
measurement. The original four producer/preview reports are byte-identical to
review commit `ddb2595c`.

Current full-page/native-detail comparisons live under
`/private/tmp/bookscan-prepared-k19-all`; use the same case/view filenames listed
above. `reversed-boxes-page-1-cropbox` through `reversed-boxes-page-3-cropbox`
add all three reversed diagonal-corner orientations, preserving original box
coordinates and exact 300-dpi RGB. Current setup also verifies `pdftotext`.
The spec/help/README explicitly accept retained-byte memory costs and
cross-page resource duplication; these costs do not alter visual fidelity.

## Human response and review

Human visual approval is **pending**. `page-geometry-k4` presented the final
working-command comparisons and recorded the unavailable response below and
in its running log. `corrected-book-k5` checks that disposition and retains
the precise missing-response or repair work before processor acceptance. Pixel
equality and code review cannot substitute for the user's response.

`page-geometry-k4` presented the current working-command comparisons separately
from geometry in `/private/tmp/bookscan-geometry-k4-final/preparation-review.pdf`
(16 lossless pages). It pairs source/output full pages and native detail for
Schoenberg colour, Fundamentals 40/140, Norwegian's entire spread, Counterpoint's
landscape canvas, Algorithm Design and both explicitly assigned Strings covers.
The inputs are the `before`/`after` PNGs and centre/detail/margin pairs listed
above under `/private/tmp/bookscan-prepared-k19-all`; the PDF's manifest records
every exact path/hash and verifies its decoded RGB streams. The existing frozen
report remains `prepared-pdf-k19-all-report.json`, unchanged by this trial.

A separate preparation-specific visual response was requested, but no reply
arrived during this session's review window. Disposition: **inconclusive because
the human response is unavailable**; no observed human defect and no approval
are recorded. `corrected-book-k5` must ask whether those exact views preserve
music/faint marks, colour, margins, complete canvases and both cover pages, and
record the user's inspected paths and acceptance/rejection/remaining ambiguity.
Geometry's automatic-extractor failure does not settle preparation's judgment.

The preparation subsystem's external review `prepared-pdf-k18` completed before
geometry; integration `prepared-pdf-k19` resolves its findings. Its scrutiny
included immutable graph reconstruction, the encoded-empty
stream incremental revision, pair/cycle equality, annotation ownership,
source-lifetime rechecks and atomic signal/commit semantics.

The historical dependency experiment/report are frozen. Their earlier Taskfile
digest describes that recipe's historical run. The retained
[preview report](prepared-preview-report.json) belongs to producer `587afb92`;
its temporary module/recipes/runner are retired. Preview establishes planning,
while the retained complete-command reports establish writing/render acceptance.
