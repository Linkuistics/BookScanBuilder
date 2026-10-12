"""Conservative contributing-image inventory, independent of raster rendering.

Complete means every possible image-bearing drawing path was accounted for,
not source fidelity. Clipping and occlusion never remove a placement. Missing
paths retain partial diagnostics but prohibit a complete-resolution conclusion.
Native sample decoding/composition truth is a separate responsibility.
"""

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import cast

import pikepdf

from bookscan.intake import ImportFailure, Page, Snapshot
from bookscan.pdf import get

type Matrix = tuple[Fraction, Fraction, Fraction, Fraction, Fraction, Fraction]
IDENTITY: Matrix = (Fraction(1), Fraction(0), Fraction(0), Fraction(1), Fraction(0), Fraction(0))
type ImageObserver = Callable[
    [pikepdf.Object | pikepdf.PdfInlineImage, object, Placement, Callable[[], None]], None
]


class Unavailable(ValueError):
    """An image-bearing path cannot be completely interpreted."""


def numbers(value: Iterable[object], count: int) -> tuple[Fraction, ...]:
    values = tuple(value)
    if len(values) != count or any(type(v) not in {int, Decimal} for v in values):
        raise Unavailable(f"expected {count} finite PDF numbers")
    try:
        return tuple(Fraction(cast(int | Decimal, v)) for v in values)
    except (ValueError, OverflowError) as error:
        raise Unavailable("nonfinite PDF number") from error


def matrix(value: object) -> Matrix:
    if not isinstance(value, pikepdf.Array):
        raise Unavailable("expected transformation array")
    return cast(Matrix, numbers(cast(Iterable[object], value), 6))


def concatenate(outer: Matrix, inner: Matrix) -> Matrix:
    # PDF uses row vectors: new transformations premultiply the existing CTM.
    # ISO 32000-1 8.3.4: https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
    a, b, c, d, e, f = outer
    g, h, i, j, k, offset_y = inner
    return (
        a * g + c * h,
        b * g + d * h,
        a * i + c * j,
        b * i + d * j,
        a * k + c * offset_y + e,
        b * k + d * offset_y + f,
    )


@dataclass(frozen=True)
class Placement:
    path: tuple[str, ...]
    object_id: tuple[int, int]
    kind: str
    samples: tuple[int, int]
    bits_per_component: int | None
    color_space: str | None
    matrix: Matrix  # image unit-square -> top-left baseline pixel edges
    ppi: tuple[float, float]  # intrinsic sample-x/sample-y axes, not screen axes

    @property
    def above_baseline_resolution(self) -> bool:
        # Compare squared rational lengths: float reporting must not erase an
        # above-300 concern at a near-boundary decimal placement.
        a, b, c, d, _, _ = self.matrix
        width, height = self.samples
        return width * width > a * a + b * b or height * height > c * c + d * d


@dataclass(frozen=True)
class Analysis:
    placements: tuple[Placement, ...]
    concerns: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.concerns

    @property
    def maximum_ppi(self) -> float | None:
        if not self.complete or not self.placements:
            return None
        return max(max(p.ppi) for p in self.placements)

    @property
    def import_fidelity(self) -> bool:
        """Whether resolution requires this reason; never a source-fidelity verdict."""
        return not self.complete or any(p.above_baseline_resolution for p in self.placements)


def resource(resources: object, category: str, name: object) -> pikepdf.Object:
    if not isinstance(resources, pikepdf.Dictionary) or not isinstance(name, pikepdf.Name):
        raise Unavailable(f"missing/malformed {category} resource")
    entries = get(resources, category)
    if not isinstance(entries, pikepdf.Dictionary):
        raise Unavailable(f"missing/malformed {category} {name}")
    value = get(entries, str(name))
    if not isinstance(value, pikepdf.Object):
        raise Unavailable(f"missing/malformed {category} {name}")
    return value


# These operators cannot introduce image-bearing resource paths. Paths/clips,
# text positioning and colour still affect composition; no fidelity is inferred.
PLAIN = frozenset(
    "w J j M d ri i m l c v y h re S s f F f* B B* b b* n W W* "
    "BT ET Tc Tw Tz TL Tr Ts Td TD Tm T* Tj TJ ' \" "
    "G g RG rg K k CS cs SC sc MP DP BMC BDC EMC BX EX d0 d1".split()
)


class Inventory:
    def __init__(
        self, check_cancel: Callable[[], None], image_observer: ImageObserver | None = None
    ):
        self._check_cancel = check_cancel
        self._image_observer = image_observer
        self._owner_error: BaseException | None = None
        self.placements: list[Placement] = []
        self.concerns: list[str] = []
        self.active: set[tuple[int, int]] = set()

    def check_cancel(self) -> None:
        try:
            self._check_cancel()
        except BaseException as error:
            # Nested traversal catches malformed-PDF exceptions of some of the
            # same types. Keep the owner's actual chosen exception identifiable.
            self._owner_error = error
            raise

    def unavailable(self, path: tuple[str, ...], error: BaseException) -> None:
        if error is self._owner_error:
            raise error
        self.concern(path, str(error))

    def concern(self, path: tuple[str, ...], message: str) -> None:
        self.concerns.append("/".join(path) + ": " + message)

    def image(
        self,
        obj: pikepdf.Object,
        ctm: Matrix,
        resources: object,
        path: tuple[str, ...],
        kind: str,
        inline: pikepdf.PdfInlineImage | None = None,
    ) -> None:
        self.check_cancel()
        if len(self.active) > 64:
            raise Unavailable("form/mask nesting exceeds analyzer depth")
        width, height = get(obj, "/Width"), get(obj, "/Height")
        if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
            raise Unavailable("invalid intrinsic image dimensions")
        a, b, c, d, _, _ = ctm
        if a * d == b * c:
            raise Unavailable("singular image placement")
        try:
            lengths = math.hypot(float(a), float(b)), math.hypot(float(c), float(d))
            ppi = width * 300 / lengths[0], height * 300 / lengths[1]
        except (OverflowError, ZeroDivisionError) as error:
            raise Unavailable("unrepresentable physical resolution") from error
        if any(not math.isfinite(v) or v <= 0 for v in ppi):
            raise Unavailable("nonfinite physical resolution")
        stencil = get(obj, "/ImageMask", False)
        if type(stencil) is not bool:
            raise Unavailable("malformed ImageMask")
        bpc = get(obj, "/BitsPerComponent", 1 if stencil else None)
        if bpc is not None and (type(bpc) is not int or bpc not in {1, 2, 4, 8, 16}):
            raise Unavailable("malformed BitsPerComponent")
        color = get(obj, "/ColorSpace")
        if isinstance(color, pikepdf.Name) and str(color) not in {
            "/DeviceGray",
            "/DeviceRGB",
            "/DeviceCMYK",
        }:
            color = resource(resources, "/ColorSpace", color)
        self.placements.append(
            Placement(
                path,
                obj.objgen,
                "stencil" if stencil and kind == "image" else kind,
                (width, height),
                bpc,
                None if color is None else str(color),
                ctm,
                ppi,
            )
        )
        if self._image_observer is not None:
            self._image_observer(
                inline if inline is not None else obj,
                resources,
                self.placements[-1],
                self.check_cancel,
            )
        if get(obj, "/Alternates") is not None:
            self.concern(path, "alternate image selection unavailable")
        for key, mask_kind in (("/Mask", "mask"), ("/SMask", "soft-mask")):
            child = get(obj, key)
            if child is None or (key == "/Mask" and isinstance(child, pikepdf.Array)):
                continue
            if not isinstance(child, pikepdf.Stream):
                self.concern(path + (key,), "malformed image mask")
                continue
            if child.objgen in self.active:
                self.concern(path + (key,), "image-mask cycle")
                continue
            self.active.add(child.objgen)
            try:
                self.image(child, ctm, resources, path + (key,), mask_kind)
            except Unavailable as error:
                self.unavailable(path + (key,), error)
            finally:
                self.active.remove(child.objgen)

    def form(
        self, obj: pikepdf.Object, ctm: Matrix, resources: object, path: tuple[str, ...]
    ) -> None:
        if not isinstance(obj, pikepdf.Stream):
            raise Unavailable("form is not a stream")
        if obj.objgen in self.active:
            raise Unavailable("form cycle")
        if len(self.active) >= 64:
            raise Unavailable("form/mask nesting exceeds analyzer depth")
        transform = matrix(get(obj, "/Matrix", pikepdf.Array([1, 0, 0, 1, 0, 0])))
        self.active.add(obj.objgen)
        try:
            # Form resources shadow caller resources; absence inherits (PDF 1.2).
            # ISO 32000-1 8.10, Table 97 (same primary PDF URL as above).
            local = get(obj, "/Resources", resources)
            self.walk(obj, concatenate(ctm, transform), local, path)
        finally:
            self.active.remove(obj.objgen)

    def walk(
        self,
        obj: pikepdf.Object | pikepdf.Page,
        ctm: Matrix,
        resources: object,
        path: tuple[str, ...],
    ) -> None:
        self.check_cancel()
        stack: list[Matrix] = []
        try:
            # Parse ALL operators: a filtered q/Q/cm/Do scan can silently omit images.
            # Exact API: https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/models/_content_stream.py
            instructions = pikepdf.parse_content_stream(obj)
        except (pikepdf.PdfError, TypeError, ValueError) as error:
            self.concern(path, f"content parsing unavailable: {error}")
            return
        for index, instruction in enumerate(instructions):
            self.check_cancel()
            here = path + (str(index),)
            try:
                if isinstance(instruction, pikepdf.ContentStreamInlineImage):
                    # Inline dictionaries expand key/value abbreviations in pinned source.
                    # https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/models/image/_classes.py
                    self.image(
                        instruction.iimage.obj, ctm, resources, here, "inline", instruction.iimage
                    )
                    continue
                operands = list(cast(Iterable[object], instruction.operands))
                op = str(instruction.operator)
                if op == "q":
                    if operands:
                        raise Unavailable("malformed q")
                    stack.append(ctm)
                elif op == "Q":
                    if operands or not stack:
                        raise Unavailable("unbalanced/malformed Q")
                    ctm = stack.pop()
                elif op == "cm":
                    ctm = concatenate(ctm, cast(Matrix, numbers(operands, 6)))
                elif op == "Do":
                    if len(operands) != 1:
                        raise Unavailable("malformed Do")
                    child = resource(resources, "/XObject", operands[0])
                    subtype = get(child, "/Subtype")
                    if subtype == pikepdf.Name.Image and isinstance(child, pikepdf.Stream):
                        self.active.add(child.objgen)
                        try:
                            self.image(child, ctm, resources, here + (str(operands[0]),), "image")
                        finally:
                            self.active.remove(child.objgen)
                    elif subtype == pikepdf.Name.Form:
                        self.form(child, ctm, resources, here + (str(operands[0]),))
                    else:
                        raise Unavailable("unaccounted XObject subtype")
                elif op == "gs":
                    if len(operands) != 1:
                        raise Unavailable("malformed gs")
                    state = resource(resources, "/ExtGState", operands[0])
                    if get(state, "/SMask", pikepdf.Name("/None")) != pikepdf.Name("/None"):
                        raise Unavailable("graphics-state soft-mask composition unavailable")
                    font = get(state, "/Font")
                    if font is not None:
                        raise Unavailable("graphics-state font image paths unavailable")
                elif op == "Tf":
                    if len(operands) != 2:
                        raise Unavailable("malformed Tf")
                    font = resource(resources, "/Font", operands[0])
                    if get(font, "/Subtype") == pikepdf.Name.Type3:
                        raise Unavailable("Type3 glyph image paths unavailable")
                elif op in {"scn", "SCN"}:
                    if any(isinstance(v, pikepdf.Name) for v in operands):
                        raise Unavailable("pattern image paths unavailable")
                elif op == "sh":
                    raise Unavailable("shading/native sample grid unavailable")
                elif op not in PLAIN:
                    raise Unavailable(f"unaccounted drawing operator {op}")
            except (Unavailable, pikepdf.PdfError, TypeError, ValueError) as error:
                self.unavailable(here, error)
        if stack:
            self.concern(path, "unbalanced q")
        self.check_cancel()

    def annotations(self, page: pikepdf.Page, ctm: Matrix, resources: object) -> None:
        annotations = get(page.obj, "/Annots", pikepdf.Array())
        if not isinstance(annotations, pikepdf.Array):
            self.concern(("annotations",), "malformed annotation list")
            return
        for index, entry in enumerate(cast(Iterable[object], annotations)):
            self.check_cancel()
            path = ("annotation", str(index))
            try:
                if not isinstance(entry, pikepdf.Dictionary):
                    raise Unavailable("malformed annotation")
                if get(entry, "/Subtype") == pikepdf.Name.Link:
                    # Snapshot intake already gated these as no-AP/zero-border
                    # navigation only; the original snapshot preserves their bytes.
                    continue
                flags = get(entry, "/F", 0)
                if type(flags) is not int:
                    raise Unavailable("malformed annotation flags")
                # Cairo PNG uses printing=false; standard static appearances
                # with Invisible are still drawn. Hidden/NoView are not.
                # Poppler 26.10.0 Annot::isVisible / pdftocairo (official tarball):
                # https://poppler.freedesktop.org/poppler-26.10.0.tar.xz
                if flags & (2 | 32):
                    continue
                if flags & (8 | 16):
                    raise Unavailable("NoZoom/NoRotate appearance mapping unavailable")
                ap = get(entry, "/AP")
                if not isinstance(ap, pikepdf.Dictionary):
                    raise Unavailable("missing static appearance")
                normal = get(ap, "/N")
                if isinstance(normal, pikepdf.Dictionary):
                    normal = get(normal, str(get(entry, "/AS")))
                if not isinstance(normal, pikepdf.Stream):
                    raise Unavailable("missing selected normal appearance")
                bbox, rect = get(normal, "/BBox"), get(entry, "/Rect")
                if not isinstance(bbox, pikepdf.Array) or not isinstance(rect, pikepdf.Array):
                    raise Unavailable("missing appearance bounds")
                x0, y0, x1, y1 = numbers(cast(Iterable[object], bbox), 4)
                rx0, ry0, rx1, ry1 = numbers(cast(Iterable[object], rect), 4)
                rx0, rx1 = sorted((rx0, rx1))
                ry0, ry1 = sorted((ry0, ry1))
                a, b, c, d, e, f = matrix(get(normal, "/Matrix", pikepdf.Array([1, 0, 0, 1, 0, 0])))
                points = [
                    (a * x + c * y + e, b * x + d * y + f) for x in (x0, x1) for y in (y0, y1)
                ]
                left, right = min(p[0] for p in points), max(p[0] for p in points)
                bottom, top = min(p[1] for p in points), max(p[1] for p in points)
                if right <= left or top <= bottom or rx1 <= rx0 or ry1 <= ry0:
                    raise Unavailable("degenerate appearance bounds")
                sx, sy = (rx1 - rx0) / (right - left), (ry1 - ry0) / (top - bottom)
                # ISO 32000-1 12.5.5: Matrix -> bounding rectangle -> Rect mapping.
                # https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
                placement: Matrix = (
                    sx,
                    Fraction(0),
                    Fraction(0),
                    sy,
                    rx0 - left * sx,
                    ry0 - bottom * sy,
                )
                self.form(normal, concatenate(ctm, placement), resources, path)
            except (Unavailable, pikepdf.PdfError, TypeError, ValueError) as error:
                self.unavailable(path, error)


def analyze(
    saved: Snapshot,
    page: Page,
    *,
    check_cancel: Callable[[], None] = lambda: None,
    image_observer: ImageObserver | None = None,
) -> Analysis:
    """Read only a verified saved occurrence; callers own dependency/commit policy."""
    saved.verify(check_cancel=check_cancel)
    ordinal = page.source_page
    if not 1 <= ordinal <= len(saved.pages) or page != saved.pages[ordinal - 1]:
        raise ImportFailure("INVALID_PROJECT", "Occurrence does not match saved snapshot.")
    inventory = Inventory(check_cancel, image_observer)
    with pikepdf.Pdf.open(saved.path, attempt_recovery=False, suppress_warnings=True) as pdf:
        source = pdf.pages[ordinal - 1]
        # Pdf.open defaults to inherit_page_attributes=True in pinned 10.16.0.
        # https://github.com/pikepdf/pikepdf/blob/v10.16.0/src/pikepdf/_methods.py
        resources = source.Resources
        inventory.walk(source, page.frame.matrix, resources, ("page", str(ordinal)))
        inventory.annotations(source, page.frame.matrix, resources)
        messages = cast(list[str], pdf.get_warnings())  # pyright: ignore[reportUnknownMemberType]
        for warning in messages:
            inventory.concern(("decoder",), warning)
    saved.verify(check_cancel=check_cancel)
    return Analysis(tuple(inventory.placements), tuple(inventory.concerns))
