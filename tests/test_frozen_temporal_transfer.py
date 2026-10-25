"""Synthetic unit tests for the frozen temporal transfer analysis (#77).

No fixture in this file is an FEC result. The real measurements live in
``docs/frozen-temporal-transfer.md``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_frozen_temporal_transfer import (  # noqa: E402
    BASELINE_TRAIN_YEARS,
    COUNTS,
    FROZEN_TEST_YEARS,
    FROZEN_TRAIN_YEARS,
    _metrics,
    evaluate,
    fit_linear,
    state_interval,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fec_analysis.core import prepare_elections  # noqa: E402


def synthetic_cohort() -> pd.DataFrame:
    """A synthetic cohort with the sizes of the frozen one."""
    rows = []
    for year, size in COUNTS.items():
        for index in range(size):
            primary = 0.20 + 0.5 * ((index % 40) / 40)
            # The target drifts with the year so that a year effect exists.
            general = primary * 0.7 + 0.15 + (0.02 if year >= 2020 else 0.0)
            rows.append(
                {
                    "year": year,
                    "state": f"S{index % 37:02d}",
                    "district": f"{index % 10:02d}",
                    "chamber": "House",
                    "primary_rep_votes": 1000 + index,
                    "primary_dem_votes": 1000 - index // 2,
                    "general_rep_votes": 1500 + index,
                    "general_dem_votes": 1500 - index // 3,
                }
            )
    frame = pd.DataFrame(rows)
    return prepare_elections(frame)


def test_the_frozen_model_never_sees_a_test_year() -> None:
    frame = synthetic_cohort()
    train = frame[frame["year"].isin(FROZEN_TRAIN_YEARS)]
    assert len(train) == sum(COUNTS[year] for year in FROZEN_TRAIN_YEARS)
    assert train["year"].max() < FROZEN_TEST_YEARS[0]


def test_the_frozen_coefficients_do_not_move_when_the_test_labels_move() -> None:
    """The 2020 and 2022 labels cannot reach the frozen coefficients."""
    frame = synthetic_cohort()
    train = frame[frame["year"].isin(FROZEN_TRAIN_YEARS)]
    before = fit_linear(train)

    shuffled = frame.copy()
    mask = shuffled["year"].isin(FROZEN_TEST_YEARS)
    order = np.arange(int(mask.sum()))[::-1]
    shuffled.loc[mask, "general_rep_votes"] = (
        shuffled.loc[mask, "general_rep_votes"].to_numpy()[order]
    )
    shuffled.loc[mask, "general_dem_votes"] = (
        shuffled.loc[mask, "general_dem_votes"].to_numpy()[order]
    )
    shuffled = prepare_elections(shuffled)
    after = fit_linear(shuffled[shuffled["year"].isin(FROZEN_TRAIN_YEARS)])

    assert before.coef_[0] == pytest.approx(after.coef_[0])
    assert before.intercept_ == pytest.approx(after.intercept_)


def test_in_2020_both_models_are_trained_on_the_same_rows() -> None:
    """The 2020 comparison is degenerate on purpose: it proves that the 2020
    labels did not enter the frozen model."""
    assert BASELINE_TRAIN_YEARS[2020] == FROZEN_TRAIN_YEARS
    summary, districts, meta = evaluate(synthetic_cohort())
    frozen = summary[summary["test_year"].eq(2020) & summary["model"].eq("frozen-2016-2018")]
    baseline = summary[summary["test_year"].eq(2020) & summary["model"].eq("baseline")]
    assert float(frozen["mae"].iloc[0]) == pytest.approx(float(baseline["mae"].iloc[0]))
    assert float(frozen["mean_signed"].iloc[0]) == pytest.approx(
        float(baseline["mean_signed"].iloc[0])
    )
    part = districts[districts["year"].eq(2020)]
    assert (part["frozen_pred"].to_numpy() == part["baseline_pred"].to_numpy()).all()
    assert meta["paired"][0]["contests_where_prediction_changed"] == 0


def test_the_paired_comparison_uses_the_same_contests() -> None:
    summary, districts, meta = evaluate(synthetic_cohort())
    for year in FROZEN_TEST_YEARS:
        part = districts[districts["year"].eq(year)]
        assert len(part) == COUNTS[year]
        assert part["frozen_pred"].notna().all()
        assert part["baseline_pred"].notna().all()
        entry = [row for row in meta["paired"] if row["test_year"] == year][0]
        assert entry["same_contests_for_both_models"] is True
        assert entry["n"] == COUNTS[year]


def test_the_metrics_use_the_declared_sign_convention() -> None:
    frame = pd.DataFrame(
        {
            "state": ["AA", "AA", "BB"],
            "primary_rep_share": [0.4, 0.5, 0.6],
            "general_rep_share": [0.5, 0.4, 0.6],
            "prediction": [0.6, 0.3, 0.6],
        }
    )
    metrics = _metrics(frame, "prediction")
    # signed = predicted - actual -> +0.1, -0.1, 0.0
    assert metrics["mean_signed"] == pytest.approx(0.0)
    assert metrics["mae"] == pytest.approx((0.1 + 0.1 + 0.0) / 3)
    assert metrics["rmse"] == pytest.approx(np.sqrt((0.01 + 0.01 + 0.0) / 3))
    assert metrics["over_predictions"] == 1
    assert metrics["under_predictions"] == 1
    assert metrics["n"] == 3


def test_the_state_interval_is_deterministic_and_needs_matching_records() -> None:
    delta = np.array([0.1, -0.2, 0.3, 0.0])
    states = np.array(["AA", "AA", "BB", "BB"])
    first = state_interval(delta, states, seed=7, repetitions=200)
    second = state_interval(delta, states, seed=7, repetitions=200)
    assert first == second
    assert len(first) == 2 and first[0] <= first[1]
    with pytest.raises(ValueError):
        state_interval(delta, states[:2], seed=7, repetitions=200)
    with pytest.raises(ValueError):
        state_interval(delta, states, seed=7, repetitions=10)


def test_the_evaluation_is_deterministic() -> None:
    frame = synthetic_cohort()
    first = evaluate(frame)
    second = evaluate(frame)
    pd.testing.assert_frame_equal(first[0], second[0])
    pd.testing.assert_frame_equal(first[1], second[1])
    assert first[2]["paired"] == second[2]["paired"]


def test_the_year_effect_and_the_retraining_effect_are_separate() -> None:
    """The frozen model is unchanged, so its residual shift is a year effect."""
    summary, _, meta = evaluate(synthetic_cohort())
    frozen = summary[summary["model"].eq("frozen-2016-2018")]
    assert frozen["slope"].nunique() == 1
    assert frozen["intercept"].nunique() == 1
    assert "year_effect" in meta and "retraining_effect" in meta
    assert meta["not_a_confirmatory_holdout"]
    assert meta["no_causal_claim"] is True


def test_the_baseline_uses_every_year_before_the_test_year() -> None:
    assert BASELINE_TRAIN_YEARS[2022] == (2016, 2018, 2020)
    for year, years in BASELINE_TRAIN_YEARS.items():
        assert all(training < year for training in years)
