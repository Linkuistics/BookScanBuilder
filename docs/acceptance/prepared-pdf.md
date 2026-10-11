# Prepared PDF acceptance

The preparation increment currently delivers its complete **dry-run preview**.
The writing command, runtime output comparison, safe publication, matched renders
and human visual acceptance remain outstanding in the writing successor of
`prepared-pdf-k13`. Do not use preview evidence as a prepared-PDF handoff.

## Reproduce preview verification

```sh
task prepare:setup
task prepare:check
# An unused artifact directory, outside the explicit collection:
task prepare:preview-acceptance ARTIFACTS=/tmp/NEW-PREVIEW-DIRECTORY 'COLLECTION=/Volumes/Glass/Book Conversion'
```

The check task runs Ruff formatting/lint, strict pyright and synthetic/public/
private-fault tests without Poppler or collection access. It exercises real
subprocess parsing/planning and the actual `prepare:plan` recipe with spaced
paths and `'all,!3'`, comparing its JSON with direct invocation. Private checks
trap temporary/write/copy/save/output-reopen/link calls and check source
changes, delivery failures and acknowledged pre-publication SIGINT/SIGTERM
against the directly launched Python host's PID. These are preview interruption
checks; writer commit-region/SIGKILL checks still belong to the writing child.

The preview acceptance runner freezes and digests its product/test scripts,
Taskfile, manifest/lock, normative spec/ADR, generated fixtures and six real
source PDFs before and after its cases. Each item records its exact command,
complete planned page/role result, all seven effective geometry values, raw
stream hashes, numeric effective version and extension level, and unchanged
artifact-directory listing. It does not render or write a prepared PDF.

Final report: `docs/acceptance/prepared-preview-report.json`; generated fixture
and runtime report paths are recorded there. Cases cover interleaved
K1,C2,K3,C1,K4, repeated unannotated K1 with separate roles, descending ranges,
exclusions, already assembled input, Fundamentals 40/140 plus front cover,
Norwegian 20, Counterpoint 20, Algorithm Design 20, and both explicitly assigned
Algorithms on Strings cover pages around generated content. Algorithm Design's
ADBE 1.7/3 is asserted directly.

The historical copying experiment remains frozen and is separate from command
acceptance. Its earlier Taskfile digest describes its own recipe, before the
preview recipes were added. No product test imports its helpers.

## Remaining acceptance and human response

No before/after **working-command write** comparisons exist yet. The complete
writing child must produce matched full-page/CropBox/MediaBox renders and useful
music/colour/faint-detail/margin/spread crops, supply their paths here, and record
all copy/validation/publication/signal/kill faults from the parent charter.
The future `prepare:acceptance` synthetic mode must run without the collection;
real/all modes use the explicit root and unused artifact directory.

Human visual approval is **pending**. `page-geometry-k4` presents the completed
preparation comparisons separately from its geometry trial and records the
preparation-specific response here and in its running log. `corrected-book-k5`
checks its disposition and retains precise missing-comparison/repair work before
processor acceptance. Pixel equality or code review cannot substitute for that
response.

Final preview verification passed 112 tests, Ruff format/lint and strict pyright.
The final frozen evidence run is at
`/private/tmp/bookscan-prepared-preview-k16-v2/report.json` with generated fixture
PDFs beside it; its retained copy is
[prepared-preview-report.json](prepared-preview-report.json). All ten cases
passed their individual assertions; all before/after subject digests matched
and were checked again before retention. Actual tools: Python 3.12.15,
pikepdf 10.16.0/qpdf 12.4.2, uv 0.13.0 and Task 3.54.0.
