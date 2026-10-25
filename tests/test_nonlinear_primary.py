"""Synthetic unit tests for the non-linear comparison (#62).

Every fixture here is synthetic. The real measurements live in
``docs/nonlinear-primary-vs-general.md``.

The protocol itself is frozen in ``configs/nonlinear-comparison.json`` and is
covered by ``tests/test_nonlinear_protocol.py``. These tests check the part
that belongs to [#62](https://github.com/SMRI2170/fec-election-analysis/issues/62):
that the comparison runs the frozen setup, that no model can be preferred with
hindsight, and that every candidate is reported, including the ones that are
worse than the linear reference.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

from evaluate_nonlinear_primary import (  # noqa: E402
    FROZEN_LINEAR_MAE,
    build_estimator,
    check_frozen_baselines,
    paired_against_reference,
    predict_with,
    run_comparison,
    score_predictions,
    state_bootstrap_interval,
)
from nonlinear_protocol import (  # noqa: E402
    LabelAccessError,
    assert_no_label_access,
    build_plan,
    load_config,
    model_names,
)
from fec_analysis.core import prepare_elections  # noqa: E402

#: The sizes of the frozen cohort, so that the synthetic fixture has the same
#: shape as the real one.
COUNTS = {2016: 200, 2018: 241, 2020: 237, 2022: 238}

NOTE = REPO / "docs" / "nonlinear-primary-vs-general.md"


def synthetic_raw() -> pd.DataFrame:
    """A synthetic cohort with the sizes of the frozen one."""
    rows = []
    for year, size in COUNTS.items():
        for index in range(size):
            primary_rep = 1000 + (index * 7) % 900
            primary_dem = 2000 - (index * 5) % 700
            general_rep = int(primary_rep * 0.72) + (index % 11) - 5
            general_dem = int(primary_dem * 0.68) + (index % 13) - 6
            rows.append(
                {
                    "year": year,
                    "state": f"S{index % 12:02d}",
                    "district": f"{index // 12 + 1:02d}",
                    "chamber": "House",
                    "election_id": f"{year}-House-S{index % 12:02d}-{index // 12 + 1:02d}",
                    "primary_rep_votes": primary_rep,
                    "primary_dem_votes": primary_dem,
                    "general_rep_votes": max(general_rep, 1),
                    "general_dem_votes": max(general_dem, 1),
                }
            )
    return pd.DataFrame(rows)


def synthetic_frame() -> pd.DataFrame:
    return prepare_elections(synthetic_raw())


@pytest.fixture(scope="module")
def config() -> dict:
    return load_config()


def test_every_frozen_model_is_scored_on_every_test_year(config: dict) -> None:
    """The comparison reports all candidates, not only the best looking one."""
    summary, predictions, paired, meta = run_comparison(synthetic_frame(), config)
    expected = set(model_names(config))
    for year in config["evaluation"]["test_years"]:
        scored = set(summary[summary["test_year"].eq(year)]["model"])
        assert scored == expected
        assert int(summary[summary["test_year"].eq(year)]["n_test"].iloc[0]) == COUNTS[
            int(year)
        ]
    # Every model produces a prediction for every evaluated contest.
    evaluated = sum(COUNTS[int(year)] for year in config["evaluation"]["test_years"])
    assert len(predictions) == evaluated * len(expected)
    assert set(meta["models"]) == expected
    # The paired comparison covers every model except the reference, in every
    # evaluated year.
    assert len(paired) == (len(expected) - 1) * len(config["evaluation"]["test_years"])


def test_the_reference_model_reproduces_a_plain_least_squares_fit(config: dict) -> None:
    """The linear reference is the same measurement as the frozen backtest."""
    from sklearn.linear_model import LinearRegression

    frame = synthetic_frame()
    plan = build_plan(config, 2020)
    train = frame[frame["year"].isin(plan.train_years)]
    test = frame[frame["year"].eq(2020)]
    prediction = predict_with(
        {"family": "linear", "hyperparameters": {}}, train, test, plan
    )
    plain = LinearRegression()
    plain.fit(
        train[["primary_rep_share"]].to_numpy(dtype=float),
        train["general_rep_share"].to_numpy(dtype=float),
    )
    expected = np.clip(
        plain.predict(test[["primary_rep_share"]].to_numpy(dtype=float)), 0.0, 1.0
    )
    assert np.allclose(prediction, expected)


def test_the_carryover_model_reads_no_target_column(config: dict) -> None:
    """The carry-over model has no fitted parameter: it is the Primary share."""
    frame = synthetic_frame()
    plan = build_plan(config, 2022)
    train = frame[frame["year"].isin(plan.train_years)]
    test = frame[frame["year"].eq(2022)]
    prediction = predict_with(
        {"family": "identity", "hyperparameters": {}}, train, test, plan
    )
    assert np.allclose(prediction, test["primary_rep_share"].to_numpy(dtype=float))
    assert build_estimator({"family": "identity", "hyperparameters": {}}) is None


def test_the_predictions_do_not_depend_on_the_test_year_target(config: dict) -> None:
    """No hindsight path: the 2022 labels cannot change the 2022 predictions.

    The 2022 results were already seen during the exploratory work, so this is
    the check that the protocol did not quietly turn into a tuned pipeline.
    """
    raw = synthetic_raw()
    first, _, _, _ = run_comparison(prepare_elections(raw), config)

    scrambled = raw.copy()
    mask = scrambled["year"].eq(2022)
    values = scrambled.loc[mask, "general_rep_votes"].to_numpy()[::-1]
    scrambled.loc[mask, "general_rep_votes"] = values
    second_frame = prepare_elections(scrambled)
    second, _, _, _ = run_comparison(second_frame, config)

    for model in model_names(config):
        left = first[first["model"].eq(model)].set_index("test_year")
        right = second[second["model"].eq(model)].set_index("test_year")
        for year in left.index:
            if year == 2022:
                # The error changes, because the labels changed.
                assert left.loc[year, "mae_points"] != right.loc[year, "mae_points"]
            else:
                # The earlier years do not see the 2022 labels at all.
                assert left.loc[year, "mae_points"] == right.loc[year, "mae_points"]
        # The 2022 prediction itself is produced by the training years only.
        assert left.loc[2022, "n_train"] == right.loc[2022, "n_train"]

    # The predictions themselves are identical, only the labels moved.
    _, predictions_first, _, _ = run_comparison(prepare_elections(raw), config)
    _, predictions_second, _, _ = run_comparison(second_frame, config)
    for model in model_names(config):
        left = predictions_first[predictions_first["model"].eq(model)]
        right = predictions_second[predictions_second["model"].eq(model)]
        left = left.sort_values("election_id").reset_index(drop=True)
        right = right.sort_values("election_id").reset_index(drop=True)
        assert np.allclose(left["prediction"].to_numpy(), right["prediction"].to_numpy())


def test_the_tuning_phase_refuses_the_target_column() -> None:
    with pytest.raises(LabelAccessError):
        assert_no_label_access(["primary_rep_share", "general_rep_share"], "tuning")
    # The fit and the evaluation phases may read the target.
    assert_no_label_access(["general_rep_share"], "fit")
    assert_no_label_access(["general_rep_share"], "evaluation")


def test_the_2018_plan_is_defined_without_an_inner_validation_year(config: dict) -> None:
    """2018 has only 2016 before it, so the configuration must stay defined."""
    plan = build_plan(config, 2018)
    assert plan.train_years == (2016,)
    assert plan.inner_validation_years == ()
    assert plan.models
    assert plan.clip == (0.0, 1.0)
    assert plan.reference_model == "linear"
    assert plan.primary_metric == "mae_points"


def test_every_year_uses_only_earlier_training_years(config: dict) -> None:
    for year in config["evaluation"]["test_years"]:
        plan = build_plan(config, year)
        assert all(train < year for train in plan.train_years)
        assert all(inner < year for inner in plan.inner_validation_years)


def test_the_predictions_are_clipped_to_the_unit_interval(config: dict) -> None:
    frame = synthetic_frame()
    plan = build_plan(config, 2018)
    train = frame[frame["year"].isin(plan.train_years)]
    test = frame[frame["year"].eq(2018)]
    for spec in config["models"]:
        prediction = predict_with(spec, train, test, plan)
        assert prediction.min() >= 0.0
        assert prediction.max() <= 1.0


def test_the_clip_actually_binds_when_the_fit_would_leave_the_interval() -> None:
    """A prediction outside the unit interval has to be clipped, not passed on.

    The synthetic fixture of the other tests stays inside the interval, so the
    clip would not be noticed there. This fixture is built so that the linear
    fit extrapolates beyond one.
    """
    rows = [
        # Two training points on a steep line: P = 0.10 -> 0.50 and
        # P = 0.11 -> 0.95, so the fitted slope is about 45 and the intercept
        # about -4.0.
        {
            "year": 2016,
            "state": "AA",
            "district": "01",
            "chamber": "House",
            "election_id": "2016-House-AA-01",
            "primary_rep_votes": 100,
            "primary_dem_votes": 900,
            "general_rep_votes": 500,
            "general_dem_votes": 500,
        },
        {
            "year": 2016,
            "state": "AA",
            "district": "02",
            "chamber": "House",
            "election_id": "2016-House-AA-02",
            "primary_rep_votes": 110,
            "primary_dem_votes": 890,
            "general_rep_votes": 950,
            "general_dem_votes": 50,
        },
    ]
    for index in range(2):
        rows.append(
            {
                "year": 2018,
                "state": "BB",
                "district": f"{index:02d}",
                "chamber": "House",
                "election_id": f"2018-House-BB-{index:02d}",
                "primary_rep_votes": 900,
                "primary_dem_votes": 100,
                "general_rep_votes": 500,
                "general_dem_votes": 500,
            }
        )
    frame = prepare_elections(pd.DataFrame(rows))
    config = load_config()
    plan = build_plan(config, 2018)
    train = frame[frame["year"].isin(plan.train_years)]
    test = frame[frame["year"].eq(2018)]
    prediction = predict_with(
        {"family": "linear", "hyperparameters": {}}, train, test, plan
    )
    # Without the clip the fit would leave the interval, because the training
    # share is far below the test share.
    assert prediction.min() >= 0.0
    assert prediction.max() <= 1.0
    assert float(prediction.max()) == pytest.approx(1.0)


def test_the_paired_comparison_uses_the_same_districts(config: dict) -> None:
    frame = synthetic_frame()
    summary, predictions, paired, _ = run_comparison(frame, config)
    for _, row in paired.iterrows():
        year = int(row["test_year"])
        name = str(row["model"])
        reference = predictions[
            predictions["year"].eq(year)
            & predictions["model"].eq(config["evaluation"]["reference_model"])
        ]
        other = predictions[
            predictions["year"].eq(year) & predictions["model"].eq(name)
        ]
        assert set(reference["election_id"]) == set(other["election_id"])
        assert int(row["n"]) == len(reference)


def test_the_state_bootstrap_is_deterministic_and_labelled_exploratory(
    config: dict,
) -> None:
    delta = np.array([0.5, -0.25, 0.75, 0.0, -1.0])
    states = np.array(["AA", "AA", "BB", "BB", "CC"])
    first = state_bootstrap_interval(delta, states, seed=7, repetitions=500)
    second = state_bootstrap_interval(delta, states, seed=7, repetitions=500)
    assert first == second
    assert len(first) == 2 and first[0] <= first[1]
    with pytest.raises(ValueError):
        state_bootstrap_interval(delta, states[:2], seed=7, repetitions=500)
    _, _, paired, meta = run_comparison(synthetic_frame(), config)
    assert "exploratory" in paired["interval_status"].iloc[0]
    assert meta["bootstrap"]["unit"] == "state"


def test_the_worse_models_are_reported_as_well(config: dict) -> None:
    """A model that is worse than the reference has to appear in the output."""
    summary, _, _, _ = run_comparison(synthetic_frame(), config)
    reference = summary[summary["model"].eq("linear")].set_index("test_year")
    constant = summary[summary["model"].eq("constant-mean")].set_index("test_year")
    for year in reference.index:
        assert constant.loc[year, "mae_points"] > reference.loc[year, "mae_points"]


def test_the_frozen_baseline_check_detects_a_wrong_number() -> None:
    """The guard against a silent drift of the frozen benchmark works."""
    rows = []
    for year, value in {2018: 0.04415746508763495, 2020: 0.054936208613780235, 2022: 0.05016777648573961}.items():
        rows.append({"test_year": year, "model": "linear", "mae_points": value * 100})
    for year, value in {2018: 0.13267294966973564, 2020: 0.1398062758375418, 2022: 0.14087496490489462}.items():
        rows.append({"test_year": year, "model": "constant-mean", "mae_points": value * 100})
    for year, value in {2018: 0.0628518903589067, 2020: 0.07838882292234665, 2022: 0.0750424587137547}.items():
        rows.append({"test_year": year, "model": "primary-carryover", "mae_points": value * 100})
    summary = pd.DataFrame(rows)
    checks = check_frozen_baselines(summary)
    assert len(checks) == 9
    broken = summary.copy()
    broken.loc[
        broken["test_year"].eq(2020) & broken["model"].eq("linear"), "mae_points"
    ] += 1.0
    with pytest.raises(AssertionError):
        check_frozen_baselines(broken)


def test_the_metrics_are_reported_in_percentage_points() -> None:
    prediction = np.array([0.6, 0.4])
    actual = np.array([0.5, 0.5])
    metrics = score_predictions(prediction, actual)
    assert metrics["mae_points"] == pytest.approx(10.0)
    assert metrics["rmse_points"] == pytest.approx(10.0)
    assert metrics["p95_abs_error_points"] == pytest.approx(10.0)
    assert metrics["mean_signed_points"] == pytest.approx(0.0)


def test_the_mean_absolute_error_is_not_the_root_mean_square_error() -> None:
    """The two errors differ on an asymmetric example, so a swap is visible."""
    prediction = np.array([0.6, 0.4])
    actual = np.array([0.4, 0.8])
    metrics = score_predictions(prediction, actual)
    assert metrics["mae_points"] == pytest.approx(30.0)
    assert metrics["rmse_points"] == pytest.approx(np.sqrt(1000.0))
    assert metrics["mae_points"] != pytest.approx(metrics["rmse_points"])
    assert metrics["mean_signed_points"] == pytest.approx(-10.0)
    assert metrics["median_signed_points"] == pytest.approx(-10.0)


def test_the_paired_rows_are_produced_for_every_model_and_year(config: dict) -> None:
    frame = synthetic_frame()
    plan = build_plan(config, 2020)
    from nonlinear_protocol import fitting_rows

    train = fitting_rows(frame, plan)
    test = frame[frame["year"].eq(2020)]
    predictions = []
    for spec in config["models"]:
        prediction = predict_with(spec, train, test, plan)
        part = test[["year", "state", "district", "election_id"]].copy()
        part["model"] = spec["name"]
        part["prediction"] = prediction
        part["actual"] = test[plan.target_column].to_numpy(dtype=float)
        part["abs_error_points"] = np.abs(
            (prediction - part["actual"].to_numpy(dtype=float)) * 100
        )
        predictions.append(part)
    rows = paired_against_reference(predictions, config, plan)
    assert len(rows) == len(config["models"]) - 1
    for row in rows:
        assert row["n"] == COUNTS[2020]
        assert row["reference"] == "linear"


def test_the_note_records_the_frozen_baseline_of_the_reference_model() -> None:
    """The reference row of the note has to carry the frozen MAE value.

    The note is written by hand, so a transcription slip in the baseline row
    would silently contradict the frozen benchmark. The check parses the note
    instead of trusting it.
    """
    text = NOTE.read_text(encoding="utf-8")
    for year, value in FROZEN_LINEAR_MAE.items():
        pattern = re.compile(
            r"^\| " + str(year) + r" \| `linear` \| (\d+) \| " + f"{value * 100:.2f}",
            re.M,
        )
        assert pattern.search(text), f"the linear row of {year} does not carry the frozen MAE"


def test_the_note_lists_every_frozen_model_in_every_year() -> None:
    text = NOTE.read_text(encoding="utf-8")
    config = load_config()
    for year in config["evaluation"]["test_years"]:
        for spec in config["models"]:
            pattern = re.compile(
                r"^\| " + str(year) + r" \| `" + re.escape(str(spec["name"])) + r"` \|",
                re.M,
            )
            assert pattern.search(text), f"{spec['name']} of {year} is missing in the note"
