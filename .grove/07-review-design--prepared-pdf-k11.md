# prepared-pdf-k11

**Reviews:** prepared-pdf-k9
**Creator:** run 6c59247b-abfa-42e9-b05e-c2fc52b74946


## Goal

Find material defects in preparation's public command and preservation contract
before `prepared-pdf-k10` cuts the working implementation. This is an adversarial,
inspection-only review of the design, not a preparation implementation or a
review of the future correction algorithm.



## Context

Read `docs/specs/prepared-pdf.md` against the confirmed requirements in `plan-k1`
and the root brief's preparation acceptance cases. Read the copying experiment
and its limits in `docs/research/prepared-pdf-copy.md`, its retained per-item
report, and the final script when a claim depends on it. The spec links the
editable browser views; the root Taskfile renders/serves them and reruns the
bounded copying experiment. The committed producer artifact is identified by
the stable handle above.

## Done when

- Check that repeated role selections, optional page expressions, exclusion
  semantics, default order, interior covers, repeated pages and already-assembled
  input form an implementable, unambiguous public command with actionable errors.
- Try to disprove complete visible-page/canvas preservation. In particular,
  examine inherited page attributes, masks/shared decoder resources,
  document-wide colour/optional-content/form dependencies, extension declarations
  and the boundary between acceptable static annotations and unsupported inputs.
  Check material library assumptions against current primary docs or installed
  source. Exact sampled Poppler pixels do not establish arbitrary-PDF support.
- Check whether private per-page role dictionaries remain independent for
  duplicated pages and useful inside a sole-PDF handoff, including unmarked,
  malformed and third-party-edited PDFs. Do not make source discovery or a
  required sidecar a hidden processor dependency.
- Challenge source/output alias checks, occupied/dangling destinations,
  source changes, temporary-file lifetime, validation, no-clobber publication
  races and pre/post-commit cancellation. Identify any promise stronger than the
  proposed mechanism or evidence supports.
- Check each root preparation fixture and public-command test seam against the
  design, including human visual comparisons and first-implementation Taskfile
  needs. Distinguish completed copying checks from future command acceptance.
- Record concrete findings with artifact location, consequence and evidence,
  or explicitly report no material findings. Leave artifact fixes to an
  integration session. Cut an integration before planning only if findings earn
  it, following the review kind's procedure.

## Notes

No in-session reviewer was used by the producer. This leaf supplies the fresh
context before downstream implementation decisions stand. Do not treat its
aimed axes as conclusions to validate; inspect the artifact against the agreed
contract and report what is wrong. The copying probe is intentionally a
dependency experiment rather than shipping preparation code. No ADR was earned
by the local, reversible choices. All increments remain in this workspace and
one tree; the root's later processor/end-to-end verification remains live.
