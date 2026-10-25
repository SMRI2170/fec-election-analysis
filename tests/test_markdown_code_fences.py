"""Guard against escaped backticks in the public Markdown documents.

An earlier editing pass wrote every inline-code and code-fence backtick as
``\\```. Markdown renders that as a literal backtick, so the affected files
lost their code blocks and their inline code spans. This test keeps the
documents renderable and fails loudly if the pattern comes back.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ESCAPED_BACKTICK = "\\`"

#: Documents that are allowed to contain the escaped form, with a reason.
ALLOWED: dict[str, str] = {}


def markdown_files() -> list[Path]:
    paths = [REPO / "README.md", REPO / "AGENTS.md"]
    paths.extend(sorted((REPO / "docs").rglob("*.md")))
    readable = []
    for path in paths:
        # AppleDouble side-car files ("._name.md") are binary resource forks
        # that the external volume recreates; they are not documents.
        if not path.exists() or path.name.startswith("._"):
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        readable.append(path)
    return readable


def test_markdown_files_are_found() -> None:
    assert len(markdown_files()) > 10


@pytest.mark.parametrize(
    "path", markdown_files(), ids=lambda p: str(p.relative_to(REPO))
)
def test_no_escaped_backticks(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    relative = str(path.relative_to(REPO))
    if relative in ALLOWED:
        pytest.skip(ALLOWED[relative])
    count = text.count(ESCAPED_BACKTICK)
    assert count == 0, (
        f"{relative} contains {count} escaped backticks; code fences and "
        "inline code spans would not render"
    )


def test_code_fences_are_balanced() -> None:
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        fences = sum(
            1
            for line in text.splitlines()
            if line.startswith("```") and not line.startswith("````")
        )
        assert fences % 2 == 0, f"{path.name} has an unbalanced code fence count"
