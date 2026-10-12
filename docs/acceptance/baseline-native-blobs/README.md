# Transactional native blobs

`bookscan.native_blobs` stores exact opaque packed channels, ICC bytes and palettes
under caller-held writer ownership. Complete v1 references bind a SHA-256 digest
and byte length. Reads verify the saved directory identity, regular unaliased file,
exact bytes and unchanged entry metadata. Writes use exclusive private names,
complete disk verification and no-clobber hard-link publication; cleanup checks
its owned inode and preserves a selected interruption. Nothing interprets a
profile, reacquires ownership or discovers/promotes an orphan as accepted state.

The header and complete checkpoint semantic verifier still need to incorporate
this directory and its references. These component operations do not deliver
public create/status/resume, an accepted project or composition fidelity.

```sh
task process:native-blob-check
task process:native-blob-acceptance ARTIFACTS=/tmp/NEW-WRITER-READING
task process:native-blob-sample-acceptance ARTIFACTS=/tmp/NEW-SAMPLE-READING
python3 docs/acceptance/baseline-native-blobs/verify.py
python3 docs/acceptance/baseline-native-blobs/controls.py
```

Paired full checks passed the same 2,196 cases, retaining all 2,146 predecessor
outcomes and adding fifty blob constructions. The installed locked wheel passed
the same 104 selected cases twice; all source/wheel/installed product members
were byte-equal. Four isolated package omissions expose three digest failures,
one trailing-length failure, one directory-redirection failure and one foreign-
cleanup failure, with unrelated constructions passing.

Two actual installed writer readings each cover eight pre/post-link release,
SIGINT, SIGTERM and SIGKILL cases. The runner checks the observed barrier PID
against its child PID before signalling, waits/reaps the writer and verifies busy
exclusion followed by immediate reacquisition. Exact exit, visibility and private
orphan outcomes agree itemwise. The raw barrier PID and runner source are retained;
the child's PID equality is asserted during execution rather than separately
recorded as a second PID field. Killed private hard links remain unusable and
unreferenced; this component performs no orphan repair or checkpoint promotion.

Four source/wheel sample readings restore fourteen samples across sixteen PDF
occurrences through thirteen exact retained blobs after removing both PDF paths
and reopening checkpoint revision two. Packed bits, Indexed palettes, recursive
profiles, Decode and placement retain their previous meanings. Malformed profiles
remain opaque bytes. Four seven-occurrence native assessments retain every prior
fact. Paired staff and synthetic preparation checks preserve all prior cases and
all 38 actual installed preparation writer outcomes. No real preparation input,
locked dependency, native API or public capability changed.

The archive retains 495 named entries through 426 digest-shared payloads in three
parts (2,479,839 compressed bytes). It includes frozen before/after metadata for
16,749 read subjects, exact product/test sources, the wheel, JUnit/log records,
writer/sample/native reports and retained native blobs. External library/tool
bytes are identified by frozen digests and metadata; they are not all copied into
this archive. The reader reconstructs the retained per-item evidence and byte
bindings without relying on the original temporary paths. It does not reproduce
historical native execution or certify glyph, colour or complete-page fidelity.
Coherent digest-valid repacks inventing delivery, removing cleanup disproof or
changing retained byte lengths are refused. See `evidence-controls.json`.

The complete finite reviewer remains on live `baseline-finite-k63`: native
inventory/resolution and header/checkpoint integration, public operations,
review/replay/inspection/acknowledgement, full/native packets and global refresh,
exact export/report/publication, compatibility, browser reuse, fixed-case and
resource acceptance remain required. Missing real truth, reactions, remedies and
complete-default/nonrigid acceptance remain with k28.
