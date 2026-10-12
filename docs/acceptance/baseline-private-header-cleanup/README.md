# Private header failure cleanup

A failed header writer removes its private name only while its captured native
identity, size, mode, link count and integer-nanosecond timestamps match both the
held descriptor and named single-link regular file. Its verified writer, held
root and captured parent must still agree. Metadata is captured after successful
creation, each write and sync. Unknown capture, changed files, added links and
replaced ancestry are retained with notes on the selected failure. Missing names
are already clean; reading alone does not disqualify cleanup. Cleanup invokes no
cancellation callback and provides no adversarial same-user rename-race guarantee.

An error after the header link retains both names when the private unlink fails.
This change does not implement complete header/store or published-asset rollback.
Initial import and public create lifecycle remain unfinished, as do the complete
finite reviewer, native packets/actions/acknowledgement/export and fidelity checks.
Successful publication and verified resume keep their previous meanings.

```sh
task process:private-header-cleanup-check
task process:native-header-check
task process:check
task geometry:staff-check
task process:header-acceptance ARTIFACTS=/tmp/NEW-header
task prepare:acceptance MODE=synthetic ARTIFACTS=/tmp/NEW-preparation
```

The initial counterexample run failed eight cases and passed three controls.
The final exact predecessor fails ten of the 74 header cases; 64 remain green.
Copied packages also fail with inode-only cleanup (9/65 failed/passed), omitted
ancestry (2/72), omitted parent identity (1/73), omitted mutation capture (4/70)
and silent unknown capture (1/73). Module paths/digests and before/after subjects
identify each exact copy. No production file was edited for those disproofs.

Both complete checks pass the same 2,719 individual outcomes, preserving all
2,702 predecessor cases and adding 17. The private-header recipe passes 144,
native-header 212, acquired/bootstrap 162 each, source 114, import 117 and staff
four, itemwise. All 9,573 named repository/environment/interpreter/selected-tool
files retain byte hashes/native metadata during the paired reading. This does
not freeze all host dynamic libraries or the separate cached staff environment.

Both native saved-header/checkpoint runs agree on 40 individual cases: actual
writer-PID asset/record/pointer barriers, INT/TERM/KILL/reap, initial/update
commitment, complete history and reacquisition. The comparison verifies each
checkpoint digest/pointer and observed PID before normalizing those run-specific
identities. It first stopped on a wrong readout key (`revision`); the corrected
instrument reads the actual `checkpoint_revision` field, in a fresh frozen
reading. No product subject changed for that instrument correction. Five wrong
report controls are rejected. These are private installed-package worker tests,
not installed public create interruption or new private-header fault barriers.

Ownership and reservation runs agree on six and seven observations. Synthetic
preparation agrees on nine full case records and 90 individual fault outcomes,
with each independently generated input frozen within its own reading. Native
ownership retains child-alive writer kill/reap and immediate reacquisition. No
real preparation source changed; no new real fidelity or viewer result is claimed.

The [index](index.json) identifies five consecutive ZIP parts and 1,867 raw
members, including logs/JUnit, measured/predecessor source, copied packages,
paired records and instruments. Concatenate the parts in filename order to open
an ordinary ZIP archive. Two deliberately unreadable generated preparation-fault
outputs are listed with native metadata; their reports/JUnit remain present and
permissions were not changed. The [verification](verification.json) checks member
integrity and consistency and rejects missing records, removed disproof, invented
public delivery and wrong measured source. It supplies no historical execution
attestation. Supplemental files have their own ordinary hash index.

The [boundary](boundary-result.json) checks all 1,842 starting paths, append-only
tests/recipes/notes and byte-exact original source segments except `_publish`.
The sole new product helper is `_remove_failed_header`. Eight wrong boundary
inputs are rejected. The same empty-described F change remains open over its
recorded parent; no retirement, partial describe/new or parent closure occurs.
Tier 2 graph coverage is best-effort; exact source, hashes and observed cases
support these bounded claims rather than graph completeness or heuristic edges.
