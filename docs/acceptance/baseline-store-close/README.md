# Individual-store close-failure cleanup

A close-only failure while initializing an assets, checkpoints or native-blobs
directory now removes that exact unchanged empty store. Both original directory
closes finish first. Cleanup reopens and verifies the original parent/root under
the existing writer, compares the store's captured native metadata and refuses an
occupied project header. It never retries a possibly reused descriptor number.
Changed stores, replaced ancestry, unknown entries and actual checkpoint content
remain intact. Secondary cleanup errors add notes to the first selected error.

The product change is bounded to `provision_store` and one private helper in
[project_reservation.py](../../../src/bookscan/project_reservation.py). All 209
other captured source/test files retain their bytes; the existing Taskfile and
task-note prefixes remain exact. Public interfaces and saved formats are unchanged.
This extends the existing cleanup contract; it supplies no protection against an
adversarial same-user rename race.

Run `task process:store-close-check`. The
[110 new filesystem cases](../../../tests/test_store_close.py) cover both close
boundaries for all three stores, unchanged/read/missing names, nanosecond metadata
changes, populated-then-emptied stores, replacements, symlinks, occupied headers,
parent/root replacement, failed cleanup, real descriptor-number reuse and a real
committed checkpoint. The initial test-first run failed 66 cases and passed 24
controls. The final copied predecessor fails 84 of the expanded 110 cases and
passes 26 controls. Removing the original-parent check fails six cases; reducing
the full store comparison to inode identity fails 18. Copied module paths and
source digests are checked by the retained disproof runner.

Two sequential Taskfile readings agree on every individual outcome: 3,044 product
tests with format/lint/strict typing, 668 focused tests, four staff cases, nine
synthetic preparation records, 90 preparation fault outcomes, 38 observed
preparation signal/kill records and 40 private installed checkpoint/source worker
records. Worker PID, native identities, source digests/metadata, checkpoint bytes
and current pointers were checked before cross-run normalization. Generated PDFs
are compared after removing only their checked generated trailer `/ID`; complete
remaining bytes agree. Four deliberately wrong per-item records are rejected.
These private workers do not satisfy public-create barrier acceptance. No real
preparation source or comparison subject changed.

All 8,006 named repository/environment/interpreter/tool/instrument subjects retain
their bytes and native metadata across both readings. The staff runner's ephemeral
uv environment and host dynamic-library graph are not exhaustively frozen.
Both command readings finished before the content verifier was written. Its first
draft incorrectly treated all preparation digest subjects as generated PDFs;
the corrected verifier includes and checks the actual repository subjects too.
Product, tests and recipes did not change during that evidence-tool correction.

The [index](index.json) records per-member hashes for the ordinary
[ZIP archive](evidence.zip). It retains source before/after, the diff, test-first
logs/JUnit, paired reports/generated artifacts, frozen inventories, copied
disproof, graph evidence and measurement/comparison instruments. Two unreadable
permission-fault outputs retain their original permissions and are explicitly
listed with native metadata. Symlink members contain their target bytes.

Run `uv run --locked python docs/acceptance/baseline-store-close/verify.py`.
The [verifier](verify.py) checks archive hashes, exact current measured source,
paired test identities, frozen inventories, preparation inputs/outcomes and
worker source/checkpoint relationships; it rejects wrong archive/member digests.
Archive contents cannot reproduce historical native inode identity or attest
execution. The retained original comparator additionally checks those identities
against the original measurement directory.

Tier 2 graph coverage at generation `2026-10-15T02:01:49Z` reports matching material
metadata with no recorded gap, a best-effort signal. Complete helper traces name
`provision_store` as the caller; the runtime-observer `stat` edge is heuristic.
Exact source and filesystem observations support the cleanup claim.

`baseline-finite-k63` remains live in its existing open jj change. Complete cleanup
after store provision returns, partly published assets and private/native resource
names, command cancellation and installed public-create barriers remain unfinished,
alongside the original review/packet/acknowledgement/export/compatibility/fidelity
and six-case obligations. This is no finite workflow or product acceptance.
