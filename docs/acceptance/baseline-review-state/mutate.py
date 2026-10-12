import hashlib, json, subprocess, sys
from pathlib import Path

TESTS = ["tests/test_baseline_state.py", "tests/test_finite_status.py"]
state = Path("src/bookscan/baseline_state.py")
status = Path("src/bookscan/finite_status.py")
originals = {state: state.read_text(), status: status.read_text()}
digests = {p.name: hashlib.sha256(t.encode()).hexdigest() for p, t in originals.items()}
mutants = {
 "restore-replays-empty-review": (state, 'facts = _replayed(base, data["review"])', 'facts = _replayed(base, review_facts.initial_review())'),
 "review-revision-unchecked": (state, '            or data["review_revision"] != facts.review_revision\n', ''),
 "snapshot-unchecked": (state, '            or _json(data["snapshot"]) != _json(facts.snapshot)\n', ''),
 "snapshot-id-unchecked": (state, '            or data["snapshot_id"] != facts.snapshot_id\n', ''),
 "image-revisions-unchecked": (state, '            data["image_revisions"] != revisions\n', '            False\n'),
 "base-aliases-import": (state, 'project_id, copy.deepcopy(value), initial_snapshot', 'project_id, value, initial_snapshot'),
 "review-aliased": (state, 'copy.deepcopy(cast(dict[str, list[dict[str, object]]], data["review"])),', 'cast(dict[str, list[dict[str, object]]], data["review"]),'),
 "act-reads-empty-review": (state, '        current.review,\n        action,', '        review_facts.initial_review(),\n        action,'),
 "act-drops-integrity": (state, '        integrity=integrity,\n    )\n    if acted.replayed', '    )\n    if acted.replayed'),
 "act-fixed-revision": (state, 'checkpoint_revision=checkpoint_revision,\n        integrity=integrity,', 'checkpoint_revision=2,\n        integrity=integrity,'),
 "retry-returns-state": (state, '    if acted.replayed:\n', '    if False:\n'),
 "act-mutates-record": (state, 'state = copy.deepcopy(cast(dict[str, object], record))', 'state = cast(dict[str, object], record)'),
 "state-keeps-review": (state, '    state["review"] = acted.review\n', ''),
 "state-keeps-review-revision": (state, '    state["review_revision"] = acted.facts.review_revision\n', ''),
 "state-keeps-snapshot": (state, '    state["snapshot"] = copy.deepcopy(acted.facts.snapshot)\n', ''),
 "state-keeps-snapshot-id": (state, '    state["snapshot_id"] = acted.facts.snapshot_id\n', ''),
 "state-aliases-snapshot": (state, 'state["snapshot"] = copy.deepcopy(acted.facts.snapshot)', 'state["snapshot"] = acted.facts.snapshot'),
 "status-no-acknowledgement": (status, 'acknowledgement=review_facts.effective_acknowledgement(current.facts),', 'acknowledgement=None,'),
 "status-no-dispositions": (status, '"dispositions": decided}', '"dispositions": []}'),
 "status-always-uninspected": (status, 'recorded = "inspected" if page["inspections"] else "uninspected"', 'recorded = "uninspected"'),
 "status-ack-always-complete": (status, "complete: {str(acknowledgement['complete']).lower()}.", "complete: true."),
}
results = {}
try:
    for name, (path, old, new) in mutants.items():
        original = originals[path]
        assert original.count(old) == 1, (name, original.count(old))
        path.write_text(original.replace(old, new))
        run = subprocess.run(["uv", "run", "--locked", "pytest", "-q", "-x", *TESTS], capture_output=True, text=True)
        results[name] = {"killed": run.returncode != 0, "tail": run.stdout.strip().splitlines()[-1] if run.stdout.strip() else ""}
        path.write_text(original)
        print(name, "KILLED" if run.returncode != 0 else "SURVIVED", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
for path in originals:
    assert hashlib.sha256(path.read_text().encode()).hexdigest() == digests[path.name]
print("restored", {k: v[:12] for k, v in digests.items()})
json.dump(results, sys.stdout, indent=1)
