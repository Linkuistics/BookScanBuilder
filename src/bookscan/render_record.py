"""Read saved full-MediaBox renderer policy using already checked input identities.

This pure component returns command/decoder facts only. Optional resource-binding
payloads require their own semantic reader and are never returned here. Matching
policy does not prove historical execution, RGB authenticity or source fidelity;
the complete project verifier must separately check those dependencies.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from bookscan import records
from bookscan.intake import Page


@dataclass
class RenderRecordError(Exception):
    message: str
    code: str = "INVALID_PROJECT"
    exit_code: int = 3

    @property
    def remediation(self) -> str:
        return (
            "Use the compatible BookScanBuilder assessment-v1 reader with bookscan baseline "
            "status PROJECT; for damaged saved content use bookscan baseline create PDF "
            "--workdir NEW with an intact supported input. Fresh import loses review facts. "
            "Without intact input or a verifiable saved state no recovery is available."
        )

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True)
class RenderFacts:
    command: tuple[str, ...]
    diagnostics: str


def _object(value: object) -> dict[str, object]:
    try:
        # Serialize first so circular direct inputs fail before the type walk.
        # https://docs.python.org/3.12/library/json.html#json.dumps
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        records.decode(raw)
        pending = [value]
        while pending:
            item = pending.pop()
            if type(item) is dict:
                data = cast(dict[object, object], item)
                if any(type(key) is not str for key in data):
                    raise ValueError("Non-string saved key.")
                pending.extend(data.values())
            elif type(item) is list:
                pending.extend(cast(list[object], item))
            elif item is not None and type(item) not in (str, int, float, bool):
                raise ValueError("Non-JSON saved value.")
    except (ValueError, TypeError, RecursionError, records.RecordError) as error:
        raise RenderRecordError("Invalid saved render JSON values.") from error
    return cast(dict[str, object], value)


def _path(value: str) -> Path:
    path = Path(value)
    if "\0" in value or not path.is_absolute() or ".." in path.parts or str(path) != value:
        raise RenderRecordError("Invalid saved renderer/source/output path.")
    return path


def restore(value: object, page: Page, snapshot: Path, renderer: Path) -> RenderFacts:
    """Bind policy to verified source-page/snapshot and historical renderer inputs.

    The full verifier supplies the checked inputs and verifies optional resources.
    No file opens, native launch, build, lock acquisition or mutation occurs here.
    Historical temporary output need not exist; it is never consumed as an asset.
    """
    data = _object(value)
    if set(data) not in (
        {"command", "diagnostics"},
        {"command", "diagnostics", "resource_binding"},
    ):
        raise RenderRecordError("Unsupported saved render fields.")
    if "resource_binding" in data and type(data["resource_binding"]) is not dict:
        raise RenderRecordError("Saved resource binding must be a separately verified object.")
    command, diagnostics = data["command"], data["diagnostics"]
    if (
        type(command) is not list
        or len(cast(list[object], command)) != 17
        or any(type(token) is not str or "\0" in token for token in cast(list[object], command))
        or type(diagnostics) is not str
    ):
        raise RenderRecordError("Invalid saved render command/diagnostics types.")
    tokens = tuple(cast(list[str], command))
    for index in (0, 15, 16):
        _path(tokens[index])
    prefix = Path(tokens[16])
    if (
        prefix.name != "page"
        or re.fullmatch("bookscan-render-[A-Za-z0-9_]+", prefix.parent.name) is None
    ):
        raise RenderRecordError("Saved output is not a private historical render prefix.")
    # Poppler 26.10.0 applies DPI/72 without UserUnit; the product compensates in
    # DPI and specifies exact rational MediaBox pixel extents, without resampling.
    # https://poppler.freedesktop.org/poppler-26.10.0.tar.xz
    expected = (
        str(renderer),
        "-f",
        str(page.source_page),
        "-l",
        str(page.source_page),
        "-singlefile",
        "-r",
        format(page.geometry.user_unit * 300, "f"),
        "-W",
        str(page.frame.pixels[0]),
        "-H",
        str(page.frame.pixels[1]),
        "-png",
        "-antialias",
        "default",
        str(snapshot),
        tokens[-1],
    )
    if tokens != expected:
        raise RenderRecordError("Saved renderer policy differs from checked page/source/renderer.")
    return RenderFacts(tokens, diagnostics)
