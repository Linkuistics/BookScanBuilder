"""Verify retained evidence content; historical OS identity requires the original run."""

import copy
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, cast

FOLDER = Path(__file__).resolve().parent
REPO = FOLDER.parents[2]
PDF_ID = rb"/ID\s*\[\s*<[0-9a-fA-F]{32}>\s*<[0-9a-fA-F]{32}>\s*\]"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read(saved: zipfile.ZipFile, name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(saved.read(name)))


def outcomes(raw: bytes) -> dict[str, str]:
    rows: dict[str, str] = {}
    for case in ET.fromstring(raw).iter("testcase"):
        key = str(case.get("classname")) + "::" + str(case.get("name"))
        assert key not in rows
        assert not any(child.tag in {"failure", "error", "skipped"} for child in case), key
        rows[key] = "passed"
    assert rows
    return rows


def normal(value: Any, run: str, key: str = "") -> Any:
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        result = {normal(k, run): normal(v, run, k) for k, v in mapping.items()}
        assert len(result) == len(mapping)
        return result
    if isinstance(value, list):
        return [normal(v, run, key) for v in cast(list[Any], value)]
    if key in {"writer_pid", "pid"}:
        assert type(value) is int and value > 0
        return "<positive-pid>"
    if isinstance(value, str):
        return re.sub(
            r"\.bookscan-prepare-[a-f0-9]{32}\.tmp",
            ".bookscan-prepare-<uuid>.tmp",
            value.replace(run, "<run>"),
        )
    return value


def workers(saved: zipfile.ZipFile, reading: str, run: str) -> dict[str, Any]:
    folder = reading + "/source-workers/"
    report = read(saved, folder + "report.json")
    result: dict[str, Any] = {}
    for case in report["cases"]:
        key = case["id"]
        assert key not in result
        record = read(saved, folder + key + ".json")
        assert case == record["reading"]
        event = record["event"]
        assert event["writer_pid"] == case["writer_pid"] > 0
        assert event["header"] == read(saved, folder + key + "/project.json")
        assert event["header"]["lock"] == event["lock"]
        source = event["source"]
        raw_source = saved.read(folder + key + "/source.pdf")
        assert sha(raw_source) == source["source_sha256"] == case["source_sha256"]
        assert len(re.findall(PDF_ID, raw_source)) == 1
        digest = case["checkpoint_sha256"]
        if digest is not None:
            raw = saved.read(folder + key + "/checkpoints/" + digest + ".json")
            assert sha(raw) == digest
            assert saved.read(folder + key + "/checkpoints/current").decode() == digest + ".json"
            checkpoint = json.loads(raw)
            assert checkpoint["checkpoint_revision"] == case["revision"]
            assert checkpoint["state"]["source"] == source
            assert checkpoint["state"]["baseline"] == event["reference"]
            assert checkpoint["state"]["note"] == ("next" if case["committed"] else "first")
        else:
            assert folder + key + "/checkpoints/current" not in saved.namelist()
        assert [p["source_pdf_page"] for p in source["pages"]] == [1, 2, 3]
        assert [p["geometry"]["pixels"] for p in source["pages"]] == [
            [300, 150],
            [150, 300],
            [300, 150],
        ]
        checked = dict(case)
        checked["source_sha256"] = sha(re.sub(PDF_ID, b"/ID[<generated><generated>]", raw_source))
        checked["checkpoint_sha256"] = "<checked>" if digest else None
        checked["pages"] = source["pages"]
        checked["document"] = source["document"]
        result[key] = normal(checked, run)
    assert len(result) == 40
    return {"truth": report["truth"], "cases": result}


def preparation(
    saved: zipfile.ZipFile, reading: str, run: str, original_repo: str
) -> dict[str, Any]:
    folder = reading + "/preparation/"
    report = read(saved, folder + "report.json")
    assert report["digests_before"] == report["digests_after"]
    inputs: dict[str, str] = {}
    for path, digest in report["digests_before"].items():
        generated = path.startswith(run + "/preparation/")
        if generated:
            name = reading + path[len(run) :]
        else:
            name = "preparation-subjects/" + str(Path(path).relative_to(original_repo))
        raw = saved.read(name)
        assert sha(raw) == digest
        if generated:
            assert len(re.findall(PDF_ID, raw)) <= 1
            raw = re.sub(PDF_ID, b"/ID[<generated><generated>]", raw)
        inputs[path] = sha(raw)
    return normal(
        {
            "cases": report["cases"],
            "signals": report["fault_checks"]["observed_signal_and_kill_cases"],
            "faults": outcomes(saved.read(folder + "fault-checks.xml")),
            "inputs": inputs,
            "versions": report["versions"],
        },
        run,
    )


def verify(index: dict[str, Any]) -> dict[str, Any]:
    archive = FOLDER / "evidence.zip"
    assert sha(archive.read_bytes()) == index["archive_sha256"]
    with zipfile.ZipFile(archive) as saved:
        assert sorted(saved.namelist()) == sorted(index["members"])
        for name, expected in index["members"].items():
            raw = saved.read(name)
            assert (len(raw), sha(raw)) == (expected["size"], expected["sha256"]), name
        boundary = read(saved, "boundary.json")
        for path, expected in boundary["current_measured_source_sha256"].items():
            assert sha((REPO / path).read_bytes()) == expected, path
        inventories = [
            read(saved, reading + "/subjects-" + when + ".json")
            for reading in ["final-a", "final-b"]
            for when in ["before", "after"]
        ]
        assert all(v == inventories[0] for v in inventories)
        counts: dict[str, int] = {}
        for name in ["focused", "product", "staff"]:
            first = outcomes(saved.read("final-a/" + name + ".xml"))
            assert first == outcomes(saved.read("final-b/" + name + ".xml"))
            counts[name] = len(first)
        a, b = [index["measurement_root"] + "/" + name for name in ["final-a", "final-b"]]
        pa = preparation(saved, "final-a", a, index["repository_root"])
        assert pa == preparation(saved, "final-b", b, index["repository_root"])
        wa = workers(saved, "final-a", a)
        assert wa == workers(saved, "final-b", b)
        summary = {
            "paired_test_outcomes": counts,
            "preparation_cases": len(pa["cases"]),
            "preparation_faults": len(pa["faults"]),
            "preparation_signal_records": len(pa["signals"]),
            "source_workers": len(wa["cases"]),
            "frozen_subjects": len(inventories[0]),
            "passed": True,
        }
        assert summary == read(saved, "comparison.json")
        return summary


def main() -> None:
    index = cast(dict[str, Any], json.loads((FOLDER / "index.json").read_text()))
    summary = verify(index)
    for name in ["archive", "member"]:
        wrong = copy.deepcopy(index)
        if name == "archive":
            wrong["archive_sha256"] = "0" * 64
        else:
            wrong["members"]["boundary.json"]["sha256"] = "0" * 64
        try:
            verify(wrong)
        except AssertionError:
            continue
        raise AssertionError("Wrong digest accepted: " + name)
    print(json.dumps({"verified": summary, "wrong_digest_controls_rejected": 2}, indent=2))


if __name__ == "__main__":
    main()
