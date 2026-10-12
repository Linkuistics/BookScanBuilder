# Private-name cleanup after a refused unlink

A failed import now retains exact transient ownership of an unpublished RGB/blob
file when its first cleanup unlink refuses removal. Import rollback can retry
that known name after verifying the original ancestry/header, untouched checkpoint
history, both store inventories, file identities and metadata. The chosen operation
error remains authoritative. Ownership comes from the returned creation descriptor,
not a content hash or enumeration.

The publisher stamps its held private file before attempting cleanup. After refusal,
it captures that name only if the held/named regular single-link file still matches
the stamp, the directory identity/mode matches, and all previously captured names
and files are unchanged. Unknown or changed entries, checkpoints and uncertain
open/link outcomes retain supporting files. Persistent unlink refusal retains the
remaining files. Resume receives no journal. This protects cooperative operations
and detected replacements; it makes no claim against hostile same-user rename
races between checking an entry and unlinking it.

Run `task process:private-import-rollback-check`. The
[filesystem challenges](../../../tests/test_private_import_rollback.py) cover
partial-write/fsync/staged-read/link/dedup-read errors, with and without preceding
RGB/native publications, plus changed-byte/mode/time/identity/link/inventory and
checkpoint controls. The initial reading failed twenty clean rollback cases with
twenty preservation controls green. Four additional uncertain-open/link-outcome
controls retain their files. Native assessment is substituted; source snapshots,
reservations, writer ownership, stores, checkpoints and rollback remain real.

The first full suite exposed a test fixture registration mistake: the fixture
worked in isolation but was unavailable after its original test module had already
been collected. That preliminary reading is retained and not credited as final
verification. A local fixture corrects collection without changing product code.

Both final sequential readings pass and agree itemwise: 3,225 product tests with
formatting/lint/strict types, 327 focused cases, four staff cases, nine synthetic
preparation cases, 90 preparation faults and 38 preparation signal/kill records.
Eight asset-worker and forty checkpoint/source-worker records retain exact RGB,
native identities, source/checkpoint relationships and immediate reacquisition.
Seven native construction imports retain the preceding RGB digests and seven
record rejections, source/resource-loss resume and a denied native-launch control.
These internal/private observations do not supply installed public-create
barriers, relocated-project compatibility or real composition-fidelity acceptance.

All 8,062 declared source/test/contract/environment/interpreter/tool/cache/recorded
linked-library/instrument subjects retain bytes and native metadata across both
readings. Staff's ephemeral uv environment and the full host dynamic-library graph
are not exhaustively frozen. Four altered per-item preparation/worker/source/PID
records reject. The bounded comparison preserves 213 other original source/test
files, the manifest/lock and original Taskfile prefix. No real preparation subject
changes or helper build occurs; complete current helper preflight matches the
retained dependency record.

Checked copied predecessor source fails twenty of the forty-four cases, with all
twenty-four preservation controls green. Removing the pre-cleanup file-stamp
check fails six; omitting directory-mode validation fails two; adopting current
enumerated names/stamps fails four. Unrelated cases remain green.

The [ordinary archive](evidence.zip) and [member index](index.json) retain raw
logs, JUnit, source/diffs, copied disproof, paired native/preparation/worker records,
input inventories and measurement instruments. Run
`uv run --locked python docs/acceptance/baseline-private-import-rollback/verify.py`
to check content and the current measured source. Its wrong archive/member digest
controls must reject. Content cannot attest historical execution or native inode
identity; the retained original comparator also checks the measurement filesystem.

This is unfinished work inside `baseline-finite-k63`'s same open jj change. Linked
private/final aliases and native/resource-name ownership still need exact cleanup;
unknown creation outcomes deliberately retain incomplete inputs. Command
cancellation/owned-child reap/committed-result
lifetime, actual installed public-create barriers and the original finite packet/
receipt/action/replay/acknowledgement/export/compatibility/B-reuse/fidelity/six-case/
resource obligations remain live. k28 retains missing real truth/reactions/remedies
and complete-default/nonrigid work. No finite delivery, partial retirement, new
task boundary or parent closure is claimed.
