"""Reconstruct saved-scope-reader measurements; host dependencies remain references."""

import gzip
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, cast


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def equal(left: object, right: object, context: str) -> None:
    if left != right:
        raise ValueError(context)


def units(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for row in ET.fromstring(raw).iter("testcase"):
        key = row.attrib["classname"] + "." + row.attrib["name"]
        if key in result:
            raise ValueError("Duplicate unit identity")
        result[key] = [child.tag for child in row if child.tag in {"failure", "error", "skipped"}]
    return result


def normalize(value: Any, directory: str) -> Any:
    if isinstance(value, str):
        return re.sub(
            r"\.bookscan-prepare-[0-9a-f]{32}\.tmp",
            ".bookscan-prepare-OWNED.tmp",
            value.replace(directory, "ARTIFACTS"),
        )
    if isinstance(value, list):
        return [normalize(item, directory) for item in cast(list[Any], value)]
    if isinstance(value, dict):
        return {
            key: normalize(item, directory) for key, item in cast(dict[str, Any], value).items()
        }
    return value


def guards(value: Any, path: str = "") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        mapping = cast(dict[str, Any], value)
        if "fontconfig_scope_guard" in mapping:
            guard = cast(dict[str, Any], mapping["fontconfig_scope_guard"])
            equal(set(guard), {"version", "scope", "verification", "limitation"}, "guard fields")
            equal(guard["version"], 3, "scope version")
            if type(guard["version"]) is not int:
                raise ValueError("scope version type")
            equal(
                guard["verification"], "fresh-configuration-only-rediscovery", "no scope-use claim"
            )
            equal(mapping["runtime_resources_verified"], False, "no named-use claim")
            scope = cast(dict[str, list[str]], guard["scope"])
            equal(
                set(scope),
                {
                    "config_files",
                    "config_dirs",
                    "font_dirs",
                    "cache_dirs",
                    "template_dirs",
                    "parsed_files",
                    "effective_font_dirs",
                    "effective_cache_dirs",
                },
                "scope fields",
            )
            for names in scope.values():
                equal(names, sorted(set(names)), "scope ordering")
            rows.append({"id": path, "scope": scope})
        for key, item in mapping.items():
            rows.extend(guards(item, path + "/" + key))
    elif isinstance(value, list):
        for index, item in enumerate(cast(list[Any], value)):
            rows.extend(guards(item, path + "/" + str(index)))
    return rows


def verify(read: dict[str, bytes]) -> dict[str, object]:
    def data(name: str) -> Any:
        return json.loads(read[name])

    measured, prior = data("frozen/measurement.json"), data("prior-measurement.json")
    equal(measured["public_finite_delivery"], False, "no finite delivery")
    equal(read["frozen/subjects-before.json.gz"], read["frozen/subjects-after.json.gz"], "freeze")
    subjects = json.loads(gzip.decompress(read["frozen/subjects-before.json.gz"]))
    equal(len(subjects), measured["subjects"], "subject roster")
    equal(
        data("frozen/frozen-status.json"),
        {"completed": True, "unchanged": True, "subjects": len(subjects)},
        "completed freeze",
    )
    a = units(read["frozen/gate-a.xml"])
    equal(a, units(read["frozen/gate-b.xml"]), "full rerun")
    equal(a, measured["units"], "unit ledger")
    equal(len(a), 1916, "unit roster")
    if any(a.values()):
        raise ValueError("Failed construction")
    equal(prior["units"], {key: a[key] for key in prior["units"]}, "predecessor units")
    new = sorted(set(a) - set(prior["units"]))
    equal(new, measured["new_units"], "new unit ledger")
    equal(len(new), 50, "new units")
    if not all(key.startswith("tests.test_fontconfig_record.") for key in new):
        raise ValueError("Unexpected new scope")
    selected = {
        key: value
        for key, value in a.items()
        if any(
            name in key
            for name in ("test_fontconfig_record.", "test_resource_record.", "test_fontconfig.")
        )
    }
    for suffix in ("a", "b"):
        equal(units(read[f"frozen/wheel-units-{suffix}.xml"]), selected, "wheel units")
    staff = units(read["frozen/staff-a.xml"])
    equal(staff, units(read["frozen/staff-b.xml"]), "staff rerun")
    equal(len(staff), 4, "staff roster")
    if any(staff.values()):
        raise ValueError("Failed staff construction")
    if (
        b"46 failed" not in read["red.txt"]
        or b"cannot import name 'fontconfig_record'" not in read["red.txt"]
    ):
        raise ValueError("Missing initial failing construction")
    if (
        b"4 failed, 46 passed" not in read["consistency-red.txt"]
        or b"DID NOT RAISE" not in read["consistency-red.txt"]
    ):
        raise ValueError("Missing contradictory-inventory disproof")
    prior_native = next(iter(prior["native"].values()))
    expected_ids = [
        "/default_binding/record/binding",
        "/controlled/binding",
        "/rediscovered/binding",
    ]
    for kind in (
        "absolute-file",
        "absolute-directory",
        "relative-file",
        "home-file",
        "xdg-file",
        "xdg-directory",
    ):
        expected_ids.extend(
            f"/optional_include_controls/{kind}/{stage}/binding" for stage in ("before", "after")
        )
    expected_ids.extend(
        f"/template_controls/{kind}/binding"
        for kind in ("absent_scope", "parsed_scope", "include_scope")
    )
    expected_facts: Any = None
    for lane in ("source", "wheel"):
        for suffix in ("a", "b"):
            label = f"assessment-{lane}-{suffix}"
            native = data(f"frozen/{label}/report.json")
            reading = {key: native[key] for key in prior_native}
            equal(reading, prior_native, "native assessment predecessor")
            equal(reading, measured["native"][label], "native assessment ledger")
            equal(
                sha(read[f"frozen/{label}/snapshot.pdf"]), native["source_sha256"], "native source"
            )
            label = f"font-{lane}-{suffix}"
            raw = data(f"frozen/{label}/result.json")
            reading = data(f"frozen/{label}-reader.json")
            equal(reading["runtime_use_verified"], False, "no reader-use claim")
            equal(reading["accepted_project"], False, "no accepted project")
            rows = guards(raw)
            equal([row["id"] for row in rows], expected_ids, "complete native scope roster")
            equal(
                [{key: row[key] for key in ("id", "scope")} for row in reading["facts"]],
                rows,
                "raw scope reader facts",
            )
            for row in reading["facts"]:
                equal(
                    row["controls"],
                    {
                        name: ["INVALID_PROJECT", 3]
                        for name in (
                            "false-runtime-use",
                            "unbound-tree",
                            "missing-parsed",
                            "old-version",
                        )
                    },
                    "native reader controls",
                )
            output = str(Path(raw["commands"][1][-2]).parent)
            normalized = normalize(reading, output)
            equal(
                normalize(reading, output),
                measured["resource_readings"][label],
                "native scope ledger",
            )
            if expected_facts is None:
                expected_facts = normalized
            equal(normalized, expected_facts, "native scope itemwise rerun")
    preparations: list[dict[str, Any]] = []
    for suffix in ("a", "b"):
        raw = data(f"frozen/preparation-{suffix}/report.json")
        directory = raw["artifacts"]
        faults: list[Any] = []
        for row in raw["fault_checks"]["observed_signal_and_kill_cases"]:
            equal(row["pid"], row["observed_barrier"]["pid"], "actual writer PID")
            equal(row["writer_reaped"], True, "writer reaped")
            equal(row["source_unchanged"], True, "source preserved")
            fact = {key: value for key, value in row.items() if key != "pid"}
            fact["observed_barrier"] = {
                key: value for key, value in row["observed_barrier"].items() if key != "pid"
            }
            faults.append(normalize(fact, directory))
        preparations.append({"cases": normalize(raw["cases"], directory), "faults": faults})
    equal(preparations[0], preparations[1], "preparation rerun")
    equal(preparations[0], prior["preparation"], "preparation predecessor")
    equal(preparations[0], measured["preparation"], "preparation ledger")
    mutations = data("mutations/result.json")
    for name, count in (
        ("verification-claim", 2),
        ("directory-binding", 4),
        ("parsed-consistency", 3),
    ):
        rows = units(read[f"mutations/{name}/result.xml"])
        failed = sorted(
            key.split("test_fontconfig_record.", 1)[1] for key, tags in rows.items() if tags
        )
        equal(failed, mutations[name]["failed"], "mutation failures")
        equal(len(failed), count, "isolated guard mutation failures")
        equal(len(rows), 50, "mutation roster")
        freeze = data(f"mutations/{name}/subjects.json")
        equal(freeze["before"], freeze["after"], "mutation freeze")
    with zipfile.ZipFile(
        io.BytesIO(read["wheel/bookscan_builder-0.1.0-py3-none-any.whl"])
    ) as archive:
        equal(
            sorted(name for name in archive.namelist() if name.startswith("bookscan/")),
            measured["wheel_product_members"],
            "wheel roster",
        )
        for name in measured["wheel_product_members"]:
            equal(archive.read(name), read["measured/src/" + name], "wheel/source member")
    return {
        "passed": True,
        "units": len(a),
        "new_units": len(new),
        "subjects": len(subjects),
        "native_scopes_per_reading": 18,
        "native_controls_per_reading": 72,
        "public_finite_delivery": False,
        "runtime_use_verified": False,
    }


def load(directory: Path) -> dict[str, bytes]:
    index = json.loads(gzip.decompress((directory / "index.json.gz").read_bytes()))
    chunks: list[bytes] = []
    for part in index["parts"]:
        raw = (directory / part["name"]).read_bytes()
        equal(sha(raw), part["sha256"], "archive part digest")
        chunks.append(raw)
    with zipfile.ZipFile(io.BytesIO(b"".join(chunks))) as archive:
        equal(len(archive.namelist()), len(set(archive.namelist())), "duplicate archive member")
        equal(set(archive.namelist()), set(index["entries"]), "archive roster")
        result = {name: archive.read(name) for name in archive.namelist()}
    for name, digest in index["entries"].items():
        equal(sha(result[name]), digest, "archive entry digest")
    return result


if __name__ == "__main__":
    print(json.dumps(verify(load(Path(__file__).parent)), sort_keys=True))
