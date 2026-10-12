"""Independent rational intervals for a fixed reversed-sRGB finite probe domain."""

import hashlib
import struct
from fractions import Fraction
from functools import lru_cache

from stage_evaluation import signed32

# Exact in-memory binary64 coefficients, not the serialized s15Fixed16 tags.
GAMMA = Fraction(5404319552844595, 2251799813685248)
A = Fraction(266800925792091, 281474976710656)
B = Fraction(7513114070305283, 144115188075855872)
C = Fraction(43571977818987, 562949953421312)
D = Fraction(2914729678834185, 72057594037927936)
ERROR_BOUND = Fraction(1, 2**24) + Fraction(1, 2**44)
SEAM_MARGIN = Fraction(1, 2**40)
PARAMETER_BOUND = Fraction(1, 2**48)


@lru_cache(maxsize=4096)
def root_interval(value: Fraction, degree: int) -> tuple[Fraction, Fraction]:
    """Bracket roots using exact integer comparisons on an 80-bit dyadic grid."""
    if degree not in (5, 12) or not 0 <= value <= 32:
        raise ValueError("Unsupported root domain")
    scale = 2**80
    numerator = value.numerator * scale**degree
    denominator = value.denominator
    low, high = 0, 2 * scale + 1
    while high - low > 1:
        middle = (low + high) // 2
        if middle**degree * denominator <= numerator:
            low = middle
        else:
            high = middle
    exact = low**degree * denominator == numerator
    return Fraction(low, scale), Fraction(low if exact else high, scale)


def branch(value: Fraction) -> str:
    """Exclude the seam; do not assume native pow's branch decision is exact.

    For these fixed coefficients, |gamma-12/5| < 2^-51 and a*d+b is in
    (0.09,0.1). Even allowing fused/separate binary64 threshold arithmetic,
    its displacement is below 2^-48, well inside the excluded 2^-40 band.
    """
    if not Fraction(-1, 16) <= value <= 2:
        raise ValueError("Unsupported reversed target value domain")
    low, high = root_interval((A * D + B) ** 12, 5)
    if value < low - SEAM_MARGIN:
        return "linear"
    if value > high + SEAM_MARGIN:
        return "power"
    raise ValueError("Unsupported reversed target boundary band")


def reverse_interval(bits: int) -> tuple[Fraction, Fraction, str]:
    """Independent mathematical inverse, with bounded gamma idealization.

    Negative type-4's linear branch is R/c; its power branch is
    (R^(1/gamma)-b)/a. For gamma=12/5 compute the twelfth root of R^5.
    https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.19.1/src/cmsgamma.c
    No native/libm/Decimal/host pow evaluates this truth. The finite observed
    accuracy ceiling is not a theorem about arbitrary native pow inputs.
    """
    if not 0 <= bits < 2**32:
        raise ValueError("Unsupported reversed target bit domain")
    try:
        value = signed32(bits)
    except ValueError as error:
        raise ValueError("Unsupported reversed target float domain") from error
    selected = branch(value)
    if selected == "linear":
        result = value / C
        return result, result, selected
    low, high = root_interval(value**5, 12)
    return (low - B) / A, (high - B) / A, selected


def expected_curves() -> list[dict[str, object]]:
    return [
        {
            "kind": -4,
            "domain": ["-9999999778196308361216", "9999999778196308361216"],
            "parameters": [str(v) for v in [GAMMA, A, B, C, D, *([Fraction()] * 5)]],
        }
        for _ in range(3)
    ]


def verify_target(data: bytes, curves: object) -> dict[str, object]:
    """Check every target value; caller first binds full pipeline and traversal."""
    if curves != expected_curves():
        raise ValueError("Unsupported/changed reversed target curves")
    if len(data) != 256 * 136:
        raise ValueError("Missing/extra reversed target vectors")
    maximum = Fraction()
    width = Fraction()
    linear = 0
    records: list[dict[str, object]] = []
    for index, row in enumerate(struct.iter_unpack("<34I", data)):
        if row[0] != index:
            raise ValueError("Wrong reversed target vector order")
        for channel, bits in enumerate(row[19:22]):
            low, high, selected = reverse_interval(bits)
            actual = signed32(row[22 + channel])
            # Use the farthest endpoint, so the complete truth interval meets
            # the ceiling; proximity to only one endpoint is insufficient.
            # The root brackets ideal gamma=12/5. On the positive branch,
            # |round64(1/gamma)-5/12| < 2^-54 and |log(R)| < 9.
            # R^(5/12) <= 2, exp(9*2^-54) < 2 and A > 9/10, giving
            # displacement < 40*2^-54 < 2^-48. Include that allowance in
            # the measured bound instead of calling an idealized root exact.
            allowance = PARAMETER_BOUND if selected == "power" else Fraction()
            error = max(abs(actual - low), abs(actual - high)) + allowance
            if error > ERROR_BOUND:
                raise ValueError(
                    f"Wrong reversed target output at vector {index}, channel {channel}"
                )
            maximum = max(maximum, error)
            width = max(width, high - low)
            linear += selected == "linear"
            records.append(
                {
                    "vector": index,
                    "channel": channel,
                    "input_bits": bits,
                    "output_bits": row[22 + channel],
                    "branch": selected,
                    "truth_interval": [str(low), str(high)],
                    "parameter_idealization_bound": str(allowance),
                    "error_upper_bound": str(error),
                }
            )
    return {
        "values": 768,
        "sha256": hashlib.sha256(data).hexdigest(),
        "linear_values": linear,
        "power_values": 768 - linear,
        "maximum_error_upper_bound": str(maximum),
        "maximum_interval_width": str(width),
        "declared_error_bound": str(ERROR_BOUND),
        "excluded_threshold_margin": str(SEAM_MARGIN),
        "parameter_idealization_bound": str(PARAMETER_BOUND),
        "domain": "finite binary32 [-1/16,2], excluding threshold band",
        "records": records,
        "reversed_target_accuracy_verified": True,
        "correctly_rounded_transcendentals_verified": False,
        "renderer_pixel_traversal_observed": False,
        "complete_cmm_precision_verified": False,
    }
