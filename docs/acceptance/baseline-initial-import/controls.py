"""Contest decoded evidence semantics after archive integrity has been checked."""

import copy
import json
from pathlib import Path

from verify import load, verify


def main() -> None:
    original = load(Path(__file__).parent)
    verify(original)
    rejected: list[str] = []
    for fault in ("invented-delivery", "removed-disproof", "wrong-source", "erased-limitations"):
        members = copy.deepcopy(original)
        measured = json.loads(members["run/measurement.json"])
        if fault == "invented-delivery":
            measured["complete_finite_handoff"] = True
        elif fault == "removed-disproof":
            name = "omit-final-verify"
            measured["controls"][name] = {key: [] for key in measured["controls"][name]}
            raw = members[f"run/{name}.xml"].decode()
            import xml.etree.ElementTree as ET

            tree = ET.fromstring(raw)
            for case in tree.iter("testcase"):
                for child in list(case):
                    if child.tag in ("failure", "error"):
                        case.remove(child)
            members[f"run/{name}.xml"] = ET.tostring(tree)
        elif fault == "wrong-source":
            path = "repo/src/bookscan/initial_import.py"
            members[path] = members[path].replace(b"native.verify()", b"native.verify_fake()")
        else:
            measured["native"]["limitations"] = []
            for name in (
                "run/native-a/report.json",
                "run/native-b/report.json",
                "run/wheel-native-a/native/report.json",
                "run/wheel-native-b/native/report.json",
                "prior/native-report.json",
            ):
                record = json.loads(members[name])
                record["limitations"] = []
                members[name] = json.dumps(record).encode()
        members["run/measurement.json"] = json.dumps(measured).encode()
        try:
            verify(members)
        except AssertionError:
            rejected.append(fault)
        else:
            raise AssertionError("Accepted altered decoded corpus: " + fault)
    print(json.dumps({"rejected": rejected}, sort_keys=True))


if __name__ == "__main__":
    main()
