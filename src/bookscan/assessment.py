"""Couple complete import evidence per occurrence, without accepted state or image edits.

The transaction owner preflights tools and later publishes all referenced assets
and records together. Iteration is uncommitted; a yielded page is no checkpoint.
Independent composition truth is still unavailable, including on apparently
simple pages: placement/sample/renderer equality supplies no fidelity verdict.
"""

import copy
import hashlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from bookscan import (
    analysis_record,
    native_inventory_record,
    native_setup,
    render,
    samples,
    triage_record,
)
from bookscan.intake import ImportFailure, Page, Snapshot
from bookscan.resources import ResourceBinding
from bookscan.skew import AssessmentFailed, Estimate
from bookscan.triage_record import Reason

LIMITATION = (
    "Within-page geometry unverified; rigid rotation and book alignment do not correct "
    "curvature or scanner-feed variation."
)


@dataclass(frozen=True)
class AssessedPage:
    source_sha256: str
    page: Page
    raster: render.Raster
    native: samples.Inventory
    estimate: Estimate
    reasons: tuple[Reason, ...]

    def to_dict(self) -> dict[str, object]:
        """Return detached JSON data; packed samples/profiles remain separate assets."""
        page, frame, hint = self.page, self.page.frame, self.page.hint
        return {
            "id": f"occ-{page.source_page:06d}",
            "source_pdf_page": page.source_page,
            "source_sha256": self.source_sha256,
            "geometry": {
                "boxes": [[str(v) for v in box] for box in page.geometry.boxes],
                "rotate": page.geometry.rotate,
                "user_unit": str(page.geometry.user_unit),
                "physical_points": [str(v) for v in frame.points],
                "pixels": list(frame.pixels),
                "matrix": [str(v) for v in frame.matrix],
                "extent_changed": frame.extent_changed,
            },
            "advisory_hint": (
                {
                    "role": hint.role,
                    "source_sha256": hint.source_sha256,
                    "source_page": hint.source_page,
                }
                if hint
                else None
            ),
            "rgb_sha256": hashlib.sha256(self.raster.rgb).hexdigest(),
            "render": {
                "command": list(self.raster.command),
                "diagnostics": self.raster.diagnostics,
                **(
                    {"resource_binding": copy.deepcopy(self.raster.resource_binding)}
                    if self.raster.resource_binding is not None
                    else {}
                ),
            },
            **native_inventory_record.record(self.native),
            "analysis": analysis_record.record(self.estimate, self.raster.size),
            "triage_reasons": triage_record.record(
                self.reasons, page, self.estimate, self.native, self.raster.diagnostics
            ),
            "limitation": LIMITATION,
            "retention": "baseline-retained/unresolved",
            "estimate_applied": False,
            "inspected": False,
        }


def assess_page(
    saved: Snapshot,
    page: Page,
    renderer: Path,
    helper: Path,
    directory: Path,
    *,
    check_cancel: Callable[[], None] = lambda: None,
    resources: ResourceBinding | None = None,
) -> AssessedPage:
    saved.verify(check_cancel=check_cancel)
    ordinal = page.source_page
    if not 1 <= ordinal <= len(saved.pages) or page != saved.pages[ordinal - 1]:
        raise ImportFailure("INVALID_PROJECT", "Assessment occurrence differs from saved snapshot.")
    raster = render.render_page(
        saved, page, renderer, check_cancel=check_cancel, resources=resources
    )
    width, height = page.frame.pixels
    if raster.size != (width, height) or len(raster.rgb) != width * height * 3:
        raise AssessmentFailed("Assessment requires complete full-size RGB.")
    inventory = samples.collect(saved, page, check_cancel=check_cancel)
    check_cancel()
    # Pillow 12.3 frombytes allocates a new decoded buffer, unlike frombuffer.
    # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.frombytes
    with Image.frombytes("RGB", raster.size, raster.rgb) as baseline:
        estimate = native_setup.assess(helper, baseline, directory, check_cancel=check_cancel)
        if (
            baseline.mode != "RGB"
            or baseline.size != raster.size
            or baseline.tobytes() != raster.rgb
        ):
            raise AssessmentFailed("Advisory analysis modified the retained RGB image.")
    if estimate.region != (0, 0, width, height):
        raise AssessmentFailed("Advisory analysis region differs from the whole baseline.")
    reasons = triage_record.derive(page, estimate, inventory, raster.diagnostics)
    check_cancel()
    saved.verify(check_cancel=check_cancel)
    if resources is not None:
        resources.verify(check_cancel=check_cancel)
    return AssessedPage(saved.sha256, page, raster, inventory, estimate, reasons)


def assess_pages(
    saved: Snapshot,
    renderer: Path,
    helper: Path,
    directory: Path,
    *,
    check_cancel: Callable[[], None] = lambda: None,
    resources: ResourceBinding | None = None,
) -> Iterator[AssessedPage]:
    """Yield every source position, with no hint exemption, duplicate or blank skip."""
    for page in saved.pages:
        check_cancel()
        yield assess_page(
            saved,
            page,
            renderer,
            helper,
            directory,
            check_cancel=check_cancel,
            resources=resources,
        )
