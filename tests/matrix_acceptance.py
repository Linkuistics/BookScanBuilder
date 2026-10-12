"""Independent ICC matrix/power byte truth and native diagnostics; no CMM precision pass."""

import argparse
import hashlib
import json
import struct
from fractions import Fraction
from pathlib import Path

import pikepdf
from icc_fixtures import profile
from icc_matrix_truth import inverse, read_profile, to_linear

from bookscan import intake, profiles, samples

PIXEL = bytes([51, 153, 204])


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def columns(data: bytes, values: tuple[tuple[int, int, int], ...]) -> bytes:
    """Write declared fixture columns independently of the truth reader."""
    result = bytearray(data)
    for name, value in zip((b"rXYZ", b"gXYZ", b"bXYZ"), values, strict=True):
        for pos in range(132, 132 + 12 * int.from_bytes(data[128:132], "big"), 12):
            if data[pos : pos + 4] == name:
                start, size = struct.unpack(">II", data[pos + 4 : pos + 12])
                assert size == 20
                result[start : start + size] = b"XYZ \0\0\0\0" + struct.pack(">iii", *value)
                break
        else:
            raise AssertionError("Fixture missing matrix column")
    return bytes(result)


def run(artifacts: Path) -> dict[str, object]:
    artifacts.mkdir()
    # Exact 3:1 mixing: M_source = M_target [[3/4,1/4,0],[1/4,3/4,0],[0,0,1]].
    # ICC Annex F.3, §10.16 type 0; no numerical CMM/library output used as truth.
    # https://www.color.org/specification/ICC1v43_2010-12.pdf
    target_bytes = columns(
        profile(1), ((28580, 14580, 912), (25236, 46980, 6364), (9376, 3976, 46804))
    )
    coupled_bytes = columns(
        profile(2), ((27744, 22680, 2275), (26072, 38880, 5001), (9376, 3976, 46804))
    )
    cases = [
        ("matched", profile(2), profile(1), ("1/25", "9/25", "16/25")),
        ("swapped", profile(2, swapped=True), profile(1), ("16/25", "9/25", "1/25")),
        ("coupled", coupled_bytes, target_bytes, ("3/25", "7/25", "16/25")),
    ]
    declaration = {
        "format": "BookScanBuilderExactMatrixTruth",
        "version": 1,
        "source": "https://www.color.org/specification/ICC1v43_2010-12.pdf",
        "input": list(PIXEL),
        "native_size": [1, 1],
        "points": [72, 36],
        "cases": {name: list(want) for name, _, _, want in cases},
        "meaning": (
            "Exact unquantized ICC F.3 matrix/power values for declared same-white linear targets"
        ),
        "native_precision_status": "unavailable: CMM interpolation/optimization/quantization proof",
        "cairo_status": (
            "unavailable: actual output-profile identity/matrix and conversion precision"
        ),
    }
    # Literal declarations and all profile bytes exist before any native reading.
    (artifacts / "truth.json").write_text(json.dumps(declaration, indent=2) + "\n")
    for name, source, target, _ in cases:
        (artifacts / f"{name}-input.icc").write_bytes(source)
        (artifacts / f"{name}-target.icc").write_bytes(target)
    frozen = {p.name: sha(p.read_bytes()) for p in artifacts.iterdir()}
    target_profile = read_profile(target_bytes)
    controls: dict[str, object] = {}
    wrong_profiles: list[tuple[str, bytes]] = []
    wanted = tuple(Fraction(v) for v in ("3/25", "7/25", "16/25"))
    # Observe wrong subjects fail exact literal truth before the native workload.
    for name, wrong in [
        (
            "missing-mixing",
            columns(profile(2), ((28580, 14580, 912), (25236, 46980, 6364), (9376, 3976, 46804))),
        ),
        (
            "missing-power",
            columns(profile(1), ((27744, 22680, 2275), (26072, 38880, 5001), (9376, 3976, 46804))),
        ),
    ]:
        got = to_linear(read_profile(wrong), target_profile, (PIXEL[0], PIXEL[1], PIXEL[2]))
        assert got != wanted
        assert got[2] == wanted[2] if name == "missing-mixing" else got[2] == Fraction(4, 5)
        controls[name] = {
            "rejected": True,
            "exact_values": [str(v) for v in got],
        }
        wrong_profiles.append((name, wrong))
        (artifacts / f"wrong-{name}.icc").write_bytes(wrong)
    pdf_path = artifacts / "Ordinary coupled ICC.pdf"
    with pikepdf.Pdf.new() as pdf:
        for source in [c[1] for c in cases] + [c[1] for c in wrong_profiles]:
            page = pdf.add_blank_page(page_size=(72, 36))
            icc = pikepdf.Stream(pdf, source)
            icc.N = 3
            image = pikepdf.Stream(pdf, PIXEL)
            image.Type, image.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
            image.Width, image.Height, image.BitsPerComponent = 1, 1, 8
            image.ColorSpace = pikepdf.Array([pikepdf.Name.ICCBased, icc])
            page.obj.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=image))
            page.obj.Contents = pikepdf.Stream(pdf, b"q 72 0 0 36 0 0 cm /I Do Q")
        pdf.save(pdf_path, deterministic_id=True)
    saved = intake.snapshot(pdf_path, artifacts / "snapshot.pdf")
    original = pdf_path.read_bytes()
    rows: dict[str, object] = {}
    actual: dict[str, bytes] = {}
    for page, (name, source, target, want) in zip(saved.pages[:3], cases, strict=True):
        exact = to_linear(
            read_profile(source), read_profile(target), (PIXEL[0], PIXEL[1], PIXEL[2])
        )
        assert tuple(str(v) for v in exact) == want
        sample = samples.collect(saved, page).images[0]
        assert sample.packed == PIXEL and sample.placement.samples == (1, 1)
        assert sample.color is not None and sample.color.profile == source
        result = profiles.display(sample, target)
        assert result.input_profile_sha256 == sha(source)
        assert result.output_profile_sha256 == sha(target)
        assert (
            result.view.rgb is not None and len(result.view.rgb) == 3 and result.view.size == (1, 1)
        )
        native = result.view.rgb
        actual[name] = native
        # Record signed rational deviations; do not infer a CMM precision bound.
        rows[name] = {
            "ideal_linear": [str(v) for v in exact],
            "actual_native": list(native),
            "error_in_8bit_codes": [
                str(Fraction(v) - 255 * ideal) for v, ideal in zip(native, exact, strict=True)
            ],
            "input_profile_sha256": result.input_profile_sha256,
            "target_profile_sha256": result.output_profile_sha256,
            "raw_sha256": sample.raw_sha256,
            "intent": result.intent,
            "flags": result.flags,
            "pillow": result.pillow,
            "littlecms": result.littlecms,
            "status": "exact analytic truth passed; native precision unavailable",
        }
    for page, (name, wrong) in zip(saved.pages[3:], wrong_profiles, strict=True):
        sample = samples.collect(saved, page).images[0]
        assert sample.packed == PIXEL and sample.placement.samples == (1, 1)
        assert sample.color is not None and sample.color.profile == wrong
        result = profiles.display(sample, target_bytes)
        assert result.input_profile_sha256 == sha(wrong)
        assert result.output_profile_sha256 == sha(target_bytes)
        assert result.view.rgb is not None and result.view.rgb != actual["coupled"]
        controls[name] = {
            "oracle": controls[name],
            "actual_native": list(result.view.rgb),
            "native_sample_grid_unchanged": True,
            "raw_sha256": sample.raw_sha256,
            "input_profile_sha256": result.input_profile_sha256,
            "target_profile_sha256": result.output_profile_sha256,
            "native_precision_status": "diagnostic; no justified CMM precision bound",
        }
    pdf_path.unlink()
    assert saved.path.read_bytes() == original
    assert all(sha((artifacts / name).read_bytes()) == digest for name, digest in frozen.items())
    inv = inverse(target_profile.matrix)
    report: dict[str, object] = {
        "format": "BookScanBuilderExactMatrixReading",
        "version": 1,
        "cases": rows,
        "controls": controls,
        "source_sha256": saved.sha256,
        "truth_sha256": sha((artifacts / "truth.json").read_bytes()),
        "target_inverse": [[str(v) for v in row] for row in inv],
        "target_inverse_infinity_norm": str(max(sum(abs(v) for v in row) for row in inv)),
        "source_loss_verified": True,
        "profile_subjects_unchanged": True,
        "native_precision_verified": False,
        "cairo_fidelity_verified": False,
        "runtime_resources_verified": False,
        "accepted_project_delivered": False,
    }
    (artifacts / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.artifacts), indent=2))
