"""A missing/foreign/mismatched native observation cannot establish font use."""

from pathlib import Path

import pytest
from font_loading import bind_loading


def records(font: Path) -> list[dict[str, object]]:
    identity = font.stat()
    base: dict[str, object] = {"version": 1, "pid": 123, "path": str(font)}
    return [
        base | {"sequence": 1, "kind": "match", "index": 2, "api": "FcFontSort"},
        base
        | {
            "sequence": 2,
            "kind": "open",
            "call": 1,
            "device": identity.st_dev,
            "inode": identity.st_ino,
            "size": identity.st_size,
        },
        base | {"sequence": 3, "kind": "face", "call": 1, "index": 2, "error": 0},
    ]


def test_selected_face_binds_the_actual_open_descriptor(tmp_path: Path) -> None:
    font = tmp_path / "font"
    font.write_bytes(b"independent-font-subject")
    result = bind_loading(records(font), 123, font)
    assert result["face_indexes"] == [2]
    assert result["open_count"] == 1
    assert result["selection_apis"] == ["FcFontSort"]


@pytest.mark.parametrize(
    "breakage",
    [
        "disabled",
        "foreign",
        "wrong-path",
        "wrong-inode",
        "wrong-face",
        "failed-face",
        "missing-open",
        "missing-match",
        "wrong-call",
        "out-of-order",
        "unknown-version",
    ],
)
def test_wrong_native_observation_is_rejected(tmp_path: Path, breakage: str) -> None:
    font = tmp_path / "font"
    font.write_bytes(b"independent-font-subject")
    events = records(font)
    if breakage == "disabled":
        events.clear()
    elif breakage == "foreign":
        events[1]["pid"] = 124
    elif breakage == "wrong-path":
        events[2]["path"] = str(tmp_path / "other")
    elif breakage == "wrong-inode":
        events[1]["inode"] = -1
    elif breakage == "wrong-face":
        events[2]["index"] = 3
    elif breakage == "failed-face":
        events[2]["error"] = 1
    elif breakage == "missing-open":
        events.pop(1)
    elif breakage == "missing-match":
        events.pop(0)
    elif breakage == "wrong-call":
        events[1]["call"] = 2
    elif breakage == "out-of-order":
        events[2]["sequence"] = 2
    elif breakage == "unknown-version":
        events[0]["version"] = 2
    with pytest.raises(ValueError):
        bind_loading(events, 123, font)
