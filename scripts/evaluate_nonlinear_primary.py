"""Run the pre-registered non-linear comparison (#62).

The comparison setup is **not** decided here. It is read from
``configs/nonlinear-comparison.json``, which was frozen in
[#61](https://github.com/SMRI2170/fec-election-analysis/issues/61) before any
test year was scored. This script only executes that configuration and reports
the result of **every** candidate model, including the ones that are worse
than the linear reference.

Five models are compared on the same out-of-year districts:

| model | family | fitted |
| --- | --- | --- |
| `constant-mean` | the training-set mean of the target | yes |
| `primary-carryover` | the Primary share used as the prediction | no |
| `linear` | ordinary least squares (the reference) | yes |
| `polynomial2-ridge` | quadratic basis, standardized, ridge penalty | yes |
| `cubic-spline-ridge` | cubic B-spline on fixed knots, standardized, ridge penalty | yes |

Every model sees the same single feature (the Primary two-party Republican
share), the same training years and the same predictions are clipped to the
unit interval before they are scored.

The target column is only read while a model is fitted and while a finished
prediction is scored. The feature side never contains a General column, so no
hindsight path exists; :func:`nonlinear_protocol.assert_no_label_access`
guards the tuning phase.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nonlinear_protocol import (  # noqa: E402
    EvaluationPlan,
    assert_no_label_access,
    build_plan,
    clip_predictions,
    design_transformer,
    fitting_rows,
    load_config,
    model_spec,
)
from fec_analysis.core import prepare_elections  # noqa: E402

#: The frozen baseline of the linear reference model, from
#: ``data/processed/backtest_metrics.csv``. The reference model of this
#: comparison has to reproduce it exactly, otherwise the comparison would not
#: be the same measurement as the frozen backtest.
FROZEN_LINEAR_MAE = {
    2018: 0.04415746508763495,
    2020: 0.054936208613780235,
    2022: 0.05016777648573961,
}
#: The frozen baseline of the two non-fitted references of ``analyze.evaluate``.
FROZEN_MEAN_MAE = {
    2018: 0.13267294966973564,
    2020: 0.1398062758375418,
    2022: 0.14087496490489462,
}
FROZEN_CARRYOVER_MAE = {
    2018: 0.0628518903589067,
    2020: 0.07838882292234665,
    2022: 0.0750424587137547,
}


def build_estimator(spec: dict) -> object | None:
    """Return the estimator of one model family.

    ``None`` means that the model has no fitted parameter, which is the case
    of ``primary-carryover``: the Primary share is the prediction itself.
    """
    family = spec["family"]
    hyperparameters = spec.get("hyperparameters", {})
    if family == "constant":
        return DummyRegressor(strategy="mean")
    if family == "identity":
        return None
    if family == "linear":
        return LinearRegression()
    if family in ("polynomial_ridge", "spline_ridge"):
        transformer = design_transformer(spec)
        steps = []
        if transformer is not None:
            steps.append(("design", transformer))
        if bool(hyperparameters.get("standardize", True)):
            steps.append(("scale", StandardScaler()))
        steps.append(
            ("model", Ridge(alpha=float(hyperparameters.get("alpha", 1.0))))
        )
        return Pipeline(steps)
    raise ValueError(f"unknown model family: {family}")


def predict_with(
    spec: dict, train: pd.DataFrame, test: pd.DataFrame, plan: EvaluationPlan
) -> np.ndarray:
    """Fit one model on the training years and predict the test year."""
    feature = plan.feature_column
    target = plan.target_column
    estimator = build_estimator(spec)
    if estimator is None:
        # The carry-over model has no fitted parameter: the Primary share is
        # the prediction. No target column is read at all.
        raw = test[feature].to_numpy(dtype=float)
    else:
        estimator.fit(train[[feature]].to_numpy(dtype=float), train[target].to_numpy(dtype=float))
        raw = estimator.predict(test[[feature]].to_numpy(dtype=float))
    return clip_predictions(np.asarray(raw, dtype=float), plan)


def score_predictions(
    prediction: np.ndarray, actual: np.ndarray
) -> dict[str, float]:
    """Score one model on one test year.

    Every number is a percentage point of the two-party share.
    """
    signed = (np.asarray(prediction, dtype=float) - np.asarray(actual, dtype=float)) * 100
    absolute = np.abs(signed)
    return {
        "mae_points": float(absolute.mean()),
        "rmse_points": float(np.sqrt((signed**2).mean())),
        "p95_abs_error_points": float(np.quantile(absolute, 0.95)),
        "mean_signed_points": float(signed.mean()),
        "median_signed_points": float(np.median(signed)),
        "p05_signed_points": float(np.quantile(signed, 0.05)),
        "p25_signed_points": float(np.quantile(signed, 0.25)),
        "p75_signed_points": float(np.quantile(signed, 0.75)),
        "p95_signed_points": float(np.quantile(signed, 0.95)),
        "min_signed_points": float(signed.min()),
        "max_signed_points": float(signed.max()),
    }


def state_bootstrap_interval(
    delta: np.ndarray,
    states: np.ndarray,
    seed: int,
    repetitions: int,
) -> list[float]:
    """Percentile interval of a paired difference, resampled over states.

    The districts of one state share the electoral rules and the candidate
    pool, so the districts are not independent. The interval is **exploratory**:
    it is conditional on a non-randomly selected set of districts.
    """
    if len(delta) != len(states) or len(delta) == 0:
        raise ValueError("paired records are required")
    part = pd.DataFrame(
        {"state": np.asarray(states).astype(str), "d": np.asarray(delta, dtype=float)}
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


def evaluate_year(
    frame: pd.DataFrame, config: dict, plan: EvaluationPlan
) -> tuple[list[dict], list[dict], list[dict]]:
    """Score every model of the configuration on one test year."""
    train = fitting_rows(frame, plan)
    test = frame[frame["year"].astype(int).eq(plan.test_year)].copy()
    if test.empty:
        raise ValueError(f"no test rows for {plan.test_year}")
    # The tuning phase may not see the target column. The hyperparameters of
    # this protocol are fixed constants, so the phase only has to be present.
    assert_no_label_access([plan.feature_column], "tuning")
    if plan.target_column in (plan.feature_column,):
        raise AssertionError("the feature column must not be the target column")

    rows: list[dict] = []
    predictions: list[dict] = []
    for name in plan.models:
        spec = model_spec(config, name)
        prediction = predict_with(spec, train, test, plan)
        metrics = score_predictions(prediction, test[plan.target_column].to_numpy(dtype=float))
        rows.append(
            {
                "test_year": plan.test_year,
                "model": name,
                "family": spec["family"],
                "fitted": bool(spec.get("fitted", True)),
                "n_train": int(len(train)),
                "n_test": int(len(test)),
                "train_years": list(plan.train_years),
                "train_max_year": int(train["year"].astype(int).max()),
                **metrics,
            }
        )
        part = test[["year", "state", "district", "election_id"]].copy()
        part["model"] = name
        part["prediction"] = prediction
        part["actual"] = test[plan.target_column].to_numpy(dtype=float)
        part["signed_error_points"] = (prediction - part["actual"].to_numpy(dtype=float)) * 100
        part["abs_error_points"] = np.abs(part["signed_error_points"])
        predictions.append(part)
    return rows, predictions, []


def paired_against_reference(
    predictions: list[pd.DataFrame], config: dict, plan: EvaluationPlan
) -> list[dict]:
    """Compare every model with the reference model on the same districts."""
    reference_name = plan.reference_model
    frames = {frame["model"].iloc[0]: frame for frame in predictions}
    if reference_name not in frames:
        raise KeyError(f"the reference model {reference_name} was not scored")
    reference = frames[reference_name].set_index("election_id")
    rows: list[dict] = []
    for name in plan.models:
        if name == reference_name:
            continue
        other = frames[name].set_index("election_id")
        if set(reference.index) != set(other.index):
            raise AssertionError("the compared models do not share the districts")
        common = reference.index
        delta = (
            other.loc[common, "abs_error_points"].to_numpy()
            - reference.loc[common, "abs_error_points"].to_numpy()
        )
        states = reference.loc[common, "state"].to_numpy()
        interval = state_bootstrap_interval(
            delta, states, plan.bootstrap_seed, plan.bootstrap_repetitions
        )
        rows.append(
            {
                "test_year": plan.test_year,
                "model": name,
                "reference": reference_name,
                "n": int(len(common)),
                "mae_reference_points": float(reference.loc[common, "abs_error_points"].mean()),
                "mae_model_points": float(other.loc[common, "abs_error_points"].mean()),
                "mae_difference_points": float(delta.mean()),
                "difference_ci95_state_bootstrap": interval,
                "districts_improved": int((delta < 0).sum()),
                "districts_worsened": int((delta > 0).sum()),
                "districts_unchanged": int((delta == 0).sum()),
                "interval_status": "exploratory; conditional on a non-random selected set of districts",
            }
        )
    return rows


def run_comparison(frame: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Run the whole comparison of the frozen configuration."""
    test_years = [int(year) for year in config["evaluation"]["test_years"]]
    summary_rows: list[dict] = []
    prediction_frames: list[pd.DataFrame] = []
    paired_rows: list[dict] = []
    fits: list[dict] = []
    for year in test_years:
        plan = build_plan(config, year)
        rows, predictions, _ = evaluate_year(frame, config, plan)
        summary_rows.extend(rows)
        prediction_frames.extend(predictions)
        paired_rows.extend(paired_against_reference(predictions, config, plan))
        for row in rows:
            fits.append(
                {
                    "test_year": row["test_year"],
                    "model": row["model"],
                    "n_train": row["n_train"],
                    "n_test": row["n_test"],
                    "train_max_year": row["train_max_year"],
                }
            )
    summary = pd.DataFrame(summary_rows)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    paired = pd.DataFrame(paired_rows)
    meta = {
        "analysis": "nonlinear-primary-comparison-v1",
        "protocol_version": config.get("protocol_version"),
        "protocol_frozen_at": config.get("frozen_at"),
        "config_path": "configs/nonlinear-comparison.json",
        "study": "official FEC 2016/2018/2020/2022, 916 selected House voting records",
        "models": {
            str(spec["name"]): str(spec["family"]) for spec in config["models"]
        },
        "reference_model": config["evaluation"]["reference_model"],
        "primary_metric": config["evaluation"]["primary_metric"],
        "metric_unit": config["evaluation"]["metric_unit"],
        "prediction_clip": config["evaluation"]["prediction_clip"],
        "hyperparameters": "fixed constants; no search, grid or tuning step",
        "fits": fits,
        "no_causal_claim": True,
        "exploratory_2022": config["evaluation"]["test_year_2022_status"],
        "bootstrap": {
            "repetitions": config["evaluation"]["bootstrap"]["repetitions"],
            "seed": config["evaluation"]["bootstrap"]["seed"],
            "unit": config["evaluation"]["bootstrap"]["unit"],
            "interval": config["evaluation"]["bootstrap"]["interval"],
            "status": "exploratory; the districts are not a random sample",
        },
    }
    return summary, predictions, paired, meta


def check_frozen_baselines(summary: pd.DataFrame) -> list[dict]:
    """Check that the three reference rows reproduce the frozen backtest."""
    checks: list[dict] = []
    expectations = {
        "linear": FROZEN_LINEAR_MAE,
        "constant-mean": FROZEN_MEAN_MAE,
        "primary-carryover": FROZEN_CARRYOVER_MAE,
    }
    for model, expected in expectations.items():
        for year, value in expected.items():
            row = summary[
                summary["test_year"].eq(year) & summary["model"].eq(model)
            ]
            if row.empty:
                raise AssertionError(f"the {model} row of {year} is missing")
            measured = float(row["mae_points"].iloc[0]) / 100
            if abs(measured - value) > 1e-12:
                raise AssertionError(
                    f"the {model} MAE of {year} does not match the frozen value: "
                    f"{measured!r} != {value!r}"
                )
            checks.append(
                {
                    "test_year": year,
                    "model": model,
                    "frozen_mae": value,
                    "measured_mae": measured,
                    "difference": measured - value,
                }
            )
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=Path("data/processed/elections.csv")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/nonlinear_comparison")
    )
    parser.add_argument(
        "--assert-baseline",
        action="store_true",
        help="check that the reference models reproduce the frozen backtest",
    )
    args = parser.parse_args()

    config = load_config()
    raw = pd.read_csv(args.input, dtype={"state": str, "district": str})
    frame = prepare_elections(raw)
    frame = frame[frame["chamber"].eq("House")].copy()
    if len(frame) != 916:
        raise AssertionError("the frozen 916-record cohort changed")

    summary, predictions, paired, meta = run_comparison(frame, config)

    if args.assert_baseline:
        meta["frozen_baseline_checks"] = check_frozen_baselines(summary)
        for year in sorted(summary["test_year"].unique()):
            part = summary[summary["test_year"].eq(year)]
            if part["n_test"].nunique() != 1:
                raise AssertionError(f"the models of {year} do not share the same n")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_dir / "nonlinear_comparison.csv", index=False)
    paired.to_csv(args.output_dir / "nonlinear_comparison_paired.csv", index=False)
    predictions.to_csv(args.output_dir / "nonlinear_comparison_districts.csv", index=False)
    (args.output_dir / "nonlinear_comparison.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    columns = [
        "test_year",
        "model",
        "n_train",
        "n_test",
        "mae_points",
        "rmse_points",
        "p95_abs_error_points",
        "mean_signed_points",
    ]
    print(summary[columns].to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print()
    print(
        paired[
            [
                "test_year",
                "model",
                "n",
                "mae_reference_points",
                "mae_model_points",
                "mae_difference_points",
                "districts_improved",
                "districts_worsened",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:.4f}")
    )
    print("Saved:", args.output_dir / "nonlinear_comparison.csv")


if __name__ == "__main__":
    main()
