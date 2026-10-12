"""Reconstruct saved-source measurements; host dependencies remain digest references."""

import gzip
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import cast

import pikepdf
from PIL import Image

HERE = Path(__file__).resolve().parent


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def equal(left: object, right: object) -> None:
    if left != right:
        raise ValueError("Retained saved-source evidence disagreement")


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
        return [normalize(v, directory) for v in cast(list[object], value)]
    if isinstance(value, dict):
        return {k: normalize(v, directory) for k, v in cast(dict[str, object], value).items()}
    return value


def main() -> int:
    index_raw = (HERE / "index.json.gz").read_bytes()
    index = cast(dict[str, object], json.loads(gzip.decompress(index_raw)))
    parts: list[bytes] = []
    for row in cast(list[dict[str, object]], index["parts"]):
        name = cast(str, row["name"])
        if re.fullmatch(r"raw-[0-9]{3}\.zippart", name) is None:
            raise ValueError("Invalid archive part path")
        raw = (HERE / name).read_bytes()
        equal((len(raw), sha(raw)), (row["size"], row["sha256"]))
        if len(raw) > 900_000:
            raise ValueError("Oversized archive part")
        parts.append(raw)
    encoded = b"".join(parts)
    equal((len(encoded), sha(encoded)), (index["archive_size"], index["archive_sha256"]))
    entries = cast(dict[str, dict[str, object]], index["entries"])
    with zipfile.ZipFile(io.BytesIO(encoded)) as archive:
        equal(len(archive.namelist()), len(set(archive.namelist())))
        equal(set(archive.namelist()), {"blobs/" + str(v["sha256"]) for v in entries.values()})
        for row in entries.values():
            raw = archive.read("blobs/" + str(row["sha256"]))
            equal((len(raw), sha(raw)), (row["size"], row["sha256"]))

        def read(name: str) -> bytes:
            return archive.read("blobs/" + str(entries[name]["sha256"]))

        def data(name: str) -> dict[str, object]:
            return cast(dict[str, object], json.loads(read(name)))

        equal((HERE / "verify.py").read_bytes(), read("instrument/verify.py"))
        measured, prior = data("frozen/measurement.json"), data("prior/measurement.json")
        equal(read("frozen/subjects-before.json.gz"), read("frozen/subjects-after.json.gz"))
        subjects = cast(
            dict[str, dict[str, object]],
            json.loads(gzip.decompress(read("frozen/subjects-before.json.gz"))),
        )

        def subject(name: str) -> dict[str, object]:
            # /var was frozen; the installed writer reports resolved /private/var.
            # Resolve only this saved spelling alias, with no current host reads.
            key = name if name in subjects else name.removeprefix("/private")
            return subjects[key]

        equal(len(subjects), measured["subjects"])
        equal(
            data("frozen/frozen-status.json"),
            {"completed": True, "unchanged": True, "subjects": len(subjects)},
        )
        actual_units = units(read("frozen/gate-a.xml"))
        equal(actual_units, units(read("frozen/gate-b.xml")))
        equal(actual_units, measured["units"])
        old = cast(dict[str, object], prior["units"])
        equal(old, {key: actual_units[key] for key in old})
        new = sorted(set(actual_units) - set(old))
        equal(new, measured["new_units"])
        equal(len(new), 64)
        if any(actual_units.values()) or not all("test_source_record" in name for name in new):
            raise ValueError("Invalid unit reading")
        for suffix in ("a", "b"):
            equal(
                units(read("frozen/wheel-units-" + suffix + ".xml")),
                {k: actual_units[k] for k in new},
            )
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
                equal(wheel.read(name), raw)
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
        native = cast(dict[str, list[dict[str, object]]], measured["native"])
        for mode in ("source", "header", "checkpoint"):
            for lane in ("source", "wheel"):
                for suffix in ("a", "b"):
                    label = mode + "-" + lane + "-" + suffix
                    report = data("frozen/" + label + "/report.json")
                    equal(
                        cast(dict[str, object], report["truth"])["saved_header"],
                        mode != "checkpoint",
                    )
                    cases = cast(list[dict[str, object]], report["cases"])
                    equal({row["id"] for row in cases}, expected_ids)
                    equal(len(cases), len(expected_ids))
                    semantic: list[dict[str, object]] = []
                    for row in cases:
                        case = cast(str, row["id"])
                        event = cast(
                            dict[str, object],
                            data("frozen/" + label + "/" + case + ".json")["event"],
                        )
                        equal(
                            (event["writer_pid"], event["phase"]), (row["writer_pid"], row["phase"])
                        )
                        equal(
                            subject(cast(str, event["package"]))["sha256"],
                            sha(product["bookscan/checkpoints.py"]),
                        )
                        number = cast(int, row["signal"])
                        committed = number == 0 or row["phase"] in {
                            "inside-pointer",
                            "post-pointer",
                        }
                        revision = int(cast(bool, row["update"])) + int(committed)
                        equal(
                            (row["committed"], row["revision"], row["reacquired"]),
                            (committed, revision, True),
                        )
                        equal(
                            row["exit_code"],
                            0 if number == 0 else -9 if number == 9 else 128 + number,
                        )
                        base = "frozen/" + label + "/" + case + "/"
                        lock = cast(dict[str, object], event["lock"])
                        saved_source: dict[str, object] | None = None
                        if mode == "source":
                            saved_source = cast(dict[str, object], event["source"])
                            source_raw = read(base + "source.pdf")
                            equal(sha(source_raw), saved_source["source_sha256"])
                            equal(row["source_sha256"], saved_source["source_sha256"])
                            equal(row["original_missing"], True)
                            equal(
                                subject(cast(str, event["source_package"]))["sha256"],
                                sha(product["bookscan/source_record.py"]),
                            )
                            entry = entries[base + "source.pdf"]
                            equal(
                                saved_source["snapshot_identity"],
                                {
                                    key: entry[key]
                                    for key in ("device", "inode", "size", "mtime_ns", "ctime_ns")
                                },
                            )
                            equal(len(source_raw), entry["size"])
                            pages: list[dict[str, object]] = []
                            for ordinal, (width, height) in enumerate(
                                ((72, 36), (36, 72), (72, 36)), 1
                            ):
                                pixels = [width * 25 // 6, height * 25 // 6]
                                pages.append(
                                    {
                                        "id": f"occ-{ordinal:06d}",
                                        "source_pdf_page": ordinal,
                                        "geometry": {
                                            "boxes": [["0", "0", str(width), str(height)]] * 5,
                                            "rotate": 0,
                                            "user_unit": "1",
                                            "physical_points": [str(width), str(height)],
                                            "pixels": pixels,
                                            "matrix": [
                                                "25/6",
                                                "0",
                                                "0",
                                                "-25/6",
                                                "0",
                                                str(pixels[1]),
                                            ],
                                            "extent_changed": False,
                                        },
                                        "advisory_hint": None,
                                    }
                                )
                            equal(
                                json.dumps(saved_source["pages"], sort_keys=True),
                                json.dumps(pages, sort_keys=True),
                            )
                            with pikepdf.Pdf.open(
                                io.BytesIO(source_raw), attempt_recovery=False
                            ) as pdf:
                                equal(len(pdf.pages), 3)
                                equal(
                                    [list(page.obj.MediaBox) for page in pdf.pages],
                                    [[0, 0, 72, 36], [0, 0, 36, 72], [0, 0, 72, 36]],
                                )
                            equal(
                                (
                                    saved_source["format"],
                                    saved_source["version"],
                                    saved_source["snapshot"],
                                ),
                                ("BookScanBuilderSource", 1, "source.pdf"),
                            )
                        if mode != "checkpoint":
                            header = data(base + "project.json")
                            equal(header, event["header"])
                            equal(
                                (header["format"], header["version"], header["lock"]),
                                ("BookScanBuilderProject", 1, lock),
                            )
                            equal(header["project_id"], "project-" + str(lock["token"]))
                            equal(header["assets"], event["rgb_directory"])
                            equal(header["checkpoints"], event["directory"])
                            saved_entry = entries[base + "project.json"]
                            equal(
                                header["header"],
                                {"device": saved_entry["device"], "inode": saved_entry["inode"]},
                            )
                            equal(
                                subject(cast(str, event["header_package"]))["sha256"],
                                sha(product["bookscan/project_header.py"]),
                            )
                        reference = cast(dict[str, object], event["reference"])
                        png = read(base + "assets/" + str(reference["id"]) + ".png")
                        equal(
                            (len(png), sha(png)), (reference["png_size"], reference["png_sha256"])
                        )
                        with Image.open(io.BytesIO(png), formats=["PNG"]) as image:
                            equal(
                                (image.mode, image.size, image.tobytes()),
                                ("RGB", (2, 1), bytes.fromhex("0001ff2a80fe")),
                            )
                        if revision:
                            digest = cast(str, row["checkpoint_sha256"])
                            equal(
                                read(base + "checkpoints/current.symlink"),
                                (digest + ".json").encode(),
                            )
                            count = revision
                            while count:
                                raw = read(base + "checkpoints/" + digest + ".json")
                                equal(sha(raw), digest)
                                record = cast(dict[str, object], json.loads(raw))
                                equal(
                                    (
                                        record["format"],
                                        record["version"],
                                        record["checkpoint_revision"],
                                    ),
                                    ("BookScanBuilderProject", 1, count),
                                )
                                equal(record["project_id"], "project-" + str(lock["token"]))
                                state = cast(dict[str, object], record["state"])
                                equal(state["baseline"], reference)
                                if saved_source is not None:
                                    equal(state["source"], saved_source)
                                equal(
                                    state["note"],
                                    "next" if count == revision and committed else "first",
                                )
                                count -= 1
                                if count:
                                    digest = cast(str, record["previous_sha256"])
                                else:
                                    equal(record["previous_sha256"], None)
                        else:
                            equal(row["checkpoint_sha256"], None)
                            if base + "checkpoints/current.symlink" in entries:
                                raise ValueError("Incomplete create has a committed pointer")
                        semantic.append(
                            {
                                k: v
                                for k, v in row.items()
                                if k
                                not in {
                                    "writer_pid",
                                    "checkpoint_sha256",
                                    "package",
                                    "source_sha256",
                                    "source_package",
                                }
                            }
                        )
                    equal(semantic, native[label])
                    equal(
                        [
                            {k: v for k, v in row.items() if k != "original_missing"}
                            for row in semantic
                        ],
                        cast(dict[str, object], prior["native"])["checkpoint-source-a"],
                    )
        for suffix in ("a", "b"):
            report = data("frozen/preparation-" + suffix + "/report.json")
            directory = cast(str, report["artifacts"])
            faults: list[object] = []
            checks = cast(dict[str, object], report["fault_checks"])
            for row in cast(list[dict[str, object]], checks["observed_signal_and_kill_cases"]):
                equal(row["pid"], cast(dict[str, object], row["observed_barrier"])["pid"])
                equal((row["source_unchanged"], row["writer_reaped"]), (True, True))
                item = {k: v for k, v in row.items() if k != "pid"}
                item["observed_barrier"] = {
                    k: v
                    for k, v in cast(dict[str, object], row["observed_barrier"]).items()
                    if k != "pid"
                }
                faults.append(normalize(item, directory))
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
                "new_units": len(new),
                "subjects": len(subjects),
                "verified": True,
                "public_finite_delivery": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
