import hashlib, json, subprocess, sys
from pathlib import Path

target = Path("src/bookscan/packet_receipts.py")
original = target.read_text()
digest = hashlib.sha256(original.encode()).hexdigest()
mutants = {
 "receipt-id-drops-issuance": ('        "packet_id": packet_id,\n        "identity": identity.record(),', '        "identity": identity.record(),'),
 "receipt-id-drops-identity": ('        "identity": identity.record(),\n        "coverage": coverage.record(),', '        "coverage": coverage.record(),'),
 "id-recomputation-skipped": ('if _receipt_id(packet_id, identity, coverage) != receipt_id:', 'if False:'),
 "descriptor-project-unchecked": ('if identity.project_id != project_id or identity.source_sha256 != source_sha256:', 'if identity.source_sha256 != source_sha256:'),
 "descriptor-source-unchecked": ('if identity.project_id != project_id or identity.source_sha256 != source_sha256:', 'if identity.project_id != project_id:'),
 "unlisted-receipt-accepted": ('if saved is None:\n        raise _fail("Receipt was not issued by this packet descriptor.", "foreign")', 'if saved is None:\n        saved = receipt'),
 "saved-entry-bytes-unchecked": ('if saved != receipt or raw_receipt != saved.raw():', 'if saved != receipt:'),
 "symlink-followed": ('return os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)', 'return os.open(parts[-1], os.O_RDONLY | os.O_CLOEXEC, dir_fd=current)'),
 "directory-symlink-followed": ('part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current', 'part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC, dir_fd=current'),
 "content-digest-unchecked": ('if hasher.hexdigest() != digest:', 'if False:'),
 "header-equality-unchecked": ('if header.text != header_text(receipt):', 'if False:'),
 "address-unchecked": ('if expected_id is not None and expected_id != digest:', 'if False:'),
 "canonical-unchecked": ('if raw != descriptor_bytes(descriptor):', 'if False:'),
 "traversal-allowed": ('any(part in ("", ".", "..") or "\\\\" in part for part in parts)', 'any(part in ("", ".") or "\\\\" in part for part in parts)'),
 "issuance-not-fresh": ('packet_id = "packet-" + secrets.token_hex(16)', 'packet_id = "packet-" + "0" * 32'),
 "native-without-regions": ('if self.view == "native" and not self.regions:', 'if False:'),
 "listed-receipt-digest-unchecked": ('if listed is None or listed != (_sha(item.raw()), len(item.raw())):', 'if listed is None:'),
 "region-order-unchecked": ('if list(self.regions) != sorted(set(self.regions)):', 'if False:'),
 "summary-digests-unchecked": ('_digest(self.unresolved_sha256, "Unresolved roster digest")', 'pass'),
 "cross-issuance-receipts-unchecked": ('if not receipts or any(item.packet_id != packet_id for item in receipts):', 'if not receipts:'),
 "receipt-identities-may-differ": ('if any(item.identity != identity for item in receipts):', 'if False:'),
 "duplicate-receipt-ids-allowed": ('if len({item.receipt_id for item in receipts}) != len(receipts):\n            raise _fail("Descriptor repeats a receipt ID.", "tampered")', 'pass'),
 "header-names-unlisted-file": ('if path not in files or not any(r.receipt_id == receipt_id for r in receipts):', 'if not any(r.receipt_id == receipt_id for r in receipts):'),
 "summary-kind-unchecked": ('if packet_kind == "summary" and not (len(planned) == 1 and is_summary[0]):', 'if False:'),
}
results = {}
try:
    for name, (old, new) in mutants.items():
        assert original.count(old) == 1, (name, original.count(old))
        target.write_text(original.replace(old, new))
        run = subprocess.run(["uv", "run", "--locked", "pytest", "-q", "-x", "tests/test_packet_receipts.py"], capture_output=True, text=True)
        results[name] = {"killed": run.returncode != 0, "tail": run.stdout.strip().splitlines()[-1] if run.stdout.strip() else ""}
        print(name, "KILLED" if run.returncode != 0 else "SURVIVED", flush=True)
finally:
    target.write_text(original)
assert hashlib.sha256(target.read_text().encode()).hexdigest() == digest
print("restored", digest[:12])
json.dump(results, sys.stdout, indent=1)
