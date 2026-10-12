"""RGB cleanup must preserve the chosen failure and never retry a released fd."""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from bookscan import assets, ownership


class Cancelled(RuntimeError):
    """A cooperative signal outcome, distinct from a filesystem OSError."""


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    project = tmp_path / "RGB close project"
    project.mkdir()
    with ownership.Writer.acquire(project, ownership.provision(project)) as writer:
        yield writer


class Fault:
    """Observe real opens/closes; inject only at the selected RGB boundaries."""

    def __init__(
        self,
        patch: pytest.MonkeyPatch,
        owner: ownership.Writer,
        stages: set[str],
        selected: BaseException | None = None,
        *,
        reuse: bool = False,
    ) -> None:
        opened, closed, read = os.open, os.close, os.read
        self.active: dict[int, str] = {}
        self.failed: list[tuple[str, OSError]] = []
        self.reused: list[int] = []
        self.injected = False
        sentinel = owner.path.parent / "independent descriptor"
        sentinel.write_bytes(b"keep independent descriptor open")

        def observe(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
            descriptor = opened(path, flags, mode, dir_fd=dir_fd)
            if path == owner.path / "assets":
                self.active[descriptor] = "directory"
            elif dir_fd in self.active and self.active[dir_fd] == "directory":
                self.active[descriptor] = "writer" if flags & os.O_WRONLY else "reader"
            return descriptor

        def fail_close(descriptor: int) -> None:
            stage = self.active.pop(descriptor, None)
            closed(descriptor)
            if stage in stages:
                error = OSError("controlled RGB " + str(stage) + " close failure")
                self.failed.append((str(stage), error))
                if reuse:
                    replacement = opened(sentinel, os.O_RDONLY | os.O_CLOEXEC)
                    assert replacement == descriptor
                    self.reused.append(replacement)
                raise error

        def fail_read(descriptor: int, count: int) -> bytes:
            if selected is not None and self.active.get(descriptor) == "reader":
                self.injected = True
                raise selected
            return read(descriptor, count)

        patch.setattr(os, "open", observe)
        patch.setattr(os, "close", fail_close)
        patch.setattr(os, "read", fail_read)

    def assert_reused_open(self) -> None:
        assert self.reused
        for descriptor in self.reused:
            try:
                assert os.pread(descriptor, 4, 0) == b"keep"
            finally:
                os.close(descriptor)


CASES = [("read", "reader"), ("read", "directory")] + [
    ("publish", stage) for stage in ["reader", "writer", "directory"]
]


@pytest.mark.parametrize("operation,stage", CASES)
@pytest.mark.parametrize("kind", ["invalid", "cancel", "interrupt", "unexpected"])
def test_close_failure_preserves_chosen_error_and_closes_remaining_descriptors(
    owner: ownership.Writer,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    stage: str,
    kind: str,
) -> None:
    store = assets.Assets.provision(owner)
    reference = store.publish(b"abc", (1, 1)) if operation == "read" else None
    selected = {
        "invalid": assets.AssetError("INVALID_PROJECT", "chosen corruption", 3),
        "cancel": Cancelled("chosen cooperative cancellation"),
        "interrupt": KeyboardInterrupt("chosen interruption"),
        "unexpected": RuntimeError("chosen producer failure"),
    }[kind]
    with monkeypatch.context() as patch:
        fault = Fault(patch, owner, {stage}, selected)
        with pytest.raises(type(selected)) as caught:
            if reference is None:
                store.publish(b"abc", (1, 1))
            else:
                store.read(reference)
    assert fault.injected and [entry[0] for entry in fault.failed] == [stage]
    assert caught.value is selected
    assert not fault.active
    assert str(fault.failed[0][1]) in " ".join(selected.__notes__)
    if reference is None:
        assert list((owner.path / "assets").iterdir()) == []
    else:
        assert store.read(reference) == b"abc"
    owner.verify()


@pytest.mark.parametrize("operation", ["read", "publish"])
def test_multiple_close_failures_accumulate_on_original_error(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    store = assets.Assets.provision(owner)
    reference = store.publish(b"abc", (1, 1)) if operation == "read" else None
    selected = Cancelled("original cancellation")
    with monkeypatch.context() as patch:
        fault = Fault(patch, owner, {"reader", "writer", "directory"}, selected)
        with pytest.raises(Cancelled) as caught:
            if reference is None:
                store.publish(b"abc", (1, 1))
            else:
                store.read(reference)
    assert caught.value is selected
    assert [entry[0] for entry in fault.failed] == (
        ["reader", "directory"] if operation == "read" else ["reader", "writer", "directory"]
    )
    assert not fault.active
    for _, failure in fault.failed:
        assert str(failure) in " ".join(selected.__notes__)


@pytest.mark.parametrize("operation,stage", CASES)
def test_close_only_failure_has_domain_result_without_retrying_reused_descriptor(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, operation: str, stage: str
) -> None:
    store = assets.Assets.provision(owner)
    reference = store.publish(b"abc", (1, 1)) if operation == "read" else None
    with monkeypatch.context() as patch:
        fault = Fault(patch, owner, {stage}, reuse=True)
        try:
            with pytest.raises(assets.AssetError) as caught:
                if reference is None:
                    store.publish(b"abc", (1, 1))
                else:
                    store.read(reference)
        finally:
            fault.assert_reused_open()
    expected = (
        ("WRITE_FAILED", 5)
        if operation == "publish" and stage != "reader"
        else ("INVALID_PROJECT", 3)
    )
    assert (caught.value.code, caught.value.exit_code) == expected
    assert len(fault.failed) == 1 and caught.value.__cause__ is fault.failed[0][1]
    assert not fault.active
    # No close-only error grants a checkpoint. Any linked RGB is a complete orphan.
    if operation == "publish" and stage == "reader":
        assert list((owner.path / "assets").iterdir()) == []
    else:
        for path in (owner.path / "assets").iterdir():
            assert path.suffix == ".png"
    owner.verify()
    with pytest.raises(ownership.OwnershipError, match="PROJECT_BUSY"):
        ownership.Writer.acquire(owner.path, owner.identity)


def test_selected_cleanup_error_survives_later_writer_and_directory_close_failures(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = assets.Assets.provision(owner)
    selected = PermissionError("private unlink denied")

    def denied(*args: object, **kwargs: object) -> None:
        raise selected

    with monkeypatch.context() as patch:
        fault = Fault(patch, owner, {"writer", "directory"})
        patch.setattr(os, "unlink", denied)
        with pytest.raises(assets.AssetError) as caught:
            store.publish(b"abc", (1, 1))
    assert caught.value.__cause__ is selected
    assert (caught.value.code, caught.value.exit_code) == ("WRITE_FAILED", 5)
    assert not fault.active
    for _, failure in fault.failed:
        assert str(failure) in " ".join(caught.value.__notes__)


@pytest.mark.parametrize("operation,stage", CASES)
def test_handled_caller_exception_does_not_hide_new_close_only_failure(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch, operation: str, stage: str
) -> None:
    store = assets.Assets.provision(owner)
    reference = store.publish(b"abc", (1, 1)) if operation == "read" else None
    unrelated = RuntimeError("already handled caller error")
    with monkeypatch.context() as patch:
        fault = Fault(patch, owner, {stage})
        try:
            raise unrelated
        except RuntimeError:
            with pytest.raises(assets.AssetError) as caught:
                if reference is None:
                    store.publish(b"abc", (1, 1))
                else:
                    store.read(reference)
    assert not getattr(unrelated, "__notes__", [])
    assert len(fault.failed) == 1 and caught.value.__cause__ is fault.failed[0][1]
    assert not fault.active


def test_provision_directory_close_failure_keeps_write_error_and_removes_empty_store(
    owner: ownership.Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    with monkeypatch.context() as patch:
        fault = Fault(patch, owner, {"directory"}, reuse=True)
        try:
            with pytest.raises(assets.AssetError) as caught:
                assets.Assets.provision(owner)
        finally:
            fault.assert_reused_open()
    assert (caught.value.code, caught.value.exit_code) == ("WRITE_FAILED", 5)
    assert len(fault.failed) == 1 and caught.value.__cause__ is fault.failed[0][1]
    assert not fault.active
    assert {path.name for path in owner.path.iterdir()} == {"writer.lock"}
    owner.verify()
