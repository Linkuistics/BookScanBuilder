import hashlib, json, subprocess, sys
from pathlib import Path

target = Path("src/bookscan/packet_descriptors.py")
original = target.read_text()
digest = hashlib.sha256(original.encode()).hexdigest()
# name -> [(old, new), ...]; every old string must occur exactly once.
mutants = {
 "links-unchecked": [("or before.st_nlink != 1\n", "\n")],
 "file-type-unchecked": [("not stat.S_ISREG(before.st_mode)", "False")],
 "size-cap-dropped": [("or before.st_size > MAX_BYTES", "or False")],
 "truncation-unchecked": [("if not chunk:", "if False:")],
 "identity-recheck-dropped": [("if _identity(before) != _identity(after) or _identity(after) != _identity(current):", "if False:")],
 "packet-binding-dropped-in-listing": [("and match.group(1) == packet_id", "")],
 "ambiguity-ignored": [("if len(found) != 1:", "if False:")],
 "packet-identity-inside-unchecked": [("if descriptor.packet_id != packet_id:", "if False:")],
 "issued-id-unvalidated": [("if type(packet_id) is not str or _PACKET.fullmatch(packet_id) is None:", "if False:")],
 "name-grammar-loose": [('r"(packet-[0-9a-f]{32})\\.([0-9a-f]{64})\\.json"', 'r"(packet-[0-9a-f]{32})\\.(.+)\\.json"')],
 "name-grammar-prefix-only": [("_NAME.fullmatch(name)", "_NAME.match(name)")],
 "unsealed-descriptor-published": [("sealed = packet_receipts.Descriptor.parse(descriptor.raw, descriptor.id)", "sealed = descriptor")],
 "replacing-publication": [("os.link(", "os.replace("), ("dst_dir_fd=directory,\n                        follow_symlinks=False,\n", "dst_dir_fd=directory,\n")],
 "private-name-kept-on-success": [("            else:\n                cleanup()", "            else:\n                pass")],
 "private-name-kept-on-failure": [("                    cleanup()\n                except (DescriptorError, OSError) as failure:", "                    pass\n                except (DescriptorError, OSError) as failure:")],
 "mode-world-readable": [("0o600,", "0o644,")],
 "address-unchecked-in-read": [("if hashlib.sha256(raw).hexdigest() != digest:", "if False:")],
 "store-identity-unchecked": [("or (held.st_dev, held.st_ino) != expected\n            or (current.st_dev, current.st_ino) != expected\n", "\n")],
}
results = {}
try:
    for name, edits in mutants.items():
        text = original
        for old, new in edits:
            assert text.count(old) == 1, (name, old, text.count(old))
            text = text.replace(old, new)
        target.write_text(text)
        try:
            run = subprocess.run(["uv", "run", "--locked", "pytest", "-q", "-x", "tests/test_packet_descriptors.py"], capture_output=True, text=True, timeout=120)
            killed, tail = run.returncode != 0, (run.stdout.strip().splitlines() or [""])[-1]
        except subprocess.TimeoutExpired:
            killed, tail = True, "timeout (hang is a kill)"
        results[name] = {"killed": killed, "tail": tail}
        print(name, "KILLED" if killed else "SURVIVED", flush=True)
finally:
    target.write_text(original)
assert hashlib.sha256(target.read_text().encode()).hexdigest() == digest
print("restored", digest[:12])
json.dump(results, sys.stdout, indent=1)
