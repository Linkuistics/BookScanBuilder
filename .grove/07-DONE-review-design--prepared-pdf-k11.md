# prepared-pdf-k11

**Reviews:** prepared-pdf-k9
**Creator:** run 6c59247b-abfa-42e9-b05e-c2fc52b74946


## Goal

Find material defects in preparation's public command and preservation contract
before `prepared-pdf-k10` cuts the working implementation. This is an adversarial,
inspection-only review of the design, not a preparation implementation or a
review of the future correction algorithm.



## Context

Read `docs/specs/prepared-pdf.md` against the confirmed requirements in `plan-k1`
and the root brief's preparation acceptance cases. Read the copying experiment
and its limits in `docs/research/prepared-pdf-copy.md`, its retained per-item
report, and the final script when a claim depends on it. The spec links the
editable browser views; the root Taskfile renders/serves them and reruns the
bounded copying experiment. The committed producer artifact is identified by
the stable handle above.

## Done when

- Check that repeated role selections, optional page expressions, exclusion
  semantics, default order, interior covers, repeated pages and already-assembled
  input form an implementable, unambiguous public command with actionable errors.
- Try to disprove complete visible-page/canvas preservation. In particular,
  examine inherited page attributes, masks/shared decoder resources,
  document-wide colour/optional-content/form dependencies, extension declarations
  and the boundary between acceptable static annotations and unsupported inputs.
  Check material library assumptions against current primary docs or installed
  source. Exact sampled Poppler pixels do not establish arbitrary-PDF support.
- Check whether private per-page role dictionaries remain independent for
  duplicated pages and useful inside a sole-PDF handoff, including unmarked,
  malformed and third-party-edited PDFs. Do not make source discovery or a
  required sidecar a hidden processor dependency.
- Challenge source/output alias checks, occupied/dangling destinations,
  source changes, temporary-file lifetime, validation, no-clobber publication
  races and pre/post-commit cancellation. Identify any promise stronger than the
  proposed mechanism or evidence supports.
- Check each root preparation fixture and public-command test seam against the
  design, including human visual comparisons and first-implementation Taskfile
  needs. Distinguish completed copying checks from future command acceptance.
- Record concrete findings with artifact location, consequence and evidence,
  or explicitly report no material findings. Leave artifact fixes to an
  integration session. Cut an integration before planning only if findings earn
  it, following the review kind's procedure.

## Notes

No in-session reviewer was used by the producer. This leaf supplies the fresh
context before downstream implementation decisions stand. Do not treat its
aimed axes as conclusions to validate; inspect the artifact against the agreed
contract and report what is wrong. The copying probe is intentionally a
dependency experiment rather than shipping preparation code. No ADR was earned
by the local, reversible choices. All increments remain in this workspace and
one tree; the root's later processor/end-to-end verification remains live.

## Findings

I inspected the producer commit `2973d3e3a76c` (`prepared-pdf-k9`) read-only:
`docs/specs/prepared-pdf.md`, `docs/research/prepared-pdf-copy.md` and its report,
`experiments/prepared_pdf_copy.py`, the design views and `Taskfile.yml`. I read them against
`plan-k1` and the root brief's preparation acceptance cases. I ran no test, build, lint or
format command and edited nothing outside this file. Library claims were checked against the
installed pikepdf 10.16.0 source in the uv cache. Two disposable read-only probes opened PDFs
with pikepdf 10.16.0 (`attempt_recovery=False`, nothing saved): the six fixture sources, and
all 204 PDFs under `/Volumes/Glass/Book Conversion`. Their results are stated where cited.
`spec:N` means `docs/specs/prepared-pdf.md` line N at that commit. Findings are ranked most
severe first.

### 1. The "unknown feature" gate has no definition an implementation can test

**Contract.** spec:159–170 names specific rejections. It then requires that "unknown features
or parser warnings that make preservation uncertain must produce an actionable error before
publication". Annotations are accepted only with a "self-contained normal appearance stream",
"except invisible link annotations".

**Defect.** Nothing says what is *known*. There is no list of catalog or page keys that are
rendering-relevant, ignorable or rejected. No rule says which qpdf warnings make preservation
"uncertain". "Self-contained" is undefined: is an `/AP /N` appearance-state dictionary
selected by `/AS` acceptable? So is "invisible": what about a link with no appearance but a
non-zero `/Border`? The failure acceptance at spec:293–296 ("unsupported visual dependencies,
malformed/recovery inputs") cannot be written against this text.

**Consequence.** `prepared-pdf-k10` must choose between two readings, and both are wrong.

- **A strict allowlist rejects real books.** The collection survey found a non-standard
  catalog `/PageList` in `Processed Books/Smalltalk-80 …`. It found page `/PieceInfo` and
  `/LastModified` on all 176 pages of `Processed Books/A Practical Approach to Eighteenth
  Century Counterpoint …`, and page `/Thumb` in two processed books. Elsewhere it found
  `/StructParents`, `/OpenAction`, `/PageLabels`, `/ViewerPreferences` and `/Outlines`.
- **A permissive reading gates only the named list.** spec:166–168 then promises nothing, and
  real hazards pass. One example is a stream whose data lives in an external `/F` file: it
  resolves differently once the output is in another directory.

**Evidence for the fix.** The survey also found that no collection PDF is encrypted, needs
recovery, or emits a qpdf warning on open. None has XFA, non-empty form fields,
`/OCProperties`, `/OutputIntents` or any annotation. The named gates therefore reject nothing
in the present collection. Only `Algorithm Design` and `Smalltalk-80` carry `/AcroForm`, and
both have empty `/Fields`.

**Smallest correction.** State the gate as a decision table:

- (a) The named rejections.
- (b) Each catalog key that affects rendering, with its outcome: reject, carry or not
  applicable. Every other catalog key is declared non-rendering and simply absent from the
  fresh document.
- (c) Page-dictionary and reachable-object rules, each with a stated outcome. These include
  external stream data and appearance-state annotations.
- (d) A binary warning policy. For example: any qpdf warning while opening sources,
  traversing selected pages or reopening the output is `SOURCE_UNSUPPORTED` or
  `OUTPUT_INVALID`.

Record the collection result so the support claim rests on evidence.

### 2. A successful dry-run promises nothing about the write

**Contract.** spec:60 has `--dry-run` "validate sources, selections and destination". Exit 0
means a "valid plan" (spec:114). spec:266 only requires that dry-run and write resolve the
same order.

**Defect.** It is unstated whether dry-run runs the preservation gates of spec:159–170. It is
also unstated whether it surfaces parser warnings that appear only once every object
reachable from a selected page is read.

**Consequence.** The obvious shell-loop use is to dry-run the collection first and fix
whatever fails. Under the weaker reading, an exit-0 `planned` result can be followed by
`SOURCE_UNSUPPORTED` or `COPY_FAILED` on the real run. Both readings fit the spec, so no test
can settle it.

**Smallest correction.** State that dry-run performs every source-level check: open without
recovery, run all gates, and traverse the selected pages' reachable objects for warnings.
Then a dry-run and a write of the same invocation differ only through destination I/O,
copy/save/validation failure and source change. If that cost is unwanted, say the opposite
explicitly, including in `--help`.

### 3. The outcome after the commit point is unspecified and can be misreported

**Contract.** spec:119 defines exits 130/143 only "before publication". spec:216–223 says a
cancellation after the link "may leave the complete valid destination". spec:302–303 accepts
only a complete valid destination after a post-commit cancellation.

**Defect.** Two post-commit cases have no exit code or JSON status:

- a SIGINT/SIGTERM that arrives after `link()` succeeds;
- a failure to write the success line to stdout, such as EPIPE in a pipeline.

Python runs signal handlers between bytecodes. An interrupt can therefore be raised after
`os.link` returns but before the code records that it committed. Unless the commit is
protected, the cleanup path then reports `INTERRUPTED` and exits 130 while a complete
destination exists. `docs/design/prepared-pdf/publication.d2` draws no post-commit branch,
and it has no dry-run success edge either.

**Consequence.** The exit code is a shell loop's only signal (spec:100). A committed book
reported as interrupted invites a retry, and the retry fails with `OUTPUT_EXISTS`. That is
safe. It is also exactly the "ambiguous interruption" the design could have avoided.

**Smallest correction.** Once the link succeeds, the result is `written` with exit 0. Cleanup
and stdout failures become warnings, with a JSON field to carry them. Defer SIGINT/SIGTERM
across the link and the recording of the commit. Add this case to the signal tests and add
both missing edges to the publication view.

### 4. The error contract is called stable but is incomplete

**Contract.** spec:102–128 promises one JSON object with structured errors, and
"representative stable error codes".

**Defect.** Four gaps:

- **Invocation errors have no codes.** Examples: missing `--output`, an unknown option, a
  third value, a role option without a path, a repeated `--output`. Python's argparse by
  default exits 2 with usage on stderr and no JSON.
- **Precedence is defined for one pair only:** collision before exists (spec:201). Nothing
  covers, for example, a token syntax error combined with a missing source and an existing
  output.
- **Cases the spec tests have no assigned code, and each pair of candidates spans two exit
  classes:**
  - zero-page sources (spec:294): `EMPTY_SELECTION` or `SOURCE_UNSUPPORTED`;
  - a destination created concurrently and caught at `link()` (spec:296): `OUTPUT_EXISTS` or
    `PUBLISH_FAILED`;
  - a destination directory without write permission (spec:297): `OUTPUT_DIRECTORY_INVALID`
    or `WRITE_FAILED`.
- **It is unstated whether one error or every selection error is reported.**

**Consequence.** The failure tests at spec:293–304 cannot assert the code or exit for these
cases. The first implementation will set the public contract by accident.

**Smallest correction.** List the complete code set, each with its exit class. State the
validation phase order: parse → token syntax → open/inspect sources → resolve selections →
destination → write. Say whether errors within a phase are aggregated.

### 5. The temporary file's write path, name and final mode are left to chance

**Contract.** spec:207–223: a "unique private temporary file in the destination directory", a
no-clobber hard link, and an "identifiable" leftover after a hard kill. spec:250–255 notes
that pikepdf's default file save can replace a destination.

**Defect.** Three gaps:

- **(a) Saving by path brings in pikepdf's own temporary file.** In installed pikepdf
  10.16.0, `Pdf.save(path)` always goes through `atomic_overwrite`
  (`pikepdf/_methods.py:425–433`). If the path already exists, as a pre-created `mkstemp` file
  does, pikepdf writes a *second* temporary file in the same directory and renames it over
  the target (`pikepdf/_io.py:100–145`). The spec never says the private temporary file must
  be written through a file object the command opened with exclusive creation. The natural
  implementation therefore gets pikepdf's file names and a replacing rename inside the
  temporary step.
- **(b) The published file's mode is unstated.** A hard link shares the inode, so a 0600
  private temporary file publishes a 0600 prepared PDF.
- **(c) "Identifiable" is undefined.** Suppose the temporary name ends in `.pdf`. Then the
  file left by a hard kill, or the second complete name left by a kill between link and
  unlink, is picked up by the next stage's `*.pdf` loop over prepared outputs.

**Smallest correction.** Write to an fd created with `O_CREAT|O_EXCL` and pass it to pikepdf
as a stream. Use a dot-prefixed name with a recognisable marker and no `.pdf` suffix. Set
the intended final mode, derived from the umask, before linking.

### 6. Output validation is undefined, and so is its owner

**Contract.** spec:207–209: reopen and "check … expected copied content/resource integrity".
spec:240: "the publication boundary hides temporary-file and no-clobber mechanics".

**Defect.** Poppler is not a runtime dependency (spec:232), so the runtime check cannot
compare renders. What it does compare is never stated. The experiment's fingerprint is
narrower (`experiments/prepared_pdf_copy.py:39–66`):

- It covers only direct page-level Image XObjects, not nested Form XObject resources.
- It hashes no stream dictionaries or `DecodeParms`. The probe found `JBIG2Globals` on the
  Algorithm Design page, and that object is absent from the report's fingerprint.

The spec also leaves a sequencing question open. The check needs PDF-representation
knowledge and must run *between* writing the temporary file and linking it, yet the
publication boundary is meant to hide that file.

**Consequence.** Two implementations can both "validate" and differ arbitrarily. The
publication interface is left for k10 to invent: one call, or stage → validate → commit.

**Smallest correction.** Define the runtime check as a per-page comparison of the reachable
object graph between source and output. Include raw stream bytes and stream dictionaries, so
decode parameters and globals are covered. Exclude `/Parent`, the marker and the dropped
`/StructParents`. Compare all effective boxes, `/Rotate` and `/UserUnit` directly (see
finding 9). Make publication a staged handle that the operation validates and then commits.

### 7. The role marker: `content` is overloaded, and its container and record need a decision

**Contract.** spec:33–42 selects interior covers, and covers inside an already-assembled
input, as content. spec:174–192 defines `/BookScanBuilder` with a `/Role` on every
destination page. spec:259–260: "No separate ADR is earned: these choices are local, visible
and reversible."

**Defect.** Three separate problems:

- **(a) `content` carries no information.** Every page selected with `--content` is written
  `/Role (content)`, covers included. A *present* `content` marker reads as an assertion that
  the page is a book page. It actually means only "not selected as front or back". The
  processor is told to treat absent markers as unavailable (spec:187). Nothing says
  `content` is just as uninformative.
- **(b) The standard container was not considered.** A private top-level page key was chosen
  without weighing the page-piece dictionary (`/PieceInfo`, ISO 32000 §14.5). That
  dictionary exists for product-private data, and it carries a `/LastModified` convention for
  detecting later edits. The collection already uses it (finding 1's survey).
- **(c) The ADR test was never applied to the marker.** Unlike the toolchain, the marker is
  persisted into every prepared PDF the user makes, and another increment consumes it. It is
  hard to reverse, and rejected alternatives exist: a sidecar, and possibly `/PieceInfo`. The
  blanket "local, visible and reversible" does not cover it.

**Smallest correction.** Define `content` as "not explicitly front or back". Decide the
container, with the alternative stated. Apply the three-part ADR test to the marker
explicitly; it may or may not earn a record.

### 8. The version and extension rules are ambiguous, and the experiment did not follow them

**Contract.** spec:146–150: use at least the highest source version. Carry extension
declarations, taking "the highest base-version/extension-level pair for each prefix", and
reject what cannot be reconciled.

**Defect.**

- **"Version" is ambiguous.** It could mean the header or the effective version: from PDF 1.4
  on, a catalog `/Version` overrides the header. The experiment compares header versions only
  (`experiments/prepared_pdf_copy.py:181–184`). No collection PDF has a catalog `/Version`.
- **The extension rule was not exercised.** `Algorithm Design.pdf` declares
  `/Extensions /ADBE << /BaseVersion /1.7 /ExtensionLevel 3 >>` (probe). The experiment saved
  with `min_version="1.7"` and no extension level. Its exactly-matching copy therefore did not
  carry the declaration the spec requires, and the fixture row at spec:276 never checks it.
- **Two edges are undefined or overreaching.** "Highest pair per prefix" is undefined for PDF
  2.0's array-valued extension entries. The reject clause can refuse a PDF for a non-visual
  reason.

**Consequence.** k10 inherits a rule with no acceptance check and an undefined edge, while
its own evidence suggests the rule is irrelevant to rendering.

**Smallest correction.** Define the effective version. Then either keep extension carrying
and assert that the Algorithm Design output declares ADBE 1.7 level 3, or drop it as
non-visual. Define the array case, or narrow the reject clause to it.

### 9. Acceptance does not check all the geometry it promises

**Contract.** spec:135–136 retains "effective MediaBox, CropBox, other page boxes, rotation
and UserUnit". spec:283–287 checks CropBox renders, MediaBox renders where the two boxes
differ, and MediaBox/CropBox values.

**Defect.** Bleed, Trim and ArtBox and UserUnit are promised but never checked. A CropBox
render does not depend on them, so a dropped box passes every stated comparison. The runtime
validation at spec:209 names only "effective boxes/rotation".

**Smallest correction.** Compare the effective values of all five boxes, `/Rotate` and
`/UserUnit` directly, both in acceptance and in the runtime check.

### 10. Duplicated annotated pages share annotation objects (plausible)

**Contract.** spec:139–140 and 179–180 allow repeated pages, each with a fresh marker.
spec:163–164 copies static annotation appearances.

**Defect.** qpdf creates a repeated foreign page as a shallow copy. The experiment confirms
the page objects are distinct (`experiments/prepared_pdf_copy.py:232`). The `/Annots` array
and its annotation dictionaries, however, are shared between the two occurrences. An
annotation's `/P` can name only one page. As I recall, ISO 32000-2 §12.5.2 also requires an
annotation dictionary to be referenced from a single page; integration should confirm that
wording. The spec's no-mutation rule protects the marker but still produces such files.
spec:278 tests duplication and spec:281 tests annotations, never both together.

**Consequence.** Low today, because the collection contains no annotations. Repeating an
annotated page would emit output that bends the format.

**Smallest correction.** Copy each repeated occurrence's annotations, or reject a repeated
selection of an annotated page. Add a combined fixture.

### 11. The `!` quoting guidance is insufficient for the user's shell

**Contract.** spec:87–88: "Quote expressions containing `!` for shells with history
expansion."

**Defect.** In interactive zsh (this Mac's shell) and in bash, double quotes do not stop
history expansion. `"all,!3"` expands `!3` or fails with "event not found"; only single
quotes are safe. The examples at spec:68 use single quotes, but the instruction never says
so. The grammar is the user's everyday interface, and no record shows the user agreed it.

**Smallest correction.** Say "single-quote" in the spec and in `--help`. Consider an
exclusion sigil that does not collide with history expansion. Confirm the grammar with the
user before k10 fixes it.

### Checked, no finding

- **Requirements are satisfied at the contract level.** Inputs are explicit selections only,
  with no discovery. Order is front → content → back whatever the argument position, and
  content is required. Interior covers are selected as content, and repetition comes from
  repeated selection. Nothing removes blanks or duplicates. The already-assembled, no-cover
  case is supported. The handoff is a single PDF with no sidecar. Originals are read-only,
  and outputs stay outside the collection.
- **Grammar examples check out.** `6-4,1,4,!5` → `6,4,1,4`; `!2,!5-6` → `1,3,4`; spec:69
  resolves to cover 1, book 2, cover 3, book 1, cover 4. "One or two values until the next
  option" is unambiguous, because only the second value is ever a page expression, exclusion
  tokens begin with `!` rather than `-`, and paths beginning with `-` need `./`.
- **Marker independence for duplicated pages is supported.** Assigning a fresh dictionary per
  occurrence (spec:179–180) after qpdf's shallow copy gave the labelled K1 front/back
  occurrences distinct objects and correct roles.
- **The evidence chain is intact.** The report's `script_sha256` (`223b6adf…`) equals the
  committed `experiments/prepared_pdf_copy.py`, and all six source digests match before and
  after. `docs/research/prepared-pdf-copy.md:102–113` keeps the copying probe distinct from
  command acceptance.
- **Alias checks are sound.** Every existing destination entry is rejected anyway, so the
  identity comparison only decides `SOURCE_OUTPUT_COLLISION` over `OUTPUT_EXISTS`, and that
  precedence is stated. `/Volumes/Glass` is local APFS, so hard-link publication works there.
- **The encoding-preservation controls are right.** `stream_decode_level=none`,
  `compress_streams=False`, `recompress_flate=False` and `normalize_content=False` do what the
  spec states (`pikepdf/_methods.py:375–395`).
- **The fixture table matches the root brief's acceptance cases,** and human visual
  comparison stays explicit.

## Decisions (running log)

The findings earn an integration. Findings 1–4 decide what `prepared-pdf-k10` can cut and
test, so the integration is inserted ahead of it as an `integrate-review-design` leaf whose
body names this review's handle rather than its findings.
