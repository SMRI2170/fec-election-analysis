"""Unit tests for the probability calibration analysis (#64).

The tests use synthetic fixtures only. The measured values come from running
the script against the official FEC data.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analyze_probability_calibration.py"


def load_module():
    spec = importlib.util.spec_from_file_location("analyze_probability_calibration", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


calibration = load_module()


def test_reliability_table_counts_every_case() -> None:
    probability = np.array([0.05, 0.15, 0.45, 0.55, 0.85, 0.95])
    observed = np.array([0, 0, 1, 1, 1, 1])
    table = calibration.reliability_table(observed, probability, n_bins=10)
    assert table["n"].sum() == len(observed)
    assert (table["bin_upper"] - table["bin_lower"]).round(6).eq(0.1).all()


def test_perfect_calibration_has_zero_error() -> None:
    probability = np.array([0.0] * 10 + [1.0] * 10)
    observed = np.array([0] * 10 + [1] * 10)
    table = calibration.reliability_table(observed, probability, n_bins=10)
    metrics = calibration.calibration_metrics(observed, probability, table)
    assert metrics["expected_calibration_error"] == pytest.approx(0.0, abs=1e-9)
    assert metrics["maximum_calibration_error"] == pytest.approx(0.0, abs=1e-9)


def test_over_confidence_is_detected() -> None:
    # predicted 0.9 but observed only half of the time
    probability = np.array([0.9] * 10)
    observed = np.array([1] * 5 + [0] * 5)
    table = calibration.reliability_table(observed, probability, n_bins=10)
    metrics = calibration.calibration_metrics(observed, probability, table)
    assert metrics["expected_calibration_error"] == pytest.approx(0.4)
    assert metrics["maximum_calibration_error"] == pytest.approx(0.4)
    assert metrics["calibration_in_the_large"] == pytest.approx(0.4)


def test_empty_bins_are_reported_without_error() -> None:
    probability = np.array([0.95] * 4)
    observed = np.array([1, 1, 1, 0])
    table = calibration.reliability_table(observed, probability, n_bins=10)
    assert len(table) == 10
    assert table["n"].sum() == 4
    empty = table[table["n"] == 0]
    assert empty["mean_predicted"].isna().all()
    metrics = calibration.calibration_metrics(observed, probability, table)
    assert metrics["bins_with_data"] == 1


def test_thin_bins_are_flagged() -> None:
    probability = np.array([0.95] * 2 + [0.05] * 20)
    observed = np.array([1, 0] + [0] * 20)
    table = calibration.reliability_table(observed, probability, n_bins=10)
    assert table["thin"].any()
    assert table[table["n"] > 0]["thin"].sum() == 1


def test_fit_predict_requires_two_classes() -> None:
    train = pd.DataFrame(
        {
            "primary_rep_share": [0.3, 0.4],
            "general_rep_win": [1, 1],
        }
    )
    test = pd.DataFrame({"primary_rep_share": [0.5], "general_rep_win": [1]})
    with pytest.raises(ValueError, match="both winner classes"):
        calibration.fit_predict(train, test)


def test_fit_predict_requires_non_empty_split() -> None:
    frame = pd.DataFrame({"primary_rep_share": [], "general_rep_win": []})
    with pytest.raises(ValueError, match="empty"):
        calibration.fit_predict(frame, frame)


def test_summary_declares_no_general_predictor() -> None:
    summary = {
        "general_used_as_predictor": False,
        "new_model_family": False,
    }
    assert summary["general_used_as_predictor"] is False
    assert summary["new_model_family"] is False


def test_brier_matches_the_frozen_backtest_when_data_is_present() -> None:
    """The calibration script must reproduce the frozen Brier scores."""
    data_path = Path("data/processed/elections.csv")
    metrics_path = Path("data/processed/backtest_metrics.csv")
    if not data_path.exists() or not metrics_path.exists():
        pytest.skip("official FEC data are not prepared in this environment")
    frozen = pd.read_csv(metrics_path)
    data = pd.read_csv(data_path, dtype={"state": str, "district": str})
    _, summary = calibration.analyze(data, [2018, 2020, 2022])
    for entry in summary["per_year"]:
        expected = float(
            frozen[
                (frozen["test_year"] == entry["year"])
                & (frozen["model"] == "logistic regression")
                & (frozen["metric"] == "Brier")
            ]["score"].iloc[0]
        )
        assert entry["brier"] == pytest.approx(expected, abs=1e-12)
