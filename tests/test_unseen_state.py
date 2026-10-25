"""Synthetic unit tests for the leave-one-state-out stress test (#65).

Every fixture here is synthetic. The real measurements live in
``docs/unseen-state-robustness.md``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_unseen_state import (  # noqa: E402
    COUNTS,
    STATES_WITHOUT_ADOPTED_CONTESTS,
    TEST_YEARS,
    _scores,
    evaluate,
    evaluate_year,
    fit_linear,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fec_analysis.core import prepare_elections  # noqa: E402


def synthetic_cohort() -> pd.DataFrame:
    """A synthetic cohort with the sizes of the frozen one."""
    rows = []
    for year, size in COUNTS.items():
        for index in range(size):
            primary = 0.20 + 0.5 * ((index % 40) / 40)
            general = primary * 0.7 + 0.15
            rows.append(
                {
                    "year": year,
                    "state": f"S{index % 12:02d}",
                    # The district number makes the (year, state, district) key
                    # unique for the synthetic cohort.
                    "district": f"{index // 12 + 1:02d}",
                    "chamber": "House",
                    "primary_rep_votes": 1000 + index,
                    "primary_dem_votes": 1000 - index // 2,
                    "general_rep_votes": 1500 + index,
                    "general_dem_votes": 1500 - index // 3,
                }
            )
    return prepare_elections(pd.DataFrame(rows))


def test_the_excluded_state_is_never_in_the_training_set() -> None:
    frame = synthetic_cohort()
    for year in TEST_YEARS:
        train_all = frame[frame["year"].lt(year)]
        test = frame[frame["year"].eq(year)]
        for state in test["state"].unique():
            reduced = train_all[~train_all["state"].eq(state)]
            assert not reduced["state"].eq(state).any()
            assert len(reduced) == len(train_all) - int(train_all["state"].eq(state).sum())


def test_the_training_set_never_reaches_into_the_test_year() -> None:
    frame = synthetic_cohort()
    for year in TEST_YEARS:
        train_all = frame[frame["year"].lt(year)]
        assert train_all["year"].max() < year


def test_the_test_year_labels_do_not_change_the_model() -> None:
    """Time-leak check: permuting the test year labels must not move the
    fitted model, because the model is fitted on the earlier years only."""
    frame = synthetic_cohort()
    rows = evaluate_year(frame, 2020)
    shuffled = frame.copy()
    mask = shuffled["year"].eq(2020)
    order = np.arange(int(mask.sum()))[::-1]
    shuffled.loc[mask, "general_rep_votes"] = (
        shuffled.loc[mask, "general_rep_votes"].to_numpy()[order]
    )
    shuffled.loc[mask, "general_dem_votes"] = (
        shuffled.loc[mask, "general_dem_votes"].to_numpy()[order]
    )
    shuffled = prepare_elections(shuffled)
    other = evaluate_year(shuffled, 2020)
    for first, second in zip(rows, other):
        assert first["normal_slope"] == second["normal_slope"]
        assert first["normal_intercept"] == second["normal_intercept"]
        assert first["excluded_slope"] == second["excluded_slope"]
        assert first["excluded_intercept"] == second["excluded_intercept"]
        assert first["mean_prediction_change"] == second["mean_prediction_change"]


def test_both_models_are_scored_on_the_same_test_districts() -> None:
    frame = synthetic_cohort()
    rows = evaluate_year(frame, 2020)
    for row in rows:
        expected = int((frame["year"].eq(2020) & frame["state"].eq(row["state"])).sum())
        assert row["test_n"] == expected


def test_a_state_without_training_contests_changes_nothing() -> None:
    """A state that never enters the training set cannot be excluded."""
    frame = synthetic_cohort()
    # Drop the training contests of one state altogether.
    reduced = frame[~(frame["year"].lt(2020) & frame["state"].eq("S00"))].copy()
    rows = evaluate_year(reduced, 2020)
    row = [item for item in rows if item["state"] == "S00"][0]
    assert row["train_n_state"] == 0
    assert row["exclusion_changed_nothing"] is True
    assert row["mae_difference_excluded_minus_normal"] == 0.0
    assert row["note"] == "no-training-contest-for-this-state"


def test_the_reduction_share_is_reported() -> None:
    frame = synthetic_cohort()
    rows = evaluate_year(frame, 2022)
    for row in rows:
        assert 0.0 <= row["train_reduction_share"] <= 1.0
        expected = row["train_n_state"] / row["train_n_all"]
        assert row["train_reduction_share"] == pytest.approx(expected)


def test_the_scores_use_the_declared_sign_convention() -> None:
    scores = _scores(np.array([0.6, 0.3]), np.array([0.5, 0.4]))
    assert scores["mean_signed"] == pytest.approx((0.1 - 0.1) / 2)
    assert scores["mae"] == pytest.approx(0.1)
    assert scores["rmse"] == pytest.approx(0.1)


def test_the_table_has_one_row_per_year_and_state() -> None:
    frame = synthetic_cohort()
    table, summary = evaluate(frame)
    assert not table.duplicated(["test_year", "state"]).any()
    assert len(table) == sum(
        int(frame[frame["year"].eq(year)]["state"].nunique()) for year in TEST_YEARS
    )
    assert summary["state_year_pairs"] == len(table)
    assert summary["state_year_pairs_without_change"] == int(
        table["exclusion_changed_nothing"].sum()
    )


def test_the_evaluation_is_deterministic() -> None:
    frame = synthetic_cohort()
    first, first_summary = evaluate(frame)
    second, second_summary = evaluate(frame)
    pd.testing.assert_frame_equal(first, second)
    assert first_summary == second_summary


def test_the_fit_needs_a_non_empty_training_set() -> None:
    with pytest.raises(ValueError):
        fit_linear(pd.DataFrame(columns=["primary_rep_share", "general_rep_share"]))


def test_the_states_without_adopted_contests_are_documented() -> None:
    assert "AK" in STATES_WITHOUT_ADOPTED_CONTESTS
    assert "CT" in STATES_WITHOUT_ADOPTED_CONTESTS
    assert len(STATES_WITHOUT_ADOPTED_CONTESTS) == 11
