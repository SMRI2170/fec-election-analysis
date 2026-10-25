"""Unit tests for the state residual composition audit (#63).

The tests use synthetic fixtures only. The measured values come from running
the script against the official FEC data.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_state_residual_composition.py"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_state_residual_composition", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


audit = load_module()


@pytest.fixture()
def metrics() -> pd.DataFrame:
    """Three states per year with a known residual composition."""
    rows = []
    for year in (2018, 2020, 2022):
        rows += [
            # two rankable states with a positive residual
            {"year": year, "state": "AA", "n": 10, "linear_mae": 0.04,
             "linear_signed_pred_minus_actual": 0.02},
            {"year": year, "state": "BB", "n": 5, "linear_mae": 0.06,
             "linear_signed_pred_minus_actual": 0.04},
            # one small state with an opposite residual
            {"year": year, "state": "CC", "n": 2, "linear_mae": 0.10,
             "linear_signed_pred_minus_actual": -0.05},
        ]
    return pd.DataFrame(rows)


@pytest.fixture()
def coverage() -> pd.DataFrame:
    rows = []
    for year in (2018, 2020, 2022):
        rows += [
            {"population": "50-state-voting-House", "year": year, "state": "AA", "selected": 10},
            {"population": "50-state-voting-House", "year": year, "state": "BB", "selected": 5},
            {"population": "50-state-voting-House", "year": year, "state": "CC", "selected": 2},
            # a state with no selected contest at all
            {"population": "50-state-voting-House", "year": year, "state": "DD", "selected": 0},
        ]
    return pd.DataFrame(rows)


@pytest.mark.parametrize(
    "n,expected",
    [(0, "n_0"), (1, "n_1_to_4"), (4, "n_1_to_4"), (5, "n_ge_5"), (10, "n_ge_5")],
)
def test_classify_boundaries(n: int, expected: str) -> None:
    assert audit.classify(n) == expected


def test_groups_partition_the_states(metrics: pd.DataFrame, coverage: pd.DataFrame) -> None:
    composition = audit.compose(metrics, coverage)
    assert len(composition) == 3 * 3
    for year in (2018, 2020, 2022):
        rows = composition[composition["year"] == year]
        assert rows["states"].sum() == 4
        assert rows["contests"].sum() == 17
        assert rows["contest_share"].sum() == pytest.approx(1.0)


def test_signed_bias_shares_sum_to_one(metrics: pd.DataFrame, coverage: pd.DataFrame) -> None:
    composition = audit.compose(metrics, coverage)
    for year in (2018, 2020, 2022):
        rows = composition[composition["year"] == year]
        assert rows["share_of_total_signed_bias"].sum() == pytest.approx(1.0)


def test_aggregate_signed_residual_is_district_weighted(
    metrics: pd.DataFrame, coverage: pd.DataFrame
) -> None:
    composition = audit.compose(metrics, coverage)
    rows = composition[composition["year"] == 2018]
    expected = (10 * 0.02 + 5 * 0.04 + 2 * -0.05) / 17
    assert rows["aggregate_signed_residual"].iloc[0] == pytest.approx(expected)


def test_small_group_can_carry_an_opposite_share(
    metrics: pd.DataFrame, coverage: pd.DataFrame
) -> None:
    composition = audit.compose(metrics, coverage)
    rows = composition[composition["year"] == 2018].set_index("group")
    assert rows.loc["n_1_to_4", "share_of_total_signed_bias"] < 0
    assert rows.loc["n_ge_5", "share_of_total_signed_bias"] > 1


def test_opposite_sign_states_are_counted(metrics: pd.DataFrame, coverage: pd.DataFrame) -> None:
    composition = audit.compose(metrics, coverage)
    summary = audit.composition_summary(composition, metrics)
    entry = summary["per_year"][0]
    assert entry["rankable_states"] == 2
    assert entry["rankable_states_opposite_to_aggregate"] == 0
    assert entry["states_zero"] == 1
    assert entry["contests_small"] == 2
    assert summary["general_used_as_predictor"] is False
    assert summary["new_model_fitted"] is False


def test_missing_columns_are_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "metrics.csv"
    pd.DataFrame([{"year": 2018, "state": "AA"}]).to_csv(bad, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        audit.load_metrics(bad)


def test_nonvoting_rows_are_dropped(tmp_path: Path) -> None:
    path = tmp_path / "coverage.csv"
    pd.DataFrame(
        [
            {"population": "50-state-voting-House", "year": 2018, "state": "AA", "selected": 3},
            {"population": "nonvoting-delegate", "year": 2018, "state": "DC", "selected": 0},
        ]
    ).to_csv(path, index=False)
    frame = audit.load_coverage(path)
    assert list(frame["state"]) == ["AA"]
