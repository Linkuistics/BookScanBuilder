"""Verify the retained red cleanup diagnostic and its negative digest controls."""

import copy
import hashlib
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import cast

Record = dict[str, object]
HERE = Path(__file__).resolve().parent


def verify(index: Record) -> Record:
    raw = (HERE / "evidence.zip").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == index["archive_sha256"]
    assert len(raw) == index["archive_size"]
    members = cast(list[Record], index["members"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) == len(members)
        assert set(names) == {row["path"] for row in members}
        for row in members:
            path = cast(str, row["path"])
            content = archive.read(path)
            assert hashlib.sha256(content).hexdigest() == row["sha256"], path
            assert len(content) == row["size"], path
            assert archive.getinfo(path).external_attr >> 16 == row["mode"], path
        before = json.loads(archive.read("final/subjects-before.json"))
        repository = cast(str, index["repository_root"])
        for name in names:
            if name.startswith("subjects/"):
                expected = before[repository + "/" + name.removeprefix("subjects/")]
                assert hashlib.sha256(archive.read(name)).hexdigest() == expected["sha256"], name
        per_run: list[dict[str, str]] = []
        preservation_records: list[int] = []
        for run in ("a", "b"):
            assert json.loads(archive.read(f"final/{run}/subjects-after.json")) == before
            outcomes: dict[str, str] = {}
            for case in ET.fromstring(archive.read(f"final/{run}/results.xml")).iter("testcase"):
                name = str(case.get("classname")) + "::" + str(case.get("name"))
                assert name not in outcomes
                assert case.find("error") is None and case.find("skipped") is None
                failure = case.find("failure")
                if failure is not None:
                    assert "test_changed_entries_survive_cleanup[" in name
                    assert "Cleanup removed or changed an entry whose ownership was invalid" in (
                        failure.text or ""
                    )
                outcomes[name] = "failure" if failure is not None else "passed"
            per_run.append(outcomes)
            observations: list[object] = [
                cast(object, json.loads(archive.read(name)))
                for name in names
                if name.startswith(f"final/{run}/cases/") and name.endswith("/observation.json")
            ]
            changed = [
                cast(Record, row)
                for row in observations
                if isinstance(row, dict) and "expected" in row
            ]
            assert len(observations) == 57 and len(changed) == 48
            assert all(
                bool(row["expected"]) and row["actual"] == {} and not row["preserved"]
                for row in changed
            )
            native = [cast(list[Record], row) for row in observations if isinstance(row, list)]
            assert len(native) == 1 and len(native[0]) == 1
            write = native[0][0]
            initial = cast(list[int], write["before"])
            held = cast(list[int], write["held_after"])
            named = cast(list[int], write["named_after"])
            assert initial[:2] == held[:2]
            assert initial[:2] != named[:2]
            assert held[3] == 0 and named[3] == 1
            preservation_records.append(len(changed))
        report = json.loads(archive.read("final/report.json"))
        assert per_run[0] == per_run[1] == report["paired_outcomes"]
        assert report["exit_codes"] == [1, 1]
        assert report["controls_passed"] and not report["preservation_passed"]
        assert len(before) == report["frozen_subjects"]
        assert sum(value == "failure" for value in per_run[0].values()) == 48
        assert sum(value == "passed" for value in per_run[0].values()) == 9
        return {
            "controls_passed": 9,
            "required_preservation_failures": preservation_records,
            "native_replacement_observed": True,
            "frozen_subjects": len(before),
            "product_preservation_passed": False,
        }


def main() -> None:
    index = cast(Record, json.loads((HERE / "index.json").read_bytes()))
    result = verify(index)
    for fault in ("archive", "member"):
        wrong = copy.deepcopy(index)
        if fault == "archive":
            wrong["archive_sha256"] = "0" * 64
        else:
            cast(list[Record], wrong["members"])[0]["sha256"] = "0" * 64
        try:
            verify(wrong)
        except AssertionError:
            pass
        else:
            raise AssertionError("Wrong digest control passed: " + fault)
    print(
        json.dumps(
            {"verified_red_diagnostic": result, "wrong_digest_controls_rejected": 2}, indent=2
        )
    )


if __name__ == "__main__":
    main()
