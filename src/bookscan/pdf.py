"""Read-only PDF gates and immutable retained-graph projection.

No PDF graph escapes this adapter. Shared nodes/cycles are explicit references
in the snapshot, allowing a later comparator to track source/output node pairs
without imposing an object-number or sharing contract.
"""

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import cast

import pikepdf

from bookscan.results import PreparationError

type Scalar = None | bool | int | Decimal | str | bytes


@dataclass(frozen=True)
class Ref:
    node: int


type Value = Scalar | Ref


@dataclass(frozen=True)
class Node:
    kind: str
    entries: tuple[tuple[str, Value], ...] = ()
    items: tuple[Value, ...] = ()
    raw: bytes | None = None


@dataclass(frozen=True)
class Geometry:
    boxes: tuple[tuple[Decimal, ...], ...]
    rotate: int
    user_unit: Decimal


@dataclass(frozen=True)
class Projection:
    geometry: Geometry
    root: Ref
    nodes: tuple[Node, ...]
    annotated: bool
    annotation_owners: tuple[bool, ...] = ()


@dataclass(frozen=True)
class DocumentInfo:
    version: tuple[int, int]
    extension_level: int


# ISO 32000-1 Table 30, pp.77–79; explicitly classified, not collection-derived.
# https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf
PAGE_STANDARD = frozenset(
    "Type Parent LastModified Resources MediaBox CropBox BleedBox "
    "TrimBox ArtBox BoxColorInfo Contents Rotate Group Thumb B Dur Trans "
    "Annots AA Metadata PieceInfo StructParents ID PZ SeparationInfo Tabs "
    "TemplateInstantiated PresSteps UserUnit VP".split()
)
PAGE_RETAIN = frozenset(
    "Resources MediaBox CropBox BleedBox TrimBox ArtBox Rotate UserUnit "
    "Contents Group BoxColorInfo Annots".split()
)
PAGE_DISCARD = frozenset(
    "Parent Type StructParents Metadata PieceInfo LastModified Thumb B Dur "
    "Trans AA Tabs PresSteps VP AF ID PZ TemplateInstantiated BookScanBuilder".split()
)
STATIC_MARKUP = frozenset(
    "/" + s
    for s in "Stamp FreeText Line Square Circle Polygon PolyLine "
    "Ink Highlight Underline Squiggly StrikeOut".split()
)


def unsupported(feature: str) -> PreparationError:
    return PreparationError(
        "SOURCE_UNSUPPORTED",
        f"Unsupported source feature: {feature}",
        "Produce a static-page PDF separately for inspection; preparation "
        "never flattens or repairs unsupported input.",
        3,
        {"feature": feature},
    )


def get(obj: pikepdf.Object, key: str, default: object = None) -> object:
    return cast(object, obj.get(key, default))


def items(obj: pikepdf.Object) -> list[tuple[str, object]]:
    return sorted((str(k), cast(object, v)) for k, v in obj.items())


def array(obj: object) -> list[object]:
    if not isinstance(obj, pikepdf.Array):
        raise unsupported("expected PDF array")
    return list(cast(Iterable[object], obj))


def dictionary(obj: object, feature: str) -> pikepdf.Object:
    if not isinstance(obj, pikepdf.Dictionary):
        raise unsupported(feature + " must be a dictionary")
    return obj


def version(value: object) -> tuple[int, int]:
    text = str(value).removeprefix("/")
    match = re.fullmatch(r"([0-9]+)\.([0-9]+)", text)
    if match is None:
        raise unsupported("malformed PDF version")
    result = int(match[1]), int(match[2])
    if result < (1, 0) or result > (1, 7):
        raise unsupported("PDF version outside 1.0–1.7")
    return result


def document_info(pdf: pikepdf.Pdf) -> DocumentInfo:
    root = pdf.Root
    if get(root, "/Type") != pikepdf.Name.Catalog:
        raise unsupported("catalog /Type")
    tree = dictionary(get(root, "/Pages"), "catalog /Pages")
    if get(tree, "/Type") != pikepdf.Name.Pages:
        raise unsupported("catalog page tree")
    highest = version(pdf.pdf_version)
    level = 0
    for key, value in items(root):
        if key in {"/OCProperties", "/OutputIntents"} or (
            key == "/NeedsRendering" and value is True
        ):
            raise unsupported(key)
        if key == "/Version":
            if not isinstance(value, pikepdf.Name):
                raise unsupported("catalog /Version must be a name")
            highest = max(highest, version(value))
        if key == "/Extensions":
            extensions = dictionary(value, "/Extensions")
            for prefix, declaration in items(extensions):
                if prefix != "/ADBE":
                    raise unsupported("/Extensions " + prefix)
                decl = dictionary(declaration, prefix)
                if set(decl.keys()) != {"/BaseVersion", "/ExtensionLevel"}:
                    raise unsupported("ADBE extension entries")
                base = get(decl, "/BaseVersion")
                ext = get(decl, "/ExtensionLevel")
                if base != pikepdf.Name("/1.7") or type(ext) is not int or not 1 <= ext <= 3:
                    raise unsupported("ADBE base/level")
                level = ext
                highest = max(highest, (1, 7))
        if key == "/AcroForm":
            form = dictionary(value, "/AcroForm")
            if (
                array(get(form, "/Fields"))
                or "/XFA" in form
                or get(form, "/NeedAppearances") is True
            ):
                raise unsupported("/AcroForm fields/XFA/NeedAppearances")
    return DocumentInfo(highest, level)


def number(value: object, feature: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise unsupported(feature + " must be numeric")
    result = Decimal(str(value))
    if not result.is_finite():
        raise unsupported(feature + " must be finite")
    return result


def box(value: object, feature: str) -> tuple[Decimal, ...]:
    nums = tuple(number(v, feature) for v in array(value))
    if len(nums) != 4 or nums[2] <= nums[0] or nums[3] <= nums[1]:
        raise unsupported(feature + " requires four numbers and positive extent")
    return nums


def inherited(page: pikepdf.Object, key: str, default: object = None) -> object:
    node = page
    seen: set[tuple[int, int]] = set()
    while True:
        if key in node:
            return get(node, key)
        parent = get(node, "/Parent")
        if parent is None:
            return default
        node = dictionary(parent, "page parent")
        if node.objgen in seen:
            raise unsupported("cyclic page inheritance")
        seen.add(node.objgen)


def annotations(page: pikepdf.Object) -> tuple[bool, list[pikepdf.Object]]:
    if "/Annots" not in page:
        return False, []
    annots = array(get(page, "/Annots"))
    retained: list[pikepdf.Object] = []
    for value in annots:
        annot = dictionary(value, "annotation")
        if "/P" in annot:
            owner = dictionary(get(annot, "/P"), "annotation /P")
            if owner.objgen != page.objgen:
                raise unsupported("annotation refers to a different owning page")
        for key, _ in items(annot):
            if key in {"/AS", "/A", "/AA", "/OC", "/Popup", "/IRT", "/RT"}:
                raise unsupported("annotation " + key)
        subtype = get(annot, "/Subtype")
        if subtype == pikepdf.Name.Link:
            border = array(get(annot, "/Border"))
            if len(border) != 3 or any(number(v, "link Border") != 0 for v in border):
                raise unsupported("visible or default-border link")
            if "/AP" in annot:
                raise unsupported("link appearance")
            if "/BS" in annot:
                bs = dictionary(get(annot, "/BS"), "link /BS")
                if "/W" not in bs or number(get(bs, "/W"), "link /BS /W") != 0:
                    raise unsupported("visible or default link /BS")
            continue
        if str(subtype) not in STATIC_MARKUP:
            raise unsupported("annotation subtype " + str(subtype))
        ap = dictionary(get(annot, "/AP"), "annotation /AP")
        if set(ap.keys()) != {"/N"}:
            raise unsupported("annotation appearance states/R/D")
        normal = get(ap, "/N")
        if not isinstance(normal, pikepdf.Stream) or get(normal, "/Subtype") != pikepdf.Name.Form:
            raise unsupported("annotation /AP /N must be a single Form stream")
        dictionary(get(normal, "/Resources"), "appearance /Resources")
        box(get(normal, "/BBox"), "appearance /BBox")
        if "/Matrix" in normal:
            matrix = array(get(normal, "/Matrix"))
            if len(matrix) != 6:
                raise unsupported("appearance /Matrix requires six numbers")
            for v in matrix:
                number(v, "appearance /Matrix")
        retained.append(annot)
    return bool(annots), retained


def project_page(page: pikepdf.Object) -> Projection:
    if get(page, "/Type") != pikepdf.Name.Page:
        raise unsupported("page /Type")
    media_value = inherited(page, "/MediaBox")
    crop_value = inherited(page, "/CropBox")
    if crop_value is None:
        crop_value = media_value
    geometry_values: dict[str, object] = {
        "/MediaBox": media_value,
        "/CropBox": crop_value,
        "/BleedBox": get(page, "/BleedBox", crop_value),
        "/TrimBox": get(page, "/TrimBox", crop_value),
        "/ArtBox": get(page, "/ArtBox", crop_value),
        "/Rotate": inherited(page, "/Rotate", 0),
        "/UserUnit": get(page, "/UserUnit", 1),
    }
    validated_boxes: dict[str, tuple[Decimal, ...]] = {}
    resources: pikepdf.Object | None = None
    annotated = False
    retained_annots: list[pikepdf.Object] = []
    rotation = 0
    unit = Decimal(1)
    # Material gates follow the same sorted-key order as retained traversal.
    for key in sorted(set(page.keys()) | set(geometry_values) | {"/Resources"}):
        name = key.removeprefix("/")
        if name in {"SeparationInfo", "OutputIntents"} or (
            name in PAGE_STANDARD and name not in PAGE_RETAIN | PAGE_DISCARD
        ):
            raise unsupported("page " + key)
        if key == "/Annots":
            annotated, retained_annots = annotations(page)
        elif key in {"/ArtBox", "/BleedBox", "/CropBox", "/MediaBox", "/TrimBox"}:
            validated_boxes[key] = box(geometry_values[key], name)
        elif key in {"/Group", "/BoxColorInfo", "/Parent"}:
            dictionary(get(page, key), key)
        elif key == "/Contents":
            contents = get(page, key)
            if isinstance(contents, pikepdf.Array):
                streams = array(contents)
                if not streams or any(not isinstance(v, pikepdf.Stream) for v in streams):
                    raise unsupported("/Contents array requires streams")
            elif not isinstance(contents, pikepdf.Stream):
                raise unsupported("/Contents requires a stream or stream array")
        elif key == "/Resources":
            resources = dictionary(inherited(page, key), "effective /Resources")
        elif key == "/Rotate":
            value = geometry_values[key]
            if type(value) is not int or value % 90:
                raise unsupported("Rotate must be an integer multiple of 90")
            rotation = value
        elif key == "/UserUnit":
            unit = number(geometry_values[key], "UserUnit")
            if unit <= 0:
                raise unsupported("UserUnit must be positive")
    assert resources is not None
    boxes = tuple(
        validated_boxes["/" + key]
        for key in ("MediaBox", "CropBox", "BleedBox", "TrimBox", "ArtBox")
    )
    nodes: list[Node] = []
    seen: dict[tuple[int, int], int] = {}
    annotation_ids = {a.objgen for a in retained_annots if a.is_indirect}

    def visit(
        value: object,
        *,
        root: bool = False,
        annotation: bool = False,
        annotation_array: bool = False,
    ) -> Value:
        if value is None or isinstance(value, (bool, int, Decimal)):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                raise unsupported("non-finite retained number")
            return Decimal(str(value))
        if isinstance(value, pikepdf.Name):
            return str(value)
        if isinstance(value, pikepdf.String):
            return bytes(value)
        if not isinstance(value, (pikepdf.Dictionary, pikepdf.Stream, pikepdf.Array)):
            raise unsupported("unrepresentable retained PDF object")
        if value.is_indirect and value.objgen in seen:
            return Ref(seen[value.objgen])
        index = len(nodes)
        nodes.append(Node("pending"))
        if value.is_indirect:
            seen[value.objgen] = index
        if isinstance(value, pikepdf.Array):
            nodes[index] = Node(
                "array", items=tuple(visit(v, annotation=annotation_array) for v in array(value))
            )
            return Ref(index)
        if get(value, "/Type") == pikepdf.Name.Page and not root:
            if value.objgen != page.objgen:
                raise unsupported("reference to a different /Type /Page")
            return Ref(0)
        for key, _ in items(value):
            if (
                isinstance(value, pikepdf.Stream) and key in {"/F", "/FFilter", "/FDecodeParms"}
            ) or key in {"/Ref", "/OPI", "/OC"}:
                raise unsupported("retained graph " + key)
        entries: list[tuple[str, Value]] = []
        if root:
            projected = {k: v for k, v in items(value) if k.removeprefix("/") in PAGE_RETAIN}
            projected["/Resources"] = resources
            # Normalize all geometry defaults on both sides of a future comparison.
            for key, coords in zip(("MediaBox", "CropBox", "BleedBox", "TrimBox", "ArtBox"), boxes):
                projected["/" + key] = pikepdf.Array(coords)
            projected["/Rotate"] = rotation
            projected["/UserUnit"] = unit
            projected.pop("/Annots", None)
            if retained_annots:
                projected["/Annots"] = pikepdf.Array(retained_annots)
            pairs = sorted(projected.items())
        else:
            pairs = items(value)
        for key, child in pairs:
            if key == "/StructParent" or (
                key == "/P" and (annotation or value.objgen in annotation_ids)
            ):
                continue
            if isinstance(value, pikepdf.Stream) and key == "/Length":
                continue
            entries.append((key, visit(child, annotation_array=root and key == "/Annots")))
        # Read *encoded* streams, including masks/globals; no JBIG2 decoder is needed.
        # https://pikepdf.readthedocs.io/en/stable/api/main.html#pikepdf.Object.read_raw_bytes
        raw = value.read_raw_bytes() if isinstance(value, pikepdf.Stream) else None
        nodes[index] = Node("stream" if raw is not None else "dictionary", tuple(entries), raw=raw)
        return Ref(index)

    root = visit(page, root=True)
    assert isinstance(root, Ref)
    return Projection(
        Geometry(boxes, rotation, unit),
        root,
        tuple(nodes),
        annotated,
        tuple("/P" in a for a in retained_annots),
    )
