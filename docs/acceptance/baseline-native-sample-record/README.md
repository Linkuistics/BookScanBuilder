# Retained native sample records

Assessment records now reference resolved colour components, exact ranges,
Indexed palettes and recursive base-profile bytes alongside their existing native
sample fields. The reader binds retained bytes to a caller-verified placement,
checks digests and complete channel grids, and preserves Decode, interpolation,
mask metadata and unavailable outcomes. It performs no ICC conversion. Malformed
profiles remain retained bytes; restoring them supplies no conversion or fidelity
verdict. PDF metadata remains opaque, except the checked device/stencil identity.

Legacy device/stencil descriptions are complete and readable. Legacy ICC/Indexed
records lacking resolved dependencies fail explicitly. These earlier construction
captures were not completed compatible-project fixtures. The full checkpoint
verifier and native blob storage remain unfinished.

Run the working checks:

```sh
task process:native-sample-record-check
task process:native-sample-record-acceptance ARTIFACTS=/tmp/NEW-NATIVE-RECORD-READING
uv run --locked python docs/acceptance/baseline-native-sample-record/verify.py
```

The retained evidence contains paired source and installed-wheel runs, exact
measurement subjects before/after, raw JUnit/log/report records, construction
inputs, retained blobs, measured product sources and the wheel. Digest-addressed
archive storage shares identical entries; seven parts stay below 900,001 bytes.
The standalone reader verifies the complete archive inventory and reconstructs
the itemwise comparisons without needing the original temporary paths.

Both full gates passed the same 2,146 cases, preserving all 2,092 predecessor
outcomes and adding 54 native-record constructions. Both installed-wheel gates
passed the same 120 selected cases. Every source/wheel/native reading agreed
itemwise. Each native-record reading covers sixteen PDF occurrences, including
blanks and duplicates, with fourteen contributing samples and thirteen retained
blobs. All original/snapshot PDF paths were removed before restoration. Every
sample rejects changed/missing bytes, foreign placement and false composition
claims. Literal cases cover partial unavailable records, exact rational Decode,
MSB packing and row padding, retained malformed profiles, owner cancellation and
hash-valid corrupt predecessor checkpoints.

Four isolated copied-package omissions demonstrate the checks: digest removal
fails the named packed/profile cases; placement removal fails five placement/type
cases; grid removal fails the short-grid case; colour-binding removal fails two
colour association cases. Unrelated cases pass in each copy. Product bytes were
untouched. The archive retains the mutated subjects and individual test outcomes.
Coherent digest-valid evidence repacks inventing delivery or removing an omission
disproof are rejected; their outcomes are in `evidence-controls.json`.

Four native seven-page assessments retain every predecessor fact except the
explicit new resolved-colour descriptors. Paired staff checks and synthetic
preparation acceptance retain all prior cases and all 38 actual installed writer
signal/kill outcomes. Source, wheel and installed product members are byte-equal.
All 16,743 declared read subjects retained their digests and native metadata.
No real preparation subject, dependency version or native API changed.

This is evidence for retained sample consistency, not complete source composition
fidelity, profile transform execution, monitor calibration, an accepted project,
public reviewer delivery or a human inspection. Native blob transactions and the
full semantic checkpoint boundary must follow, together with the remaining
review/replay/acknowledgement, packets, export, compatibility and fixed-case work
on live `baseline-finite-k63`.
