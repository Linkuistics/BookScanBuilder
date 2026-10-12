"""Reconstruct bounded owned-source cleanup evidence; consistency is not execution attestation."""

import gzip
import hashlib
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

CONTROL_FAILURES = {
    "clean-committed-source": {
        "test_post_commit_native_cleanup_failure_preserves_committed_fact_and_resume",
        "test_store_error_after_actual_commit_retains_outcome_latch",
        "test_cancellation_preserves_actual_checkpoint_boundary[True]",
    },
    "float-time-recheck": {"test_remove_file_preserves_nanosecond_identity_change"},
    "omit-source-cleanup": {
        "test_failure_cleans_snapshot_without_sweeping_unknown_children",
        "test_failed_import_keeps_changed_source_or_root[hardlink]",
        "test_unfinished_or_invalid_import_never_commits[late-corruption]",
        "test_failed_import_keeps_changed_source_or_root[modify]",
        "test_cancellation_preserves_actual_checkpoint_boundary[False]",
        "test_unfinished_or_invalid_import_never_commits[resource]",
        "test_failed_import_keeps_changed_source_or_root[symlink]",
        "test_unfinished_or_invalid_import_never_commits[dependency]",
        "test_unfinished_or_invalid_import_never_commits[partial]",
        "test_failed_import_keeps_changed_source_or_root[replace]",
        "test_source_cleanup_error_preserves_selected_failure",
        "test_unfinished_or_invalid_import_never_commits[bad-rgb]",
        "test_failure_before_bootstrap_cleans_snapshot_and_empty_root[False]",
        "test_failure_before_bootstrap_cleans_snapshot_and_empty_root[True]",
        "test_failed_import_keeps_changed_source_or_root[root]",
    },
    "omit-source-identity": {
        "test_failed_import_keeps_changed_source_or_root[replace]",
        "test_failed_import_keeps_changed_source_or_root[modify]",
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
    assert index["format"] == "BookScanBuilderSourceCleanupEvidence" and index["version"] == 1
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
    script = members["run/installed-console-script"]
    interpreter = script.splitlines()[0].removeprefix(b"#!").decode()
    # The measured installation was not moved; /tmp is the macOS /private/tmp alias.
    canonical = "/private" + interpreter if interpreter.startswith("/tmp/") else interpreter
    assert canonical in before
    units = ledger(members["run/gate-a.xml"])
    assert units == ledger(members["run/gate-b.xml"]) == measured["units"]
    assert not any(units.values())
    prior = ledger(members["prior/gate-a.xml"])
    assert {key: value for key, value in units.items() if key in prior} == prior
    new = {key: value for key, value in units.items() if key not in prior}
    assert new == measured["new_units"] and len(new) == 31
    assert all(
        any(module in key for module in ("test_initial_import.", "test_project_reservation."))
        for key in new
    )
    for suffix in ("a", "b"):
        for name, modules in (
            ("import", ("test_initial_import", "test_import_assembly", "test_baseline_state")),
            ("assembly", ("test_import_assembly", "test_baseline_state")),
            ("cleanup", ("test_initial_import", "test_project_reservation")),
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
        assert observed == measured["controls"][name] and len(observed) == 63
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
        io.BytesIO(members["run/dist/bookscan_builder-0.1.0-py3-none-any.whl"])
    ) as wheel:
        packaged = {
            name: sha(wheel.read(name)) for name in wheel.namelist() if name.startswith("bookscan/")
        }
    assert packaged == measured["package_members"]
    mutations = {
        "omit-source-cleanup": ("initial_import.py", "if not progress.committed:", "if False:"),
        "clean-committed-source": ("initial_import.py", "if not progress.committed:", "if True:"),
        "omit-source-identity": (
            "initial_import.py",
            "intake.Identity.read(entry) == saved.private_identity",
            "True",
        ),
        "float-time-recheck": (
            "project_reservation.py",
            "_file_stamp(current) != _file_stamp(entry)",
            "current != entry",
        ),
    }
    for name, (file, old, changed) in mutations.items():
        source = members["repo/src/bookscan/" + file].decode()
        assert source.count(old) == 1
        assert members[f"run/controls/{name}/bookscan/{file}"].decode() == source.replace(
            old, changed
        )
    for name, digest in packaged.items():
        path = "src/" + name
        assert sha(members["repo/" + path]) == digest
        subjects = [
            data
            for key, data in before.items()
            if key.endswith("/" + path) and not key.startswith("/private/tmp/")
        ]
        assert subjects and all(subject["sha256"] == digest for subject in subjects)
    for name, digest in packaged.items():
        expected_suffix = "/installed/lib/python3.12/site-packages/" + name
        installed = [data for key, data in before.items() if key.endswith(expected_suffix)]
        assert installed and all(data["sha256"] == digest for data in installed)
    return {
        "checks": len(units),
        "new_checks": len(new),
        "subjects": len(before),
        "package_members": len(packaged),
        "controls": len(CONTROL_FAILURES),
    }


if __name__ == "__main__":
    print(json.dumps(verify(load(Path(__file__).parent)), sort_keys=True))
