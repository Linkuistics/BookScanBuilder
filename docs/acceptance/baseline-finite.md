# Finite baseline delivery evidence

`baseline-finite-k63` remains live. No installed finite reviewer, project, packet,
receipt action or geometry export has been delivered. This note records the
required first native-view mechanism probe; milestone 1 and all later delivery
checks remain unfinished.

## Renderer-independent native-scale probe — 2026-10-12

The bounded probe uses a synthetic RGB PNG, without a PDF or renderer. Its
construction declares a 640 × 480 image, a one-pixel red frame at
`[64,64,576,416)` (512 × 352), alternating one-pixel black/white columns at
`[96,96,544,160)` and rows at `[96,192,160,384)`. The geometry expectation is
exact: a native capture must retain the frame dimensions and each of the 28,672
horizontal / 12,288 vertical band samples. Fixed dark/light classification
(all channels ≤64 / ≥192) permits JPEG capture only; it establishes no colour,
source-detail or PDF-render fidelity. These bounds precede the reusable
comparison outputs. The frame/band construction was declared before UI captures.

Actual host/viewer configuration:

| Fact | Observation |
| --- | --- |
| OS / viewer | macOS 27.0.1 (26A434), Preview 11.0 |
| Display | P40w-20, display ID 3; 5120 × 2160 screen points and framebuffer pixels; backing scale 1.0 |
| Preview image-scale definition | Existing selected “1 image pixel equals 1 screen pixel”; print-size mode unselected |
| Viewer action | Open the PNG, Actual Size; one Zoom In for the negative control, then Actual Size again |
| Native window | CoreGraphics window 3280, Preview PID 58156; bounds x=4, y=35, width=708, height=584 points |
| Capture | Original CUA app-window bytes, JPEG, 708 × 584; no image resizing or thumbnail measurement |
| Measured region | Capture `[0,80,708,584)`, excluding toolbar colours; both complete band regions are measured |
| PNG density | 72 dpi, from 72 × observed backing scale; density alone establishes no viewer behaviour |

Window bounds × backing scale match the original capture grid. Both dimensions
are checked before crediting the sample grid as framebuffer pixels. Native
configuration evidence is retained in
[display-observation.txt](baseline-native-probe/display-observation.txt), with
the read-only [source](baseline-native-probe/display-observation.swift),
[image-scale settings](baseline-native-probe/preview-images-settings.txt) and
[restored viewer state](baseline-native-probe/preview-restored-state.txt).

The observed wrong zoom is evaluated first, before crediting Actual Size:

| Original capture | Frame in capture pixels | x / y scale | Outcome |
| --- | --- | --- | --- |
| [Zoom In control](baseline-native-probe/preview-zoom-in.jpg) | `[70,123,637,512)` = 567 × 389 | 1.107421875 / 1.1051136363636365 | **Failed**, exit 1; wrong frame geometry while capture-size check stays green |
| [Actual Size](baseline-native-probe/preview-actual-size.jpg) | `[98,142,610,494)` = 512 × 352 | 1 / 1 | **Passed**, exit 0; all 40,960 band samples retain their one-pixel classification |
| [Restored Actual Size](baseline-native-probe/preview-restored.jpg) | `[98,142,610,494)` = 512 × 352 | 1 / 1 | **Passed**, exit 0; same complete bands |

The [source ruler](baseline-native-probe/ruler-72dpi.png) SHA-256 is
`6096f9ccf43e1f38d19d755fa80116331dfa28f22539f294310800fa011172f6`.
The reusable generator reproduces those original PNG bytes exactly. Capture
digests, frozen read subjects and itemwise rerun outputs are in
[verification.json](baseline-native-probe/verification.json).
Complete preparation signal/kill exits, result fields, visibility and reaping
agree across synthetic/real/all reruns in
[fault-rerun.json](baseline-native-probe/fault-rerun.json). Those are preparation
regressions, not the still-unimplemented finite writer's fault acceptance.

This establishes a usable PNG native-scale mechanism on this **1.0-backing-scale
display and existing Preview setting**. It neither tests Retina nor shows that
PNG density controls device pixels in another setting. Apple documents separate
pixel and print-size scale definitions and View → Actual Size; percentage alone
is not a device-pixel observation.
[Preview scale definitions](https://support.apple.com/en-mide/guide/preview/prvw15556/mac),
[Actual Size](https://support.apple.com/en-ie/guide/preview/prvw11470/mac).

## Reusable measurement procedure for finite packets and browser B

1. Observe the actual display/backing scale and native viewer-window bounds.
   The retained Swift reader queries AppKit/CoreGraphics without controlling UI:
   `swift docs/acceptance/baseline-native-probe/display-observation.swift`.
   Bind the observation to the actual viewer/display; do not substitute the
   display maximum resolution or assume Retina. In B, measure its browser window.
2. Construct an unused ruler after recording construction truth, with
   `task process:native-ruler ARTIFACTS='/existing/output directory' BACKING_SCALE=1`.
   Use the measured scale. `tests/native_view_scale.py` never opens a viewer and
   refuses overwrite. It preserves RGB pixels when density changes.
3. Open that PNG through ordinary viewer UI; record actual viewer/version,
   image-scale definition and Actual Size action. Capture the complete window
   through the test-owned UI driver and retain original bytes/encoding. Confirm
   capture dimensions equal independently observed window bounds × backing scale.
   If the driver resizes its capture, obtain an unscaled observation; no pass.
4. Capture a deliberately wrong zoom, then restore the proposed native mode and
   capture again. Choose a content rectangle excluding toolbar colours but
   containing the **complete** ruler. Run the negative capture first, then the
   actual/restored captures, using the same measurement and declared truth:

   ```sh
   task --exit-code process:native-measure \
     CAPTURE='docs/acceptance/baseline-native-probe/preview-zoom-in.jpg' \
     LEFT=0 TOP=80 RIGHT=708 BOTTOM=584 FRAMEBUFFER_WIDTH=708 FRAMEBUFFER_HEIGHT=584
   # Expected exit 1. Repeat with preview-actual-size.jpg / preview-restored.jpg: exit 0.
   ```

   The direct runner gives one JSON object with capture digest, measured bounds,
   per-axis scale, sample coverage and failures. A passing screenshot test alone
   does not authenticate the supplied OS geometry: retain both observations.
   `--exit-code` makes Task propagate the measurement's exit 1; without that
   option Task reports its own task-failure exit (201 on the observed version).
5. Apply the measured mode to **actual packet tiles**, recording project/source/
   occurrence/image/review/view/region identity separately. Recheck native scale
   at that presentation boundary and measure B's browser independently. The
   whole-image native tiling, ordinary-viewer navigation and actual refreshed
   receipt inspection still require their complete acceptance. A ruler result
   cannot attest an unseen packet, a neighbour tile or refreshed receipt.

No real input or human visual response was used in this probe. No geometry,
source fidelity, preparation or product acceptance is inferred. The complete
real-packet/20-tile/19-refresh demonstration remains F's milestone 3 work.

## Work still owned by F

The packaged helper/native preflight, full static import/assessment/analyzer,
project/lock/transactions/readers, matched packets/receipts/replay/review actions,
acknowledged exact exporter, installed faults/denied reads, six real resource/
truth packets and frozen compatible predecessor remain required here. Only
the commissioned direct Pillow 12.3.0 pin and the early native mechanism/procedure
have been added. There is no milestone DONE mark or partial task commit.

## Packaged advisory estimator — continuation on 2026-10-12

The product now packages its own C source at `src/bookscan/native/skew.c`, with
the Python analysis/protocol boundary in `bookscan.skew` and explicit build/cache
preflight in `bookscan.native_setup`. It does not use an experiment executable,
fit path or correction model. These internal mechanisms introduce no installed
baseline command, saved project or export. Milestone 1 remains incomplete.

The disposable analysis is the whole RGB image converted to Pillow 12.3.0 L,
without resizing or excluding regions. Retained RGB remains untouched. Leptonica
1.87.0 binarizes that copy at 160 and assesses with explicit 4/2 sweep/search
reductions, +/-7 degrees, 1-degree sweep step and 0.01-degree search step. The
record retains linked version/settings, native status, signed deskew angle,
max/min score ratio, diagnostics and `[0,0,width,height)` region. No confidence
threshold, angle deadband, probability or automatic rotation is introduced.
Nonfinite numbers are null with an explicit invalid-numeric label; nonzero
status, zero confidence or nonfinite outputs give assessment-unavailable.
The library's sweep-edge diagnostic/boundary stays a separate reason.

The primary decision-site references are
[Leptonica skew](https://raw.githubusercontent.com/DanBloomberg/leptonica/1.87.0/src/skew.c),
[binary thresholding](https://raw.githubusercontent.com/DanBloomberg/leptonica/1.87.0/src/grayquant.c),
[version/severity API](https://raw.githubusercontent.com/DanBloomberg/leptonica/1.87.0/src/utils1.c)
and [Pillow conversion](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.convert).
Installed headers confirm the exact API signatures and header version. The
helper enables warning severity so range-edge messages are retained.

Construction truth precedes comparison outputs in the self-test source: 1200 x
900 RGB canvases have 24 rows of short black glyph rectangles whose y coordinates
follow `round((x-600)*tan(degrees))`, with x right and y down. Source clockwise
+2 degrees requires approximately -2 deskew degrees; -2 requires +2. The declared
0.125-degree API/sign bound accommodates at most two pixels across the 1000-pixel
constructed row width (~0.115 degrees) plus the 0.01-degree search step. It is
neither a measured real-page accuracy bound nor confidence calibration. Upright,
blank, +6.5-degree near-edge and +8-degree beyond-edge controls distinguish tiny
valid estimates, actual status-zero/confidence-zero and range-edge unavailability.
Private protocol records separately exercise valid exact zero, nonzero status,
zero confidence and nonfinite angle/ratio. They do not claim that a real page
returned those injected values. A wrong-sign helper must fail before any result
is credited; changed/incomplete/cache-symlink/wrong-dimension controls also fail.

Working developer recipes are:

```sh
task --exit-code process:setup
task --exit-code process:preflight
task --exit-code process:check
task --exit-code process:native-acceptance ARTIFACTS='/unused/artifact directory'
```

Setup syncs the locked environment and explicitly builds. Preflight verifies
without compiling or modifying the cache. For an isolated development build,
pass `NATIVE_CACHE='/existing parent/unused cache'` to setup/preflight. The default
is `~/Library/Caches/BookScanBuilder/skew-v1`. Completed build directories are
immutable; the cache pointer is replaced only after native controls pass. The
manifest records source/build/executable digests, compiler wrapper and selected
Xcode driver identity, pkg-config identity/flags, all Leptonica headers, the main
linked Leptonica dylib, supported Poppler identity, pinned Python libraries and
settings. Missing/changed/incompatible/unbuilt dependencies fail with the
DEPENDENCY_UNAVAILABLE/5 setup remedy. This cache is not a project checkpoint.

The currently supported native releases are Poppler 26.10.0 and Leptonica 1.87.0,
with Pillow 12.3.0/pikepdf 10.16.0. A Homebrew upgrade is checked explicitly and
cannot silently bypass the locked Python versions. Renderer composition/physical
mapping/ppi fidelity, transitive codec characterization and public import/resume
preflight integration still require their own milestone-1 checks. An accepted
image is never regenerated by this helper. Actual writer-PID signals, kernel
project ownership, transactions and all later finite delivery remain required.

Final isolated verification is retained in
[verification.json.gz](baseline-native-helper/verification.json.gz) (lossless gzip), with the complete
[native A](baseline-native-helper/native-a.json) /
[native B](baseline-native-helper/native-b.json) records and the separately frozen
[installed-wheel reading](baseline-native-helper/installed-verification.json).
The 8,917 enumerated workspace/library/stdlib/header/tool/contract subjects are
byte-identical before/after; the installed wheel separately freezes 1,765
subjects. Every native control and dependency/build/binary identity agrees
itemwise between A/B and the installed wheel. Preflight leaves its existing cache
byte-identical; an absent cache remains absent and returns 5. Wheel source bytes
equal the packaged C source, and the wheel runs outside this checkout. Full
command logs/build assets/reports and the verifier are under
`/private/tmp/bookscan-k63-helper-final/evidence-v2` and its parent.

`process:setup`, `process:preflight`, `process:check` (Ruff, strict types, 290
tests), native acceptance twice, Task discovery and `geometry:staff-check` (four
tests) pass. Synthetic preparation acceptance passes nine cases/24 pages, with
geometry/resources/roles/order/full and detail RGB records and all 38 actual
installed preparation signal/kill outcomes agreeing itemwise with the earlier
frozen synthetic run. This is preparation regression evidence, not a finite
writer or denied-collection-read result. Preparation's existing source/renderer/
publication and dependency versions remain unchanged; no new real copying claim
is inferred or substituted for the earlier real comparisons.

Native deskew results are -2.03125 for the +2-degree construction, +1.96875 for
-2, and -0.046875 for upright. The latter remains a nonzero advisory reason.
Blank returns status 1/confidence 0; near/beyond-edge constructions return status
0/confidence 0 with the retained edge warning. They are unavailable, never
valid-zero suggestions. Wrong-sign helper, changed cache and wrong subject/
protocol controls reject their named failures. RGB/encoded baseline bytes remain
unchanged. Numerical sign/API checks do not establish real-page angle accuracy,
source/native PDF fidelity, public project persistence or human visual approval.

## Cancellation through native preflight — 2026-10-12 continuation

`bookscan.native_setup.preflight` now takes the operation owner's cancellation
check. It carries that check through cache verification, chunked dependency and
executable hashing, dependency identity commands, helper identity and every
analysis/self-test boundary. It preserves the owner's selected exception and
uses the existing executor to terminate/reap an owned native child. The native
settings, version identities, build/cache protocol and successful control records
remain unchanged. This is internal implementation progress; no finite baseline
command, saved project or imported page has been delivered.

Ten new tests exercise cancellation before missing-cache access, during chunked
hashing and with actual private executable PID barriers during dependency and
helper operations, including through a complete verified cache. Each parked
child is reaped and retained cache/subject bytes remain unchanged. They supplement
future installed finite-writer signal/lock/checkpoint acceptance.

The reusable recipe is:

```sh
task --exit-code process:native-cancel-acceptance \
  NATIVE_CACHE='/existing complete helper cache' REPORT='/unused/report.json'
```

It uses the actual supported native tools. A private observation boundary records
the actual child returned by Popen; the operation owner supplies cancellation at
`preflight`, immediately after the selected child starts. The ten observed phases
are Leptonica version, Poppler version, compiler-driver lookup, include/library
directory lookup, compiler version, pkg-config version/flags, helper identity and
helper analysis. Each is checked for selected 130/143-style exceptions. Every
child is waited/reaped, the exact selected exception propagates and cache bytes
remain identical. These are **callback outcomes**: this runner sends no OS signal
and establishes no installed finite-writer, project lock or checkpoint behaviour.
A deliberately broken `checked` adapter drops the caller's callback; the same
runner first observes that control fail at Leptonica version, then validates the
real implementation. No public fault option or alternative native tool is added.

Frozen evidence is retained in
[verification.json.gz](baseline-native-cancellation/verification.json.gz), with
[native A](baseline-native-cancellation/native-a.json),
[native B](baseline-native-cancellation/native-b.json),
[installed cancellation outcomes](baseline-native-cancellation/installed.json) and
[installed-file provenance](baseline-native-cancellation/installed-cancellation-verification.json.gz).
The primary reading freezes 8,920 code/library/stdlib/header/tool/fixture/contract
subjects; the separate installed reading freezes 1,771 installed/cache/tool/script
subjects. All before/after digests agree. Each of the twenty cancellation records
agrees across both native runs and the wheel installed outside the checkout,
ignoring only per-run child PIDs. The two unit reruns agree by test identity and
outcome. Full native dependency/build/binary/control records also agree with the
previous helper evidence; successful preflight and retained RGB remain unchanged.
Read-only preflight leaves complete caches byte-identical, and missing cache
still returns 5 without creating it.

`process:setup`, `process:preflight`, the new recipe twice, native acceptance twice,
wheel build/installed preflight, `process:check` (Ruff, strict types and 300 tests),
Task discovery and `geometry:staff-check` pass. Synthetic preparation acceptance
again passes its nine cases/24 pages; full geometry/resources/order/roles/RGB and
all 38 installed preparation signal/kill outcomes agree itemwise with the previous
frozen synthetic record. No preparation code, dependency version or frozen
experiment changed. Those copying checks establish no finite import or denied-
collection-read result. Full commands, logs, XML per-test outcomes, verifier and
installed wheel are at `/private/tmp/bookscan-k63-cancel-final/evidence` and its
parent. Documentation/log additions occur after measurements finish.

Milestone 1 still needs static gates/private snapshot, verified full-MediaBox
rendering/physical mapping, persisted every-page analysis and complete placement/
ppi/source-native fidelity accounting with independent constructions/controls.
All project/lock/checkpoint/readers, packets/receipts/actions/replay/ack, exact
export/report and installed public/signal/isolation/six-case/compatibility/B-reuse
checks remain F's work. F stays live in its original open task-owned jj change;
no partial milestone, parent or product is retired or sealed.

## Static snapshot and exact page mapping — 2026-10-12 continuation

The internal `bookscan.intake.snapshot` operation now validates a sole static PDF
through the existing read-only document/page support gates, copies its exact
bytes to an unused private 0600 file, and independently verifies its digest,
source metadata/identity and private-file identity. It retains every occurrence
in order, original five boxes, effective Rotate/UserUnit and available version-1
preparation hint role/immediate-source provenance. Absent, unknown and malformed
hints remain unavailable; they neither reject ordinary input nor grant an
assessment exemption. No copying/export adapter or preparation commit policy is
used. The exact [pikepdf 10.16.0 stream-open source](https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/_methods.py#L550)
was checked for caller-owned streams and explicit recovery/overwrite controls.

Chunked hashes/copy and operation boundaries receive the owner's cancellation
check. Source symlink retargeting, replaced files, changed bytes/metadata and
private-copy tampering fail explicitly. Cleanup checks the attempt's acquired
inode and preserves a replaced private entry; failure while wrapping the newly
acquired descriptor closes it and removes the owned file. FIFO/directory inputs
fail as unreadable before a blocking read. These are internal snapshot tests,
not installed finite-writer signals, project transactions or exclusion evidence.
Originals have no exclusive lock against other programs; the eventual project
owner must reverify complete saved assets before checkpoint commit.

Page mapping uses exact rational pixel-edge transforms at the signed 300-dpi
scale, preserving nonzero/reversed coordinates, clockwise PDF rotation and
physical UserUnit. Stored physical dimensions remain the MediaBox extent; ceil
pixel dimensions retain the final partial pixel. Effective MediaBox/CropBox
disagreement is recorded independently. This mapping has not yet been coupled
to a product renderer, so it supplies no rendered canvas, source-native
composition, colour/detail fidelity or accepted-project result.

Reproduce the bounded construction check with an unused external directory:

```sh
task --exit-code process:import-acceptance ARTIFACTS='/tmp/NEW IMPORT CHECK'
```

The test-owned runner declares its [analytic truth](baseline-static-import/truth.json)
before snapshot output: a 72 by 36 user-unit page at (10,20), UserUnit 2, all
four rotations, reversed/distinct boxes and a fifth duplicate blank occurrence.
Six isolated wrong-unit/box/order/pixel-extent/physical-extent/edge-map controls
fail their respective oracles, with unrelated occurrence and byte checks green.
It then deletes only its generated original and verifies the retained private
PDF. This source-loss check covers the snapshot boundary, not future saved
project status/resume. No source collection or real-page truth is consumed.

Final evidence is [verification.json.gz](baseline-static-import/verification.json.gz),
[construction A](baseline-static-import/import-a.json),
[construction B](baseline-static-import/import-b.json) and
[installed-file verification](baseline-static-import/installed-verification.json.gz).
All 8,931 primary and 1,231 separately installed read subjects retain their
before/after digests. Thirty-nine focused cases agree by test identity/outcome;
complete construction/control records agree across both recipes and a newly
built wheel executed outside the checkout. The wheel's intake source is
byte-identical to the measured source. The initial stopped reading compared
in-memory tuples against decoded JSON arrays; it is discarded. The corrected
frozen reading compares complete JSON records, without ignoring semantic fields.

`process:check` passes Ruff, strict types and 339 tests; `geometry:staff-check`,
Task discovery, read-only native preflight, both new recipe runs, focused reruns,
wheel build/installed check and synthetic preparation acceptance pass. Native
preflight's full records remain identical to prior evidence. Preparation's nine
cases/24 pages and all 38 observed installed writer signal/kill outcomes agree
itemwise with the previous synthetic reading, including geometry/resources/
roles/order/RGB and exits/results/visibility/source identity/reaping. Preparation
code, all native settings and every dependency version remain unchanged; its
existing real comparisons retain their previous scope. No running subject was
edited. Complete scripts/logs/fixtures/wheel are retained at
`/private/tmp/bookscan-k63-import-final/evidence-v2` and its parent.

Next, finish milestone 1 with exact selected-version full-MediaBox rendering,
transitive renderer/codec identities, independent actual pixel/physical
constructions and wrong-subject controls; then complete contributing placement/
ppi/sample/mask/colour analysis and persisted every-page assessment/provenance/
regions. The snapshot/geometry types are internal responsibilities to integrate
into the sole owning operation, not a new public pipeline. All project/lock/
checkpoint/status/source-loss resume, packets/ordinary-viewer refresh/receipts/
Q1 actions/replay/scoped inspection/acknowledgement, exact export/report, installed
signal/isolation/six-case/resource/compatibility and B-reuse inventories remain.
F stays live in its original task-owned jj change; no milestone is retired or
sealed, and no renderer/fidelity/product/human acceptance is inferred.

The final boundary audit checks all 202 files from this continuation's initial
jj snapshot `cd8019a1`: earlier artifacts remain byte-identical, with append-only
Taskfile/task/acceptance prose. It also checks the 166 protected original files
against k66 and the unchanged lock records. The installed launch's ephemeral
`_uv_ephemeral_overlay.pth` existed unchanged on both sides of its measurement
and was removed by uv after that child returned; the audit records this one
expired launch subject explicitly. Installed package/module/library bytes still
exist and rehash exactly; no disappearance is credited as a current-file match.

## Complete MediaBox Cairo rendering — continuation on 2026-10-12

The internal `bookscan.render` adapter renders a verified private snapshot into
uncommitted complete RGB, checking the snapshot before/after and validating
occurrence/geometry, dimensions, PNG format and decoded mode. It propagates the
owner's cancellation through the existing child executor; it introduces no
public baseline operation, saved project or accepted asset. Resume rendering can
use the private snapshot after the original disappears. The complete F stays live.

Use Poppler 26.10.0 `pdftocairo`, white-background RGB PNG, default antialiasing,
complete MediaBox and static appearances, with effective DPI `300 * UserUnit`.
The exact rational full-page pixel extent controls output allocation; no scale-to
or subsequent pixel resizing is used. The read-only renderer version check gives
DEPENDENCY_UNAVAILABLE/5 for incompatible tools; failed/incomplete/mismatched
render output gives RENDER_FAILED/5. The operation owner must integrate complete
dependency provenance and these errors before accepting an initial checkpoint.
The exact API/scale/box/appearance/filter decisions were checked against
[Poppler's official 26.10.0 release source](https://poppler.freedesktop.org/poppler-26.10.0.tar.xz),
especially utils/pdftocairo.cc, poppler/Page.cc, GfxState.cc and CairoOutputDev.cc.

The first independent aligned-RGB construction rejected Splash/pdftoppm: its
floor(x)+1 upper image bounds and bilinear upsampling below 4x enlargement alter
source samples even with Interpolate=false. A 300x150 construction changes 39,999
pixels. This is a failed preservation mechanism, not signed >300-ppi loss.
The same source and independently declared truth pass exactly through Cairo.
No source representation/policy, Pillow/native version, preparation renderer or
native helper/cache changed. An actual Splash wrong-subject control remains in
the runner and is rejected on every final reading. Cairo remains subject to the
unperformed complete composition/unaligned/colour/fine-feature checks below.

Construction truth precedes all comparison outputs in
[truth.json](baseline-render/truth.json). Integer 72x36 and decimal 14.4x9.6
user-unit rectangles at (10,20), reversed MediaBox/CropBox corners, independent
clockwise 0/90/180/270-degree pixel permutations and UserUnit 1/2 give declared
physical extents and whole RGB buffers. Contributing RGB samples are on the
exact output grid; nested Forms/resources/matrices position them. Independent
green vector and magenta static-stamp regions include CropBox-hidden material.
No output-derived tolerance is used. All twelve construction variants, one blank
and one duplicate pass exact full-buffer and physical comparisons. The ten
observed wrong-subject controls reject image, orientation, unit, channel, erased
vector, erased static appearance, actual CropBox rendering, actual changed nested
CTM, order and Splash preservation, with unrelated geometry/source checks green.
The original decimal construction is retained and passes under Cairo too.

```sh
task --exit-code process:render-acceptance ARTIFACTS='/unused/artifact directory'
task --exit-code process:check
```

Final evidence is [verification.json.gz](baseline-render/verification.json.gz),
[render A](baseline-render/render-a.json), [render B](baseline-render/render-b.json)
and [installed verification](baseline-render/installed-verification.json.gz).
Full logs, source fixtures, PNGs, wheel and verifier are at
`/private/tmp/bookscan-k63-render-work/evidence-v2`. The earlier reading is
superseded: its installed provenance enumerated Python's base environment,
missing uv overlay package bytes. The final reading asserts actual imported
bookscan/render/Pillow/pikepdf paths outside this checkout and freezes those
packages. All 9,839 primary and 1,527 installed subjects are unchanged before/
after; installed wheel source matches product source exactly. Fourteen focused
unit outcomes and every construction/control agree itemwise across both primary
runs and the actual installed wheel. Source-loss rendering passes.

The identity record follows static Mach-O references to 40 non-system linked
files, including Poppler/Cairo/font/image/colour codecs, retaining complete load
commands, resolved paths and hashes. Apple shared-cache references are named
with the actual OS build, without invented on-disk hashes. This is static
characterization, not proof of runtime dlopen/font/config/ICC resource access or
complete dependency preflight integration. Those remain milestone-1 work.

The new render recipe, process:check (Ruff, strict types, 353 tests), staff checks,
Task discovery, wheel build/installed run and unchanged read-only native preflight
pass. Synthetic preparation's nine cases/24 pages and all 38 actual installed
preparation writer faults match the prior frozen report itemwise, including
full geometry/resources/roles/order/RGB, exits/results/visibility/source identity/
reaping. No copying, native settings/cache or frozen experiment changed.

Scope remains bounded to these constructions. Font/inline-image/stencil/mask/
grayscale/unaligned/ICC and >300-ppi fine-detail fidelity, the complete contributing
placement/ppi/source-native analyzer and persisted every-occurrence assessment
are unfinished. No real-case truth/reaction, native-view packet/refresh usability,
project/checkpoint/lock, finite writer fault, denied-read workflow or public
review/export result is supplied here. All remain in F's original inventory.

## Read-only static dependency boundary — 2026-10-13 continuation

`bookscan.dependencies.preflight` combines the unchanged helper/cache/version/
self-test record with the actual selected Poppler 26.10.0 Cairo renderer,
transitive static Mach-O identities for Cairo and the imported `PIL._imaging`/
`pikepdf._core` extensions, and Pillow 12.3.0 supported feature/codec versions.
It checks one native architecture, follows load/weak/reexport/upward/lazy library
commands and runpaths, ignores a dylib's own install ID, rejects malformed/
unresolved/ambiguous/context-dependent references and verifies file hashes again
after traversal. Extension `@executable_path` uses the actual Python interpreter.
Apple shared-cache references carry the actual OS build and explicitly claim no
absent on-disk bytes. The selected owner's cancellation passes unchanged through
commands/chunked hashes and terminates/reaps its actual owned native child.

The decisions were checked against [Apple's load-command definitions](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/EXTERNAL_HEADERS/mach-o/loader.h),
[Apple's runpath documentation](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/RunpathDependentLibraries.html)
and [Pillow 12.3.0's feature API](https://pillow.readthedocs.io/en/stable/reference/features.html),
with source links beside the corresponding calls. Known constructed graphs
independently declare expected edges/bytes, nested runpaths/cycles/executable
context and bad-reference outcomes. Observed failing tests exposed a system-path
parent escape and the missing extension executable-context API before repair.

```sh
task --exit-code process:dependency-preflight NATIVE_CACHE='/existing helper cache'
task --exit-code process:dependency-acceptance NATIVE_CACHE='/existing helper cache' REPORT='/unused/report.json'
```

These are additional working read-only tasks beside the unchanged helper tasks.
They create no project or accepted import. Every result explicitly records
`runtime_resources_verified: false`: this static record is not an observation
of dyld's actual loaded closure, dynamically loaded codecs, font substitutions/
files, ICC profiles, configuration or environment-dependent resources. The
remaining native/Python extensions and actual tool implementation identities
still need operation integration. The present roots cover the renderer and
core PNG/RGB/PDF modules; supported feature version reporting is not a hash of
every optional Pillow module. Complete runtime provenance remains milestone 1
work, before accepted state; this boundary must not be mistaken for that result.

Final frozen evidence is [verification.json.gz](baseline-dependencies/verification.json.gz),
[native A](baseline-dependencies/native-a.json), [native B](baseline-dependencies/native-b.json)
and [installed verification](baseline-dependencies/installed-verification.json.gz).
Logs, wheel, verifier and full per-item preparation records remain at
`/private/tmp/bookscan-k63-dependencies-work/evidence-v2`. All 8,978 primary and
1,577 installed read subjects are unchanged before/after; actual imported wheel/
Pillow/pikepdf paths are outside this checkout and their package bytes are frozen.
Twenty-seven unit identities/outcomes agree on both runs. The full static
graph records, feature/renderer/helper meanings and six selected-child outcomes
agree itemwise across primary A/B and the actual wheel, comparing file/edge bytes
while retaining raw environment paths. Per-run child PIDs are retained separately.

The record contains 40 Cairo, eight Pillow imaging and three pikepdf core files.
Cairo's files/hashes equal the previous independently written test-owned static
characterization. Missing-Cairo and deliberately dropped native-callback controls
are observed failing. Each of the six actual Cairo/sw_vers/otool children is
reaped, the selected 130/143-style owner exception is preserved and the cache stays
byte-exact. No OS signal is sent by these callbacks; installed finite-writer
SIGINT/SIGTERM/SIGKILL/lock/checkpoint checks remain required. Missing cache gives
DEPENDENCY_UNAVAILABLE/5 without creating it.

Both new recipes twice, process:check (Ruff/strict types/380 tests), staff checks,
Task discovery, exact wheel-source bytes and the unchanged helper preflight pass.
Synthetic preparation's nine cases/24 pages and all 38 installed preparation
writer fault outcomes agree itemwise with the prior frozen reading, including
geometry/resources/roles/order/RGB, exits/results/visibility/source identity/reaping.
No preparation/renderer/helper/cache/settings/native/manifest/lock/experiment
change follows from these added internal mechanisms.

F remains live in its original open change. Next complete actual runtime resource
provenance and the contributing-placement/ppi/sample/mask/colour/source-native
analyzer with independent mixed font/inline/stencil/mask/grayscale/unaligned/ICC/
>300-ppi fidelity controls, then integrate snapshot/render/helper into saved
every-occurrence assessment/provenance/regions. All original saved-project/
ownership/checkpoint/source-loss-reader, matched packet/native/global-refresh,
receipt/Q1–Q3/replay/inspection/selection-union acknowledgement, exact export/
report/publication, installed faults/isolation, six-case/resources/predecessor
and five B-reuse requirements remain. This is no public or fidelity handoff.

The first dependency reading is superseded for complete build provenance: its
uv build used an isolated Hatchling environment not separately enumerated. The
final v2 wheel is built through explicit pinned Hatchling 1.27.0, with actual
distribution/package paths, build inputs, interpreter and before/after hashes
retained in [build verification](baseline-dependencies/build-verification.json.gz).
All 7446 build subjects remain unchanged. To stay below jj's existing
new-file guard, the primary archive references that separate lossless build
record by filename and decoded-byte digest. Materializing the reference reproduces
the original complete v2 verification JSON bytes exactly. No repository guard
setting changes. The complete rerun retains the same per-item native/unit/
installed/preparation outcomes; raw v1 logs stay diagnostic at the earlier
temporary path. No product/native-source fix follows from the verifier correction.

## Conservative placement/resolution analyzer — internal, 2026-10-13

The product now parses every content operator to inventory repeated image
placements, q/Q/cm state, nested Form matrices/resource scopes, inline images,
stencils and attached image/soft-mask grids. Supported static annotation
appearances use the ISO BBox/Matrix/Rect mapping. Physical resolution follows the
intrinsic sample axes after page Rotate/UserUnit; it is not inferred from a
raster bounding box. Decimal matrices remain rational until ppi reporting.
The above-300 reason uses exact squared rational lengths, so a reporting float
rounded to 300 cannot hide an above-ceiling placement.

Unaccounted pattern/shading/Type3/graphics-state soft-mask paths, invalid/missing
resources, cyclic or excessive nesting and invalid transforms leave named
unavailable concerns. Partial placements remain diagnostics and cannot supply a
complete <=300-ppi conclusion. Clipping and occlusion are conservatively
counted; this can overstate contributing resolution, never discard fine detail.
The `import_fidelity` boolean means a resolution reason is required; false is
no source-fidelity verdict. Native samples/Decode/mask/ICC/colour identities and
independent composition-fidelity checks are still unfinished. This reader is an
internal operation over the verified snapshot; it introduces no public route,
accepted project, saved assessment, receipt or export handoff.

Reproduce the working construction/visibility recipe in an unused directory:

```sh
task process:placement-acceptance ARTIFACTS='/tmp/NEW placement evidence'
task process:check
```

[Pre-output truth](baseline-placement/truth.json) declares exact physical
placements for four Rotate/half-UserUnit/reversed-box pages, repeated placements,
nested resource shadowing, mask/stencil/inline grids, a rotated static appearance,
blank and duplicate occurrences. Isolating wrong CTM, unit-resolution, resource,
order, missing-mask and partial-inventory subjects are observed failing while
unrelated occurrence and original/snapshot-byte checks stay green. The order
control preserves its count and is rejected on its first mismatched ppi.
These controls test placement/resolution, not complex composition truth.

Actual Cairo 26.10.0 PNG rendering agrees with independently declared constant
gray/white visibility for static Stamp F=0/1/2/4/32: Invisible alone still draws;
Hidden/NoView do not. Full 300x300 RGB buffers are exactly 128 or 255 in all
channels. This is a bounded aligned visibility construction, not an oracle for
real composite pages. Forty-two focused cases also cover incomplete paths,
source-loss/corruption, exact near-ceiling decimals, resource inheritance and
selected owner cancellation through nested traversal. Caught cancellation
preserves the owner's original exception rather than recording PDF unavailability.
No OS writer signal/lock/checkpoint behaviour is inferred here.

Final frozen evidence lives at
`/private/tmp/bookscan-k63-placement-work/evidence-v2`. The earlier stopped
reading remains diagnostic: its temporary verifier incorrectly expected the
order oracle's matrix diagnostic, although ppi correctly failed first. All edits
finished before the corrected whole reading began. Retained records:

- [Primary verification](baseline-placement/verification.json.gz)
- [Construction/native A](baseline-placement/placement-a.json) and
  [B](baseline-placement/placement-b.json)
- [Installed wheel verification](baseline-placement/installed-verification.json.gz)
- [Actual pinned builder verification](baseline-placement/build-verification.json.gz)

The 9,096 enumerated primary subjects, 1,487 installed subjects and 7,447 actual
Hatchling 1.27.0 build subjects have matching before/after digests. Runtime-loaded
resources remain explicitly unverified; these inventories do not certify their
completeness. Builder packages are enumerated from their actual distribution
paths. The primary archive references its separately retained lossless builder
record by decoded-byte digest; materialization exactly reproduces the complete
measured JSON, within jj's unchanged file guard. The actual wheel contains every
product source/resource byte exactly and runs outside the checkout. Its full
15-occurrence/placement/control/source-loss/native-visibility result equals both
primary runs item by item. Official pinned parser/image source bytes also match
the installed 10.16.0 source.

The new recipe twice, all 42 focused case identities twice, process:check and
prepare:check (Ruff, strict types, 422 tests), staff checks, task discovery,
unchanged helper preflight and the actual wheel pass. Preparation's nine
synthetic cases/24 pages and all 38 installed preparation writer faults agree
itemwise with the earlier dependency reading, including geometry/resources/
roles/order/RGB and exits/results/visibility/source identity/reaping. No copying
engine, renderer/helper, native version/settings/cache, dependency manifest/lock
or historical experiment changed. Existing real preparation comparisons retain
their unchanged subjects; no new real-page fidelity/reaction is claimed.

Milestone 1 and the complete F owner remain live. Next integrate native-source
sample/colour/mask metadata and independent mixed-composition fidelity controls,
actual runtime resource identity and every-occurrence saved assessment; then
complete the original project/ownership/packet/receipt/replay/ack/export/public/
fault/isolation/six-case/compatibility/B-reuse inventories before retirement.

## Source-native packed samples — continuation on 2026-10-13

`bookscan.samples.collect` now consumes the verified private snapshot and the
placement walk's exact image/resource scopes. It retains raw packed channels per
contributing placement, separate stencil/explicit-mask/soft-mask grids, original
bit depth and row padding, filter/decoder parameters, Decode/interpolation,
colour-key masks and Matte. DeviceGray/RGB/CMYK, Indexed palette bytes/base/high
and ICC profile bytes/ranges/local default-colour substitutions are recorded.
The sample bytes never apply Decode, colour conversion, interpolation, masks,
placement, clipping or blending. A decoded sample is not an RGB page oracle.
Unsupported specialized DCT/JPX/CCITT/JBIG2 decoding and other colour
interpretations retain precise unavailable records. No largest-image substitute
or native-view/composition-fidelity result follows.

Pinned pikepdf 10.16.0's generalized stream decoding is verified against its
[Object API source](https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/_core/_object.pyi)
and [inline-image source](https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/models/image/_classes.py).
The convenience inline decoder creates a temporary page with a three-unit minimum;
the reader instead decodes a disposable stream, preserving tiny sample grids.
Unfiltered inline data includes qpdf's pre-EI whitespace; only bytes beyond the
declared grid can be treated as delimiter. Source/decoder bytes stay unchanged.
PDF row/channel and colour metadata interpretations follow ISO 32000-1 sections
8.9.3, 8.6.5.5 and 8.6.6.3, with source citations at their code decision sites.

Working bounded recipe:

```sh
task --exit-code process:sample-acceptance ARTIFACTS='/unused/output directory'
```

[Pre-output truth](baseline-samples/truth.json) declares six literal 1/2/4/8/16-bit
gray/RGB/CMYK grids, independent integer channels, Decode and exact physical
placement. A duplicate and blank retain eight input positions. Bounds are exact
packed bytes/channel values, with no output-derived tolerance or renderer oracle.
Observed wrong-image, padding/channel, colour, Decode, ppi, placement and order
subjects fail their named checks; unrelated checked fields remain green.
The [first](baseline-samples/sample-a.json) and
[second](baseline-samples/sample-b.json) readings and actual installed wheel agree
itemwise. Original deletion is deliberate test-owned source-loss work; the saved
snapshot remains byte-exact and supports every repeated sample read.

The final isolated reading is `/private/tmp/bookscan-k63-samples-work/evidence-v2`.
[Primary verification](baseline-samples/verification.json.gz),
[installed verification](baseline-samples/installed-verification.json.gz) and
[pinned-builder verification](baseline-samples/build-verification.json.gz) retain
9,106 / 2,193 / 7,448 actual enumerated read subjects unchanged before/after.
The builder subrecord is factored losslessly by decoded-byte digest. Actual
installed package paths are outside this checkout; every product source/resource
in the wheel matches measured bytes. All 27 sample test identities/outcomes agree
across both checkout runs and the installed wheel, normalizing only the explicit
`tests.test_samples` → `runners.test_samples` relocation prefix and retaining raw
JUnit names. The first reading stopped at that namespace comparator mismatch and
remains diagnostic; no product change was required by its correction.

The new recipe twice, process:check and prepare:check (Ruff, strict types and
449 tests), staff checks, task discovery, unchanged helper preflight and actual
wheel checks pass. The complete placement/ppi and five actual Cairo annotation
visibility records equal the prior reading. Synthetic preparation's nine cases /
24 pages and all 38 installed writer-fault outcomes agree with prior final
placement evidence itemwise, including geometry/resources/roles/order/RGB and
exact exits/results/visibility/source identity/reaping. Preparation sources,
renderer/helper/cache/native versions/settings, manifest/lock and frozen
experiments are unchanged; no affected real preparation subject changed.

Milestone 1 remains unfinished. Specialized source codecs, validated colour and
mixed vector/font/inline/mask/unaligned/ICC/>300-ppi composition controls, actual
runtime resource discovery and saved every-occurrence advisory assessment remain
required before accepted import. All project/lock/checkpoint/packet/action/export,
ordinary-viewer refresh, installed faults/isolation/six-case/resource/compatibility
and B-reuse work remains in F. This bounded internal reader supplies no installed
finite operation, accepted project, full source-fidelity verdict or human response.

## Specialized source channels — continuation on 2026-10-13

The sample reader now adds bounded DCT grayscale/ordinary RGB and CCITT G3/G4
decoding. It normalizes a disposable image stream, verifies the actual decoded
mode/dimensions against the declared grid, and returns native channel samples.
Decode, ICC conversion and masks remain separate metadata. Lossless wrappers,
inline images and stencil scopes retain their own source identity. This extends
the earlier specialized-codec unavailability for those supported paths only.
CMYK JPEG polarity, nonstandard ColorTransform, JPX codestream/colour/alpha and
JBIG2 external/global decoding remain unavailable. No complete-page composition
or real-JPEG fidelity oracle follows from a decoded sample.

The exact [pikepdf 10.16.0 image API](https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/models/image/_classes.py)
and [extraction source](https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/models/image/_extract.py)
were checked before implementation; the latter equals the installed source
byte-for-byte. Explicitly disabling Decode/mask processing preserves raw channels.
Malformed grid/parameter/type or decoder failures are named unavailable. CCITT
byte alignment, nondefault EndOfBlock/damaged-row handling and unverified codec
chains are unavailable rather than silently ignored. Selected owner cancellation
still propagates unchanged through recursive handlers.

Working bounded recipe:

```sh
task --exit-code process:codec-acceptance ARTIFACTS='/unused/output directory'
```

[Pre-output truth](baseline-codecs/truth.json) declares eight constructions:
exact neutral JPEG DC channels, constant-colour Q100/no-subsampling JPEG with
an independently declared two-level integer channel bound, hand-encoded T4
white/black runs, G4 polarity and wrapped/inline/stencil paths. The hand stream
`001a0009a880` uses TIFF6 section 10's EOL, white9, white0 and black9 codes;
it depends on no image encoder. TIFF BlackIsZero reverses self-photometric fax
runs; the initial TIFF-derived expectation was corrected after this independent
check. Canonical row padding is not an image sample. Eight altered subjects
reject wrong size/depth/channel/erased feature/polarity/row order/Decode and false
composition credit, with unrelated fields green. Source/snapshot bytes remain
exact, and sample rereads succeed after deletion of each test-owned original.

The [first](baseline-codecs/codec-a.json),
[second](baseline-codecs/codec-b.json) and installed-wheel records agree itemwise.
Final frozen verification is `/private/tmp/bookscan-k63-codecs-work/evidence`.
[Primary](baseline-codecs/verification.json.gz),
[installed](baseline-codecs/installed-verification.json.gz) and
[pinned-builder](baseline-codecs/build-verification.json.gz) records retain
9,113 / 2,193 / 7,448 enumerated read subjects unchanged before/after. The builder
subrecord is factored by decoded-byte digest and reproduces the complete measured
JSON exactly. Actual wheel modules are outside this checkout and match product
source/resource bytes. All 34 focused test identities/outcomes agree on both
checkout readings and the wheel, retaining raw JUnit names and normalizing only
the explicit test-directory relocation prefix.

The new recipe twice, process:check and prepare:check (Ruff, strict types and
483 tests), staff checks, Task discovery, unchanged helper preflight and actual
wheel checks pass. The previous complete raw-sample and placement/ppi/native
annotation records remain equal itemwise. Synthetic preparation's nine cases /
24 pages and all 38 installed writer-fault outcomes equal prior final sample
evidence, including geometry/resources/roles/order/RGB and exact exits/results/
visibility/source identity/reaping. Preparation, renderer/helper/cache/native
versions/settings, manifest/lock and frozen experiments did not change; existing
real preparation comparison subjects remain intact.

Milestone 1 remains live for validated colour/display and independent mixed
vector/font/inline/mask/grayscale/unaligned/ICC/>300-ppi composition controls,
actual runtime resources and saved every-occurrence advisory assessment. All
original saved-project/ownership/packet/action/export/public/fault/isolation/
six-case/resource/compatibility/B-reuse work remains required before F retirement.

## Native colour interpretation — continuation on 2026-10-13

The internal `bookscan.colour` seam now interprets the previously verified native
samples without changing packed bytes, a source snapshot or any baseline. Exact
rational channels apply PDF Decode followed by colour-space clipping. Indexed
Decode maps to an index, rounded to nearest with half ties upward and clipped to
hival, then expands lookup bytes into the base colour's declared ranges. Device
Gray/RGB and their Indexed bases produce separately labelled uncombined native
RGB display bytes. A colour-key alpha plane tests every raw component's inclusive
range before Decode or palette expansion. Neither this plane nor a display byte
array composites a page.

The [PDF standard](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf),
sections 8.9.5.2/Table 90, 8.6.6.3 and 8.9.6.4, supplies the decoding, lookup and
raw-mask rules. The standard was downloaded/read before implementation; its bytes
and text extraction are frozen reading subjects. Display quantization is explicitly
nearest 8-bit with half ties upward. Exact rational source channels remain available
separately, including 16-bit detail; the diagnostic display is not a lossless
high-bit-depth colour representation. No sRGB or calibrated display/profile meaning
is inferred from DeviceRGB. Default resource substitutions are honoured by the
existing sample reader rather than discarded for a convenient device display.

ICC and CMYK retain decoded source-space channels and metadata, but RGB conversion
is unavailable with a named missing profile/colour oracle. A stencil or soft-mask
view is labelled as a diagnostic plane, with no stencil paint colour, soft-mask
composition, Matte unpremultiplication, page clipping, placement, interpolation or
blending applied. Missing specialized sample decoding stays unavailable. The
complete-page independent colour/vector/text/mask oracle remains unfinished.
This is an internal byte-display seam; no new ordinary-viewer observation, packet,
accepted project, public finite command or composition-fidelity pass is claimed.

Eighteen focused tests exercise packed-row order/padding, reverse/out-of-range/
constant Decode, exact 16-bit channels, Indexed defaults/reversal/half ties/clipping,
ICC lookup range expansion and local DefaultRGB substitution, raw-before-Decode/
raw-before-palette colour-key alpha, diagnostic mask labels and unchanged selected
owner-cancellation exceptions. The initial absent-module RED preceded production
implementation; 121 focused colour/codec/sample/placement cases pass.

The reusable recipe is:

```sh
task --exit-code process:colour-acceptance ARTIFACTS='/existing parent/unused directory'
```

Its [pre-output truth](baseline-colour/truth.json) declares eight literal native
constructions. Exact rational channels and diagnostic RGB/alpha bytes pass for
2-bit grayscale, reversed grayscale, reversed RGB with colour-key alpha, clipped
Indexed RGB, stencil bits and 16-bit grayscale. ICC/CMYK conversion unavailability
is separately verified with retained channels. The ten-page source preserves an
explicit blank and duplicate position; source-loss rereads reproduce every sample
inventory, and source/snapshot bytes remain unchanged. Nine isolated wrong-grid,
wrong-depth, erased-source-feature, ignored-Decode, wrong-palette-colour,
Decode-before-key, fabricated-ICC-RGB, false-conversion-availability and
false-composition subjects fail only their named comparator field. These controls
contest the declared native channel/display mechanism, not full-page fidelity.

Final frozen verification is `/private/tmp/bookscan-k63-colour-work/evidence`.
[Primary](baseline-colour/verification.json.gz),
[installed](baseline-colour/installed-verification.json.gz) and
[pinned-builder](baseline-colour/build-verification.json.gz) records retain all
9,121 primary, 2,194 outside-checkout installed and 7,449 actual Hatchling 1.27.0
build read subjects unchanged before/after. The factored build reference carries
the decoded-byte digest and materialization instructions; expanding it reconstructs
the complete measured JSON bytes exactly. This retention changes no measurement.
All actual installed product/resource bytes equal the checkout; no module imported
from this workspace supplies the installed colour reading.

Two recipe readings ([A](baseline-colour/colour-a.json),
[B](baseline-colour/colour-b.json)) and the installed wheel agree itemwise on eight
constructions, nine controls, all ten source positions and source-loss bytes. All
18 unit identities/outcomes agree twice and in the wheel, normalizing only the
declared `tests` versus relocated `runners` JUnit prefix while retaining raw names.
`process:check`/`prepare:check` pass Ruff/strict types/all 501 tests, staff checks
and task discovery pass, and the existing helper preflight is unchanged. Earlier
codec/sample/placement/ppi and five Cairo annotation records agree exactly.
Synthetic preparation's nine cases/24 pages and all 38 installed writer faults
agree with the prior frozen reading, including geometry/resources/order/roles/RGB,
exact exits/results/visibility/source identity and actual writer reaping. No
preparation, renderer/helper/native settings/cache, manifest/lock or frozen
experiment changed. Runtime-loaded resource completeness stays unverified.

F remains live in its original open jj change. Next verify actual profile/device
colour conversion and independent mixed composition/fine-detail truth, discover
runtime native/font/ICC/config/environment resources, and couple snapshot/render/
placement/sample/helper into every-occurrence saved assessment/hint provenance.
All saved-project/lock/checkpoint/status/resume, matched full/native/source-native
packet/ordinary-viewer refresh, Q1–Q3 actions/replay/scoped acknowledgement, exact
export/report, installed writer/isolation/migration faults, six actual resource/
truth packets and complete B reuse/compatibility evidence remain required. These
native channel/display checks complete neither milestone 1 nor F and supply no
human geometry, colour-fidelity, preparation or product acceptance.

## Analytic composed pixels — continuation on 2026-10-13

`process:composition-acceptance` now verifies actual `bookscan.render` Cairo
pixels against renderer-independent construction truth. It supplements the
previous exact RGB/vector/Form/annotation/box controls with grayscale, one-bit
fine detail, inline images inside a Form, stencil paint/polarity, explicit masks,
raw-before-Decode colour-key masks and soft-mask composition. The nine mechanisms
occupy an eleven-page ordinary PDF with a blank and duplicate preserved at their
original positions. Every frame is independently declared as 15.36×7.68 points,
64×32 baseline pixels at 300 dpi. No largest-image extraction or baseline/export
equality computes the expected page pixels.

[ISO 32000-1](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf)
sections 8.9.4–8.9.7 and 11.6.5.3 supply sample coordinates, inline syntax,
stencil/explicit/colour-key and soft-mask semantics. The already verified official
PDF and its text extraction are frozen read subjects. DeviceGray/DeviceRGB
channels have no independently calibrated display or ICC meaning here. The
source-channel interpretation seam remains separately labelled and uncombined;
these tests add bounded composition evidence without making it a compositor.

| Construction | Independent pixel/feature obligation and observed result |
| --- | --- |
| Aligned 8-bit grayscale, one-bit alternating columns, inline grayscale | All 2,048 pixels match exact declared channels, including every one-pixel black column. Inline 8×4 samples expand into known 8×8 cells, with interpolation disabled. |
| Stencil and reversed stencil | The literal bit grid paints blue over a green vector background at the declared polarity; all pixels match exactly. |
| Explicit mask | An independently packed mask paints pure red or leaves the green background; all pixels match exactly. |
| Colour-key with reversed Decode | Raw zero is transparent before Decode; other samples decode to black. Exact composition preserves the green background rather than testing the decoded key. |
| Soft mask | Pure red over pure blue at alpha 0/85/170/255 yields exact integer RGB `(alpha,0,255-alpha)` without a fitted tolerance or premultiplication ambiguity. All pixels match exactly. |
| Half-pixel-shifted 150-ppi grayscale | Source cell `s` occupies `[0.5+2s,2.5+2s)` in baseline pixel edges. Intersecting cells determine each pixel's local convex grayscale interval before rendering. All channels remain neutral; 1,280 interior pixels are exact and 768 boundary pixels satisfy those predeclared local bounds. The one-sample black feature has a guaranteed exact black interior at x=5 and remains present. |
| Blank and duplicate occurrences | All pixels, positions, dimensions and physical frames match their separate declared records. |

The phase bound permits only values between source cells touching that destination
pixel, plus white background where exposed. It cannot permit arbitrary nonlocal
blur or hide colour-channel drift. It is a feature/grid bound for this construction,
not a claim of exact fractional-grid sampling, a universal interpolation method
or preservation at every phase. All other constructions require exact every-pixel
RGB. Full-page bound buffers are written and hashed before any comparison output,
and remain unchanged through native rendering and source-loss rereads.

Ten oracle tests were observed failing before implementation, then passed. They
reject a changed exact channel, an erased feature, nonlocal phase colour,
non-neutral grayscale, wrong dimensions/byte counts and malformed/inverted bounds.
Twelve observed wrong-subject controls reject wrong image/order/stencil polarity,
missing masks, Decode-before-key alpha, erased aligned/misaligned features and
wrong colour. Three use actual native renders of source PDFs with one explicit
mask removed, one soft mask removed, or the image CTM shifted. Page frames and
positions stay unchanged; the unaffected inline composition still passes.
These controls and complete source-loss rerenders are included in both readings.

```sh
task --exit-code process:composition-acceptance ARTIFACTS='/existing parent/unused directory'
```

[Pre-output truth](baseline-composition/truth.json),
[reading A](baseline-composition/composition-a.json),
[reading B](baseline-composition/composition-b.json) and
[complete construction fixtures](baseline-composition/fixtures.zip) retain the
exact source snapshot, original bounds, actual PNGs and native wrong-source
controls. The ZIP's fixed-timestamp members were compared byte for byte with
the measured reading; its `snapshot.pdf` is an ordinary source fixture, not a
saved review project. It includes no claim of actual viewer inspection.

Final evidence is `/private/tmp/bookscan-k63-composition-work/evidence`.
[Primary verification](baseline-composition/verification.json.gz),
[outside-checkout installed verification](baseline-composition/installed-verification.json.gz)
and [Hatchling build provenance](baseline-composition/build-verification.json.gz)
record 9,130 primary, 2,243 actual installed and 7,449 actual pinned-builder
subjects unchanged before/after. Materializing the primary record's builder
reference by its decoded-byte digest reconstructs the original complete measured
JSON exactly. The two recipe readings and actual installed wheel agree itemwise
on all page/control/truth/source-loss records. The ten unit identities/outcomes
agree twice and outside the checkout, normalizing only the documented `tests`
versus relocated `runners` JUnit prefix and retaining raw names.

`process:check`/`prepare:check` pass formatting, Ruff, strict types and 511 tests;
staff checks, Task discovery, helper preflight and the actual wheel build pass.
Earlier complete render/colour/codec/sample/placement and Cairo-annotation records
agree exactly. Synthetic preparation's nine cases/24 pages and all 38 installed
writer faults match the earlier frozen reading itemwise, including complete
geometry/resources/order/roles/RGB, exits/results/visibility/source identity and
reaping. No renderer/helper/native settings/cache, product source, manifest/lock,
preparation or frozen experiment changed. Evidence retention follows completed
measurement, with no subjects edited during a run.

Required font/ICC/device-colour/Matte/general-composition and >300-ppi independent
controls, runtime-loaded font/profile/config/dlopen resources and every-occurrence
saved assessment remain unfinished. Complex real numerical truth remains precisely
unavailable until its oracle is established. These tests complete neither
milestone 1 nor F. Project ownership/checkpoints/status/resume, actual matched
packets/native/global refresh, Q1–Q3 actions/replay/acknowledgement, exact export,
installed finite-writer/isolation/migration faults, six real packets and B reuse
still belong to this live owner. No product, real preservation or human visual
acceptance is inferred from these synthetic device-channel results.

## Coupled occurrence assessment — continuation on 2026-10-13

The private `bookscan.assessment` boundary now connects verified snapshot,
complete immutable RGB, placements/native samples and disposable native analysis
for every source position. Its detached JSON records retain physical geometry,
immediate-source advisory hints, source/decoded digests, sample/decoder metadata,
analysis status/angle/ratio/settings/regions and initial unresolved reasons.
RGB is checked unchanged after analysis; no estimate, inspection or fidelity
acceptance is applied. These are uncommitted import artifacts. Complete saved
assets/checkpoints and the public workflow remain unfinished.

Reproduce the actual synthetic coupling with an existing verified helper cache:

```sh
task process:assessment-acceptance \
  ARTIFACTS='/existing/NEW assessment directory' \
  NATIVE_CACHE='/existing/product helper cache'
```

The [pre-output truth](baseline-assessment/truth.json) declares seven positions:
front/upright, content/+2-degree rows, back/-2-degree rows, +6.5-degree sweep-edge,
blank with an invalid hint, 600-ppi channels, and a duplicate front occurrence.
Independent aligned black/white RGB buffers require exact every-channel equality.
The analytic row sign/control bound is 0.125 degrees (two-pixel phase over 1000
pixels plus the 0.01-degree search step), supplying no real-page accuracy bound.
The 600-ppi case verifies source-native packed bytes/placement/resolution only;
its 300-dpi raster has no declared preservation oracle.

Actual +2/-2-degree rows report -2.03125/+1.96875; the upright/duplicate report
-0.046875 and remain nonzero suggestions, with no deadband. Sweep-edge reports
status 0/ratio 0 with a separate edge reason; blank reports status 1/ratio 0.
The 600-ppi pattern also reports zero confidence and stays unavailable. Every
occurrence retains orientation, within-page and missing complete-composition
truth limitations; only skew-nonzero permits reject. Hint roles exempt no page.
Nine isolated wrong-record controls reject occurrence/RGB/hint/region/assessment/
limitations/inspection/applied-estimate/fidelity changes while the unrelated blank
stays correct. Source deletion precedes assessment; another actual complete
source-loss pass matches all seven records itemwise.

The final frozen reading is `/private/tmp/bookscan-k63-assessment-work/evidence-v2`.
[Verification](baseline-assessment/verification.json.gz) retains all 9,139
primary read subjects, commands, itemwise outcomes and preparation faults.
[Build provenance](baseline-assessment/build-verification.json.gz) retains 7,450
actual Hatchling 1.27.0 subjects; its reference expands the measured JSON
byte-exactly. [Installed reading](baseline-assessment/installed-verification.json.gz)
retains 2,242 subjects and outside-checkout package paths. All before/after digests
match. [Reading A](baseline-assessment/assessment-a.json) and
[reading B](baseline-assessment/assessment-b.json) match complete records and the
installed wheel. [Fixtures](baseline-assessment/fixtures.zip) retain every measured
snapshot/truth/report member exactly. [Pinned Pillow source](baseline-assessment/pillow-frombytes.txt)
records the verified copy-allocation API used beside its source citation.

Twenty-one focused tests agree in both checkout runs and the installed wheel,
normalizing only the documented relocated JUnit prefix. `process:check`,
`prepare:check` (532 tests, format/lint/strict types), staff checks, Task discovery,
the unchanged helper preflight, wheel build and the new recipe twice pass.
Earlier render/colour/codec/sample/placement/composition records agree itemwise.
Synthetic preparation's nine cases/24 pages and 38 actual writer faults also
match the earlier reading, including full geometry/resources/order/roles/RGB and
exact exits/results/visibility/source identity/reaping. An initial verification
instrument named an unused uncopied helper; it stopped before its installed
reading and was discarded. All edits preceded the complete final measurement.

This advances milestone 1 without completing it. Required font/ICC/device-colour/
Matte/general composition and >300-ppi construction controls and actual runtime
resource verification stay live. Project assets/ownership/checkpoints/status,
matched packets/ordinary-viewer scale/global refresh, Q1–Q3 actions/replay/inspection/
acknowledgement, exact export, installed finite-writer/isolation/migration faults,
six actual resource/truth packets and compatible predecessor/B reuse remain
required. Complex real numerical truth and human responses retain their precise
unavailable/pending ownership; no source study, product or visual acceptance follows.

## Embedded text, Matte, Screen and high-resolution detail — 2026-10-13

The independent `process:advanced-composition-acceptance` recipe supplements the
existing composed-pixel checks with five constructions in an ordinary seven-page
PDF, retaining a blank and duplicate. All pages have a declared 15.36×7.68-point
frame and a 64×32 RGB baseline. Truth buffers, the native 128×64 grayscale grid
and their digests are written before any native render. No product decoder,
placement walker, alternate render or unchanged export computes the expected
composed RGB.

```sh
task --exit-code process:advanced-composition-acceptance \
  ARTIFACTS='/existing parent/NEW construction directory'
```

The verified official [ISO 32000-1](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf)
provides Type3 glyph semantics (§9.6.5), Screen (§11.3.5/Table136), soft-mask
Matte inversion (§11.6.5.3/Tables145–146) and transparency groups (§11.6.6).
Its complete bytes/text and selected Poppler 26.10.0 Cairo source are frozen
reading subjects. The web tool could not open the large PDF; the previously
verified official local PDF/text was read directly. No new native API or render
settings were selected.

| Construction | Independent requirement and actual outcome |
| --- | --- |
| Embedded Type3 text plus RGB image and vector | Two explicit glyph programs declare a filled square and a square with a hole, exact advances and grid edges. All 2,048 RGB pixels match the literal glyph/image/vector truth. This verifies embedded constructed text without relying on a system font, hinting, or an alternate font rasterizer. |
| White and black Matte | True pure red is preblended with the named matte at alpha 85/255 or 170/255. Recovering the original colour before compositing over blue yields exact `(alpha,0,255-alpha)`. All pixels match for both mattes; no fitted rounding tolerance. |
| Isolated Screen group | Opaque red over blue inside an isolated DeviceRGB transparency group gives magenta in the left half and blue in the right half. Every pixel matches the analytic `1-(1-cb)*(1-cs)` primary-channel result. Other blend modes remain outside this bounded truth. |
| 600-ppi detail | Complete native grayscale samples and independently declared 600×600-ppi placement match exactly. The 300-dpi baseline keeps exact macro interiors and neutral bounded transition/fine regions. The declared source-native comparator detects lost alternating detail, separately from those passed baseline controls. |
| Blank and duplicate | Full pixels, geometry, source positions and duplicate equality remain exact; source deletion does not prevent a complete matching reread. |

The 600-ppi comparator explicitly evaluates each source sample centre against
its aligned constant baseline texel at a 2:1 mapping. The source alternates black
and white inside each baseline pixel in its fine band. No one texel can equal
both values: at least 2,048 of those native samples must change, independently
of the render's interpolation. The actual reading changes 4,096 of 8,192 native
samples, while the original source bytes remain intact. Its classification is
**failed (signed >300-ppi resolution limitation), synthetic only**. This is no
perceptual metric, universal interpolation oracle or real fixed-case loss. It
commissions no speculative loss-policy leaf. The bound also requires exact
large black/white interiors, so erasing the complete image cannot hide under the
fine-band range. Its scope and comparator are declared in the
[pre-output truth](baseline-advanced-composition/truth.json).

Ten oracle regressions were observed failing before their implementation. They
reject erased glyph ink, retained matte contamination, omitted blend colour,
erased macro detail, wrong native mappings and missing sample bytes. Ten
isolated comparison controls fail in each actual reading. Six change an actual
source PDF's glyph program, white/black Matte entry, Screen mode, macro sample
bytes or physical image CTM. Unrelated page pixels, page frames and/or native
sample bytes stay correct as appropriate to the isolated mechanism. The other
controls alter image/order/colour/feature subjects directly. No expected colour
or bound was changed to fit any rendered output.

The final frozen reading is `/private/tmp/bookscan-k63-advanced-work/evidence`.
[Reading A](baseline-advanced-composition/advanced-a.json),
[reading B](baseline-advanced-composition/advanced-b.json) and the actual installed
wheel agree on all seven source positions, ten controls, pre-output truth,
source-native loss and complete source-loss rereads. The
[fixtures ZIP](baseline-advanced-composition/fixtures.zip) retains every measured
snapshot, bound, native sample, PNG, report and altered-source member exactly;
it contains no saved review project or viewer inspection claim.

[Primary verification](baseline-advanced-composition/verification.json.gz)
retains 9,151 read subjects, commands and complete itemwise comparisons;
[installed verification](baseline-advanced-composition/installed-verification.json.gz)
retains 2,245 subjects and actual package paths outside the checkout;
[pinned build provenance](baseline-advanced-composition/build-verification.json.gz)
retains 7,450 actual Hatchling 1.27.0 subjects. All before/after digests match.
The primary record's digest-checked builder reference materializes the complete
measured JSON byte-exactly. Ten focused test identities/outcomes match twice
and in the wheel, normalizing only the documented relocated JUnit prefix.

The new recipe twice, `process:check`/`prepare:check` (542 tests, formatting,
Ruff and strict types), staff checks, Task discovery, unchanged helper preflight
and actual wheel pass. Earlier assessment/composition/colour/render/codec/sample/
placement records match exactly. Synthetic preparation's nine cases/24 pages
and all 38 installed writer faults match the earlier reading itemwise, including
geometry/resources/order/roles/RGB and exits/results/visibility/source identity/
reaping. No product source, renderer/helper/cache/native settings/version,
manifest/lock, preparation or frozen experiment changed. Evidence retention
follows completed measurement; no running subject was edited.

F remains live in its original open task-owned jj change. ICC/device calibration,
arbitrary font fidelity, other blend/composite mechanisms and actual runtime
font/profile/config/dlopen/native-extension provenance remain unfinished before
accepted import. Type3 resolution remains explicitly unavailable; this test-owned
construction truth grants no arbitrary runtime composition pass. All original
saved-project/ownership/checkpoint/status/resume, matched packet/native/global
refresh, Q1–Q3 actions/replay/inspection/acknowledgement, exact export, installed
writer/isolation/migration, six actual/resource/truth and B reuse/compatibility
checks stay with F. Complex real numerical truth and human visual acceptance
remain separate. This advances milestone 1 and completes neither that milestone
nor the finite public handoff.

## Actual runtime loader observation — 2026-10-13

The test-owned `tests/runtime_loader.py` instrument separates PID-bound
UUID/path image events, opaque loader messages and original application
diagnostics. Missing observation, foreign PID, malformed UUID/path or conflicting
UUIDs fail. Fifteen tests observed the unimplemented boundary fail before the
implementation. Loader events establish neither initialization state nor complete
resource provenance. Apple's [logging documentation](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/LoggingDynamicLoaderEvents.html)
and current [logLoad source](https://github.com/apple-oss-distributions/dyld/blob/main/dyld/Loader.cpp)
support the selected mechanism; the event grammar is characterized on this Mac,
not asserted as a stable ABI or the installed dyld's exact source revision.

The native construction declares a post-launch `dlopen` leaf returning 73 and
a separate wrong leaf returning 74. The executable's static link inventory
contains neither leaf. Actual wrong-leaf and disabled-logging controls fail
before the positive observation; foreign-PID, missing-event and wrong-UUID
controls fail separately. Each observed child is launched directly and reaped.
These are test children, not installed finite writers or OS-signal evidence.

An ordinary one-page PDF declares a 72 × 36-point MediaBox with a red left half
and white right half. The pre-output 300 × 150 RGB truth checks every actual Cairo
channel exactly. The Python workload performs PNG roundtrip, sRGB identity-profile
smoke and pikepdf roundtrip, importing actual imaging/profile/font/math native
extensions. The identity-profile smoke is no independent ICC conversion oracle;
font-extension import supplies no arbitrary-font raster truth.

| Observed operation | UUID/path events | Other loader messages | Non-system disk images |
| --- | ---: | ---: | ---: |
| Wrong post-launch leaf | 82 | 0 | 2 |
| Expected post-launch leaf | 82 | 0 | 2 |
| Actual Cairo rendering | 585 | 157 | 40 |
| Python codec/profile/PDF workload | 567 | 155 | 21 |

Every non-system event UUID matches its native-architecture disk `LC_UUID` and
the disk bytes remain unchanged across the frozen reading. A UUID is not a
cryptographic digest of mapped memory. System events retain reported mapped
UUIDs and actual macOS build; absent shared-cache disk files are not hashed.
The delayed-state messages remain visible, without declaring those images active
or initialized. All inherited environment values are bound by an opaque digest
without exposing credentials; only the child logging override is changed.
This is not complete environment/configuration-resource discovery.

Working private recipes use existing parents and unused destinations:

```sh
task --exit-code process:runtime-fixtures ARTIFACTS='/tmp/unused native fixtures'
task --exit-code process:runtime-acceptance \
  FIXTURES='/tmp/unused native fixtures' ARTIFACTS='/tmp/unused loader observation'
```

Frozen [runtime A](baseline-runtime-loader/runtime-a.json) and
[runtime B](baseline-runtime-loader/runtime-b.json) agree itemwise on every event
UUID/disk digest, opaque message, diagnostic, construction result and imported
source digest. Actual PIDs/paths/environment fingerprints remain in the raw
records. The independently installed wheel has the same meanings, with actual
module paths outside the checkout. Deployment paths and PIDs are not compared
as semantic equality; A/B environment fingerprints also agree.

[Primary verification](baseline-runtime-loader/verification.json.gz) retains
9,792 enumerated subjects and command/test/preparation outcomes;
[primary subjects](baseline-runtime-loader/primary-subjects.json.gz) and
[pinned builder](baseline-runtime-loader/build-verification.json.gz) are
digest-checked references that reconstruct the full measured JSON byte-exactly.
[Installed verification](baseline-runtime-loader/installed-verification.json.gz)
retains 2,251 subjects and outside-checkout paths; the builder retains 7,450
actual Hatchling 1.27.0 subjects. Before/after digests match for these enumerated
inputs. Complete font/profile/configuration reads remain undiscovered, so this
is explicitly partial runtime provenance. The
[truth](baseline-runtime-loader/truth.json) and
[fixture ZIP](baseline-runtime-loader/fixtures.zip) retain every source/native/
header-dependency/analytic-truth byte from the actual run. No saved project,
viewer inspection or accepted import is delivered.

Both new recipes, `process:check`/`prepare:check` (557 tests, formatting, Ruff,
strict types), staff checks, Task discovery, unchanged helper preflight and the
actual wheel pass. Fifteen unit identities/outcomes agree twice and in the wheel.
Synthetic preparation's nine cases/24 pages and 38 installed writer faults match
the earlier reading itemwise, including complete geometry/resources/order/roles/
RGB and exact exits/results/visibility/source identity/reaping. Production code,
renderer/helper/cache settings, dependency versions, preparation and experiments
are unchanged. Evidence retention follows completed measurement.

F remains live in its original open jj change. This advances actual loader/dlopen/
extension evidence without completing milestone 1. Required font/profile/config/
environment discovery and integration into the product operation remain, alongside
independent ICC/device-colour/arbitrary-font/other composition truth. All original
saved-project/ownership/checkpoint/resume, packets/native/global refresh, Q1–Q3
actions/replay/inspection/acknowledgement, exact export, installed faults/isolation/
migration, six actual/resource/truth and B reuse/compatibility checks remain here.

## Explicit-profile native RGB and constructed ICC fidelity — 2026-10-13

`bookscan.profiles.display` supplies a separate private native-view interpretation:
unit-range ICC RGB (including Indexed and DefaultRGB) is decoded, clipped and
quantized to 8-bit channels, then converted into the exact target ICC bytes
supplied by its caller. The result retains both profile SHA-256 identities,
Pillow 12.3.0/LittleCMS 2.19, relative-colorimetric intent 1 and NOOPTIMIZE 256.
There is no implicit monitor profile, black-point compensation, accepted-pixel
mutation or device-colour fallback. Original packed samples/exact decoded channels
remain separate; raw colour-key alpha is retained without applying external masks,
soft-mask Matte, painting, clipping or blending. Nonunit ranges, unprofiled CMYK,
missing/malformed/incompatible profiles and incompatible conversion versions remain
explicitly unavailable. Complete project/packet integration remains unfinished.

Seventeen focused tests cover actual power-curve conversion, Decode-before-profile,
Indexed palette/native-grid identity, raw-key alpha, source immutability, malformed
headers/tables, unsupported ranges, selected owner cancellation and exact packed
row lengths. The missing module initially failed fourteen tests. Two later RED
cases caught incomplete/extra source bytes becoming plausible RGB; the conversion
boundary now rejects them before invoking the CMM. Callback cancellation stays
outside native-error handlers and is checked between row operations. An indivisible
native transform can finish before the next cancellation check.

The independent construction builds ICC v4 matrix/TRC bytes directly from fixed
fields and power-curve parameters; neither Pillow nor Poppler constructs the
source oracle. Both explicit input/target matrices match, so conversion into the
linear target has the independently known response `round(v²/255)`, with a
one-code bound for the CMM's intermediate/final quantization. Original native
channels remain 5×1. The ordinary PDF places them into a 72×36-point frame:
300×150 full RGB. The source profile's squared channels and ICC's published sRGB
transfer equations independently define Cairo's expected complete buffers.

The draft two-code Cairo envelope lacks a complete independent target-profile
matrix/precision proof. Its explanation assumed column discrepancies smaller
than independently established; correcting the earlier omission of the inverse
matrix norm did not discharge that assumption. The envelope remains a diagnostic
hypothesis only. Cairo comparison/control outputs are recorded, but numerical
ICC composition fidelity is **unavailable** until that exact target-profile proof
is established. The explicit linear-target native conversion has independently
matched matrices and known power response; its bounded conversion claim is separate.
This is no arbitrary-profile, real-page, display-calibration or complete-composite
accuracy promise. The sources are [ICC.1:2010](https://www.color.org/specification/ICC1v43_2010-12.pdf),
[ICC sRGB equations](https://registry.color.org/rgb-registry/srgb), the exact
[Pillow 12.3.0 API](https://raw.githubusercontent.com/python-pillow/Pillow/12.3.0/src/PIL/ImageCms.py)
and selected Poppler 26.10.0 colour path. The fetched Pillow source equals the
installed source byte-exactly.

Five constructed cases pass explicit linear-target native conversion and satisfy
the diagnostic Cairo envelope: power ramp, reverse Decode, Indexed palette,
swapped source primaries and DefaultRGB. A sixth deliberately malformed ICC
profile stays unavailable, without any composition-fidelity credit. Six actual
source mutations—ignored curve, wrong primary matrix, omitted Decode, wrong
palette, dropped DefaultRGB and erased colour—fail the diagnostic pixel envelope.
Unrelated page pixels and image dimensions remain correct; original raw channels
also remain correct except in the deliberately erased-source case. Blanks,
duplicates and all eight source positions are retained. Deleting the original
still permits exact sample rereads and duplicate conversion from its verified
snapshot; no saved review project or human inspection is inferred.

```sh
task --exit-code process:profile-acceptance ARTIFACTS='/tmp/unused profile evidence'
```

The corrected frozen reading is `/private/tmp/bookscan-k63-profile-work/evidence-v2`.
[Profile A](baseline-profiles/profile-a.json),
[profile B](baseline-profiles/profile-b.json) and the actual outside-checkout wheel
agree on every construction, complete-buffer digest, conversion identity,
unavailable outcome, native control and source-loss meaning. The
[pre-output truth](baseline-profiles/truth.json) and
[fixture ZIP](baseline-profiles/fixtures.zip) preserve every measured profile,
source snapshot, bound, PNG and wrong-source byte. These are construction assets,
not a saved project or viewer observation.

[Primary verification](baseline-profiles/verification.json.gz) retains 9,180
subjects, command outcomes and full itemwise comparisons; its digest-checked
[subject table](baseline-profiles/primary-subjects.json.gz) and
[builder record](baseline-profiles/build-verification.json.gz) reconstruct the
complete measured JSON byte-exactly. The pinned Hatchling 1.27.0 builder freezes
7,451 actual subjects; [installed verification](baseline-profiles/installed-verification.json.gz)
freezes 2,243 and records actual imported modules outside this checkout. All
before/after digests match. Complete external font/profile/configuration resource
discovery remains unverified, separately from these enumerated read subjects.

The new recipe twice, `process:check`/`prepare:check` (574 tests, formatting,
Ruff and strict types), staff checks, Task discovery, unchanged helper preflight
and actual wheel pass. Seventeen focused identities/outcomes match twice and in
the wheel, normalizing only the documented relocated JUnit prefix. Synthetic
preparation's nine cases/24 pages and all 38 installed writer faults match prior
complete meanings itemwise. No preceding product module, renderer/helper/cache/
native setting/version, manifest/lock, preparation or frozen experiment changed.
Retention follows completed measurement, with no subject edited during a run.

F remains live in its original open task-owned jj change. This advances supported
explicit-profile native interpretation and diagnostic ICC composition evidence
without completing milestone 1. Independent Cairo target-profile matrix/precision
proof, arbitrary-font/general composition, real calibrated colour truth, complete
runtime resource discovery and actual import preflight integration remain. The target profile must be retained by the later packet/
asset owner; no implicit target, complete source-native composition or monitor
calibration was introduced. All original saved-project/OS ownership/checkpoints/
resume, matched packets/actual native/global refresh, Q1–Q3 receipts/actions/
replay/inspection/acknowledgement, exact export, installed faults/isolation/
migration, six real/resource/truth and B reuse/compatibility checks remain here.

## Exact constructed ICC matrices and native diagnostics — 2026-10-13

`task process:matrix-acceptance ARTIFACTS=/tmp/NEW-DIRECTORY` reads the actual
hand-encoded matrix and power-curve bytes with a separate test-owned instrument.
It uses exact rational inversion and the matrix/curve equations in
[ICC.1:2010, Annex F.3](https://www.color.org/specification/ICC1v43_2010-12.pdf).
The reader accepts only the declared v4.3 display RGB/XYZ, D50 media/PCS-white,
power-1/power-2 profile subset. Unsupported transforms, curves, overlapping/truncated
tables, negative XYZ and singular matrices fail explicitly. This reader does not
validate arbitrary ICC profiles or reproduce a colour-management module.

Literal nonsymmetric inverse, exchanged-pivot and unequal coupled-matrix tests
contest mistakes hidden by matched-matrix cancellation. The independent coupled
construction has source columns equal to a 3:1 mix of the target's red/green
columns. Its input `(51,153,204)` and power-2 curves give exact unquantized linear
target values `(3/25,7/25,16/25)`. The actual product-native conversion observes
`(31,71,163)` and records signed rational code deviations `(2/5,-2/5,-1/5)`.
These deviations are diagnostic: no tolerance is inferred from their size.
Missing-mixing and missing-power subjects fail literal analytic truth before
native observations; actual conversions of those altered profiles change output
while retained raw samples and native grids match. Matched and swapped constructions
are separate named readings. The exact inverse norm belongs to the explicit
constructed target; it supplies no matrix bound for Cairo's unidentified target.

The [A reading](baseline-matrices/matrix-a.json),
[B reading](baseline-matrices/matrix-b.json) and actual
[installed-wheel reading](baseline-matrices/installed-verification.json.gz)
agree itemwise, including every rational value, native diagnostic, control,
profile/source digest, unavailable outcome and source-loss meaning. The
[pre-output declaration](baseline-matrices/truth.json) and
[fixture ZIP](baseline-matrices/fixtures.zip) retain exact profile, wrong-profile,
truth and five-occurrence source-snapshot bytes. They are construction assets,
not a saved project or viewer observation.

[Primary verification](baseline-matrices/verification.json.gz), its digest-checked
[subject table](baseline-matrices/primary-subjects.json.gz) and
[builder record](baseline-matrices/build-verification.json.gz) reconstruct the
complete measured JSON byte-exactly. All 9,191 primary, 2,242 installed and 7,451
actual Hatchling 1.27.0 builder subjects remain unchanged before/after. The
[verification tools](baseline-matrices/verification-tools.zip) retain the exact
freezers and observed RED records; [command records](baseline-matrices/command-records.zip)
retain raw command/JUnit outputs. Complete runtime font/profile/configuration/
environment discovery remains unverified.

Thirty-one focused identities/outcomes agree twice and in the outside-checkout
wheel, normalizing only the documented relocated JUnit prefix. The first 29
unimplemented failures and a later observed non-D50-white failure contest the
instrument before its native readings. New recipe twice, `process:check`/
`prepare:check` (605 tests, format/Ruff/strict types), staff checks, Task discovery,
unchanged helper preflight and wheel-source checks pass. Synthetic preparation's
nine cases/24 pages and all 38 installed writer fault meanings match earlier
complete evidence itemwise. No preceding product module, renderer/helper/cache/
native setting, manifest/lock, preparation or frozen experiment changed. Retention
and this prose follow completed measurement; no running subject was edited.

F remains live/unsealed. Exact constructed matrix truth advances milestone 1;
native conversion precision, Cairo target-profile identity/matrix/precision,
arbitrary-font/other composition truth, real/device calibration and complete
runtime resources bound to import remain unfinished. All original saved-project,
OS ownership/checkpoint/resume, packets/native/global refresh, Q1–Q3 actions/
replay/inspection/acknowledgement, acknowledged export, installed faults/isolation/
migration, six real/resource/truth and B reuse/compatibility obligations remain.

These retained records are the corrected frozen v2 reading at
`/private/tmp/bookscan-k63-matrix-work/evidence-v2`. The first reading and initial
retention are diagnostic only, preserved in that temporary work directory.
Exact runner inspection identified a missing direct check between the declared
profile bytes and native result identities. Every construction and altered-source
case now checks the extracted input profile bytes and both actual Conversion
digests, and records the returned identities. Complete A/B/installed records and
all subject/check/preparation outcomes agree again after a fresh frozen reading.
No product, profile/native setting or rational truth/tolerance changed; the same
precision/Cairo/resource and complete-F gaps remain.

## Actual Cairo target observation — 2026-10-13

This advances the missing target-profile identity question. It supplies **serialized
metadata evidence**, not CMM precision or complete ICC composition fidelity. F
and milestone 1 remain live; no baseline public command or saved project exists.

The test-owned `tests/native/target_observer.c` interposes only this direct test
child's `cmsCreate_sRGBProfile` and `cmsCreateTransform` calls on the characterized
macOS arm64 host. It passes through the original calls and serializes their actual
profile handles, retaining PID/sequence/handle/format/intent/flags/CMM-version events.
The current SDK lacks `dyld-interposing.h`; the source emits Apple's documented
pair section directly. Actual interception and disabled-child controls verify this
host's mechanism; no arm64e/ptrauth or other-host portability is claimed. Official
[LittleCMS 2.19 declarations](https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19/include/lcms2.h)
and [Apple interposition source](https://raw.githubusercontent.com/apple-oss-distributions/dyld/main/include/mach-o/dyld-interposing.h)
are cited at the C call/section sites. The linked Homebrew library is LittleCMS
2.19.1, reporting encoded CMM version 2190 and pkg-config version 2.19.

Before rendering, the ordinary static PDF construction declares one RGB sample
`[51,153,204]`, embedded in the existing hand-encoded power-two profile, placed
as a 36-point square on a 72×36-point page. The actual product snapshot/sample
reader verifies its exact native/profile bytes. The unchanged product renderer
supplies 300×150 RGB: image on the left, white on the right. This comparison
checks observer pass-through only; neither the baseline nor an uninjected Cairo
render supplies independent colour fidelity truth.

Two actual sRGB profile creations precede eight total events. XYZ display
transforms use the first; the selected image transforms at sequences 7 and 8
use the second. They have input formats 262169 and 25 (the latter a component-only
format), output 262169, relative-colorimetric intent 1 and flags 8448
(NOOPTIMIZE | BLACKPOINTCOMPENSATION). Each selected transform is bound to its
actual earlier creation handle. Equal serialized metadata does not make distinct
handles interchangeable. Source input tags match the constructed profile; every
raw input/target profile and event is retained.

The independently read serialized target RGB→XYZ matrix is:

```text
[ 893/2048      25239/65536  9375/65536  ]
[ 14581/65536   46983/65536  993/16384   ]
[ 57/4096      6361/65536   46787/65536 ]
```

The exact rational inverse and all parametric type-3 curve coefficients, D50
white, adaptation/chromaticity and text tags appear in the complete semantic
record. Its serialized inverse infinity norm is
`5670996672512/1081779929801`. These rational calculations describe the saved
s15Fixed16 coefficients only. Serialization may quantize in-memory values;
the actual CMM pipeline, adaptation/black-point stages, arithmetic/LUT/curve
precision and output quantization are still unbounded. This norm is **not** a
justification for the earlier diagnostic Cairo colour envelope. No tolerance
is widened or chosen from the observed RGB.

All declared controls fail before the successful record is credited:

| Control | Observed rejection / unchanged independent part |
| --- | --- |
| Actual uninjected child | No capture sequence; decoded RGB and dimensions equal the injected and product render. |
| Foreign PID | Actual events reject a different expected PID; their bytes/RGB/geometry stay unchanged. |
| Wrong input profile | Actual captured input tags reject the independently supplied power-one profile; native samples/profile/RGB remain unchanged. |
| Wrong target handle | A copy of the actual sequence-7 event is changed to an unobserved handle. Binding fails with `Unrelated target handle`; all captured profile bytes, process identity, RGB and geometry stay unchanged. This is an altered-evidence control, not a different native transform execution. |

Working recipes (existing parent, unused directories):

```sh
task --exit-code process:target-fixtures ARTIFACTS='/existing parent/new fixtures'
task --exit-code process:target-acceptance \
  FIXTURES='/existing parent/new fixtures' ARTIFACTS='/existing parent/new reading'
```

The corrected frozen v2 reading is at
`/private/tmp/bookscan-k63-target-final/evidence-v2`. Its first reading stopped
in a copied preparation comparison helper on a missing import; that attempt stays
diagnostic in the temporary directory. No running subject was edited. The complete
reading restarted after the fix, without product/renderer/profile/cache changes.
Earlier temporary work directories were absent; their missing boundary script
was not claimed rerun. A new explicit helper cache was built with the existing
source/settings and verified without modification during this reading.

The final 9,338 primary, 2,250 outside-checkout installed and 7,451 actual
Hatchling 1.27.0 builder subjects have equal before/after digests. All 23 focused
case identities/outcomes, each semantic event, exact matrix/curve/tag, input/output
digest, limitation and four control outcomes agree itemwise across A/B and the
wheel. Raw PID/handle/date/path/dyld records are retained separately; semantic
comparison excludes these volatile observation identities. Installed JUnit
comparison normalizes only the documented `runners`/`tests` module prefix.
Every observed non-system mapped native image was already in the frozen subject
set and matches its recorded disk digest/UUID. OS shared-cache UUIDs are labelled
without claiming system disk hashes or in-memory identity. Full font/profile/
config/environment resource discovery remains unverified.

New build/check recipes, process:check and prepare:check (628 tests, format,
Ruff, strict types), staff checks, Task discovery, unchanged-cache preflight and
wheel-source integrity pass. Preparation's nine cases/24 pages and all 38 actual
installed writer fault outcomes agree itemwise across A/B and prior retained
meanings. These remain preparation regressions, not finite-writer acceptance.

Retained complete evidence:

- [target A](baseline-target-observation/target-a.json), [target B](baseline-target-observation/target-b.json), [pre-output construction/build truth](baseline-target-observation/truth.json).
- [Frozen verification](baseline-target-observation/verification.json.gz), [primary subjects](baseline-target-observation/primary-subjects.json.gz), [actual installed wheel](baseline-target-observation/installed-verification.json.gz), [actual builder](baseline-target-observation/build-verification.json.gz).
- [Exact profile/event/PNG/snapshot/observer/wheel bytes](baseline-target-observation/fixtures.zip), [measurement scripts and copied runners](baseline-target-observation/verification-tools.zip), [commands/JUnit/preparation records](baseline-target-observation/command-records.zip).

Factored references reconstruct the complete measured verification JSON byte-for-
byte, and every ZIP member matches its measured source byte. These archives are
construction/observation evidence, never a saved review project or viewer receipt.

Next finish independent CMM precision/complete ICC composition fidelity and actual
font/profile/config/environment discovery tied to import, plus remaining
arbitrary-font composition controls. Then couple snapshot/geometry/render/native/
assessment into complete saved assets with OS ownership/checkpoints/status/resume.
All original packets/actual-viewer/global-refresh, authentic actions/replay/Q1–Q3/
scoped acknowledgement, exact export/report/no-clobber, installed faults/isolation/
six-real-case/resource/compatibility/B-reuse obligations remain in F. Real/device
calibration, unsupported ICC Gray/CMYK/ranges, native-codec/complex-real truth and
Type3-resolution outcomes stay precisely unverified. No metadata reading or passed
native conversion supplies any missing required fidelity proof.

## Actual in-memory profile observations

The separate test-owned `profile_memory_observer.c` image reuses the earlier
observer source unchanged. On its buffer-writing `cmsSaveProfileToMem` call,
after the size query and before that write, it reads the same profile handle's
public XYZ tags, one parametric curve segment and complete estimated curve tables.
The [LittleCMS 2.19 declarations](https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19/include/lcms2.h)
and [curve accessors](https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19/src/cmsgamma.c)
are cited beside the native access and retained with the measurement tools.
No private transform structure is inspected. Finite floating values are written
as hexadecimal and read as exact binary rationals; original raw text is retained.

All eight actual events bind fourteen input/target role records. The non-RGB XYZ
input profiles remain explicitly unsupported by this RGB memory reader. Both
selected image-input formats and every sRGB target have complete XYZ/curve data,
including all 4,096 estimated-table entries per curve. The selected targets match
their actual earlier creation's in-memory data. Constructed input matrix/curve
parameters agree with their serialized values. The actual target matrix and
type-4 LittleCMS curve parameters differ from their s15Fixed16 serialization;
the complete exact differences are retained. Equal serialized profiles therefore
do not establish equal numeric in-memory values. These observations supply no
evaluation-error or conversion-fidelity bound.

The estimated tables belong to the observed profile curves; no claim is made
that the final transform evaluates those tables. Its final stages, input/output
formatters, curve reversal/evaluation, BPC/adaptation, arithmetic and quantization
still require independent proof. CMM precision, complete Cairo ICC fidelity,
device calibration and complete font/profile/config/environment discovery remain
unverified before accepted import. No prior diagnostic colour envelope becomes
a pass, and no renderer/profile/native setting or tolerance changes.

Five memory controls fail: actual uninjected child, foreign PID, missing memory
record, wrong handle, and one altered actual image target's matrix coefficient.
The last is rejected specifically because its memory differs from that same
handle's earlier observed creation. Actual ICC bytes, rendered RGB and geometry
remain unchanged. The earlier observer's four controls are also rerun unchanged.
All injected/uninjected/product RGB buffers and dimensions agree exactly.

Working recipes, requiring existing parents and unused destinations:

```sh
task --exit-code process:memory-fixtures ARTIFACTS='/existing parent/new fixtures'
task --exit-code process:memory-acceptance \
  FIXTURES='/existing parent/new fixtures' ARTIFACTS='/existing parent/new reading'
```

The frozen reading at `/private/tmp/bookscan-k63-memory-work/evidence` preserves
9,358 primary, 2,255 actual outside-checkout installed and 7,451 pinned-builder
subjects unchanged before/after. Every binary rational, table entry, serialized
record/difference and control agrees itemwise across A/B and the actual wheel;
raw PID/handle/date/path/loader identities remain separately retained. The 25 new
focused identities and 23 earlier observer identities agree with only JUnit's
documented `runners`/`tests` relocation normalized. New recipes, 653-test format/
lint/strict-type checks, staff/Task/helper/wheel checks pass. Preparation's nine
cases/24 pages/38 actual installed writer faults agree itemwise twice and with
their prior complete meanings. These remain preparation regressions.

Evidence:

- [Memory A](baseline-profile-memory/memory-a.json.gz), [memory B](baseline-profile-memory/memory-b.json.gz), [pre-reading build/subject declaration](baseline-profile-memory/truth.json).
- [Frozen verification](baseline-profile-memory/verification.json.gz), [primary subjects](baseline-profile-memory/primary-subjects.json.gz), [actual wheel reading](baseline-profile-memory/installed-verification.json.gz), [actual builder](baseline-profile-memory/build-verification.json.gz).
- [Fixture/observer/wheel bytes](baseline-profile-memory/fixtures.zip), [A captures](baseline-profile-memory/native-a-captures.zip), [B captures](baseline-profile-memory/native-b-captures.zip), [installed captures](baseline-profile-memory/installed-captures.zip).
- [Tools and native source](baseline-profile-memory/verification-tools.zip), [commands/JUnit/preparation](baseline-profile-memory/command-records.zip), [exact report reconstruction](baseline-profile-memory/report-index.json).

Factored references reconstruct the full measured verification byte-exactly.
Capture archives omit duplicate `report.json` members whose exact bytes reconstruct
from the named gzip record and JSON keys in report-index. Every remaining ZIP
member matches its measured source. An initial combined capture ZIP exceeded jj's
existing new-file size guard; the lossless per-reading archives fit it without
changing repository settings. This retention change follows completed measurement.

F remains live in its original unsealed change. The complete CMM/fidelity/resource
proof, arbitrary-font composition and all original saved-project/ownership/
checkpoint/status/resume, packet/viewer/global-refresh, actions/replay/Q1–Q3/ack,
export/report/no-clobber, installed faults/isolation/migration, six real packets,
compatible predecessor and B-reuse obligations remain unfinished in this owner.

## Actual RGB transform formatters — 2026-10-13

The preceding profile-memory evidence does not describe the complete CMM
pipeline. This continuation resolves the narrower input/output formatter gap
with a separate test-owned observer. It obtains the **current formatter function
pointers from the actual completed transform**, through the public
`_cmsGetTransformFormatters16` accessor. It registers no plugin and assumes no
private transform layout. `_cmsGetTransformFlags` returns **original flags**;
that value is retained without inferring final optimization state.
The previous memory and serialized observers are included byte-exactly. Their
old hook array remains ordinary data; this test image alone owns its two active
pass-through interpose entries. Product rendering, profiles, settings and helper
cache semantics remain unchanged.

The independent integer construction is declared before output in
[truth.json](baseline-transform-formatters/truth.json):

- Input: enumerate `v=0..255`, with distinct channel permutations
  `(v,255-v,73*v mod 256)`. Expect each component to expand exactly to `v*257`.
- Output: enumerate `v=0..65535`, with channel permutations
  `(v,65535-v,73*v mod 65536)`. Expect nearest conversion `(v+128)//257`.
- Every channel sees every code; the odd multiplier makes the third permutation
  bijective. These are declared per-channel permutations, **not all RGB tuples**.
  Pointer advances, unchanged input words and surrounding byte/word guards are
  checked by the native observer before retaining bytes.
- For that observed scalar rounding map, maximum error is exactly `128/257`
  in 8-bit code units, or `128/65535` normalized. This is an output-formatter
  bound only; it includes no intermediate CMM curve/matrix/LUT/BPC error.

Actual image-transform events 7 and 8 have input formats `262169` and `25`,
output format `262169`, original flags `8448` and encoded CMM version `2190`.
Both bound formatters produce identical complete code records:
input SHA-256 `ab51d27c4ff12d0b7146ac2e0b13658507b82e9378099f0be4972d8a23c06e35`;
output SHA-256 `c645e58ee92ce923fb70f7273f63fb48110a82801564d40527028f30c30b50b8`.
`dladdr` observations bind both pointers to the actual process's LittleCMS
2.19.1 image, with mapped/disk UUID
`C82F20BF-AEC5-32FA-85DC-CA4EEFA06424` and unchanged file digest.
These observations supply no cryptographic memory hash or general ABI claim.
Official selected declarations/source URLs sit beside the native accessor calls.

The actual disabled child and six altered-evidence controls reject: foreign PID,
wrong transform handle, missing formatter, altered channel, altered rounding and
unobserved module. Actual captured profiles, ordinary geometry and RGB remain
unchanged by those alterations. Injected/uninjected actual rendering has exact
RGB equality. The preceding five memory controls and four serialized controls
also pass through their separate actual child reruns. Intermediate evaluator/
curve reversal, BPC/adaptation and floating arithmetic precision remain unverified;
this evidence does not promote the earlier diagnostic colour envelope to a pass.

The frozen reading at `/private/tmp/bookscan-k63-formatter-work/evidence`
compares all formatter code records/module identities, profile-memory values/full
tables, serialized deltas, controls and explicit limitations itemwise across A/B
and an actual outside-checkout wheel. Raw PID/handle/path/date/dyld records remain
separate and retained; only JUnit location prefixes are normalized. All 9,401
primary, 7,451 pinned-builder and 2,260 installed read subjects remain unchanged.
All 67 focused test identities/outcomes agree; full format/lint/strict-type checks
and 672 tests pass. New formatter fixture/acceptance recipes, earlier memory/
serialized native recipes through the same runner, helper preflight, staff checks,
Task discovery and wheel checks pass. Both synthetic preparation runs preserve
nine cases/24 pages and all 38 actual installed writer faults itemwise, also
matching their previously complete meanings. No real preparation subject changed.

Durable evidence preserves the full measured records byte-exactly:
[verification](baseline-transform-formatters/verification.json.gz),
[primary subjects](baseline-transform-formatters/primary-subjects.json.gz),
[builder verification](baseline-transform-formatters/build-verification.json.gz),
[installed verification](baseline-transform-formatters/installed-verification.json.gz),
[installed subjects](baseline-transform-formatters/installed-subjects.json.gz),
[reading A](baseline-transform-formatters/formatter-a.json.gz),
[reading B](baseline-transform-formatters/formatter-b.json.gz),
[fixtures and wheel](baseline-transform-formatters/fixtures.zip),
[command/JUnit archive index](baseline-transform-formatters/archive-index.json) and
[exact instruments/source](baseline-transform-formatters/verification-tools.zip).
[Archive index](baseline-transform-formatters/archive-index.json) enumerates every
raw capture, profile, code table, module observation, wrong-subject control,
snapshot, PNG and script across the factored capture ZIPs, with original measured
paths. [Report index](baseline-transform-formatters/report-index.json) reconstructs
every nested report from retained JSON keys with exact digests. Factoring respects
the unchanged jj file-size guard without dropping or rewriting measured bytes.

F remains live on its same unsealed jj change. Next resolve the intermediate
CMM evaluator/pipeline and independent curve/matrix/BPC/arithmetic bounds using
actual profile-memory values. Complete ICC composition fidelity, arbitrary-font
construction and actual font/profile/config/environment resource binding remain
required before accepted import. Real calibration and unsupported Gray/CMYK/
ranges/native codecs/complex-real/Type3 detail remain precisely unavailable.
Saved assets/ownership/checkpoints, permanent finite public readers/packets,
ordinary-viewer identity/native/global refresh, Q1–Q3 actions/replay/scoped
inspection/acknowledgement, exact export, installed writer faults/isolation,
compatibility, six real resource/native/truth packets and five browser reuse
properties still await their coupled delivery. No project, finite public handoff,
CMM/fidelity result, product review, retirement or sealed milestone is inferred.


## Actual final transform pipeline — bounded construction evidence

This continuation supplies test-only native stage/binding evidence. The complete
finite reviewer remains live; no saved project, public review workflow, final
ICC precision/fidelity result or real-page calibration follows.

The exported `_cmsDefaultICCintents` hook failed with exit 111: the actual built-in
intent table calls its private static counterpart. The failed source is retained
as a diagnostic. The working observer uses the exact official LittleCMS 2.19.1
internal header on this arm64 binary, with actual disassembly checking the Lut
load/free at 0x70 and the transform worker at 0x08. It cross-checks available
public format/flags/formatter/context/worker/user-data getters before reading
Lut, captures the actual worker's module identity, and compares the real pipeline
with `cmsDoTransform`. This deliberately bounded private test ABI is neither a
portable accessor nor a product dependency. A separately compiled wrong-offset
child exits 110 before reading Lut. Native code, profiles and render settings
are unchanged.

Both actual RGB transforms (262169 and 25 -> 262169, flags 8448) have three final
stages: gamma-2 source curves, a combined near-identity matrix without an offset,
and negative type-4 sRGB output curves. Original/reversed curve parameters match
actual profile memory exactly. Exact rational T^-1*S independently predicts
the matrix; the predeclared construction coefficient envelope is
64*2^-53*max(1,||T^-1||*||S||)*max(1,cond(T)), restricted to cond(T)<=16.
The observed maximum coefficient difference is approximately 2.623e-16, within
the 1.953e-13 envelope. This checks these observed coefficients, not arbitrary
ICC arithmetic, curve/libm precision, or full conversion fidelity. Requested BPC
and before/after adaptation getter values are creation metadata, not an observed
intent callback or a proof of their arithmetic.

Each transform's 256 declared RGB triples (v,255-v,73*v%256) agrees through
Eval16 followed by the independently verified (word+128)//257 packer and the
real completed transform. These are binding/consistency probes, not independent
colour truth or the full RGB cube. All eleven foreign/missing/changed matrix/
curve/probe/module/disassembly/native-ABI/disabled controls reject. Injected and
uninjected RGB/geometry remain identical. The worker binds to mapped/disk UUID
C82F20BF-AEC5-32FA-85DC-CA4EEFA06424 and library SHA-256
faf9c8f2322a2bb47d04d3077a79cc7103fba68a186697cf91e5f6ef467d1b77.

Frozen measurement at `/private/tmp/bookscan-k63-pipeline-work/evidence` retains
9,458 primary, 7,451 pinned-builder and 2,267 actual outside-checkout installed
subjects unchanged. All 94 focused case identities/outcomes and complete final
stage/matrix/profile/probe/control semantics agree itemwise A/B/wheel, together
with preceding formatter/memory/serialized records. Full checks pass 699 tests,
format/lint/strict types, staff/Task/helper/wheel recipes. Preparation's nine
synthetic cases/24 pages and all 38 actual installed writer faults agree twice
and with prior evidence. No preparation/experiment/source setting changes.

Read [verification](baseline-transform-pipeline/verification.json.gz),
[primary subjects](baseline-transform-pipeline/primary-subjects.json.gz),
[installed verification](baseline-transform-pipeline/installed-verification.json.gz),
[installed subjects](baseline-transform-pipeline/installed-subjects.json.gz),
[builder verification](baseline-transform-pipeline/build-verification.json.gz),
[reading A](baseline-transform-pipeline/pipeline-a.json.gz),
[reading B](baseline-transform-pipeline/pipeline-b.json.gz), and
[declared fixture truth](baseline-transform-pipeline/truth.json).
[Archive index](baseline-transform-pipeline/archive-index.json) names each retained
ZIP/member/source; [report index](baseline-transform-pipeline/report-index.json)
reconstructs every nested report and factored command stdout byte-exactly. A
`$gzip` object names a file/hash reference: expand recursively, then restore
verification's named subject/build references. Factoring meets the unchanged jj
file guard without changing any measured byte. Retained native/ICC/PNG/fixture/
wheel/command/tools records preserve their exact inputs and outputs.

Next establish the actual final evaluator and intermediate source-curve, matrix,
reversed-curve, saturation/floating/quantization bounds against independent truth.
Final stage data and packer consistency cannot supply those bounds. Complete
ICC composition, arbitrary-font construction and font/profile/config/environment
resource bindings remain required before accepted import. Unsupported ICC spaces/
ranges, complex real/native-codec/Type3 detail and real calibration remain named
unavailable. Then deliver saved assets/OS ownership/checkpoints/source-loss resume,
immutable packets/actual ordinary-viewer 1:1 and global refresh, Q1–Q3 actions/
replay/scoped inspection/selection-union acknowledgement, exact acknowledged
export/report/no-clobber, installed writer faults/isolation/migration, six real
resource/native/truth packets and all five browser reuse properties. No partial
retirement, sealed milestone, tree cut or parent closure is inferred.

## Actual source gamma-2 evaluator — finite input domain

The separate test-child observer calls `cmsEvalToneCurveFloat` on the three actual
source curves in each of the renderer's two selected final transforms. The prior
observer first verifies the installed 2.19.1 arm64 transform ABI, final pipeline,
profile-memory stage data and transform probes. The new observer uses public stage
and curve accessors; it introduces no private stage/curve layout, plugins, alternate
profiles or rendering settings. `dladdr` identifies the public evaluator's native
module, whose path is tied to the observed loader UUID and unchanged disk digest.
All preceding product/native/profile/cache settings and sources remain unchanged.

The independent oracle decodes and rounds IEEE binary32 with exact rational and
integer arithmetic, including nearest-even ties and subnormal boundaries. For
every `v` from 0 through 65535 it requires `x = round32(v/65535)` and
`y = round32(x²)` bit-for-bit on each actual source curve. Expected values use no
LittleCMS, host floating operations, `pow` or renderer output. Before native
comparison the absolute source-domain bound is declared as
`3 × 2⁻²⁵ + 2⁻⁵⁰`: on `[0,1]`, input and output rounding each cost at most
`2⁻²⁵`, while squaring propagates input error by at most `2e + e²`.
The pinned implementation decision is cited at the observer/oracle call sites:
[LittleCMS 2.19.1 curve evaluation](https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsgamma.c).

Both transforms and all three channels agree for every declared input/output
bit pair. The largest exact normalized error relative to `(v/65535)²` is
`3092604377/36027697515724800`, approximately `8.584 × 10⁻⁸`, below the declared
`100663297/1125899906842624`. Eight controls reject foreign PID, wrong transform,
wrong channel, altered input bit, altered output bit, omitted code, foreign module
and disabled observation. Injected and uninjected RGB/geometry remain exact.
This checks the actual public curve evaluator over this finite domain. Arbitrary
float inputs, actual pipeline stage dispatch, intermediate matrix arithmetic,
reversed-target evaluation, saturation, BPC/adaptation and complete CMM/ICC
composition fidelity remain unfinished; this result cannot substitute for them.

The frozen reading retains 9,508 primary, 7,451 pinned-builder and 2,272 actual
outside-checkout installed subjects, unchanged before/after. All 126 focused test
identities/outcomes and complete curve/stage/probe/control records agree itemwise
across A/B and the installed wheel. Format/lint/strict types and 731 tests pass;
working new fixture/acceptance recipes and affected helper/staff/Task/wheel checks
pass. The complete preceding pipeline semantics also match their retained record
itemwise, with its prior frozen subjects checked before edits and after this
reading. Preparation's nine cases/24 pages and all 38 actual installed writer
fault outcomes match both reruns and earlier full meanings.

Exact raw evidence is retained in [the file index](baseline-source-gamma/file-index.json.gz):
ordered SHA-256 chunk references reconstruct every indexed source file from the
`raw-*.zip` archives. Identical chunks are stored once; every raw byte, original
file name/path and file mode remains recorded. The archive reader temporarily adds
owner-read access only for this run's intentionally unreadable preparation-fault
outputs, restoring their exact original modes immediately. This is post-measurement
retention, with no measurement input/output bytes edited. The index also retains
actual fixtures/controls/profiles/headers/disassembly/PNG/wheel, command/JUnit/
preparation records, observer sources and exact measurement/audit scripts.

- [Pre-output truth and build subjects](baseline-source-gamma/truth.json)
- [Complete A record](baseline-source-gamma/gamma-a.json.gz) and [B record](baseline-source-gamma/gamma-b.json.gz)
- [Frozen measurement](baseline-source-gamma/verification.json.gz), [actual installed wheel](baseline-source-gamma/installed-verification.json.gz) and [prior-boundary comparison](baseline-source-gamma/supplement.json.gz)

Large JSON subrecords use digest-checked `$gzip` references to sibling files.
Recursive expansion restores their complete original JSON bytes exactly. The
file index independently reconstructs every raw measurement file, including
command stdout and all nested prior reports. No repository file-size setting or
measured input is changed. Reproduce with `process:gamma-fixtures` and
`process:gamma-acceptance`, passing unused `ARTIFACTS` and the built `FIXTURES`.
The precise original commands and frozen subjects are retained in the measurement.
No saved review project, public finite workflow, complete import-fidelity verdict
or milestone retirement follows; the same finite implementation owner stays live.


## Actual source/matrix stage dispatch and arithmetic

The new observer runs only in a separate native test child. It preserves every
previous observer through inclusion, then checks the exact official 2.19.1 stage
header against this installed arm64 binary's constructor, public getters and
native evaluator/LUT-loop disassembly. Runtime public getters cross-check type,
channels, data and next pointers before the new private `EvalPtr` is called.
The actual floating control register is zero: nearest-even, no flush-to-zero.
The observed source and matrix evaluator addresses equal the real mapped module
base plus native `EvaluateCurves` and `EvaluateMatrix` offsets `0xdb68` and `0xdf00`.
Module UUID and disk SHA-256 bind those addresses to the selected actual PID,
transform and retained final pipeline. This is a test-only private ABI; no product
API, alternate profile, optimizer, native setting or previous source changed.
The source decision is cited beside the non-obvious calls and verifier:
[LittleCMS 2.19.1 stages](https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmslut.c)
and [exact internal header](https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/lcms2_internal.h).

Before native comparison, declare 65,536 triples `(v,65535-v,73*v mod 65536)`.
Every channel sees every normalized word once; this is not all RGB combinations.
Call the actual retained source-stage pointer, then the actual retained matrix-
stage pointer on its output. Independently require bit-exact rational nearest-even
`round32(round32(word/65535)^2)` source results. Compare matrix results to exact
rational row-major dot products of the previously profile-checked coefficients
and represented source outputs. For row L1 norm <=2, no offset and binary32 inputs
in `[0,1]`, the predeclared arithmetic bound is `2^-24 + 2^-48`: at most six
binary64 operations cost <=`2*gamma6` plus negligible underflow, below `2^-48`;
binary32 output rounding on `[-2,2]` adds <=`2^-24`. It includes this binary's
fused multiply/add accumulation. The bound is independent of native results.

Both selected transforms match all source-stage bits and satisfy the matrix
bound on every declared vector. Exact maximum matrix error is
`18222049939003298785933/316912650057057350374175801344`, about `5.749865e-8`,
below `16777217/281474976710656`, about `5.960465e-8`. Fifteen controls reject
foreign PID/transform/Lut/stage/symbol/module/floating-mode, altered input/source
bits, erased matrix channel, nonfinite output, omitted vector, wrong native ABI/
disassembly and disabled observation. The actual wrong-offset child exits 150
before this extension's private stage read/EvalPtr call. Altered stage evidence
leaves the preceding gamma/profile/pipeline checks green. Injected/uninjected
complete RGB and geometry agree exactly.

This verifies isolated actual source/matrix stage pointers over the declared
finite vectors. The installed LUT-loop instructions are checked, but its dynamic
end-to-end traversal is not observed here. Reversed target-curve evaluation,
saturation/remaining floating/quantization arithmetic, BPC/adaptation composition
and complete ICC fidelity remain unfinished. Arbitrary-font constructions and
actual font/profile/config/environment resource binding remain required. Complex
real/native-codec/Type3 detail and unsupported ICC spaces/ranges retain their
precise unavailable outcomes. No complete import or saved-review handoff follows.

The frozen readings have 9,541 primary, 7,451 pinned-builder and 2,279 actual
outside-checkout installed subjects, unchanged before/after. All 159 focused
identities/outcomes, complete two-stage vector tables, native symbol bindings,
profile/stage/probe comparisons and fifteen controls agree itemwise A/B/wheel.
Full format/lint/strict types and 764 tests pass; new working stage recipes and
affected staff/helper/Task/wheel checks pass. Preceding complete gamma and pipeline/
formatter/memory/serialized semantics are checked separately. Preparation's nine
cases/24 pages and all 38 actual installed writer faults agree twice and with
retained full meanings. No preparation, experiment or prior native/profile/cache/
source/manifest/lock bytes change. All original finite-owner milestones remain.

- [Pre-output truth/build subjects](baseline-stage-evaluation/truth.json)
- [Complete A](baseline-stage-evaluation/stage-a.json.gz) and [B](baseline-stage-evaluation/stage-b.json.gz)
- [Frozen verification](baseline-stage-evaluation/verification.json.gz), [installed wheel](baseline-stage-evaluation/installed-verification.json.gz) and [prior-boundary comparison](baseline-stage-evaluation/supplement.json.gz)
- [Exact raw file/chunk index](baseline-stage-evaluation/file-index.json.gz)

Digest-bound recursive `$gzip` references restore complete report JSON exactly.
The raw index concatenates ordered SHA-256 chunks from `raw-*.zip`, retaining
all complete raw files, names/paths/modes, native sources/headers/disassembly,
profile/PNG/fixture/wheel/command/JUnit/preparation records and exact instruments.
Only derived intentionally unreadable preparation-fault outputs temporarily gain
owner-read access during post-measurement retention; their exact modes are restored.
No running input or measurement byte changes. Reproduce with
`process:stage-fixtures` and `process:stage-acceptance`, supplying unused
`ARTIFACTS` and the built `FIXTURES`. The same original F change stays unsealed;
there is no product/leaf/parent retirement or browser/geometry acceptance.

## Actual full-LUT transform probes (2026-10-13)

A separate test child now traces 256 synchronous `cmsDoTransform` probes through
both actual renderer-owned RGB8 transforms. Predeclared inputs are
`(v,255-v,73*v mod 256)`, covering every 8-bit code in each channel once, not the
RGB cube. Exact native address/module UUID/digest binding identifies `CachedXFORM`
at offset `0x1a918`, then the actual LUT16 source-curve/matrix/reversed-target
stage chain. Each probe records one LUT evaluation and three ordered stage calls.
Original callbacks receive unchanged arguments; complete pipeline/stage structs
restore byte-exactly, and the repeated uninstrumented output agrees exactly.
Injected/uninjected render pixels and dimensions also remain exact.

The first strict dispatcher reading rejected an incorrect `PrecalculatedXFORM`
assumption. Official 2.19.1 source and installed flags (`0x2100`, omitting NOCACHE)
explain `CachedXFORM`; the failed reader/capture remains diagnostic evidence.
These inputs avoid the initial all-zero cache and actual counters verify every
probe call. No cache-hit behavior or traversal of every renderer pixel is claimed.

Source-stage values are independently correctly rounded on this declared domain.
Matrix outputs stay within the previously declared rational arithmetic bound
`2^-24+2^-48`; maximum error is
`427235384249380499915571/10141204801825835211973625643008`.
Complete stage links, final 16-bit word domain, byte formatting and restored
outputs are checked. A low-bit word mutation can retain its formatted byte and
is not a saturation oracle: reversed-target/remaining floating/saturation/BPC/
adaptation/complete ICC fidelity remain unverified. Font and actual import
resource binding, saved projects and the complete finite public handoff remain
unfinished. All six real packets, ordinary-viewer refresh/navigation, installed
checkpoint/packet/export lifecycle and B compatibility/reuse obligations stay live.

Frozen A/B/outside-checkout installed-wheel measurements agree itemwise on every
probe, all 20 controls and all 200 focused unit identities. Actual wrong-ABI and
bypassed-stage children exit 160 and 162. Linked source/matrix alterations fail
independent arithmetic while preceding gamma/profile/stage evidence passes.
Primary/build/installed measurements freeze 9,581/7,451/2,287 read subjects.
Full formatting/lint/strict types and 805 tests pass; new working recipes, helper,
staff and prior gamma/pipeline checks pass. Preparation repeats agree on all nine
cases/24 pages and all 38 actual writer faults, including prior full semantics.
Measured code/native/library/profile/cache/fixture/instrument bytes stay unchanged.

- [Pre-output truth/build subjects](baseline-lut-traversal/truth.json)
- [Complete A](baseline-lut-traversal/traversal-a.json.gz) and [B](baseline-lut-traversal/traversal-b.json.gz)
- [Frozen verification](baseline-lut-traversal/verification.json.gz), [installed wheel](baseline-lut-traversal/installed-verification.json.gz) and [prior-boundary comparison](baseline-lut-traversal/supplement.json.gz)
- [Exact raw file/chunk index](baseline-lut-traversal/file-index.json.gz)

Digest-bound recursive `$gzip` references reconstruct complete JSON. The ordered
raw chunk index retains complete names/paths/modes and native/profile/PNG/fixture/
wheel/command/JUnit/preparation/instrument bytes, including diagnostic failures.
Reproduce with `process:traversal-fixtures` and `process:traversal-acceptance`,
using unused `ARTIFACTS` and the built `FIXTURES`. The original F task/jj change
remains live and unsealed; this bounded result supplies no product retirement or
source-fidelity/geometry/browser acceptance.


## Native float-to-word saturation (2026-10-13)

A separate test-owned rational verifier now checks the final words of both
actual renderer-owned RGB8 transforms on the existing 256 full-LUT probe
triples. It binds the entire installed arm64 `LUTeval16` instruction body and
its referenced literal-pool values (65535 and -32767) to the same native library
whose PID, address, UUID, profile, stage and floating-mode identities the
unchanged preceding readers verify. The binder deliberately supports this
exact binary, not another build or architecture. The source decision remains
cited beside the oracle: [LittleCMS 2.19.1 LUT evaluation](https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmslut.c)
and [fast-floor implementation](https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/lcms2_internal.h).

Before comparison, the declared domain is finite binary32 [-2,2]. Expected
words use integer/rational binary64 nearest-even operations for scaling, adding
one half, clamping and the fast-floor magic addition; no host float or second
CMM supplies truth. Fast floor quantizes to 16 fractional bits. The literal
constructed boundary `0x3700007f` produces word 1 rather than ideal floor 0;
this is a unit construction, not an observed renderer boundary. All actual
probe outputs here agree with both algorithms. Signed zeros, subnormals,
clamps, half/boundary values and unsupported-domain controls are tested.

Both fresh readings check all 1,536 words, with bit-identical per-transform
records and distinct observed input formats 262169/25. Four actual-table
wrong-word controls preserve byte formatting, restored output and every earlier
source/matrix/stage check, then fail the independent word oracle. Five native
instruction/literal controls fail too; all 20 preceding traversal controls pass
in each reading. The 8,457 enumerated project/fixture/native/interpreter/stdlib/
venv/cache/tool subjects stay unchanged before/after; the Task wrapper disables
bytecode writes. Full format/lint/strict types and all 842 test identities pass
twice. Preparation's nine cases and 38 actual writer fault cases agree itemwise
twice; staff checks pass. Earlier product, native observer, reader, experiment,
manifest and lock bytes remain unchanged.

- [Complete frozen A/B measurement](baseline-lut-saturation/measurement.json.gz)
- [Complete regression readings](baseline-lut-saturation/regression.json.gz)
- [Exact raw source/file/chunk index](baseline-lut-saturation/file-index.json.gz)

The index retains complete raw native/probe/control/profile/vector/PNG/preparation/
JUnit/command/instrument/source bytes with exact paths and modes. Its ordered
chunks reconstruct files from `raw-NNN.zip`; archives stay below the existing
repository size limit. The earlier fixture archive is referenced under its
unchanged digest boundary. Intentionally unreadable test-owned fault outputs
only gain owner-read access during retention, then regain their exact mode.
Reproduce with `task process:saturation-acceptance FIXTURES=TRAVERSAL-FIXTURES
ARTIFACTS=NEW-READING`. This reruns actual transforms, not just archived values.

The target curve's float output remains observed input to this oracle; reversed-
target accuracy, remaining composition/BPC/adaptation arithmetic, actual renderer
pixel/cache-hit traversal, complete ICC fidelity and runtime font/profile/config/
environment binding remain unverified. Complex real/Type3/native-codec truth
and real calibration retain their precise missing oracles. No saved project or
public finite reviewer is delivered. The same F owner/jj change stays live and
unsealed for the complete assets/checkpoints/ownership/resume, packets/receipt
actions/inspection/acknowledgement, exact export and six-case/reuse acceptance.

## Reversed-sRGB finite accuracy (2026-10-13)

A separate test-owned rational verifier checks every reversed-target value in
both actual renderer-owned RGB8 transforms. The unchanged preceding readers
bind the PID, module/ABI, exact final in-memory negative type-4 curve parameters,
ordered source/matrix/target stages, formatters, probe traversal and restoration.
They continue to report their own narrower meanings. No prior reader, native
observer, product module, library, profile or fixture is changed.

Before comparison, the domain was finite binary32 [-1/16,2], excluding a 2^-40
band around the mathematical branch threshold. All actual probes lie in this
admitted domain. Integer bisection on an 80-bit dyadic grid brackets the ideal
12/5 threshold with a fifth root of `(a*d+b)^12`, and the inverse power output
with a twelfth root of `R^5`. The linear output is exact rational `R/c`, including
negative values. Coefficients are the complete retained in-memory binary64
values, independently checked against the source/profile/pipeline evidence;
serialized ICC tag precision is not substituted. The non-obvious formula is
cited beside its implementation to [LittleCMS 2.19.1](https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsgamma.c).

The predeclared absolute ceiling is `2^-24 + 2^-44` (about 5.96047e-8): half the
largest binary32 spacing on this output range plus a conservative elementary
arithmetic allowance. Each power-branch comparison explicitly adds `2^-48` for
idealizing the actual gamma and reciprocal exponent. For the admitted positive
range, exponent displacement is below 2^-54, absolute log below 9, root at most
2, exponential perturbation below 2 and `a>9/10`; displacement is therefore
below `40*2^-54 < 2^-48`. The root interval and parameter allowance remain
separate in every value's record. This observes finite accuracy; it assumes no
global native libm error theorem and proves no exact-nearest-even transcendental
result. Oracle branch labels are mathematical truth, not separately observed
native branches. Arbitrary native threshold accuracy is not certified.

The credited A/B readings each check all 1,536 values: 45 linear and 723 power
values per transform, with formats 262169 and 25. Every input/output bit,
interval, branch and error record agrees itemwise. Maximum error including the
parameter allowance is about 4.58859e-8, below the declared ceiling. Four
wrong-target controls change an interior target float and its consistent
saturation word while retaining final/restored bytes; source/matrix/traversal/
saturation/formatter checks remain green and the new target oracle rejects.
All preceding traversal and native saturation controls also pass. A diagnostic
first reading retains its original instruments; it is not credited after the
reported allowance/control improvements. Both new absent-module and missing-
allowance tests were seen to fail before implementation; all 34 focused tests pass.

The credited measurement's 8,475 enumerated subjects remain byte-identical,
including native tools, interpreter, stdlib, venv/caches, project and prior
fixtures. Full formatting/lint/strict typing and all 876 test identities pass
twice; synthetic preparation's nine cases and 38 installed writer fault cases
agree itemwise twice; staff checks pass. No measured subject is edited during a
run. Actual real preparation subjects are unchanged and earn no new copying claim.

- [Complete credited measurement and reconstruction manifest](baseline-reversed-target/measurement-index.json)
- [Complete regression readings and reconstruction manifest](baseline-reversed-target/regression-index.json)
- [Exact raw file/chunk index](baseline-reversed-target/file-index.json.gz)

For each report manifest, verify/concatenate the ordered `parts`, check the
compressed digest, gzip-decompress once, then check the decoded digest/length.
The raw index independently reconstructs every original command/JUnit/native/
profile/vector/PNG/preparation/instrument/source byte and mode. Deduplicated
archives and report parts stay below the existing 1-MiB new-file limit; no
repository setting is relaxed. Previous exact traversal/saturation fixture
indices are referenced with their unchanged digests. Reproduce actual fresh
native A/B readings with `task process:reversed-acceptance
FIXTURES=TRAVERSAL-FIXTURES ARTIFACTS=NEW-READING`.

Source/matrix/reversed-target/word checks have separate bounded domains. Composing
them into an independent complete ICC/composition error envelope remains work;
these records do not establish that envelope, actual renderer pixel/cache-hit
traversal, arbitrary fonts, runtime font/profile/config/environment binding,
complex real/Type3/native-codec truth or real calibration. F remains live and
unsealed: complete saved assets/checkpoints/OS ownership/resume, immutable packets/
actual native refresh, receipts/replay/Q1–Q3 review/acknowledgement, exact export/
report/publication, installed faults/isolation/migration, six real cases and B's
five reuse properties are all still required. No finite reviewer or saved project
is delivered by this arithmetic continuation.

## Controlled source-to-byte composition envelope

The next bounded arithmetic reading connects the preceding independently checked
source, matrix, reversed-target, word and formatter stages. It computes ideal
`(code/255)^2`, the exact retained row-major matrix, and rational inverse intervals
with ideal exponent 12/5 directly from source codes. Observed intermediate
floats are not inputs to this new final-byte oracle. All earlier parameter,
native dispatch, linked-stage, arithmetic and restoration readers run unchanged.

Before fresh outputs, the normalized ceiling was declared as
`13*(2*source_bound+matrix_bound)+target_bound+129/65535`, or approximately
0.5027510821 of an output byte. Source normalization and square rounding use
`3*2^-25+2^-50`; a matrix row has L1 norm at most 2. The fixed inverse's linear
slope is 12.92 and its power slope is below 13, independently bounded with exact
integer roots. The whole propagated matrix interval must fit [-1/16,2] and one
admitted branch. Seam crossings fail explicitly: rounded coefficients need not
make the branches continuous. The preceding target allowance includes exponent
idealization and covers root-endpoint width. Clipping cannot enlarge error;
word and byte conversion contribute conservative 1-word and 128-word allowances.

Fresh actual readings in `/private/tmp/bookscan-k63-envelope-work/credited`
check both renderer-owned input formats on every declared triple: 1,536 channel
values per reading. A/B complete per-value identities and records agree. Maximum
byte error is approximately 0.4999319299, below the predeclared ceiling. Four
altered-final-byte controls keep source/matrix/target/word arithmetic unchanged
and fail this independent output oracle. They also violate the deterministic
formatter, which cannot remain valid with a different byte for the same word;
no stronger isolation is claimed. All previous native controls still pass.

All 23 new test cases were seen failing with the module absent, then passing.
One narrow fresh-context reviewer independently challenged the mathematical
composition and reported no issues; its default Python lacked pytest, so only
the parent locked test runs supply executable results. This spends F's single
leaf-wide allowance. The actual reading freezes 8,502 subjects; regression
freezes 8,503 including its instrument. All subjects stay unchanged through
format/lint/strict types, 899 unit identities/outcomes twice, nine preparation
cases and 38 installed writer outcomes twice, and staff checks. Wrong unit/case
controls fail before itemwise agreement is credited.

- [Complete credited A/B report and reconstruction manifest](baseline-composed-envelope/measurement-index.json)
- [Complete regression report and reconstruction manifest](baseline-composed-envelope/regression-index.json)
- [Exact raw files, instruments and source chunk index](baseline-composed-envelope/file-index.json.gz)

Concatenate each report's ordered digest-checked compressed parts, decompress
once, and verify decoded digest/length. The raw index reconstructs bytes and
modes of all retained files; its unchanged prior indices retain the older exact
traversal/saturation/reversed-target evidence. Parts remain below the existing
1-MiB new-file limit. Reproduce with `task process:composed-acceptance
FIXTURES=TRAVERSAL-FIXTURES ARTIFACTS=NEW-READING`.

This conditional envelope covers the bound controlled pipeline probes. Actual
renderer pixels/cache hits, arbitrary ICC profiles or fonts, runtime font/profile/
configuration/environment resources, complete page composition and real calibration
remain unverified. Complex real/native-codec/Type3 truth retains its precise
missing oracle. F stays live/unsealed: complete saved assets/OS ownership/
checkpoints/resume, immutable native packets/global refresh, Q1–Q3 actions/replay/
inspection/selection-union acknowledgement, exact export/report/publication,
installed faults/isolation/migration, six real resource/native/truth packets,
compatible predecessor and all five B reuse properties remain required. No
finite reviewer or accepted saved project is delivered by this continuation.


## Actual controlled renderer conversions and cache reuse

A separate test-owned pass-through observer captures real conversion calls during
an opaque, unfiltered, grid-aligned 516x2 RGB image render. It preserves all earlier
observers by inclusion. Actual input/output formatters, LUT and ordered three-stage
callbacks receive unchanged arguments; complete native structs restore exactly.
The complete installed arm64 worker/formatter instruction bodies and actual
PID/module/address/transform/LUT/format identities are bound. The official
[LittleCMS 2.19.1 cached worker](https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsxform.c)
copies its zero cache seed at each call; the reader checks that reset independently.

Fresh A/B readings each observe two 516-pixel RGB8 calls, each with 257 misses,
259 hits and 771 stage calls. Repeated samples and the initial black samples
exercise cache reuse. Every miss meets the preceding rational source/matrix/
reversed-target/saturation/ideal-byte criteria; hits return their exact cached
words and formatted bytes. Actual inputs match the complete decoded source roster,
and outputs match every pixel in the 516x2 PNG. Plain/injected/disabled renders
remain exact. Both created transform formats retain the earlier construction-
probe checks; format 262169 has no observed real conversion call in this fixture.
Only actual format 25 use is credited.

All 16 controls fail on wrong arithmetic/words/bytes/cache paths/order, complete
source binding, an erased rendered feature, wrong canvas, disabled observation,
worker/cache instructions and actual wrong ABI. A wrong-output-record native
child keeps its rendered PNG and earlier readers exact while the new reader
rejects. Actual wrong ABI exits 180 and is reaped. The first complete reading is
diagnostic after adding the image-binding controls; its exact instruments are
retained separately. All 57 new unit cases were observed failing before their
methods existed, following correction of the initial header-test constructor.

Credited A/B freezes 8,537 enumerated subjects; regression freezes 8,538 including
its instrument. Every subject stays unchanged. Format/lint/strict types and all
956 unit identities/outcomes agree twice; nine preparation cases and38 installed
writer cases agree itemwise, with wrong-case controls rejected; staff checks pass.

- [Complete credited A/B report](baseline-renderer-calls/measurement-index.json)
- [Complete regression report](baseline-renderer-calls/regression-index.json)
- [Exact raw source/file/chunk index](baseline-renderer-calls/file-index.json.gz)

Verify and concatenate ordered compressed report parts, decompress once, then
check decoded length/digest. The raw index reconstructs retained bytes/modes and
references unchanged preceding archive indices. New files remain below 1 MiB.
Reproduce with `task process:pixel-fixtures FIXTURES=TRAVERSAL-FIXTURES
ARTIFACTS=NEW-PIXEL-FIXTURES`, then `task process:pixel-acceptance
FIXTURES=NEW-PIXEL-FIXTURES ARTIFACTS=NEW-READING`.

This verifies the declared controlled image's conversion/cache/PNG association.
General composition, arbitrary ICC/font truth, actual font/profile/configuration/
environment binding, complex real/Type3/native-codec truth and real calibration
remain unresolved. F stays live/unsealed for saved assets/OS ownership/checkpoints/
resume, immutable native packets/global refresh, Q1–Q3 actions/replay/inspection/
selection-union acknowledgement, exact export/report/publication, installed fault/
isolation/migration acceptance, six real packets, compatible predecessor and B's
five reuse properties. No finite reviewer or accepted saved project is delivered.


The original wrong-output/disabled controls omitted saving their loader-result
objects. Fresh supplementary readings retain their complete actual PID/command/
loader/module/environment-hash/reaped records with unchanged code/native subjects.
Every wrong-control pixel/stage/gamma value agrees itemwise with the original
reading; earlier readers pass, the new reader rejects, and original/supplemental
PNG bytes remain exact. The raw index includes these separate readings and their
frozen instrument. The original missing loader objects remain unavailable.


## Local kernel writer ownership (partial finite implementation)

The packaged `bookscan.ownership` mechanism now provisions a permanent local
`writer.lock` once in a new operation-owned directory. Acquisition requires the
expected directory/lock device/inode and opaque token; it never creates a missing
lock or derives expected identity from the entry it is about to trust. macOS
F_GETPATH supplies canonical parent/case spelling. Held directory and lock
identities/content are checked before operations and commits; replacement,
symlink/hardlink/FIFO, corrupt content, foreign identities and closed owners fail
INVALID_PROJECT/3. The complete private header/reader still must persist/verify
these identities. Portable project relocation and complete compatibility fixtures
are not claimed by this internal mechanism.

Use `Writer.acquire` as caller-held ownership, verifying it in shared operations
rather than reacquiring. Actual same-process second acquisition returns busy/4.
Closing an independently opened descriptor leaves exclusion intact. Context exit
closes owned references without deleting the inode or issuing a shared LOCK_UN;
failed context entry also closes them. Unsupported native locking maps to5.
The actual Mac kernel checks accompany the [Python3.12 fcntl API](https://docs.python.org/3.12/library/fcntl.html)
and [Apple flock contract](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/flock.2.html);
POSIX process-scoped lockf is not credited as equivalent.

Frozen verification on macOS27.0.1 arm64/build26A434, local /dev/disk3s1, uses two
source and two independently installed-wheel readings of every lifecycle case.
Raw PID/parent/command/path/inode/token observations are retained. A competing
operation and actual case/symlink-parent aliases return busy. Every contention
attempt is nonblocking. Ordinary release keeps the lock file bytes/inode.

| Actual owner condition | Observed outcome |
| --- | --- |
| Normal release | Wait result0; immediate new ownership; stable lock inode/content. |
| Deliberate process-lock substitute | Unrelated-descriptor close loses exclusion; actual wrong-mechanism control rejected. |
| SIGINT/SIGTERM during actual native sleep | Wait result130/143; unchanged product child executor terminates/reaps child; immediate reacquisition. |
| SIGKILL during child executor | Writer reaped with wait result-9; immediate single reacquisition while native child still alive. |
| SIGKILL with deliberately open exec descriptors | Same immediate reacquisition while native child remains alive; CLOEXEC prevents ownership inheritance even with close_fds=False. |

The installed-wheel product file has the same exact bytes as the source module,
with its actual imported path beneath the independent environment. These are
internal mechanism tests. Public finite commands and complete saved checkpoints,
packet/publication and export signal policies remain unimplemented.

All9,119 frozen subjects remain unchanged throughout four native readings and
two full regressions. Format/lint/strict types and979 unit identities/outcomes
agree twice. Nine synthetic preparation cases and38 installed preparation writer
outcomes agree itemwise; deliberately wrong native-row/unit/case controls reject;
coordinate staff checks pass. Earlier native/renderer/preparation/real input and
frozen experiment subjects remain unchanged. Diagnostic driver failures are
retained separately and supply no credited reading.

Reproduce the native mechanism with `task process:ownership-acceptance
ARTIFACTS=NEW`. This recipe uses real writer/native processes and immutable
expected identities; no public product test mode or browser feature exists.

- [Complete measurement reconstruction manifest](baseline-ownership/measurement-index.json)
- [Exact raw outputs, sources, wheel and instruments](baseline-ownership/file-index.json.gz)

Verify each ordered manifest part, concatenate and gzip-decompress once, then
verify decoded length/digest. The raw index binds every retained original byte
and mode; previous acceptance archive indices retain their original digests.
All new files stay below the existing1-MiB limit. Full finite delivery still
requires resource/font/composition fidelity completion, durable saved assets/
headers/checkpoints/resume, actual immutable packets/native refresh, receipt
review/replay/Q1–Q3/scoped acknowledgement, exact image-only export/report and
installed fault/isolation/migration/six-case/compatibility/B reuse acceptance.
F stays live/unsealed, with no product or geometry/preparation visual acceptance.

## Named render resources and child environment — 2026-10-14

The internal renderer can now carry a `ResourceBinding`: explicit caller-named
required/optional files, their logical/resolved paths and byte/device/inode
identities, captured child environment and working-directory identity. Checks
before/after rendering and after advisory assessment reject changed supplied
subjects. The child receives a copied environment and explicit working directory;
provenance contains an environment digest, never its values. Assessment preserves
a detached copy per occurrence. This is uncommitted import machinery; no finite
create/status/export, checkpoint or private-format capability is delivered here.

The scope is deliberately recorded in every binding: caller-named files do not
establish complete runtime font/profile/config discovery or actual-use identity.
Before/after checks also cannot exclude a transient change restored during a
native read. Complete default font/config/cache/directory/CMap/profile/native
inventory and independent whole-glyph/full-page composition truth remain required.
`runtime_resources_verified` stays false. Missing complex-real/native-codec/Type3
truth and real calibration retain their earlier meanings.

Construction declares two controlled native font/config scopes before outputs:
Helvetica and Courier candidates, unembedded Helvetica PDF text and a vector
rectangle, 600×150 RGB frame, exact captured test-environment value and changed-
resource exit5. This is a resource-selection/guard test with **whole-glyph fidelity
unavailable**; it supplies no font raster tolerance or preservation verdict.
Actual Fontconfig2.18.3 match logs name the respective external font files. The
[official Fontconfig reference](https://fontconfig.pages.freedesktop.org/fontconfig/fontconfig-user.html)
documents the config selection and match diagnostics; the actual command output
and unchanged external-font bytes bind this host's observations.

Credited source A/B and separately installed-wheel A/B agree itemwise: bound-A
rendering survives an ambient config-B change and matches direct-A RGB; direct-B
RGB differs. Mutating a bound config produces DEPENDENCY_UNAVAILABLE/5 without
returning usable pixels. Real child environment isolation and reaped native PIDs
are recorded. All9746 enumerated read subjects remain byte-identical throughout
measurement; complete wheel/installed product members match source.

Both full format/lint/strict-type/unit readings pass with999 matching test
identities/outcomes. Nine synthetic preparation cases and38 installed writer
fault cases agree itemwise with wrong-case/identity controls rejected. Two actual
six-case lock lifecycles and fourteen independent full-page render cases with
ten wrong-subject controls agree; staff-check passes. Previous preparation,
real-input and experiment bytes remain unchanged. This resource step gives no
new public finite-writer, complete saved-project or real-case fidelity result.

The [measurement index](baseline-resources/measurement-index.json) binds the
complete frozen report. The [raw file index](baseline-resources/file-index.json.gz)
identifies digest-bound chunks for exact instruments, diagnostics, source/config/
cache/font/PNG/PDF subjects, wheel/installed product, native records and regression
outputs. Earlier failing/diagnostic runs are retained separately from credited
readings. Original F and every incomplete public/native/packet/export/compatibility/
six-case/B obligation remain live under baseline-finite-k63.

### Candidate directory binding (k63 continuation, 2026-10-14)

The internal resource guard now binds explicitly supplied directory trees as
well as named files/environment/cwd. It records every directory entry, including
hidden files and symlinked external subtrees, regular-file bytes/native identity,
directory native identity/membership and optional absent roots. Added/deleted
candidates, replaced roots/nested directories/files and retargeted aliases prevent
returning a raster. Unreadable entries, cycles and special files fail dependency5;
no partial inventory is returned. Access-time changes from reads are ignored;
owner RuntimeError/KeyboardInterrupt cancellation remains unchanged. These are
before/after checks, not proof against a transient mutation restored during use.

Primary Python3.12 directory semantics were verified against
[the official pathlib reference](https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.iterdir).
The first native diagnostic showed cached fc-list results after a same-second
font addition. Test-owned cache rebuilding uses the verified2.18.3
[fc-cache implementation](https://github.com/fontconfig/fontconfig/blob/2.18.3/fc-cache/fc-cache.c)
and is explicitly confined to the output-owned candidate/cache control. These
sources and uncredited diagnostic/TDD failures are retained with the reading.

New working recipe: `task process:directory-resource-acceptance FIXTURES=DIR
ARTIFACTS=NEW`. Fixtures use the existing `process:resource-fixtures`; no public
resource/test mode is introduced. The actual controlled Fontconfig scope starts
with Helvetica.ttc and, after the deliberately added Courier.ttc and forced
test-cache rebuild, lists both native files. The directory guard rejects that
changed scope with DEPENDENCY_UNAVAILABLE/5; the deliberately wrong file-only
guard still returns pixels. This control proves candidate-set change detection,
not changed glyph pixels, glyph fidelity or complete native-use discovery. Stable
directory-guarded RGB equals the direct/configured-A and earlier file-guarded RGB.

Four credited readings (source A/B and separately installed-wheel A/B) agree
itemwise on both candidate sets, all literal controls and native RGB identities.
Complete wheel/product bytes equal source and installed product. All10306
enumerated read subjects stay byte-identical: tracked contracts/code/evidence,
previous frozen subjects, both Python installations, actual font/config/cache
inputs, native tools/libraries and measurement instruments. Changed candidates
and their caches are declared output controls; original fixtures stay frozen.
Both prepare:check readings pass format/lint/strict types and the same1024 unit
identities/outcomes. Synthetic preparation's nine cases/38 actual writer outcomes
match itemwise; changed unit/native-hash/preparation-case controls reject. Both
six-case ownership lifecycles and fourteen-case/ten-control independent renderer
readings agree; geometry:staff-check passes. No earlier real-source/preparation/
experiment bytes change, so no new affected real preparation comparison is claimed.

Exact instruments/commands/raw reports/PDF/PNG/config/cache/font subjects, wheel,
installed product and graph coverage are retained in
[baseline-resource-directories](baseline-resource-directories/measurement-index.json),
with a digest-bound file/chunk index. Measurement starts after edits stop; later
bookkeeping appends are checked against the exact measured prefixes.

`runtime_resources_verified` remains false. The caller still supplies discovery
scope; complete actual default Fontconfig config/font/cache/directory, Poppler
CMap/profile/native/environment inventory and actual-use binding are unfinished,
as are independent arbitrary-font/glyph/full-page composition truth and real
calibration. This mechanism is internal packaged import progress, not a completed
saved project or installed finite workflow. Original F remains live/unsealed;
all immutable store/public packet/action/replay/ack/export/installed fault/
isolation/migration/six-case/resource/predecessor/B-reuse requirements remain.

### Directory evidence audit correction (2026-10-14)

The earlier final audit was not read-only: after checking the retained raw files,
it rewrote its own retained `coverage-fallback.json` input with current archive
digests. Retaining that file inside those archives makes the archive-digest records
circular. An actual old-instrument run exited 0 while changing that input; its next
run exited 1 at exact raw-file comparison. Those historical fallback records are
not current archive-integrity evidence. The original archives and instrument
remain intact, and the fallback was restored from independently digest-checked
archived bytes after preserving the divergent diagnostic.

[The corrected instrument](baseline-resource-directories/audit-preserving.py)
keeps derived current coverage in its result, never overwriting a retained input.
`task --exit-code process:directory-evidence-check` runs the complete historical
directory measurement and current-host byte/mode audit. It requires the original
host subjects and `/private/tmp/bookscan-k63-directory-work`; it neither rebuilds
missing subjects nor remeasures native outcomes. Its result is written separately
to `/private/tmp/bookscan-k63-audit-repair/preserving-audit.json`. As in the original
instrument, deliberate mode-000 preparation fixtures temporarily gain owner-read
permission, restored immediately; this is a byte/mode-preserving audit, not a claim
of zero transient permission changes.

Two corrected runs have preserved 11,435 enumerated byte/mode/native-identity/
symlink records and produced identical per-item results, while the old mutating
instrument fails its retry. The final Taskfile-based frozen rerun and its exact
diagnostic/instrument/result bytes are retained separately in
[the audit repair index](baseline-resource-directories/audit-repair-index.json).
That output generation is separate from the retained measurement inputs; do not
repeat the earlier retain/audit loop or place an archive's own digest inside it.
The original resource measurement, frozen native readings and protected product/
preparation/experiment bytes are independently checked rather than replaced.

The historical Taskfile bytes are also retained unchanged. The current Taskfile
adds exactly the named audit recipe above; the corrected audit verifies those
original bytes plus that exact addition, rejecting an altered recipe control.
Task/acceptance bookkeeping remains checked against measured prefixes. These
declared later changes are distinct from the original frozen native measurement.
All other retained live raw files must match their historical bytes and modes.

This corrects evidence handling only. `runtime_resources_verified` remains false;
actual runtime resource discovery/composition truth, saved projects, finite packets/
actions/export and all original acceptance/B-reuse work remain unfinished. No
product or complete finite handoff follows from this audit repair.

### Evidence closure after bookkeeping appends (2026-10-14)

The original repair boundary, archives, input map and instruments remain unchanged.
Its exact-current-log check correctly rejects a later Grove decision append. The
[closure checker](baseline-resource-directories/audit-repair-closure.py) reconstructs
the complete digest-bound historical task and acceptance prefixes, permits appends
only to those two paths, and preserves their mode, native identity and symlink
checks. Every other historical input must remain exact. It hashes the entire
current files before and after reading, including the new appends; an edit during
the reading still fails. Derived output belongs to a separate unused destination.

[Eleven focused controls](baseline-resource-directories/audit-repair-closure-tests.py)
cover changed/truncated prefixes, a false archived prefix, an unrelated-file append
and changed mode/inode/symlink. The actual original boundary passed before the
decision append and failed on that exact task path afterward. The new checker
passes without rewriting any historical evidence. Final repeated readings and
the focused test/type/lint results are bound by
[the closure evidence index](baseline-resource-directories/audit-repair-closure-index.json).

This completes this evidence repair only. The finite reviewer stays live and
unsealed. Actual runtime resource discovery, composition truth, saved state,
finite packets/actions/export and the original acceptance/B-reuse work remain
unfinished. Historical host-bound instruments verify their named historical
subjects; they do not authorize replay that overwrites archived inputs or a new
native-fidelity conclusion.

### Configured Fontconfig scope discovery (2026-10-14)

The private importer now discovers the renderer-linked Fontconfig 2.18.3 library
and uses an isolated, reaped Python child with the captured native environment
and working directory. It creates a configuration and parses the default file
directly, then lists reported config entries, include directories, font roots
and cache roots. It recursively binds these roots, including absent optional
roots, and requires exact rediscovery after binding. Environment values are
never serialized. Parsed include directories are trees, even when returned in
the library's config-file list.

The [versioned implementation](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcinit.c)
reveals that FcInitLoadConfig can build font caches on its failure path despite
the developer reference's configuration-only description. The probe instead
uses FcConfigCreate/FcConfigParseAndLoad and never enters that fallback. Empty
configured cache scopes and native debug/parse diagnostics fail explicitly.
FC_DEBUG even set to zero prints diagnostic text; the controlled acceptance
environment leaves that debug variable unset for both discovery and rendering.

`task process:fontconfig-acceptance FIXTURES=... ARTIFACTS=...` consumes the
unchanged process:resource-fixtures construction. It checks actual default
configuration enumeration/cache nonmutation, controlled configured roots and
unchanged RGB under stable inputs, actual include growth/rediscovery, an
incorrect file-only guard that still returns pixels, and malformed parsing
without cache mutation. Guard equality supplies no independent glyph fidelity.
Final frozen source/installed-wheel reruns and raw subjects/results are retained
in baseline-fontconfig-discovery. Construction diagnostics remain uncredited.

On this Mac strict default binding is **unavailable**, because the hidden
Library/Fonts/.home-manager-fonts-version symlink targets absent /nix. No user
font configuration is changed and no candidate is silently omitted. Reported
configured scope is distinct from complete runtime scope or actual renderer
opens/matches. Safe accounting for ignored/dangling entries, missing optional
includes/templates, Poppler CMaps/profiles, native codec inputs and arbitrary
font/glyph/full-page truth remain unfinished. runtime_resources_verified stays
false. The finite reviewer and all saved-project/packet/action/export/public/
representative/B-reuse acceptance remain live in the original open F change.

The final frozen reading preserved all 13,515 enumerated input identities,
bytes, modes, directory members and symlink targets. Source A/B and independent
installed-wheel A/B agree itemwise on default configured roots, controlled scope,
RGB/dimensions and all three native controls. The complete wheel's product-member
set and installed product bytes equal source. Two prepare:check runs pass the
same 1,043 unit identities, including 19 new Fontconfig cases; staff-check passes.
Synthetic preparation reruns preserve all nine case records and 38 actual
writer outcomes itemwise against each other and the retained historical record.
Wrong RGB/size/scope/control/unit/case records are observed rejected. These are
configured-scope/guard/regression results, with the precise unavailable default
binding and missing whole-glyph/native-use truth still explicit. The original
finite handoff remains incomplete.

[The retained index](baseline-fontconfig-discovery/index.json) binds 1,059 raw
files/symlinks in three bounded ZIP parts, including the full source/installed
wheel, native outputs, fixtures/fonts, primary source, graph and instruments.
The separate historical comparer preserves observed writer/barrier identity and
hook/private-name/count facts; its first omitted-barrier diagnostic is uncredited.
Only declared per-run paths, PIDs and opaque private-name tokens are normalized.
A changed barrier, case or unit identity is observed rejected. Retention restores
mode-000 fault files immediately after temporary owner-read access. Later notes
are checked as appends to complete digest-bound archived bookkeeping prefixes;
measurement archives are not rebuilt to include their own derived checks.

The repository jj snapshot limit rejected the initial two-million-byte parts.
The same exact digest-bound ZIP bytes are now partitioned into five parts of
at most900000 bytes; no measurement/raw entry is regenerated. The current index
is authoritative for the final part list. Complete reconstruction/current-host
boundary verification passes with1059 entries/13515 subjects/1043 unit outcomes,
1024 preserved units,9 preparation cases/38 writer outcomes and exact source/wheel
bytes; only complete archived task/acceptance prefixes admit later appends.
The same original F change stays live/unsealed over03eb30ab. Remaining product
work and all original completion obligations remain as recorded above.

### Dangling resource entries (2026-10-14)

Resource-directory binding now retains dangling child symlinks as explicit
absent-target entries. Every directory name remains in the inventory, including
hidden names; the entry records its spelling, resolved missing destination,
symlink text and filesystem identity. Target appearance, alias replacement or
retargeting invalidates the guard. Absence is rechecked after entry/alias reads.
Required roots/files, cyclic aliases, unreadable and special entries still fail.
The versioned Fontconfig scan excludes only `.` and `..`, so a general hidden-name
exemption would be incorrect; see
[Fontconfig 2.18.3 fcdir.c](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcdir.c).

The actual native acceptance runner now includes output-owned missing-target
recording, later target appearance and readable rediscovery. An incorrect
file-only guard still returns the same pixels after candidate growth, exposing
why pixel equality alone is inadequate. Test-owned cold caches are warmed before
stable-resource binding; a cold native render creating cache files correctly
invalidates a bound cache inventory. No user font tree or default cache is edited.

This advances configured-root binding only. Missing optional includes/templates,
actual renderer opens/matches, complete Poppler/native resource scope, cold-cache
integration and arbitrary glyph/full-page truth remain unfinished. The historical
Fontconfig measurement and its unavailable default-binding result are preserved;
new evidence is recorded separately. runtime_resources_verified remains false.
F stays live in its original open jj change; saved state, finite packets/actions/
export, representative acceptance and browser reuse remain outstanding.

The new frozen reading binds 13,521 entire inputs unchanged before/after. Source
A/B and independently installed-wheel A/B agree itemwise on reported default
configured trees, stable RGB/dimensions and every native control. Default discovery
now records 14 roots/1,018 entries/one dangling child without modifying it; this is
configured-scope binding, not complete optional-include/runtime-use/glyph proof.
All 1,053 unit identities/outcomes agree across complete checks, preserving the
previous 1,043 units and adding 10 directory cases. Staff checks pass. All nine
synthetic preparation cases and 38 observed actual-writer outcomes agree with
historical records, including full PID/barrier facts. Wrong case/barrier/unit/
native records are rejected. Complete wheel/product bytes match source.

Raw outputs, fixture/source/wheel bytes, input identities, instruments, primary
source and graph evidence are retained separately under
[baseline-dangling-entries](baseline-dangling-entries/index.json). The two
bookkeeping documents admit later appends to their complete bound prefixes;
all other frozen inputs remain exact. This continuation keeps F live and
unsealed, with all remaining product/acceptance obligations stated above.

The retained ZIP reconstructs 1,104 raw entries from 11 parts, each at most
900,000 bytes. The [read-only current-host checker](baseline-dangling-entries/verify.py)
verifies every retained entry, exact source/wheel product bytes, all frozen
subjects and complete bookkeeping prefixes without regenerating a native run
or rewriting an archive. Temporary owner-read permission on mode-000 fault
artifacts is restored immediately. The checker requires these original host
subjects; it does not reconstruct missing fonts/configuration from digest maps.
F remains live and unsealed at the recorded continuation boundary.

### Lifetime Fontconfig scope rediscovery (2026-10-14)

The resource guard returned by private `discover_fontconfig` now performs a
fresh isolated configuration-only probe whenever the renderer verifies it,
before execution and after native RGB decoding. It retains the captured full
environment, working directory and original file/tree identities, and compares
all four reported scopes. The plain resource subjects guard the probe itself;
rediscovery does not recursively invoke itself or build a font database/cache.
The saved provenance names this additional guard explicitly. Existing normal
resource bindings retain their original behaviour.

In [Fontconfig 2.18.3 fcxml.c](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c),
`_FcConfigParse` adds a configuration filename only after resolution succeeds.
An optional missing include is therefore absent from the original loaded-file
list. A later empty include can change configuration scope while producing
identical RGB; binding only the original reported trees misses that change.
Fresh resolution guards that boundary without pretending to enumerate every
missing candidate or duplicate the native parser's path rules.

The expanded `process:fontconfig-acceptance` recipe uses output-owned absolute
files/directories, relative search-path files, home files and XDG files/directories.
Each begins absent, then loads an empty new include outside the initial reported
trees: the original tree-only guard returns identical pixels, while the new
guard rejects with DEPENDENCY_UNAVAILABLE/5. Explicit rediscovery binds the new
scope and returns the same pixels. A private decode-boundary substitution adds
an include after actual native rendering/decoding and requires the final guard
to reject it; the native child and decoder themselves remain real. Complete
records/commands are written to result.json; terminal output is only a compact
summary. Construction diagnostics are separate from the final frozen reading.

This is configured-scope currency, not complete absent-candidate/template
enumeration, actual renderer file opens/matches, cold-cache integration,
Poppler CMap/profile/native/codec scope or arbitrary-font/glyph fidelity.
Changes restored entirely between checks remain outside the guarantee.
`runtime_resources_verified` remains false. The complete finite reviewer is
still live/unsealed in its original F change; no new public operation or
accepted project is delivered by this private guard.

The final frozen optional-include reading completes with13,541 entire inputs
byte/mode/identity/member/symlink exact before/after. Source A/B and separately
installed-wheel A/B agree per case on all six include kinds, changed-scope
rejection, original-tree-only guard disproof, rediscovery, RGB/dimensions and
post-native rejection. Source/wheel complete product member sets and installed
bytes agree; locked Python product dependencies match. Both prepare:check
readings pass format/lint/strict types and the same1,060 unit identities/outcomes;
all1,053 prior units remain and seven new Fontconfig guard cases pass. Staff
passes. Synthetic preparation pairs preserve all9 historical cases and38
actual writer outcomes including full observed PID/barrier/name/count facts.
Independent read-only comparers reject wrong unit/case/barrier and31 individual
optional-case/post-native records, with all their input hashes unchanged.
A preliminary dependency-name diagnostic stopped before native measurement;
its assumed obsolete transitive names were replaced by names from the locked
export. It remains diagnostic evidence, not an accepted reading.

Retain these new raw records/fixtures/wheel/product/instruments/primary source/
graph bytes under baseline-optional-includes, separately from unchanged prior
archives. Only six of758 existing repository paths changed: this task, acceptance,
Taskfile and the three named Python source/test/instrument files. Runtime
resources/glyph fidelity remain unverified. F remains live in original unsealed
change ryouonnvvlkzyyxmxrpqxnuqrysrqtvy over03eb30ab; no retirement/describe/new,
reviewer/tree cut/cascade/teardown.

Next account for optional templates and complete configured scope versus actual
renderer opens/matches, including cold-cache integration, then Poppler CMaps/
profiles/native/codec/environment and independent arbitrary-font/glyph/full-page
truth. Couple import/assessment/mappings and kernel ownership to immutable
assets/private header/checkpoints/status/source-loss resume. All original
milestones2–5 remain here: native/global-refresh packets; Q1–Q3 actions/durable
replay/scoped inspection/selection-union acknowledgement; exact image-only
export/report/no-clobber; installed writer/isolation/migration/six actual
resource/native/truth packets; compatible predecessor and all five B-reuse
properties. Complex-real/native-codec/Type3 truth and calibration stay unavailable;
k28 retains every missing real truth/reaction/remedy and complete-default/nonrigid
obligation. F/k53/k47/B/k54 remain live. Verify exact archive reconstruction and
current-host/task-owned boundary before advancing continuation, as the last action.

[The retained optional-include index](baseline-optional-includes/index.json) binds
1,161 raw entries in12 parts of at most900,000 bytes (10,552,085 compressed
bytes). The [current-host reconstruction checker](baseline-optional-includes/verify.py)
passes formatting/lint/strict types and verifies every archive/product/wheel
byte, the frozen inputs and exact later-bookkeeping prefixes. It also verifies
752 unchanged files in the pre-edit inventory and the six declared changed
files; the jj diff from the original session snapshot independently names
only those existing changes plus this new evidence directory. It requires
this Mac's original host subjects and temporarily restores owner-read access
to mode-000 test artifacts, then restores each mode. It claims no absence of
transient permission changes. Run it with
`uv run --locked python docs/acceptance/baseline-optional-includes/verify.py`.
All older archives remain exact. The complete finite F product remains live.

### Optional scan-only Fontconfig templates (2026-10-14)

The private configured-input probe now mirrors the successful native initializer's
optional `FcConfigParseOnly` pass. Its version-2 private protocol separately
reports the effective template root and all parsed filenames, including inactive
templates and their includes; loaded-file/directory meanings remain separate.
The resource binding captures every parsed file and the complete optional template
tree, then repeats isolated discovery at each verification. No initialization,
font database build, cache fallback or translated description lookup is invoked.

The compiled template root has no public getter. This implementation supports
the exact current Mac library build, SHA-256
`e1f5e06e8339b42f0e1af11cc77979ef6a8f48ffa7588e4dc243e4bd69ea656d`:
its `FcInitLoadOwnConfig` disassembly supplies the Cellar
`share/fontconfig/conf.avail` path. Other builds fail dependency discovery rather
than infer their compiled setting from the version or installation prefix.
[Fontconfig's build setting](https://github.com/fontconfig/fontconfig/blob/2.18.3/meson.build),
[initializer](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcinit.c),
[parser](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c) and
[file-info iterator](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c)
are the primary sources. Returned iterator filenames are freed; descriptions are
not requested. The actual native sysroot prefixes the recorded optional root.

Construction tests first reject the old protocol/omitted template binding and
unverified native build. Actual output-owned native sysroot controls exercise
absent-template appearance, inactive template byte changes, a later optional
include outside the template tree, malformed templates and an unknown build.
The old loaded-file-only guard misses the changes while all four loaded scopes
remain identical. Fresh discovery binds scan-only includes without activating
their rules or creating the test-owned cache. The existing real-render acceptance
still checks stable glyph RGB and changed-resource rejection separately.
Diagnostic runs precede the frozen final reading and are not credited as that
measurement.

This advances configured-input binding only. Complete candidate enumeration,
actual renderer opens/matches, cold-cache integration, Poppler CMaps/profiles,
native codecs, arbitrary glyph/full-page truth and transient restored changes
remain unverified. Non-template font/cache sysroot resolution is not established
by these configuration-only controls. `runtime_resources_verified` remains false.
All original finite product, project/action/packet/export/native/public/fault/
six-case/compatibility and browser-reuse obligations remain on live F; no accepted
project or public finite reviewer is delivered by this private probe.

The final frozen template reading passes with19,024 entire current inputs byte/
mode/identity/member/symlink exact before/after. Source A/B and separately
installed wheel A/B agree itemwise on default configured/parsed scopes, all
six optional include cases, template controls, stable RGB/dimensions and the
existing post-native guard. Output-owned actual native template controls reject
absent-root appearance, altered inactive bytes, later external scan-only include,
malformed templates and unknown builds; all four loaded scopes stay unchanged,
rules remain inactive and cache absent. Full wheel/product-member/installed bytes
and locked Python dependencies agree. Both complete prepare:check readings pass
format/lint/strict types and the same1,070 unit identities/outcomes; all1,060
prior units remain and10 new template/protocol cases pass. Staff passes. Both
synthetic preparation readings preserve all9 historical cases and38 actual
writer outcomes, including actual PID/barrier/name/count facts. Independent
read-only comparers reject42 individual native records plus wrong unit/case/
barrier records, retaining their input hashes. The stopped first freeze remains
a diagnostic. Only seven existing repository paths changed, exactly this task/
acceptance/Taskfile and the four named implementation/test files; older artifacts
and native/user/default caches remain exact. Retain this new bounded template
evidence separately, then verify archive reconstruction/current-host and the
same task-owned unsealed F boundary before continuation.

Next complete configured scope versus actual renderer opens/matches, cold-cache
integration and non-template native sysroot resource resolution, then Poppler
CMaps/profiles/native/codec/environment and independent arbitrary-font/glyph/
full-page truth. Couple import/assessment/mappings and verified kernel ownership
to immutable assets/private header/checkpoints/status/source-loss resume. All
original milestones2–5 stay here: complete native/global-refresh packets; Q1–Q3
actions/durable replay/scoped inspection/selection-union acknowledgement; exact
image-only export/report/no-clobber; installed writer/isolation/migration and
six actual resource/native/truth packets; compatible predecessor and every B
reuse property. Complex-real/native-codec/Type3 truth/calibration are unavailable;
k28 owns every missing real truth/reaction/remedy and full-default/nonrigid
obligation. No complete runtime-resource/glyph claim, accepted project or public
finite handoff follows. Same live/unsealed F change
ryouonnvvlkzyyxmxrpqxnuqrysrqtvy over03eb30ab; F/k53/k47/B/k54 stay live. No
retirement/describe/new/reviewer/tree cut/cascade/teardown. Advancing continuation
is the final action only after exact retained evidence/boundary verification.

Retention/current-host reconstruction passes with1,290 raw entries in15 parts
of at most900,000 bytes (12,852,831 compressed bytes). Exact source/wheel/installed
product bytes, all19,024 frozen subjects,1,070 units/1,060 preserved units,9
preparation cases/38 writer outcomes,6 optional-include cases and5 native template
controls verify. The checker passes format/lint/strict types. It requires the
original Mac subjects and restores owner-read access for mode000 fault artifacts
immediately after reading; bytes/modes are preserved without claiming absence
of temporary chmod. Native library/header/disassembly, primary source, default
parsed/template config bytes, fixtures, wheel/full product and instruments are
retained separately under baseline-templates. Historical archives stay exact.
The preceding stopped run remains diagnostic, never an accepted measurement.
Tier2 generation2026-10-14T01:27:53Z reports matching metadata/no recorded issue
for material source/tests/recipe/contracts/checker/index, best-effort only. uv.lock
is not_tracked graph metadata and was directly read/exported/digested. Both
directions of discovery trace finish reported pages (16 callers/12 callees);
unrelated heuristic pdf.get/placement.check_cancel edges are not runtime facts.
Exact source/snippet/native outcomes govern. The jj diff from84c2928d names
only the seven existing changed paths plus this new evidence directory, and
the same original open F change still has03eb30ab as its parent. No review or
retirement/sealing/cascade/teardown. One final read-only reconstruction validates
these later bookkeeping appends and the unchanged task boundary, then advancing
continuation is the last action. The immediately preceding unfinished product
inventory remains binding.

[Retained template evidence](baseline-templates/index.json) binds the new
archive; [its current-host checker](baseline-templates/verify.py) reconstructs
all parts and verifies raw/current product, installed wheel and frozen-input
identities. Run `uv run --locked python docs/acceptance/baseline-templates/verify.py`.
This preserves the original complete task/acceptance prefixes while allowing
later bookkeeping appends. The finite reviewer remains live and unsealed.

### Effective Fontconfig font/cache roots (2026-10-14)

The configured-input probe now preserves logical font/cache getter paths and
separately reports effective filesystem roots in private protocol3. Fontconfig
2.18.3 scan/cache I/O always prepends its canonical native sysroot, including
logical paths already beginning with that string. Config/template parsing uses
a distinct prefix-avoidance rule. Resource bindings now capture effective font/
cache trees; loaded config and parsed-template paths keep their previous meaning.
The primary sources are [scan implementation](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcdir.c)
and [cache implementation](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccache.c).
Unknown/old probe protocols fail dependency discovery before use.

The new reusable `process:fontconfig-sysroot-acceptance` recipe uses two
output-owned native sysroots: ordinary logical paths and already-prefixed
logical paths. Its original-code control fails when effective font growth
escapes the resource guard. Construction tests exercise present/absent effective
trees and reject old/incomplete/malformed protocol; unrelated logical font
growth stays outside the bound native scope. Native configured discovery leaves
caches untouched, then actual confined fc-list enumerates the copied font and
populates effective caches. Both cache/font growth and those cold-cache writes
invalidate the old binding with DEPENDENCY_UNAVAILABLE/5, while a deliberately
logical-only guard misses the changes. Fresh warm discovery verifies.

This is bounded Fontconfig configured-input/native enumeration evidence. It
does not establish complete actual Poppler opens/matches, successful cold-cache
renderer import, arbitrary glyph/full-page truth, codecs/CMaps/profiles or
transient-restored-change detection. All original F milestones and completion
checks remain live in the same unsealed task-owned jj change. Native controls
run during edits are diagnostic only; final evidence follows frozen reruns.

The restarted final frozen reading completes with19,625 full input subjects
byte/mode/identity/member/symlink exact before/after. Source A/B and separately
installed wheel A/B agree itemwise on the prior configured/optional/template/
RGB cases and both ordinary/already-prefixed sysroot cases. Effective font
growth, cache growth and actual confined fc-list cold-cache population reject
with DEPENDENCY_UNAVAILABLE/5; the intentionally logical-only guard misses
the changes, and fresh warm discovery verifies. Full product member sets,
wheel/installed/source bytes and locked Python dependencies agree. Both
prepare:check readings pass format/lint/strict types and the same1,079 unit
identities/outcomes; all1,070 previous units remain and nine additions pass.
Staff passes. Synthetic preparation A/B preserve all9 historical cases and
38 installed writer outcomes with exact PID/barrier/name/count facts.
The independent historical comparer permits only the declared private
protocol2->3 and effective-root additions in native records; other existing
records agree. Wrong native/sysroot/unit/case/barrier records reject.
The first shifted-parameter-ID reading is diagnostic only.

A separately captured original-product control retains the complete original
product shadow and actual command/exit/stderr: its native effective-font-growth
case fails with exit1, proving the previous guard omission. Its scripts/product
bytes are exact before/after; frozen current native inputs remain bound by the
final reconstruction. No historical archive or original source/cache changes.
Only six pre-existing repository files changed: the task, acceptance note,
Taskfile, two Fontconfig modules and test_fontconfig; the native sysroot runner
and new bounded retained evidence are additions. Retain raw original/final/
diagnostic records, fonts/cache outputs, primary source, full product/wheel,
construction/regression instruments and graph separately under baseline-sysroot.

Next establish actual renderer opens/matches and a successful cold-cache import
path with explicit immutable-resource/cache ownership; native cache-write
rejection is not that success. Complete Poppler CMap/profile/native/codec/
environment accounting and independent arbitrary-font/glyph/full-page truth.
Couple import/assessment/mappings and kernel ownership to immutable assets/
private header/checkpoints/status/source-loss resume. All original milestones
2–5 remain here: complete native/global-refresh packets; Q1–Q3 actions/durable
replay/scoped inspection/selection-union acknowledgement; exact image-only
export/report/no-clobber; installed writer/isolation/migration/six actual
resource/native/truth packets; compatible predecessor and all five B reuse
properties. Complex-real/native-codec/Type3 truth/calibration remain unavailable;
k28 retains all missing real truth/reactions/remedies and full-default/nonrigid
work. No public finite handoff, accepted project or complete runtime-resource/
glyph claim follows. Same live unsealed F change ryouonnvvlkzyyxmxrpqxnuqrysrqtvy
over03eb30ab; F/k53/k47/B/k54 stay live. No retirement/describe/new/reviewer/
tree cut/cascade/teardown. Reconstruct exact retained evidence and verify the
current-host/task-owned boundary before advancing continuation as the last action.

Retention/current-host reconstruction passes with2,553 raw entries in44 parts
of at most900,000 bytes (39,079,958 compressed bytes). Exact original control,
full source/wheel/installed product,19,625 frozen subjects,1,079 units/1,070
preserved units,9 preparation cases/38 writer outcomes,6 optional-include
cases,5 template controls and2 native sysroot cases verify. The checker passes
format/lint/strict types. It requires original Mac subjects and temporarily
restores owner-read access for mode000 fault artifacts, immediately restoring
mode/bytes; no claim of absent transient chmod. Previous archives remain exact;
the first shifted-ID reading is retained as diagnostic only. Tier2 generation
2026-10-14T01:50:42Z reports matching metadata/no recorded issue for material
source/test/recipe/contract/checker/index paths, best-effort only. uv.lock was
directly read/exported/digested. Exact snippets and both-direction discovery
trace pages (19 callers/12 callees) are retained; heuristic pdf.get/placement
check_cancel edges establish no runtime relationship. Native and source
evidence govern. An initial jj diff -r read shows that revision's changes
relative to its parent; the correct --from3990b8e2 --to@ check verifies only
the six named existing files plus the new native runner and sysroot evidence.
The same original live/unsealed F change still has03eb30ab as parent, with no
retirement/sealing/cascade/teardown or further reviewer. One final read-only
reconstruction checks these bookkeeping appends and exact task boundary, then
signal advancing continuation as the last action. The immediately preceding
unfinished product inventory remains binding.

## Named renderer font use and private cache ownership

The next bounded acceptance instrument is `tests/font_loading_acceptance.py`.
It builds a Mac arm64 test-only pass-through observer against Fontconfig 2.18.3
and FreeType 2.14.3 headers (the latter reports pkg-config ABI version 26.6.20).
It copies the existing controlled Helvetica/Courier inputs into unused private
directories. The observer records actual `FcFontSort`/`FcFontMatch` candidates,
`FT_New_Face` results and the font descriptor opened inside the same face call.
Selection API, face index, PID, order, device, inode and size must agree; disabled,
foreign-PID, wrong-font/inode/index observations must fail. Sorted candidates alone
are not final font use. PID-bound dyld UUID/disk checks retain the actual mapped
observer and native images. This is named API/open evidence, not complete reads
or independent arbitrary-glyph/full-page truth.

Before comparison outputs, construction declares a 600 by 150 RGB frame, exact
pass-through equality and distinct output for the two controlled font subjects.
The ordinary guarded render, directly observed render and disabled-observer
render must have identical decoded RGB for each font. Equality checks interception
and captured-resource behaviour; it supplies no independent source-fidelity pass.

The cold-render rejection uses a separate initially empty private cache. Explicit
`fc-list` construction populates another initially empty private cache before
discovery and binding. Completed cache, fonts and config then remain immutable
through guarded and observed renders. Cache mutation before binding is owned
construction; mutation after binding stays an error. No host cache is deliberately
warmed or edited, no public import/cache API is introduced, and the native observer
is neither packaged nor injected by the product.

```sh
task --exit-code process:font-loading-fixtures \
  FIXTURES=/private/tmp/bookscan-k63-resource-work/fixtures \
  ARTIFACTS=/tmp/NEW-FONT-LOADING-FIXTURES
task --exit-code process:font-loading-acceptance \
  FIXTURES=/tmp/NEW-FONT-LOADING-FIXTURES \
  ARTIFACTS=/tmp/NEW-FONT-LOADING-READING
```

The existing resource fixture supplies test-owned fonts and the constructed PDF;
it does not supply independent glyph truth. Edited-tree diagnostics are separate
from the forthcoming frozen measurement. Complete native resources, general
font/CMap/profile/codec use, actual immutable import-cache lifecycle and every
original F project/view/action/export/public/fault/six-case obligation remain live.

The final frozen reading completed under
`/private/tmp/bookscan-k63-font-loading-work/frozen`. All 19,727 read subjects
preserved their bytes, modes, identities, member sets and symlinks before/after.
Source A/B and separately installed-wheel A/B agree itemwise for both fonts:
the cold pre-bound render rejects with `DEPENDENCY_UNAVAILABLE`/5; explicit
private cold-cache construction precedes successful guarded rendering; native
`FcFontSort` candidates lead to face index 0 and its actual opened private font
descriptor. PID-bound mapped UUID/disk records include the observer. Disabled,
foreign-PID, wrong-font/inode/index controls reject, and observed/disabled/guarded
600 by 150 RGB is exact per font. Helvetica and Courier output digests differ.
The independent itemwise comparer rejects wrong records. This establishes the
named mechanism on this Mac, not general font/glyph/full-page fidelity or complete
runtime resources/reads; restored transient changes remain outside these checks.

Both `prepare:check` readings pass formatting/lint/strict types and the same
1,091 unit identities/outcomes, retaining all 1,079 preceding units plus twelve
construction checks. Staff passes. Synthetic preparation A/B agree on all nine
historical cases and 38 installed-writer outcomes, including observed PID/barrier,
exit, visibility, source-unchanged and reap facts. Complete product member sets
and source/wheel/installed bytes agree; Python runtime dependency versions agree.
Product source is unchanged in this continuation; the observer stays test-only.
No affected real preparation input/product changes require a new real comparison.

Raw fixtures, private fonts/caches, native PID/events/UUID records, PNGs,
construction/build/regression instruments, complete product/wheel, native headers,
frozen inputs and graph evidence are retained in
[baseline-font-loading/index.json](baseline-font-loading/index.json): 1,353 entries
in eighteen parts at most 900,000 bytes (15,370,205 compressed bytes).
Run `uv run --locked python docs/acceptance/baseline-font-loading/verify.py`
to reconstruct and recheck them on this original Mac. Its initial reconstruction
passes, and the checker passes formatting/lint/strict types. Mode000 fault outputs
need temporary owner-read while retaining their exact bytes/modes; this is not a
claim of absent temporary chmod. Prior historical archives are unchanged.

Next implement the actual import-owned immutable resource/private-cache lifecycle
and complete Poppler CMap/profile/native/codec/environment accounting, with named
remaining resource coverage and independent arbitrary-font/glyph/full-page truth.
Couple import/assessment/mappings and existing kernel ownership to immutable
assets/private format/checkpoints/status/source-loss resume. All original
milestones 2–5 remain here: native/global-refresh packets, Q1–Q3 durable receipt
actions/replay/inspection/selection acknowledgement, exact export/report/no-clobber,
installed writer/isolation/migration/six actual resource/native/truth packets,
compatible predecessor and all five B reuse properties. Complex-real/native-codec/
Type3/calibration truth remains unavailable; k28 retains every missing real truth,
reaction/remedy and full-default/nonrigid obligation. The same open F change
ryouonnvvlkzyyxmxrpqxnuqrysrqtvy over03eb30ab remains live, with F/k53/k47/B/k54
unclosed. No public finite handoff, accepted project, retirement/seal, reviewer,
tree cut, cascade or teardown follows this bounded runtime evidence.

## Product-owned private font cache construction

`prepared_fontconfig_cache` now owns a bounded private cache lifetime. Its caller
supplies a configuration whose effective cache roots all resolve to one unused
directory. The operation reserves that directory, binds configuration/font/template/
native inputs, then explicitly invokes `FcConfigBuildFonts` in the isolated child
using the renderer-linked library. The child checks its actual parsed effective
cache roots before building that same configuration. No fallback initializer or
second native tool is used. Fontconfig's [2.18.3 initializer](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcinit.c)
establishes the direct parse/build separation.

Only the reserved cache may change during construction. A fresh discovery binds
the completed cache before rendering; later cache mutation fails the existing
resource guard. The context removes its own reservation on exit, retaining a
replaced root untouched and preserving an already selected cancellation/error.
The returned resource record names construction inputs/method/command; it remains
provenance, with complete runtime resources explicitly unverified. Default scope
discovery remains configuration-only.

The construction tests catch occupied/dangling/aliased roots, foreign effective
roots, font/cache overlap, changed font inputs, native diagnostics/errors,
cancellation, post-binding mutation and replacement-safe cleanup. The actual
native runner exercises two controlled fonts, repeated exact 600 by 150 guarded
renders, mutation refusal, cleanup and foreign-root refusal both in the owner and
the actual isolated child before cache writes:

```sh
task --exit-code process:cache-construction-acceptance \
  FIXTURES=/private/tmp/bookscan-k63-font-loading-work/fixtures \
  ARTIFACTS=/tmp/NEW-CACHE-CONSTRUCTION-READING
```

This operation does not yet copy ordinary configuration/font resources into the
project or remap ordinary host cache routes. The caller must already supply the
confined configuration; the public importer/store remains unfinished. There is
no new public route, accepted project, independent glyph truth, complete native
resource coverage or exclusion of transient changes restored during reads.
Original import/project/packet/action/export/fault/isolation/six-case requirements
and B's five reuse properties remain in the same live F owner. The next frozen
reading verifies this new operation, the existing native font-loading evidence,
the installed wheel and inherited preparation/staff checks item by item.

The corrected final frozen reading retains 20,327 unchanged input subjects.
Source A/B and independently installed wheel A/B agree itemwise on both controlled
fonts for the new constructor and inherited actual face/open/native-image checks.
The constructor's exact 600 by 150 PNGs agree with the inherited guarded renders;
completed native caches are copied before cleanup. Post-binding growth rejects
with DEPENDENCY_UNAVAILABLE/5. Foreign cache roots remain empty after rejection by
both the owner and actual child. Construction, rendering, mutation refusal and
cleanup are exercised together; ordinary configuration/font snapshotting and
public import integration remain unfinished.

Both full checks pass formatting, lint, strict types and identical 1,107 unit
identities/outcomes, preserving all 1,091 preceding units plus sixteen constructor
cases. Staff passes. Preparation A/B retain all nine historical cases and 38
installed-writer outcomes itemwise. The independent comparer preserves prior
native records and rejects wrong unit/case/barrier/native/cache records. Complete
product member sets/source/wheel/installed bytes and all four locked Python runtime
dependency versions agree. No preparation code or real input changed.

[Retained raw evidence](baseline-cache-construction/index.json) contains 2,663
entries in 45 parts of at most 900,000 bytes (40,024,855 compressed bytes), including
final and diagnostic records, fonts, completed cache copies, PNGs, native records,
complete product/wheel, locked runtime export, primary source, instruments and
Tier 2 graph evidence. The first wrapper's self-output binding is diagnostic only.
Run `uv run --locked python docs/acceptance/baseline-cache-construction/verify.py`
on this original Mac to reconstruct and recheck the final evidence. Its initial
reconstruction and formatting/lint/strict types pass. Mode000 fault records need
temporary owner-read, immediately restored; no transient-change exclusion follows.
Historical archives remain unchanged. F and its original jj change stay live
and unsealed for the complete remaining import/project/view/action/export handoff.

## Explicit configuration/font snapshot ownership

`prepared_fontconfig_snapshot` now couples a supported explicitly selected
configuration/font copy to the product's private cache lifetime. It binds the
original inputs, copies complete configured trees (including hidden candidates
and dereferenced aliases), checks their byte identities, redirects loaded
configuration/include/font/cache paths to physical private locations and verifies
actual native rediscovery before constructing a fresh cache. All non-path XML
bytes, including match rules, DTDs and comments, remain exact. Native libraries
and the installed scan-only template tree remain explicitly bound host subjects.
This is an internal import mechanism, not durable project publication or default
configuration selection.

The original sysroot approach failed the actual host-loss check. Fontconfig's
scan resolved private effective directories but still emitted logical original
`FC_FILE` paths; Cairo used those paths and its RGB changed after the test-owned
originals disappeared. The replacement uses physical copied paths and retains
that failed diagnostic separately. The relevant version-specific semantics are
in [Fontconfig 2.18.3](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcdir.c).
Namespace-disabled Expat also preserves Fontconfig's actual undeclared `xsi:nil`
template syntax; a namespace-aware XML serializer had rejected that input.

The context owns only its unused reservation and cache. It rejects occupied or
overlapping roots, a preexisting sysroot, unbound tree scopes, dangling candidates,
entity-dependent XML, relative-realpath/remap constructs and unsupported path
prefixes. A relative include is supported only when it identifies one bound
loaded destination. Input changes or cancellation during copying prevent a
usable result and clean partial output. Later copied input changes fail the
resource guard. Cleanup leaves a replaced root untouched and preserves a chosen
cancellation/error.

The native construction case includes a directory of matching rules, an explicit
font root, two equivalent ordinary/xdg cache routes and two distinct controlled
fonts. It compares exact 600×150 RGB against the original-resource render,
removes the test-owned original configuration/font paths, repeats the private
render, observes copied-font mutation refusal and retains completed resources
before cleanup. These comparisons establish this lifetime and pass-through
behaviour; they are no independent glyph/composition fidelity oracle.

```sh
task --exit-code process:font-snapshot-acceptance \
  FIXTURES=/private/tmp/bookscan-k63-font-loading-work/fixtures \
  ARTIFACTS=/tmp/NEW-FONT-SNAPSHOT-READING
```

Default configuration discovery/copying, xdg/relative/remap font/include semantics,
fully project-owned template/native/Poppler CMap/profile/codec resources and
independent arbitrary-font/glyph/full-page truth remain unfinished. Every original
finite project/packet/action/export/fault/denied-read/six-case obligation and B's
five reuse prerequisites remain in the same live unsealed F owner. No public
finite handoff or accepted project follows from this bounded mechanism.

The frozen reading verifies 20,955 unchanged input subjects. Source A/B and the
independently installed locked wheel A/B agree itemwise for both fonts, including
exact original-resource/private/post-host-loss RGB, copied-font mutation refusal
and cleanup. The inherited font-face/open/native-image and cache-construction
runs also agree itemwise and preserve the preceding records. Source, complete
wheel member set and installed product bytes match; all four Python runtime
dependency versions match the locked environment.

Both `prepare:check` readings pass format/lint/strict types and identical 1,127
unit outcomes, preserving all 1,107 previous units plus twenty snapshot cases.
Staff passes. Synthetic preparation reruns preserve nine cases and 38 actual
installed-writer outcomes itemwise. No preparation implementation or real input
changed; no affected real preparation comparison follows from this private addition.

[Raw retained evidence](baseline-font-snapshot/index.json) contains 1,468 entries
in 44 parts of at most 900,000 bytes (39,433,239 compressed bytes). It includes
successful source/wheel/native/cache/snapshot runs, failed sysroot diagnostic
PNGs, completed private resources, inputs, product/wheel, locked runtime export,
primary source, graph and measurement/comparison instruments. The failed
sysroot diagnostic records the observed old mechanism; the retained product is
the replacement. Recheck the successful evidence on this original Mac with
`uv run --locked python docs/acceptance/baseline-font-snapshot/verify.py`.
Initial reconstruction and the checker's format/lint/strict types pass. Mode000
fault evidence needs temporary owner-read, immediately restored; this establishes
no exclusion of transient changes. Existing archives remain unchanged.

## Native default configuration selection

The snapshot context now accepts an omitted explicit configuration. It resolves
Fontconfig's captured default selection, including a relative `FONTCONFIG_FILE`
searched through `FONTCONFIG_PATH`, before reserving any output. The selected
entry point must belong to the verified loaded configuration and bound file
inventory. It is never inferred from the sorted parsed-file roster, which also
contains included rules and scan-only templates. Explicit selection keeps its
override behaviour; provenance distinguishes `explicit` and `captured-fontconfig`.

The verified Fontconfig 2.18.3 library exports `FcConfigGetFilename(config, NULL)`.
The isolated helper passes a newly created empty configuration, frees the returned
filename and destroys that configuration. Calling `FcConfigFilename(NULL)` would
reference global state and can initialize/build fonts; installing an empty current
configuration also triggers font construction. The decision is grounded in the
[versioned native implementation](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c).
The separate selection protocol leaves configured-scope version 3 unchanged.
Malformed/foreign/unbound results, diagnostics and cancellation cannot produce a
usable snapshot. Native ownership/failure checks also exercise allocated filename
release, configuration destruction and avoidance of loading/font-build branches.

```sh
task --exit-code process:font-selection-acceptance \
  FIXTURES=/private/tmp/bookscan-k63-font-loading-work/fixtures \
  ARTIFACTS=/tmp/NEW-DEFAULT-SELECTION-READING
task --exit-code process:font-selection-acceptance SELECTION=environment \
  FIXTURES=/private/tmp/bookscan-k63-font-loading-work/fixtures \
  ARTIFACTS=/tmp/NEW-ENVIRONMENT-SELECTION-READING
```

The controlled fixture has an included rule preceding its main entry point in
the native sorted roster. With no `FONTCONFIG_FILE`, and separately with the
relative `fonts.conf` value, both font cases retain exact 600×150 RGB through
copying and original-resource disappearance. Source A/B and independently
installed locked wheel A/B agree itemwise for both selection modes and the
inherited explicit mode. Copied-font mutation is refused and only owned private
resources are removed. These are controlled selection/lifetime results, not
independent glyph/full-page fidelity or successful copying of this Mac's entire
ordinary default configuration. XDG, relative-realpath and remapped font/include
paths, project-owned templates/native/Poppler CMap/profile/codec resources and
complete import/project/public review/export remain unfinished in this live F.

The final reading froze 21,579 subjects. Every recorded identity, member set,
mode, symlink and byte digest stayed unchanged during measurement. Exploratory
reads had regenerated Python caches before this freeze; those prior differences
are recorded separately, with no exemption from the final before/after check.
Both full `prepare:check` readings pass format/lint/strict types and identical
1,141 unit outcomes, preserving every previous 1,127 outcome plus fourteen new
cases. The original wheel rejects all fourteen new cases. Inherited actual
font-face/open/image and cache readings remain itemwise equal to their prior
records. Staff passes; synthetic preparation reruns retain all nine cases and
38 installed writer/barrier/exit/source/visibility/reap outcomes. Preparation's
implementation and real fixtures did not change.

[Retained raw evidence](baseline-font-selection/index.json) stores logical records
through digest-bound deduplicated ZIP blobs, with independent part/entry hashes.
It includes the source/wheel/native/default/environment/explicit runs, complete
private resources and PNGs, construction truth, frozen subjects, primary source,
original-code controls, graph evidence, product/wheel and locked export.
Reconstruct it on the original Mac with
`uv run --locked python docs/acceptance/baseline-font-selection/verify.py`.
The same live unsealed F change owns the remaining work; this mechanism publishes
no accepted project and retires neither F nor its baseline/page-review parents.

## Captured font-path copying

The configuration/font snapshot now resolves XDG font directories against the
captured data-home and **all** data-directory roots, realpath-relative directories
against the original configuration, cwd/default paths against the captured child
working directory, and home-relative font paths against captured HOME. Loaded XDG
includes use their distinct config-home rule. Every expanded font directory must
belong to the bound native scope. Copying retains salts and all non-path XML bytes;
the existing native rediscovery checks the complete copied scope before building
the owned cache. These rules follow the pinned
[Fontconfig 2.18.3 parser](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c),
[configuration implementation](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c)
and [filename implementation](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcstr.c).

The new recipe runs an actual original-resource/copy/host-loss render and copied-
font mutation refusal for each of two controlled fonts. PATH_FORM is one of
`xdg`, `relative`, `relative-alias`, `cwd`, or `home`; use a new output per reading.
The XDG construction has three font roots and a config-home include. The alias
construction resolves a relative font directory from the configuration's real
location, rather than its symlink spelling. Exact 600×150 RGB equality establishes
resource lifetime and unchanged controlled rendering, without supplying an
independent glyph/full-page truth oracle.

```sh
task --exit-code process:font-paths-acceptance PATH_FORM=xdg \
  FIXTURES=/private/tmp/bookscan-k63-font-loading-work/fixtures \
  ARTIFACTS=/tmp/NEW-FONT-PATH-READING
```

Remap-dir, unresolved/optional XDG includes, unsupported path prefixes, complete
ordinary default copying, project-owned scan-only templates/native/Poppler CMap/
profile/codec resources, and independent arbitrary-font/glyph/full-page truth
remain unfinished. All original finite project/packet/action/export/fault/isolation/
six-case requirements and browser reuse prerequisites remain in the same live F.

The frozen reading retained 22,176 declared subjects unchanged. Source A/B and
separately installed locked wheel A/B agree itemwise for all five path forms,
both controlled fonts, exact original/private/post-host-loss RGB, copied-font
mutation refusal and owned cleanup. The native XDG scope has all three roots.
Inherited font-face/open/native-image/cache and explicit/default/environment
records preserve their preceding outcomes. Full product/source/wheel/installed
membership and bytes and locked runtime versions agree.

Both full checks pass format/lint/strict types and the same 1,153 test identities
and outcomes, preserving all 1,141 previous outcomes plus twelve new cases. Ten
positive cases reject the preceding installed wheel; two unbound-expansion cases
check refusal rather than newly missing behaviour. Staff passes. Preparation
reruns preserve nine cases and 38 installed-writer outcomes itemwise. Preparation
code, dependencies and real fixtures are unchanged.

[Retained evidence](baseline-font-paths/index.json) includes 2,564 logical records
in 21 digest-bound parts, exact PNG/resource copies, construction truth, source/
wheel/native records and measurement instruments. Reconstruct and recheck it on
this original Mac with:

```sh
uv run --locked python docs/acceptance/baseline-font-paths/verify.py
```

Its initial reconstruction and checker format/lint/strict types pass. The bounded
copy result supplies no accepted project, public finite workflow or glyph-fidelity
acceptance. The same live unsealed F owner retains the complete remaining work.

## Missing optional XDG include copying

The latest bounded copy mechanism handles a genuinely absent optional XDG include.
It preserves the include element and its attributes, redirects the destination
into the private namespace and leaves that destination absent. Required absence,
unknown/false optional values, existing unbound files/directories and dangling
links refuse. This completes the missing-optional-XDG case left open above;
general include resolution and remap/default completeness remain unfinished.
Boolean interpretation follows the pinned
[Fontconfig 2.18.3 implementation](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcname.c),
including its nonzero DontCare values. Original and copied native scope verification
remain mandatory; a later appearing private include invalidates the guard.

Seven new positive constructions fail against the preceding source and separately
installed preceding wheel. Six refusal controls supplement them. The actual native
case exercises seven boolean spellings and both controlled fonts, checks complete
copied scope and absence, observes new-rule refusal, compares exact 600×150 RGB
through original-resource disappearance and rejects copied-font mutation. These
are resource-lifetime and controlled-render results, with no independent glyph or
full-page fidelity claim.

```sh
task --exit-code process:font-paths-acceptance PATH_FORM=xdg-optional \
  FIXTURES=/private/tmp/bookscan-k63-font-loading-work/fixtures \
  ARTIFACTS=/tmp/NEW-OPTIONAL-INCLUDE-READING
uv run --locked python docs/acceptance/baseline-font-includes/verify.py
```

The final frozen reading retains 22,783 subjects unchanged in bytes, modes,
identities, member sets and symlinks. Source A/B and separately installed locked
wheel A/B agree itemwise for the optional case and every inherited font-loading,
cache, explicit/default/environment selection and five previous path forms.
Full product/wheel/installed membership, bytes and four locked runtime versions
match. Both full checks pass format/lint/strict types and identical 1,166 unit
outcomes, preserving all previous 1,153 outcomes plus thirteen new cases. Staff
passes. Preparation reruns retain nine cases and 38 installed-writer outcomes
itemwise; preparation implementation, dependencies and real inputs are unchanged.

[Retained evidence](baseline-font-includes/index.json) contains 2,813 logical
entries in 22 digest-bound parts (19,782,291 compressed bytes). It includes exact
PNG/private-resource/native records, primary sources, source/wheel/original-code
controls, frozen subjects and comparison instruments. Original-host reconstruction
and checker format/lint/strict types pass. Two incomplete readings are explicitly
uncredited: the first stopped for a stale checker count, and the next failed at a
runner type annotation; their diagnostics and named temporary directories remain
recorded in the task. No interrupted reading supplies final-measurement credit.

General include resolution, remap-dir, ordinary default copying, project-owned
scan templates/native/Poppler CMap/profile/codec resources and independent arbitrary-
font/glyph/full-page truth remain. Complete finite saved projects, packets/actions,
resume/export, installed faults/isolation/six-case acceptance, predecessor fixture
and all five browser reuse prerequisites remain in the same live unsealed F.
This bounded result publishes no accepted project or complete public finite handoff.

## Captured home includes and absolute destination validation

The bounded copier resolves home-prefixed include names against captured HOME,
using the pinned [Fontconfig 2.18.3 filename join](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c).
Both `~/config/conf.d` and `~config/conf.d` join HOME and the remaining name with
a separator. The copied include retains its attributes and points into the
private namespace. Absolute destinations must be loaded configuration or a
genuinely absent optional boundary; required absence, existing unbound files/
directories and dangling entries refuse. Captured-home absence is unsupported.
The ordinary relative search-path resolver and remap/default completeness remain
unfinished. The existing recipe accepts `home-include`, `home-include-bare`,
`home-optional` and `home-optional-bare` with a new output for every reading.

```sh
task --exit-code process:font-paths-acceptance PATH_FORM=home-optional-bare \
  FIXTURES=/private/tmp/bookscan-k63-font-loading-work/fixtures \
  ARTIFACTS=/tmp/NEW-HOME-INCLUDE-READING
```

Twenty construction additions expose eight previously rejected home positive
cases and six previously unvalidated absolute destinations; six home refusal
controls already reject. The preceding independently installed wheel also rejects
the actual native home-optional-bare case. Controlled native equality measures
resource lifetime, with no independent glyph/full-page fidelity claim. Complete
finite saved projects, packets/actions, resume/export, installed faults/isolation/
six-case acceptance, predecessor fixture and browser reuse prerequisites stay live.
The frozen reading and its itemwise comparison are recorded below after completion.

The complete frozen reading passes with 23,392 declared subjects unchanged in bytes,
modes, identities, member sets and symlinks. Source A/B and independently installed
locked wheel A/B agree itemwise for all four new home-include forms and every
inherited native face/open/image/cache, explicit/default/environment selection
and six path forms. Both controlled fonts retain exact 600×150 RGB through
original-resource loss; optional home cases retain seven absent private includes,
reject a newly appearing rule and refuse copied-font mutation. Full product/
wheel/installed membership and bytes and four locked runtime versions agree.

Both prepare:check readings pass format/lint/strict types and the same 1,186 unit
outcomes, preserving all prior 1,166 plus 20 additions. Staff passes. Synthetic
preparation A/B preserve all nine cases and 38 actual installed writer outcomes
itemwise. Preparation implementation, dependencies and real inputs are unchanged.
One earlier reading was stopped for a stale reconstruction-checker count and is
explicitly uncredited at `/private/tmp/bookscan-k63-home-includes-work/frozen-stopped`.

[Retained evidence](baseline-home-includes/index.json) contains 3,389 logical
entries in 28 digest-bound parts of at most 900,000 bytes (25,022,051 compressed
bytes). It retains exact PNG/private-resource/native/selection records, product/
wheel/locked export, primary sources, red diagnostics and comparison instruments.
The [original-host reconstruction checker](baseline-home-includes/verify.py)
passes, as do its format/lint/strict-type checks. Recheck on this original Mac:

```sh
uv run --locked python docs/acceptance/baseline-home-includes/verify.py
```

This verifies the bounded copy mechanism only. Ordinary relative search paths,
remap-dir, ordinary default copying, project-owned templates/native/Poppler CMap/
profile/codec/environment accounting and independent arbitrary-font/glyph/full-page
truth remain unfinished. All finite saved-project/packet/action/resume/export/
fault/isolation/six-case and browser reuse obligations remain with the same live F.
No accepted project or complete public finite handoff is delivered here.

## Captured ordinary include search order

The copier now resolves ordinary relative includes through the captured native
search order rather than a unique loaded suffix. It searches FONTCONFIG_PATH,
then this checksum-verified Fontconfig 2.18.3 build's `/opt/homebrew/etc/fonts`.
Relative roots use captured cwd; interior empty roots join as `/name`, and the
trailing empty root is skipped. Optional missing includes retain a private absent
boundary. Selected unbound files/directories, dangling or unreadable candidates,
required absence and empty include selection refuse. Symlink/parent normalization
that changes the filesystem target refuses, preventing silent loaded-file substitution.
The private renderer environment uses the same normalized, confined search roots.

The version-specific evidence is [FcConfigGetPath/FcConfigFileExists](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c)
and [the compile-time path definition](https://github.com/fontconfig/fontconfig/blob/2.18.3/meson.build).
Native empty-config filename resolution independently checks the actual default
root in four environment forms without parsing or building a font database.
The package's `confdir` and library checksum agree. New construction tests expose
search-order/suffix errors, environment confinement and symlink-parent substitution
before their fixes. The old independently installed wheel rejects the new native
optional-search construction at its suffix-guessing branch.

The existing `process:font-paths-acceptance` recipe adds `search-first`,
`search-second`, `search-relative`, `search-empty` and `search-optional`. Each uses
two independently loaded directories with the same suffix, actual native scope
verification, two controlled fonts, copied/original render comparison, host-resource
loss and copied-font mutation. Optional cases retain seven private absent includes
and refuse a newly appearing rule. These check resource lifetime and configuration
selection; they supply no independent glyph or complex-page fidelity oracle.

The complete frozen source/wheel A/B reading and retained raw evidence follow
below after verification. Remap semantics, ordinary default configuration,
project-owned templates/Poppler CMaps/profiles/native-codec/environment coverage,
independent real/glyph truth and all saved-project/public finite milestones remain
unfinished in the same live F owner. No partial project or finite handoff is accepted.

The first frozen reading stopped when native ConfigFiles returned a relative
included-directory path in the relative-search construction. The strict parent
protocol rejected it; the other native path records were absolute. The stopped
reading is diagnostic only, retained as `frozen-scope-failure`. A native raw-scope
probe confirmed the exact relative entry. The scope child now makes configuration
filenames absolute against its captured cwd, including native default selection,
without changing protocol version 3 or permitting target-changing alias/parent
normalization. Five additional construction tests precede the helper; together
with the copy/context tests there are thirty-one added unit identities.
The path recipe now forwards optional `SELECTION`, permitting explicit/default/
environment selection on the same relative-search construction. Source and wheel
repeats for those two additional selection variants belong to the restarted
frozen reading. Product/instrument/wheel edits finish before that restart.

Actual relative-search explicit/default/environment explorations now succeed for
both controlled fonts. The next frozen reading stopped before native measurements
at the strict private-test-access check; it is retained as `frozen-type-failure`,
without complete-measurement credit. Narrow test-only private-access annotations
resolve that gate while preserving the product helper's private visibility.
The final reading starts only after the full product gate passes. It expects all
1,186 inherited unit identities plus 31 additions, 88 native readings including
68 path-form readings, and the unchanged synthetic preparation/writer outcomes.

The final frozen reading passes with 24,016 declared subjects unchanged in bytes,
mode, alias/target identity and directory membership. Both complete product gates
pass formatting, lint, strict types and identical 1,217 units, preserving all 1,186
previous outcomes plus 31 additions. All 88 source/wheel A/B native readings agree
itemwise, including five new search forms and relative default/environment selection.
Both controlled fonts retain exact 600×150 RGB through resource copying and host
loss. Optional search cases retain seven absent private include boundaries and
reject a newly appearing rule; copied-font mutation refuses with 5 and cleanup
removes the owned snapshot. Complete product/wheel/installed membership and bytes,
and all four locked runtime dependencies, agree. Staff passes. Synthetic
preparation A/B preserve nine cases and 38 installed writer outcomes itemwise.
No preparation implementation, dependency or real fixture changed.

[Retained evidence](baseline-search-includes/index.json.gz) has 7,175 logical
entries in 67 parts of at most 900,000 bytes, with SHA-256 deduplication and
60,024,852 compressed archive bytes. The compressed index is 202,254 bytes,
keeping every artifact within jj's existing new-file limit. It includes the two
explicitly uncredited failed readings, final raw records and PNGs, full copied
resources, wheel/product, pinned primary sources, red constructions, native default
selection and measurement/comparison instruments. The [reconstruction checker](baseline-search-includes/verify.py)
passes original-host byte/identity, archive membership, full source/wheel and
per-item native/regression verification; its format/lint/strict checks pass.

```sh
uv run --locked python docs/acceptance/baseline-search-includes/verify.py
```

Tier 2 coverage at generation 2026-10-14T05:40:33Z has matching metadata/no
recorded issue for changed code/tests/recipe/note/task and the new checker,
best-effort only. The compressed index is parsed and digest-verified directly
where graph tracking metadata lags; the explicit jj boundary verifies it is
tracked together with every part. Exact snippets and complete one-hop pages
support the two path helpers' consumers; heuristic unrelated resolve/get edges
are not filesystem or native-call evidence. Actual native processes and red
controls govern the behavioral claims. Remap/default configuration, remaining
include edge forms, complete project-owned/native resources, independent glyph/
complex-page truth and saved-project/public finite milestones remain unfinished
with F. This internal mechanism supplies no accepted finite handoff or visual approval.

## Copied Fontconfig remap directories — 2026-10-14

The copier now redirects bound physical `remap-dir` directories into its private
resource snapshot while preserving their logical `as-path`, salt and order.
It uses the existing captured prefix expansion and refuses missing map attributes,
empty or unbound physical directories and nested path elements. A later `dir`
replaces an earlier mapping for the same physical root, as the native library does.
Logical cache paths are retained rather than treated as another font-read tree.

The pinned primary evidence is [Fontconfig 2.18.3 remap parsing](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c),
[ordered directory/map/salt replacement](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcstr.c),
and [mapped-directory plus salt cache naming](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccache.c).
Native cache names are checked against independent keys declared before rendering.
The wrong-salt control disagrees with the observed native key; copy construction
controls expose lost map/salt/order/prefix behavior. The corrected preceding-product
reading fails all 24 new positive remap cases, while four conservative refusals
already hold. An initial test-only cwd mistake is diagnostic only. The preceding
independently installed wheel refuses the new native remap construction.

The existing `process:font-paths-acceptance` recipe now accepts `remap-absolute`,
`remap-relative`, `remap-home`, `remap-xdg`, `remap-override`,
`remap-logical-home` and `remap-logical-relative`. Every form uses both controlled
fonts, verified copied native scope, exact original/copy RGB comparison, original
resource disappearance, copied-font mutation refusal and owned cleanup. XDG uses
three physical roots; the later-dir case checks the overriding salt/cache key.
These checks establish controlled resource copying and lifetime, with no
independent arbitrary-font/glyph or complex-page fidelity claim.

The final frozen reading passes with 24,671 declared subjects unchanged in bytes,
mode, alias/target identity and directory membership. Source A/B and the separately
installed locked wheel A/B agree itemwise across all 116 native readings: inherited
face/open/image/cache/snapshot/selection/path records and 28 new remap readings.
Both product gates pass formatting, lint, strict types and identical 1,245 unit
identities, preserving all 1,217 predecessors plus 28 additions. Staff passes.
Synthetic preparation A/B preserve nine cases and all 38 actual installed-writer
barrier/exit/visibility/reap outcomes itemwise. Complete product/wheel/installed
membership and bytes and four locked runtime dependency versions agree. No
preparation implementation, dependency or real fixture changed.

[Retained evidence](baseline-remap-dirs/index.json.gz) contains 5,650 logical
entries in 50 parts of at most 900,000 bytes and 44,454,386 compressed archive
bytes, with SHA-256 deduplication and complete entry/part verification. It retains
raw readings/PNGs/private resources, wheel/product/fixtures, primary sources,
red constructions, the old-wheel refusal and measurement/comparison instruments.
The [reconstruction checker](baseline-remap-dirs/verify.py) passes on the original
Mac, including per-construction native cache keys, full private resource bytes,
source/wheel comparisons and all inherited regressions; its format/lint/strict
checks pass too.

```sh
uv run --locked python docs/acceptance/baseline-remap-dirs/verify.py
```

Tier 2 has matching metadata/no recorded issue for the current code and new
checker, a best-effort signal. The compressed index/parts are read, decompressed
and digest-verified directly where graph tracking metadata lags. Exact source
and the reported one-hop caller page support the copier relationship; nested
callbacks are verified in source rather than inferred from missing graph edges.
Red constructions and actual native processes govern the behavioral claims.
Complete ordinary default configuration, remaining include/string edge forms,
project-owned templates/CMaps/profiles/native-codec/environment coverage,
independent glyph/complex-page truth and all saved-project/public finite milestones
remain unfinished with F. This internal mechanism supplies no accepted project,
finite handoff, real fidelity or visual acceptance.

## Exact copied path text — 2026-10-14

The Fontconfig copier now preserves path character data, including boundary
whitespace. Trimming could otherwise select a different, already-bound sibling.
Nested path children refuse instead of combining their separate native string
buffers. Include `prefix="relative"` uses the captured ordinary search resolver;
Fontconfig handles only `xdg` specially for includes. These decisions are checked
against [the pinned Fontconfig 2.18.3 parser](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c)
and cited beside the changed calls.

All twenty added constructions fail against the preceding implementation:
four relative-prefix search forms, twelve exact-space/tab/newline/nonbreaking-space
font/remap/include paths with independently bound trimmed decoys, and four nested
path-child refusals. The corrected snapshot suite passes all 141 identities.
Actual native `font-space`, `include-space` and `include-relative` constructions
extend the existing `process:font-paths-acceptance` recipe. Each uses both controlled
fonts, verified native scope, exact copied rules, original-resource and copied
renders, original-resource disappearance and copied-font mutation refusal. The
previous installed wheel refuses the new whitespace-font case. These are copy/
render-equivalence checks, not an independent glyph or arbitrary-page oracle.

The frozen source A/B and independently installed locked wheel A/B agree itemwise
across all 128 native runs, including 108 path readings over 27 forms. Both complete
product gates pass formatting, lint, strict types and the same 1,265 unit identities,
preserving all 1,245 predecessors and adding twenty. All 25,305 declared subjects
are unchanged. Complete product/wheel/installed bytes and membership, plus the
four locked runtime versions, agree. Staff passes; synthetic preparation A/B
preserve all nine cases and 38 installed-writer outcomes itemwise. Preparation
implementation, dependency pins and real fixture subjects are unchanged.

[Retained evidence](baseline-path-text/index.json.gz) has 6,057 logical entries,
54 parts of at most 900,000 bytes and 48,000,976 compressed archive bytes with
SHA-256 deduplication and complete entry/part verification. Its compressed index
is 169,546 bytes. The [reconstruction reader](baseline-path-text/verify.py) passes
on the original Mac, including exact retained resources and RGB panels. Its first
summary inherited a hardcoded 96 path readings; the reader now derives 108 from
the verified per-form records. Frozen original instruments remain unchanged in
the archive; no measurement was adjusted during reading. Reader format/lint/strict
types pass. Reproduce the reconstruction with:

```sh
uv run --locked python docs/acceptance/baseline-path-text/verify.py
```

Tier 2 code coverage has matching metadata/no recorded issue, best-effort only;
the copied checker and compressed archive are verified directly. The red
constructions and actual native processes provide the executable disproof
instrument for these behaviors; no additional reviewer is used.

Complete ordinary default configuration and remaining path edge cases still
belong to F, followed by project-owned templates/Poppler CMaps/profiles/native/
codec/environment accounting and independent glyph/complex-page truth. All
saved-project, matched packet/action/acknowledgement, exact export, installed
fault/isolation, compatible-project and six-case obligations remain unfinished.
F/k53/k47/B/k54 remain live under the same complete-owner cadence exception.

## Private missing font targets and the ordinary default configuration

The input copier now retains bound dangling font names as private symlinks to
mirrored missing destinations under its owned root. It preserves the candidate
name without leaving a route to host resources. New unbound names still refuse;
changing a copied link or making its missing target readable invalidates the
binding before native rendering. Configuration rules and every ordinary file's
bytes retain the previous copy contract. Native libraries and scan-only templates
remain host-bound, and arbitrary-font/full-page glyph truth is unavailable.

Nine absolute/relative/chained constructions first fail at the preceding copier's
refusal. The new native forms exercise both controlled fonts through copy and
original-resource disappearance, with a newly readable copied target rejected as
DEPENDENCY_UNAVAILABLE/5. The test retention helper now preserves symlinks rather
than dereferencing intentionally missing targets. Historical evidence and its
unavailable default results remain unchanged.

```sh
task --exit-code process:font-paths-acceptance PATH_FORM=dangling-absolute \
  FIXTURES=/private/tmp/bookscan-k63-font-loading-work/fixtures \
  ARTIFACTS=/tmp/NEW-ABSENT-TARGET-READING
task --exit-code process:font-default-acceptance \
  SOURCE=/private/tmp/bookscan-k63-font-loading-work/fixtures/source.pdf \
  ARTIFACTS=/tmp/NEW-ORDINARY-DEFAULT-READING
```

The second recipe selects this Mac's ordinary default Fontconfig configuration,
checks the complete copied native scope and non-configuration file digests,
preserves private missing targets, renders the declared 600×150 fixture through
its private warmed cache and removes the snapshot. It never changes user fonts,
configuration or default caches. Its render is reproducibility evidence, not
independent glyph truth or original-host/source fidelity. Frozen source/wheel
paired readings and their retained evidence are recorded below after verification.
These internal import checks publish no saved accepted project or finite public
handoff. F remains live for project/resource ownership and its original complete
review/resume/export and acceptance inventory.

The final frozen reading holds 25,970 declared subjects unchanged before/after.
Source A/B and the independently installed locked wheel A/B agree itemwise for
120 path readings and four actual ordinary-default readings, alongside the
inherited font-loading/cache/snapshot/selection evidence. Both complete product
gates pass format/lint/strict types and identical 1,274 unit outcomes, preserving
all 1,265 predecessors plus nine additions. Each full-default reading verifies
965 copied non-configuration file identities and one privately confined absent
target. Both controlled fonts preserve exact 600×150 RGB across copy and host
loss; copied-target appearance and copied-font mutation refuse with 5. Staff
passes; synthetic preparation pairs preserve nine cases and all 38 installed
writer/barrier/exit/source/visibility/reap outcomes. Preparation code, locked
runtime dependencies and real fixtures are unchanged.

[Retained evidence](baseline-absent-targets/index.json.gz) contains the raw paired
readings, construction failures, original-wheel refusal, complete controlled
resources, product/wheel bytes and frozen subject manifests. The ordinary Mac
font bytes remain digest-bound host references, not duplicated into the archive;
reconstruction requires that original host. The
[reconstruction checker](baseline-absent-targets/verify.py) verifies every archive
part/entry, checks per-item results and retained native records, and decodes each
comparison image. Its format/lint/strict-type checks and original-host
reconstruction pass. Re-run with:

```sh
uv run --locked python docs/acceptance/baseline-absent-targets/verify.py
```

This establishes the observed ordinary-default configuration/font snapshot's
copy/cache/render lifetime and safe absence handling. Native libraries, scan-only
templates, Poppler CMap/profile/codec/environment accounting and independent
arbitrary-font/glyph/full-page truth remain unfinished or explicitly unavailable;
`runtime_resources_verified` remains false. Complete import-to-project storage,
matched packets/receipts/actions/replay/acknowledgement, exact export and all
original public/native/fault/six-case/compatibility/browser-reuse checks remain
with the same live F. No technical or visual finite handoff is accepted here.

## Exact RGB asset storage — 2026-10-14 continuation

The private `bookscan.assets.Assets` operation now publishes and reads exact RGB
PNGs under caller-held verified writer ownership. Provisioning reserves a new
assets directory and retains its device/inode. Every use checks that identity and
the writer, so closed/foreign ownership or a missing/replaced/symlinked directory
cannot redirect operations. Asset identity includes dimensions and decoded RGB;
checkpoint references must additionally bind the complete PNG digest and length.
Duplicate publication verifies/reuses the existing bytes without replacement.

Publication encodes losslessly, checks exact decoded pixels, writes an owned
private file, then independently reads/decodes/digests that staged file before a
no-clobber link. Reads require a regular single-link file and exact encoded and
decoded identities, mode and dimensions. Nanosecond modification/change metadata
and pathname/descriptor identity are checked around reading; normal access-time
updates are permitted. Cleanup touches only this invocation's exact name/inode,
and cleanup failure adds a note to an already selected interruption/error.
No file enumeration or asset publication creates accepted state. A post-link
SIGKILL can leave a complete unreferenced PNG and its private hard link; this
reader refuses that orphan, and performs no automatic promotion or cleanup.
The future checkpoint owner must verify all saved references before mutation.

Thirty construction tests cover exact pixels, every byte value in each RGB
channel, duplicate reuse, dimension identity, corrupt/missing/aliased/FIFO assets,
forged references, wrong decoded truth despite matching encoded identity,
replaced directories, closed/busy ownership, pre/post-link interruptions, cleanup
failure and wrong staged disk bytes. The initial 26 cases failed on the missing
boundary. Three later controls exposed and then rejected access-time misclassification,
post-link-only disk validation and interruption replacement by cleanup failure.
The all-channel companion uses declared native samples rather than renderer truth.

Reproduce supplemental real Mac process observations in an unused directory:

```sh
task --exit-code process:asset-acceptance ARTIFACTS=/tmp/NEW-ASSET-READING
# Optional independently installed locked wheel interpreter; preserve its venv spelling.
task --exit-code process:asset-acceptance ARTIFACTS=/tmp/NEW-WHEEL-READING PYTHON=/path/to/venv/bin/python
uv run --locked python docs/acceptance/baseline-rgb-assets/verify.py
```

The test adapter launches the actual product module in an observed writer process,
with barriers immediately before/after the real link. Both phases exercise normal
release, SIGINT/130, SIGTERM/143 and SIGKILL/-9, complete/absent PNG visibility,
exact pixels and immediate lock reacquisition after reap. Caught signals clean the
owned private name; kills retain it. No checkpoint exists in any case. These are
private-operation supplements, not completed public finite command/checkpoint,
packet or export acceptance. The runner fixed two exploratory harness failures:
realpath on venv Python selected its dependency-free base; closing stdin before
signal termination raced barrier EOF. Final runs preserve the interpreter path
and wait for termination before closing stdin.

The frozen measurement retains 26,504 unchanged declared read subjects. Both full
`process:check`/`prepare:check` gates pass format/lint/strict types and identical
1,304 unit identities, preserving all 1,274 predecessors plus 30 asset cases.
Source A/B and independently installed locked wheel A/B agree itemwise on all
eight native asset cases. Full package/wheel/installed membership and bytes agree;
locked runtime requirements are unchanged. Staff passes. Synthetic preparation
A/B agree with each other and the preceding reading on all nine cases and 38
installed-writer barrier/signal/kill outcomes. Wrong unit identity, asset visibility
and preparation-case record controls refuse. Preparation implementation, runtime
dependencies, real fixtures and frozen experiments are unchanged; this isolated
new module affects no real preparation comparison subject.

[Retained reading](baseline-rgb-assets/index.json.gz) binds 1,061 logical entries
in three digest-checked ZIP parts, each at most 900,000 bytes. It includes raw
paired results, JUnit, construction failures, exploratory diagnostics, native
projects/PNGs, preparation reports/fixtures, the wheel/full product bytes, test
instruments and frozen before/after manifests. Host tool/font/standard-library
subjects remain digest/identity references, not all copied bytes. The
[standalone reader](baseline-rgb-assets/verify.py) reconstructs every part/blob,
unit outcome, native RGB case, predecessor preparation record and product/wheel
membership without requiring the old temporary output paths. Reconstruction and
reader format/lint/strict types pass. This is durable bounded asset evidence;
it is not a frozen complete compatible saved-project fixture.

Next couple the source snapshot, complete assessed occurrence records/physical
mappings and these asset references to private header/capability validation,
immutable checkpoints and atomic current-pointer transactions, with source-loss
verified status/resume and actual pre/post-checkpoint interruption tests. Complete
renderer template/CMap/profile/native/codec/environment accounting and remaining
configuration semantics before accepted import; arbitrary glyph/full-page,
complex-real and Type3 fidelity/calibration stay precisely unavailable until their
independent truth exists. All original packet/native/global-refresh, Q1–Q3 action/
replay/inspection/selection acknowledgement, exact export/report/publication,
installed isolation/migration/six-case/resource, frozen-project compatibility and
five browser-reuse properties remain here. F/k53/k47/B/k54 remain live; k28 retains
every missing real truth/reaction/remedy and full-default/nonrigid obligation.

## Saved RGB reference reader — 2026-10-14 continuation

`RGBAsset.record()` now emits a complete private `BookScanBuilderRGBAsset`
version-1 record; `from_record()` validates its exact required fields without
coercion, file reads or repair. Dimensions, decoded RGB identity and encoded PNG
length/digest all remain required. Missing/unknown fields, incompatible versions,
boolean/fractional/coerced sizes, invalid digest types and inconsistent identity
return `INVALID_PROJECT`/3. Direct forged references receive the same domain error.
Record arrays are detached from immutable references. Parsing a record alone
verifies no image bytes: the existing ownership-bound `Assets.read()` still checks
complete encoded bytes and exact decoded RGB. The eventual checkpoint JSON reader
must reject duplicate keys before this object boundary. No optional nonsemantic
reference fields are currently declared.

Fifty new constructions first fail against the preceding implementation, then
pass alongside its thirty asset cases. A real asset is published, its reference
JSON round-tripped and its pixels read under reopened ownership. The actual
native worker/acceptance reader now use this record boundary instead of field
casts, exercising both sides of publication with release/INT/TERM/KILL and
immediate kernel reacquisition. These remain private supplemental operations.

The frozen paired reading preserves 27,035 declared read subjects and all 1,304
preceding unit identities, with fifty additions. Both complete product gates
pass format/lint/strict types and identical 1,354 outcomes. Source A/B and a
separately installed locked wheel A/B agree itemwise for eight native cases each;
removing only the new explicit reference format/version fields reproduces the
preceding asset records. Full product/wheel/installed bytes and membership agree.
The four runtime distributions match the actual locked hash-verified export.
An initial wheel setup guessed older transitive versions; that reading was stopped,
discarded and retained as diagnostic before the corrected frozen measurement.
Staff passes; synthetic preparation A/B match each other and the preceding nine
cases and 38 installed writer/barrier/signal/kill outcomes. Wrong unit identity,
asset visibility and preparation-case controls refuse. Preparation implementation,
locked dependencies, real fixtures and frozen experiments retain their bytes;
this reference-only change affects no real preparation comparison subject.

[Retained evidence](baseline-asset-records/index.json.gz) binds 1,122 logical
entries across five ZIP parts, each at most 900,000 bytes. It retains raw paired
JUnit/native/preparation outputs, first-failure tests, discarded diagnostics,
complete product/wheel bytes, instruments and frozen before/after manifests.
Host subjects remain explicit digest/identity references. The
[standalone checker](baseline-asset-records/verify.py) verifies all archive parts/
blobs, per-item predecessor/current results, complete package membership and
native RGB samples. Reconstruction and its format/lint/strict types pass.

```sh
uv run --locked python docs/acceptance/baseline-asset-records/verify.py
task --exit-code process:asset-acceptance ARTIFACTS=/tmp/NEW-ASSET-REFERENCE-READING
```

This supplies a strict reference boundary for the upcoming saved-project reader.
It commits no checkpoint and delivers no public finite review/resume/export.
Next integrate source/assessed-occurrence/physical records and these references
with header/capabilities, immutable checkpoints/current-pointer transactions,
verified source-loss status/resume and actual checkpoint faults. Renderer templates,
CMaps/profiles/native/codecs/environment/configuration accounting and independent
arbitrary-font/glyph/full-page truth remain unfinished. All original matched/
native/global-refresh packets, Q1–Q3 actions/replay/inspection/acknowledgement,
exact export/report/publication, public isolation/migration/six-case/resource,
compatible-project and five B reuse obligations remain in the same live F.
F/k53/k47/B/k54 remain live; k28 retains every missing real truth/reaction/remedy
and full-default/nonrigid obligation. No technical or visual handoff is accepted.


2026-10-14 — strict serialized private records (F remains live).

`bookscan.records.decode` now reads one UTF-8 object record and rejects duplicate
keys (including escaped aliases and nested objects), malformed/trailing JSON,
nonfinite constants/float overflow and unpaired Unicode surrogates before saved
meaning is interpreted. `RGBAsset.from_json` uses it and then retains all existing
version/field/dimension/digest checks; the actual native writer/reader exercises
serialized references before decoded asset reads. This is an internal checkpoint
input boundary, not an accepted project or public finite review/export handoff.

The frozen reading retained at [baseline-json-records](baseline-json-records/index.json.gz)
is reconstructed by `uv run --locked python docs/acceptance/baseline-json-records/verify.py`.
All 15,652 declared host/product/test/contract/instrument subjects remain unchanged
before/after. Both `task process:check` gates pass formatting/lint/strict types and
identical 1,395 individual unit outcomes: every preceding 1,354 outcome plus 41 new
constructions. Source and separately installed locked wheel A/B each pass eight
actual Mac asset-link writer/PID/signal/kill/reap/reopen cases and agree with the
predecessor item by item. Wheel/product/installed product membership and bytes
agree; installed runtime versions are lxml6.1.3/packaging26.3/pikepdf10.16.0/Pillow12.3.0.
`geometry:staff-check` passes. Two synthetic preparation acceptance runs preserve
all nine preceding cases and 38 installed writer interruption/visibility outcomes.
Preparation sources/fixtures and dependency locks did not change; no affected
real-preparation subject was changed or new real comparison claimed.

Seven separately frozen mutation controls show duplicate/escaped/nested-key,
nonfinite/overflow and Unicode checks rejecting their deliberately wrong inputs;
removing only each relevant guard accepts that wrong input while the unrelated
ordered-record control stays green. Repacked wrong unit outcome, native visibility
and preparation outcome records are rejected by the standalone evidence reader.
The archive binds 1,197 entries across six parts (5,075,982 compressed bytes, each
part at most 900,000 bytes), including raw red/green/paired records, discarded gate/
first-green diagnostics, subjects, wheel, product and instruments. Host binary/
stdlib/dependency subjects remain explicit identity/digest references.

The first green test mistakenly expected valid deeply nested JSON to hit the
installed decoder's recursion limit. Direct Python 3.12 observation disproved that
assumption; the final construction checks a deeply nested nonfinite value instead.
No arbitrary depth limit was introduced. The first complete gate stopped on an
unformatted added test; it is uncredited, retained and followed by the complete
restarted frozen run. The checker itself was formatted/type-checked after primary
measurement and changes no measured product or test byte.

Next: complete header/capability/source/assessed occurrence/physical mapping
records and RGB references in immutable checkpoints with atomic current-pointer
commit, then verified source-loss status/resume and actual checkpoint faults.
Use strict JSON decoding before semantic/version validation. Renderer resource/
configuration closure and independent arbitrary-glyph/complex-page truth remain
unfinished before accepted import. Matched/native/global-refresh packets, Q1–Q3
review/replay/inspection/selection-union acknowledgement, exact image-only export/
report/no-clobber, compatible complete-project/B reuse, installed public/isolation/
migration/six-case/resource evidence remain this F's original obligations. Existing
missing real truth/reactions/remedies/full-default/nonrigid work remains k28's.
No leaf retirement, partial sealing, parent closure, public delivery, browser or
visual acceptance is supplied by this boundary.

## Immutable checkpoint transactions — 2026-10-14 continuation

The private checkpoint store now publishes complete content-addressed UTF-8
records and chooses one current checkpoint atomically under the caller's existing
writer lock. Each record carries strict format/version/project/capability identity,
monotonic checkpoint revision and its predecessor digest. Reads verify the entire
predecessor chain and call the required payload/asset verifier on every state.
Payload objects returned to callers are detached from saved bytes. Immutable
records and their assets survive a failed update; orphan enumeration supplies no
saved state. Unknown fields/capabilities/version, duplicate JSON keys, wrong
project/revision, missing/corrupt predecessors or referenced RGB are refused.

The current pointer is a relative digest-only symlink read without following
arbitrary targets. Initial creation cannot replace an occupied name; subsequent
updates replace the verified pointer, retaining predecessor records. Actual
macOS creation/rename/signal behavior is measured below. Checks reject replaced
checkpoint directories, invalid pointers and known private-pointer replacement;
this is cooperative writer ownership and identity verification, not exclusion
of an arbitrary external program racing every syscall. There is no power-loss
claim, orphan promotion, automatic repair or public rollback operation.

Caught handlers record signals. Only the pointer syscall/outcome assignment is
briefly deferred. Pre-commit interruption retains the preceding checkpoint;
post-commit SIGINT/SIGTERM still returns 130/143 with committed true. Genuine
post-commit descriptor cleanup failure retains that fact with a warning. Detected
post-commit directory/lock corruption returns INVALID_PROJECT/3 with committed
true. Cleanup preserves an already selected cancellation/error and touches only
known owned names. The storage primitive introduces no export or packet commit.

The corrected frozen reading passes both `task process:check` and
`task prepare:check`: format, lint, strict types and identical 1,449 unit
identities/outcomes. All 1,395 predecessor outcomes remain, plus 54 checkpoint
constructions. Two source and two separately installed locked-wheel runs each
observe forty actual writer-PID cases: initial/update transactions at assets-
complete, immutable-record-complete, pre-pointer, inside-pointer and post-pointer
boundaries, crossed with release/SIGINT/SIGTERM/SIGKILL. Exact exits, visibility,
commit/revision, unchanged known RGB, busy ownership and immediate post-reap
reacquisition agree itemwise. An inside-pointer signal occurs after the actual
native syscall while delivery is blocked, then returns the new committed state
with 130/143; kill/reap resumes that state without a retry record invented by the
adapter. These are actual installed private operations, not public create/status
acceptance or launcher-PID evidence.

Paired RGB-asset checks retain all eight predecessor cases per source/wheel run.
Paired staff checks pass. Paired synthetic preparation checks preserve all nine
cases and 38 installed writer/barrier/fault outcomes itemwise against their
predecessor. No preparation runtime/fixture/experiment changed; real preparation
subjects are unaffected. All 11,121 declared repository/interpreter/library/tool/
wheel/instrument/contract subjects retain before/after digest and identity.
The installed wheel contains exactly the frozen product members/bytes, with
locked lxml 6.1.3, packaging 26.3, pikepdf 10.16.0 and Pillow 12.3.0.

[Retained evidence](baseline-checkpoints/index.json.gz) binds raw unit/native/
preparation readings, all observed checkpoint/PNG bytes, source/test/contract/
wheel bytes and the frozen subject manifests. Host dependencies remain explicit
identity/digest references. First-red constructions, uncredited diagnostic 1 and
aborted diagnostic 2 and superseded diagnostic 3 remain distinguished from the corrected reading. The
[standalone reader](baseline-checkpoints/verify.py) verifies every archive blob,
unit/predecessor comparison, native pointer/history/pixel fact and wheel member;
its format/lint/strict types pass. Valid repacked wrong unit, checkpoint-commit
and preparation records are refused; control instruments, payload deltas and
refusal transcripts are retained, with their full scratch archives reconstructable
from the bound baseline blobs rather than duplicated here.

```sh
task process:checkpoint-acceptance ARTIFACTS='/tmp/NEW checkpoint reading'
task process:checkpoint-acceptance ARTIFACTS='/tmp/NEW installed reading' PYTHON='/path/to/locked-installed/python'
uv run --locked python docs/acceptance/baseline-checkpoints/verify.py
```

The required callback here verifies controlled RGB-reference payloads. Complete
source/assessed-occurrence/physical-mapping/native-sample semantics and bootstrap
header/directory-identity loading still need their responsible project operation;
this envelope is not a usable accepted import or the frozen complete predecessor
fixture for B. Public create/status/source-loss resume, receipt/actions/replay/
acknowledgement, whole native/global-refresh packets, exact export/report, additive
semantic upgrades and full public/isolation/six-case/resource acceptance remain
on live F. Existing renderer-resource and arbitrary glyph/complex-page truth
limitations remain; no checkpoint equality supplies source fidelity. k28 retains
all missing real truth/reactions/remedies and full-default/nonrigid work. F stays
in the same unsealed jj change; no retirement or parent closure is implied.

## Saved native header and restart boundary

The private [saved-header owner](../../src/bookscan/project_header.py) now supplies
the persisted project, writer-lock, header-file, RGB-directory and checkpoint-
directory identities needed by a restarted storage reader. It reads a strict
UTF-8 version-1 header before acquiring ownership, rechecks its exact bytes and
native identity under the lock, and uses the saved directory identities. It never
accepts newly statted replacement directories as the original stores. The header
records its own inode while private, so identical-byte replacement fails on fresh
resume as well. Complete header publication uses a no-clobber native link; it is
not a baseline checkpoint or accepted import.

`resume` requires the operation's semantic verifier for the current record and
every predecessor. Controlled tests verify full RGB references, note semantics,
missing pixels and corrupt history; header-only creates and orphans cannot resume
as saved state. Caller-held operations do not reacquire or close caller ownership.
Busy/aliases, foreign entries, private-name replacement, incompatible format/
capabilities, duplicate/nonfinite/invalid Unicode JSON, short writes, cancellation
and cleanup errors have observed constructions. Cleanup preserves the selected
failure and leaves foreign private replacements untouched. Native identity checks
and cooperative writer exclusion do not exclude arbitrary external syscall races,
make a power-loss promise or provide a manual recovery operation.

Both frozen complete gates pass with identical 1,506 unit outcomes: all 1,449
predecessors plus 57 saved-header constructions. The same 57 constructions pass
against the separately installed locked wheel twice. All 11,654 declared subject
bytes and native identities stay unchanged. The wheel contains exactly the frozen
product members and bytes; runtime requirements use the locked hashes. Each of
two source and two installed-wheel readings observes forty header-backed writer
cases at the existing initial/update checkpoint boundaries, with actual INT/TERM/
KILL/reap, exact visibility/exit/revision/RGB and immediate ownership reacquisition.
All four original no-header checkpoint readings also preserve those forty
predecessor outcomes itemwise. These are installed private operation observations,
not public create/status or source-loss acceptance. Paired staff and synthetic
preparation preserve the nine cases and 38 installed preparation fault readings;
preparation/experiment/runtime/real-source subjects are unchanged.

[Retained evidence](baseline-header/index.json.gz) binds 3,254 entries in five
parts, including raw red/green, paired gates/wheel/native/preparation results,
original project/header/history/PNG files, product/test/contract bytes, the wheel
and frozen manifests/instruments. Host dependencies remain explicit identity/
digest references. The [standalone reader](baseline-header/verify.py) verifies
every blob and per-item outcome; valid repacked wrong-unit, wrong-header and
wrong-commit records refuse. [Control reconstruction](baseline-header/reconstruct-controls.py)
reproduces their exact archive/index bytes and refusal reasons from retained
deltas and ZIP metadata, without three duplicate full archives. Both readers
pass formatting, lint and strict types. Mode-zero preparation outputs were read
only for post-measurement retention with temporary owner-read permission restored;
the index records this capture action and the original mode/identity. They are
measurement outputs, never altered frozen read subjects.

```sh
task process:header-acceptance ARTIFACTS='/tmp/NEW header reading'
task process:header-acceptance ARTIFACTS='/tmp/NEW installed header reading' PYTHON='/path/to/locked-installed/python'
uv run --locked python docs/acceptance/baseline-header/verify.py
uv run --locked python docs/acceptance/baseline-header/reconstruct-controls.py
```

This supplies native bootstrap identity loading; complete source/assessed-
occurrence/physical-mapping/native-sample semantics remain the next required
project operation. No complete accepted import, compatible complete predecessor,
additive semantic upgrade, public command, viewer/native/global-refresh result,
receipt/replay/acknowledgement, export/report, source-fidelity or six-case outcome
is claimed here. All original F/B obligations and k28's missing truth/reactions/
remedies/full-default/nonrigid work remain. F stays live in its original unsealed
jj change, without retirement or parent closure.

## Verified saved source and complete source-page meaning

`source_record` now records and verifies the fixed project `source.pdf` under the
caller's existing writer. Its closed private version-1 record retains original
identity/path as descriptive provenance, exact snapshot identity/digest, document
version and the complete ordered source roster: IDs, all five boxes, Rotate,
UserUnit, independent pixel/physical mapping, effective extent and advisory hints.
Resume opens only the saved snapshot using nonblocking/no-follow native gates,
checks regular type/single link/native identity/bytes before and after the existing
pinned static inspection, then compares every saved field with the rederived
source meaning. JSON-type differences, unknown fields/version, wrong source/order/
box/unit/mapping/hint, replaced/missing/aliased source and lost ownership refuse
without repair or mutation. Source identity is no independent composition-fidelity
or geometry-correction verdict. Original disappearance requires no source read.

The [retained source evidence](baseline-source/index.json.gz) reconstructs 4,570
entries in five parts, each at most 900,000 bytes (4,374,729 compressed bytes).
It includes the first 54 failing constructions, focused temporal/cleanup/static-
gate/alias controls, frozen source/tests/contracts/wheel/instruments, complete
paired outcomes and actual native histories/assets. The first archive-reader
attempt exposed /var versus resolved /private/var spellings in the saved subject
index; the reader now resolves that recorded spelling alias without current host
reads. No measured product/input changed. Two early alias-test assertions had
compared a source PDF path with its project directory; those instrument errors
were corrected before the credited reading. Output-only mode-zero preparation
files temporarily gained owner-read permission during capture, restored immediately;
the index explicitly records these output captures. Frozen inputs stayed unchanged.

Both complete `prepare:check` readings preserve all 1,506 predecessor unit outcomes
and add the same 64 source-record constructions, giving 1,570 per reading. Two
installed-wheel focused readings preserve those same 64. All 11,663 declared
read subjects remain unchanged. For source-backed, header-only and original
checkpoint modes, source A/B and installed locked-wheel A/B each retain forty
actual-writer PID cases: INT/TERM/KILL/reap, pointer visibility/commit/revision,
exact RGB, death/reacquisition and complete predecessor verification. The new
source mode deletes its test original before barriers and verifies every saved
predecessor's source as well as RGB on restart. These controlled states are not
complete assessed projects. Existing header/checkpoint per-case outcomes agree
with their predecessor readings. Paired staff and synthetic preparation retain
nine cases and all 38 installed preparation fault records itemwise. Every wheel/
installed product member matches frozen source bytes; runtime packages were
installed from locked hash-checked requirements. Host dependencies remain digest/
identity references rather than portable archived executables.

Reproduce the private writer boundary with an unused destination:

```sh
task process:source-acceptance ARTIFACTS=/tmp/NEW-SOURCE-CHECKS
uv run --locked python docs/acceptance/baseline-source/verify.py
uv run --locked python docs/acceptance/baseline-source/controls.py
```

The standalone reader verifies every blob and bound per-item unit, source/PNG,
checkpoint/history, native, preparation and wheel fact. Three valid repacked
wrong unit/source-geometry/commit records refuse; the construction script and
raw refusal transcripts are retained beside it. The source reader and both
evidence scripts pass format/lint/strict types. The full installed public source-
loss and denied-collection-read handoff, complete assessed-occurrence/native-
sample/review semantic verifier, additive semantic upgrades and compatible complete
project are still unfinished. This source component alone grants no accepted
import. Matched native/global-refresh packets, Q1–Q3 actions/replay/inspection/ack,
exact export/report/no-clobber and all remaining public/fidelity/six-case/B checks
remain with live F; every original k28 missing-truth/reaction/remedy obligation
remains. No retirement, parent closure or new product acceptance is claimed.

## Checked saved advisory analysis

The existing assessment-v1 analysis object now has a strict reader in
`analysis_record`. It checks the exact Leptonica/settings, closed fields, emitted
JSON types, finite-or-null measurements, diagnostic text and one complete region
at the independently supplied baseline size. It rederives nonfinite markers,
availability, nonzero and range-edge reasons from the saved measurements. Unknown
or contradictory meaning fails INVALID_PROJECT/3; it never becomes a new
suggestion or implied acceptance. No helper, renderer or setup runs while reading.
Assessed serialization uses the same guard before emitting saved analysis.

The [retained evidence](baseline-analysis-record/index.json.gz) binds 1,224 entries
in six parts of at most 900,000 bytes (4,721,046 compressed bytes). It retains
raw first-red/green, the observed serializer-bypass failure, a rejected lint-gate
reading, frozen inputs/instruments, installed-wheel bytes, native source snapshots
and paired per-item observations. The first 95 constructions failed on the absent
reader. A history assertion initially assumed oldest-first verification; the actual
loader verifies current then predecessors, and the corrected construction rejects
a hash-valid invalid predecessor even with a valid current record. An overlong
embedded test-script line stopped the first frozen attempt before tests; that
reading is uncredited. Those test-instrument repairs preceded the credited run.

Both complete checks passed 1,667 tests, preserving every one of the 1,570 earlier
outcomes and adding 97. Both installed locked-wheel readings passed the same
118 focused analysis/assessment cases. Four actual native readings (source/wheel,
each twice) agree on every one of seven occurrence records, including the native
blank zero-confidence and sweep-edge sentinels, duplicate/order, hints/geometry
and retained RGB. The native runner itself also compares repeated source-loss
assessment itemwise. Paired staff and synthetic preparation preserve all nine
cases and 38 actual preparation fault outcomes against the preceding reading.
All 17,227 declared code/library/tool/fixture/contract/instrument read subjects
stayed unchanged; each wheel/installed product member matches frozen source.
Host dependencies are identity/digest references, not portable archived binaries.
Post-measurement capture temporarily enabled owner-read on two output-only
mode-zero preparation files and restored their modes; the index records it.

The [standalone reader](baseline-analysis-record/verify.py) reconstructs blob
digests, frozen subjects, per-item unit/predecessor/native/preparation facts and
wheel members. [Controls](baseline-analysis-record/controls.py) repack valid
archives with all matching repeated observations and indexes updated: wrong unit
failure, wrong whole-image region and false blank availability still refuse the
semantic checks. Raw refusals are retained in controls-result.json. The evidence
scripts pass formatting, lint and strict types. An actual post-import denied-read
control confirms that valid saved-analysis reading needs no native launch or file
content read; corrupt data refuses under that same boundary. A controlled saved
RGB/checkpoint history exercises the reader without claiming a complete project.

```sh
task process:analysis-record-check
uv run --locked python docs/acceptance/baseline-analysis-record/verify.py
uv run --locked python docs/acceptance/baseline-analysis-record/controls.py
```

Next bind every assessed occurrence, render/resource and native sample/profile/RGB
reference to the verified source and physical mapping in the full checkpoint
semantic verifier, then deliver public create/status/source-loss resume and
complete semantic upgrade compatibility. This analysis reader is a component of
that operation; it neither authenticates the source/image association alone nor
supplies accuracy, source fidelity, inspection or acceptance. Whole matched/native/
global-refresh packets, Q1–Q3 actions/durable replay/scoped inspection/selection-union
acknowledgement, exact image-only export/report/no-clobber and actual installed
public/isolation/six-case/resource/B reuse checks remain live in F. k28 retains
all named missing truth/reactions/remedies and complete-default/nonrigid work.
No leaf retires, parent closes or partial milestone is sealed here.

## Verified occurrence core associations

`occurrence_record.verify_cores` now checks the complete ordered occurrence and
baseline-reference roster under caller-held verified ownership. It restores the
fixed saved source, compares each stable ID/source position/digest/box/Rotate/
UserUnit/physical mapping/advisory hint with that source, reads the full lossless
RGB asset and binds its decoded digest/dimensions to the saved occurrence, then
restores the saved whole-baseline analysis. Initial inspection, applied-estimate,
fidelity and retention flags cannot silently acquire acceptance. It checks source
identity again after the asset reads and returns only verified core fields.
Render/resource/native-sample/profile/triage and review/acknowledgement semantics
remain outside this component; its returned object exposes none of those payloads.
Consistent saved associations supply no independent proof of source rendering or
composition fidelity and no complete accepted project.

The [retained evidence](baseline-occurrence-core/index.json.gz) binds 2,359 entries
in five parts of at most 900,000 bytes (4,114,169 compressed bytes). It contains
raw red/green, the observed cyclic-input timeout and source-comparison bypass,
paired full/focused/native/preparation readings, real source/PNG/checkpoint-history
fixtures, frozen product/tests/contracts/instruments and the locked installed
wheel. Host libraries/tools and preceding evidence corpora remain digest/identity
references. Two output-only mode-zero preparation files temporarily gained owner-
read permission for retention, with the original modes restored and indexed.
Frozen read subjects were untouched.

Both `prepare:check` runs passed 1,718 tests, preserving every one of the 1,667
predecessor outcomes and adding the same 51 core constructions. Both installed-
wheel runs passed the same 270 core/source/analysis/RGB-reference checks. All
16,697 declared read subjects stayed unchanged. Source/wheel native assessment
readings, each twice, preserve every one of seven occurrence records; paired staff
checks and synthetic preparation preserve nine cases and all 38 installed writer
fault outcomes itemwise against the prior reading. The new root task passes.
Every installed product/wheel member agrees with frozen source bytes. No affected
real preparation subject changed, so no new real preparation comparison is claimed.

The first red run required a corrected test-module import before 49 expected
missing-reader failures. The malformed-history construction initially failed
during writing because the existing checkpoint writer already verifies predecessors;
its deliberately inadequate writer now stores a valid current core above the
hash-valid bad predecessor, which real resume rejects. A new bounded subprocess
construction exposed a cyclic direct Python value hanging in type traversal.
Serialization now rejects cycles before traversal, without accepting tuple/key/
boolean/numeric coercions. Those corrections preceded the credited frozen runs.

The [standalone reader](baseline-occurrence-core/verify.py) reconstructs every
blob, per-item reading, measured retained repository byte, wheel member and
independent small PNG/history facts. [Coherent controls](baseline-occurrence-core/controls.py)
repack valid archives with updated indexes and related observations: wrong unit
outcomes, wrong physical mapping and the missing corrupted-predecessor control
all refuse semantically. Their raw refusals are in controls-result.json. The
reader/control scripts pass format/lint/strict types. Early retention attempts
ran the reader before packing had completed and copied old evidence corpora;
neither was credited. The final bounded archive was read only after its writer
completed. Control-script repairs corrected a pytest class-name prefix and the
expected named unit refusal; no measured product changed.

```sh
task process:occurrence-core-check
uv run --locked python docs/acceptance/baseline-occurrence-core/verify.py
uv run --locked python docs/acceptance/baseline-occurrence-core/controls.py
```

Next complete the saved render/resource/native-sample/profile/triage and review
readers, integrating this core binding into the full checkpoint verifier. Public
create/status/source-loss resume, complete semantic additive upgrades and compatible
complete predecessor remain unfinished. All matched native/global-refresh packets,
Q1–Q3 authentic actions/durable replay/inspection/selection-union acknowledgement,
exact export/report/no-clobber and installed public/isolation/six-case/resource/B
reuse obligations remain in F. k28 retains all missing real truth/reactions/remedies
and complete-default/nonrigid work. F stays live in its original open jj change;
no retirement, partial sealing or parent closure occurs.

## Checked initial triage records

`triage_record.restore` checks the initial reason roster against already checked
page geometry, advisory analysis, native inventory and decoder diagnostics. It
requires exact reason order, concern details, Q1 decision domains, strict JSON
arrays/text and the initial `baseline-retained/unresolved` disposition. Dropped
orientation/fidelity/extent/decoder concerns, invented reasons, changed placement
paths and claimed initial acceptance fail with `INVALID_PROJECT`/3. Later review
dispositions remain separate. The existing derivation and `Reason` now live with
this reader; `AssessedPage.to_dict` also refuses inconsistent in-memory reasons.
This preserves the emitted assessment meaning and introduces no new format or
capability. It does not verify native/resource inputs, implement a review action,
establish a complete accepted project or grant a source-fidelity verdict.

The [retained evidence](baseline-triage-record/index.json.gz) contains 1,751 entries
in seven parts of at most 900,000 bytes (6,182,559 compressed bytes). It retains
raw first-red/green observations, paired full/focused/native/preparation readings,
real source/checkpoint/PNG fixtures, measured source/tests/contracts/instruments,
the locked wheel and isolated mutation subjects/results. Host dependencies and
older corpora remain digest references. Two output-only mode-zero preparation
captures temporarily gained owner-read permission for retention and had their
original modes restored; capture-metadata.json records them. No frozen read
subject was changed by retention.

Both full `prepare:check` runs pass all 1,760 identical unit outcomes, preserving
all 1,718 predecessor outcomes and adding the same 42 triage cases. Both installed
locked-wheel runs pass the same 160 triage/assessment/analysis checks. All 16,711
declared read subjects retain exact bytes and recorded metadata across the run.
Four actual native assessment readings (source/wheel, each twice) agree on every
seven-occurrence record and match the preceding occurrence-core reading exactly.
Paired staff checks and synthetic preparation retain four staff outcomes, nine
preparation cases and all 38 actual writer fault outcomes itemwise. The new root
task runs twice; wheel and installed package members match measured source bytes.
No affected real preparation subject changed, so no new real comparison is claimed.

The first 40 constructions failed on the missing reader. Two further constructions
check good history with native launches denied and pure reads with file opens
denied. A real hash-valid bad predecessor beneath a good current checkpoint is
refused. Before the frozen readings, strict types identified a test's indefinite
matrix tuple annotation and an unnecessary cast; both were corrected. Three
isolated product mutations then fail only their intended checks: weakened decision
domains (three failures, 39 unrelated passes), weakened detail binding (two failures,
40 unrelated passes), and bypassed serializer validation (one failure, 41 unrelated
passes). Every mutation runs a separately identified copied package.

The [standalone reader](baseline-triage-record/verify.py) reconstructs all archive
entries, checks itemwise reruns/predecessor outcomes, measured repository bytes,
wheel members, native limitations/Q1 domains and actual preparation writer PIDs.
[Coherently repacked controls](baseline-triage-record/controls.py) update archive
identities and corresponding native ledgers together; missing orientation still
fails the independent limitation check. Removing a domain disproof fails its
exact mutation-outcome check. Raw refusals are in controls-result.json. Both
evidence scripts pass format/lint/strict types.

```sh
task process:triage-record-check
uv run --locked python docs/acceptance/baseline-triage-record/verify.py
uv run --locked python docs/acceptance/baseline-triage-record/controls.py
```

Next verify saved render/resource/native-sample/profile semantics, then compose
the full checkpoint verifier with core binding and this triage reader. Those
inputs remain unchecked by this component; `verify_cores` still returns only its
verified core fields. Full review/replay/acknowledgement semantics and installed
create/status/source-loss resume, matched native/global-refresh packets, authentic
Q1–Q3 actions/inspection/selection-union acknowledgement, exact export/report/
no-clobber, public/isolation/migration/six-case/resource/compatibility/B reuse
remain unfinished in F. k28 retains every missing real truth/reaction/remedy and
full-default/nonrigid obligation. The same F change remains live and unsealed;
no retirement, partial sealing or parent closure occurs.


## Saved full-MediaBox rendering policy — 2026-10-14

The pure `render_record.restore` component binds saved command tokens to an
already checked source page, snapshot path and historical renderer path. It
requires the exact source range, UserUnit-compensated 300-dpi density, complete
rotated MediaBox dimensions, lossless PNG and default antialias settings. It
preserves decoder diagnostics as exact UTF-8, including valid control whitespace.
It performs no file reads, native launch, build or lock acquisition and returns
only detached immutable command/diagnostic facts. Historical private output need
not exist and is never consumed. Optional resource-binding payloads are not
returned or established as semantically valid by this component. A policy match
cannot authenticate historical execution or prove RGB/source fidelity.

Thirty-eight real-source/literal/history constructions first failed on the missing
reader, then passed. A hash-valid wrong-density predecessor below a good current
checkpoint fails without native tools or mutation; good history works after
original-source loss. The actual seven-occurrence native assessment runner checks
every saved command and rejects wrong page, density, width, CropBox option and
source substitutions while unrelated construction facts stay green.

Both full `prepare:check` readings pass the same 1,798 units, retaining every 1,760
predecessor outcome and adding precisely the same 38. Paired locked installed-wheel
runs pass 74 render/reader/assessment cases; all package members equal the frozen
source and wheel bytes. Four actual native assessment readings (source and wheel,
twice) preserve the preceding seven-occurrence facts and agree on the five new
policy controls. Paired staff and synthetic preparation retain every per-item
case and all 38 actual preparation writer faults. The new root
`process:render-record-check` recipe passes twice. No affected real preparation
subject changed. All 16,714 declared read subjects retain identical bytes and
recorded native metadata across the complete measurement.

An isolated copied-package mutation removes only the saved-policy comparison.
The intended 14 policy/predecessor tests fail and 24 unrelated cases pass; product
source remains unchanged. The ordinary [retained evidence reader](baseline-render-record/verify.py)
reconstructs raw red/green/frozen/native/history/wheel/controls records from seven
bounded archive parts. [Coherent repacked controls](baseline-render-record/controls-result.json)
change all matching ledgers yet still reject wrong density and a removed native
control against independent literal requirements. Host dependencies and previous
corpora remain digest references. Output-only mode-zero preparation captures were
temporarily made owner-readable for retention and restored; no measured subject
changed. One initial packing attempt required a nonexistent export log; correcting
that retention-only input changed no measurement or product. Reconstruction and
reader formatting/lint/strict types pass.

Complete saved resource/native-sample/profile verification and the full checkpoint
semantic/review verifier remain unfinished. Public create/status/source-loss
resume, complete compatible-project upgrades, packets/actual native refresh,
Q1–Q3 authentic actions/replay/scoped inspection/acknowledgement, exact image-only
export/report/publication and integrated public/isolation/migration/six-case/B
reuse checks remain owned by this live F. Every missing real truth/reaction/remedy
and full-default/nonrigid obligation remains on k28. F/k53/k47/B/k54 remain live;
this component supplies no complete project, preservation verdict or retirement.

## Saved named-resource inventory reader (continuation within F)

`resource_record.restore_named` reads immutable saved caller-named resource facts
without opening historical paths, launching native tools, recreating the secret
environment or returning an executable `ResourceBinding`. It checks strict JSON/
UTF-8/scalar types, opaque digest/native identity, present/absent file consistency,
sorted unique inventories, exact tree membership, symlink/dangling metadata and
native-ancestor cycles. Logical caller spellings remain unchanged. Optional
Fontconfig scope guards are not semantically checked or returned. Consistent
named facts do not prove historical use, complete runtime discovery, transient
identity, source fidelity or a complete accepted project.

The reader passes 68 constructions, including real inventory restoration after
historical files disappear and hash-valid predecessor verification below a good
current checkpoint without native launch or mutation. Initial missing-reader
failures and the observed ancestor-cycle acceptance failure are retained.
Both frozen full checks pass the same 1,866 tests, preserving all 1,798 earlier
outcomes and adding these 68. Paired installed-wheel checks pass 123 file/tree/
reader tests; every installed/wheel package member equals frozen source bytes.
Four source/wheel actual native directory-resource readings each exercise guarded
file/tree rendering and pass every saved-binding reader refusal control. Each
lane's opaque environment digest is stable on rerun; different interpreter
startup environments remain separately recorded. Four native assessments retain
every preceding seven-occurrence fact. Paired staff and synthetic preparation
retain their per-item outcomes and all 38 actual preparation writer faults.
The working `process:named-resource-record-check` recipe passes twice. All
16,742 declared subjects retain bytes/native metadata. No real preparation
subject changed.

Three isolated copied-package mutations fail only the intended runtime-claim
(three failures, 65 green), omitted-membership (one failure, 67 green) and ancestor-
cycle (one failure, 67 green) checks. Product and each mutation's read subjects
remain frozen. The [ordinary evidence reader](baseline-named-resource-record/verify.py)
reconstructs final raw runs, real file/tree/history fixtures, measured code/
contracts/instruments and locked wheel. [Coherent repack controls](baseline-named-resource-record/controls-result.json)
refuse a runtime-use upgrade and a deleted cycle disproof despite valid archive
digests and matching changed ledgers. Dependencies/older corpora remain digest
references. Two output-only mode-zero captures were made owner-readable during
retention and had modes restored; frozen subjects were untouched. The first
reading's final wheel comparison failed from an accidentally added ZipFile mode
argument; it is explicitly uncredited, retained as rejected instrument evidence,
and a corrected complete paired reading passed. No product/native API changed.

Fontconfig-specific saved scope/cache/snapshot semantics, native-sample/profile
readers and the full checkpoint semantic/review verifier remain unfinished.
Public create/status/source-loss resume, complete compatible projects/upgrades,
whole matched/native/global-refresh packets, Q1–Q3 authentic actions/durable replay/
scoped inspection/selection-union acknowledgement, exact image-only export/report/
no-clobber, actual public/isolation/migration/six-case/resource/B reuse acceptance
remain in the same live F. Historical renderer execution and complete native/
codec/glyph/complex-page fidelity truth remain unverified. k28 retains all missing
real truth/reaction/remedy and full-default/nonrigid obligations. F/k53/k47/B/k54
stay live; no complete finite handoff, retirement or partial sealing is claimed.

## Saved configuration-only scope guard reader — 2026-10-14 continuation

The saved named-resource binding now has a separate pure scope reader in
`fontconfig_record.restore_guard`. It validates the optional version-3 guard's
closed fields, exact configuration-only claim/limitation and complete sorted
scope; loaded configuration and parsed files must have present captured identities,
reported effective/config/template roots must have named tree inventories, and
parsed files cannot contradict overlapping tree entries. Absent optional roots
remain recorded absences. Logical versus effective sysroot paths and historical
alias/parent spellings survive. No guard returns None; guarded input returns a
detached immutable ConfiguredScope, never an executable guard or secret environment.
It opens no historical path and launches no native probe. Outer discovery,
cache construction/resource-snapshot and native-use/fidelity meanings remain
separate unverified components.

Fifty new constructions pass after observed failures: 46 initially fail on the
missing reader, and four more first demonstrate contradictory file/tree facts
and file/directory kind acceptance before the checks are added. Real captured
inputs can disappear before reading; hash-valid malformed predecessor guards
below good current checkpoints fail without native execution or checkpoint
mutation. Isolated copied-package omissions fail exactly two verification-claim,
four directory-binding and three parsed-consistency cases, with all other cases
green. Product source stays unchanged across these measurements.

The complete paired frozen reading has 16,745 unchanged named subjects. Both
prepare:check runs return 1,916 identical unit outcomes, retaining all 1,866
preceding outcomes plus these 50. Both locked installed-wheel checks pass the
same selected guard/named-resource/discovery roster, and all wheel/installed
product members equal measured source bytes. Four actual native Fontconfig runs
(source and installed wheel, twice) each yield eighteen saved guards across
ordinary default configuration, controlled/rediscovered inputs, six optional
include families before/after, and scan-only absent/parsed/include templates.
Each reader checks all eighteen identities and 72 isolating refusal controls,
with unrelated named-inventory checks green. Normalized configured scopes and
control outcomes agree itemwise in every lane. Opaque historical environments
are not reconstructed or treated as proof of native-use truth. Four native
assessment readings retain the preceding seven-occurrence facts. Paired staff
and synthetic preparation readings retain each case and all 38 actual writer
fault outcomes. New process:fontconfig-record-check passes twice. No real
preparation subject changed.

Ordinary retained evidence is [baseline-fontconfig-record](baseline-fontconfig-record/).
Its 1,773 archive entries include measured code/contracts/instruments, raw
red/green/native/history/mutation readings, frozen subjects and installed wheel,
in 27 parts no larger than 900,000 bytes (24,110,081 compressed bytes). Existing
host/library/tool dependencies and earlier corpora stay explicit digest references.
Standalone reconstruction passes; coherent repacks with changed valid digests
still refuse a native-use verification claim or a removed consistency disproof.
Evidence readers pass formatting/lint/strict types. The early probe expected
three guards but found eighteen; that uncredited cardinality assumption was
replaced by the complete explicit path roster before frozen readings. Two
output-only mode-zero captures temporarily gained owner-read for retention and
had modes restored; frozen subjects were untouched.

Reproduce the checks without the collection:

```sh
task process:fontconfig-record-check
uv run --locked python docs/acceptance/baseline-fontconfig-record/verify.py
uv run --locked python docs/acceptance/baseline-fontconfig-record/controls.py
```

Continue same live undescribed F change ryouonnvvlkzyyxmxrpqxnuqrysrqtvy over
03eb30abe1ae485696e5deec25bfb229a42ecf69. Next finish outer saved Fontconfig
cache/resource-snapshot/discovery and native-sample/profile readers, then bind
all checked source/core/render/resource/triage meanings in the full checkpoint
semantic verifier. Complete review/replay/inspection/selection-union acknowledgement,
public create/status/source-loss resume, transactional semantic upgrades and the
complete compatible predecessor remain unfinished. Every original matched/full/
native/global-refresh packet, actual-viewer Q1–Q3 action, exact export/report/
no-clobber/public/isolation/migration/six-case/resource/native-codec/glyph/complex-
page fidelity and B reuse obligation stays with F. k28 retains all missing real
truth/reaction/remedy/full-default/nonrigid work. F/k53/k47/B/k54 stay live;
no complete finite delivery, partial sealing, retirement or parent closure.

## Saved cache-construction reader continuation (2026-10-14)

`fontconfig_cache_record.restore_cache` now reads an optional saved construction
against its completed guarded named binding without reopening historical files,
resolving aliases, recreating an environment or executing native tools. It checks
closed JSON/method/initial-empty/root/isolated-command fields, matching scope guards
and fixed files/trees/cwd/native identity/opaque environment facts. Only recorded
complete cache trees are exempted from the fixed construction inventory. Logical
sysroot routes remain separate from effective roots; historical cache aliases can
be the sole named spelling. Immutable returned facts carry no runtime verifier.
This checks recorded consistency, not actual initial emptiness/execution/file use,
glyph fidelity, complete discovery or an accepted saved project. Outer discovery,
copied resource snapshots and native-sample/profile semantics remain unfinished.

[Ordinary retained evidence](baseline-fontconfig-cache-record/index.json.gz),
[standalone reconstruction](baseline-fontconfig-cache-record/verify.py) and
[coherent contradiction controls](baseline-fontconfig-cache-record/controls.py)
retain raw red/green/alias/history/omission/native/installed-wheel constructions.
The corpus contains 1,469 entries in fourteen parts no larger than 900,000 bytes
(12,491,427 compressed bytes). Host dependencies and earlier corpora stay digest
references; two output-only mode-zero captures gained temporary owner-read for
retention and had original modes restored. Frozen read subjects stayed unchanged.

Initial 49 tests fail because the reader is absent. A later alias-only positive
construction fails before the reader stops demanding an extra canonical named
spelling; 53 final constructions pass. Three copied-package omission controls
fail exactly the intended initial-empty/history (three), scope-guard (two) and
fixed-subject (eight) cases, leaving every other case green and measured product
untouched. Real deleted captures and hash-valid predecessor checks preserve source-
loss meaning without native launches or checkpoint mutation. New working root
`process:fontconfig-cache-record-check` passes 119 cases twice.

Both frozen full checks pass the same 1,969 unit outcomes, preserving all 1,916
predecessor outcomes and adding 53. Both locked installed-wheel checks pass the
same 119 selected outcomes; every wheel/installed product member equals frozen
source bytes. Four actual cache readings (source and wheel, twice) each retain two
completed cache records and fourteen saved-reader refusal controls. Their normalized
root/scope/command/outcome facts agree itemwise; interpreter/probe installation paths
are explicitly labelled per lane. Opaque environment digests include unique input
paths, remain in raw facts and are not falsely compared as identical contexts.
Native cache RGB/lifetime/refusal outcomes equal the historical actual construction
reading. Four native assessment readings preserve all seven occurrence facts.
Paired staff and synthetic preparation outcomes retain every case and all 38
actual writer fault outcomes. All 16,740 declared read subjects retain before/after
bytes/native metadata. No real preparation subject or pinned/native API changed.

The full checkpoint verifier still omits outer resource/discovery/snapshot/native
payload meanings. F's remaining saved readers/checkpoint/review/replay/inspection/
selection-union acknowledgement/public-create/status/source-loss-resume/view/action/
exact export/report/no-clobber/compatibility/migration/native-scale/global-refresh/
independent-fidelity/six-case/resource/B-reuse obligations remain with the same live
owner. k28 retains missing real truth/reactions/remedies and complete-default/nonrigid
work before appearance/final acceptance. F/k53/k47/B/k54 stay live. This continuation
supplies no complete finite delivery, partial seal, retirement or parent closure.


## Saved static native graph reader — 2026-10-14 continuation

`linked_record.restore` checks the saved native dependency graph against the saved
named-file inventory. It checks closed fields, supported recorded architecture,
OS build, canonical file/context paths and digests, exact captured file/architecture
header, load-kind/reference ordering, target/root reachability, complete OS reference
roster and matching present bound file digests. Cyclic graphs and every supported
load kind remain valid. The existing pure Mach-O command parser is shared as
`dependencies.load_commands`; the native collector's behavior is unchanged.

Returned facts are immutable and detached. The reader never opens, resolves or
executes historical resources or consults the current OS. Saved symlink/runpath
resolution remains historical descriptive information; the reader cannot attest
which native libraries/files dyld used. System shared-cache references retain the
saved OS build and explicitly claim no disk bytes. Static consistency proves no
configuration currency, complete runtime-resource discovery, glyph/source fidelity
or accepted project. Outer Fontconfig discovery/copied-snapshot and native-sample/
profile meanings, and the complete checkpoint semantic verifier, remain unfinished.

[Retained raw evidence](baseline-linked-record/index.json.gz),
[standalone reconstruction](baseline-linked-record/verify.py) and
[coherent contradiction controls](baseline-linked-record/controls.py) preserve
1,454 entries in fifteen parts of at most 900,000 bytes (12,867,845 compressed
bytes). Code/contracts/instruments, raw red/green/native/unit/mutation readings,
locked wheel and frozen subject rosters are retained; host dependencies remain
digest references. Reconstruction refuses digest-valid repacks inventing native-use
truth or removing the observed header disproof. Two output-only mode-zero captures
briefly gained owner-read for retention and had their modes restored; no frozen
measurement subject changed.

Initial tests failed 59 times on the absent reader. Three later disproofs exposed
same-prefix/wrong-architecture captured headers; the reader now checks their exact
identity. All 63 constructions pass, including dependency-free historical reads,
both saved architectures, all five load kinds, cycles, deleted actual captured
file subjects and both valid/invalid hash-valid checkpoint predecessors. Four
isolated copied-package omissions fail precisely five bound-digest cases, five
reference-sequence cases, one orphan-closure case and three header cases, leaving
all unrelated constructions green and the measured product untouched.

Both full `prepare:check` readings pass all 2,032 unit outcomes, preserving every
one of the preceding 1,969 cases. Both locked installed-wheel readings pass the
same 158 selected linked/dependency/named-resource cases. Every product member and
its bytes agree across source, wheel and installed package. The new
`process:linked-record-check` recipe passes twice. Four native cache readings each
retain two actual forty-file static graphs and fourteen refusal controls; their
complete reader facts agree itemwise with each other and the historical capture.
Native RGB/cache/lifetime/refusal outcomes remain identical to their predecessor.
Four native assessment readings preserve all seven preceding occurrence facts.
Paired staff and synthetic preparation retain all four/nine cases and all 38
observed actual installed writer faults. All 16,744 declared read subjects retain
before/after bytes and native metadata. Evidence-reader Ruff/format/strict types
also pass. No real preparation subject, native/framework API, public command
contract or required private capability changed.

This remains an internal continuation of complete finite owner F. There is no
public finite delivery, partial task seal, retirement or parent closure. Continue
with outer discovery/copied-resource-snapshot/native-sample/profile readers and
complete semantic checkpoint binding, then all original review/action/view/ack/
public create/status/source-loss resume/accepted exact export/compatibility/B-reuse/
native-codec/glyph/complex-page/global-refresh/six-case/resource obligations.
Missing real truth/reactions/remedies/full-default/nonrigid work stays with k28.

## Saved Fontconfig outer discovery and copied-resource consistency

The new `fontconfig_discovery_record.restore` couples the saved outer version,
configured scope, named guard, static linked graph, optional completed cache and
copied-resource snapshot. It checks source selection, mapped config/font/cache
routes, saved resolved overlap, unchanged host native/template subjects and
complete copied candidate inventories/byte confinement. Returned facts are
immutable and non-executable. Copied XML bytes may change; historical rewrite
correctness, native execution/file use, configuration currency and glyph fidelity
remain unverified. No complete accepted project is inferred.

The [retained evidence](baseline-discovery-record/README.md) reconstructs 1,981
named entries through twenty <=900,000-byte digest-addressed parts. Both full
checks pass the same 2,092 cases, retaining all 2,032 predecessors and adding 60;
paired installed locked-wheel checks pass the same 226 selected cases with whole
source/wheel/installed member equality. Native captures supply eight cache,
24 explicit/captured/XDG/dangling snapshot and twelve historical selected/ordinary-
default saved readings after cleanup. Their raw resource identities remain distinct
per capture; actual RGB/lifetime/refusal outcomes compare per case. Four native
assessments preserve all preceding seven-occurrence facts. Paired staff/synthetic
preparation preserve all cases and 38 actual installed writer faults. The new
root `process:fontconfig-discovery-record-check` recipe passes twice.

All 16,750 frozen subjects retain bytes/native metadata. Retained red stages
and four isolated copied-package omissions demonstrate the scope/history,
cache-library, copied-font-byte and host-route checks. Standalone archive
reconstruction, coherent false-native-use/removed-alias-disproof controls and a
valid-chunk/misaddressed-shared-blob control pass. Two output-only mode-zero
captures had owner-read added for retention and their modes restored. No pinned/
native API, capability, real preparation subject or public product contract changed.

Continue the same undescribed/unsealed F change
ryouonnvvlkzyyxmxrpqxnuqrysrqtvy over 03eb30abe1ae485696e5deec25bfb229a42ecf69.
Next finish saved native-sample/profile meanings, then couple source/core/render/
resource/triage and review meanings in the complete checkpoint semantic verifier;
`verify_cores` still omits outer payload meanings and no complete project is verified.
All original milestones 2–5 remain: public create/status/source-loss resume,
review/replay/inspection/selection-union acknowledgement, matched packets and actual
native/global-refresh/Q1–Q3 actions, B's five reusable seams, exact export/report/
no-clobber, compatible complete predecessor/additive upgrade, native-codec/glyph/
complex-page fidelity, public/isolation/migration and all six fixed-case/resource
acceptance. k28 retains every missing real truth/reaction/remedy and complete-
default/nonrigid question. F/k53/k47/B/k54 stay live; this advances F's approved
cadence without partial sealing, retirement, parent closure or teardown.

## Retained native samples and resolved colours — 2026-10-15

The assessment writer now retains resolved Indexed base/profile/palette/channel/
range references alongside all existing native sample fields. The pure reader
binds those facts to verified placement and exact retained blobs without decoding
a source again, launching native tools, converting colour or regenerating accepted
pixels. Simple legacy device/stencil records remain readable; older ICC/Indexed
construction records without required resolved facts are explicitly unsupported.
No completed compatible project was promised by those early captures. Opaque PDF
metadata is preserved; these checks do not reconstruct or prove its source meaning.

[Reproduction and ordinary retained evidence](baseline-native-sample-record/README.md)
include paired full/installed gates, native assessments, actual packed/profile
sample captures, inherited preparation/staff checks, complete frozen subjects and
isolating omission disproof. Both full gates pass 2,146 identical cases, preserving
all 2,092 predecessors and adding 54. Both installed-wheel gates pass the same
120 selected cases. Four actual native-record readings each cover sixteen
occurrences/fourteen samples/thirteen blobs, restore after both PDF paths disappear,
and refuse changed/missing bytes, wrong placement and false composition claims.
Four seven-occurrence native assessments preserve prior meanings apart from the
new explicit colour descriptors. Paired preparation retains every prior case and
all 38 actual writer signal/kill outcomes. All 16,743 declared subjects retain
bytes/native metadata; source/wheel/installed members are exact.

Four copied-package omissions fail only their named digest (two), placement (five),
grid (one) and colour-binding (two) cases while unrelated cases pass. The standalone
archive reader reconstructs every itemwise reading; coherent digest-valid repacks
inventing delivery or removing disproof fail. Malformed ICC profiles remain bytes,
not transform or fidelity acceptance. No public create/resume, full native blob
store/checkpoint semantics, packet/actions/ack/export, compatible completed fixture,
B reuse or six-case acceptance is supplied here. All remain on the same live F;
k28 keeps missing real truth/reactions/remedies and complete-default/nonrigid work.

## Transactional native blob continuation

The retained channel/profile/palette bytes now have a caller-owned transactional
store with strict v1 digest/length references, saved directory identity, verified
private files, no-clobber publication and exact-name cleanup. The source-loss
sample reader consumes these bytes after writer reopen; no profile conversion or
composition acceptance is inferred. Header/native inventory/resolution and complete
checkpoint integration remain unfinished.

[The ordinary native-blob evidence](baseline-native-blobs/README.md) retains paired
2,196-case full gates, 104 installed-wheel cases, sixteen actual installed writer
outcomes, four source-loss sample readings, four unchanged native assessments,
staff and synthetic preparation regressions. All 16,749 frozen subjects remained
unchanged. Four copied-package omissions expose the intended digest/length/
directory/cleanup failures while unrelated cases pass. Coherent evidence repacks
also refuse false delivery, removed disproof and wrong retained lengths.

This advances the same live, undescribed/unsealed F change, not a completed
project or public finite handoff. Every original milestone 2–5 review/public/view/
ack/export/compatibility/B/fidelity/six-case/resource obligation remains live;
k28 retains all missing real truth/reactions/remedies/full-default/nonrigid work.

## Saved native resolution and inventory (continuation within F)

The checked `native_inventory_record` reader/writer now binds the existing five
native fields to complete ordered placements and retained sample bytes. It checks
rational nonsingular matrices, intrinsic grids, finite ppi, exact above-300 flags,
complete/maximum summaries, unique placement paths, one sample per placement and
derived unavailable-sample concerns. A named missing composition oracle remains;
no source reopening, decoder/CMM launch or composition verdict is introduced.
Assessment uses this writer without changing saved field meanings. Owner-selected
cancellation retains its exact exception even across the nested sample reader's
OSError/KeyError missing-blob classification.

[Evidence and reproduction](baseline-native-inventory/README.md) retain the final
paired 2,263-case gate, 185-case installed checks, five isolated code omissions,
four actual source/wheel native-inventory readings and frozen subject ledgers.
Each native reading restores 31 occurrences/32 samples/20 blobs after both PDF
paths disappear and writer/store reopen, rejecting 124 altered inventories.
All earlier native assessment facts and synthetic preparation/staff outcomes,
including 38 actual installed preparation writer faults, agree item by item.
All 16,753 enumerated subjects remain unchanged across the corrected measurement.
Initial absent-module and later four cancellation failures are retained separately;
the earlier completed 63-case reading is preliminary, not the final measurement.

The standalone archive reader reconstructs per-item evidence and exact retained
native byte bindings without the temporary paths. Coherent digest-valid repacks
inventing delivery, removing cancellation disproof, changing native lengths/maxima
or erasing the missing oracle fail. External native/library bytes retain frozen
identity metadata rather than all being recopied; offline reconstruction makes no
historical execution or independent source-fidelity claim.

This is still an internal component on live baseline-finite-k63. Native-directory
header integration and the complete semantic checkpoint verifier remain next,
followed by every original review/replay/inspection/selection-union acknowledgement,
public create/status/source-loss resume, packet/native/global-refresh/Q1–Q3,
exact export/report/no-clobber, predecessor/additive-upgrade, B-reuse and full
public/native/isolation/fixed-case/resource obligation. k28 retains missing real
truth/reactions/remedies/full-default/nonrigid work. F, k53, k47, B and k54 stay
live; no complete finite delivery or scoped human inspection is inferred.

## Saved native directory identity (continuation within F)

The bootstrap header now binds the native-byte directory as well as RGB assets
and checkpoint storage. Resume supplies both saved-identity stores to the mandatory
semantic callback under one writer acquisition; existing RGB-only component
callers are adapted explicitly. The real constructed inventory runner now keeps
blob references inside each checkpoint and reopens using only the saved header.
Missing native identity has no fresh-stat fallback. No accepted complete project
or compatibility migration is inferred from this internal scaffold integration.

[Native-header evidence and reproduction](baseline-native-header/README.md)
retain paired 2,284-case full gates, 195-case installed-wheel checks, eighty actual
installed checkpoint-writer outcomes and four source-loss inventory readings.
All earlier 2,263 cases, native assessment meanings, staff and synthetic preparation
outcomes remain unchanged itemwise, including all 38 preparation writer cases.
The 21 new cases cover saved directory/context, replacement/type refusals,
predecessor-only bad bytes/meaning and selected cancellation. Two code omissions
each expose six targeted failures; six coherent evidence repacks also refuse.
All 19,482 frozen read subjects remained unchanged.

The complete semantic checkpoint verifier is next: bind source/core/render/resource/
triage/native meanings into one accepted initial-state schema before public create/
status/resume. Every original review/replay/inspection/acknowledgement, packet/
native/global-refresh/Q1–Q3, exact export/report/no-clobber, completed predecessor/
additive-upgrade, B-reuse and public/native/fidelity/six-case/resource/isolation
obligation stays on live F. k28 retains missing real truth/reactions/remedies and
complete-default/nonrigid work. No partial retirement, task commit or node closure.

## Combined assessed-occurrence reader continuation

The initial-occurrence reader now composes source/core/RGB/analysis, renderer,
optional named-resource/scope, native-inventory and triage checks under saved store
ownership, binds placements back to the private PDF and requires exact native-byte
closure. Its predecessor checks reject corrupt old payloads beneath a valid current
record. It returns immutable checked facts; historical decoder accuracy, outer
resource discovery, complete checkpoint/review schema and public create/resume
remain separate obligations. No accepted pixels are regenerated on restart.

Both frozen gates pass the same 2,351 outcomes, retaining 2,284 predecessors and
adding 67 constructions; installed-wheel runs retain those 67. Four actual native
source/wheel readings restore seven assessed pages after original loss and refuse
28 altered payloads. Four placement/eight triage omission failures demonstrate the
corresponding checks, with unrelated cases green. All 19,486 read subjects remain
unchanged; native inventory/assessment, forty installed checkpoint writer outcomes,
staff and synthetic preparation retain their itemwise meanings, including 38
preparation writer cases. No dependency/native API/real preparation subject changed.

Ordinary evidence, standalone reconstruction and four coherent false-corpus
controls are in [the assessed-record evidence](baseline-assessed-record/README.md).
The same live undescribed/unsealed F change remains; complete checkpoint schema,
public/review/replay/inspection/ack/packet/native-refresh/export/report/compatibility/
B/fidelity/six-case/resource/isolation work remains on F. k28 retains missing real
truth/reactions/remedies and complete-default/nonrigid obligations. No finite
handoff, retirement, parent closure or teardown follows from this component.

## Historical dependency metadata — 2026-10-15 continuation

The historical preflight reader checks helper input/build digests, complete saved
self-test meaning, pinned versions/settings/build flags and renderer/codec graph
associations against named-file identities without reopening historical paths.
Its immutable result now supplies a checked renderer context for the initial
occurrence reader. Real source-loss history tests reject corrupt predecessors
without checkpoint mutation and release writer ownership. This is metadata
consistency, not a complete checkpoint or public-create/resume handoff.

Both full gates pass the same 2,413 tests: all 2,351 predecessors plus 62 new
checks. Installed-wheel tests pass the same 62; actual source/wheel preflight
readings, each repeated, agree on saved helper/control/native-graph/codec meanings
and six refusal controls. All 19,566 frozen read subjects remain unchanged. Staff
and synthetic preparation outcomes remain itemwise equal, including 38 installed
preparation writer cases. No native API, dependency pin or real preparation
subject changed. Copied-package omissions expose two build and six association
failures with unrelated cases green. Product bytes were not modified by controls.

[Retained dependency evidence](baseline-dependency-record/README.md) includes 211
named entries, five bounded archive parts, raw outcome/native records, frozen
source/wheel identities and an offline consistency reader. Four coherently
rehashed false corpora refuse invented delivery, removed disproof, wrong build
and erased limitations. External tool/library bytes remain frozen references,
not all recopied. Matching metadata cannot attest native execution/resource use,
complete codec discovery or source fidelity; a helper hash cannot supply absent
retained binary bytes. Complete checkpoint/occurrence/discovery associations and
initial review/snapshot/retry/ack semantics remain next, before public create/
status/verified source-loss resume and every original finite delivery obligation.
No retirement, complete finite handoff or parent closure is claimed.

## Initial checkpoint envelope

The initial-state implementation binds saved historical dependency/Fontconfig
discovery/cache/copy records to every occurrence's complete render-resource
context, verified source/RGB/native/analysis/reasons and project identity. Initial
review/retry/ack records are empty; image/review/export-snapshot digests have
distinct meanings. Paired gates pass 2,464 identical outcomes (51 new), installed
wheel checks pass the same 51, and four actual native seven-page runs agree.
Source-loss/copied-resource-loss resume launches no native tools and preserves
exact RGB. Eight render-context and four discovery-inventory omission failures
prove the association checks matter. Staff/preparation results remain itemwise
equal, and all 14,483 frozen subjects retain digests/native metadata.

[Retained evidence and reproducible readers](baseline-initial-state/README.md)
include exact source/RGB/native/checkpoint/wheel bytes, raw ledgers and four
coherent false-corpus refusals. Historical consistency cannot attest execution,
actual resource use or source composition fidelity. Original native inode facts
are no completed compatible browser fixture. Helper binary-byte/path references
remain absent rather than fabricated. F remains live/unsealed: installed
create/status/resume, real review/replay/ack operations and all complete packet,
native/global-refresh, export, compatibility, browser-reuse, isolation/fidelity
and six-case/resource work still follow. No complete finite handoff is claimed.


## Installed finite invocation grammar — 2026-10-15 continuation

Q2 routing/help/lexical parsing now separates explicit preparation from finite
invocations. Unknown/reserved commands emit named v1 errors with null operation;
recognized argument errors keep their exact operation. Literal option values and
-- termination do not trigger help/JSON. Human help reads no input/project/cache
or PDF/RGB dependency. Real Mac denial and EPIPE checks pass; preparation retains
its original help/parser/result/publication meaning. Valid finite state operations
remain explicitly unavailable: no create/status/review/packet/ack/export success
or complete handoff is claimed.

Final paired gates agree on all 2,525 outcomes (all 2,464 predecessors plus 61),
source/wheel/installed bytes agree, and four installed runners agree on 22 cases.
Five isolated parsing/routing disproofs per copied mistake fail with unrelated
checks green; the old-entry copy fails 60 checks and preserves preparation.
Staff and synthetic preparation outcomes, including 38 writer observations,
remain itemwise equal. All 21,001 final frozen subjects retain digest/native facts.
[Retained evidence and reconstruction](baseline-finite-protocol/README.md) include
111 entries in five parts and four coherent false-corpus refusals. External
subject bytes remain identity references; consistency is no execution attestation,
completed finite review/export, native-display or source-fidelity claim. F remains
live/unsealed, with real create/status/source-loss resume and every original
review/view/ack/export/compatibility/B-reuse/fidelity/six-case obligation next.

## Installed initial-baseline status — 2026-10-15

`bookscan baseline status PROJECT` now verifies an initial saved baseline and
prints its complete ordered roster; `--json` returns CommandResult v1 with
`baseline.status`, `verified`/0, project/review/snapshot identities and the
separate checkpoint identity. The read commits nothing. Every occurrence keeps
its boxes, physical/pixel mapping, advisory provenance, analysis, native/resolution
facts, reason domains, unresolved retention and explicit empty inspection/
disposition scope. Blanks and duplicate occurrences remain distinct. Initial
retention supplies neither inspection, acknowledgement nor composition fidelity.
The opening historical note describes the original probe boundary; this section
records the current installed **status-only implementation boundary**.

```sh
uv run --locked bookscan baseline status 'Existing initial project' --json
task process:status -- 'Existing initial project'
task process:status-check
task process:status-acceptance ARTIFACTS='/existing/NEW' NATIVE_CACHE='/existing/cache'
```

Public create, status-with-output summary publication, page packets, review
receipt actions, acknowledgement and export remain unavailable. This is progress
within the same complete F owner, not a retired independently complete reviewer.
Nonempty review state remains unsupported until its real operations/readers land.
Status verifies every checkpoint predecessor and referenced source/RGB/native
asset under one writer acquisition; it does not reopen the original, execute
historical tools, rebuild pixels or inspect vanished copied resources. Dependency
preflight before import/serving remains a separate required operation obligation.
Missing/corrupt content and unknown format/capability give `INVALID_PROJECT`/3
without mutation, with compatible-status/new-import guidance and explicit loss of
review facts. Symlinked-parent/case aliases reach the same lock; busy is 4.

Both final full gates passed formatting, Ruff, strict types and the same 2,545
per-item tests: all 2,525 predecessor outcomes plus twenty status checks. Source
and built-wheel runs agree on all 81 status/invocation checks. All 45 source/
wheel/installed package members are byte-equal. The two actual native readings
retain the same seven construction-page RGB digests and six per-phase writer
outcomes, while keeping each project's source/checkpoint/review/snapshot/inode
identities separate. These constructions are not the six required real-book cases.

The actual installed writer was paused with ownership before and after initial
semantic verification. Its observed PID equals the signalled/reaped PID.
SIGINT/SIGTERM returned 130/143, `INTERRUPTED` and committed false; SIGKILL
returned -9 without a result. Every resumed status recovered the identical
saved roster and immediately reacquired ownership. All project bytes and native
metadata were unchanged. A success-serialization signal control exposed an early
cancellation check; the completed implementation checks cancellation after full
serialization, before fixing success for delivery. Later delivery signals keep
that selected result. Real EPIPE returns 5 for a read success and keeps a selected
error's exit; it emits no second record or Python shutdown/120.

Actual Mac read denial permits installed status with original source/copied
resource trees gone and collection reads denied. A read from the same boundary
fails as the observed control. Both `process:status` forwarding runs, protocol
acceptance, staff checks and synthetic preparation acceptance pass. Preparation's
per-page meanings and all 38 installed writer outcomes agree itemwise; no real
preparation or native API/pin subject changed. The protocol's no-I/O terminator
check uses the still-unimplemented summary form now that plain status legitimately
verifies saved bytes; standalone/literal flag grammar is unchanged.

Final measurement freezes 19,959 actual read subjects before and after, including
current repository/package/test/contract/recipe files, interpreter/dependency/
tool/library references, the built wheel, current native cache and the measurement
input manifests/instrument. Vanished ancestral temporary installations are not
inputs to this reading; its instrument excludes those old temporary references
and includes the current installations explicitly. No subject moved, no edit
occurred mid-run and one writer owned the reading. Skipping predecessor semantics
in a copied package fails its one coherent-bad-predecessor check with 80 other
checks green. Ignoring signals fails three checks with 78 others green. Original
product bytes remain unchanged by both controls.

Ordinary retained evidence is in
[baseline-finite-status/index.json](baseline-finite-status/index.json),
[verification.json.gz](baseline-finite-status/verification.json.gz) and
[seven archive parts](baseline-finite-status/index.json): 756 entries, 5,509,653 compressed
bytes, with raw ledgers/logs/public/native reports, measured source/wheel bytes,
subjects/instrument, saved source/RGB/native/header/checkpoint evidence and
construction truth. Preparation's intentionally unreadable private fault output
directories are omitted; their complete outcome XML/ledgers remain. Native
inode-bound projects are historical evidence, not a relocated compatible
completed-project fixture. External tool/library/interpreter bytes are identity
references, not all recopied binaries.

```sh
uv run --locked python docs/acceptance/baseline-finite-status/verify.py --reconstruct
uv run --locked python docs/acceptance/baseline-finite-status/controls.py
```

The [reader](baseline-finite-status/verify.py) verifies byte/outcome closure and
reconstructs the exact twenty archived status checks. The macOS /var alias first
caused pytest to omit module names; a canonical rootdir fixes exact per-item
identity. An initial unsorted passed-item comparison was corrected in this reader.
Neither correction changed product or measured subjects. Four coherently rehashed
[controls](baseline-finite-status/controls.json) refuse invented complete delivery,
removed disproof, wrong source and erased fidelity limits. Consistency attests
neither historical execution nor complete review/export, native viewing or source
composition fidelity. k63 stays live in its same undescribed/unsealed jj change.
Next is installed complete create and its checkpoint/dependency/signal acceptance;
all packet/Q1–Q3/replay/ack/export/compatibility/B-reuse/public/native/isolation/
fidelity/six-case/resource obligations remain. k28 retains every missing real
truth/reaction/preservation remedy and full-default/nonrigid obligation.

## Shared complete import-asset assembly — 2026-10-15

The product now owns `bookscan.import_assembly.assemble`, rather than leaving
all-occurrence asset publication in a test-owned runner. Under caller-held stores,
it checks exact saved source/page order and complete RGB, publishes every packed
sample and recursive profile/palette payload, freezes producer metadata and
returns only completely verified uncommitted initial state. Blanks/duplicates
remain distinct occurrences; identical assets may share content addresses.
The existing native runner consumes this operation before its real checkpoint
commit/source-loss resume. Reservation/preflight/live resource guarding and
public create's signal/result/cleanup lifecycle remain concrete unfinished work.

[Ordinary assembly evidence](baseline-import-assembly/README.md) retains raw
source/wheel/constructor/subject/ledger/native records and executable readers.
Both frozen full gates have the same 2,562 individual passing tests, including all
2,545 predecessors and seventeen new assembly checks. All 46 packaged members
match source/wheel/installation. Source and wheel constructions/native readings
agree on all seven RGB digests; actual installed status interruption/read-denial/
EPIPE and source/resource-loss resume retain their prior meanings. Staff and
synthetic preparation outcomes agree itemwise. The 19,979 read subjects have
unchanged bytes/native facts; no measured input or instrument changed mid-run.

The native integration exposed tuples inside each occurrence's resource record;
a red tuple-resource counterexample preceded normalization at that boundary.
Copied-package omissions independently fail profile/palette closure (one check)
and final asset verification (two checks), with unrelated assembly checks green.
The archive reader reconstructs all seventeen checks and decoded false-corpus
controls reject invented delivery, removed disproof, wrong source and erased
fidelity limits. External binary subjects are identity references; saved projects
are historical inode-bound evidence, not compatible completed-project fixtures.
Consistency supplies no historical execution attestation or source-fidelity pass.

Public create is still unavailable; status remains its verified initial-state
reader. No complete finite reviewer, packet/receipt action/ack/export or actual
native-packet demonstration is claimed. The same live F owner next connects
complete create reservation/source/dependency/native/assembly/checkpoint/public
outcomes and installed pre/post-commit/child/signals/kill/reap faults. All original
Q1–Q3/replay/ack/views/export/compatibility/B-reuse/public/native/isolation/fidelity/
six-case/resource obligations stay live. k28 retains missing real truth/reactions/
preservation remedies and complete-default/nonrigid work. No public route, native
API, dependency pin, preparation meaning or frozen experiment changed here.

## New-project reservation continuation

[Reservation evidence](baseline-reservation/README.md) records the product's
exclusive unused-name reservation and its use in actual native initial-state
assembly. Eighteen tests cover conflicts, canonical aliases, replaced parent/root,
empty-only cleanup, cancellation and selected-error/descriptor behavior. Four
real private process runs each observe seven signal/reap/competition cases;
retained incomplete roots fail installed status with the explicit new-import remedy.
These are not public-create/checkpoint/native-child acceptance.

Final paired checks preserve all 2,562 predecessor outcomes and add eighteen,
with 20,000 unchanged read subjects and exact source/wheel/installed package bytes.
Four native readings retain seven construction RGB digests and source/resource-
loss resume meanings. Mutation copies expose missing identities and recursive
cleanup while unrelated checks remain green. The ordinary reader and four
semantic false-corpus controls run without temporary paths or native execution.
Preparation/staff and installed status denial/signal/EPIPE checks agree itemwise.
No source-composition fidelity or complete finite handoff is inferred.

Public create remains unavailable until owned cleanup/source/preflight/native/
checkpoint/result integration and actual installed create faults are complete.
Every original F review/packet/ack/export/compatibility/B-reuse/fidelity/six-case/
resource requirement remains live; no partial retirement, sealing or parent closure.

## Product initial-import continuation

The [initial-import evidence](baseline-initial-import/README.md) records the
product-owned source-first reservation/writer/native-resource/assessment/assembly/
initial-checkpoint operation and its real native runner. Final paired gates agree
on all 2,594 checks, preserving 2,580 predecessors and adding fourteen import-owner
checks. Source/wheel/native/preparation/staff results agree itemwise; three copied
omission controls fail the expected cases. The primary and console-script
supplementary frozen records cover 26,166 unchanged read subjects. Nine bounded
archive parts retain the raw corpus, with standalone reconstruction and four
semantic corpus controls. The stopped preliminary expectation and original
console-script installation binding are explicit in that note.

The committed outcome survives later cancellation/cleanup without changing signal
exits into public success. Public create remains unavailable pending exact owned
nonempty cleanup, command/child/signal/result integration and actual installed
create faults. The complete F review/view/global-refresh/replay/selection/ack/export/
compatibility/fidelity/six-case/resource and B reuse obligations remain live.
This evidence supplies no independent composition fidelity, completed project
fixture, new human reaction, finite retirement or complete-default/nonrigid result.


## Owned source cleanup continuation — 2026-10-15

Uncommitted initial import now removes only its unchanged owned source snapshot
through the held reservation directory. Replaced/modified snapshots, links,
unknown children and changed reservations remain untouched; cleanup errors keep
the selected failure, and actual committed state retains verified resume.
The metadata recheck uses integer nanosecond times after an actual APFS control
rejected ordinary stat-tuple equality. No adversarial same-user rename-race defense
or complete store/private-entry cleanup is claimed.

Paired complete gates agree on all 2,625 checks, preserving all 2,594 predecessors
and adding 31; the 63 focused cases and affected source/wheel checks agree itemwise.
All 48 package members match. Four native readings retain the seven earlier RGB
construction digests and source/resource-loss resume. Staff/synthetic preparation
cases and full fault ledgers agree; no real preparation subject changed. Four
copied-package mistakes have their exact related failures and unrelated green
checks retained. Every one of 15,042 named read subjects stays byte/native exact.

[Ordinary evidence and reconstruction](baseline-source-cleanup/README.md) retain
source/contracts/wheel, raw ledgers/logs, native assets, frozen subjects and mutation
copies in eleven bounded parts. Four decoded-corpus controls reject invented
delivery, missing disproof, changed source and erased fidelity limitations.
The first lexical /tmp native reading is preliminary; the final full rerun uses
canonical /private/tmp paths without changing product/test/recipe subjects.
The private construction runner's raw /tmp limitation remains explicit.
Installed writer signals/read-denial/EPIPE observations are status faults, not
public-create/checkpoint/native-child acceptance. Consistency is no execution
attestation or source-composition fidelity, and old inode-bound projects are not
relocated compatible fixtures. Reader/recipe notes were added after measurement.

Public create and the complete finite reviewer remain unfinished in the same
live F change. Next complete exact store/private-entry cleanup, command/child/
signal/result lifetime and actual installed creation faults, then every original
review/view/global-refresh/replay/selection/ack/export/compatibility/B-reuse/
fidelity/six-case/resource obligation. k28 retains missing real truth/reactions
and complete-default/nonrigid work. This continuation retires or seals no leaf.

### Owned empty store directory cleanup boundary

The live F owner's reservation now supports identity-bound removal of one exact
empty child directory, with held-root-relative rmdir and no recursive scan.
Unknown children, links, replacements and changed reservations remain untouched.
The [ordinary evidence](baseline-empty-store-cleanup/README.md) retains 26 observed
red/green cases, five copied-package disproofs and paired full/affected/staff/
synthetic preparation checks. This boundary is not yet wired into the importer;
owned bootstrap/store/private-entry cleanup, including partly published assets,
stays next. Public create and the entire original finite delivery remain live.

Failed lock provisioning now cleans only its captured unchanged partial writer
lock, allowing initial import's existing source/empty-root cleanup to complete.
Successful writer locks retain their stable inode. Frozen paired checks, actual
private native ownership/reservation outcomes and exact change boundaries are in
[bootstrap cleanup](baseline-bootstrap-cleanup/README.md). Store/private-asset
cleanup and the complete finite/public/native/fidelity handoff remain unfinished;
no leaf is retired or partial change sealed.

## Acquired-bootstrap failure cleanup continuation

[Acquired-bootstrap cleanup evidence](baseline-acquired-bootstrap-cleanup/README.md)
records the next narrow failed-import cleanup mechanism. Initial import removes
its captured unchanged acquired lock while still holding writer ownership, then
cleans its saved source and empty root. Changes, missing identity, unknown children
and unacquired locks remain safe; successful imports and latched committed state
retain the stable inode. Writer context exit preserves an already selected error
through an OS close failure. The existing source/header/checkpoint meanings and
all original finite/public/native/fidelity obligations remain binding.

```sh
task process:acquired-bootstrap-cleanup-check
```

Both final full gates pass identical 2,702 itemwise cases, retaining 2,678
predecessors and adding 24. Affected acquired/bootstrap/source/import/staff recipes
agree (162/162/114/117/4); native ownership/reservation and synthetic preparation
cases/fault ledgers agree. Paired actual native imports retain the seven known
construction RGB digests, seven context controls and source/resource-loss resume.
Named freezes preserve 9,553 main and 9,599 native subjects. Copied predecessor
and five distinct faulty packages reject the corresponding mechanisms; raw
per-case records, source copies and instruments are retained in the ordinary
indexed ZIP parts. This supplies no new public create, complete finite delivery,
real source-composition fidelity, relocated project compatibility or real visual
response. Exact owned store/header/private-name/partly published asset cleanup
and the original command/child/review/packet/ack/export/fault/six-case/B-reuse
inventory remain unfinished in the same live, unsealed F change.

Private header failure cleanup now compares captured integer-nanosecond metadata
and single-link regular-file identity against held/named files, the held root,
verified writer and captured parent. It retains changed entries, unknown capture
and post-link files; missing names are already clean. This safeguards only the
private-header failure path. Complete store/header/published-asset rollback and
public create remain unfinished. Run `task process:private-header-cleanup-check`;
ordinary evidence is in `baseline-private-header-cleanup/README.md`.

## Failed private publication continuation

Failed private RGB/blob writes now reconcile their import ownership journal after
successful own-file cleanup, permitting exact rollback of an otherwise clean
incomplete project. Changed or foreign files, directory-mode changes, checkpoints
and unlink refusals retain the supporting state and selected error. The
[current ordinary evidence](baseline-aborted-publication/README.md) records the
32 filesystem challenges, copied disproof and paired 3,181-case product gates,
preparation/native/writer checks and frozen subjects. Run
`task process:aborted-publication-check`. Public create, uncaptured private/native/
resource cleanup and the complete original finite review/export handoff remain
live in the same unsealed F change; no partial leaf is retired.

## Exact advisory-analysis cleanup

[Analysis cleanup evidence](baseline-analysis-cleanup/README.md) records the
replacement of recursive advisory-workspace deletion with captured exclusive-file,
complete-inventory/stamp and empty-root cleanup. Changed/unknown entries and
uncertain creation outcomes are retained; selected errors survive cleanup/close,
and actual child cancellation/reap is checked. The new recipe is
`process:analysis-cleanup-check`. Paired full/focused/native/preparation/worker
readings and observed failing controls are retained there. Renderer/Fontconfig
resource-name cleanup and the complete finite handoff remain unfinished in k63.
