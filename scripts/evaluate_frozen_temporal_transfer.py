"""Separate the year effect from the retraining effect (#77).

The out-of-year backtests report a mean signed residual that flips from
-4.58 points in 2020 to +3.00 points in 2022. The 2022 model, however, was
trained on one year more than the 2020 model. This script separates the two
reasons:

* **Year effect.** One linear model is fitted on the 2016 and 2018 contests
  only (441 rows). Its coefficients are frozen and the model is applied to the
  2020 and 2022 contests unchanged. The difference of its mean signed residual
  between the two years cannot come from retraining, because the model never
  changed.
* **Retraining effect.** On the identical 238 contests of 2022 the frozen model
  and the current baseline (fitted on 2016, 2018 and 2020) are compared in a
  paired way. The difference of the two predictions is the change the extra
  training year produced.

Both effects are reported in **separate tables**. Nothing here claims that the
2022 result is a confirmatory holdout: 2022 was already inspected during the
exploratory work, the two test years do not share the same selected contests,
and the FEC workbooks are published after the election.
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
#: The training years of the frozen model. Only the years before 2020 are
#: allowed, so that the 2020 and 2022 labels can never reach its coefficients.
FROZEN_TRAIN_YEARS = (2016, 2018)
#: The test years the frozen model is applied to.
FROZEN_TEST_YEARS = (2020, 2022)
#: The baseline the frozen model is compared with: every contest before the
#: test year, which is the current out-of-year baseline.
BASELINE_TRAIN_YEARS = {2020: (2016, 2018), 2022: (2016, 2018, 2020)}
#: The frozen baseline values of the current backtest, reproduced by this
#: script so that a change of the pipeline is noticed.
BASELINE_CHECKS = {
    2022: {"mae": 0.0502, "mean_signed": 0.0300},
}


def fit_linear(frame: pd.DataFrame, x: str = "primary_rep_share", y: str = "general_rep_share"):
    """Fit the one-variable linear model on the given rows."""
    if frame.empty:
        raise ValueError("training set is empty")
    model = LinearRegression().fit(frame[[x]], frame[y])
    return model


def _metrics(frame: pd.DataFrame, prediction_column: str, y: str = "general_rep_share") -> dict:
    """Collect the metrics of one model on one test year."""
    signed = frame[prediction_column].to_numpy(dtype=float) - frame[y].to_numpy(dtype=float)
    return {
        "n": int(len(frame)),
        "states": int(frame["state"].nunique()),
        "mae": float(np.abs(signed).mean()),
        "rmse": float(np.sqrt((signed**2).mean())),
        "mean_signed": float(signed.mean()),
        "over_predictions": int((signed > 0).sum()),
        "under_predictions": int((signed < 0).sum()),
        "mean_primary_share": float(frame["primary_rep_share"].mean()),
        "mean_general_share": float(frame[y].mean()),
    }


def state_interval(
    delta: np.ndarray, states: np.ndarray, seed: int, repetitions: int = 4000
) -> list[float]:
    """Cluster bootstrap over states; a diagnostic interval, not a national CI."""
    if len(delta) != len(states) or len(delta) == 0 or repetitions < 100:
        raise ValueError("paired records and at least 100 draws are required")
    part = pd.DataFrame(
        {
            "state": np.asarray(states).astype(str),
            "d": np.asarray(delta, dtype=float),
        }
    )
    if not np.isfinite(part["d"].to_numpy()).all():
        raise ValueError("invalid error values")
    grouped = part.groupby("state", sort=True)["d"].agg(["sum", "count"])
    if len(grouped) < 2:
        raise ValueError("at least two states are required")
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(grouped), size=(repetitions, len(grouped)))
    totals = grouped["sum"].to_numpy()[draws].sum(axis=1)
    counts = grouped["count"].to_numpy()[draws].sum(axis=1)
    return [round(float(value), 6) for value in np.quantile(totals / counts, [0.025, 0.975])]


def evaluate(data: pd.DataFrame, seed: int = 20261025) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Apply the frozen model and the baseline to the two test years.

    Returns the per-year summary, the per-district predictions and the run
    metadata.
    """
    frame = data[data["chamber"].eq("House")].copy()
    frozen_train = frame[frame["year"].isin(FROZEN_TRAIN_YEARS)].copy()
    if len(frozen_train) != sum(COUNTS[year] for year in FROZEN_TRAIN_YEARS):
        raise AssertionError("the frozen training set does not match the cohort")
    if frozen_train["year"].max() >= FROZEN_TEST_YEARS[0]:
        raise AssertionError("the frozen training set reaches into the test years")

    frozen = fit_linear(frozen_train)
    frozen_coefficients = {
        "train_years": list(FROZEN_TRAIN_YEARS),
        "train_n": int(len(frozen_train)),
        "slope": round(float(frozen.coef_[0]), 6),
        "intercept": round(float(frozen.intercept_), 6),
    }

    rows = []
    district_rows = []
    for year in FROZEN_TEST_YEARS:
        test = frame[frame["year"].eq(year)].copy()
        if len(test) != COUNTS[year]:
            raise AssertionError(f"the {year} test set does not match the cohort")
        baseline_train = frame[frame["year"].isin(BASELINE_TRAIN_YEARS[year])].copy()
        if baseline_train["year"].max() >= year:
            raise AssertionError("the baseline training set reaches into the test year")
        baseline = fit_linear(baseline_train)

        test["frozen_pred"] = frozen.predict(test[["primary_rep_share"]]).clip(0, 1)
        test["baseline_pred"] = baseline.predict(test[["primary_rep_share"]]).clip(0, 1)
        test["frozen_signed"] = test["frozen_pred"] - test["general_rep_share"]
        test["baseline_signed"] = test["baseline_pred"] - test["general_rep_share"]
        test["prediction_change"] = test["baseline_pred"] - test["frozen_pred"]

        for name, prediction in (("frozen-2016-2018", "frozen_pred"), ("baseline", "baseline_pred")):
            entry = {
                "test_year": int(year),
                "model": name,
                "train_years": list(
                    FROZEN_TRAIN_YEARS if name == "frozen-2016-2018" else BASELINE_TRAIN_YEARS[year]
                ),
                "train_n": int(
                    len(frozen_train) if name == "frozen-2016-2018" else len(baseline_train)
                ),
                "slope": round(
                    float(frozen.coef_[0] if name == "frozen-2016-2018" else baseline.coef_[0]), 6
                ),
                "intercept": round(
                    float(
                        frozen.intercept_
                        if name == "frozen-2016-2018"
                        else baseline.intercept_
                    ),
                    6,
                ),
            }
            entry.update(_metrics(test, prediction))
            rows.append(entry)
        district_rows.append(test)

    summary = pd.DataFrame(rows)
    districts = pd.concat(district_rows, ignore_index=True)

    # The retraining effect: the same 238 contests of 2022, two models.
    paired_rows = []
    for year in FROZEN_TEST_YEARS:
        part = districts[districts["year"].eq(year)]
        delta_mae = part["baseline_signed"].abs().to_numpy() - part["frozen_signed"].abs().to_numpy()
        delta_pred = part["prediction_change"].to_numpy()
        interval = state_interval(
            delta_mae, part["state"].to_numpy(), seed=seed + year
        )
        paired_rows.append(
            {
                "test_year": int(year),
                "n": int(len(part)),
                "same_contests_for_both_models": True,
                "mae_frozen": float(part["frozen_signed"].abs().mean()),
                "mae_baseline": float(part["baseline_signed"].abs().mean()),
                "mae_difference_baseline_minus_frozen": float(delta_mae.mean()),
                "mae_difference_ci95_state_bootstrap": interval,
                "mean_prediction_change": float(delta_pred.mean()),
                "prediction_change_abs_mean": float(np.abs(delta_pred).mean()),
                "prediction_change_min": float(delta_pred.min()),
                "prediction_change_max": float(delta_pred.max()),
                "contests_where_prediction_changed": int((delta_pred != 0).sum()),
                "mean_signed_frozen": float(part["frozen_signed"].mean()),
                "mean_signed_baseline": float(part["baseline_signed"].mean()),
            }
        )
    paired = pd.DataFrame(paired_rows)

    meta = {
        "analysis": "frozen-temporal-transfer-v1",
        "study": "official FEC 2016/2018/2020/2022, 916 selected House voting records",
        "frozen_model": frozen_coefficients,
        "frozen_model_note": (
            "fitted on 2016 and 2018 only; the 2020 and 2022 labels never reach "
            "its coefficients"
        ),
        "year_effect": (
            "the mean signed residual of the unchanged frozen model in 2020 and "
            "in 2022; it cannot be caused by retraining"
        ),
        "retraining_effect": (
            "the difference of the two predictions on the identical 2022 "
            "contests; it is caused by the additional 2020 training year"
        ),
        "no_causal_claim": True,
        "not_a_confirmatory_holdout": (
            "2022 was already inspected during the exploratory work; the two test "
            "years do not share the same selected contests or state composition"
        ),
        "state_bootstrap": {
            "iterations": 4000,
            "seed_rule": "20261025 + test_year",
            "warning": "exploratory; conditional on non-random selected districts",
        },
        "paired": paired_rows,
    }
    return summary, districts, {**meta, "paired_frame": paired}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/elections.csv"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/frozen_transfer")
    )
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument(
        "--assert-baseline",
        action="store_true",
        help="check that the current baseline metrics are reproduced",
    )
    args = parser.parse_args()

    data = prepare_elections(pd.read_csv(args.input, dtype={"state": str, "district": str}))
    summary, districts, meta = evaluate(data, seed=args.seed)

    if args.assert_baseline:
        if sum(COUNTS.values()) != 916:
            raise AssertionError("the frozen 916-record cohort changed")
        for year, expected in BASELINE_CHECKS.items():
            row = summary[(summary["test_year"].eq(year)) & (summary["model"].eq("baseline"))]
            if row.empty:
                raise AssertionError(f"the baseline row for {year} is missing")
            mae = float(row["mae"].iloc[0])
            signed = float(row["mean_signed"].iloc[0])
            if abs(mae - expected["mae"]) > 0.0001:
                raise AssertionError(
                    f"the {year} baseline MAE changed: {mae:.4f} != {expected['mae']:.4f}"
                )
            if abs(signed - expected["mean_signed"]) > 0.0001:
                raise AssertionError(
                    f"the {year} baseline mean signed residual changed: "
                    f"{signed:.4f} != {expected['mean_signed']:.4f}"
                )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_dir / "frozen_temporal_transfer.csv", index=False)
    meta["paired_frame"].to_csv(args.output_dir / "frozen_temporal_transfer_paired.csv", index=False)
    districts[
        [
            "year", "state", "district", "primary_rep_share", "general_rep_share",
            "frozen_pred", "baseline_pred", "frozen_signed", "baseline_signed",
            "prediction_change",
        ]
    ].to_csv(args.output_dir / "frozen_temporal_transfer_districts.csv", index=False)
    payload = {key: value for key, value in meta.items() if key != "paired_frame"}
    (args.output_dir / "frozen_temporal_transfer.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print()
    print(
        meta["paired_frame"].drop(columns=["same_contests_for_both_models"]).to_string(
            index=False, float_format=lambda value: f"{value:.4f}"
        )
    )
    print("Saved:", args.output_dir / "frozen_temporal_transfer.csv")


if __name__ == "__main__":
    main()
