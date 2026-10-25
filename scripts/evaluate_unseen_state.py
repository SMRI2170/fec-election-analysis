"""Leave-one-state-out stress test of the out-of-year model (#65).

For every test year and every state that appears in that year, the model is
fitted twice on the same training years:

* the **normal** model, trained on every contest of the earlier years,
* the **excluded** model, trained on the earlier years with all contests of
  that state removed.

Both models are scored on the **same test districts**: the districts of that
state in the test year. The comparison therefore answers one question only:
how much of the prediction for a state depends on that state's own earlier
elections.

States that have no contest in the training years cannot be removed, so the
exclusion changes nothing there. That case is recorded explicitly instead of
being dropped.

The results are a stress test, not a performance claim: the states are not
independent, several of them have very few contests, and the test years were
already inspected during the exploratory work.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fec_analysis.core import prepare_elections  # noqa: E402

#: The frozen cohort, unchanged by this script.
COUNTS = {2016: 200, 2018: 241, 2020: 237, 2022: 238}
#: The test years of the stress test.
TEST_YEARS = (2018, 2020, 2022)
#: The states that never enter the study cohort. They are listed so that the
#: absence of a training row is documented instead of assumed.
STATES_WITHOUT_ADOPTED_CONTESTS = (
    "AK", "AR", "CA", "CT", "DE", "LA", "MN", "ND", "NY", "SD", "WA",
)


def fit_linear(frame: pd.DataFrame, x: str = "primary_rep_share", y: str = "general_rep_share"):
    """Fit the one-variable linear model on the given rows."""
    if frame.empty:
        raise ValueError("training set is empty")
    return LinearRegression().fit(frame[[x]], frame[y])


def _scores(prediction: np.ndarray, actual: np.ndarray) -> dict:
    """Metrics of one prediction on one set of districts."""
    signed = np.asarray(prediction, dtype=float) - np.asarray(actual, dtype=float)
    return {
        "mae": float(np.abs(signed).mean()),
        "rmse": float(np.sqrt((signed**2).mean())),
        "mean_signed": float(signed.mean()),
    }


def evaluate_year(frame: pd.DataFrame, year: int) -> list[dict]:
    """Run the leave-one-state-out stress test for one test year."""
    train_all = frame[frame["year"].lt(year)].copy()
    test = frame[frame["year"].eq(year)].copy()
    if train_all.empty or test.empty:
        raise ValueError(f"empty train or test set for {year}")
    if train_all["year"].max() >= year:
        raise AssertionError("the training set reaches into the test year")

    normal = fit_linear(train_all)
    rows = []
    for state in sorted(test["state"].unique()):
        train_state = train_all[train_all["state"].eq(state)]
        reduced = train_all[~train_all["state"].eq(state)]
        test_state = test[test["state"].eq(state)]
        x_test = test_state[["primary_rep_share"]]
        y_test = test_state["general_rep_share"].to_numpy(dtype=float)

        normal_pred = normal.predict(x_test).clip(0, 1)
        normal_scores = _scores(normal_pred, y_test)

        if len(reduced) == len(train_all):
            # The state has no contest in the training years: nothing to remove.
            excluded_pred = normal_pred
            excluded_scores = normal_scores
            excluded = None
            state_note = "no-training-contest-for-this-state"
        else:
            excluded = fit_linear(reduced)
            excluded_pred = excluded.predict(x_test).clip(0, 1)
            excluded_scores = _scores(excluded_pred, y_test)
            state_note = ""

        rows.append(
            {
                "test_year": int(year),
                "state": str(state),
                "test_n": int(len(test_state)),
                "train_n_all": int(len(train_all)),
                "train_n_state": int(len(train_state)),
                "train_n_after_exclusion": int(len(reduced)),
                "train_reduction_share": float(
                    len(train_state) / len(train_all) if len(train_all) else 0.0
                ),
                "states_in_training": int(train_all["state"].nunique()),
                "normal_mae": normal_scores["mae"],
                "normal_rmse": normal_scores["rmse"],
                "normal_mean_signed": normal_scores["mean_signed"],
                "excluded_mae": excluded_scores["mae"],
                "excluded_rmse": excluded_scores["rmse"],
                "excluded_mean_signed": excluded_scores["mean_signed"],
                "mae_difference_excluded_minus_normal": (
                    excluded_scores["mae"] - normal_scores["mae"]
                ),
                "mean_prediction_change": float((excluded_pred - normal_pred).mean()),
                "normal_slope": round(float(normal.coef_[0]), 6),
                "normal_intercept": round(float(normal.intercept_), 6),
                "excluded_slope": (
                    None if excluded is None else round(float(excluded.coef_[0]), 6)
                ),
                "excluded_intercept": (
                    None if excluded is None else round(float(excluded.intercept_), 6)
                ),
                "exclusion_changed_nothing": excluded is None,
                "note": state_note,
            }
        )
    return rows


def evaluate(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Run the stress test for every test year."""
    rows: list[dict] = []
    for year in TEST_YEARS:
        rows.extend(evaluate_year(frame, year))
    table = pd.DataFrame(rows)
    changed = table[~table["exclusion_changed_nothing"]]
    summary = {
        "analysis": "unseen-state-stress-test-v1",
        "study": "official FEC 2016/2018/2020/2022, 916 selected House voting records",
        "test_years": list(TEST_YEARS),
        "states_without_adopted_contests": list(STATES_WITHOUT_ADOPTED_CONTESTS),
        "state_year_pairs": int(len(table)),
        "state_year_pairs_with_training_contests": int(len(changed)),
        "state_year_pairs_without_change": int(len(table) - len(changed)),
        "state_year_pairs_worse_after_exclusion": int(
            (changed["mae_difference_excluded_minus_normal"] > 0).sum()
        ),
        "state_year_pairs_better_after_exclusion": int(
            (changed["mae_difference_excluded_minus_normal"] < 0).sum()
        ),
        "state_year_pairs_equal_after_exclusion": int(
            (changed["mae_difference_excluded_minus_normal"] == 0).sum()
        ),
        "per_year": {
            str(year): {
                "state_year_pairs": int(len(part)),
                "without_change": int(part["exclusion_changed_nothing"].sum()),
                "worse_after_exclusion": int(
                    (part["mae_difference_excluded_minus_normal"] > 0).sum()
                ),
                "better_after_exclusion": int(
                    (part["mae_difference_excluded_minus_normal"] < 0).sum()
                ),
                "median_mae_difference_points": round(
                    float(part["mae_difference_excluded_minus_normal"].median() * 100), 4
                ),
                "max_mae_difference_points": round(
                    float(part["mae_difference_excluded_minus_normal"].max() * 100), 4
                ),
                "min_mae_difference_points": round(
                    float(part["mae_difference_excluded_minus_normal"].min() * 100), 4
                ),
                "median_test_n": float(part["test_n"].median()),
                "median_train_n_state": float(part["train_n_state"].median()),
            }
            for year, part in table.groupby("test_year")
        },
        "largest_degradation": changed.nlargest(5, "mae_difference_excluded_minus_normal")[
            ["test_year", "state", "test_n", "train_n_state", "mae_difference_excluded_minus_normal"]
        ].to_dict(orient="records"),
        "largest_improvement": changed.nsmallest(5, "mae_difference_excluded_minus_normal")[
            ["test_year", "state", "test_n", "train_n_state", "mae_difference_excluded_minus_normal"]
        ].to_dict(orient="records"),
        "median_mae_difference_points": round(
            float(changed["mae_difference_excluded_minus_normal"].median() * 100), 4
        ) if not changed.empty else None,
        "max_mae_difference_points": round(
            float(changed["mae_difference_excluded_minus_normal"].max() * 100), 4
        ) if not changed.empty else None,
        "min_mae_difference_points": round(
            float(changed["mae_difference_excluded_minus_normal"].min() * 100), 4
        ) if not changed.empty else None,
        "no_causal_claim": True,
        "not_a_confirmatory_holdout": (
            "the test years were already inspected during the exploratory work"
        ),
        "limitations": [
            "the states are not independent: they share parties, media and candidate pools",
            "several states have very few contests, so the excluded model is close to the normal one",
            "the comparison keeps the test districts fixed and changes only the training set",
        ],
    }
    return table, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/elections.csv"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/unseen_state")
    )
    args = parser.parse_args()

    data = prepare_elections(pd.read_csv(args.input, dtype={"state": str, "district": str}))
    data = data[data["chamber"].eq("House")].copy()
    if len(data) != sum(COUNTS.values()):
        raise AssertionError("the frozen 916-record cohort changed")
    table, summary = evaluate(data)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output_dir / "unseen_state.csv", index=False)
    (args.output_dir / "unseen_state_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print()
    print(
        table[
            [
                "test_year",
                "state",
                "test_n",
                "train_n_state",
                "train_reduction_share",
                "normal_mae",
                "excluded_mae",
                "mae_difference_excluded_minus_normal",
                "exclusion_changed_nothing",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:.4f}")
    )
    print("Saved:", args.output_dir / "unseen_state.csv")


if __name__ == "__main__":
    main()
