# Failed writer-lock bootstrap cleanup

When creating, writing or syncing a new lock fails, `ownership.provision`
removes only its unchanged, exclusively created partial `writer.lock`. It compares the named and held file's native
identity, type, link count, size and integer-nanosecond metadata against the last
successful creation/write observation, and checks the held root and original
parent. Replacement entries, links, changed metadata and unavailable creation
identity are retained. Cleanup and descriptor-close errors add notes to the
selected failure. Successful provisioning and normal writer closure retain the
stable lock inode. This offers no adversarial same-user rename-race guarantee.

This also lets initial import remove its owned source and empty reservation when
lock provisioning itself fails. It does not yet clean a failure after successful
provisioning, store bootstrap, partly published assets or other private names.
Public create remains unavailable, and the complete finite reviewer remains live.

```sh
task process:bootstrap-cleanup-check
task process:check
task process:ownership-acceptance ARTIFACTS=/tmp/NEW-ownership-check
task process:reservation-acceptance ARTIFACTS=/tmp/NEW-reservation-check
task prepare:acceptance MODE=synthetic ARTIFACTS=/tmp/NEW-preparation-check
```

The original test-first run reproduced 14 direct failures and two import failures.
The exact final tests reject the copied predecessor source in 25 cases, with
48 unrelated or successful-path cases passing.
The final direct cleanup suite has 25 cases, with two additional import cases.
Both full checks pass the same 2,678 classname/name/outcome records, preserving all
2,651 predecessor cases. The bootstrap recipe passes 138 cases; affected source
and import recipes pass 91 and 94, and staff checks pass four. Both actual native
ownership runs agree on six outcomes, including caught-signal child reaping,
writer kill with a child alive, case aliases and immediate lock reacquisition.
Both reservation runs agree on all seven cases. These are private operation
checks, not installed public-create acceptance.

All nine full synthetic preparation case records and 90 fault test outcomes
agree. Each run's preparation subjects retain their own hashes; independently
constructed synthetic PDFs can have different document-ID bytes. Comparison
normalizes the artifact root, observed writer/child PIDs and private filename
nonces after checking their relationships. Native contention duration is checked
below two seconds in each run rather than compared for exact equality. The raw
reports retain those values. No real preparation subject changed.

Five distinct copied-package faults are rejected while the unchanged ownership
suite stays green:

| Fault | Failed | Passed |
| --- | ---: | ---: |
| Omitted cleanup | 22 | 25 |
| Omitted root checks | 2 | 45 |
| Float-time identity comparison | 2 | 45 |
| Trusted pathname in place of captured identity | 2 | 45 |
| Replaced selected error during descriptor close | 1 | 46 |

The [index](index.json) hashes ordinary JSON/gzip evidence, raw output/JUnit,
predecessor and current source/test/recipe bytes, individual outcomes, copied
fault sources, native/preparation reports and the measurement instruments.
The before/after freeze covers 9,527 named repository, virtual-environment,
interpreter and selected-tool files with byte hashes and native metadata. It
does not audit every host dynamic library or the separate cached staff environment.
The first mutation comparison refused JUnit's module prefix; the first report
comparison refused expected per-run PIDs/nonces/generated PDF IDs. Both instruments
were corrected and rerun without changing any measured product subject.

The read-only boundary checks all 1,795 starting paths, the open empty-described
F change and parent, append-only test/recipe/notes and every original ownership
function/method except the deliberately changed provision operation. Eight wrong
boundary inputs are rejected. Tier 2 coverage checks 1,796 pre-evidence paths;
material source/tests have matching metadata and no recorded gap. Untracked or
excluded bytes are read/hashed directly, with the three historical partial ranges
read separately. Coverage remains best-effort; none of those metadata gaps proves
native execution, source fidelity or complete finite delivery. The index supplies
content integrity, not independent execution attestation.
