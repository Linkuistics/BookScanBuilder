# Native store identity on restart

The private project header now records the native-byte directory's device/inode
alongside RGB assets and checkpoint storage. Provision creates all three stores
before publishing the header. Resume rejects a missing/replaced directory and
passes the verified `Stores` context to its mandatory semantic callback, under
one writer acquisition. The callback can read checkpoint-owned native references
without trusting freshly observed directory identities or reacquiring ownership.
Existing internal RGB-only callback callers are explicitly adapted.

A header still establishes no accepted import. Missing native identity is rejected
as an incomplete scaffold, with no fresh-stat fallback. No completed predecessor
project or public format migration has been delivered. The complete semantic
checkpoint verifier must still bind source/core/render/resource/triage/review
meanings; the construction callbacks here establish only their named components.

```sh
task process:native-header-check
task process:native-inventory-acceptance ARTIFACTS=/tmp/NEW-NATIVE-READING
task process:header-acceptance ARTIFACTS=/tmp/NEW-WRITER-READING PYTHON=/path/to/installed/python
python3 docs/acceptance/baseline-native-header/verify.py
python3 docs/acceptance/baseline-native-header/controls.py
```

Both frozen full gates passed the same 2,284 cases, retaining every prior 2,263
outcome and adding 21 native-header constructions. Both installed-wheel readings
passed the same 195 selected cases. All product source, wheel and installed
members are byte-equal. The initial reading had thirteen failures for missing
native identity/provisioning/context plus eight already-covered strict refusals.
Two isolated copied-package omissions each expose six targeted failures while
unrelated cases pass: native-directory verification and semantic-history callback
verification. Product bytes are untouched by these controls.

Both actual installed-writer readings passed all forty initial/update release,
SIGINT, SIGTERM and SIGKILL cases at asset-complete, record-complete, pre-pointer,
inside-pointer and post-pointer barriers. The adapter asserts barrier PID equals
its child PID, busy exclusion, exact exits/commit/visibility and reacquisition
following reap. Retained per-case events name the saved native-directory identity
and header. These checks exercise the storage component, not public create.

Four source/wheel constructed inventory readings each restore 31 occurrences,
32 samples and 20 blobs after both input/snapshot PDF paths disappear. Restart
uses `project.json` and references saved in each checkpoint. All 124 altered
inventories refuse, retaining the earlier sample/placement/concern meanings.
Literal tests additionally reject predecessor-only corrupt native bytes and a
hash-valid wrong maximum behind a valid current record. Four native assessment
readings retain prior facts. Paired staff and synthetic preparation retain their
itemwise outcomes, including all 38 actual preparation writer cases. No dependency,
native API or real preparation subject changed; real comparisons were unaffected.

All 19,482 declared read subjects retained their digests and native metadata across
the paired run. The archive has 864 named entries through 710 shared payloads in
five parts (4,039,351 compressed bytes), retaining exact product/test sources,
wheel, raw logs/JUnit/reports, native blob bytes and measurement instruments.
External tool/library bytes have frozen identity metadata rather than all being
copied. The standalone reader reconstructs itemwise outcomes, saved identities,
references and byte closure. Six coherent digest-valid repacks fail when they
invent delivery, remove semantic disproof, alter lengths/maxima/writer identity
or erase the missing composition oracle. Offline reconstruction does not replay
historical native execution or establish source composition fidelity.

This is progress within live `baseline-finite-k63`, in its same undescribed,
unsealed jj change. Full checkpoint semantics, public create/status/resume,
review/replay/inspection/selection-union acknowledgement, complete packets and
actual native/global-refresh use, exact export/report/publication, predecessor/
upgrade compatibility, browser reuse and all six-case/resource/isolation work
remain required. k28 retains missing real truth, reactions, preservation remedies
and complete-default/nonrigid work. F, k53, k47, B and k54 remain live.
