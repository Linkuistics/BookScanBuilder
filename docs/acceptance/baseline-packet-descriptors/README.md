# Project-owned packet descriptor store (finite baseline, milestone 3)

Product module: `src/bookscan/packet_descriptors.py`; saved-header wiring in
`src/bookscan/project_header.py`. Tests: `tests/test_packet_descriptors.py` (30 cases) plus
the `packets` store added to the existing store provision/close/rollback parametrizations
(task `process:packet-descriptors-check`).

## Decision

A receipt carries only its issued packet ID, so a descriptor cannot be found from its own
content address. The project therefore stores each descriptor as
`packets/<packet-id>.<sha256>.json`: the file's own digest is the content address and the
packet ID makes lookup exact with no second index to keep in step. `packets` is a fifth
header-identified store (`Header.packets`, JSON key `packets`), provisioned at create beside
assets, checkpoints and native blobs, so replacement is refused like the others and the
frozen compatible-reader fixture (milestone 5) is built against one header shape.

## What it fixes

- `publish(descriptor)`: re-seals through `Descriptor.parse`, writes a private `0600` name,
  fsyncs, reads it back against the digest, links no-clobber, unlinks the private name.
  An existing identical name is accepted only after exact verification; a conflicting one is
  never replaced. Cancellation at every boundary leaves no private name.
- `read(packet_id)`: lists only to find names carrying that one issued ID; exactly one
  match is read through `O_NOFOLLOW` with regular-file, single-link, size-bound, digest,
  stable-identity and directory-identity checks, then parsed and required to name the same
  packet. Unlisted sidecar and private names are ignored, never adopted.
- Errors: absent packet is `INVALID_RECEIPT`/6 `unknown-packet`; any damage to a saved
  descriptor (changed bytes, wrong packet inside, ambiguity, extra link, replaced
  directory) is `INVALID_PROJECT`/3, because it is project corruption rather than a bad
  receipt; unsealed input is `WRITE_FAILED`/5.
- Header: unsupported without or with extra store fields; resume refuses a replaced/missing/
  symlinked `packets` directory before the semantic verifier and releases the lock.

## Not done here

Packet files/PDF/PNG writer, the commands that publish descriptors before the no-replace
directory publication, receipt-used/replay records stored with the checkpoint, and any
native-scale claim. A descriptor alone is not a published packet.

## Checks

`mutate.py` applies 18 single-edit guard mutations and restores the module (digest
`d882a7c28d42`). 17 fail at least one test. The survivor, `file-type-unchecked`, is
equivalent: a directory in the name already fails the link-count check (nlink 2) and an
empty FIFO fails the content-address check, so the regular-file test is defence in depth.
Redundant `owner.verify()` calls (the directory context already verifies ownership) and a
final post-publication re-read were removed after they showed as unkillable.
