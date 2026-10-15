import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("plot_results", ROOT / "scripts" / "plot_results.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_report_figures_are_reproducible_with_synthetic_fixture(tmp_path):
    rows = []
    for year in [2016, 2018, 2020, 2022]:
        for state, r, d in [("AA", 55, 45), ("BB", 35, 65)]:
            rows.append({
                "year": year, "state": state, "chamber": "House", "district": "01",
                "primary_rep_votes": r, "primary_dem_votes": d,
                "general_rep_votes": r + 5, "general_dem_votes": d - 5,
            })
    values = []
    for year in [2018, 2020, 2022]:
        for model_name, score in [
            ("mean-share baseline", 0.15),
            ("primary-share identity", 0.08),
            ("linear regression", 0.05),
        ]:
            values.append({
                "test_year": year, "task": "share", "metric": "MAE",
                "model": model_name, "score": score,
            })
    paths = mod.render_figures(pd.DataFrame(rows), pd.DataFrame(values), tmp_path)
    assert len(paths) == 2
    for path in paths:
        assert path.exists() and path.stat().st_size > 1000
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_missing_backtest_model_fails(tmp_path):
    rows = [
        {
            "year": year, "state": "AA", "chamber": "House", "district": "01",
            "primary_rep_votes": 50, "primary_dem_votes": 50,
            "general_rep_votes": 55, "general_dem_votes": 45,
        }
        for year in [2016, 2022]
    ]
    with pytest.raises(ValueError, match="Missing share models"):
        mod.render_figures(pd.DataFrame(rows), pd.DataFrame([
            {"test_year": 2022, "task": "share", "metric": "MAE", "model": "linear regression", "score": 0.05}
        ]), tmp_path)
