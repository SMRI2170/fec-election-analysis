"""Unit tests for the code-appendix builder (Issue #87)."""
from __future__ import annotations

import importlib.util
import sys
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
    # The module has to be registered before it is executed, otherwise the
    # dataclass decorator cannot resolve its own module.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = _load_script("build_code_appendix")


def test_every_listed_file_exists():
    for item in builder.APPENDIX_FILES:
        assert item.absolute.exists(), item.path


def test_the_appendix_covers_the_pipeline_in_reproduction_order():
    paths = [item.path for item in builder.APPENDIX_FILES]
    assert paths[0] == "scripts/download_fec.py"
    assert paths[-1] == "scripts/plot_selective_primary.py"
    assert "scripts/normalize_fec.py" in paths
    assert "scripts/evaluate_selective_primary.py" in paths
    assert "scripts/compare_random_abstention.py" in paths
    assert "scripts/selective_primary_rule.py" in paths


def test_collect_reports_checksums_and_lines():
    entries = builder.collect()
    assert len(entries) == len(builder.APPENDIX_FILES)
    for entry in entries:
        assert len(entry["sha256"]) == 64
        assert entry["bytes"] > 0
        assert entry["lines"] > 0
        assert entry["git_commit"] and len(entry["git_commit"]) == 40


def test_render_contains_every_file_in_full():
    entries = builder.collect()
    text = builder.render_appendix(entries)
    for entry in entries:
        assert entry["path"] in text
        assert entry["sha256"] in text
        # The complete source must be present, not an excerpt.
        source = (ROOT / entry["path"]).read_text(encoding="utf-8").rstrip("\n")
        assert source in text, entry["path"]


def test_render_has_one_header_per_file():
    entries = builder.collect()
    text = builder.render_appendix(entries)
    assert text.count("--- リスト") == len(entries)


def test_render_preserves_the_exact_source_bytes():
    entries = builder.collect()
    text = builder.render_appendix(entries)
    for entry in entries:
        source = (ROOT / entry["path"]).read_text(encoding="utf-8").rstrip("\n")
        assert text.count(source) == 1


def test_a_missing_source_is_reported(monkeypatch, tmp_path):
    monkeypatch.setattr(
        builder,
        "APPENDIX_FILES",
        (builder.AppendixFile("scripts/does_not_exist.py", "x", "y"),),
    )
    with pytest.raises(FileNotFoundError):
        builder.collect()
