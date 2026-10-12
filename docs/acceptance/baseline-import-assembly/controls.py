"""Contest semantic closure after decoding, beyond archive-checksum failures."""

import copy
import json
from pathlib import Path
from typing import Any, cast

from verify import bundle, verify


def main() -> None:
    directory = Path(__file__).resolve().parent
    original = bundle(directory)
    outcomes: dict[str, bool] = {}
    for fault in ["invented-delivery", "removed-disproof", "wrong-source", "erased-limitations"]:
        data = dict(original)
        measured = cast(dict[str, Any], json.loads(data["reading/measurement.json"]))
        if fault == "invented-delivery":
            measured["complete_finite_handoff"] = True
        elif fault == "removed-disproof":
            measured["controls"].pop("omit-final-verification")
            data.pop("reading/omit-final-verification.xml")
        elif fault == "wrong-source":
            data["project/src/bookscan/import_assembly.py"] += b"\n# wrong measured source\n"
        else:
            measured["native"]["composition_fidelity_verified"] = True
            for name in [
                "native-a",
                "native-b",
                "pre-native-valid",
                "wheel-native-a/native",
                "wheel-native-b/native",
            ]:
                native = json.loads(data[f"reading/{name}/report.json"])
                native["composition_fidelity_verified"] = True
                data[f"reading/{name}/report.json"] = json.dumps(native).encode()
        data["reading/measurement.json"] = json.dumps(measured).encode()
        try:
            verify(data)
        except (AssertionError, KeyError):
            outcomes[fault] = True
        else:
            raise AssertionError("False decoded corpus accepted: " + fault)
        assert original == bundle(directory)
        assert verify(copy.copy(original))["complete_finite_handoff"] is False
    print(json.dumps(outcomes, sort_keys=True))


if __name__ == "__main__":
    main()
