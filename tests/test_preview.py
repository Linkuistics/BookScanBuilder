import json
import subprocess
from pathlib import Path

import pikepdf
import pytest


def labels(path: Path, count: int = 6, prefix: str = "P") -> Path:
    with pikepdf.Pdf.new() as pdf:
        for n in range(1, count + 1):
            page = pdf.add_blank_page(page_size=(240, 320))
            page.obj["/Resources"] = pikepdf.Dictionary(
                Font=pikepdf.Dictionary(
                    F1=pdf.make_indirect(
                        pikepdf.Dictionary(
                            Type=pikepdf.Name.Font,
                            Subtype=pikepdf.Name.Type1,
                            BaseFont=pikepdf.Name.Helvetica,
                        )
                    )
                )
            )
            page.obj["/Contents"] = pdf.make_stream(  # pyright: ignore[reportUnknownMemberType]
                f"BT /F1 20 Tf 20 50 Td ({prefix}{n}) Tj ET\n".encode()
            )
        pdf.save(path)
    return path


def invoke(*args: str) -> subprocess.CompletedProcess[str]:
    folder = Path.cwd()
    if "--output" in args:
        index = args.index("--output") + 1
        if index < len(args) and Path(args[index]).parent.is_dir():
            folder = Path(args[index]).parent
    listing = sorted(p.name for p in folder.iterdir())
    result = subprocess.run(
        ["uv", "run", "--locked", "bookscan", "prepare", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if "--dry-run" in args:
        assert sorted(p.name for p in folder.iterdir()) == listing
    if result.returncode and args.count("--dry-run") == 1:
        write_args = tuple(a for a in args if a != "--dry-run")
        written = subprocess.run(
            ["uv", "run", "--locked", "bookscan", "prepare", *write_args],
            capture_output=True,
            text=True,
            check=False,
        )
        assert written.returncode == result.returncode, written.stderr + written.stdout
        if "--json" in args:
            assert json.loads(written.stdout) == json.loads(result.stdout)
    return result


@pytest.mark.parametrize(
    ("expression", "want"),
    [
        ("6-4,1,4,!5", [6, 4, 1, 4]),
        ("!2,!5-6", [1, 3, 4]),
        ("all", [1, 2, 3, 4, 5, 6]),
        ("2,2,1", [2, 2, 1]),
    ],
)
def test_preview_order_and_no_files(tmp_path: Path, expression: str, want: list[int]) -> None:
    source = labels(tmp_path / "Spaced input.pdf")
    before = sorted(tmp_path.iterdir())
    result = invoke(
        "--content",
        str(source),
        expression,
        "--output",
        str(tmp_path / "Prepared book.pdf"),
        "--dry-run",
        "--json",
    )
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout)
    assert record["status"] == "planned"
    assert [p["source_page"] for p in record["pages"]] == want
    assert [p["role"] for p in record["pages"]] == ["content"] * len(want)
    assert sorted(tmp_path.iterdir()) == before


def test_grouping_interleaved_and_selection_local_exclusion(tmp_path: Path) -> None:
    source = labels(tmp_path / "input.pdf")
    result = invoke(
        "--back",
        str(source),
        "4",
        "--content",
        str(source),
        "2",
        "--front",
        str(source),
        "1",
        "--content",
        str(source),
        "3,!1",
        "--content",
        str(source),
        "1",
        "--output",
        str(tmp_path / "out.pdf"),
        "--dry-run",
        "--json",
    )
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout)
    assert [p["source_page"] for p in record["pages"]] == [1, 2, 3, 1, 4]
    assert [p["role"] for p in record["pages"]] == [
        "front",
        "content",
        "content",
        "content",
        "back",
    ]


@pytest.mark.parametrize(
    ("args", "code"),
    [
        ([], "INVALID_ARGUMENT"),
        (["--output", "x"], "CONTENT_REQUIRED"),
        (["--content", "missing", "!all", "--output", "x", "--dry-run"], "INVALID_SELECTION"),
        (["--content", "missing", "--output", "x", "--dry-run"], "SOURCE_NOT_FOUND"),
        (["--content", "missing", "--output", "x", "--dry-run", "--dry-run"], "INVALID_ARGUMENT"),
        (["--content", "missing", "--output", "x", "--dry-run", "--wat"], "INVALID_ARGUMENT"),
        (["--content", "missing", "--output", "x"], "SOURCE_NOT_FOUND"),
    ],
)
def test_early_json_precedence(args: list[str], code: str) -> None:
    result = invoke(*args, "--json")
    assert result.returncode in (2, 3)
    record = json.loads(result.stdout)
    assert record["code"] == code
    assert record["remediation"]
    assert record["warnings"] == []


def test_help_precedence_and_contract() -> None:
    result = invoke("--unknown", "--json", "--content", "missing", "--help")
    assert result.returncode == 0
    for phrase in [
        "front",
        "content",
        "back",
        "descending",
        "single-quote",
        "no overwrite",
        "hash",
        "reservation",
        "permission",
        "retry",
        "--dry-run",
    ]:
        assert phrase in result.stdout.lower()


@pytest.mark.parametrize(
    "expression",
    ["", ",1", "1,", "0", "-1", "1.5", "1-", "-2", "!all", "1 2", "all, all", "1--2", "!0"],
)
def test_malformed_before_source(expression: str, tmp_path: Path) -> None:
    result = invoke(
        "--content",
        str(tmp_path / "missing"),
        expression,
        "--output",
        str(tmp_path / "out.pdf"),
        "--dry-run",
        "--json",
    )
    # A value starting with '-' is an option/arity error, still before any source access.
    record = json.loads(result.stdout)
    assert record["code"] in ("INVALID_SELECTION", "INVALID_ARGUMENT")
    assert result.returncode == 2
    if record["code"] == "INVALID_SELECTION":
        assert record["page_count"] is None
        assert record["selection"] == expression


@pytest.mark.parametrize(
    ("expression", "code"),
    [
        ("7", "PAGE_OUT_OF_RANGE"),
        ("!7", "PAGE_OUT_OF_RANGE"),
        ("1-7", "PAGE_OUT_OF_RANGE"),
        ("all,!1-6", "EMPTY_SELECTION"),
    ],
)
def test_resolution_errors(tmp_path: Path, expression: str, code: str) -> None:
    source = labels(tmp_path / "in.pdf")
    result = invoke(
        "--content",
        str(source),
        expression,
        "--output",
        str(tmp_path / "out.pdf"),
        "--dry-run",
        "--json",
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["code"] == code


def check_gate(path: Path, want: str = "SOURCE_UNSUPPORTED", expression: str = "all") -> None:
    before = path.read_bytes()
    listing = sorted(path.parent.iterdir())
    result = invoke(
        "--content",
        str(path),
        expression,
        "--output",
        str(path.parent / "out.pdf"),
        "--dry-run",
        "--json",
    )
    assert result.returncode == (0 if want == "planned" else 3), result.stderr + result.stdout
    record = json.loads(result.stdout)
    assert (record["status"] if want == "planned" else record["code"]) == want
    assert sorted(path.parent.iterdir()) == listing
    if want == "planned":
        written = invoke(
            "--content", str(path), expression, "--output", str(path.parent / "out.pdf"), "--json"
        )
        assert written.returncode == 0, written.stdout + written.stderr
        assert json.loads(written.stdout)["status"] == "written"
        (path.parent / "out.pdf").unlink()
        assert sorted(path.parent.iterdir()) == listing
    assert path.read_bytes() == before


@pytest.mark.parametrize("key", ["/OCProperties", "/OutputIntents", "/NeedsRendering"])
def test_catalog_gates(tmp_path: Path, key: str) -> None:
    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page()
        pdf.Root[key] = True if key == "/NeedsRendering" else pikepdf.Dictionary()
        pdf.save(path)
    check_gate(path)


@pytest.mark.parametrize("key", ["/SeparationInfo", "/OutputIntents"])
def test_standard_page_rejection(tmp_path: Path, key: str) -> None:
    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page().obj[key] = pikepdf.Dictionary()
        pdf.save(path)
    check_gate(path)


@pytest.mark.parametrize("key", ["/F", "/FFilter", "/FDecodeParms", "/Ref", "/OPI", "/OC"])
def test_nested_resource_gates(tmp_path: Path, key: str) -> None:
    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page()
        inner = pdf.make_stream(b"nested data")  # pyright: ignore[reportUnknownMemberType]
        inner[key] = pikepdf.String("external")
        form = pdf.make_stream(b"")  # pyright: ignore[reportUnknownMemberType]
        form["/Resources"] = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=inner))
        page.obj["/Resources"] = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Fm=form))
        pdf.save(path)
    check_gate(path)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("/MediaBox", [0, 0, 0, 3]),
        ("/CropBox", [0, 0, 3]),
        ("/BleedBox", [2, 2, 1, 1]),
        ("/TrimBox", [0, 0, 3]),
        ("/ArtBox", [0, 0, 1, 0]),
        ("/Rotate", 45),
        ("/UserUnit", 0),
        ("/UserUnit", -1),
    ],
)
def test_geometry_gates(tmp_path: Path, key: str, value: list[int] | int) -> None:
    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page()
        page.obj[key] = pikepdf.Array(value) if isinstance(value, list) else value
        pdf.save(path)
    check_gate(path)


@pytest.mark.parametrize("mode", ["empty", "fields-missing", "fields-wrong", "xfa", "appearance"])
def test_form_gates(tmp_path: Path, mode: str) -> None:
    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page()
        form = pikepdf.Dictionary(Fields=pikepdf.Array())
        if mode == "fields-missing":
            del form["/Fields"]
        if mode == "fields-wrong":
            form["/Fields"] = pikepdf.Dictionary()
        if mode == "xfa":
            form["/XFA"] = pikepdf.String("x")
        if mode == "appearance":
            form["/NeedAppearances"] = True
        pdf.Root["/AcroForm"] = form
        pdf.save(path)
    check_gate(path, "planned" if mode == "empty" else "SOURCE_UNSUPPORTED")


@pytest.mark.parametrize(
    "mode",
    [
        "static",
        "state",
        "rollover",
        "widget",
        "link-zero",
        "link-default",
        "link-border",
        "action",
        "repeat",
    ],
)
def test_annotation_gates(tmp_path: Path, mode: str) -> None:
    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page()
        normal = pdf.make_stream(b"0 0 10 10 re S")  # pyright: ignore[reportUnknownMemberType]
        normal["/Type"] = pikepdf.Name.XObject
        normal["/Subtype"] = pikepdf.Name.Form
        normal["/BBox"] = pikepdf.Array([0, 0, 10, 10])
        normal["/Resources"] = pikepdf.Dictionary()
        annot = pikepdf.Dictionary(
            Subtype=pikepdf.Name.Stamp,
            Rect=pikepdf.Array([0, 0, 10, 10]),
            AP=pikepdf.Dictionary(N=normal),
            P=page.obj,
        )
        if mode.startswith("link"):
            annot["/Subtype"] = pikepdf.Name.Link
            del annot["/AP"]
            if mode != "link-default":
                annot["/Border"] = pikepdf.Array([0, 0, 0 if mode == "link-zero" else 1])
        if mode == "widget":
            annot["/Subtype"] = pikepdf.Name.Widget
        if mode == "state":
            annot["/AP"]["/N"] = pikepdf.Dictionary(Yes=normal)
        if mode == "rollover":
            annot["/AP"]["/R"] = normal
        if mode == "action":
            annot["/A"] = pikepdf.Dictionary(S=pikepdf.Name.JavaScript)
        page.obj["/Annots"] = pikepdf.Array([pdf.make_indirect(annot)])
        if mode == "widget":
            with pytest.warns(pikepdf.PageCopyWarning):
                pdf.save(path)
        else:
            pdf.save(path)
    check_gate(
        path,
        "planned" if mode in ("static", "link-zero") else "SOURCE_UNSUPPORTED",
        "1,1" if mode == "repeat" else "all",
    )


def test_discarded_keys_do_not_gate(tmp_path: Path) -> None:
    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page()
        page.obj["/BookScanBuilder"] = pikepdf.Dictionary(OC=True)
        page.obj["/PrivateVendor"] = pikepdf.Dictionary(F=pikepdf.String("external"))
        pdf.Root["/OpenAction"] = pikepdf.Dictionary(S=pikepdf.Name.JavaScript)
        pdf.save(path)
    check_gate(path, "planned")


@pytest.mark.parametrize("alias", ["same", "symlink", "hardlink", "case"])
def test_source_alias_before_occupation(tmp_path: Path, alias: str) -> None:
    source = labels(tmp_path / "Input.pdf")
    out = tmp_path / "alias.pdf"
    if alias == "same":
        out = source
    elif alias == "symlink":
        out.symlink_to(source)
    elif alias == "hardlink":
        import os

        os.link(source, out)
    else:
        out = tmp_path / "input.pdf"
        if not out.exists():
            pytest.skip("Case-sensitive filesystem")
    result = invoke("--content", str(source), "--output", str(out), "--dry-run", "--json")
    assert result.returncode == 4
    assert json.loads(result.stdout)["code"] == "SOURCE_OUTPUT_COLLISION"


@pytest.mark.parametrize("occupant", ["file", "directory", "dangling"])
def test_occupied_destination_unchanged(tmp_path: Path, occupant: str) -> None:
    source = labels(tmp_path / "in.pdf")
    out = tmp_path / "out.pdf"
    if occupant == "file":
        out.write_bytes(b"sentinel")
    elif occupant == "directory":
        out.mkdir()
    else:
        out.symlink_to(tmp_path / "missing")
    before = sorted(tmp_path.iterdir())
    result = invoke("--content", str(source), "--output", str(out), "--dry-run", "--json")
    assert result.returncode == 4
    assert json.loads(result.stdout)["code"] == "OUTPUT_EXISTS"
    assert sorted(tmp_path.iterdir()) == before
    if occupant == "file":
        assert out.read_bytes() == b"sentinel"
    if occupant == "dangling":
        assert out.is_symlink()


def test_source_before_output_and_parent(tmp_path: Path) -> None:
    out = tmp_path / "occupied"
    out.write_bytes(b"sentinel")
    result = invoke(
        "--content", str(tmp_path / "missing"), "--output", str(out), "--dry-run", "--json"
    )
    assert json.loads(result.stdout)["code"] == "SOURCE_NOT_FOUND"
    source = labels(tmp_path / "in.pdf")
    result = invoke(
        "--content", str(source), "--output", str(out / "nested.pdf"), "--dry-run", "--json"
    )
    assert result.returncode == 4
    assert json.loads(result.stdout)["code"] == "OUTPUT_DIRECTORY_INVALID"


@pytest.mark.parametrize("mode", ["empty", "encrypted", "malformed"])
def test_source_input_gates(tmp_path: Path, mode: str) -> None:
    path = tmp_path / "in.pdf"
    if mode == "malformed":
        path.write_bytes(b"not a PDF")
    else:
        with pikepdf.Pdf.new() as pdf:
            if mode != "empty":
                pdf.add_blank_page()
            pdf.save(
                path,
                encryption=pikepdf.Encryption(owner="owner", user="")
                if mode == "encrypted"
                else False,
            )
    check_gate(path, "SOURCE_EMPTY" if mode == "empty" else "SOURCE_UNSUPPORTED")


@pytest.mark.parametrize(
    "mode", ["2.0", "catalog-bad", "prefix", "array", "base", "level", "extra"]
)
def test_versions_and_extensions(tmp_path: Path, mode: str) -> None:
    path = tmp_path / "in.pdf"
    from pdf_fixtures import raw_pdf

    decl = b"<< /BaseVersion /1.7 /ExtensionLevel 3 >>"
    if mode == "base":
        decl = decl.replace(b"/1.7", b"/1.6")
    if mode == "level":
        decl = decl.replace(b"Level 3", b"Level 4")
    if mode == "extra":
        decl = decl[:-2] + b"/Private true >>"
    if mode == "array":
        decl = b"[" + decl + b"]"
    catalog = (
        b"/Extensions << " + (b"/OTHER" if mode == "prefix" else b"/ADBE") + b" " + decl + b" >>"
    )
    if mode == "catalog-bad":
        catalog = b"/Version (1.7)"
    if mode == "2.0":
        catalog = b"/Version /2.0"
    raw_pdf(path, catalog=catalog)
    with pikepdf.Pdf.open(path) as observed:
        assert not observed.get_warnings()  # pyright: ignore[reportUnknownMemberType]
        if mode not in ("2.0", "catalog-bad"):
            assert "/Extensions" in observed.Root
    check_gate(path)


def test_projection_inherited_geometry_cycle_and_nested_globals(tmp_path: Path) -> None:
    from decimal import Decimal

    from bookscan.prepare import plan
    from bookscan.selections import parse

    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(240, 320))
        parent = page.obj["/Parent"]
        parent["/MediaBox"] = page.obj["/MediaBox"]
        del page.obj["/MediaBox"]
        parent["/CropBox"] = pikepdf.Array([10, 10, 230, 310])
        parent["/Rotate"] = 90
        page.obj["/UserUnit"] = 1.25
        page.obj["/TrimBox"] = pikepdf.Array([20, 20, 220, 300])
        globals_stream = pdf.make_stream(b"global bytes")  # pyright: ignore[reportUnknownMemberType]
        image = pdf.make_stream(b"image bytes")  # pyright: ignore[reportUnknownMemberType]
        image["/DecodeParms"] = pikepdf.Dictionary(JBIG2Globals=globals_stream)
        form = pdf.make_stream(b"form bytes")  # pyright: ignore[reportUnknownMemberType]
        resource = pdf.make_indirect(pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=image)))
        resource["/Cycle"] = resource
        form["/Resources"] = resource
        parent["/Resources"] = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Fm=form))
        del page.obj["/Resources"]
        pdf.Root["/Version"] = pikepdf.Name("/1.7")
        pdf.save(path, compress_streams=False)
    before = path.read_bytes()
    result = plan(
        parse(["--content", str(path), "--output", str(tmp_path / "out.pdf"), "--dry-run"])
    )
    projection = result.projections[0]
    assert projection.geometry.boxes == (
        (0, 0, 240, 320),
        (10, 10, 230, 310),
        (10, 10, 230, 310),
        (20, 20, 220, 300),
        (10, 10, 230, 310),
    )
    assert projection.geometry.rotate == 90
    assert projection.geometry.user_unit == Decimal("1.25")
    assert {node.raw for node in projection.nodes if node.raw is not None} >= {
        b"global bytes",
        b"image bytes",
        b"form bytes",
    }
    assert result.version == (1, 7)
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("/Contents", pikepdf.Dictionary()),
        ("/Contents", pikepdf.Array([pikepdf.Dictionary()])),
        ("/Group", pikepdf.Array()),
        ("/BoxColorInfo", pikepdf.String("bad")),
    ],
)
def test_invalid_retained_page_types(tmp_path: Path, key: str, value: pikepdf.Object) -> None:
    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page().obj[key] = value
        pdf.save(path)
    check_gate(path)


def test_source_annotation_owner_must_match(tmp_path: Path) -> None:
    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page()
        other = pdf.add_blank_page()
        normal = pdf.make_stream(b"")  # pyright: ignore[reportUnknownMemberType]
        normal["/Subtype"] = pikepdf.Name.Form
        normal["/BBox"] = pikepdf.Array([0, 0, 10, 10])
        normal["/Resources"] = pikepdf.Dictionary()
        page.obj["/Annots"] = pikepdf.Array(
            [
                pdf.make_indirect(
                    pikepdf.Dictionary(
                        Subtype=pikepdf.Name.Stamp,
                        P=other.obj,
                        Rect=pikepdf.Array([0, 0, 10, 10]),
                        AP=pikepdf.Dictionary(N=normal),
                    )
                )
            ]
        )
        pdf.save(path)
    check_gate(path, expression="1")


def test_page_gate_first_error_uses_sorted_keys(tmp_path: Path) -> None:
    path = tmp_path / "in.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page()
        page.obj["/MediaBox"] = pikepdf.Array([0, 0, 0, 1])
        page.obj["/SeparationInfo"] = pikepdf.Dictionary()
        page.obj["/Annots"] = pikepdf.Array(
            [pdf.make_indirect(pikepdf.Dictionary(Subtype=pikepdf.Name.Widget))]
        )
        with pytest.warns(pikepdf.PageCopyWarning):
            pdf.save(path)
    result = invoke(
        "--content", str(path), "--output", str(tmp_path / "out.pdf"), "--dry-run", "--json"
    )
    assert result.returncode == 3
    assert json.loads(result.stdout)["feature"] == "annotation subtype /Widget"


def test_actual_task_forwarding(tmp_path: Path) -> None:
    source = labels(tmp_path / "Generated path with spaces.pdf")
    args = [
        "--content",
        str(source),
        "all,!3",
        "--output",
        str(tmp_path / "Spaced destination.pdf"),
        "--dry-run",
        "--json",
    ]
    direct = invoke(*args)
    recipe = subprocess.run(
        ["task", "prepare:run", "--", *args], capture_output=True, text=True, check=False
    )
    assert direct.returncode == recipe.returncode == 0, recipe.stderr
    assert json.loads(direct.stdout) == json.loads(recipe.stdout)


def test_repeated_invisible_links_rejected(tmp_path: Path) -> None:
    path = tmp_path / "link.pdf"
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page()
        page.obj["/Annots"] = pikepdf.Array(
            [
                pdf.make_indirect(
                    pikepdf.Dictionary(Subtype=pikepdf.Name.Link, Border=pikepdf.Array([0, 0, 0]))
                )
            ]
        )
        pdf.save(path)
    check_gate(path, expression="1,1")


def test_selection_order_source_opening_and_bounds(tmp_path: Path) -> None:
    good = labels(tmp_path / "good.pdf")
    missing = tmp_path / "missing.pdf"
    # Source opening is command order, independently of front/content/back grouping.
    result = invoke(
        "--back",
        str(missing),
        "--content",
        str(good),
        "7",
        "--output",
        str(tmp_path / "out.pdf"),
        "--dry-run",
        "--json",
    )
    assert json.loads(result.stdout)["code"] == "SOURCE_NOT_FOUND"
    result = invoke(
        "--back",
        str(good),
        "7",
        "--content",
        str(good),
        "8",
        "--output",
        str(tmp_path / "out.pdf"),
        "--dry-run",
        "--json",
    )
    assert json.loads(result.stdout)["token"] == "7"


def test_malformed_source_error_context(tmp_path: Path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"not PDF syntax")
    result = invoke(
        "--content", str(path), "--output", str(tmp_path / "out.pdf"), "--dry-run", "--json"
    )
    assert result.returncode == 3
    assert json.loads(result.stdout)["source"] == str(path)


def test_long_integer_is_bounded_after_source_open(tmp_path: Path) -> None:
    path = labels(tmp_path / "in.pdf")
    result = invoke(
        "--content",
        str(path),
        "9" * 5000,
        "--output",
        str(tmp_path / "out.pdf"),
        "--dry-run",
        "--json",
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["code"] == "PAGE_OUT_OF_RANGE"
