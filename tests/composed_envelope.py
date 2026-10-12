"""Conditional controlled-ICC byte envelope from source codes, not stage outputs."""

import hashlib
import struct
from fractions import Fraction
from functools import lru_cache

from reversed_target import ERROR_BOUND, A, B, C, D, branch, root_interval
from source_gamma import BOUND
from stage_evaluation import MATRIX_BOUND

# The source bound includes normalization to binary32 before squaring. Propagate
# through row L1 <=2, then matrix rounding and one admitted inverse branch.
# Word quantization contributes <=1 word; round-to-byte contributes <=128 words.
BYTE_BOUND = 255 * (13 * (2 * BOUND + MATRIX_BOUND) + ERROR_BOUND + Fraction(129, 65535))


def verify_slope() -> bool:
    """Prove the ideal inverse's branch-local slope ceiling without host pow.

    Linear derivative is 1/C. Power derivative is (5/12)/A * R^(-7/12).
    R exceeds (A*D+B)^(12/5); its derivative is therefore at most
    (5/12)/A / (A*D+B)^(7/5). Use the rational fifth-root lower bracket.
    The seam may have a jump; callers must admit the entire input interval.
    https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsgamma.c
    """
    lower, _ = root_interval((A * D + B) ** 7, 5)
    if 1 / C > 13 or Fraction(5, 12) / A / lower > 13:
        raise ValueError("Unproved reversed-curve slope")
    return True


def clip(value: Fraction) -> Fraction:
    return max(Fraction(), min(Fraction(1), value))


@lru_cache(maxsize=4096)
def _ideal(
    codes: tuple[int, ...], matrix: tuple[Fraction, ...]
) -> tuple[tuple[Fraction, Fraction, str], ...]:
    inputs = [Fraction(v, 255) ** 2 for v in codes]
    result: list[tuple[Fraction, Fraction, str]] = []
    for channel in range(3):
        row = matrix[3 * channel : 3 * channel + 3]
        value = sum((coefficient * sample for coefficient, sample in zip(row, inputs)), Fraction())
        uncertainty = sum(abs(v) for v in row) * BOUND + MATRIX_BOUND
        left, right = branch(value - uncertainty), branch(value + uncertainty)
        if left != right:
            raise ValueError("Unsupported propagated reversed-curve branch crossing")
        if left == "linear":
            low = high = value / C
        else:
            low, high = root_interval(value**5, 12)
            low, high = (low - B) / A, (high - B) / A
        result.append((clip(low), clip(high), left))
    return tuple(result)


def ideal_channels(
    codes: tuple[int, ...], coefficients: list[str]
) -> list[tuple[Fraction, Fraction, str]]:
    """Ideal clipped output intervals with the whole numerical domain admitted."""
    if len(codes) != 3 or any(not 0 <= v <= 255 for v in codes) or len(coefficients) != 9:
        raise ValueError("Unsupported composed input/matrix domain")
    matrix = tuple(Fraction(v) for v in coefficients)
    if any(sum(abs(v) for v in matrix[3 * r : 3 * r + 3]) > 2 for r in range(3)):
        raise ValueError("Unsupported composed matrix row domain")
    verify_slope()
    return list(_ideal(codes, matrix))


def verify_composed(data: bytes, coefficients: list[str]) -> dict[str, object]:
    """Compare final bytes against ideal source/matrix/inverse composition.

    Caller independently binds the complete pipeline and verifies earlier stage
    arithmetic, target finite accuracy, saturation and formatter/restoration.
    This oracle intentionally reads no observed intermediate value. It does not
    establish native dispatch, arbitrary profiles or renderer-pixel traversal.
    """
    if len(data) != 256 * 136:
        raise ValueError("Missing/extra composed vectors")
    maximum = Fraction()
    records: list[dict[str, object]] = []
    for index, row in enumerate(struct.iter_unpack("<34I", data)):
        codes = (index, 255 - index, index * 73 % 256)
        if row[0] != index or row[1:4] != codes or row[4:7] != tuple(c * 257 for c in codes):
            raise ValueError("Wrong composed vector/input association")
        ideal = ideal_channels(codes, coefficients)
        for channel, (low, high, selected) in enumerate(ideal):
            actual = row[28 + channel]
            error = max(abs(actual - 255 * low), abs(actual - 255 * high))
            if actual > 255 or error > BYTE_BOUND:
                raise ValueError(f"Wrong composed byte at vector {index}, channel {channel}")
            maximum = max(maximum, error)
            records.append(
                {
                    "vector": index,
                    "channel": channel,
                    "source_codes": list(codes),
                    "ideal_normalized_interval": [str(low), str(high)],
                    "branch": selected,
                    "output_byte": actual,
                    "byte_error_upper_bound": str(error),
                }
            )
    return {
        "values": 768,
        "sha256": hashlib.sha256(data).hexdigest(),
        "matrix": coefficients,
        "declared_byte_bound": str(BYTE_BOUND),
        "maximum_byte_error_upper_bound": str(maximum),
        "domain": "256 RGB triples; row L1 <=2; propagated interval in one admitted branch",
        "records": records,
        "controlled_composed_byte_envelope_verified": True,
        "preceding_native_evidence_required": True,
        "renderer_pixel_traversal_observed": False,
        "arbitrary_icc_verified": False,
        "page_composition_fidelity_verified": False,
    }
