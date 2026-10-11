# prepared-pdf-k13

## Goal

Deliver the complete, independently useful `bookscan prepare` command specified
in `docs/specs/prepared-pdf.md`: explicitly selected whole PDF pages, advisory
roles, unchanged originals and visible appearance, and safe publication of one
ordinary PDF before geometry or OCR work begins.

## Context

- `docs/specs/prepared-pdf.md` is the integrated, normative command, preservation,
  error-precedence, runtime-validation and publication contract. Read all of it;
  its full acceptance tables apply, not just the examples in this leaf.
- `docs/adr/prepared-page-hints.md` fixes version-1 advisory page dictionaries
  and the sole-PDF handoff. No processor implementation belongs here.
- `prepared-pdf-k9` and `prepared-pdf-k12` delivered and repaired the design;
  `prepared-pdf-k10` planned this handoff. Read any intervening planning review
  and integration from their committed handles before implementation.
- `docs/research/prepared-pdf-copy.md`, its retained JSON report and
  `experiments/prepared_pdf_copy.py` provide bounded copying evidence and reusable
  labelled-fixture/render mechanics. Their fingerprint is not the specified
  runtime projected-page comparator; the probe is not command acceptance.
- `Taskfile.yml` already wraps the experiment and design diagrams. Extend it
  in place; keep the experiment wrapper while a lasting recipe calls it.
- The root brief supplies explicit real-source paths and the integrated outcome.
  Fixtures and artifacts stay outside the source collection. Ordinary command
  use and synthetic checks must not depend on access to that collection.

## Done when

### Complete command and preservation

- Python 3.12, pinned pikepdf 10.16.0 and a locked uv environment install
  `bookscan`. Public subprocess checks invoke `uv run --locked bookscan prepare`;
  Poppler remains an acceptance dependency, independent of runtime use.
- Implement the spec's exact options/arity, singleton checks, one-based PDF-page
  grammar, repetitions, ascending/descending ranges and unioned exclusions.
  Group front/content/back independently of argument interleaving, retain order
  within groups, and require nonempty content. No inference, deduplication,
  blank removal, collection discovery or spread classification occurs.
- Follow the spec's private ownership boundaries for parsing/reporting,
  immutable selections, the preparation operation, PDF copy/validation adapter
  and staged publication handle. The operation owns source lifetimes and
  stage → save → validate → source recheck → commit. Callers do not manage
  PDF graphs or a write protocol; no public fault-injection flags.
- Implement human/JSON output, every stable code/exit and first-error phase
  exactly as specified. Early standalone `--json` handles parser errors;
  standalone `--help` takes precedence and opens no inputs. Serialize one
  version-1 result with warnings before emission. Dry-run reports every planned
  page, runs all source gates/raw traversal/stability checks and destination
  preconditions, and creates no PDF or temporary file.
- Enforce the complete static PDF 1.0–1.7 catalog/page/reachable-object,
  annotation, version/ADBE-extension and warning gates in dry-run and write.
  Use the standard page-key classification, not sample-derived allowlists.
  Preserve the selected page's entire retained rendering graph and effective
  canvas. Apply exactly the inherited/default geometry and discarded-key rules.
  Keep static appearances and reject repeated annotated pages, including links.
- Save losslessly through the staged stream with the prescribed controls.
  Compute numeric effective header/catalog version and merged extensions;
  use tuple `min_version` for accepted ADBE levels. Algorithm Design keeps 1.7/3.
  Fresh independent version-1 markers carry role, source SHA-256 and page;
  replacing old hints never mutates sources or aliases repeated occurrences.
- Reopen staged output without recovery. Implement the complete recursive
  retained-source-projection/output comparison, raw streams/dictionaries and
  object-pair cycle tracking specified by the runtime-validation section.
  Separately verify all seven geometry values, annotation ownership, independent
  markers, page count/order, effective version/extensions and warnings.
- Keep sources read-only; hash before copying and before commit, and check
  identity/size/mtime/path identity. Reject all destination/source aliases before
  generic occupation. Stage one exclusive unpredictable mode-0600 dot-prefixed
  temporary file in the destination directory and lend its seekable stream.
  After validation/source recheck, flush/fchmod to `0666 & ~startup_umask`/fsync,
  then atomically link with no clobber or replacing rename/copy fallback.
- Block/defer SIGINT/SIGTERM across final cancellation check/link/commit-state
  recording. Link success fixes written/exit 0; later signals, cleanup and result
  delivery failures have the defined warnings. Pre-commit failures preserve any
  occupant and remove only this run's private name where possible. SIGKILL can
  leave private remnants or prevent reporting, never a partial destination.

### Public-command verification and real acceptance

| Request | Required order/role/fidelity observation |
| --- | --- |
| Labelled covers K1–K4/content C1–C2, role arguments interleaved; front K1, content C2 then K3 then C1, back K4 | Dry-run/write: K1,C2,K3,C1,K4; front,content,content,content,back. K2 omitted; extraction/renders/dictionaries confirm order. |
| Six-page fixture: `'6-4,1,4,!5'`; separately `'!2,!5-6'` | Exactly 6,4,1,4; separately 1,3,4. Exclusions apply only to their own selection. |
| Unannotated K1 front and back around content | Two occurrences with independent markers and unchanged source dictionary/digest. |
| Already-assembled labelled PDF, sole content, no covers or PAGES | Same complete count/order/composition; content hints describe this assembly. |
| Fundamentals 40,140 with SchoenbergComposition 1 explicitly front | Exactly cover 1,music 40,music 140; intact colour and image/stencil detail. |
| Norwegian 20; Counterpoint 20; Algorithm Design 20, separate no-cover commands | One unchanged complete spread; one unchanged landscape-canvas single page; one intact existing JBIG2 page with decoder globals and ADBE 1.7/3. |
| Algorithms on Strings, Trees, and Sequence cover 1 front and 2 back around labelled C1,C2 | Exactly 1,C1,C2,2; inspect both explicit cover assignments. |
| Inherited geometry/resources, distinct optional boxes and absent-box companions, Rotate/UserUnit, existing text, static markup, nested Form→Image/masks/globals and catalog Version override | Preserve seven effective geometry values, visible composition, extractable text, nested resources and effective version. |

- Compare every real/synthetic page at matched 300-dpi Poppler settings with
  exact decoded RGB pixels/dimensions, all seven geometry values and raw
  image/mask/decoder-resource hashes. Compare MediaBox/CropBox separately and
  render MediaBox when they differ. Include independent nested-Form and static
  annotation visible fixtures. Provide before/after paths at useful zoom for
  music, colour, faint detail, margins and full spread/canvas; distinguish
  automated equality from user visual approval.
- Assert all specified invalid-expression, arity/unknown/positional/singleton,
  source/readability/empty/change/unsupported/recovery and output parent/type/
  alias/occupation failures with exact code/exit/context/remediation. Compound
  cases prove syntax before missing source, source before occupied output,
  collision before generic occupation, missing output before missing content.
  Check early JSON detection and help precedence.
- Exercise every source gate in dry-run/write, including late raw-traversal
  warnings, empty-form acceptance, malformed/unsupported extensions,
  appearance-state annotations, border/default links, external streams and
  repeated annotated pages. Accepted discarded/private keys must not falsely
  reject. Mutate nested bytes/DecodeParms/JBIG2Globals, every geometry value and
  retained dictionaries/markers to prove runtime validation detects faults.
- Use real public subprocesses for parsing, copying, collisions and OS signals;
  a private adapter/subprocess host controls copy/save/reopen/validation,
  permission/flush/fsync/mode/link faults, source changes, concurrent occupation,
  warnings, cleanup and result delivery. Match errors to the spec's phases.
  Check sentinel destinations and original digests after failures. Verify
  stream-only saving, private naming/mode and startup-umask final permissions.
- SIGINT/SIGTERM before publication yield INTERRUPTED/130 or 143. Exercise
  pending cancellation, blocked-region/post-link signals, EPIPE and cleanup
  failures against the commit-point rule. Kill during writing and after link
  before unlink: the destination is absent or complete. No-link filesystems
  fail explicitly; repeat success gives OUTPUT_EXISTS/4 without changing output.
  Pre-commit cleanup failure retains the original error and TEMP_CLEANUP_FAILED
  warning/path. Include dry-run result-delivery failure and post-commit warnings.
- Freeze/digest scripts, recipe/lock inputs, generated fixtures and real sources
  before/after acceptance. Retain per-item commands, versions, artifacts and
  page/role/geometry/render/hash assertions. Rerun after instrument edits;
  aggregate totals or the dependency probe do not establish command acceptance.

### Reusable commands and handoff

- Extend the existing root Taskfile with `prepare:setup`, `prepare:run`,
  `prepare:check`, `prepare:acceptance` as specified: locked setup/dependency
  checks, forwarded arguments to the installed command, formatting/lint/type
  plus synthetic/fault checks, and real acceptance in an unused caller-selected
  artifact directory with explicit collection root. Synthetic checks need no
  collection. Run all new/changed recipes and existing recipes affected by setup.
  Retain or explicitly replace/remove and verify existing wrapper-backed recipes.
- Add durable setup/usage documentation with quoted paths, single-quoted `!`,
  interior-cover/no-cover examples, dry-run/JSON/support limits and no-overwrite/
  retry behaviour. Record reproduction/comparison paths and any still-pending
  human visual acceptance. Update “not yet implemented” wording in the spec only
  after command verification. Keep checks with implementation, not a test-only leaf.
- Commit product, verification, docs and retirement here. Assess the finished
  implementation for an earned `review-impl`; insert required review before
  `page-geometry-k4`, naming this producer handle. That review cuts integration
  lazily before consumers. Spend no in-session reviewer beside a scheduled review.

## Notes

Packaging belongs in `pyproject.toml`/`uv.lock`; private modules can be
`src/bookscan/cli.py`, `selections.py`, `prepare.py`, `pdf.py`, `publication.py`,
with synthetic/subprocess checks under `tests/` and one explicit-fixture
acceptance runner. Follow the spec's ownership; private filenames are not a
public contract. Read the Python coding skill before writing code. Start with
failing public selection/order tests, then bring copying/gates/validation/
publication and their checks to one complete green command in this same slice.

Do not weaken reviewed gates to make the bounded sample pass. A genuine support
or contract change needs an explicit design decision. Geometry, border or
appearance cleanup, splitting, OCR, a GUI and review controls stay downstream.
The output works in ordinary readers now and as the processor's sole required
input later. `corrected-book-k5` retains final collection-isolated end-to-end
acceptance and optional-cleanup handoff. Preparation does not close the root.
No driver is launched.
