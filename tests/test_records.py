"""Private record parsing refuses ambiguity before saved-state interpretation."""

import pytest


def test_preserves_utf8_values_and_occurrence_order() -> None:
    from bookscan.records import decode

    raw = '{"note":"café 🎵","pages":[3,1,3],"nested":{"zero":-0.0,"x":null}}'
    assert decode(raw.encode("utf-8")) == {
        "note": "café 🎵",
        "pages": [3, 1, 3],
        "nested": {"zero": -0.0, "x": None},
    }


@pytest.mark.parametrize(
    "raw",
    [
        b'{"version":2,"version":1}',
        b'{"version":1,"version":1}',
        rb'{"version":2,"\u0076ersion":1}',
        b'{"pages":[{"id":"wrong","id":"right"}]}',
        b'{"optional":{"mapping":{"x":0,"x":1}}}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'{"x":-Infinity}',
        b'{"x":1e9999}',
        b'{"x":-1e9999}',
        b'{"x":[{"y":NaN}]}',
        b'{"x":"\xff"}',
        rb'{"x":"\ud800"}',
        rb'{"x":["\udfff"]}',
        rb'{"\ud800":1}',
        b"\xef\xbb\xbf{}",
        "{}".encode("utf-16"),
        b'{"x":1} {"x":2}',
        b'{"x":1} trailing',
        b'{"x":1,}',
        b'{"x":"line\nfeed"}',
        b"{",
        b"",
        b"[]",
        b"null",
        b"true",
        b"1",
        b'"object"',
        b'{"x":' + b"9" * 5000 + b"}",
        b'{"x":' + b"[" * 2000 + b"NaN" + b"]" * 2000 + b"}",
    ],
    ids=[
        "duplicate-version",
        "duplicate-equal",
        "duplicate-escaped",
        "duplicate-array-object",
        "duplicate-nested",
        "nan",
        "infinity",
        "negative-infinity",
        "overflow",
        "negative-overflow",
        "nested-nan",
        "invalid-utf8",
        "high-surrogate",
        "low-surrogate",
        "surrogate-key",
        "bom",
        "utf16",
        "two-records",
        "trailing-text",
        "trailing-comma",
        "unescaped-control",
        "incomplete",
        "empty",
        "array-root",
        "null-root",
        "bool-root",
        "number-root",
        "string-root",
        "integer-runtime-limit",
        "deep-nonfinite",
    ],
)
def test_invalid_record_is_domain_error(raw: bytes) -> None:
    from bookscan.records import RecordError, decode

    with pytest.raises(RecordError) as error:
        decode(raw)
    assert (error.value.code, error.value.exit_code) == ("INVALID_PROJECT", 3)


def test_independent_objects_may_repeat_keys_and_valid_surrogate_pair() -> None:
    from bookscan.records import decode

    assert decode(rb'{"a":{"id":1},"b":{"id":2},"note":"\ud834\udd1e"}') == {
        "a": {"id": 1},
        "b": {"id": 2},
        "note": "𝄞",
    }
