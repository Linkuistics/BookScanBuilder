# Owned empty store directory removal

`Reservation.remove_directory` removes one explicitly named, unchanged owned
empty child through the held project directory descriptor. Its caller must supply
the captured native identity. It refuses paths, links, other file types, replaced
directories and closed or replaced reservations. Missing children are already
clean. The kernel refuses nonempty directories, including a child populated after
the last metadata check; unknown files, empty directories and dangling links stay
untouched. Integer nanosecond timestamps preserve the existing source-cleanup
identity check. This does not defend against an adversarial same-user rename race.

```sh
task process:empty-store-cleanup-check
task process:source-cleanup-check
task process:initial-import-check
task process:check
```

All 26 new cases were observed failing because the operation was absent. They
pass with the implementation; the complete reservation suite passes 65 cases.
Two frozen runs of the full check pass the same 2,651 classname/name/outcome
records. Their affected source/import checks, four staff checks, nine synthetic
preparation case records and 90 preparation fault records agree item by item.
No real preparation subject changed. The first complete-check attempt stopped
at a test-local strict-typing error; the paired final reading started afresh
after correction. Its preliminary log remains in the evidence.

Five separately copied package mistakes are rejected while unrelated reservation
checks stay green:

| Mistake | Failed cases | Passed cases |
| --- | ---: | ---: |
| Omitted removal | 5 | 60 |
| Omitted captured-identity predicate | 6 | 59 |
| Omitted post-predicate root check | 2 | 63 |
| Float-time metadata comparison | 1 | 64 |
| Accepted paths/traversal | 7 | 58 |

[The index](index.json) gives digests for standard JSON/gzip evidence: raw output,
per-case ledgers, exact copied mistakes, measured source/test/recipe bytes, both
preparation reports and the measurement instruments. Python's `gzip`/`json`
modules or `gzip -dc FILE.json.gz` read them directly. The 9,505 named repository,
virtual-environment, interpreter and selected tool files have matching pre/post
byte hashes and native metadata. This is a named-scope freeze, not a complete
audit of host dynamic libraries or the separate cached staff dependency environment.
Preparation also retains its own before/after input digests. Only each run's
artifact root is normalized for synthetic case comparison; test ledgers compare
classname, name and outcome without path substitution. These records establish
consistency, not independent execution attestation.

The [boundary record](boundary-result.json) and [original prefix identities](prefixes.json)
verify the five changed starting paths, append-only notes/recipe and preservation
of every original test/function/method. Eight deliberately wrong boundary inputs
are rejected. Coverage is best-effort only: [the graph record](coverage.json.gz)
retains exact snippets and both trace directions, while [direct fallback](coverage-fallback.json.gz)
reads/hashes nontracked or excluded files and retains the historical HTML/header
missed ranges. These unchanged bytes support the change boundary, without any
structural or native completeness claim. The heuristic graph edge to a historical
same-name stat symbol is not evidence of an OS call or execution.

This is an internal unfinished part of the live `baseline-finite-k63` owner.
The importer does not yet call this method. Exact owned bootstrap/store/private
entry cleanup, including partly published assets, remains next; public create
remains unavailable. The complete command cancellation/child/result lifetime,
installed writer faults, review/replay, whole-page packets/native refresh,
acknowledgement, export, compatibility, six-case fidelity/resource and browser
reuse obligations remain live. No leaf is retired or partial change sealed.
The existing k28 ownership of missing real truth/reactions/remedies and complete
default/nonrigid acceptance is unchanged.
