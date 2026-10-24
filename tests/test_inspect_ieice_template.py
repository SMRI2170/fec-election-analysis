"""Unit tests for the IEICE template inspector (Issue #83).

The official template is confidential and is never committed, so these tests
build a **synthetic minimal DOCX** in memory and check the inspection logic
against it. The real inspection is reproduced by running the script against
the privately held original.
"""
from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for extra in (str(ROOT / "scripts"), str(ROOT / "src")):
    if extra not in sys.path:
        sys.path.insert(0, extra)


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inspector = _load_script("inspect_ieice_template")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

DOCUMENT_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="a6"/></w:pPr><w:r><w:t>題名</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="af5"/></w:pPr><w:r><w:t>あらまし　本文</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="af7"/></w:pPr><w:r><w:t>キーワード　キーワード1，キーワード2</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="a5"/></w:pPr><w:r><w:t>本文段落</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="aff"/></w:pPr><w:r><w:t>2.2　英文アブストラクト，英文キーワード</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="af9"/></w:pPr><w:r><w:t>文　　　献</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="aff2"/></w:pPr><w:r><w:t>付　　録</w:t></w:r></w:p>
    <w:sectPr>
      <w:pgSz w:w="10318" w:h="14570"/>
      <w:pgMar w:top="1418" w:bottom="1418" w:left="821" w:right="821"/>
      <w:cols w:num="2" w:space="425"/>
    </w:sectPr>
  </w:body>
</w:document>
"""

STYLES_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault><w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:eastAsia="ＭＳ 明朝"/>
      <w:sz w:val="17"/>
    </w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr><w:spacing w:line="300" w:lineRule="exact"/></w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:styleId="a5">
    <w:name w:val="共通_本文"/><w:basedOn w:val="a"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="af8">
    <w:name w:val="共通_節見出し"/><w:basedOn w:val="a"/>
    <w:pPr><w:outlineLvl w:val="0"/></w:pPr>
  </w:style>
</w:styles>
"""


@pytest.fixture()
def synthetic_docx(tmp_path) -> Path:
    path = tmp_path / "synthetic.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", DOCUMENT_XML)
        archive.writestr("word/styles.xml", STYLES_XML)
        archive.writestr("word/footer1.xml", f"<w:ftr xmlns:w='{W[1:-1]}'><w:p><w:r><w:t>1</w:t></w:r></w:p></w:ftr>")
    return path


def test_twips_conversion():
    assert inspector.twips_to_mm(1440) == pytest.approx(25.4)
    assert inspector.twips_to_mm(0) == 0.0


def test_sections_are_reported(synthetic_docx):
    report = inspector.inspect(synthetic_docx)
    assert len(report["sections"]) == 1
    section = report["sections"][0]
    assert section["columns"] == 2
    assert section["margin_top_mm"] == pytest.approx(25.01)
    # 821 twips is the value Word stores for 14.5 mm.
    assert section["margin_left_mm"] == pytest.approx(14.48)
    assert section["page_width_mm"] == pytest.approx(182.0)


def test_defaults_are_reported(synthetic_docx):
    report = inspector.inspect(synthetic_docx)
    assert report["defaults"]["default_ascii_font"] == "Times New Roman"
    assert report["defaults"]["default_size_pt"] == pytest.approx(8.5)


def test_styles_and_outline_levels_are_reported(synthetic_docx):
    report = inspector.inspect(synthetic_docx)
    by_id = {style["style_id"]: style for style in report["styles"]}
    assert by_id["a5"]["name"] == "共通_本文"
    assert by_id["af8"]["outline_level"] == 0
    assert by_id["a5"]["outline_level"] is None


def test_markers_are_found(synthetic_docx):
    report = inspector.inspect(synthetic_docx)
    markers = report["markers"]
    assert markers["abstract_ja"]["present"] is True
    # The abstract sits in a body paragraph, not in a heading style.
    assert markers["abstract_ja"]["present_in_a_heading"] is False
    assert markers["references"]["present_in_a_heading"] is True
    assert markers["appendix"]["present_in_a_heading"] is True
    assert markers["keywords_en"]["present"] is False


def test_headings_are_collected_with_their_styles(synthetic_docx):
    report = inspector.inspect(synthetic_docx)
    headings = {(item["style"], item["text"]) for item in report["headings"]}
    assert ("af9", "文　　　献") in headings
    assert ("aff2", "付　　録") in headings
    assert ("aff", "2.2　英文アブストラクト，英文キーワード") in headings
    # A body paragraph is not a heading.
    assert not any(item["text"] == "本文段落" for item in report["headings"])


def test_body_outline_keeps_the_style_and_text(synthetic_docx):
    report = inspector.inspect(synthetic_docx)
    outline = report["body_outline"]
    first = outline[0]
    assert first["style"] == "a6"
    assert first["text"] == "題名"


def test_headers_and_footers_are_listed(synthetic_docx):
    report = inspector.inspect(synthetic_docx)
    parts = {item["part"]: item for item in report["headers_footers"]}
    assert "word/footer1.xml" in parts
    assert parts["word/footer1.xml"]["kind"] == "footer"
    assert parts["word/footer1.xml"]["non_empty_paragraphs"] == ["1"]


def test_sha256_is_recorded(synthetic_docx):
    report = inspector.inspect(synthetic_docx)
    assert len(report["sha256"]) == 64
    assert report["bytes"] == synthetic_docx.stat().st_size


def test_missing_template_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError):
        inspector.inspect(tmp_path / "absent.docx")
