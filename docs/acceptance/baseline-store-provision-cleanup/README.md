# Individual store provisioning cleanup

Failed initialization of an RGB, checkpoint or native-blob store now cleans its
own captured unchanged empty directory, including failures before the store
returns to `Stores.provision`. Creation holds verified project/root descriptors;
cleanup checks writer ownership, ancestry and native metadata, including integer
nanosecond modification/change times. Ordinary reads may change atime. Removal
uses the existing verified empty-only `rmdir` boundary.

Unknown capture, changed/replaced/populated entries, changed ancestry and an
occupied project header retain the directory with cleanup notes. Cleanup and
descriptor failures preserve the selected exception. This does not complete
published-header/asset/import rollback or defend against an adversarial same-user
rename race. No saved-state format or public constructor signature changes.

The initial tests reproduced 39 failures and three missing-name controls. The
final 51 filesystem cases pass. A copied exact predecessor fails 45 and passes
six controls; a copied inode-only cleanup fails nine mutation cases while the
other 42 pass. Imported module paths/hashes and unchanged copied sources are
recorded. Run `task process:store-provision-cleanup-check` for the focused checks.

Final paired Taskfile runs agree on 2,786 product outcomes, preserving all 2,735
predecessor cases, 410 focused outcomes and four staff outcomes. Formatting,
linting and strict typing pass. Synthetic preparation agrees itemwise on nine
case records, 90 fault outcomes and 38 observed signal/kill records. Each run's
input digests match before/after and direct rehashes. Comparison normalizes
artifact roots, positive PIDs and valid staging UUID names; wrong-role/wrong-exit
controls reject with unrelated records unchanged. No real preparation input changed.

Paired actual private worker runs agree on eight RGB asset cases, forty saved
header/checkpoint cases and eight native-blob cases. Before normalization,
comparison verifies recorded filesystem/lock/store identities, lock tokens,
checkpoint file hashes/current pointers and positive writer PIDs. These are
installed-package worker mechanisms. Actual installed public-create failure
barriers and ordinary-viewer acceptance remain unfinished.

The final main and worker measurements each freeze 7,927 named repository,
environment, interpreter, selected-tool and instrument inputs with unchanged byte
hashes/native metadata. Host dynamic libraries and the staff runner's separately
cached environment are not exhaustively frozen. Preliminary readings omitted
the instrument from their inventory and do not support these final claims.

The [archive index](index.json) records standard ZIP part and member digests.
Concatenate `evidence-*.zippart` in filename order to read the archive. It retains
final logs/JUnit/reports, manifests/instruments, starting/final source, copied
disproof and private worker artifacts. Stored symlink entries have their link
targets as bytes and `kind: symlink` in the member index. Synthetic generated
PDF/PNG views remain at the recorded external paths. Content hashes establish
integrity, not historical execution or native filesystem identity after extraction.

Run `python3 docs/acceptance/baseline-store-provision-cleanup/verify.py.txt` from
the repository root to check archive integrity, paired JUnit outcomes, copied
disproof and the current source boundary. Its deliberately wrong records must
be rejected. The archived comparison instrument additionally checks live native
artifact identities while those external paths remain available.

Only the three original store provisioning methods change, with one added
`provision_store` helper and necessary imports. The other 62 original functions
in the four touched modules retain exact source. All 1,862 starting paths remain;
unrelated bytes and original tests are unchanged, and Taskfile/task notes retain
their original prefixes. Tier 2 coverage is best-effort; the historical observer
`stat` edge is heuristic and nested callbacks are not native execution evidence.
The untracked uv lock was read and hashed directly.

F remains live and unsealed in its original jj change. Complete importer rollback,
finite lifecycle/actions/views/acknowledgement/export, compatibility/browser reuse
and required public/native/fidelity/six-case acceptance remain required.
