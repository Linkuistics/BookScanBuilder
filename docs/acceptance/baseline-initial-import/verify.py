"""Reconstruct bounded import evidence; consistency is not execution attestation."""

import gzip
import hashlib
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

CONTROL_FAILURES = {
    "omit-native-verify": {
        "test_unfinished_or_invalid_import_never_commits[resource]",
        "test_complete_commit_reopens_after_source_loss_with_order_and_duplicates",
        "test_unfinished_or_invalid_import_never_commits[late-corruption]",
    },
    "omit-final-verify": {"test_unfinished_or_invalid_import_never_commits[late-corruption]"},
    "omit-commit-latch": {
        "test_complete_commit_reopens_after_source_loss_with_order_and_duplicates",
        "test_post_commit_native_cleanup_failure_preserves_committed_fact_and_resume",
        "test_cancellation_preserves_actual_checkpoint_boundary[True]",
    },
}
NATIVE_KEYS = (
    "truth_sha256",
    "baseline_sha256",
    "controls",
    "source_loss_resume",
    "resource_loss_resume",
    "native_resume_launch_denied",
    "public_finite_delivery",
    "composition_fidelity_verified",
    "limitations",
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load(directory: Path) -> dict[str, bytes]:
    index = json.loads((directory / "index.json").read_bytes())
    assert index["format"] == "BookScanBuilderInitialImportEvidence" and index["version"] == 1
    chunks: list[bytes] = []
    for item in index["parts"]:
        raw = (directory / item["path"]).read_bytes()
        assert len(raw) == item["bytes"] <= 900000 and sha(raw) == item["sha256"]
        chunks.append(raw)
    raw = b"".join(chunks)
    assert sha(raw) == index["archive_sha256"]
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) and set(names) == set(index["members"])
        members = {name: archive.read(name) for name in names}
    for name, data in members.items():
        assert {"bytes": len(data), "sha256": sha(data)} == index["members"][name]
    return members


def ledger(raw: bytes) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in ET.fromstring(raw).iter("testcase"):
        key = str(item.get("classname")) + "." + str(item.get("name"))
        assert key not in result
        result[key] = [child.tag for child in item if child.tag in ("failure", "error", "skipped")]
    return result


def verify(members: dict[str, bytes]) -> dict[str, int]:
    def record(name: str) -> Any:
        return json.loads(members[name])

    measured = record("run/measurement.json")
    assert measured["complete_finite_handoff"] is False
    before = json.loads(gzip.decompress(members["run/subjects-before.json.gz"]))
    assert before == json.loads(gzip.decompress(members["run/subjects-after.json.gz"]))
    assert len(before) == measured["subjects"]
    supplement = json.loads(gzip.decompress(members["run/base-installation-before.json.gz"]))
    assert supplement == json.loads(gzip.decompress(members["run/base-installation-after.json.gz"]))
    combined = dict(before)
    for name, facts in supplement.items():
        assert name not in combined or combined[name] == facts
        combined[name] = facts
    closure = record("run/closure.json")
    assert closure["primary_subjects"] == len(before)
    assert closure["console_script_subjects"] == len(supplement)
    assert closure["union_subjects"] == len(combined)
    script = members["run/installed-console-script"]
    interpreter = script.splitlines()[0].removeprefix(b"#!").decode()
    assert interpreter in supplement and interpreter == closure["console_interpreter"]
    units = ledger(members["run/gate-a.xml"])
    assert units == ledger(members["run/gate-b.xml"]) == measured["units"]
    assert not any(units.values())
    prior = ledger(members["prior/gate-a.xml"])
    assert {key: value for key, value in units.items() if key in prior} == prior
    new = {key: value for key, value in units.items() if key not in prior}
    assert new == measured["new_units"] and len(new) == 14
    assert all("test_initial_import." in key for key in new)
    for suffix in ("a", "b"):
        for name, modules in (
            ("import", ("test_initial_import", "test_import_assembly", "test_baseline_state")),
            ("assembly", ("test_import_assembly", "test_baseline_state")),
            (
                "wheel-units",
                (
                    "test_initial_import",
                    "test_project_reservation",
                    "test_import_assembly",
                    "test_baseline_state",
                    "test_finite_status",
                    "test_finite_protocol",
                ),
            ),
        ):
            selected = {
                key: value
                for key, value in units.items()
                if any("." + module + "." in key for module in modules)
            }
            assert selected == ledger(members[f"run/{name}-{suffix}.xml"])
    for name, expected in CONTROL_FAILURES.items():
        observed = ledger(members[f"run/{name}.xml"])
        assert observed == measured["controls"][name] and len(observed) == 14
        assert {key.rsplit(".", 1)[1] for key, value in observed.items() if value} == expected
    native = measured["native"]
    for name in ("native-a", "native-b", "wheel-native-a/native", "wheel-native-b/native"):
        found = record(f"run/{name}/report.json")
        assert {key: found[key] for key in NATIVE_KEYS} == native
    prior_native = record("prior/native-report.json")
    assert {key: prior_native[key] for key in NATIVE_KEYS} == native
    assert native["public_finite_delivery"] is False
    assert native["composition_fidelity_verified"] is False
    assert native["limitations"] == [
        "Historical resource/dependency consistency does not attest execution or actual file use.",
        "Helper metadata has a binary digest, not a retained binary-byte/path reference.",
        "Native metadata and baseline equality do not establish source composition fidelity.",
    ]
    assert len(native["baseline_sha256"]) == 7
    assert native["baseline_sha256"][0] == native["baseline_sha256"][-1]
    assert native["source_loss_resume"] and native["resource_loss_resume"]
    status_keys = (
        "baseline_sha256",
        "truth_sha256",
        "source_loss_resume",
        "resource_loss_resume",
        "denied_collection_control",
        "denied_read_control_exit",
        "epipe_exit",
        "complete_finite_handoff",
        "composition_fidelity_verified",
        "limitations",
    )
    for name in ("wheel-native-a", "wheel-native-b"):
        found = record(f"run/{name}/result.json")
        observations: list[dict[str, Any]] = []
        expected = {
            (phase, signum)
            for phase in ("before", "after")
            for signum in ("SIGINT", "SIGTERM", "SIGKILL")
        }
        assert {
            (item["phase"], item["signal"]) for item in found["writer_observations"]
        } == expected
        for item in found["writer_observations"]:
            assert item["owner_pid"] == item["observed_pid"]
            assert item["resumed"] and item["bytes_and_native_unchanged"]
            assert item["exit"] == {"SIGINT": 130, "SIGTERM": 143, "SIGKILL": -9}[item["signal"]]
            observations.append(
                {
                    key: value
                    for key, value in item.items()
                    if key not in ("owner_pid", "observed_pid")
                }
            )
        meaning = {key: found[key] for key in status_keys}
        meaning["writer_observations"] = observations
        assert meaning == measured["installed_status"]
        assert found["denied_collection_control"] and found["denied_read_control_exit"] == 1
        assert found["epipe_exit"] == 5 and found["complete_finite_handoff"] is False
    assert (
        ledger(members["run/staff-a.xml"])
        == ledger(members["run/staff-b.xml"])
        == measured["staff"]
    )
    assert (
        ledger(members["run/prepare-a/fault-checks.xml"])
        == ledger(members["run/prepare-b/fault-checks.xml"])
        == measured["preparation_writer"]
    )
    with zipfile.ZipFile(
        io.BytesIO(members["run/wheel/bookscan_builder-0.1.0-py3-none-any.whl"])
    ) as wheel:
        packaged = {
            name: sha(wheel.read(name)) for name in wheel.namelist() if name.startswith("bookscan/")
        }
    assert packaged == measured["package_members"]
    source = members["repo/src/bookscan/initial_import.py"].decode()
    mutations = {
        "omit-native-verify": ("                native.verify()\n", ""),
        "omit-final-verify": (
            "                    baseline_state.restore(stores, value, check_cancel=check_cancel)",
            "                    return",
        ),
        "omit-commit-latch": (
            "                progress.committed = result.committed",
            "                progress.committed = False",
        ),
    }
    for name, (old, changed) in mutations.items():
        assert source.count(old) == 1
        assert members[
            f"run/controls/{name}/bookscan/initial_import.py"
        ].decode() == source.replace(old, changed)
    for name, digest in packaged.items():
        path = "src/" + name
        assert sha(members["repo/" + path]) == digest
        subjects = [
            data
            for key, data in before.items()
            if key.endswith("/" + path) and not key.startswith("/private/tmp/")
        ]
        assert subjects and all(subject["sha256"] == digest for subject in subjects)
    return {
        "checks": len(units),
        "new_checks": len(new),
        "subjects": len(combined),
        "package_members": len(packaged),
        "controls": len(CONTROL_FAILURES),
    }


if __name__ == "__main__":
    print(json.dumps(verify(load(Path(__file__).parent)), sort_keys=True))
