# Finite baseline commands

Keep the unchanged-baseline command family finite permanently, and reserve
process/review for foreground browser servers from their first release. Export
remains finite for both workflows. The behavioural contract is in
[Page and book geometry](../specs/rotation-processor.md#finite-baseline-review).

This keeps scripts written for finite review from silently hanging when browser
support arrives. Retaining the family adds a lasting help, compatibility and
regression surface, even after browser review is available. Reusing finite
process/review names for a later server was rejected because changing their
blocking meaning would break the shell-loop contract. Hidden mode/version
switches were rejected because a caller could not infer termination from the
command name. Any future retirement requires an explicit command transition
and remedies for existing callers, not an alias with different lifetime.
