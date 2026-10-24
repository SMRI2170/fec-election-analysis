"""Inspect the official IEICE Word template without modifying it.

The template is the authoritative format for the assignment manuscript
(Issue #83). This script reads the DOCX package with the standard library
only and reports the structure that a manuscript must follow:

* page setup: paper size, margins and the number of columns per section,
* headers and footers, and which section each one belongs to,
* the paragraph styles defined by the template, with their outline levels so
  the heading hierarchy is explicit,
* the default fonts and the body text size,
* the field blocks the template provides for the title, authors, abstract and
  keywords,
* where the body ends and the appendix begins.

Nothing is written back into the template. The DOCX itself is confidential
and must not be committed; only this report is.

Usage
-----
    python scripts/inspect_ieice_template.py path/to/cs_papertemplete.docx
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

#: Word's unit: 1 twentieth of a point.
EMU_PER_TWIP = 635


def twips_to_mm(value: int) -> float:
    return round(value / 1440.0 * 25.4, 2)


def read_part(archive: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        payload = archive.read(name)
    except KeyError:
        return None
    return ET.fromstring(payload)


def paragraph_text(node: ET.Element) -> str:
    return "".join(t.text or "" for t in node.iter(f"{W}t"))


def style_of(paragraph: ET.Element) -> str:
    properties = paragraph.find(f"{W}pPr")
    if properties is None:
        return ""
    style = properties.find(f"{W}pStyle")
    if style is None:
        return ""
    return style.get(f"{W}val", "")


def describe_sections(archive: zipfile.ZipFile) -> list[dict]:
    """Report the page setup of every section in the document body."""
    document = read_part(archive, "word/document.xml")
    if document is None:
        return []
    body = document.find(f"{W}body")
    sections: list[dict] = []
    for index, sect in enumerate(body.iter(f"{W}sectPr"), start=1):
        page_size = sect.find(f"{W}pgSz")
        margins = sect.find(f"{W}pgMar")
        columns = sect.find(f"{W}cols")
        info: dict = {"section_index": index}
        if page_size is not None:
            info["page_width_mm"] = twips_to_mm(int(page_size.get(f"{W}w", "0")))
            info["page_height_mm"] = twips_to_mm(int(page_size.get(f"{W}h", "0")))
            info["orientation"] = page_size.get(f"{W}orient", "portrait")
        if margins is not None:
            for name in ("top", "bottom", "left", "right", "header", "footer", "gutter"):
                key = f"{W}{name}"
                if key in margins.attrib:
                    info[f"margin_{name}_mm"] = twips_to_mm(int(margins.get(key, "0")))
        if columns is not None:
            info["columns"] = int(columns.get(f"{W}num", "1"))
            info["column_space_mm"] = twips_to_mm(int(columns.get(f"{W}space", "0")))
            info["has_column_separator"] = columns.get(f"{W}sep", "0") not in ("0", "false")
        for kind in ("headerReference", "footerReference"):
            references = []
            for reference in sect.findall(f"{W}{kind}"):
                references.append(
                    {
                        "type": reference.get(f"{W}type"),
                        "relationship_id": reference.get(f"{R}id"),
                    }
                )
            if references:
                info[kind] = references
        info["title_page"] = sect.find(f"{W}titlePg") is not None
        sections.append(info)
    return sections


def describe_styles(archive: zipfile.ZipFile) -> list[dict]:
    """Report every paragraph style with its outline level and base style."""
    styles = read_part(archive, "word/styles.xml")
    if styles is None:
        return []
    result: list[dict] = []
    for style in styles.findall(f"{W}style"):
        if style.get(f"{W}type") != "paragraph":
            continue
        name = style.find(f"{W}name")
        properties = style.find(f"{W}pPr")
        outline = None
        based_on = None
        if properties is not None:
            outline_node = properties.find(f"{W}outlineLvl")
            if outline_node is not None:
                outline = int(outline_node.get(f"{W}val", "9"))
        based = style.find(f"{W}basedOn")
        if based is not None:
            based_on = based.get(f"{W}val")
        result.append(
            {
                "style_id": style.get(f"{W}styleId"),
                "name": name.get(f"{W}val") if name is not None else None,
                "based_on": based_on,
                "outline_level": outline,
            }
        )
    return result


def describe_defaults(archive: zipfile.ZipFile) -> dict:
    """Report the document default font and size."""
    styles = read_part(archive, "word/styles.xml")
    defaults: dict = {}
    if styles is None:
        return defaults
    doc_defaults = styles.find(f"{W}docDefaults")
    if doc_defaults is None:
        return defaults
    run_defaults = doc_defaults.find(f"{W}rPrDefault")
    if run_defaults is not None:
        run = run_defaults.find(f"{W}rPr")
        if run is not None:
            fonts = run.find(f"{W}rFonts")
            if fonts is not None:
                defaults["default_ascii_font"] = fonts.get(f"{W}ascii")
                defaults["default_east_asian_font"] = fonts.get(f"{W}eastAsia")
            size = run.find(f"{W}sz")
            if size is not None:
                defaults["default_size_pt"] = int(size.get(f"{W}val", "0")) / 2
    paragraph_defaults = doc_defaults.find(f"{W}pPrDefault")
    if paragraph_defaults is not None:
        paragraph = paragraph_defaults.find(f"{W}pPr")
        if paragraph is not None:
            line = paragraph.find(f"{W}spacing")
            if line is not None:
                if f"{W}line" in line.attrib:
                    defaults["default_line_twips"] = int(line.get(f"{W}line"))
                if f"{W}lineRule" in line.attrib:
                    defaults["default_line_rule"] = line.get(f"{W}lineRule")
    return defaults


def describe_headers_footers(archive: zipfile.ZipFile) -> list[dict]:
    """Report the text content of every header and footer part."""
    result: list[dict] = []
    for name in sorted(archive.namelist()):
        if not re.fullmatch(r"word/(header|footer)\d+\.xml", name):
            continue
        root = read_part(archive, name)
        if root is None:
            continue
        texts = [paragraph_text(p).strip() for p in root.iter(f"{W}p")]
        result.append(
            {
                "part": name,
                "kind": "header" if "header" in name else "footer",
                "non_empty_paragraphs": [t for t in texts if t],
                "paragraph_count": len(texts),
            }
        )
    return result


def describe_body_outline(archive: zipfile.ZipFile, limit: int = 120) -> list[dict]:
    """Report the first paragraphs with their style, to locate the fields."""
    document = read_part(archive, "word/document.xml")
    if document is None:
        return []
    body = document.find(f"{W}body")
    outline: list[dict] = []
    index = 0
    for paragraph in body.iter(f"{W}p"):
        index += 1
        text = paragraph_text(paragraph).strip()
        style = style_of(paragraph)
        if not text and not style:
            continue
        outline.append({"index": index, "style": style, "text": text[:110]})
        if len(outline) >= limit:
            break
    return outline


#: Paragraph styles that act as headings in the IEICE template.
HEADING_STYLES = (
    "af8",  # 共通_節見出し
    "aff",  # 共通_項見出し
    "aff0",  # 共通_綱見出し
    "af9",  # 共通_文献見出し
    "aff2",  # 共通_付録見出し
    "afd",  # 共通_終わり
)


def describe_headings(archive: zipfile.ZipFile) -> list[dict]:
    """List every heading paragraph with its style id and text.

    Searching the whole document text for a marker such as "付録" would also
    match the explanatory sentence that lists the required sections. Headings
    are therefore collected from the heading styles only, so a match is
    evidence that the heading itself exists.
    """
    document = read_part(archive, "word/document.xml")
    if document is None:
        return []
    body = document.find(f"{W}body")
    headings: list[dict] = []
    for paragraph in body.iter(f"{W}p"):
        style = style_of(paragraph)
        if style not in HEADING_STYLES:
            continue
        headings.append({"style": style, "text": paragraph_text(paragraph).strip()})
    return headings


def _normalize(text: str) -> str:
    """Remove every kind of space, including the full-width ones.

    The template writes the headings as "文　　　献" and "付　　録", so a
    literal search for "文献" or "付録" would miss them.
    """
    return re.sub(r"\s+", "", text)


def find_markers(archive: zipfile.ZipFile) -> dict:
    """Locate the labelled blocks the template provides, in heading paragraphs."""
    headings = describe_headings(archive)
    heading_text = _normalize("".join(item["text"] for item in headings))
    document = read_part(archive, "word/document.xml")
    full_text = ""
    if document is not None:
        full_text = "".join(t.text or "" for t in document.iter(f"{W}t"))
    normalized_body = _normalize(full_text)

    markers = {
        "abstract_ja": "あらまし",
        "abstract_en": "Abstract",
        "keywords_ja": "キーワード",
        "keywords_en": "Keywords",
        "references": "文献",
        "appendix": "付録",
        "conclusion": "むすび",
    }
    found: dict = {}
    for key, needle in markers.items():
        in_heading = needle in heading_text
        in_body = needle in normalized_body
        found[key] = {
            "present": in_body,
            "present_in_a_heading": in_heading,
            "character_offset": full_text.find(needle) if in_body else None,
        }
    return found


def inspect(path: Path) -> dict:
    """Inspect a template file and return the full report."""
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    with zipfile.ZipFile(path) as archive:
        report = {
            "file_name": path.name,
            "bytes": len(payload),
            "sha256": digest,
            "sections": describe_sections(archive),
            "defaults": describe_defaults(archive),
            "styles": describe_styles(archive),
            "headers_footers": describe_headers_footers(archive),
            "markers": find_markers(archive),
            "headings": describe_headings(archive),
            "body_outline": describe_body_outline(archive),
            "media": [
                name for name in archive.namelist() if name.startswith("word/media/")
            ],
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect the official IEICE Word template structure"
    )
    parser.add_argument("template", type=Path, help="path to the official .docx")
    parser.add_argument("--output", type=Path, help="write the report as JSON")
    args = parser.parse_args()

    if not args.template.exists():
        parser.error(f"missing {args.template}")
    report = inspect(args.template)

    print(f"file      : {report['file_name']} ({report['bytes']:,} bytes)")
    print(f"sha256    : {report['sha256']}")
    print(f"sections  : {len(report['sections'])}")
    for section in report["sections"]:
        print(
            f"  #{section['section_index']}: "
            f"{section.get('page_width_mm')}x{section.get('page_height_mm')}mm "
            f"margins T{section.get('margin_top_mm')} B{section.get('margin_bottom_mm')} "
            f"L{section.get('margin_left_mm')} R{section.get('margin_right_mm')} "
            f"columns={section.get('columns')}"
        )
    print(f"defaults  : {report['defaults']}")
    print("markers   :")
    for key, value in report["markers"].items():
        where = "heading" if value["present_in_a_heading"] else "body"
        print(f"  {key:<16} {'present' if value['present'] else 'ABSENT':<8} ({where})")
    print(f"headings  : {len(report['headings'])}")
    for heading in report["headings"]:
        print(f"  [{heading['style']:<5}] {heading['text']}")
    print(f"styles    : {len(report['styles'])} paragraph styles")
    for style in report["styles"]:
        if style["outline_level"] is not None and style["outline_level"] < 9:
            print(
                f"  outline {style['outline_level']}: {style['style_id']} "
                f"({style['name']})"
            )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
