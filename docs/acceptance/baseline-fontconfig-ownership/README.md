# Fontconfig ownership repair: mutation guards and real-import observation

Subject: `src/bookscan/owned_tree.py` (sha256 `4439b03dafea713ab0c45dba8fe1f4df8315e389f32e338451affbe07164e342`).
Original red evidence stays unchanged in `../baseline-fontconfig-cleanup-probe`.

## Mutation guards (`mutate.py <original> <name>`, run against tests/test_fontconfig_cleanup.py)

| Mutant | Observed |
| --- | --- |
| names-unchecked (verify ignores added/removed names) | fails (1 failed, first-failure stop) |
| root-unchecked (root replacement/change not detected) | fails |
| file-stamp-ignored (files/links match unconditionally) | fails |
| dir-identity-ignored (directory identity/mode not bound) | fails |
| prefetch-verify-dropped (remove skips whole-inventory verify) | fails |
| symlink-target-ignored | **survived the 57 real-filesystem cases**: a retargeted link changes inode/ctime, so the full stamp already catches it on a real filesystem (equivalent mutant there). The target/kind comparison is now pinned directly by test_entry_match_binds_link_target_and_kind_beyond_the_stamp, which fails under this mutant. |

Original file was restored after each run and its digest re-verified.

## Real import through the owned snapshot/cache

`task process:initial-state-acceptance` (cache built by `process:setup` into a scratch
directory, not the user cache) completes seven actual native construction imports
through `prepared_fontconfig_snapshot` with the OwnedTree cleanup. Cleanup fails
closed, so a native rewrite of the owned cache would have raised; none did, and no
`.import-resources`, `.cache-*` or `.NEW` names remain. Baseline digests equal those
recorded by earlier evidence (e.g. baseline-rgb-close). `real-import-report.json.gz` is that run's report.

Limits: no hostile same-user race guarantee; salt/remap cache-name policy remains
unverified and unclaimed; this is not full-product acceptance.
