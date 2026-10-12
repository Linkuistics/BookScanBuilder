# Exact renderer output cleanup

Rendering now removes only its precreated, held PNG and verified empty private
directory. Recursive temporary-directory removal is gone from this lifetime.
Exclusive creation establishes ownership before the native child starts. The
supported Poppler 26.10.0 writer opens that file with `fopen(..., "wb")`, retaining
its inode; the official versioned source and actual native observations are in
the evidence archive. Rendering settings, independent construction pixels and
the saved project format are unchanged.

At the completed or reaped native invocation boundary, capture the authorized
writes only if the original file identity/mode/single link, complete root stamp
and sole-name inventory remain valid. Check the captured file stamp before and
after decoding and during cleanup. Changed bytes after native capture, changed
modes/links, replacement files/roots, extra names and unknown creation outcomes
retain their supporting workspace. A known successful unlink permits only the
expected empty-root transition; a changed root mode still prevents removal.
APFS directory link counts include regular children, so this transition does
not assume a POSIX directory link count. These checks detect changes; they do
not distinguish hostile concurrent writes from authorized native writes or
guarantee protection against same-user races between checks and removal.

Cleanup preserves an already-selected native/decoder/cancellation error,
including a caller-selected `OSError`. A nonzero native exit is selected before
ownership capture can fail. Each held descriptor closes once; reported close
failures do not cause a retry against a reused descriptor number. Reservation
exit closes only its descriptors and cannot independently delete a changed root.

Use these working recipes:

```sh
task --exit-code process:render-cleanup-check
task --exit-code process:render-cleanup-acceptance ARTIFACTS=/tmp/NEW-RENDER-CHECK
```

Both final sequential readings agree itemwise on 3,378 product tests with
formatting/lint/strict types, 138 focused cases, four staff cases, nine synthetic
preparation cases, 90 preparation faults and 38 preparation signal/kill records.
The native observer checks sixteen actual Poppler writes, fourteen independently
constructed page cases, ten wrong-subject controls and source-loss rendering.
All exact render workspaces are removed. Seven native construction imports retain
the inherited RGB digests and rejection outcomes; eight asset-worker and forty
checkpoint/source-worker records preserve their source/checkpoint/RGB associations.
An actual parked child is cancelled and reaped before workspace cleanup, without
inheriting the held output descriptor. This is private operation evidence, not
installed public-create or complete command-signal acceptance.

All 8,072 declared read subjects retain their bytes/native metadata across both
readings. The complete explicit-cache dependency preflight matches the inherited
identity; no helper is built. Staff's ephemeral uv environment and the complete
host dynamic-library graph remain non-exhaustive. Preparation subjects and real
collection sources are unchanged. The initial failing tests, APFS/selected-error/
observer diagnostics, checked predecessor and isolating guard mutations, paired
logs/JUnit/reports/assets, frozen subjects and instruments are retained in the
[archive](evidence.zip) with its [member index](index.json). The predecessor
rejects thirty preservation cases with four clean controls green. Isolated native
file-core, post-native stamp, root/inventory and empty-root-mode mutations fail
their relevant cases; unrelated per-item outcomes remain green. Five altered
per-item comparison records reject.

Run `uv run --locked python docs/acceptance/baseline-render-cleanup/verify.py`
to verify retained content, current measured code/recipes, paired test outcomes,
decoded RGB/checkpoint/source relationships and both wrong-digest controls.
The original comparator additionally checks the actual measurement filesystem
and itemwise preparation/worker/render/native relationships. Archived content
cannot attest historical execution or a removed workspace's native inode identity.
Symlinks retain their target spelling; two intentionally unreadable permission-
fault outputs retain their native modes and are listed without changing permissions.
Tier 2 coverage at generation 2026-10-15T03:56:10Z matches material source metadata,
best-effort only; flagged vendored header ranges and uv.lock are read directly.
Heuristic trace edges are checked against exact source.

This advances the same live `baseline-finite-k63` change. Fontconfig copied
resources/cache cleanup, complete command cancellation/reap/commit/remedy lifetime
and actual installed public-create barriers remain unfinished. Every original
packet/action/replay/acknowledgement/export/compatibility/B-reuse/fidelity/six-case/
resource obligation remains live. k28 retains missing real truth/reactions/remedies
and complete-default/nonrigid work. No partial retirement, commit boundary,
parent closure or teardown is claimed.
