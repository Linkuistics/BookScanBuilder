"""Catch saved renderer policy substitutions without reopening native tools.

Commands use literal expectations and real source geometry/checkpoint histories.
Resource payloads and historical execution authenticity remain separate checks.
"""

import copy
import json
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pikepdf
import pytest

from bookscan import intake, ownership, project_header, records

RENDERER = Path("/historical/Poppler/pdftocairo")


@pytest.fixture
def saved(tmp_path: Path) -> intake.Snapshot:
    original = tmp_path / "Original café.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(72, 36))
        page.obj.MediaBox = pikepdf.Array([2.4, 1.2, 0, 0])
        page.obj.CropBox = pikepdf.Array([0.24, 0, 2.4, 1.2])
        page.obj.Rotate, page.obj.UserUnit = 90, 2
        pdf.save(original, min_version="1.7")
    result = intake.snapshot(original, tmp_path / "source.pdf")
    original.unlink()
    return result


def literal(saved: intake.Snapshot) -> dict[str, object]:
    return {
        "command": [
            str(RENDERER),
            "-f",
            "1",
            "-l",
            "1",
            "-singlefile",
            "-r",
            "600",
            "-W",
            "10",
            "-H",
            "20",
            "-png",
            "-antialias",
            "default",
            str(saved.path),
            "/historical/tmp/bookscan-render-abc123/page",
        ],
        "diagnostics": "Decoder warning café\n",
    }


def test_restore_preserves_full_rotated_media_policy_and_decoder_text(
    saved: intake.Snapshot,
) -> None:
    from bookscan import render_record

    value = literal(saved)
    raw = json.dumps(value).encode()
    result = render_record.restore(records.decode(raw), saved.pages[0], saved.path, RENDERER)
    assert result.command[1:15] == (
        "-f",
        "1",
        "-l",
        "1",
        "-singlefile",
        "-r",
        "600",
        "-W",
        "10",
        "-H",
        "20",
        "-png",
        "-antialias",
        "default",
    )
    assert result.command[-2] == str(saved.path)
    assert result.diagnostics == "Decoder warning café\n"
    assert not hasattr(result, "resource_binding") and not hasattr(result, "rgb")
    cast(list[str], value["command"])[7] = "300"
    assert result.command[7] == "600"


@pytest.mark.parametrize(
    "fault",
    [
        "renderer",
        "first-page",
        "last-page",
        "density",
        "crop-width",
        "height",
        "crop-option",
        "hide-annotations",
        "scale-to",
        "antialias",
        "format",
        "source",
        "source-relative",
        "prefix-relative",
        "prefix-parent",
        "prefix-name",
        "missing-token",
        "extra-token",
        "float-page",
        "integer-page",
        "tuple-command",
        "string-command",
        "bool-diagnostic",
        "surrogate-diagnostic",
        "surrogate-command",
        "nul-command",
        "missing-field",
        "extra-field",
        "nonobject",
        "nonobject-binding",
        "nonstring-key",
        "cycle",
    ],
)
def test_wrong_saved_command_is_refused(saved: intake.Snapshot, fault: str) -> None:
    from bookscan import render_record

    data = literal(saved)
    command = cast(list[object], data["command"])
    value: object = data
    changes: dict[str, tuple[int, object]] = {
        "renderer": (0, "/foreign/pdftocairo"),
        "first-page": (2, "2"),
        "last-page": (4, "2"),
        "density": (7, "300"),
        "crop-width": (9, "9"),
        "height": (11, "10"),
        "crop-option": (5, "-cropbox"),
        "hide-annotations": (5, "-hide-annotations"),
        "scale-to": (8, "-scale-to-x"),
        "antialias": (14, "none"),
        "format": (12, "-jpeg"),
        "source": (15, str(saved.original_path)),
        "source-relative": (15, "source.pdf"),
        "prefix-relative": (16, "page"),
        "prefix-parent": (16, "/historical/tmp/bookscan-render-a/../page"),
        "prefix-name": (16, "/historical/tmp/bookscan-render-a/output"),
        "float-page": (2, "1.0"),
        "integer-page": (2, 1),
        "surrogate-command": (16, "/historical/tmp/bookscan-render-\ud800/page"),
        "nul-command": (16, "/historical/tmp/bookscan-render-a\0/page"),
    }
    if fault in changes:
        index, token = changes[fault]
        command[index] = token
    elif fault == "missing-token":
        command.pop()
    elif fault == "extra-token":
        command.append("-cropbox")
    elif fault == "tuple-command":
        data["command"] = tuple(command)
    elif fault == "string-command":
        data["command"] = "pdftocairo"
    elif fault.endswith("diagnostic"):
        data["diagnostics"] = {
            "bool-diagnostic": True,
            "surrogate-diagnostic": "\ud800",
            "nul-diagnostic": "a\0b",
        }[fault]
    elif fault == "missing-field":
        del data["diagnostics"]
    elif fault == "extra-field":
        data["version"] = 99
    elif fault == "nonobject":
        value = []
    elif fault == "nonobject-binding":
        data["resource_binding"] = []
    elif fault == "nonstring-key":
        value = {True: "coercion", **data}
    elif fault == "cycle":
        data["resource_binding"] = data
    else:
        raise AssertionError(fault)
    with pytest.raises(render_record.RenderRecordError) as caught:
        render_record.restore(value, saved.pages[0], saved.path, RENDERER)
    assert caught.value.code == "INVALID_PROJECT" and caught.value.exit_code == 3
    assert "Fresh import loses review facts" in caught.value.remediation


def test_optional_resource_payload_is_not_returned_or_claimed_verified(
    saved: intake.Snapshot,
) -> None:
    from bookscan import render_record

    value = literal(saved)
    value["resource_binding"] = {"unverified": ["requires its own reader"]}
    result = render_record.restore(value, saved.pages[0], saved.path, RENDERER)
    assert result.diagnostics == "Decoder warning café\n"
    assert not hasattr(result, "resource_binding")


def test_decoder_diagnostics_preserve_valid_utf8_without_stripping(
    saved: intake.Snapshot,
) -> None:
    from bookscan import render_record

    value = literal(saved)
    value["diagnostics"] = "\0 café\n\t "
    result = render_record.restore(value, saved.pages[0], saved.path, RENDERER)
    assert result.diagnostics == "\0 café\n\t "


def test_reader_never_opens_files_or_launches_tools(
    saved: intake.Snapshot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import render_record

    value = literal(saved)

    def deny(*args: object, **kwargs: object) -> None:
        raise PermissionError("mechanism denied")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", deny)
        patch.setattr(subprocess, "Popen", deny)
        with pytest.raises(PermissionError, match="mechanism denied"):
            saved.path.open()
        with pytest.raises(PermissionError, match="mechanism denied"):
            subprocess.Popen(["forbidden"])
        result = render_record.restore(value, saved.pages[0], saved.path, RENDERER)
    assert result.command[-2] == str(saved.path)


@pytest.fixture
def owner(tmp_path: Path) -> Iterator[ownership.Writer]:
    path = tmp_path / "Saved project"
    path.mkdir()
    with ownership.Writer.acquire(path, ownership.provision(path)) as held:
        yield held


@pytest.mark.parametrize("bad_predecessor", [False, True])
def test_complete_history_checks_renderer_policy_below_good_current(
    owner: ownership.Writer,
    saved: intake.Snapshot,
    bad_predecessor: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bookscan import render_record

    stores = project_header.Stores.provision(owner)
    good: dict[str, object] = {"render": literal(saved)}
    bad = copy.deepcopy(good)
    cast(list[str], cast(dict[str, object], bad["render"])["command"])[7] = "300"
    previous = stores.checkpoints.commit(
        bad if bad_predecessor else good,
        expected=None,
        verify_state=lambda _: None,
    ).checkpoint
    stores.checkpoints.commit(good, expected=previous, verify_state=lambda _: None)
    path = owner.path
    owner.close()
    before = {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()}

    def verify(images: object, state: dict[str, object]) -> None:
        render_record.restore(state["render"], saved.pages[0], saved.path, RENDERER)

    def deny(*args: object, **kwargs: object) -> None:
        raise PermissionError("native launch denied")

    monkeypatch.setattr(subprocess, "Popen", deny)
    if bad_predecessor:
        with pytest.raises(render_record.RenderRecordError):
            with project_header.resume(
                path, verify_state=lambda stores, state: verify(stores.images, state)
            ):
                pytest.fail("bad predecessor render policy accepted")
    else:
        with project_header.resume(
            path, verify_state=lambda stores, state: verify(stores.images, state)
        ) as (_, current):
            assert current.revision == 2 and current.state == good
    assert {p.name: p.read_bytes() for p in (path / "checkpoints").iterdir()} == before
