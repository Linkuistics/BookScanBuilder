# Failed import cleanup under acquired ownership

Initial import now captures its writer lock's native identity, size, mode and
integer-nanosecond metadata after verified acquisition. A failed, uncommitted
import removes that unchanged single-link regular file through the held project
reservation while the writer still holds its kernel lock. Missing names are
already clean. Replaced entries, changed bytes or metadata, links, unavailable
capture and changed ancestry are retained, with notes on the original failure.
Unknown children remain untouched. Source cleanup then allows an empty reservation
to disappear. Successful imports and latched postcommit failures retain the stable
lock inode and saved state. A failed acquisition retains the provisioned lock:
another live writer cannot safely be excluded. There is no adversarial same-user
rename-race guarantee.

Writer context exit now adds an OS descriptor-close error to an already selected
operation error. Normal close failures still raise. This does not promise safe
retry of an ambiguous failed close or repair context-entry/command lifecycle.

```sh
task process:acquired-bootstrap-cleanup-check
task process:check
task geometry:staff-check
task process:initial-import-acceptance ARTIFACTS=/tmp/NEW-import NATIVE_CACHE=/path/to/verified-cache
task prepare:acceptance MODE=synthetic ARTIFACTS=/tmp/NEW-preparation
```

Both final full checks pass the same 2,702 individual outcomes, preserving all
2,678 predecessors and adding 24 cases. The acquired/bootstrap recipes each pass
162; source cleanup passes 114, import/assembly/state 117 and staff four. Paired
native imports retain all seven construction RGB digests, seven context controls
and verified source/resource-loss resume. Paired native ownership observations
retain six mechanisms, including writer kill/reap with a child alive and immediate
reacquisition. Reservation observations agree on seven cases; synthetic preparation
agrees on nine complete cases and 90 fault outcomes. These remain private operation
and native construction checks. Public create and the complete finite reviewer are
unfinished, including header/store/private-name and partly published asset cleanup.

Copied packages fail with the exact predecessor (20 failures), omitted cleanup
(18), ignored captured metadata (2), early writer release (7), ignored commitment
(4), and lost selected close error (2). Their remaining 52/54/70/65/68/70 cases
pass, respectively. Imported module paths and subject digests identify each exact
copy; product source was unchanged for these runs.

The [index](index.json) identifies eight consecutive ZIP parts and their member
hashes. Concatenate the parts in filename order to open an ordinary ZIP archive.
It retains raw output/JUnit, paired records, current and predecessor source,
mutation copies, scripts and named before/after freezes. Two intentionally
unreadable generated preparation-fault outputs are listed separately with native
metadata; their reports and JUnit are retained. No permissions were changed to
archive those outputs, and none is a measured input. The index supplies content
integrity, not execution attestation or relocated saved-project compatibility.

The main freeze checks 9,553 named repository/environment/interpreter/selected-tool
files; the native freeze checks 9,599, adding the existing helper cache and
recorded linked-library files. Each preserves byte hashes and native metadata.
Neither claims every host dynamic library or the separate cached staff environment.
The report comparison initially refused pytest's 3.05/3.07-second stdout timing;
the final instrument validates its exact outcome grammar and normalizes only
elapsed seconds alongside already declared per-run PID/nonces/artifact roots.
All individual fault outcomes remain checked. No measured subject changed for
that instrument correction. No new real preparation or source-fidelity result,
ordinary-viewer/public-create acceptance, review retirement or partial task commit
is claimed.
