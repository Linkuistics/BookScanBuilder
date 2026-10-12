# Failed empty-store provisioning cleanup

Failed `Stores.provision` now removes only its captured, unchanged empty stores
before a header is published. Each returned directory is captured under held
root/parent descriptors. Removal verifies writer ownership, ancestry, native
identity, mode, link count, size and integer nanosecond timestamps; read-only
atime is excluded. The existing empty-only remover rechecks immediately before
`rmdir`. No enumeration or recursive deletion establishes ownership.

Changed, replaced, populated and unreturned directories remain intact. Any
published or foreign header prevents this rollback. Cleanup notes preserve the
selected failure, and caller-held writer ownership remains held. This is not an
adversarial same-user rename defense or complete import rollback. Cleanup after
individual store creation fails before returning its identity, published-header
rollback and partly published assets still need implementation.

The initial tests reproduced nine failures and one preservation control. Three
further tests rejected inode-only removal after mode, timestamp and
populated-then-emptied mutations. The final 16 cases pass; a copied package with
the exact starting `project_header.py` fails 15 of them and passes the published
header control. The copied module path and digest identify that disproof.

Two frozen Taskfile passes agree on all 2,735 full product test outcomes,
including the 16 new cases. The new `process:empty-provision-cleanup-check`
agrees on 225 cases, private-header cleanup on 160, initial import on 117 and
staff checks on four. Formatting, lint and strict typing pass in both full
runs. All 7,917 named repository/environment/interpreter/selected-tool subjects
retain hashes and native metadata during the measurement. Host dynamic libraries
and the separate cached staff environment are not exhaustively frozen.

Synthetic preparation agrees on nine complete case records, 90 individual fault
test outcomes and 38 observed signal/kill records. Each run's generated subjects
retain their before/after digests. Comparison normalizes artifact roots, positive
writer PIDs and validated private staging UUID filenames; all other semantic
fields agree. Wrong-role and wrong-exit controls fail their respective comparison
while the unrelated record set remains equal. The first comparison deliberately
refused the differing staging UUID names before that normalization was added.
No real preparation subject changed; no new real comparison or visual approval
is claimed.

The two archive parts retain command logs, JUnit outcomes, starting/final
source, measurement inputs, subject digests and synthetic reports. The standard
[integrity index](index.json) records archive/member sizes and SHA-256 digests.
Concatenate `evidence-000.zippart` and `evidence-001.zippart`, in that order, into
an ordinary ZIP, then use Python's `zipfile` module or a ZIP reader to extract it. Digests
prove content integrity, not historical execution. Generated synthetic PDF/PNG
subjects remain at the reports' artifact paths, rather than being a new viewer
acceptance packet.

Only `Stores.provision` changes among original product functions. All 1,855
starting repository files remain present; unrelated bytes are unchanged and the
original tests, Taskfile and task note remain exact prefixes. F remains live in
its original open jj change. The finite create lifecycle, complete rollback,
packets/actions/acknowledgement, export, compatible predecessor, browser reuse
and required public/native/fidelity/six-case acceptance remain unfinished.

Run `python3 docs/acceptance/baseline-empty-provision-cleanup/boundary.py.txt`
from the repository root to reconstruct the archive integrity and exact source
boundary. Its five deliberately wrong boundary inputs must be rejected. The
saved [boundary result](boundary.json) and [Tier 2 coverage](coverage.json) retain
the narrow evidence. Graph coverage is best-effort; the native `stat` edge into
a historical runtime observer is heuristic, and nested callback edges are not
execution proof. Exact source and filesystem tests support the cleanup claims.
