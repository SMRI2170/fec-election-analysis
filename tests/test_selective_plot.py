"""Unit tests for the coverage-risk figures (Issue #82).

Synthetic fixtures only. The official figures are rendered from the real FEC
data by the official-FEC GitHub Actions workflow.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
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


plotter = _load_script("plot_selective_primary")


def make_grid(
    years=(2018, 2020, 2022),
    thresholds=(0, 5, 10, 15, 20),
    accepted_by_year=None,
    wrong_by_year=None,
) -> pd.DataFrame:
    """Build a synthetic grid with the same shape as the real one."""
    accepted_by_year = accepted_by_year or {}
    wrong_by_year = wrong_by_year or {}
    rows = []
    for year in years:
        eligible = 100
        for threshold in thresholds:
            # The default keeps at least one answered contest at every
            # threshold; tests that need a silent condition set it explicitly.
            accepted = accepted_by_year.get((year, threshold), 100 - 2 * threshold)
            wrong = wrong_by_year.get((year, threshold), 0)
            if accepted == 0:
                risk = float("nan")
            else:
                risk = wrong / accepted
            rows.append(
                {
                    "test_year": year,
                    "t_pct": threshold,
                    "eligible": eligible,
                    "accepted": accepted,
                    "abstained": eligible - accepted,
                    "coverage": accepted / eligible,
                    "correct_accepted": accepted - wrong,
                    "wrong_accepted": wrong,
                    "selective_risk": risk,
                    "conditional_accuracy": 1 - risk if accepted else float("nan"),
                    "correct_abstained": 0,
                    "wrong_abstained": 0,
                    "wrong_per_eligible": wrong / eligible,
                }
            )
    return pd.DataFrame(rows)


def make_random_baseline(grid: pd.DataFrame) -> pd.DataFrame:
    frame = grid.copy()
    frame["all_wrong"] = frame["wrong_accepted"]
    frame["all_eligible"] = frame["eligible"]
    frame["random_abstention_expected_wrong"] = (
        frame["accepted"] * frame["all_wrong"] / frame["all_eligible"]
    )
    return frame


# --------------------------------------------------------------------------
# Figure rendering
# --------------------------------------------------------------------------


def test_coverage_risk_figure_is_written_as_png_and_svg(tmp_path):
    grid = make_grid()
    paths = plotter.plot_coverage_risk(grid, tmp_path, make_random_baseline(grid))
    names = {path.name for path in paths}
    assert names == {"selective_coverage_risk.png", "selective_coverage_risk.svg"}
    for path in paths:
        assert path.exists() and path.stat().st_size > 1000
    png = tmp_path / "selective_coverage_risk.png"
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_random_comparison_figure_is_written(tmp_path):
    grid = make_grid()
    paths = plotter.plot_random_comparison(make_random_baseline(grid), tmp_path)
    assert len(paths) == 1
    assert paths[0].exists() and paths[0].stat().st_size > 1000


def test_random_comparison_requires_the_reference_columns(tmp_path):
    with pytest.raises(ValueError, match="random-abstention columns"):
        plotter.plot_random_comparison(make_grid(), tmp_path)


def test_empty_grid_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        plotter.plot_coverage_risk(pd.DataFrame(), tmp_path)


# --------------------------------------------------------------------------
# Point selection
# --------------------------------------------------------------------------


def test_every_condition_with_an_answer_is_plotted():
    grid = make_grid()
    description = plotter.describe_figure(grid)
    assert description["total_points_plotted"] == len(grid)
    for series in description["series"]:
        assert series["points_plotted"] == series["conditions"]


def test_a_condition_without_an_answer_is_not_plotted():
    grid = make_grid(accepted_by_year={(2022, 20): 0})
    description = plotter.describe_figure(grid)
    series = {item["test_year"]: item for item in description["series"]}
    assert series[2022]["points_plotted"] == 4
    assert series[2022]["conditions"] == 5
    assert series[2022]["conditions_without_an_answer"] == 1
    # The risk of a condition with no answer is NA, not zero.
    risks = dict(zip(series[2022]["t_pct"], series[2022]["selective_risk_percent"]))
    assert risks[20] is None


def test_description_reports_the_coverage_and_risk_in_percent():
    grid = make_grid(accepted_by_year={(2018, 5): 80}, wrong_by_year={(2018, 5): 4})
    description = plotter.describe_figure(grid)
    series = {item["test_year"]: item for item in description["series"]}
    coverage = dict(zip(series[2018]["t_pct"], series[2018]["coverage_percent"]))
    risk = dict(zip(series[2018]["t_pct"], series[2018]["selective_risk_percent"]))
    assert coverage[5] == pytest.approx(80.0)
    assert risk[5] == pytest.approx(5.0)


def test_description_names_the_baseline_condition():
    grid = make_grid()
    description = plotter.describe_figure(grid)
    for series in description["series"]:
        assert "t=0" in series["baseline_condition"]


def test_series_are_ordered_by_threshold():
    grid = make_grid()
    series = plotter.build_series(grid)
    for frame in series.values():
        thresholds = frame["t_pct"].tolist()
        assert thresholds == sorted(thresholds)


def test_figure_survives_a_grid_without_the_random_baseline(tmp_path):
    grid = make_grid()
    paths = plotter.plot_coverage_risk(grid, tmp_path, None)
    for path in paths:
        assert path.exists()
