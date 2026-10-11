# prepared-pdf-k18

**Reviews:** prepared-pdf-k13
**Creator:** run a8c952b7-5949-454d-940e-a4b8be18eb50

## Goal

Adversarially review the completed preparation subsystem against its complete
normative contract before geometry consumes it. Produce findings, not fixes.

## Context

- Read `docs/specs/prepared-pdf.md`, `docs/adr/prepared-page-hints.md`, the root
  brief and the complete `prepared-pdf-k13` node brief. Find producer commits by
  their stable handles. The final implementing leaf is `prepared-pdf-k17`; its
  diff starts from preview commit `587afb92`. Review the combined product,
  including inherited source gates, rather than treating the final diff alone
  as the contract. This session closes that node after its final child retires.
- Product boundaries are parsing/reporting, immutable selections, the operation
  owning live sources, the PDF copy/validation adapter and staged publication.
  Focus on reopening/rehashing every invocation, source/path identity and phase
  precedence; the operation must not write from a closed cached preview plan.
- Scrutinize immutable retained-graph reconstruction: scalar types, dictionaries,
  raw encoded streams, arrays, cycles and comparison by source/output node pairs
  independent of storage identity/sharing. Check seven effective geometry values,
  annotation ownership/indirection, marker freshness/non-aliasing, page order/count,
  numeric header/catalog versions, ADBE tuple controls and all warning gates.
- An additional serialization seam preserves filtered zero-byte streams that
  qpdf 12.4.2 otherwise normalizes. `copying.py` temporarily carries their encoded
  dictionaries under an unpredictable private key and appends standard incremental
  revisions using reopened output object numbers. Try to disprove correctness of
  restoration, exact dictionaries, references, xref/trailer/Prev handling, empty
  bytes, failure attribution and absence of reachable restoration tags. Consult
  the cited pinned library source and ISO section; real render equality alone
  cannot establish this seam's general correctness.
- Try to break the exclusive mode-0600 seekable stage, startup-umask final mode,
  completed-stream flush/fsync, no-clobber hard link, pending cancellation and
  signal-blocked link/commit-state boundary. Check pre-commit error precedence,
  cleanup warnings, real EPIPE exits, post-commit success/warnings and observed
  SIGKILL two-name/complete-destination guarantees. There are no product fault
  flags; the private subprocess host launches the installed writer directly.
- `task prepare:check` passed 199 tests, Ruff and strict pyright. Read tests as
  evidence to challenge: source-gate dry/write parity, mutation sensitivity,
  exact directory snapshots, race occupants, barrier/PID observations and
  no-write traps. Re-run targeted checks when useful.
- `docs/acceptance/prepared-pdf.md` and three retained complete-command reports
  record frozen synthetic/real/all acceptance. Compare per-item observations
  and before/after subject digests, not aggregate totals. The combined run has
  13 cases/31 pages, exact matched 300-dpi RGB, geometry and encoded resources;
  each mode retains 18 signal/kill records. Artifact/crop paths are external.
  The first real run was invalidated by an instrument edit and discarded;
  only frozen v2 runs are evidence. Historical dependency/preview reports are
  unchanged and establish their original bounded claims.
- Human visual approval is pending and owned separately by `page-geometry-k4`;
  `corrected-book-k5` checks its disposition. Neither this review nor automated
  pixel equality substitutes for that response. Geometry/OCR/cleanup stay outside
  this review's implementation scope.

## Done when

Record actionable findings with contract/evidence, concrete trigger and source
coordinates against the producer commit. If findings warrant integration, cut
`integrate-review-impl` with this review's handle as its charter immediately
before the first later sibling entry containing live work (currently
`page-geometry-k4`), using the producer's bare `prepared-pdf` slug. Create no
integration if there is nothing actionable. Do not fix the product in this
review or add a competing in-session reviewer.
