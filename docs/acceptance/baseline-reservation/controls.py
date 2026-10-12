"""Contest decoded evidence meaning, beyond archive CRC and member hashes."""

import copy
import gzip
import json
from pathlib import Path

from verify import digest, obj, read, verify


def run(directory: Path) -> list[str]:
    original, root = read(directory)
    verify(original, root)
    refused: list[str] = []
    for fault in ("invented-delivery", "removed-disproof", "wrong-source", "erased-limitations"):
        members = copy.copy(original)
        measurement = obj(json.loads(members["run/measurement.json"]))
        if fault == "invented-delivery":
            measurement["complete_finite_handoff"] = True
        elif fault == "removed-disproof":
            del obj(measurement["controls"])["recursive-cleanup"]
        elif fault == "wrong-source":
            name = "repo/src/bookscan/project_reservation.py"
            members[name] += b"\n# altered source control\n"
            for record in ("run/subjects-before.json.gz", "run/subjects-after.json.gz"):
                facts = obj(json.loads(gzip.decompress(members[record])))
                obj(facts[root + name.removeprefix("repo/")])["sha256"] = digest(members[name])
                members[record] = gzip.compress(json.dumps(facts).encode(), mtime=0)
        else:
            native = obj(measurement["native"])
            native["composition_fidelity_verified"] = True
            native["limitations"] = []
            for name in (
                "run/native-a/report.json",
                "run/native-b/report.json",
                "run/wheel-native-a/native/report.json",
                "run/wheel-native-b/native/report.json",
                "prior/native-report.json",
            ):
                record = obj(json.loads(members[name]))
                record.update(native)
                members[name] = json.dumps(record).encode()
        members["run/measurement.json"] = json.dumps(measurement).encode()
        try:
            verify(members, root)
        except AssertionError:
            refused.append(fault)
        else:
            raise AssertionError("False corpus accepted: " + fault)
    verify(original, root)
    return refused


if __name__ == "__main__":
    print(json.dumps({"refused": run(Path(__file__).parent)}, sort_keys=True))
