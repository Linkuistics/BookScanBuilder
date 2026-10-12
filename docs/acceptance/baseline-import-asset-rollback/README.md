# Captured import asset rollback

A failed initial import can now remove its completed RGB and native-blob
publications before rolling back the empty bootstrap, source snapshot and lock.
The importing invocation captures ownership at successful publication, before
descriptor release or the final verification read. Duplicate publication reuses
only its already captured file. Matching content alone grants no ownership.
The journal is transient; resume cannot reconstruct or use it.

Rollback verifies original ancestry/header, untouched checkpoint history and both
complete captured store inventories before deleting any asset. Changed bytes,
metadata, replacements, symlinks/hardlinks, foreign names and checkpoint activity
retain the supporting import files. Cleanup removes only captured unchanged names
and preserves the selected failure. An unlink refusal or a changed store during
cleanup retains the remaining files. This guards cooperative writer operations
and detected replacements; it provides no hostile same-user rename defense.

Run `task process:import-asset-rollback-check`. Its 251 cases include the
[33 new filesystem challenges](../../../tests/test_import_asset_rollback.py).
The test-first predecessor fails nine cleanup cases with 24 controls green.
Copied omissions of checkpoint guarding, full file stamps and cleanup transition
validation fail two, six and two cases respectively, with unrelated cases green.
Tests substitute native assessment only; reservations, snapshots, ownership,
PNG/blob publication and checkpoint transactions use the real filesystem.

An actual APFS probe showed directory link count changing from 2 to 3 to 4 as
file names were added. Publication therefore checks invariant directory identity
and mode, exact file names/stamps, then captures the new complete directory stamp.
Between owned operations that complete stamp must remain unchanged. The initial
implementation's link-count assumption failed before correction. Preliminary
full-suite failures also exposed an assembly fixture that deliberately deletes
its constructed assets. That fixture now discards its invalid transient journal;
all assembly assertions remain. Initial-import expectations now distinguish clean
owned rollback from late corruption and committed state.

Two sequential final readings agree item by item on 3,149 product tests with
format/lint/strict types, 251 focused cases, four staff cases, nine synthetic
preparation records, 90 preparation faults and 38 preparation signal/kill records.
Eight asset-worker and 40 checkpoint/source-worker cases preserve exact assets,
native identities, signal/kill visibility and immediate writer reacquisition.
Seven native construction imports preserve the preceding exact RGB digests and
seven record rejections, with source/resource-loss resume and a denied native
launch control. These internal/private observations do not provide installed
public-create barriers or real composition-fidelity acceptance. No helper build
or real preparation subject changed.

All 8,060 declared source/test/contract/environment/interpreter/tool/cache/recorded
linked-library/instrument subjects retain hashes and native metadata across both
readings. Staff's ephemeral uv environment and the full host dynamic-library
graph are not exhaustively frozen. Four altered preparation/worker/source/PID
records reject. The bounded source comparison retains 207 other original
source/test files, the manifest/lock and original Taskfile prefix exactly.

The [standard ZIP](evidence.zip) and [member index](index.json) retain source/diffs,
test-first/preliminary/final logs, JUnit, copied disproof, paired reports/assets,
frozen inventories and instruments. Two unreadable permission-fault outputs retain
their permissions and are listed explicitly; symlink members contain target bytes.
Run `uv run --locked python docs/acceptance/baseline-import-asset-rollback/verify.py`.
The [content verifier](verify.py) checks all member digests, current measured
source, paired individual outcomes, native saved-source/checkpoint/RGB relationships
and each copied mutation's failing and passing cases. Both wrong digest controls
reject. Content cannot attest historical execution or inode identity; the original
comparator additionally checks the retained filesystem.

`baseline-finite-k63` remains live in its existing open jj change. Uncaptured
private files or incomplete link/private-name cleanup still retain the bootstrap;
their exact ownership and native/resource-name cleanup remain next. Command
cancellation/owned-child/committed-result lifetime, installed public-create
barriers, packet/action/replay/acknowledgement/export, compatibility/B reuse,
independent fidelity and all six-case/resource obligations remain unfinished.
k28 retains missing real truth/reactions/remedies and full-default/nonrigid work.
No finite handoff, retirement, partial task boundary or parent closure is claimed.
