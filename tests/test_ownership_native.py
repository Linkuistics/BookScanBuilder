"""Writer death/child lifecycle requires real kernel evidence, not a lock mock."""

from pathlib import Path

from ownership_processes import run


def test_real_native_owner_lifecycle_and_wrong_process_lock(tmp_path: Path) -> None:
    result = run(tmp_path / "reading")
    assert result["verified"] is True
    assert result["wrong_process_lock_rejected"] is True
    assert result["case_alias_verified"] is True
