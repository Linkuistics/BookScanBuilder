"""Reconstruct private checkpoint evidence; host dependencies remain digest references."""

import gzip
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import cast

from PIL import Image

HERE = Path(__file__).resolve().parent


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def equal(left: object, right: object) -> None:
    if left != right:
        raise ValueError("Retained evidence disagreement")


def units(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in ET.fromstring(raw).iter("testcase"):
        key = item.attrib["classname"] + "." + item.attrib["name"]
        if key in result:
            raise ValueError("Repeated test identity")
        result[key] = [p.tag for p in item if p.tag in {"failure", "error", "skipped"}]
    return result


def normalize(value: object, directory: str) -> object:
    if isinstance(value, str):
        return re.sub(
            r"\.bookscan-prepare-[0-9a-f]{32}\.tmp",
            ".bookscan-prepare-OWNED.tmp",
            value.replace(directory, "ARTIFACTS"),
        )
    if isinstance(value, list):
        return [normalize(v, directory) for v in cast(list[object], value)]
    if isinstance(value, dict):
        return {k: normalize(v, directory) for k, v in cast(dict[str, object], value).items()}
    return value


def main() -> int:
    index_raw = (HERE / "index.json.gz").read_bytes()
    index = cast(dict[str, object], json.loads(gzip.decompress(index_raw)))
    parts: list[bytes] = []
    for part in cast(list[dict[str, object]], index["parts"]):
        name = cast(str, part["name"])
        if re.fullmatch(r"raw-[0-9]{3}\.zippart", name) is None:
            raise ValueError("Invalid part name")
        raw = (HERE / name).read_bytes()
        equal((len(raw), sha(raw)), (part["size"], part["sha256"]))
        parts.append(raw)
    raw_archive = b"".join(parts)
    equal((len(raw_archive), sha(raw_archive)), (index["archive_size"], index["archive_sha256"]))
    entries = cast(dict[str, dict[str, object]], index["entries"])
    with zipfile.ZipFile(io.BytesIO(raw_archive)) as archive:
        equal(len(archive.namelist()), len(set(archive.namelist())))
        equal(set(archive.namelist()), {"blobs/" + str(row["sha256"]) for row in entries.values()})
        for row in entries.values():
            raw = archive.read("blobs/" + str(row["sha256"]))
            equal((len(raw), sha(raw)), (row["size"], row["sha256"]))

        def read(name: str) -> bytes:
            return archive.read("blobs/" + str(entries[name]["sha256"]))

        def data(name: str) -> dict[str, object]:
            return cast(dict[str, object], json.loads(read(name)))

        measured = data("frozen/measurement.json")
        prior = data("prior/measurement.json")
        equal(read("frozen/subjects-before.json.gz"), read("frozen/subjects-after.json.gz"))
        subjects = cast(
            dict[str, dict[str, object]],
            json.loads(gzip.decompress(read("frozen/subjects-before.json.gz"))),
        )
        actual_units = units(read("frozen/gate-a.xml"))
        equal(actual_units, units(read("frozen/gate-b.xml")))
        equal(actual_units, measured["units"])
        old_units = cast(dict[str, object], prior["units"])
        equal(old_units, {key: actual_units[key] for key in old_units})
        equal(sorted(set(actual_units) - set(old_units)), measured["new_units"])
        if any(actual_units.values()):
            raise ValueError("Failed unit record")
        equal(units(read("frozen/staff-a.xml")), units(read("frozen/staff-b.xml")))
        equal(measured["public_finite_delivery"], False)
        product = {
            name.removeprefix("product/"): read(name)
            for name in entries
            if name.startswith("product/")
        }
        with zipfile.ZipFile(
            io.BytesIO(read("wheel/bookscan_builder-0.1.0-py3-none-any.whl"))
        ) as wheel:
            equal(set(product), {name for name in wheel.namelist() if name.startswith("bookscan/")})
            equal(sorted(product), measured["wheel_product_members"])
            for name, raw in product.items():
                equal(raw, wheel.read(name))
        native = cast(dict[str, list[dict[str, object]]], measured["native"])
        expected_ids = {
            mode + "-" + phase + "-" + str(number)
            for mode in ("initial", "update")
            for phase in (
                "assets-complete",
                "record-complete",
                "pre-pointer",
                "inside-pointer",
                "post-pointer",
            )
            for number in (0, 2, 15, 9)
        }
        for label in ("source-a", "source-b", "wheel-a", "wheel-b"):
            equal(native[label], native["source-a"])
            report = data("frozen/" + label + "/report.json")
            cases = cast(list[dict[str, object]], report["cases"])
            equal({row["id"] for row in cases}, expected_ids)
            equal(len(cases), len(expected_ids))
            semantic: list[dict[str, object]] = []
            for row in cases:
                case = cast(str, row["id"])
                event = cast(
                    dict[str, object], data("frozen/" + label + "/" + case + ".json")["event"]
                )
                equal(event["writer_pid"], row["writer_pid"])
                equal(event["phase"], row["phase"])
                package = cast(str, event["package"])
                equal(subjects[package]["sha256"], sha(product["bookscan/checkpoints.py"]))
                number = cast(int, row["signal"])
                committed = number == 0 or row["phase"] in {"inside-pointer", "post-pointer"}
                revision = int(cast(bool, row["update"])) + int(committed)
                equal(row["committed"], committed)
                equal(row["revision"], revision)
                equal(row["exit_code"], 0 if number == 0 else -9 if number == 9 else 128 + number)
                equal(row["reacquired"], True)
                base = "frozen/" + label + "/" + case + "/"
                reference = cast(dict[str, object], event["reference"])
                png = read(base + "assets/" + str(reference["id"]) + ".png")
                equal((len(png), sha(png)), (reference["png_size"], reference["png_sha256"]))
                with Image.open(io.BytesIO(png), formats=["PNG"]) as image:
                    equal(
                        (image.mode, image.size, image.tobytes()),
                        ("RGB", (2, 1), bytes.fromhex("0001ff2a80fe")),
                    )
                if revision:
                    digest = cast(str, row["checkpoint_sha256"])
                    equal(read(base + "checkpoints/current.symlink"), (digest + ".json").encode())
                    count = revision
                    while True:
                        raw = read(base + "checkpoints/" + digest + ".json")
                        equal(sha(raw), digest)
                        record = cast(dict[str, object], json.loads(raw))
                        equal(
                            (record["format"], record["version"], record["checkpoint_revision"]),
                            ("BookScanBuilderProject", 1, count),
                        )
                        lock = cast(dict[str, object], event["lock"])
                        equal(record["project_id"], "project-" + str(lock["token"]))
                        equal(
                            set(cast(list[str], record["required_capabilities"])),
                            {
                                "baseline-rgb-v1",
                                "assessment-v1",
                                "review-records-v1",
                                "snapshot-ack-v1",
                            },
                        )
                        state = cast(dict[str, object], record["state"])
                        equal(state["baseline"], reference)
                        equal(state["note"], "next" if count == revision and committed else "first")
                        count -= 1
                        if count == 0:
                            equal(record["previous_sha256"], None)
                            break
                        digest = cast(str, record["previous_sha256"])
                else:
                    equal(row["checkpoint_sha256"], None)
                    if base + "checkpoints/current.symlink" in entries:
                        raise ValueError("Uncommitted checkpoint has a pointer")
                semantic.append(
                    {
                        k: v
                        for k, v in row.items()
                        if k not in {"writer_pid", "checkpoint_sha256", "package"}
                    }
                )
            equal(semantic, native[label])
        for label in ("asset-source-a", "asset-source-b", "asset-wheel-a", "asset-wheel-b"):
            report = data("frozen/" + label + "/result.json")
            sem: dict[str, object] = {"truth": report["truth"], "records": {}}
            rows: dict[str, object] = {}
            for row in cast(list[dict[str, object]], report["records"]):
                barrier = cast(dict[str, object], row["barrier"])
                item = {
                    k: row[k]
                    for k in (
                        "exit",
                        "visible_before",
                        "visible_after",
                        "immediate_reacquisition",
                        "checkpoint",
                    )
                }
                item.update(
                    private_count=len(cast(list[str], row["private_names"])),
                    reference=barrier["reference"],
                    phase=barrier["phase"],
                )
                rows[cast(str, row["case"])] = item
            sem["records"] = rows
            equal(sem, cast(dict[str, object], prior["native"])["source-a"])
        for label in ("preparation-a", "preparation-b"):
            report = data("frozen/" + label + "/report.json")
            directory = cast(str, report["artifacts"])
            faults: list[object] = []
            checks = cast(dict[str, object], report["fault_checks"])
            for row in cast(list[dict[str, object]], checks["observed_signal_and_kill_cases"]):
                barrier = cast(dict[str, object], row["observed_barrier"])
                equal(row["pid"], barrier["pid"])
                equal((row["source_unchanged"], row["writer_reaped"]), (True, True))
                fault = {k: v for k, v in row.items() if k != "pid"}
                fault["observed_barrier"] = {k: v for k, v in barrier.items() if k != "pid"}
                faults.append(normalize(fault, directory))
            equal(
                {"cases": normalize(report["cases"], directory), "faults": faults},
                measured["preparation"],
            )
        equal(measured["preparation"], prior["preparation"])
    equal((HERE / "index.json.gz").read_bytes(), index_raw)
    print(
        json.dumps(
            {
                "entries": len(entries),
                "parts": len(parts),
                "units": len(actual_units),
                "subjects": measured["subjects"],
                "verified": True,
                "public_finite_delivery": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
