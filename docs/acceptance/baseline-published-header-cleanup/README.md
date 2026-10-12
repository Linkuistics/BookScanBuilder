# Failed published-bootstrap cleanup

Caught failures during header publication, readback and final bootstrap verification
now remove only this operation's captured unchanged header names and unchanged
empty stores, while writer ownership remains held. Header publication can briefly
own two hard links; only the expected link-count and ctime transition is adopted.
Device/inode, mode, size and integer-nanosecond mtime must remain fixed. Store
stamps come from creation, preventing later checkpoint activity from being
mistaken for an untouched store.

Changed/replaced names, additional links, unknown metadata, changed ancestry,
store activity and checkpoint state remain intact. Cleanup errors add notes to
the selected exception. This covers bootstrap failures before `Stores.provision`
returns, without changing public interfaces or saved formats. Complete importer
rollback, partly published assets, and failures arising only from closing an
otherwise successful bootstrap still need completion. It provides no guarantee
against an adversarial same-user rename race.

Run `task process:published-header-cleanup-check`. The initial counterexamples
produced 24 failures and 18 passing controls. Additional tests exposed six unsafe
metadata-transition cases and two early-checkpoint cases before their repairs.
All 60 new filesystem cases now pass. An exact copied predecessor fails 36 and
passes 24 controls; an inode-only mutation fails 21 and passes 39. Imported module
paths/digests and unchanged copied subjects identify those runs.

Final paired runs agree itemwise on 2,846 full product tests, 336 focused tests,
four staff tests, nine complete synthetic preparation case records, 90 preparation
fault outcomes and 38 observed signal/kill records. Formatting, lint and strict
typing pass. All 2,786 predecessor outcomes remain passing; two historical tests
now assert rollback instead of the old unfinished retention behavior. Paired
private installed-package header/checkpoint workers agree on 40 cases, after
checking actual lock/store identities, writer PIDs, checkpoint bytes and pointers.
These are existing private workers, not installed public-create barrier acceptance.

All 9,583 named repository, environment, interpreter, selected-tool and measurement
instrument subjects retain byte hashes and native metadata during the final
reading. Host dynamic libraries and the staff runner's separately cached
environment are not exhaustively frozen. Generated preparation inputs match
before/after digests and direct rehashes. Comparisons normalize only artifact
roots, validated staging UUID names, positive PIDs and verified checkpoint digests.
Three deliberately wrong report records reject with unrelated records unchanged.
An earlier paired reading is retained as preliminary because the early-checkpoint
repair followed it; only the final pair supports the current artifact claim.

The [archive index](index.json) describes a standard ZIP split into ordered
`evidence-*.zippart` files, with part/member SHA-256 hashes. It retains source,
logs, JUnit, reports, manifests, instruments, copied disproof and worker artifacts.
Permission-fault outputs that cannot be read remain unchanged and are listed
with native metadata under `unreadable_generated_files`; no permissions were
changed to archive them. Symlink entries retain their target bytes. Content
integrity does not attest historical execution or reproduce native inode identity.

Run `python3 docs/acceptance/baseline-published-header-cleanup/verify.py.txt` from
the repository root. It checks archive contents, paired outcomes, predecessor
coverage, frozen manifests, copied disproof, preparation/header relationships
and current exact source, then rejects four deliberately wrong inputs.

Only `_publish` and `Stores.provision` change among original product functions;
three private helpers are added. All 1,872 starting paths survive, unrelated
bytes remain exact, and the original Taskfile and task notes retain their prefixes.
Tier 2 coverage reports matching material source metadata without a recorded gap;
it remains best-effort. Historical observer `stat` edges are heuristic, not native
execution evidence. The full finite owner remains live and unsealed in its
original jj change, with all finite workflow and required acceptance still owned.
