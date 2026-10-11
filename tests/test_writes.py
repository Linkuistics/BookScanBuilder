"""Public write contracts, independently labelled order and unchanged sources."""

import hashlib
import json
import subprocess
from pathlib import Path

import pikepdf
import pytest
from test_preview import labels


def invoke(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "--locked", "bookscan", "prepare", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "expression,want",
    [
        ("6-4,1,4,!5", [6, 4, 1, 4]),
        ("!2,!5-6", [1, 3, 4]),
        ("all", [1, 2, 3, 4, 5, 6]),
    ],
)
def test_public_write_order_and_retry(tmp_path: Path, expression: str, want: list[int]) -> None:
    source = labels(tmp_path / "Spaced source.pdf")
    output = tmp_path / "Prepared book.pdf"
    before = digest(source)
    args = ["--content", str(source), expression, "--output", str(output), "--json"]
    preview = invoke(*args, "--dry-run")
    assert preview.returncode == 0, preview.stderr
    result = invoke(*args)
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout) == {
        "schema_version": 1,
        "status": "written",
        "output": str(output),
        "page_count": len(want),
        "warnings": [],
    }
    assert [p["source_page"] for p in json.loads(preview.stdout)["pages"]] == want
    with pikepdf.Pdf.open(output, attempt_recovery=False) as pdf:
        assert len(pdf.pages) == len(want)
        for page, number in zip(pdf.pages, want, strict=True):
            assert f"(P{number})".encode() in page.obj["/Contents"].read_bytes()
            marker = page.obj["/BookScanBuilder"]
            assert str(marker["/Role"]) == "content"
            assert marker["/SourcePage"] == number
            assert str(marker["/SourceSHA256"]) == before
            assert marker["/Version"] == 1
    after = digest(output)
    retry = invoke(*args)
    assert retry.returncode == 4
    assert json.loads(retry.stdout)["code"] == "OUTPUT_EXISTS"
    assert digest(output) == after and digest(source) == before
    assert sorted(p.name for p in tmp_path.iterdir()) == [output.name, source.name]


def test_public_interleaved_roles_and_repeated_marker(tmp_path: Path) -> None:
    covers = labels(tmp_path / "covers.pdf", 4, "K")
    content = labels(tmp_path / "content.pdf", 2, "C")
    output = tmp_path / "out.pdf"
    args = [
        "--back",
        str(covers),
        "1",
        "--content",
        str(content),
        "2",
        "--front",
        str(covers),
        "1",
        "--content",
        str(covers),
        "3",
        "--content",
        str(content),
        "1",
        "--output",
        str(output),
        "--json",
    ]
    before = [digest(covers), digest(content)]
    result = invoke(*args)
    assert result.returncode == 0, result.stderr + result.stdout
    with pikepdf.Pdf.open(output) as pdf:
        assert [str(p.obj["/BookScanBuilder"]["/Role"]) for p in pdf.pages] == [
            "front",
            "content",
            "content",
            "content",
            "back",
        ]
        assert [p.obj["/Contents"].read_bytes() for p in pdf.pages] == [
            b"BT /F1 20 Tf 20 50 Td (K1) Tj ET\n",
            b"BT /F1 20 Tf 20 50 Td (C2) Tj ET\n",
            b"BT /F1 20 Tf 20 50 Td (K3) Tj ET\n",
            b"BT /F1 20 Tf 20 50 Td (C1) Tj ET\n",
            b"BT /F1 20 Tf 20 50 Td (K1) Tj ET\n",
        ]
        assert pdf.pages[0].obj.objgen != pdf.pages[-1].obj.objgen
        first, last = (pdf.pages[n].obj["/BookScanBuilder"] for n in (0, -1))
        assert first.objgen != last.objgen
        last["/Role"] = pikepdf.String("content")
        assert str(first["/Role"]) == "front"
    assert [digest(covers), digest(content)] == before


def test_actual_run_recipe_forwarding(tmp_path: Path) -> None:
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


@pytest.mark.parametrize("minor", range(8))
def test_accepted_numeric_source_versions(tmp_path: Path, minor: int) -> None:
    from pdf_fixtures import raw_pdf

    source = raw_pdf(tmp_path / "source.pdf")
    source.write_bytes(source.read_bytes().replace(b"%PDF-1.7", f"%PDF-1.{minor}".encode(), 1))
    output = tmp_path / "out.pdf"
    result = invoke("--content", str(source), "--output", str(output), "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    with pikepdf.Pdf.open(output) as pdf:
        assert tuple(map(int, pdf.pdf_version.split("."))) >= (1, minor)
