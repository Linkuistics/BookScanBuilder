"""Single-edit guard mutations of the finite receipt-action command.

Each mutant is one exact textual edit of src/bookscan/finite_action.py or the
action routing in finite_protocol.py; the suite must fail with it applied and the
original digests must be restored. Run from the repository root:
    uv run --locked python docs/acceptance/baseline-finite-actions/mutate.py
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

TESTS = [
    "tests/test_finite_action.py",
    "tests/test_finite_protocol.py",
    "tests/test_finite_status.py",
]
action = Path("src/bookscan/finite_action.py")
protocol = Path("src/bookscan/finite_protocol.py")
originals = {action: action.read_text(), protocol: protocol.read_text()}
digests = {p.name: hashlib.sha256(t.encode()).hexdigest() for p, t in originals.items()}

mutants: dict[str, tuple[Path, str, str]] = {
    "static-check-removed": (
        action,
        "    review_facts.check_values(_action(request, _UNREAD))\n",
        "",
    ),
    "integrity-dropped": (
        action,
        "            integrity=_packet_integrity(descriptor, receipt, given),\n",
        "",
    ),
    "authenticate-removed": (
        action,
        """        packet_receipts.authenticate(
            descriptor,
            raw,
            project_id=cast(str, checkpoint.state["project_id"]),
            source_sha256=cast(str, snapshot["source_sha256"]),
        )
""",
        "",
    ),
    "authenticate-ignores-source": (
        action,
        'source_sha256=cast(str, snapshot["source_sha256"]),',
        "source_sha256=packet_receipts.Receipt.parse(raw).identity.source_sha256,",
    ),
    "authenticate-ignores-project": (
        action,
        'project_id=cast(str, checkpoint.state["project_id"]),\n            source',
        "project_id=receipt.identity.project_id,\n            source",
    ),
    "revision-not-advanced": (
        action,
        "checkpoint_revision=checkpoint.revision + 1,",
        "checkpoint_revision=checkpoint.revision,",
    ),
    "retry-reports-new": (
        action,
        "Applied(moved.result, True, None, project_id, moved.facts.review_revision)",
        "Applied(moved.result, False, None, project_id, moved.facts.review_revision)",
    ),
    "commit-reports-replayed": (
        action,
        "            moved.result,\n            False,\n            committed.checkpoint,",
        "            moved.result,\n            True,\n            committed.checkpoint,",
    ),
    "commit-unconditional-expected": (
        action,
        "moved.state, expected=checkpoint, verify_state=verifier",
        "moved.state, expected=None, verify_state=verifier",
    ),
    "commit-warnings-dropped": (
        action,
        "            moved.facts.review_revision,\n            committed.warnings,\n",
        "            moved.facts.review_revision,\n",
    ),
    "progress-not-recorded": (
        action,
        "        progress.applied = applied\n",
        "        pass\n",
    ),
    "current-revision-is-historical": (
        action,
        "current_review_revision=applied.current_review_revision,",
        'current_review_revision=result["review_revision"],',
    ),
    "replayed-not-reported": (
        action,
        "        replayed=applied.replayed,\n",
        "",
    ),
    "receipt-size-unbounded": (
        action,
        "        while len(data) <= MAX_RECEIPT_BYTES:\n",
        "        while True:\n",
    ),
    "receipt-limit-off-by-one": (
        action,
        "        while len(data) <= MAX_RECEIPT_BYTES:\n",
        "        while len(data) < MAX_RECEIPT_BYTES:\n",
    ),
    "receipt-regular-file-unchecked": (
        action,
        "        if not stat.S_ISREG(os.fstat(descriptor).st_mode):\n",
        "        if False:\n",
    ),
    "receipt-open-blocks": (
        action,
        "os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK",
        "os.O_RDONLY | os.O_CLOEXEC",
    ),
    "location-unchecked": (
        action,
        "        if len(names) <= len(parts) or list(names[-len(parts) :]) != parts:\n",
        "        if len(names) <= len(parts):\n",
    ),
    "location-suffix-too-short": (
        action,
        "list(names[-len(parts) :]) != parts",
        "list(names[-1:]) != parts[-1:]",
    ),
    "packet-root-wrong": (
        action,
        "        root = Path(*names[: -len(parts)])\n",
        "        root = Path(*names[:-1])\n",
    ),
    "context-dropped": (
        action,
        '            context["receipt"] = error.context\n',
        "            pass\n",
    ),
    "committed-from-error-ignored": (
        action,
        'committed = applied is not None or getattr(error, "committed", False) is True',
        "committed = applied is not None",
    ),
    "committed-from-progress-ignored": (
        action,
        'committed = applied is not None or getattr(error, "committed", False) is True',
        'committed = getattr(error, "committed", False) is True',
    ),
    "committed-failure-no-verify-remedy": (
        action,
        'remediation=f"{remedy} {VERIFY}" if committed else remedy,',
        "remediation=remedy,",
    ),
    "failure-drops-committed-identity": (
        action,
        "    if applied is not None:\n        _attach(record, applied)\n",
        "    if applied is not None:\n        pass\n",
    ),
    "failure-drops-affected": (
        action,
        '        record["affected_ids"] = applied.result["affected_ids"]\n',
        "",
    ),
    "invalid-project-remedy-generic": (
        action,
        '    if code == "INVALID_PROJECT":\n',
        "    if False:\n",
    ),
    "write-failed-remedy-recovery": (
        action,
        '    if code == "WRITE_FAILED" or getattr(error, "exit_code", 0) == 5:\n',
        "    if False:\n",
    ),
    "oserror-not-classified": (
        action,
        "        OSError,\n        packet_receipts.ReceiptError,\n",
        "        packet_receipts.ReceiptError,\n",
    ),
    "interrupt-exit-lost": (
        action,
        '            exit_code=error.exit_code,\n            message=(\n                "Action interrupted after',
        '            exit_code=1,\n            message=(\n                "Action interrupted after',
    ),
    "success-not-signal-checked": (
        action,
        "            text = _serialize(record, request.json)\n            control.check()\n",
        "            text = _serialize(record, request.json)\n",
    ),
    "human-error-on-stdout": (
        action,
        "        target = stdout if request.json or result == 0 else stderr",
        "        target = stdout",
    ),
    "delivery-failure-masks-success": (
        action,
        "            return result or 5\n",
        "            return result\n",
    ),
    "delivery-failure-unrecorded": (
        action,
        "            if delivery is not None:\n                delivery.failed = True\n",
        "",
    ),
    "warnings-not-on-stderr": (
        action,
        '        if record["status"] != "error":\n            for warning in',
        "        if False:\n            for warning in",
    ),
    "route-removed": (
        protocol,
        "            if request.operation in ACTIONS:\n",
        "            if False:\n",
    ),
}

results: dict[str, dict[str, object]] = {}
try:
    for name, (path, old, new) in mutants.items():
        original = originals[path]
        assert original.count(old) == 1, (name, original.count(old))
        path.write_text(original.replace(old, new))
        try:
            run = subprocess.run(
                ["uv", "run", "--locked", "pytest", "-q", "-x", *TESTS],
                capture_output=True,
                text=True,
                timeout=300,
            )
            killed = run.returncode != 0
            tail = run.stdout.strip().splitlines()[-1] if run.stdout.strip() else ""
        except subprocess.TimeoutExpired:
            # A mutant that makes the suite hang (e.g. a blocking open) is detected.
            killed, tail = True, "timeout"
        results[name] = {"killed": killed, "tail": tail}
        path.write_text(original)
        print(name, "KILLED" if killed else "SURVIVED", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
for path in originals:
    assert hashlib.sha256(path.read_text().encode()).hexdigest() == digests[path.name]
print("restored", {k: v[:12] for k, v in digests.items()})
json.dump(results, sys.stdout, indent=1)
survivors = [name for name, item in results.items() if not item["killed"]]
print("\nsurvivors:", survivors)
