"""Boundary checks for the coordinate-only native prerequisite instrument."""

from staff_coordinates import preflight


def rules(ys: list[float]) -> list[list[list[float]]]:
    return [[[10.0, y], [909.0, y]] for y in ys]


def test_span_must_exceed_half_page() -> None:
    # Changing > to >= would accept the first unsupported fixture.
    assert not preflight(rules([100.0] * 7 + [600.0] * 8), 1000, 1000)["passed"]
    assert preflight(rules([100.0] * 7 + [601.0] * 8), 1000, 1000)["passed"]


def test_half_counts_use_native_rounding() -> None:
    result = preflight(rules([10.0] * 3 + [499.6] + [800.0] * 11), 1000, 1000)
    assert result["top_count"] == 3
    assert not result["passed"]


def test_native_longest_filter_precedes_count() -> None:
    lines = rules([10.0] * 7 + [800.0] * 7)
    lines.append([[10.0, 900.0], [728.0, 900.0]])  # 719 < float32(.8) * 900
    result = preflight(lines, 1000, 1000)
    assert result["retained_count"] == 14
    assert not result["passed"]


def test_short_line_at_native_boundary_is_retained() -> None:
    lines = rules([10.0] * 7 + [800.0] * 7)
    lines.append([[10.0, 900.0], [729.0, 900.0]])  # native 720 boundary
    assert preflight(lines, 1000, 1000)["passed"]
