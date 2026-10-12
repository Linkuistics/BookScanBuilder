# Failed private-write cleanup

A failed initial RGB/blob publication can now remove its owned private file and
still roll back the importing project's captured assets, empty bootstrap, source
snapshot and lock. Previously that successful private unlink left the transient
directory journal stale, stranding an otherwise removable incomplete project.

After cleanup succeeds, the publisher verifies the original directory identity
and mode, exact captured names and every file stamp before recording the directory
change. It adopts no names from enumeration or matching content. Changed files,
foreign entries, directory-mode changes (including during unlink), checkpoints
and cleanup refusals preserve the supporting project files. Capture/cleanup
failure preserves the selected operation error. Resume receives no journal.
This protects cooperative writer operations and detected replacements, without
claiming defense against hostile same-user rename races.

Run `task process:aborted-publication-check`. The
[32 filesystem challenges](../../../tests/test_aborted_publication.py) cover
write/fsync/staged-read/link/dedup-read failures with and without preceding
RGB/native publications, plus preservation controls. Only native assessment is
substituted; reservation, source, locking, stores and rollback remain real.
The initial test-first run failed twenty cleanup paths with ten controls green;
two later unlink-mode controls also pass. Checked copied predecessor source
fails the same twenty paths with all twelve preservation controls green.
Removing directory-mode validation or adopting current inventory produces four
failures each, with unrelated checks green.

Two sequential final readings agree itemwise on 3,181 product tests with
formatting/lint/strict typing, 283 focused cases, four staff cases, nine synthetic
preparation cases, 90 preparation faults and 38 preparation signal/kill records.
Eight asset-worker and forty checkpoint/source-worker records retain exact RGB,
native identities, source/checkpoint relationships and immediate reacquisition.
Seven native construction imports retain the preceding RGB digests, seven record
rejections, source/resource-loss resume and a denied native-launch control.
These internal/private checks do not supply installed public-create barriers,
relocated predecessor compatibility or real composition-fidelity acceptance.

All 8,061 declared source/test/contract/environment/interpreter/tool/cache/recorded
linked-library/instrument subjects retain bytes and native metadata across both
readings. Staff's ephemeral uv environment and the complete host dynamic-library
graph are not exhaustively frozen. Four altered preparation/worker/source/PID
records reject. The source comparison preserves 212 other original source/test
files, the manifest/lock and original Taskfile prefix. No real preparation subject
changes and no helper build occurs. The current setup preflight matches the
retained dependency record's complete helper block; comparing those two different
top-level schemas directly first failed and supplies no credited equality.

The [ordinary ZIP](evidence.zip) and [member index](index.json) contain raw logs,
JUnit, source/diffs, copied disproof, paired assets/reports, frozen inventories
and instruments. Two unreadable preparation permission-fault outputs retain
their permissions and are explicitly listed; symlinks retain target bytes.
Run `uv run --locked python docs/acceptance/baseline-aborted-publication/verify.py`.
The [content verifier](verify.py) checks member digests, exact current measured
source, individual paired outcomes, native saved-source/checkpoint/decoded RGB
relationships and each mutant's passing/failing cases. Two wrong digest controls
reject. Content cannot attest historical execution or inode identity; the retained
original comparator additionally checks the live measurement filesystem.

`baseline-finite-k63` stays live in its same undescribed, unsealed jj change.
Private cleanup refusals, incomplete publications whose names were not captured,
failed opens whose descriptor never returns and native/resource-name ownership
still need exact cleanup. Command cancellation/child reap/committed-result lifetime,
installed public-create barriers and every original packet/action/replay/selection/
acknowledgement/export/compatibility/B-reuse/fidelity/six-case/resource obligation
remain unfinished. k28 retains missing real truth/reactions/remedies and full
default/nonrigid work. No finite handoff, retirement or partial task boundary is
claimed. Evidence-reader and note edits follow measurement without changing its
product/test/recipe subjects.
