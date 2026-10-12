"""Guard mutations of src/bookscan/finite_create.py against tests/test_finite_create.py.

Each mutant must fail at least one case; the original bytes are restored and their
digest re-verified after every run. Run from the repository root:
    uv run --locked python docs/acceptance/baseline-finite-create/mutate.py REPORT.json
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

TARGET = Path("src/bookscan/finite_create.py")
MUTANTS = {
    "committed-fact-dropped": (
        "    committed = progress.committed or (\n"
        "        isinstance(error, checkpoints.CheckpointError) and error.committed\n    )\n",
        "    committed = False\n",
    ),
    "post-serialize-check-dropped": (
        "            text = _serialize(record, request.json)\n            control.check()\n",
        "            text = _serialize(record, request.json)\n",
    ),
    "verify-remedy-dropped": (
        '        if committed:\n            remedy = f"{remedy} {VERIFY}"\n',
        "",
    ),
    "interrupt-exit-collapsed": (
        "            exit_code=error.exit_code,\n            message=(\n",
        "            exit_code=130,\n            message=(\n",
    ),
    "delivery-failure-unrecorded": (
        "            if delivery is not None:\n                delivery.failed = True\n",
        "",
    ),
    "uncommitted-success-accepted": (
        "            if not progress.committed or progress.result is None:\n"
        "                raise checkpoints.CheckpointError(\n"
        '                    "WRITE_FAILED", "Create returned without a committed checkpoint.", 5\n'
        "                )\n",
        "            if False:\n                pass\n",
    ),
    "warnings-not-carried": (
        "        warnings=[_warning(item) for item in result.warnings],\n",
        "        warnings=[],\n",
    ),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    original = TARGET.read_bytes()
    expected = digest(original)
    report: dict[str, object] = {"source_sha256": expected, "mutants": {}}
    baseline = subprocess.run(
        ["uv", "run", "--locked", "pytest", "-q", "tests/test_finite_create.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    report["original"] = baseline.stdout.strip().splitlines()[-1]
    assert baseline.returncode == 0, baseline.stdout
    try:
        for name, (old, new) in MUTANTS.items():
            text = original.decode()
            assert text.count(old) == 1, name
            TARGET.write_text(text.replace(old, new))
            result = subprocess.run(
                ["uv", "run", "--locked", "pytest", "-q", "tests/test_finite_create.py"],
                capture_output=True,
                text=True,
                check=False,
            )
            failed = [
                line.split("::")[1].split(" ")[0]
                for line in result.stdout.splitlines()
                if line.startswith("FAILED")
            ]
            cast = report["mutants"]
            assert isinstance(cast, dict)
            cast[name] = {"returncode": result.returncode, "failed": failed}
            assert result.returncode != 0 and failed, f"mutant survived: {name}"
    finally:
        TARGET.write_bytes(original)
    assert digest(TARGET.read_bytes()) == expected
    Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
