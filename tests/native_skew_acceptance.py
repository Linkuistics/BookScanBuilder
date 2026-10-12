"""Actual packaged helper acceptance, separate from dependency-free preparation tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import cast

from PIL import Image

from bookscan.native_setup import assess, build, load_cache, preflight, self_test
from bookscan.skew import NativeError


def run(artifacts: Path) -> dict[str, object]:
    artifacts.mkdir()
    cache = artifacts / "cache with spaces"
    built = build(cache)
    ready = preflight(cache)
    controls = cast(dict[str, dict[str, object]], ready["controls"])
    assert controls["near-edge"]["native_status"] == 0
    assert controls["near-edge"]["score_ratio"] == 0
    assert "skew-range-edge" in cast(list[str], controls["beyond-edge"]["reasons"])
    assert load_cache(cache).binary == built.binary
    assert ready["controls"] == self_test(built.binary)

    # Independent wrong-helper control: protocol/dimensions look valid; all signs
    # and the blank sentinel are deliberately wrong. No private product fault flag.
    wrong = artifacts / "wrong helper"
    wrong.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "from PIL import Image\n"
        "if sys.argv[1] == '--identity':\n"
        " print(json.dumps({'schema':'BookScanBuilderSkewIdentity','version':1,"
        "'leptonica':'leptonica-1.87.0','headers':'1.87.0'}))\n"
        "else:\n"
        " with Image.open(sys.argv[2]) as image: w,h=image.size\n"
        " print(json.dumps({'schema':'BookScanBuilderSkew','version':1,"
        "'leptonica':'leptonica-1.87.0','width':w,'height':h,"
        "'status':0,'angle_degrees':2,'score_ratio':10}))\n"
    )
    wrong.chmod(0o700)
    try:
        self_test(wrong)
    except NativeError as error:
        wrong_outcome = str(error)
    else:
        raise AssertionError("wrong sign helper passed preflight")

    # Analyze sparse/blank/RGB originals; pixels and serialized PNG bytes stay exact.
    image = Image.new("RGB", (640, 480), (251, 243, 219))
    source = artifacts / "baseline.png"
    image.save(source)
    encoded = hashlib.sha256(source.read_bytes()).hexdigest()
    decoded = hashlib.sha256(image.tobytes()).hexdigest()
    estimate = assess(built.binary, image, artifacts)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == encoded
    assert hashlib.sha256(image.tobytes()).hexdigest() == decoded
    image.close()

    # A changed complete cache must fail without building or repairing its bytes.
    corrupt = artifacts / "corrupt cache"
    shutil.copytree(cache, corrupt)
    binary = load_cache(corrupt).binary
    binary.write_bytes(b"broken executable")
    corrupt_before = binary.read_bytes()
    try:
        preflight(corrupt)
    except NativeError as error:
        corrupt_outcome = str(error)
    else:
        raise AssertionError("changed native cache accepted")
    assert binary.read_bytes() == corrupt_before
    return {
        "schema": "BookScanBuilderNativeAcceptance",
        "version": 1,
        "preflight": ready,
        "wrong_sign_control": wrong_outcome,
        "corrupt_cache_control": corrupt_outcome,
        "rgb_unchanged": {"png_sha256": encoded, "rgb_sha256": decoded},
        "blank_assessment": estimate.to_dict(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.artifacts)
    (args.artifacts / "report.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps({"report": str(args.artifacts / "report.json"), "passed": True}))


if __name__ == "__main__":
    main()
