"""Disprove broad append exemptions in the final evidence closure checker."""

from __future__ import annotations

import hashlib
import runpy
from pathlib import Path

import pytest

CHECKER = Path(__file__).with_name("audit-repair-closure.py")
ORIGINAL = {
    "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    "mode": 420,
    "device": 1,
    "inode": 2,
    "symlink": None,
}


def check(content: bytes, prefix: bytes | None = None, **metadata: object) -> None:
    namespace = runpy.run_path(str(CHECKER))
    actual = {**ORIGINAL, "sha256": hashlib.sha256(content).hexdigest(), **metadata}
    namespace["check_identity"](actual, ORIGINAL, content, prefix)


def test_authorized_complete_prefix_allows_appended_decision() -> None:
    check(b"abc\nnew decision\n", b"abc")


def test_exact_subject_needs_no_exemption() -> None:
    check(b"abc")


@pytest.mark.parametrize("content", [b"xbc\nnew", b"ab", b"new\nabc", b"acb"])
def test_changed_or_truncated_prefix_fails(content: bytes) -> None:
    with pytest.raises(AssertionError):
        check(content, b"abc")


def test_unrelated_subject_append_fails() -> None:
    with pytest.raises(AssertionError):
        check(b"abc\nnew")


def test_false_archived_prefix_fails() -> None:
    with pytest.raises(AssertionError):
        check(b"xyz\nnew", b"xyz")


@pytest.mark.parametrize("metadata", [{"mode": 384}, {"inode": 3}, {"symlink": "new"}])
def test_bookkeeping_exemption_cannot_hide_metadata_change(metadata: dict[str, object]) -> None:
    with pytest.raises(AssertionError):
        check(b"abc\nnew", b"abc", **metadata)
