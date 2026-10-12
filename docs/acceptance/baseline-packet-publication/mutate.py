import hashlib, subprocess, sys

P = "src/bookscan/packet_publication.py"
orig = open(P).read()
digest = hashlib.sha256(orig.encode()).hexdigest()
muts = {
    "replacing-rename": (
        "    if function(parent, os.fsencode(source), parent, os.fsencode(target), RENAME_EXCL) != 0:",
        "    if function(parent, os.fsencode(source), parent, os.fsencode(target), 0) != 0:",
    ),
    "no-early-occupied-check": (
        '        else:\n            raise PacketPublicationError(\n                "OUTPUT_EXISTS", "Packet destination is already occupied.", 4\n            )\n        name = _private_name',
        "        else:\n            pass\n        name = _private_name",
    ),
    "no-probe": ("        _probe(parent, name, rename)\n", "        pass\n"),
    "no-mode-widening": (
        "            os.chmod(self._stage_name, 0o777 & ~mask, dir_fd=self._parent)\n",
        "            pass\n",
    ),
    "published-flag-late": (
        "        self.published = True\n        try:\n            final",
        "        try:\n            final",
    ),
}
for name, (a, b) in muts.items():
    assert orig.count(a) == 1, name
    try:
        open(P, "w").write(orig.replace(a, b))
        r = subprocess.run(
            ["uv", "run", "--locked", "pytest", "-q", "tests/test_packet_publication.py"],
            capture_output=True,
            text=True,
        )
        tail = [l for l in r.stdout.splitlines() if l.startswith("FAILED")]
        print(name, "exit", r.returncode, [t.split("::")[1].split(" ")[0] for t in tail])
    finally:
        open(P, "w").write(orig)
assert hashlib.sha256(open(P).read().encode()).hexdigest() == digest
print("restored", digest)
