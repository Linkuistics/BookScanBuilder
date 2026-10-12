# Failed-import cleanup of known linked aliases

A failed import can now remove its captured RGB/native publications when cleanup
of a known private file refuses removal after successful publication or deduplication.
The publisher transfers ownership evidence before closing its creation descriptor.
A returned no-clobber link permits capture of exactly its two private/final names;
deduplication permits capture of the separate single-link private file. Import
rollback still verifies original ancestry/header, untouched checkpoint history and
both complete store inventories before removing anything.

The held file is stamped before the refused unlink. Both known aliases must match
that stamp, regular type and exactly two links, with unchanged directory identity/
mode and previously captured files. After rollback successfully unlinks one owned
alias, only the survivor's link count and ctime may advance; identity, mode, size,
mtime and all other files remain checked. Extra links, changed/unknown names,
uncertain open/link outcomes and checkpoint activity prevent adoption/removal.
A persistent refusal retains the remaining file and supporting source/bootstrap;
earlier exact owned files may already have been removed. Resume receives no journal.
This guards cooperative operations and detected changes, without claiming protection
against hostile same-user replacement between the last check and unlink.

Run `task process:linked-import-rollback-check`. The
[78 filesystem challenges](../../../tests/test_linked_import_rollback.py) exercise
actual source/reservation/writer/stores/checkpoints/rollback, with native assessment
substituted. The test-first reading reproduced eight clean rollback failures with
52 preservation controls green. Later cases cover changes after capture, changes
immediately after an own alias unlink, final-alias refusal and an unknown third
link already present before the pre-cleanup stamp. The first green diagnostic
used an overstrict persistent-refusal expectation; its log is retained separately
from the corrected final readings.

Checked predecessor code fails 24 of the final 78 cases, with 54 preservation
controls green. Adopting the post-refusal stamp fails twelve, omitting survivor
transition checks fails ten, and permitting a third link fails two. The third-link
mutation initially passed the existing tests because their independent stamp guard
still caught the later extra-link changes. The added before-stamp case exposes
that distinct bug. Copied module paths/digests and individual outcomes are retained.

Both sequential readings pass and agree itemwise: 3,303 product tests with
formatting/lint/strict types, 405 focused cases, four staff cases, nine synthetic
preparation cases, 90 preparation faults and 38 preparation signal/kill records.
Eight actual asset-worker and forty checkpoint/source-worker cases verify exact
RGB, identities, source/checkpoint relationships, interruption visibility and
immediate reacquisition. Seven native construction imports retain the prior RGB
and record-rejection outcomes plus source/resource-loss resume. Complete dependency
preflight matches the inherited identity; the helper-only check is retained as a
separate record. No helper build or real collection comparison was needed: the
preparation implementation/subjects remain unchanged.

All 8,064 declared subjects retain bytes/native metadata across both readings.
These include source/tests, normative inputs, manifests/lock/recipes, the Python
environment/base interpreter, instruments, declared native tools/cache and recorded
linked files. Staff's ephemeral uv environment and the full host dynamic-library
graph are not exhaustively frozen. Four altered per-item preparation/worker/source/
PID records reject. The bounded source comparison preserves 214 other original
source/test files, the manifest/lock and original recipe prefix.

The [archive](evidence.zip) and [member index](index.json) retain source/diffs,
test-first and intermediate diagnostics, copied disproof, paired reports/assets,
subject inventories and instruments. Two unreadable permission-fault outputs keep
their native modes and are listed; symlink members retain target bytes. Run
`uv run --locked python docs/acceptance/baseline-linked-import-rollback/verify.py`
for content verification and two wrong-digest controls. The reader checks measured
source and individual paired source/checkpoint/decoded-RGB relationships. Content
cannot attest historical execution/native inode identity; the retained original
comparator additionally checks the measurement filesystem. The preceding private-
rollback archive also verifies against this continuation's captured starting source.

This is internal unfinished work in the same live, undescribed/unsealed
`baseline-finite-k63` change. Native/resource-name ownership and complete command
cancellation/owned-child reap/committed-result/remedy lifetime remain, followed by
actual installed public-create barriers and every original packet/receipt/action/
replay/acknowledgement/export/compatibility/B-reuse/fidelity/six-case/resource check.
The worker observations here do not supply installed public-create acceptance,
relocated predecessor compatibility or real composition fidelity. k28 retains
missing real truth/reactions/remedies and complete-default/nonrigid work. No finite
delivery, partial retirement, task boundary, parent closure or teardown is claimed.
