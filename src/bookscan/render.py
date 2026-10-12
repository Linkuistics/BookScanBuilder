"""Complete static MediaBox rendering into uncommitted RGB, at preserved physical scale."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from bookscan import render_workspace
from bookscan.intake import ImportFailure, Page, Snapshot
from bookscan.native_setup import execute, tool
from bookscan.resources import ResourceBinding
from bookscan.skew import NativeError


class RenderFailed(RuntimeError):
    code = "RENDER_FAILED"
    exit_code = 5
    remediation = "Check the named renderer diagnostic and resources; retry the supported input."


@dataclass(frozen=True)
class Raster:
    size: tuple[int, int]
    rgb: bytes
    diagnostics: str
    command: tuple[str, ...]
    resource_binding: dict[str, object] | None = None


def renderer_path(*, check_cancel: Callable[[], None] = lambda: None) -> Path:
    """Read-only Cairo version check; caller still owns complete dependency provenance."""
    check_cancel()
    path = tool("pdftocairo")
    result = execute([str(path), "-v"], check_cancel=check_cancel)
    lines = (result.stdout + result.stderr).splitlines()
    if result.returncode != 0 or not lines or lines[0] != "pdftocairo version 26.10.0":
        raise NativeError("Unsupported Poppler Cairo; verified pdftocairo version is 26.10.0.")
    check_cancel()
    return path


def _decode(path: Path, size: tuple[int, int]) -> bytes:
    try:
        # No convert/resize fallback: the renderer must supply complete RGB.
        # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.open
        with Image.open(path) as image:
            if image.format != "PNG" or image.mode != "RGB" or image.size != size:
                raise RenderFailed(
                    f"Expected complete RGB PNG {size}; "
                    f"got {image.format}/{image.mode}/{image.size}."
                )
            image.load()
            data = image.tobytes()
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise RenderFailed(f"Cannot decode complete renderer output {path}: {error}") from error
    if len(data) != size[0] * size[1] * 3:
        raise RenderFailed("Renderer output has an incomplete RGB buffer.")
    return data


def render_page(
    saved: Snapshot,
    page: Page,
    renderer: Path,
    *,
    check_cancel: Callable[[], None] = lambda: None,
    resources: ResourceBinding | None = None,
) -> Raster:
    """Caller preflights renderer and owns the later asset/checkpoint transaction.

    Temporary PNGs are never accepted state. Source-loss rendering uses only the
    verified private snapshot. Caught owner cancellation propagates unchanged.
    """
    saved.verify(check_cancel=check_cancel)
    ordinal = page.source_page
    if not 1 <= ordinal <= len(saved.pages) or page != saved.pages[ordinal - 1]:
        raise ImportFailure("INVALID_PROJECT", "Occurrence/geometry does not match saved snapshot.")
    check_cancel()
    if resources is not None:
        resources.verify(check_cancel=check_cancel)
    try:
        return _render(saved, page, renderer, check_cancel=check_cancel, resources=resources)
    except render_workspace.WorkspaceError as error:
        raise RenderFailed(f"Cannot use exact private render workspace: {error}") from error


def _render(
    saved: Snapshot,
    page: Page,
    renderer: Path,
    *,
    check_cancel: Callable[[], None],
    resources: ResourceBinding | None,
) -> Raster:
    with render_workspace.output() as workspace:
        prefix = workspace.path.with_suffix("")
        # Poppler 26.10.0 Page/GfxState/pdftoppm use DPI/72 with no UserUnit factor.
        # Compensate in DPI; never resize pixels. Default pdftocairo uses MediaBox.
        # https://poppler.freedesktop.org/poppler-26.10.0.tar.xz
        # pdftocairo ceil(double extent) can add a spurious epsilon row. Specify
        # the exact rational full-page pixel extent; this clips no mathematical
        # MediaBox area and keeps the original DPI/CTM (no scale-to sampling).
        dpi = format(page.geometry.user_unit * 300, "f")
        command = [
            str(renderer),
            "-f",
            str(page.source_page),
            "-l",
            str(page.source_page),
            "-singlefile",
            "-r",
            dpi,
            "-W",
            str(page.frame.pixels[0]),
            "-H",
            str(page.frame.pixels[1]),
            "-png",
            "-antialias",
            "default",
            str(saved.path),
            str(prefix),
        ]
        try:
            with workspace.writing():
                result = (
                    execute(command, check_cancel=check_cancel)
                    if resources is None
                    else execute(
                        command,
                        check_cancel=check_cancel,
                        environment=resources.environment(),
                        directory=resources.directory,
                    )
                )
                if result.returncode != 0:
                    raise RenderFailed(
                        f"Poppler exited {result.returncode}: {result.stderr.strip()}"
                    )
        except NativeError as error:
            raise RenderFailed(str(error)) from error
        check_cancel()
        workspace.verify()
        rgb = _decode(prefix.with_suffix(".png"), page.frame.pixels)
        workspace.verify()
        check_cancel()
        saved.verify(check_cancel=check_cancel)
        if resources is not None:
            resources.verify(check_cancel=check_cancel)
        return Raster(
            page.frame.pixels,
            rgb,
            result.stderr,
            tuple(command),
            None if resources is None else resources.record(),
        )
