# Packet issuance, receipts and descriptor (finite baseline, milestone 3)

Product module: `src/bookscan/packet_receipts.py`. Tests: `tests/test_packet_receipts.py`
(task `process:packet-receipts-check`, 46 cases). Pure data: no project store,
writer ownership, packet directory or renderer is consulted.

## What it fixes

- **Fresh issuance.** `issue()` draws a new opaque `packet-<32 hex>` ID each call;
  every receipt ID (`receipt-<64 hex>`) hashes that packet ID with the project/source/
  review/snapshot identity and the exact coverage. Identical views or summaries at one
  unchanged snapshot therefore get distinct receipts and distinct descriptors.
- **Coverage.** `full` names no regions; `native` names sorted unique `native-NNN`
  regions; `source-native` may name regions; `summary` names no occurrence and carries
  the unresolved-roster and inspection/disposition digests. Digests belong to summaries only.
- **Header identity.** `header_lines(receipt)` is the only source of the visible header:
  project, source snapshot, review revision, export snapshot, packet, receipt, view, box,
  scale and (non-summary) source PDF page, occurrence, image revision, region. `describe()`
  refuses a header that differs from its receipt, so header-to-receipt identity holds by
  construction. The descriptor records each header's digest and file.
- **Descriptor.** Canonical JSON, content address = SHA-256 of its bytes, lists every
  receipt (with its exact file digest) and every packet file (digest, size). `parse()`
  verifies address, grammar, canonical encoding, receipt recomputation, one issuance,
  one identity and header/file references.
- **Authenticity then integrity.** `authenticate()` equals the receipt bytes to the saved
  descriptor entry for this project/source and consults no file, revision or replay.
  `verify_files()` is the separate new-action check: it opens each listed path through a
  directory descriptor with `O_NOFOLLOW`, so a replaced file or directory symlink is a
  changed packet. Files not listed (a viewer's sidecar) are ignored.
- Errors are `INVALID_RECEIPT`/6 with context `malformed`, `foreign`, `tampered` or
  `packet-file-changed` (`receipt-used` belongs to the replay store, not here).

## Not done here

Descriptor storage in the project, the packet file/PDF/PNG writer, the commands that
read receipts, replay, and any native-scale claim. Nothing here records inspection.

## Checks

`mutate.py` applies 24 single-edit guard mutations to the module and restores the
original (digest checked). All 24 fail at least one test. Three early survivors were
resolved rather than excused: three receipt-level checks duplicated the descriptor lookup
(receipt IDs bind issuance and identity) and were removed; several edited-record tests
had used non-canonical JSON so the canonical-encoding guard masked the guard under
test, and now re-encode canonically. One mutant (dropping the descriptor size
comparison in `verify_files`) is equivalent to the digest check and is retained as a
fast reject.

Reading: format, lint, strict types and 3,537 tests (3,491 + 46) pass.
Module digest `2d01c6e51ffa`.
