# prepared-pdf-k18

**Reviews:** prepared-pdf-k13
**Creator:** run a8c952b7-5949-454d-940e-a4b8be18eb50

## Goal

Adversarially review the completed preparation subsystem against its complete
normative contract before geometry consumes it. Produce findings, not fixes.

## Context

- Read `docs/specs/prepared-pdf.md`, `docs/adr/prepared-page-hints.md`, the root
  brief and the complete `prepared-pdf-k13` node brief. Find producer commits by
  their stable handles. The final implementing leaf is `prepared-pdf-k17`; its
  diff starts from preview commit `587afb92`. Review the combined product,
  including inherited source gates, rather than treating the final diff alone
  as the contract. This session closes that node after its final child retires.
- Product boundaries are parsing/reporting, immutable selections, the operation
  owning live sources, the PDF copy/validation adapter and staged publication.
  Focus on reopening/rehashing every invocation, source/path identity and phase
  precedence; the operation must not write from a closed cached preview plan.
- Scrutinize immutable retained-graph reconstruction: scalar types, dictionaries,
  raw encoded streams, arrays, cycles and comparison by source/output node pairs
  independent of storage identity/sharing. Check seven effective geometry values,
  annotation ownership/indirection, marker freshness/non-aliasing, page order/count,
  numeric header/catalog versions, ADBE tuple controls and all warning gates.
- An additional serialization seam preserves filtered zero-byte streams that
  qpdf 12.4.2 otherwise normalizes. `copying.py` temporarily carries their encoded
  dictionaries under an unpredictable private key and appends standard incremental
  revisions using reopened output object numbers. Try to disprove correctness of
  restoration, exact dictionaries, references, xref/trailer/Prev handling, empty
  bytes, failure attribution and absence of reachable restoration tags. Consult
  the cited pinned library source and ISO section; real render equality alone
  cannot establish this seam's general correctness.
- Try to break the exclusive mode-0600 seekable stage, startup-umask final mode,
  completed-stream flush/fsync, no-clobber hard link, pending cancellation and
  signal-blocked link/commit-state boundary. Check pre-commit error precedence,
  cleanup warnings, real EPIPE exits, post-commit success/warnings and observed
  SIGKILL two-name/complete-destination guarantees. There are no product fault
  flags; the private subprocess host launches the installed writer directly.
- `task prepare:check` passed 199 tests, Ruff and strict pyright. Read tests as
  evidence to challenge: source-gate dry/write parity, mutation sensitivity,
  exact directory snapshots, race occupants, barrier/PID observations and
  no-write traps. Re-run targeted checks when useful.
- `docs/acceptance/prepared-pdf.md` and three retained complete-command reports
  record frozen synthetic/real/all acceptance. Compare per-item observations
  and before/after subject digests, not aggregate totals. The combined run has
  13 cases/31 pages, exact matched 300-dpi RGB, geometry and encoded resources;
  each mode retains 18 signal/kill records. Artifact/crop paths are external.
  The first real run was invalidated by an instrument edit and discarded;
  only frozen v2 runs are evidence. Historical dependency/preview reports are
  unchanged and establish their original bounded claims.
- Human visual approval is pending and owned separately by `page-geometry-k4`;
  `corrected-book-k5` checks its disposition. Neither this review nor automated
  pixel equality substitutes for that response. Geometry/OCR/cleanup stay outside
  this review's implementation scope.

## Done when

Record actionable findings with contract/evidence, concrete trigger and source
coordinates against the producer commit. If findings warrant integration, cut
`integrate-review-impl` with this review's handle as its charter immediately
before the first later sibling entry containing live work (currently
`page-geometry-k4`), using the producer's bare `prepared-pdf` slug. Create no
integration if there is nothing actionable. Do not fix the product in this
review or add a competing in-session reviewer.

## Findings

I inspected the final producer commit `750cc07b6165` (`prepared-pdf-k17`, diff
from preview commit `587afb92`) as the combined product under
`src/bookscan/` (`cli.py`, `selections.py`, `prepare.py`, `pdf.py`,
`copying.py`, `publication.py`, `results.py`), read against
`docs/specs/prepared-pdf.md` (`spec:N` is that file's line N), the ADR, the
`prepared-pdf-k13` node brief, the tests and the three retained reports. I ran no
test, build, lint or format command (`task prepare:check` was not re-run, so its
"199 tests" claim is taken from the producer's log), and I edited nothing outside
this file. I did run **scratch probes** that import the committed product and
write only under the session scratchpad, to turn suspicions into observations;
each finding says whether it is confirmed by a probe or only by reading.
Coordinates are `file:line` in `750cc07b6165`. Ranked most severe first.

### 1. A caught SIGINT/SIGTERM during staged-output validation is reported as `OUTPUT_INVALID`/5, not `INTERRUPTED`/130|143

**Contract.** `spec:130` and the brief require a caught interrupt/termination
before publication to be `INTERRUPTED` with exit 130/143; `OUTPUT_INVALID` means
reopen/representation mismatch (`spec:162`). The acceptance note claims
pre-commit signals "yield `INTERRUPTED`/130 or 143".

**Defect.** `Control.interrupt` raises `PreparationError("INTERRUPTED", …)`
from the signal handler at an arbitrary bytecode (`publication.py:34-40`).
`copying.validate` wraps its whole body in `try`, and its handler
`except PreparationError as exc` re-raises only `OUTPUT_INVALID` and converts
every other `PreparationError` — including that `INTERRUPTED` — into
`failure("OUTPUT_INVALID", "Unsupported staged output: …")` with exit 5
(`copying.py:265-268`). The clause exists to relabel `SOURCE_UNSUPPORTED` raised
by the shared gates on output pages; it was written without the asynchronous
exception in mind.

**Trigger.** Ctrl-C or `kill -TERM` while `validate` runs. That is one of the two
longest pre-commit phases for a book (the whole output is reopened and every
page's retained graph is re-projected and compared), so it is the likeliest
moment for a user to interrupt.

**Evidence (confirmed by probe).** With the real handler installed and a real
`os.kill(getpid(), SIGINT)` sent from inside the first `project_page` call made by
`validate`, `run()` returned exit 5 with
`{"code": "OUTPUT_INVALID", "message": "Unsupported staged output: Caught signal 2
before publication."}`; no destination and no private file remained. The retained
signal evidence cannot have seen this: every real-signal barrier pauses inside
`Pdf.save`, the link/mask/cleanup hooks or `before_recheck`
(`tests/writer_hooks.py:30-79`, `tests/test_faults.py:155-192`,
`tests/test_publication.py:266-325`); none holds the process in `validate`, the
source recheck, `Staged.finish` or a dry run.

**Consequence.** Wrong stable code and exit for the one phase a user is most
likely to interrupt. Shell loops that test for 130/143 keep iterating, the
remediation text ("inspect the destination … choose a new path") is for a
different failure, and the claim in the acceptance note is false for this window.
The destination is never partial, so this is a reporting defect, not a safety one.

**Smallest correction.** Convert only the codes that mean "source gate rejected
the output" (or re-raise any `PreparationError` whose code is already stable) so
`INTERRUPTED` passes through; add a real-signal barrier inside validation, the
recheck and a dry run to the private host.

### 2. The interrupt handler raises outside the protected region, so a catchable signal can yield a traceback or a leaked private file

**Contract.** `spec:119`/`spec:350-352`: a traceback is not a normal diagnostic,
and a caught pre-commit signal removes this run's private name where possible.

**Defect.** The handler raises whenever `committed` is false, from wherever the
interpreter happens to be. The producer protected only link/commit-state
(`publication.py:89-113`); three other places are exposed:

- **(a) After `operate()` returns and before `run()` ends** — dry-run success and
  the error branch. The exception escapes `run()` and `main()` as an uncaught
  `PreparationError` (`cli.py:107-110`). **Confirmed by probe:** a SIGINT sent
  from inside `emit` produced a Python traceback and exit 1, with no result on
  stdout even under `--json`.
- **(b) During `Staged.cleanup()`** (`publication.py:115-123`, invoked from
  `finally` at `prepare.py:289-291`): a second Ctrl-C raises inside the cleanup
  and skips `unlink`, leaving a possibly large `.bookscan-prepare-*.tmp`.
  *Plausible by reading; not probed.*
- **(c) Between `os.open` returning and the `Staged` object being assigned**
  (`publication.py:61-77`, `prepare.py:273`): the file exists but `staged` is
  still `None`, so `finally` does not clean it. The window is a few bytecodes.
  *Plausible by reading; not probed.*

**Consequence.** (a) is a visible contract breach with a very narrow window; (b)
and (c) are rare private remnants that the spec permits only for SIGKILL.

**Smallest correction.** Either let the handler only record the interrupt and
check it at designated points, or mask SIGINT/SIGTERM around result emission and
cleanup and create the staged file under the same guard that guarantees an owner
exists for the descriptor.

### 3. Peak memory is about 3–4× the selected encoded bytes, even for `--dry-run`

**Contract.** `spec:168-174` makes dry-run a hash/gate/raw-traversal run with
"no copy, save"; nothing there requires the bytes to stay resident. The README
admits "an I/O/memory cost" without quantifying it.

**Defect.** `project_page` stores each retained stream's full raw bytes in an
immutable `Node` (`pdf.py:372-373`); `operate` appends one projection per
output occurrence and keeps them all in `Plan.projections`
(`prepare.py:231-264`) until the end; `copy_page` then copies them again with
`make_stream` (`copying.py:65`). A dry run only needs a length and digest per
stream for gating and cannot use the bytes.

**Evidence (confirmed by probe).** 40 pages × 4 MB of distinct image streams
(160 MB): peak RSS 523 MB in `--dry-run` and 690 MB in a write. The user's own
sources are 16–253 MB (Fundamentals 253 MB/238 pages), so a whole-book run is
roughly 1 GB resident today; a larger scan set or a 1 GB assembled book scales
the same way.

**Consequence.** Acceptable on this Mac for the sampled books; a visible
scalability limit that was never recorded as a trade-off.

**Smallest correction.** Hold a digest and length per stream in the snapshot and
re-read bytes lazily (per page) during copy and comparison, or accept and record
the limit in the spec and `--help`.

### 4. Shared resources are copied once per output page

**Contract.** `spec:383-384` permits differing sharing ("Do not require sharing
to be identical across occurrences"), so this is not a contract violation.
`spec:219` forbids pruning resources "as an optimization", which is a different
matter.

**Defect.** The `nodes`/`seen` tables are local to one `project_page` call
(`pdf.py:304-305`) and `copy_page` materialises every node of every occurrence as
new objects (`copying.py:58-91`), so a font, ICC profile, colour space or
`JBIG2Globals` stream referenced by N selected pages is written N times.

**Evidence (confirmed by probe).** 20 pages sharing one 1 MB stream: input
1.0 MB, output 20.0 MB (19.9×); pikepdf's own page copy of the same input writes
1.0 MB. **Not triggered by the real acceptance set:** I opened (read-only) the
five real sources the acceptance uses — Algorithm Design has 863 distinct
`JBIG2Globals` objects (no page shares one) and none of the others shares a font
across pages — so the matched renders and reports are not wrong, only silent on
this class.

**Consequence.** An already-assembled or OCR-processed PDF whose pages share
fonts or decoder globals grows by roughly the page count × the shared bytes,
and save, validation and hashing grow with it. This also sits poorly beside the
spec's headline "already assembled PDF is valid input" case.

**Smallest correction.** A design decision, not a bug: either record "no
cross-page sharing" as an accepted trade-off, or give each source one
objgen→node table across its selected pages while keeping annotations
per-occurrence (annotations need a single owner). The pair comparator already
tolerates either.

### 5. Box gating rejects legal rectangles and blames the wrong key

**Contract.** `spec:398-399`: "finite four-number boxes of positive extent".
ISO 32000-1 §7.9.5 allows a rectangle to name any two diagonal corners.

**Defect.** `box()` demands `nums[2] > nums[0]` and `nums[3] > nums[1]`
(`pdf.py:177-181`), so `[100 100 0 0]` fails although its extent is positive. The
page key loop validates boxes in sorted key order (`pdf.py:268-277`) and the
optional boxes default to CropBox then MediaBox, so the first failing key is
`/ArtBox` even when only MediaBox is bad.

**Evidence (confirmed by probe).** `MediaBox [100 100 0 0]` →
`SOURCE_UNSUPPORTED`, feature "ArtBox requires four numbers and positive
extent" (dry-run and write agree; `[0 0 0 0]` gives the same message). A real
`TrimBox [10 10 5 5]` is correctly attributed to `TrimBox`.

**Consequence.** Low: producers rarely write reversed corners and rejection is
fail-closed. The remediation text sends a user to a box that is absent.

**Smallest correction.** Decide whether the support domain includes
unnormalised rectangles (normalise on both projections and compare the
normalised values) or document the narrower rule; report defaulted boxes under
the key they were derived from.

### 6. A negative page number is `INVALID_ARGUMENT`, and the test was loosened to hide the ambiguity

**Contract.** `spec:92-93` lists negative numbers among invalid expressions and
`spec:135` makes malformed page tokens `INVALID_SELECTION`; `spec:46` also says
values belong to an argument "until the next option".

**Defect.** The parser ends an argument's values at any string starting with `-`
(`selections.py:68`), so `--content book.pdf -3` is "Unknown option or
positional argument: -3" (`INVALID_ARGUMENT`, exit 2) with no grammar guidance.
`test_malformed_before_source` accepts either code for `-1` and `-2`
(`tests/test_preview.py:162-185`), so the contract was never pinned.

**Evidence (confirmed by probe).** `PAGES=-3` → `INVALID_ARGUMENT`; `PAGES=0` →
`INVALID_SELECTION`.

**Classification.** Contract stated unclearly more than a defect: both readings
are defensible and exit 2 is common to both. It needs one decision recorded.

**Smallest correction.** Either treat a value matching `-[0-9]` that follows the
path as an expression, or state in the spec/help that a leading `-` always ends
the values, and make the test assert the chosen code.

### 7. `prepare:setup` checks `pdftoppm` but acceptance also needs `pdftotext`

`Taskfile.yml:31` runs `command -v pdftoppm` only; `tests/prepare_acceptance.py:411`
invokes `pdftotext` and `README.md:16` lists both. A machine lacking
`pdftotext` passes setup and fails mid-run, after consuming the unused artifact
directory the recipe requires. *Confirmed by reading.* Add the second check.

### 8. The retired preview's seams remain in production code

The README and spec say the temporary preview was retired, but `parse(args,
*, preview=…)` still carries the "temporary preview requires explicit --dry-run"
error (`selections.py:53`, `96-97`), and `operate` keeps a `preview` flag, a
`plan()` wrapper and a `before_recheck` hook (`prepare.py:202-213`,
`278-279`) that only tests use. They are not public CLI flags, so the "no public
fault-injection flags" rule holds. *Confirmed by reading.* Low: remove the
unreachable product branch and keep the private hooks only where a seam needs
them.

### Traced and sound (no finding)

- **Reopen/rehash on every invocation; no cached plan is written from.**
  `operate` opens and hashes each distinct path, builds the projection and
  stages/saves while the sources stay open; `Source.recheck` repeats
  fd-identity, path-identity, size, mtime and digest (`prepare.py:42-54`,
  `206-292`). Dry-run uses the same function, so the gates are shared, and
  duplicated `/Annots` entries are rejected identically in dry-run and write by
  a qpdf warning (probe).
- **Phase precedence and destination identity.** Tokens are checked for all
  selections before any source opens; bounds resolve in command-line order
  before traversal in front/content/back order; source collision, including
  inode and dangling-symlink cases, precedes generic occupation
  (`prepare.py:216-259`, `161-199`).
- **Pair comparison.** Scalars are compared as specified (numbers numerically,
  strings by bytes, names exactly, booleans distinct from integers), keys and raw
  encoded bytes compared, cycles terminated by
  visited source/output node pairs, and storage identity/sharing ignored
  (`copying.py:26-55`, `pdf.py:308-374`). Mutation tests reach nested bytes,
  masks, globals, DecodeParms, the seven geometry values and markers.
- **Zero-byte filtered-stream restoration.** I tried to disprove it with a source
  holding empty streams with `/Filter` arrays, an indirect `/DecodeParms`
  containing an indirect array, `null` placeholders, a direct `/DecodeParms`, an
  image dictionary and an `ASCIIHexDecode` chain. All were restored with exact
  dictionaries, valid references and `/Length 0`; the file had two revisions and
  the output reopened without warnings under `attempt_recovery=False`. The
  reopened (output) object numbers are used consistently, the appended xref/
  trailer carries `/Prev`, `/Size`, `/Root` and `/ID`, and the tagged
  dictionaries are replaced, not merely hidden. The random tag string still
  appears in the superseded first revision's bytes (three times in the probe) but
  is unreachable, which is what the spec and brief require. Failure attribution
  is slightly uneven (`PdfError` while reopening for restoration is
  `WRITE_FAILED`, a qpdf warning there is `COPY_FAILED`) but neither is
  reachable from the probes; I do not count it a defect.
- **Publication ordering and the blocked region.** Create (0600, `O_EXCL`) →
  save → validate → recheck → flush/`fchmod`/fsync → pending snapshot and
  block → no-clobber `link` → `committed = True` inside the block → restore.
  Link-region signals are warnings, `EEXIST` is `OUTPUT_EXISTS`, other link
  errors are `PUBLISH_FAILED`, cleanup warnings are carried in the same list the
  error record holds (`publication.py:49-123`, `prepare.py:270-291`). I found no
  defect inside the region itself; findings 1 and 2 are *outside* it.
- **Versions/extensions.** Numeric header/catalog maximum, the 1.3 floor and
  `min_version=(version, level)` for ADBE are implemented and validated on the
  reopened output (`pdf.py:114-165`, `prepare.py:260-269`, `copying.py:181-197`).
- **Retained acceptance evidence is internally consistent.** Parsing the three
  reports: before and after subject digests are identical in each, the repository
  files match the committed tree, all 64 renders have identical dimensions and
  RGB with empty diagnostics, the 31 corresponding pages agree across the
  synthetic, real and all reports item by item (geometry, roles, source pages,
  encoded-resource hashes, render hashes), and each retains 18 signal/kill
  records. The labelled text extraction verifies order for the five labelled
  cases. The real pages have no text layer, so "existing text" is only exercised
  on synthetic pages.

### Not established by this review

- The 199-test `task prepare:check` result and Ruff/pyright state were not
  re-run (inspection only); the retained fault evidence covers only
  `test_publication.py` and `test_validation.py` (70 tests).
- Human visual approval is pending and owned by `page-geometry-k4`; nothing here
  substitutes for it.
- Whether the restoration probes generalise to arbitrary qpdf/pikepdf versions is
  out of scope: the pinned 10.16.0/12.4.2 pair is the only one examined.

## Decisions (running log)

Scratch probes that import the committed product were used in addition to
reading, because findings 1–5 are claims about observable behaviour that a
reading alone leaves plausible; they wrote only under the session scratchpad and
changed neither the repository nor any source PDF. The real source PDFs were
opened read-only and only to count page sharing.

Findings 1 and 2 are the actionable defects against the written contract; 3–8 are
low-severity and are charter material for the integration, which must classify
each (real defect, visible trade-off needing a recorded decision, or contract
stated unclearly) rather than apply the list wholesale. An integration is cut
before `page-geometry-k4`, because geometry consumes the command whose signal
exit codes finding 1 concerns.
