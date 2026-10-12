"""Own one precreated native PNG, never infer cleanup ownership from a filename.

The trusted renderer may write only the held file until its invocation is reaped.
Capture those writes at that boundary; later changes retain the workspace. These
checks detect changes, not hostile same-user races between stat and unlink.
"""

import os
import stat
import sys
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from bookscan import project_reservation
from bookscan.import_publications import stamp


class WorkspaceError(RuntimeError):
    pass


@contextmanager
def _held(
    reservation: project_reservation.Reservation,
) -> Iterator[project_reservation.Reservation]:
    # Close only; ordinary Reservation exceptional exit can remove an empty
    # root by identity without this operation's additional mode/stamp checks.
    try:
        yield reservation
    finally:
        selected = sys.exception()
        try:
            reservation.close()
        except (OSError, project_reservation.ReservationError) as error:
            if selected is None:
                raise WorkspaceError("Cannot close render reservation.") from error
            selected.add_note("Render reservation close failed: " + str(error))


@dataclass
class Workspace:
    reservation: project_reservation.Reservation
    descriptor: int
    directory_stamp: tuple[int, ...]
    file_stamp: tuple[int, ...]

    @property
    def path(self) -> Path:
        return self.reservation.path / "page.png"

    def verify(self) -> None:
        try:
            self.reservation.verify()
            if (
                stamp(self.reservation.path.lstat()) != self.directory_stamp
                or {p.name for p in self.reservation.path.iterdir()} != {"page.png"}
                or stamp(os.fstat(self.descriptor)) != self.file_stamp
                or stamp(self.path.lstat()) != self.file_stamp
            ):
                raise WorkspaceError("Render output/root changed; retaining the workspace.")
        except (OSError, project_reservation.ReservationError) as error:
            raise WorkspaceError("Cannot verify owned render output/root.") from error

    @contextmanager
    def writing(self) -> Iterator[None]:
        """Capture native writes only after the caller completes/reaps its child."""
        self.verify()
        try:
            yield
        finally:
            selected = sys.exception()
            try:
                self.reservation.verify()
                held = os.fstat(self.descriptor)
                if (
                    stamp(held)[:4] != self.file_stamp[:4]
                    or stamp(self.path.lstat()) != stamp(held)
                    or stamp(self.reservation.path.lstat()) != self.directory_stamp
                    or {p.name for p in self.reservation.path.iterdir()} != {"page.png"}
                ):
                    raise WorkspaceError("Native render changed output ownership; retaining it.")
                self.file_stamp = stamp(held)
                self.verify()
            except (OSError, project_reservation.ReservationError, WorkspaceError) as error:
                if selected is None:
                    raise WorkspaceError("Cannot capture native render writes.") from error
                selected.add_note("Render ownership capture failed: " + str(error))

    def cleanup(self) -> None:
        self.verify()
        self.reservation.remove_file(
            "page.png", matches=lambda entry: stamp(entry) == self.file_stamp
        )
        # Only our successful known unlink may change directory size/times.
        # Preserve a changed mode/identity or any remaining name. APFS directory
        # link counts change for regular children too, so do not assume POSIX 2.
        self.reservation.verify()
        root = stamp(self.reservation.path.lstat())
        if root[:3] != self.directory_stamp[:3] or list(self.reservation.path.iterdir()):
            raise WorkspaceError("Render root changed after own unlink; retaining it.")
        if stamp(self.reservation.path.lstat()) != root:
            raise WorkspaceError("Render root changed before removal; retaining it.")
        self.reservation.remove_empty()


@contextmanager
def output() -> Iterator[Workspace]:
    """Hold an exclusive noninheritable PNG until exact cleanup and one close.

    Poppler 26.10.0 writePageImage uses fopen wb, not replacement publication:
    https://poppler.freedesktop.org/poppler-26.10.0.tar.xz (utils/pdftocairo.cc).
    Native write capture therefore permits size/timestamp changes on this inode
    only. No returned creation descriptor means no authority to remove a file.
    """
    try:
        reservation = project_reservation.reserve(
            Path(tempfile.gettempdir()) / ("bookscan-render-" + uuid.uuid4().hex)
        )
    except (OSError, project_reservation.ReservationError) as error:
        raise WorkspaceError("Cannot reserve private render directory.") from error
    with _held(reservation) as reserved:
        descriptor = -1
        captured: Workspace | None = None
        try:
            original = stamp(reserved.path.lstat())
        except OSError as error:
            raise WorkspaceError("Cannot capture private render directory.") from error
        try:
            try:
                descriptor = os.open(
                    reserved.path / "page.png",
                    os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                )
                created = os.fstat(descriptor)
                current = stamp(reserved.path.lstat())
                if (
                    current[:3] != original[:3]
                    or not stat.S_ISREG(created.st_mode)
                    or created.st_nlink != 1
                    or created.st_size != 0
                ):
                    raise WorkspaceError("Created render output/root changed before capture.")
                captured = Workspace(reserved, descriptor, current, stamp(created))
                captured.verify()
            except (OSError, project_reservation.ReservationError) as error:
                raise WorkspaceError("Cannot create/capture render output.") from error
            yield captured
        finally:
            selected = sys.exception()
            try:
                if captured is not None:
                    captured.cleanup()
                else:
                    reserved.verify()
                    if stamp(reserved.path.lstat()) != original:
                        raise WorkspaceError("Uncaptured render output/root retained.")
                    reserved.remove_empty()
            except (OSError, project_reservation.ReservationError, WorkspaceError) as error:
                if selected is None:
                    raise WorkspaceError(
                        "Cannot clean exact render workspace: " + str(error)
                    ) from error
                selected.add_note("Render cleanup retained: " + str(error))
            finally:
                if descriptor >= 0:
                    selected = sys.exception()
                    try:
                        os.close(descriptor)
                    except OSError as error:
                        if selected is None:
                            raise WorkspaceError(
                                "Cannot close render output descriptor."
                            ) from error
                        selected.add_note("Render descriptor close failed: " + str(error))
