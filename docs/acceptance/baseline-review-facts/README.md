# Review facts: Q1 dispositions, inspection, acknowledgement, replay (finite baseline, milestone 3)

Product module: `src/bookscan/review_facts.py`. Tests: `tests/test_review_facts.py`
(task `process:review-facts-check`, 60 cases). Pure data over a detached initial
snapshot: no store, writer ownership, packet file or checkpoint is consulted.

## What it fixes

- **One derivation.** `act()` for a new action and `replay()` for verifying saved
  review state share the same currency and domain rules. A saved history is accepted
  only if re-running every normalized request, at the checkpoint revision of its
  record, rebuilds exactly the saved four lists (`dispositions`, `inspections`,
  `acknowledgements`, `retries`).
- **Q1 domains.** `skew-nonzero` permits `reject|retain-unresolved`; every other
  reason permits `retain-unresolved` only. `REASON_DECISIONS` is asserted equal to
  `triage_record.Reason.allowed_decisions`. A decision outside the domain, an unknown
  reason or a reason absent from the occurrence is `INVALID_ARGUMENT`/2 naming the
  reason, allowed decisions and the exact valid command, before any checkpoint.
  Reject marks only that reason `suggestion-rejected`; orientation, fidelity, extent
  and the universal limitation keep their unresolved coverage. A later decision on
  the same occurrence/reason supersedes the earlier one; the history is kept.
- **Receipt-agnostic boundary.** `Displayed` carries request ID, project, review
  revision, snapshot and (for page views) occurrence/image revision/view/regions.
  `Displayed.from_receipt` adapts a finite receipt; a browser request builds the same
  value. This is B's reuse prerequisite 2 at the state boundary only: receipt
  authenticity stays in `packet_receipts`, HTTP authentication is B's.
- **First-error order inside the boundary.** static value checks, replay verification
  of the saved history, durable retry lookup (identical -> original result, replayed;
  different values or operation on a used ID -> `INVALID_RECEIPT`/6 `receipt-used`),
  revision order, displayed currency (`STALE_ACTION`/6), caller-supplied external
  packet-file integrity, then view-kind/domain checks. A replay never calls integrity.
- **Identities.** `review_revision` hashes project, import value, dispositions and
  inspections with the same domain/encoding as the initial baseline state, so the
  initial value is unchanged. `snapshot_id` hashes the snapshot with effective
  decisions and inspections and excludes acknowledgements, retries and checkpoint
  bookkeeping. An acknowledgement is effective only while its recorded review
  revision is current; an identical re-record changes the revision and therefore
  invalidates it (conservative, as the spec's "review facts invalidate" requires).
  Acknowledgement itself changes neither identity.
- **Selection union.** Several acknowledgement records may cover one snapshot;
  `effective_acknowledgement` unions them per page and reports complete/missing IDs,
  the universal limitation and each individual scope/note. Narrow inspection never
  supplies acknowledgement.
- **Summary digests.** `unresolved_digest` and `inspection_digest` define the two
  values a summary receipt carries.

## Not done here

Wiring into `baseline_state.restore`/`_identities` (which still accepts the initial,
review-empty state only), checkpoint commit of an action, the `disposition`/
`inspected`/`acknowledge` commands, packet content, export. Nothing here records that
a human actually inspected anything.

## Checks

`mutate.py` applies 47 single-edit guard mutations and restores the original (digest
checked); all 47 fail at least one test. Two review passes of the mutants drove
changes rather than excuses: nine replay guards first survived because overlapping
checks masked each other (the final saved-versus-derived equality subsumed per-record
digest, result and record comparisons, which were removed), and the remaining guards
(reused request ID, shared revision, revision below 2, list order) are now each
exercised by a forged but otherwise self-consistent history built by bypassing the
public boundary's lookup/order guard.

Retained as equivalent: none.
