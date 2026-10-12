# Fontconfig cleanup: failing preservation checks

Both Fontconfig contexts still remove changed entries during cleanup. Two fixed,
sequential actual-native readings agree item by item: all 48 changed-entry checks
fail, while nine clean/native controls pass. Each failed observation records a
nonempty expected inventory followed by an absent root. This is unfinished
implementation work in `baseline-finite-k63`, not a preservation pass.

The cases cover cache and copied-resource contexts, changed bytes, replacement
files, file/root permissions, additional hard links and unknown files,
directories and symlinks. Each runs on return, selected cancellation and selected
processing error. Controls check ordinary cleanup, error identity, replacement-root
retention and native publication. All 7,405 declared source/environment/native
subjects retain their digests and metadata across both readings. OS shared-cache
bytes and complete runtime/dynamic-open coverage are outside that frozen set.

The native publication control keeps a precreated cache file open: Fontconfig
publishes a different inode, leaving the held sentinel unlinked and unchanged.
The pinned build emits cache version 12 and compatibility links 9–11. This
matches [the versioned cache writer](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccache.c)
and [atomic rename implementation](https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcatomic.c).
The renderer's inode-preserving PNG write mechanism cannot be copied unchanged.

Run the diagnostic with an unused artifact directory:

```sh
task process:fontconfig-cleanup-diagnostic ARTIFACTS=/tmp/NEW-FONTCONFIG-DIAGNOSTIC
```

The current diagnostic exits 1; Task reports its failed command. It uses empty,
test-owned font trees and no collection. It supplies no glyph, fidelity, installed
public-create or complete finite-workflow acceptance. The failing tests remain
outside the ordinary product suite until their ownership repair is implemented.
Preserve these historical subjects/results when migrating checks into that repair.

`evidence.zip` and `index.json` retain both complete readings, per-case
observations, generated inputs/surviving outputs, frozen subjects, exact product
and diagnostic source, official native sources and raw XML/logs. The initial
exploratory XML is explicitly invalid: its source changed during execution and
its displaced-root ctime control needed correction. Its totals are not evidence.
The index names one unreadable preparation permission-fault output; its mode
was preserved and its bytes are not included.

Run `uv run --locked python docs/acceptance/baseline-fontconfig-cleanup-probe/verify.py`
to check retained content and two wrong-digest controls. Content alone cannot
establish historical native inode identity or execution.

Routine regressions passed separately: preparation's format/lint/strict types
and 3,378 product tests, four staff checks and synthetic preparation acceptance.
Those results do not clear these failing cleanup checks. Exact-name creation,
native-write ownership, partial-failure retention and selected-error-preserving
cleanup remain to implement in the same live F owner.
