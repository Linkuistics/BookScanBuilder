# BookScanBuilder

A personal two-stage workflow: explicitly assemble chosen whole PDF pages, then
correct the assembled book and add aligned English OCR. **PDF preparation is
implemented.** Geometry and the processor remain downstream work.

Use Python 3.12, uv and Task. Runtime is pinned to pikepdf 10.16.0 in `uv.lock`.

```sh
task prepare:setup       # locked sync; checks Poppler for render acceptance
task prepare:check       # format/lint/strict types and synthetic/fault tests
uv run --locked bookscan prepare --help
```

Checks and normal preparation need neither Poppler nor the collection. Poppler
(`pdftoppm` and `pdftotext`) is used only by render acceptance. Actual tools used
and per-item evidence are in [the acceptance note](docs/acceptance/prepared-pdf.md).

```sh
# Already assembled: preserve every whole PDF page, with no separate covers.
uv run --locked bookscan prepare --content 'Assembled Book.pdf' --output 'Prepared Book.pdf'
# Explicit front/back covers, deliberate selection-local exclusions:
task prepare:run -- --front 'Covers.pdf' 1 --content 'Book.pdf' 'all,!3,!9-10' --back 'Covers.pdf' 4 --output 'Prepared.pdf'
# Insert an interior cover as content, in the chosen sequence:
uv run --locked bookscan prepare --content 'Book.pdf' 2 --content 'Covers.pdf' 3 --content 'Book.pdf' 1 --output 'Interior cover.pdf' --dry-run --json
```

Each front/content/back option takes `PDF [PAGES]`. Quote spaced paths and
single-quote expressions containing `!`; double quotes allow history expansion
in interactive zsh/bash. For names starting with `-`, use an absolute path or
`./` prefix. Numbers are one-based PDF pages. Comma-separated `all`, `N`, `A-B`
tokens expand in order, including descending ranges and repetitions. Unioned
`!N`/`!A-B` exclusions remove all matching occurrences from that selection only.
Exclusions alone begin with all pages. Empty/malformed/out-of-range/fully
excluded selections fail without clamping.

All front selections precede content, then back, regardless of argument
interleaving. At least one nonempty content selection is required. Omitted
PAGES means all pages. Nothing infers roles, removes blanks or duplicates,
searches collection files, or splits a spread. Interior covers and covers in
an assembled PDF selected as content have the advisory `content` role.

`--dry-run` hashes each source twice and traverses its retained graph, including
nested encoded streams, so large PDFs have an I/O/memory cost. It checks all
source gates, geometry, selections, destination preconditions and stability,
and reports the complete order. It creates no PDF or temporary file, tries no
write permissions and reserves no destination. A later write can still fail.
The temporary preview module and recipes have been removed; dry-run is now part
of the complete command.

Preparation preserves whole static PDF 1.0–1.7 pages and bounded ADBE 1.7
levels 1–3: encoded drawing/image/mask resources, existing text, effective canvas
and supported static annotations. It rejects encryption, recovery/parser
warnings, interactive or external/optional rendering dependencies and repeated
annotated pages. The full supported domain is in [the spec](docs/specs/prepared-pdf.md).
Fresh independent advisory role/provenance dictionaries travel in the ordinary
prepared PDF; no sidecar or collection access is required by a later reader.

Writes use one exclusive mode-0600 private `.bookscan-prepare-<random>.tmp`
stream beside the destination. The complete output is reopened and validated,
sources are rechecked, final startup-umask permissions are applied and the file
is flushed/fsynced. An atomic no-clobber hard link publishes it. Existing files,
dangling symlinks and source aliases are errors. There is no overwrite, replacing
rename/copy fallback or automatic retry. Filesystems without the required link
semantics fail explicitly.

Human success prints the absolute destination only; dry-run prints the numbered
plan. `--json` emits one version-1 result, including parser errors, and `--help`
wins over other arguments without opening inputs. Diagnostics use stderr.
After ambiguous interruption, inspect the destination before retrying. Caught
SIGINT/SIGTERM before publication yield `INTERRUPTED`/130 or 143; after the link,
success remains `written`/0 with reportable warnings. SIGKILL can leave a private
remnant and prevent reporting, while the destination is absent or complete.
Later runs never sweep other runs' private files. Source files remain read-only.

```sh
# Unused external artifact directories; synthetic never reads the collection.
task prepare:acceptance MODE=synthetic ARTIFACTS=/tmp/NEW-SYNTHETIC-DIRECTORY
# Both synthetic and the explicitly selected real fixtures:
task prepare:acceptance MODE=all ARTIFACTS=/tmp/NEW-ALL-DIRECTORY 'COLLECTION=/Volumes/Glass/Book Conversion'
# MODE=real selects only the real cases.
```

Acceptance freezes/digests its scripts, recipe/lock/spec inputs and source
fixtures, retains per-item assertions, and supplies full-page and native 300-dpi
crops. Automated equality and pending user visual approval are distinct;
`page-geometry-k4` obtains the preparation-specific response before the processor
consumer treats it as accepted. The historical dependency experiment/report and
preview report remain separate evidence.
