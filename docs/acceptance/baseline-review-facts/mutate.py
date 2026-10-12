import hashlib, json, subprocess, sys
from pathlib import Path

target = Path("src/bookscan/review_facts.py")
original = target.read_text()
digest = hashlib.sha256(original.encode()).hexdigest()
mutants = {
 "reject-allowed-for-orientation": ('"orientation-unverified": ("retain-unresolved",),', '"orientation-unverified": ("reject", "retain-unresolved"),'),
 "decision-domain-unchecked": ('if action.decision not in allowed:', 'if False:'),
 "unknown-reason-defaulted": ('allowed = REASON_DECISIONS.get(action.reason)', 'allowed = REASON_DECISIONS.get(action.reason, ("retain-unresolved",))'),
 "blank-note-allowed": ('if type(value) is not str or not value.strip():', 'if type(value) is not str:'),
 "non-utf8-note-allowed": ('        value.encode("utf-8")\n', '        pass\n'),
 "scope-name-unchecked": ('if action.scope not in SCOPES:', 'if False:'),
 "empty-selection-allowed": ('if action.pages is not None and not action.pages:', 'if False:'),
 "reject-does-not-suppress": ('if decided["decision"] == "reject":', 'if False:'),
 "first-decision-wins": ('latest[(cast(str, record["occurrence_id"]), cast(str, record["reason"]))] = record', 'latest.setdefault((cast(str, record["occurrence_id"]), cast(str, record["reason"])), record)'),
 "revision-omits-dispositions": ('            "dispositions": dispositions,\n', ''),
 "revision-omits-inspections": ('            "inspections": inspections,\n        },\n    )\n    latest', '        },\n    )\n    latest'),
 "snapshot-omits-inspections": ('            for record in inspections\n            if record["occurrence_id"] == identifier\n', '            for record in []\n            if record["occurrence_id"] == identifier\n'),
 "no-ack-is-not-none": ('    if not scopes:\n        return None\n', '    if not scopes:\n        scopes = []\n'),
 "currency-unchecked": ('if shown.review_revision != facts.review_revision or shown.snapshot_id != facts.snapshot_id:', 'if False:'),
 "image-revision-unchecked": ('if page["image_revision"] != shown.image_revision:', 'if False:'),
 "project-unchecked": ('if shown.project_id != base.project_id:', 'if False:'),
 "unknown-occurrence-unchecked": ('        if page is None:\n            raise _argument(f"Unknown occurrence {shown.occurrence_id}.")\n', '        if page is None:\n            return\n'),
 "page-action-accepts-summary": ('elif view == "summary" or action.displayed.occurrence_id is None:', 'elif False:'),
 "ack-accepts-page-view": ('        if view != "summary":\n            return ReceiptError(\n                f"Acknowledgement needs', '        if False:\n            return ReceiptError(\n                f"Acknowledgement needs'),
 "scope-receipt-mismatch-allowed": ('if action.scope != shown.view:', 'if False:'),
 "absent-reason-unchecked": ('if action.reason not in present:', 'if False:'),
 "unknown-pages-unchecked": ('        if unknown:\n', '        if False:\n'),
 "integrity-skipped": ('    integrity()\n    record = _record', '    record = _record'),
 "integrity-before-currency": ('    _currency(base, facts, action)\n    integrity()\n', '    integrity()\n    _currency(base, facts, action)\n'),
 "unresolved-digest-ignores-reasons": ('"pages": [{"id": i, "reasons": list(facts.unresolved[i])} for i in facts.page_ids],\n        },\n    )\n\n\ndef inspection_digest', '"pages": [{"id": i, "reasons": []} for i in facts.page_ids],\n        },\n    )\n\n\ndef inspection_digest'),
 "inspection-digest-omits-inspections": ('                "inspections": page["inspections"],\n', ''),
 "inspection-digest-omits-decisions": ('if "decision" in r', 'if False'),
 "selection-not-normalized": ('sorted(set(action.pages))', 'list(action.pages)'),
 "request-digest-omits-displayed": ('        "displayed": action.displayed.record(),\n', ''),
 "request-digest-omits-id": ('        "request_id": action.displayed.request_id,\n        "displayed"', '        "displayed"'),
 "receipt-regions-dropped": ('            coverage.regions,\n        )', '            (),\n        )'),
 "inspections-aliased": ('tuple(copy.deepcopy(inspections))', 'tuple(inspections)'),
 "ack-affected-ids-empty": ('affected = [page["id"] for page in cast(list[dict[str, object]], record["pages"])]', 'affected = []'),
 "status-not-distinguished": ('"acknowledged" if action.kind == "acknowledge" else "recorded"', '"recorded"'),

 "ack-ignores-review-revision": ('        if record["review_revision"] != facts.review_revision:\n            continue\n', ''),
 "retry-conflict-replayed": ('        if retry["request_sha256"] != digest:', '        if False:'),
 "currency-before-retry-lookup": ('    prior = _prior(saved, action, facts)\n', '    _currency(base, facts, action)\n    prior = _prior(saved, action, facts)\n'),
 "integrity-before-retry-lookup": ('    prior = _prior(saved, action, facts)\n', '    integrity()\n    prior = _prior(saved, action, facts)\n'),
 "revision-order-unchecked": ('    if checkpoint_revision <= newest:', '    if False:'),
 "snapshot-currency-unchecked": ('or shown.snapshot_id != facts.snapshot_id', ''),
 "replay-request-reuse-unchecked": ('        if action.displayed.request_id in seen:', '        if False:'),
 "replay-shared-revision-unchecked": ('    if len(set(revisions)) != len(revisions):', '    if False:'),
 "replay-count-unchecked": ('    if len(revisions) != len(retries):', '    if False:'),
 "replay-values-unchecked": ('            check_values(action)\n            _currency(base, facts, action)\n            record =', '            _currency(base, facts, action)\n            record ='),
 "replay-currency-unchecked": ('            _currency(base, facts, action)\n            record =', '            record ='),
 "replay-equality-skipped": ('    if running != saved:', '    if False:'),
 "replay-revision-minimum-unchecked": ('if type(revision) is not int or revision < 2:', 'if type(revision) is not int:'),
}
results = {}
try:
    for name, (old, new) in mutants.items():
        assert original.count(old) == 1, (name, original.count(old))
        target.write_text(original.replace(old, new))
        run = subprocess.run(["uv", "run", "--locked", "pytest", "-q", "-x", "tests/test_review_facts.py"], capture_output=True, text=True)
        results[name] = {"killed": run.returncode != 0, "tail": run.stdout.strip().splitlines()[-1] if run.stdout.strip() else ""}
        print(name, "KILLED" if run.returncode != 0 else "SURVIVED", flush=True)
finally:
    target.write_text(original)
assert hashlib.sha256(target.read_text().encode()).hexdigest() == digest
print("restored", digest[:12])
json.dump(results, sys.stdout, indent=1)
