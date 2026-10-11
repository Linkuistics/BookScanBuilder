# BookScanBuilder

A personal two-stage workflow: explicitly assemble chosen whole PDF pages, then
correct the assembled book and add aligned English OCR. Preparation currently
has a **complete dry-run preview**. PDF writing and the processor are still live
work; this increment installs no `bookscan` console command.

Use Python 3.12, uv and Task. The locked dependency is pikepdf 10.16.0.

```sh
task prepare:setup
# setup also checks pdftoppm, required by the eventual render acceptance.
task prepare:check
```

Checks need neither Poppler nor the collection. To preview explicit selections:

```sh
task prepare:plan -- --content 'Assembled Book.pdf' --output 'Prepared Book.pdf' --dry-run
uv run --locked python -m bookscan.preview --front 'Covers.pdf' 1 --content 'Book.pdf' 'all,!3,!9-10' --back 'Covers.pdf' 4 --output 'Prepared.pdf' --dry-run --json
# Insert a cover page as ordinary interior content, in the chosen sequence:
task prepare:plan -- --content 'Book.pdf' 2 --content 'Covers.pdf' 3 --content 'Book.pdf' 1 --output 'Interior cover.pdf' --dry-run
uv run --locked python -m bookscan.preview --help
```

Each front/content/back option takes `PDF [PAGES]`. Quote spaced paths and
single-quote expressions containing `!`; double quotes allow history expansion
in interactive zsh/bash. For names starting with `-`, use an absolute path or
`./` prefix. Page numbers are one-based PDF pages. Comma-separated positive
`all`, `N`, `A-B` tokens expand in order, including ascending/descending ranges
and repetitions. The union of `!N`/`!A-B` exclusions removes all matching
occurrences only from that selection. Exclusions alone begin with all pages.
Empty/malformed/out-of-range/fully excluded selections fail without clamping.

All front selections precede content, then back, regardless of argument
interleaving. At least one nonempty content selection is required. Omitted
PAGES means all pages. Nothing infers cover roles, removes blanks/duplicates,
looks for collection files, or splits a spread. Interior covers and covers in
an already-assembled PDF selected as content have the advisory `content` role.

Preview hashes each source twice and traverses its entire retained rendering
graph, including raw nested streams, so large PDFs have a real I/O/memory cost.
It opens sources read-only, checks supported static PDF 1.0–1.7 features and
bounded ADBE 1.7 levels 1–3, rejects encryption/recovery/parser warnings,
interactive or external/optional rendering dependencies, and reports all planned
pages. It validates effective canvas values and supported static appearances;
repeating an annotated page is rejected even if it contains only invisible links.
The full supported domain is in [the spec](docs/specs/prepared-pdf.md).

A plan creates no PDF or temporary file. It makes no write-permission trial,
reserves no destination, and cannot predict a later I/O or publication failure.
Explicit `--dry-run` is required by the temporary module/recipe. The complete
writing command and `prepare:run` will install together when their contract is
verified; there is no public unimplemented-write stub.

`--json` emits one version-1 result, including parser errors. `--help` wins over
all arguments and opens nothing. Human plans show numbered sources/pages/roles;
diagnostics go to stderr. Stable codes, exits and error precedence follow the
spec's phases 1–5 plus source stability recheck. An existing output, dangling
symlink or source alias is an error. There is no overwrite or automatic retry.
After an ambiguous interruption, inspect the destination before retrying and
choose a new path if it exists. Broken stdout cannot deliver its own error.

Preview evidence and reproduction commands are in
[the acceptance note](docs/acceptance/prepared-pdf.md). That evidence does not
establish copying fidelity or human visual approval.
