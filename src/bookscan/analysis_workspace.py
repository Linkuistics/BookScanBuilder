"""One advisory input's transient creation evidence, never reconstructed on resume.

Only the returned exclusive creation descriptor grants file ownership. Native
use starts after capture; changed/unknown entries retain the reservation. This
guards detected changes, not hostile same-user races between stat and unlink.
"""

import os
import stat
import sys
import uuid
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from bookscan import project_reservation
from bookscan.import_publications import stamp
from bookscan.skew import AssessmentFailed, write_analysis_stream


@dataclass(frozen=True)
class Workspace:
    reservation: project_reservation.Reservation
    directory_stamp: tuple[int, ...]
    file_stamp: tuple[int, ...]

    @property
    def path(self) -> Path:
        return self.reservation.path / "whole.png"

    def verify(self) -> None:
        try:
            self.reservation.verify()
            if (
                stamp(self.reservation.path.lstat()) != self.directory_stamp
                or {entry.name for entry in self.reservation.path.iterdir()} != {"whole.png"}
                or stamp(self.path.lstat()) != self.file_stamp
            ):
                raise AssessmentFailed("Analysis reservation/input changed; retaining it.")
        except (OSError, project_reservation.ReservationError) as error:
            raise AssessmentFailed("Cannot verify owned analysis reservation/input.") from error

    def cleanup(self) -> None:
        self.verify()
        try:
            self.reservation.remove_file(
                "whole.png", matches=lambda entry: stamp(entry) == self.file_stamp
            )
            self.reservation.remove_empty()
        except project_reservation.ReservationError as error:
            raise AssessmentFailed("Cannot remove exact owned analysis input/root.") from error


def _capture(
    reservation: project_reservation.Reservation,
    descriptor: int,
    created: os.stat_result,
    directory: os.stat_result,
) -> Workspace:
    reservation.verify()
    current, held = reservation.path.lstat(), os.fstat(descriptor)
    if (
        stamp(current)[:3] != stamp(directory)[:3]
        or stamp(held)[:3] != stamp(created)[:3]
        or not stat.S_ISREG(held.st_mode)
        or held.st_nlink != 1
    ):
        raise AssessmentFailed("Created analysis input/root changed before capture.")
    result = Workspace(reservation, stamp(current), stamp(held))
    result.verify()
    return result


@contextmanager
def image(baseline: Image.Image, directory: Path) -> Iterator[Workspace]:
    """Write/capture one disposable grayscale input, then clean exact names only.

    Capture partial own writes at the writer boundary, before any native child.
    Unknown open outcomes retain files. Cleanup never calls cancellation and
    never replaces a selected native/write/cancellation error.
    """
    # close-only context: Reservation's ordinary exceptional exit may remove an
    # empty root by identity alone; this operation additionally guards its stamp.
    with closing(
        project_reservation.reserve(directory / (".analysis-" + uuid.uuid4().hex))
    ) as reserved:
        captured: Workspace | None = None
        descriptor = -1
        original = reserved.path.lstat()
        try:
            descriptor = os.open(
                reserved.path / "whole.png",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
            )
            created = os.fstat(descriptor)
            try:
                # Unbuffered writes finish before capture, even on a partial
                # encoder failure; wrapper close never closes the creation fd.
                # https://docs.python.org/3.12/library/os.html#os.fdopen
                with os.fdopen(descriptor, "wb", buffering=0, closefd=False) as stream:
                    write_analysis_stream(baseline, stream)
            finally:
                selected = sys.exception()
                try:
                    captured = _capture(reserved, descriptor, created, original)
                except (OSError, project_reservation.ReservationError, AssessmentFailed) as error:
                    if selected is None:
                        raise
                    selected.add_note("Analysis ownership capture failed: " + str(error))
            if captured is None:
                raise AssessmentFailed("Analysis input ownership was not captured.")
            captured.verify()
            yield captured
        finally:
            selected = sys.exception()
            try:
                if captured is not None:
                    captured.cleanup()
                else:
                    # Only a still-exact empty pre-file root is removable.
                    # Unknown open outcomes cannot confer file ownership.
                    reserved.verify()
                    if stamp(reserved.path.lstat()) != stamp(original):
                        raise AssessmentFailed("Uncaptured analysis input/root retained.")
                    reserved.remove_empty()
            except (OSError, project_reservation.ReservationError, AssessmentFailed) as error:
                if selected is None:
                    raise
                selected.add_note("Analysis cleanup retained: " + str(error))
            finally:
                if descriptor >= 0:
                    selected = sys.exception()
                    try:
                        os.close(descriptor)
                    except OSError as error:
                        if selected is None:
                            raise AssessmentFailed(
                                "Cannot close analysis input descriptor."
                            ) from error
                        selected.add_note("Analysis descriptor close failed: " + str(error))
