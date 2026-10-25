"""Guard the public documents against mixed-script text corruption.

Several editing passes introduced stray English words inside Japanese
sentences and, twice, Korean syllables inside a Japanese sentence. Both are
silent in review because the surrounding text still looks like Japanese. The
documents in this repository are written in Japanese, so:

* a Hangul syllable is always a defect,
* an ASCII word directly between Japanese characters is a defect unless it is
  one of the known technical terms listed below.

The whitelist is deliberately explicit: a new term has to be added here in a
reviewable way instead of slipping into the prose unnoticed.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
ASCII_IN_CJK = re.compile(r"[぀-ヿ一-鿿][A-Za-z]{2,}[぀-ヿ一-鿿]")

#: Technical terms that legitimately sit between Japanese characters.
ALLOWED_TERMS = frozenset(
    {
        "AI", "ASCII", "Accuracy", "Action", "Actions", "Alton", "Artifact",
        "Artifacts", "Bonferroni", "Brier", "CI", "CSV", "Canvass", "Clark",
        "Close", "Closed", "Codex", "DISTRICT", "DOCX", "Defiance", "Delegate",
        "District", "DoD", "ECE", "Erie", "Excel", "FEC", "Fung", "General",
        "Git", "GitHub", "Goffstown", "HHI", "House", "ID", "IEICE", "Issue",
        "JSON", "Kaptur", "Kent", "LibreOffice", "Logistic", "Logit", "MAE",
        "Madison", "Majewski", "Manaba", "McNemar", "Michigan", "NH", "Ohio",
        "Open", "Ottawa", "PDF", "PMF", "PNG", "PR", "Preface", "Primary",
        "Python", "QA", "RCV", "README", "RQ", "Riedel", "Runoff", "SHA",
        "Scattered", "Senate", "Totals", "URL", "Word", "XLS", "XLSX",
        "accuracy", "canvass", "coverage", "district", "docx", "fixture", "git",
        "main", "manifest", "pip", "primary", "private", "pytest",
        "requirements", "risk", "vs", "vsLogit",
    }
)


def markdown_files() -> list[Path]:
    paths = [REPO / "README.md", REPO / "AGENTS.md"]
    paths.extend(sorted((REPO / "docs").rglob("*.md")))
    readable = []
    for path in paths:
        if not path.exists() or path.name.startswith("._"):
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        readable.append(path)
    return readable


def test_documents_are_found() -> None:
    assert len(markdown_files()) > 10


@pytest.mark.parametrize(
    "path", markdown_files(), ids=lambda p: str(p.relative_to(REPO))
)
def test_no_hangul_in_japanese_documents(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    found = HANGUL.findall(text)
    assert not found, (
        f"{path.relative_to(REPO)} contains Hangul syllables {found}; "
        "the documents are written in Japanese"
    )


@pytest.mark.parametrize(
    "path", markdown_files(), ids=lambda p: str(p.relative_to(REPO))
)
def test_no_unexpected_ascii_inside_japanese(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    unexpected = []
    for match in ASCII_IN_CJK.finditer(text):
        for word in re.findall(r"[A-Za-z]{2,}", match.group(0)):
            if word not in ALLOWED_TERMS:
                unexpected.append(word)
    assert not unexpected, (
        f"{path.relative_to(REPO)} contains unexpected Latin words inside "
        f"Japanese text: {sorted(set(unexpected))}"
    )
