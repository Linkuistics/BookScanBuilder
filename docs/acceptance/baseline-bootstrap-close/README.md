# Bootstrap close-failure cleanup

A close-only failure after complete header publication or final store verification
now rolls back the exact unchanged header and empty stores under the still-held
writer. All original descriptor closes finish first. Cleanup opens fresh directory
handles and verifies the original parent/root, saved header stamp and store creation
stamps. It never retries a possibly reused descriptor number. Changed entries,
additional links, replaced ancestry and checkpoint activity remain intact;
cleanup failures add notes while preserving the first selected error.

The change is bounded to `_publish`, `Stores.provision` and one private helper in
[project_header.py](../../../src/bookscan/project_header.py). Other original source
segments remain exact. It changes no public interface or saved format. Complete
import rollback after bootstrap returns, partly published assets/private resources,
and earlier individual-store close lifetimes remain unfinished. This supplies no
protection against an adversarial same-user rename race and no complete finite
workflow, native-view or source-fidelity acceptance.

Run `task process:bootstrap-close-check`. The
[88 new filesystem cases](../../../tests/test_bootstrap_close.py) exercise four
close boundaries, unchanged/read/missing headers, byte/mode/nanosecond/link changes,
changed/emptied stores, checkpoint activity, ancestry replacement, failed cleanup,
second close errors and actual descriptor-number reuse for an unrelated live file.
The first test-first run exposed ten cleanup failures with 42 passing controls.
The final copied predecessor fails 30 of 88 cases and passes 58 controls. Removing
the parent check fails four cases; ignoring store activity fails 20; reducing the
header comparison to inode identity fails 12. Copied imported module paths and
hashes are verified, without changing the working product for disproof.

Final paired Taskfile readings agree on every individual outcome: 2,934 product
cases with format/lint/strict typing, 424 focused cases, four staff cases, nine
synthetic preparation case records, 90 preparation fault outcomes, 38 observed
preparation signal/kill records and 40 private installed-package header/checkpoint
worker records. The latter are existing private workers, not public-create barrier
acceptance. No real preparation source or comparison subject changed.

All 7,963 named repository/environment/interpreter/tool/instrument subjects retain
their bytes and native metadata throughout both command readings. The staff
runner's ephemeral uv environment and host dynamic-library graph are not
exhaustively frozen. The comparator was corrected only after both readings
finished: it initially missed run paths used as dictionary keys, then exposed
six generated input PDFs differing only in their generated trailer `/ID`.
Their complete remaining bytes match. Raw input hashes are verified per run;
only that checked trailer ID is normalized for cross-run fixture comparison.
The original comparator is retained with its measured digest. The revised
comparator retains its own before/after digest and rejects four deliberately
wrong source, preparation, worker and test records. Product, tests and recipes
were unchanged throughout these comparison corrections.

The [index](index.json) describes an ordinary [ZIP archive](evidence.zip) with
per-member hashes. It retains source before/after, test-first logs/JUnit, final
paired logs/reports/generated artifacts, frozen inventories, copied disproof,
graph evidence and measurement/comparison instruments. Two unreadable generated
permission-fault outputs are listed with metadata; their permissions and bytes
were not changed for archiving. Symlink members preserve target bytes. Archives
cannot reproduce historical native inode identity or attest execution.

Run `python3 docs/acceptance/baseline-bootstrap-close/verify.py.txt` from the
repository root. It checks archive contents, exact current measured source,
paired per-test outcomes, frozen inventories and the original comparator digest,
and rejects two wrong digest controls. The archived comparator additionally uses
the retained measurement directory to verify native worker identities before
normalizing run-specific values.

Tier 2 graph coverage at generation `2026-10-15T01:47:13Z` reports matching
material metadata with no recorded gap, a best-effort signal. Complete helper
traces name its two bootstrap callers; exact source and filesystem observations
support the cleanup claim. The complete `baseline-finite-k63` owner remains live,
empty-described and unsealed in its existing jj change.
