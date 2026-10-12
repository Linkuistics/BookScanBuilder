# Review state in the saved baseline (finite baseline, milestone 3)

Product modules: `src/bookscan/baseline_state.py` (restore/act) and
`src/bookscan/finite_status.py`. Tests: `tests/test_baseline_state.py` and
`tests/test_finite_status.py` (task `process:review-state-check`). The pure model is
`review_facts` (`docs/acceptance/baseline-review-facts`); this step connects it to the
saved payload and the finite reader without adding any command.

## What it fixes

- **Restore replays.** `baseline_state.restore` no longer refuses nonempty review
  lists. It builds a `review_facts.Base` from the verified import value, replays every
  saved normalized request through the action rules, and requires the payload's
  top-level `review_revision`, `snapshot` and `snapshot_id` (and image revisions) to
  equal that derivation. A rehashed payload with an out-of-domain decision, stale or
  foreign displayed identity, reused request ID, unknown occurrence, edited result,
  record without a retry (or the reverse) or an identity that ignores a decision is
  `INVALID_PROJECT`/3 and the input record is never mutated.
- **One derivation for initial and later states.** `initial()` takes its review
  revision, snapshot and snapshot ID from the same replay of an empty review, so the
  initial values are unchanged and no second digest implementation exists.
- **Action transition.** `baseline_state.act` verifies the saved state, then applies
  one action in replay-before-currency order and returns a detached next state for
  the owner to commit through `Checkpoints.commit` with `restore` as verifier. A
  durable identical retry returns the original result with `state` None (nothing to
  commit). Stale/tampered/reused/out-of-domain requests propagate `ReviewError`/
  `ReceiptError` and leave the record untouched. The caller supplies the revision its
  commit will assign and the external packet-file integrity hook; neither is derived
  here.
- **Status shows recorded review.** `baseline status` reports decided reasons per
  page (`dispositions`), recorded inspections, and the effective acknowledgement
  (ids, missing ids, complete flag, scopes) from the saved history alone, with human
  text distinguishing inspected from uninspected pages and partial from complete
  acknowledgement.

## Evidence

`mutate.py` applies 21 single-edit guard mutants (restore replay, each identity
comparison, aliasing of base/review/snapshot, transition fields, integrity/revision
forwarding, retry state, status fields); each fails at least one test. The sweep
restores both sources and asserts their digests.

## Not done here

No `disposition`/`inspected`/`acknowledge` command, receipt adapter or external
packet-file integrity, no packet content, no checkpoint-revision/record binding beyond
`review_facts`' own ordering rule, no predecessor/upgrade fixture.
