# RGB descriptor cleanup

RGB descriptor release now preserves a failure chosen inside its own operation,
adding close details without replacing cancellation, corruption or private-file
cleanup errors. Each acquired descriptor is closed once. A failed close is never
retried: its number may already refer to another open file. A close-only failure
uses `WRITE_FAILED`/5 for publication/provisioning and `INVALID_PROJECT`/3 for
reading/verification. An already handled caller exception cannot hide that new
failure. Asset bytes, saved formats and complete-orphan semantics are unchanged.

Run `task process:rgb-close-check`. The [34 filesystem cases](../../../tests/test_rgb_close.py)
cover all three release boundaries, multiple failures, actual descriptor reuse,
private cleanup failure and provisioning rollback. The final copied predecessor
fails 29 cases and passes five controls. Removing close notes fails 23; inheriting
an unrelated caller exception fails five; retrying the released descriptor fails
all 34. Copied source paths and digests are checked.

The initial full reading failed because three existing fault substitutions did
not accept the new private optional `writing` keyword. Their signatures were
updated with every ownership assertion preserved. The failed reading is retained
separately; final measurements restarted after all source/test/recipe edits.

Two sequential final readings agree on every individual outcome: 3,116 product
tests with formatting/lint/strict typing, 312 focused tests, four staff tests,
nine synthetic preparation cases, 90 preparation faults and 38 preparation
signal/kill records. Eight actual asset-worker cases verify pre/post-link
visibility, signals/kill, exact RGB and immediate writer reacquisition. Forty
checkpoint/source-worker cases verify saved source/checkpoint relationships and
native identities. Seven native construction imports preserve the predecessor's
exact RGB digests and seven rejection controls, with source/resource-loss resume
and an observed denied native-launch control. These private worker/internal
native checks do not satisfy installed public-create or real fidelity acceptance.

All 8,058 declared subjects retain byte hashes and native metadata through both
readings: source/tests, contracts, manifests, environment/interpreter, tools,
existing helper cache, recorded linked-library files and measured instruments.
Staff's ephemeral uv environment and the complete host dynamic-library graph are
not exhaustively frozen. Cross-run input comparison normalizes only the checked
generated PDF trailer ID. Four altered preparation/worker/source/PID records
are rejected. No real preparation comparison subject changed.

The [index](index.json) identifies each member of the ordinary [ZIP](evidence.zip):
source before/after and diffs, test-first/failed/final logs and JUnit, copied
disproof, paired reports and saved assets, inventories and instruments. Two
unreadable permission-fault outputs retain their permissions and are explicitly
listed; symlink members contain their target bytes.

Run `uv run --locked python docs/acceptance/baseline-rgb-close/verify.py`.
The [content verifier](verify.py) checks archive/member integrity, exact current
measured source, paired individual outcomes and saved source/checkpoint/decoded
RGB relationships. Both wrong digest controls reject. Content cannot attest
historical process execution or native inode identity; the original comparator
also checks the retained filesystem.

The bounded source comparison retains 210 other original source/test files
exactly. Product changes are confined to `assets.py`; existing test changes are
the three substitution signatures, with the new RGB-close test file. Original
task/recipe prefixes and manifest/lock bytes remain exact. Tier 2 graph coverage
reports matching material metadata with no recorded gap; exact source and
executable cases support that best-effort evidence. Final documentation/evidence
reader edits follow measurements and change no measured product/test/recipe.

`baseline-finite-k63` remains live in its same open jj change. Captured rollback
of partly published RGB/native assets and exact private/resource names remains
next. The command cancellation/child/committed-result lifetime, installed public
barriers and every original packet/action/replay/acknowledgement/export/
compatibility/fidelity/six-case obligation remain unfinished. No finite handoff,
leaf retirement or partial task boundary is claimed.
