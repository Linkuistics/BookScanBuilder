"""Reconstruct strict JSON/RGB reading; host tools remain digest references."""

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


def equal(left: object, right: object) -> None:
    if left != right:
        raise ValueError("Retained per-item evidence disagreement")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def units(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in ET.fromstring(raw).iter("testcase"):
        key = item.attrib["classname"] + "." + item.attrib["name"]
        if key in result:
            raise ValueError("Duplicate unit identity")
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
        return [normalize(item, directory) for item in cast(list[object], value)]
    if isinstance(value, dict):
        return {
            key: normalize(item, directory) for key, item in cast(dict[str, object], value).items()
        }
    return value


def main() -> int:
    index_bytes = (HERE / "index.json.gz").read_bytes()
    checker = Path(__file__).read_bytes()
    index = cast(dict[str, object], json.loads(gzip.decompress(index_bytes)))
    parts = cast(list[dict[str, object]], index["parts"])
    raw_parts: list[bytes] = []
    for item in parts:
        name = cast(str, item["name"])
        if re.fullmatch(r"raw-[0-9]{3}\.zippart", name) is None:
            raise ValueError("Invalid archive part name")
        raw = (HERE / name).read_bytes()
        equal((len(raw), sha(raw)), (item["size"], item["sha256"]))
        raw_parts.append(raw)
    raw_archive = b"".join(raw_parts)
    equal((len(raw_archive), sha(raw_archive)), (index["archive_size"], index["archive_sha256"]))
    entries = cast(dict[str, dict[str, object]], index["entries"])
    with zipfile.ZipFile(io.BytesIO(raw_archive)) as archive:
        equal(len(archive.namelist()), len(set(archive.namelist())))
        equal(
            set(archive.namelist()), {"blobs/" + str(item["sha256"]) for item in entries.values()}
        )
        for item in entries.values():
            raw = archive.read("blobs/" + str(item["sha256"]))
            equal((len(raw), sha(raw)), (item["size"], item["sha256"]))

        def read(name: str) -> bytes:
            return archive.read("blobs/" + str(entries[name]["sha256"]))

        def data(name: str) -> dict[str, object]:
            return cast(dict[str, object], json.loads(read(name)))

        equal(read("frozen/subjects-before.json"), read("frozen/subjects-after.json"))
        measured = data("frozen/measurement.json")
        current_units = units(read("frozen/units-a.xml"))
        equal(current_units, units(read("frozen/units-b.xml")))
        equal(current_units, measured["units"])
        old_units = cast(dict[str, object], data("prior/measurement.json")["units"])
        equal(old_units, {name: current_units[name] for name in old_units})
        if any(current_units.values()):
            raise ValueError("Unsuccessful unit outcome")
        equal(sorted(set(current_units) - set(old_units)), measured["new_units"])
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
            equal(set(product), set(cast(list[str], measured["wheel_product_members"])))
            for name, raw in product.items():
                equal(raw, wheel.read(name))
        native = cast(dict[str, object], measured["native"])
        predecessor = cast(dict[str, object], data("prior/measurement.json")["native"])
        equal(native["source-a"], predecessor["source-a"])
        equal(read("frozen/controls-before.json"), read("frozen/controls-after.json"))
        controls = cast(list[dict[str, object]], json.loads(read("frozen/controls.json")))
        equal(
            {row["case"] for row in controls},
            {
                "duplicate-top",
                "duplicate-escaped",
                "duplicate-nested",
                "nan",
                "infinity",
                "overflow",
                "surrogate",
            },
        )
        for row in controls:
            equal(row["strict_refused"], True)
            equal(row["mutation_accepted_wrong_subject"], True)
            equal(row["unrelated_control_passed"], True)
        for label in ("source-a", "source-b", "wheel-a", "wheel-b"):
            equal(native[label], native["source-a"])
            result = data("frozen/" + label + "/result.json")
            equal(result["product_sha256"], sha(product["bookscan/assets.py"]))
            truth = cast(dict[str, object], result["truth"])
            rgb = bytes.fromhex(cast(str, truth["rgb_hex"]))
            equal(rgb, bytes((0, 1, 255, 42, 128, 254)))
            records = cast(list[dict[str, object]], result["records"])
            equal(
                {row["case"] for row in records},
                {
                    phase + "-" + str(n)
                    for phase in ("pre-link", "post-link")
                    for n in (0, 2, 15, 9)
                },
            )
            for row in records:
                case = cast(str, row["case"])
                phase, number_text = case.rsplit("-", 1)
                number = int(number_text)
                equal(row["exit"], 0 if number == 0 else -9 if number == 9 else 128 + number)
                equal(row["checkpoint"], False)
                equal(row["immediate_reacquisition"], True)
                visible = cast(list[str], row["visible_after"])
                equal(bool(visible), phase == "post-link" or number == 0)
                equal(bool(row["private_names"]), number == 9)
                if visible:
                    png = read("frozen/" + label + "/" + case + "/assets/" + visible[0])
                    with Image.open(io.BytesIO(png), formats=["PNG"]) as image:
                        equal((image.mode, image.size, image.tobytes()), ("RGB", (2, 1), rgb))
        for label in ("preparation-a", "preparation-b"):
            report = data("frozen/" + label + "/report.json")
            directory = cast(str, report["artifacts"])
            faults: list[object] = []
            checks = cast(dict[str, object], report["fault_checks"])
            for row in cast(list[dict[str, object]], checks["observed_signal_and_kill_cases"]):
                barrier = cast(dict[str, object], row["observed_barrier"])
                equal(row["pid"], barrier["pid"])
                equal((row["source_unchanged"], row["writer_reaped"]), (True, True))
                semantic = {key: value for key, value in row.items() if key != "pid"}
                semantic["observed_barrier"] = {
                    key: value for key, value in barrier.items() if key != "pid"
                }
                faults.append(normalize(semantic, directory))
            equal(
                {"cases": normalize(report["cases"], directory), "faults": faults},
                measured["preparation"],
            )
        equal(measured["preparation"], data("prior/measurement.json")["preparation"])
    equal(Path(__file__).read_bytes(), checker)
    equal((HERE / "index.json.gz").read_bytes(), index_bytes)
    print(
        json.dumps(
            {
                "entries": len(entries),
                "parts": len(parts),
                "units": len(current_units),
                "subjects": measured["subjects"],
                "verified": True,
                "public_finite_delivery": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
