"""Wrong process/path/UUID and discarded diagnostics must invalidate the instrument."""

import pytest
import runtime_loader as subject

UUID = "12345678-1234-4321-ABCD-123456789ABC"
LINE = f"dyld[42]: <{UUID}> /private/tmp/native lib.dylib"


def test_retains_exact_image_identity_without_classifying_delayed_images() -> None:
    result = subject.parse_log(
        LINE + "\ndyld[42]: move loaded to delayed: CoreFoundation\nPDF warning\n", 42
    )
    assert result.images == (("/private/tmp/native lib.dylib", UUID),)
    assert result.loader_messages == ("move loaded to delayed: CoreFoundation",)
    assert result.diagnostics == "PDF warning\n"


@pytest.mark.parametrize(
    "line",
    [
        LINE.replace("[42]", "[43]"),
        LINE.replace(UUID, "invalid"),
        LINE.replace("/private/tmp/native lib.dylib", "relative.dylib"),
        LINE.replace("dyld[42]:", "dyld[invalid]:"),
        LINE.replace("/private/tmp/native lib.dylib", "/usr/lib/../wrong.dylib"),
    ],
)
def test_rejects_malformed_or_foreign_image_evidence(line: str) -> None:
    with pytest.raises(ValueError):
        subject.parse_log(line, 42)


def test_duplicate_events_keep_event_order() -> None:
    result = subject.parse_log(LINE + "\n" + LINE + "\n", 42)
    assert result.images == (
        ("/private/tmp/native lib.dylib", UUID),
        ("/private/tmp/native lib.dylib", UUID),
    )


def test_one_path_with_conflicting_mapped_uuids_fails() -> None:
    with pytest.raises(ValueError, match="conflicting"):
        subject.parse_log(LINE + "\n" + LINE.replace(UUID, "87654321" + UUID[8:]), 42)


def test_absent_loader_evidence_does_not_pass() -> None:
    with pytest.raises(ValueError, match="No image"):
        subject.parse_log("PDF warning\n", 42)


def test_unknown_loader_messages_remain_visible() -> None:
    result = subject.parse_log(LINE + "\ndyld[42]: unknown future event\n", 42)
    assert result.loader_messages == ("unknown future event",)


@pytest.mark.parametrize("pid", [0, -1])
def test_invalid_observed_pid_is_not_identity(pid: int) -> None:
    with pytest.raises(ValueError):
        subject.parse_log(LINE, pid)


def test_preserves_application_diagnostics_byte_for_byte() -> None:
    result = subject.parse_log("\nPDF warning\r\n" + LINE + "\nlast line", 42)
    assert result.diagnostics == "\nPDF warning\r\nlast line"


def test_mapped_uuid_mismatch_rejects_changed_disk_subject() -> None:
    with pytest.raises(ValueError, match="UUID"):
        subject.verify_uuid(UUID, "87654321" + UUID[8:])


def test_missing_disk_uuid_is_unavailable() -> None:
    with pytest.raises(ValueError, match="UUID"):
        subject.verify_uuid(UUID, None)
