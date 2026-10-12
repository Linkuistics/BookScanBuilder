"""Verify retained content and per-item outcomes without the measurement filesystem."""

import copy
import hashlib
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import cast

from PIL import Image

from bookscan.records import decode

Record = dict[str, object]
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def outcomes(raw: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for case in ET.fromstring(raw).iter("testcase"):
        key = str(case.get("classname")) + "::" + str(case.get("name"))
        assert key not in result
        assert not any(child.tag in {"failure", "error", "skipped"} for child in case)
        result[key] = "passed"
    assert result
    return result


def verify(index: Record) -> Record:
    raw = (HERE / "evidence.zip").read_bytes()
    assert digest(raw) == index["archive_sha256"]
    assert len(raw) == index["archive_size"]
    members = cast(list[Record], index["members"])
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        assert len(bundle.namelist()) == len(set(bundle.namelist())) == len(members)
        assert set(bundle.namelist()) == {row["path"] for row in members}
        for row in members:
            name = cast(str, row["path"])
            content = bundle.read(name)
            assert digest(content) == row["sha256"] and len(content) == row["size"], name
            assert bundle.getinfo(name).external_attr >> 16 == row["mode"], name
        counts: dict[str, int] = {}
        before = bundle.read("final-a/subjects-before.json")
        for run in ("final-a", "final-b"):
            assert decode(before) == decode(bundle.read(run + "/subjects-before.json"))
            assert decode(before) == decode(bundle.read(run + "/subjects-after.json"))
        for name in ("product", "focused", "staff"):
            first = outcomes(bundle.read("final-a/" + name + ".xml"))
            assert first == outcomes(bundle.read("final-b/" + name + ".xml"))
            counts[name] = len(first)
        frozen = decode(before)
        original_repo = cast(str, index["repository_root"])
        for name in bundle.namelist():
            if name.startswith("subjects/"):
                rel = name.removeprefix("subjects/")
                expected = cast(Record, frozen[original_repo + "/" + rel])
                assert digest(bundle.read(name)) == expected["sha256"], name
        for row in cast(list[Record], json.loads(bundle.read("changed-source.json"))):
            name = cast(str, row["path"])
            assert digest(bundle.read("after/" + name)) == row["after_sha256"]
            assert digest((REPO / name).read_bytes()) == row["after_sha256"], name
        inherited = decode(bundle.read("native-prior.json"))
        fields = cast(Record, inherited["per_case"])
        for run in ("final-a", "final-b"):
            report = decode(bundle.read(run + "/native/report.json"))
            assert {key: report[key] for key in fields} == fields
            state = cast(Record, report["state"])
            baselines = cast(list[Record], state["baselines"])
            pages = cast(list[Record], state["occurrences"])
            hashes: list[str] = []
            for baseline, page in zip(baselines, pages, strict=True):
                path = run + "/native/project/assets/" + cast(str, baseline["id"]) + ".png"
                encoded = bundle.read(path)
                assert digest(encoded) == baseline["png_sha256"]
                with Image.open(io.BytesIO(encoded)) as image:
                    assert image.mode == "RGB" and list(image.size) == baseline["size"]
                    rgb = digest(image.tobytes())
                assert rgb == baseline["rgb_sha256"] == page["rgb_sha256"]
                hashes.append(rgb)
            assert hashes == report["baseline_sha256"] and len(hashes) == 7
            checkpoint = bundle.read(
                run
                + "/native/project/checkpoints/"
                + cast(str, report["checkpoint_sha256"])
                + ".json"
            )
            assert digest(checkpoint) == report["checkpoint_sha256"]
            assert decode(checkpoint)["state"] == state
            assert (
                digest(bundle.read(run + "/native/project/source.pdf"))
                == cast(Record, state["source"])["source_sha256"]
            )
        comparison = decode(bundle.read("comparison.json"))
        assert comparison == index["comparison"]
        assert counts == comparison["paired_test_outcomes"]
        assert len(frozen) == comparison["frozen_subjects"]
    return comparison


def main() -> None:
    index = decode((HERE / "index.json").read_bytes())
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
    print(json.dumps({"verified": result, "wrong_digest_controls_rejected": 2}, indent=2))


if __name__ == "__main__":
    main()
