# Empty-bootstrap rollback after import failure

A failure after store provisioning now removes the exact untouched empty
bootstrap before removing its owned source and writer lock. The provisioning
instance retains its original parent, header and store identities in memory.
Cleanup consumes that evidence once under the same writer; it never infers
ownership from names after failure. Resumed store instances have no creation
evidence.

Any store activity, changed header, replaced ancestry or cleanup failure retains
the remaining source, lock and bootstrap together. This protects a checkpoint
from losing its supporting files just because an outer outcome latch is unset.
Unknown root entries remain untouched. The change reuses the existing verified
fresh-descriptor cleanup and does not defend against an adversarial same-user
rename race. Complete cleanup of partly published assets and private native
resources remains unfinished.

Run `task process:import-bootstrap-rollback-check`. The
[38 new filesystem cases](../../../tests/test_import_bootstrap_rollback.py)
exercise unchanged/read-only/unknown-entry cases, store activity and replacement,
nanosecond metadata changes, changed headers, replaced roots and parents,
cleanup denial and preservation of a real generic checkpoint. That checkpoint
tests store retention, not baseline-semantic validity. The initial run failed
35 cases and passed three ancestry controls. The copied predecessor reproduces
those outcomes. Removing the original-parent check fails one case; reducing
store comparison to inode identity fails 13. Copied module paths and hashes are
checked by the retained disproof instrument.

Two sequential primary readings agree on every individual outcome: 3,082 product
tests with formatting, lint and strict typing; 706 focused tests; four staff
cases; nine synthetic preparation cases; 90 preparation fault outcomes; 38
preparation signal/kill records; and 40 private checkpoint/source-worker cases.
The comparator checks actual worker PIDs, native identities and saved source/
checkpoint relationships. It removes only the checked generated PDF trailer
ID when comparing independently generated fixture bytes. Four deliberately
wrong per-item preparation/worker/source/PID records are rejected.

Both native supplementary readings pass the existing 117 initial-import tests
and seven construction imports with seven record-rejection controls. They keep
the predecessor's exact RGB digests and stable report meanings, and verify
source/resource-loss resume with a denied native-launch control. No helper is
built. These internal native checks and private workers do not satisfy public
create, installed create interruption, real composition fidelity or relocated
project compatibility acceptance.

All 8,014 named primary subjects and 8,063 named supplementary subjects retain
their byte hashes and native metadata through their respective paired readings.
The primary inventory includes source/tests, manifests, contracts, environment,
interpreter, selected tools and instruments. The supplement adds the existing
helper cache, recorded linked-library files and supplementary inputs. Staff's
ephemeral uv environment and the host dynamic-library graph are not exhaustively
frozen. No real preparation comparison subject changed.

The [index](index.json) identifies every readable member and its digest in the
ordinary [ZIP archive](evidence.zip). It retains source before/after, diffs,
test-first logs, raw paired reports, actual native saved assets, frozen subject
inventories, copied disproof and instruments. Two unreadable permission-fault
outputs retain their original permissions and are explicitly listed with native
metadata; symlink members contain target bytes.

Run `uv run --locked python docs/acceptance/baseline-import-bootstrap-rollback/verify.py`.
The [content verifier](verify.py) checks member integrity, exact current measured
source, paired individual results, native checkpoint/source/decoded RGB
relationships and the preserved predecessor meanings. It rejects two wrong
archive/member digests and three altered native-meaning records. Its first
strict-type check exposed a JSON-list annotation in the new supplementary reader;
that reader was corrected after all measurements, without changing measured
product, tests, recipes or instruments. Archive content cannot attest historical
execution or native inode identity; the original comparator additionally checks
the retained native filesystem.

The bounded source check preserves all 208 other captured source/test files
byte-for-byte. Product edits are in `initial_import.py` and `project_header.py`;
`test_initial_import.py` updates retention expectations, and the new test file
adds the challenges. Original Taskfile/task-note prefixes and manifest/lock bytes
remain intact. The preceding store-close verifier passed before these edits;
its exact-current-source checks remain historical after the deliberate changes.

`baseline-finite-k63` stays live in its existing open jj change. Partly published
assets and exact private/native resource cleanup, command cancellation and child
lifetime, and installed public-create barriers remain next, followed by all
original review/packet/acknowledgement/export/compatibility/fidelity and six-case
obligations. This is no completed finite workflow or product acceptance.
