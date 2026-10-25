"""Evaluate the frozen 2024 plan (#54).

The script executes the plan of
[#53](https://github.com/SMRI2170/fec-election-analysis/issues/53) and nothing
else: the model set, the hyperparameters, the preprocessing, the metric and the
bootstrap settings are read from ``configs/frozen-2024-evaluation.json``.

If the 2024 source or the normalised 2024 file is missing, the script stops
with a documented reason and **produces no value**.

The classification metrics use the two-party vote lead as the label. That
label is a vote lead and **not** a certified election winner.
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
from sklearn.preprocessing import PolynomialFeatures, SplineTransformer, StandardScaler

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

from frozen_2024_protocol import build_plan, load_config  # noqa: E402
from fec_analysis.core import prepare_elections  # noqa: E402


class EvaluationUnavailable(RuntimeError):
    """Raised when the frozen evaluation cannot be executed."""


def build_estimator(spec: dict) -> object | None:
    """Return the estimator of one model family, or ``None`` for the identity."""
    family = spec["family"]
    hyperparameters = spec.get("hyperparameters", {})
    if family == "constant":
        return DummyRegressor(strategy="mean")
    if family == "identity":
        return None
    if family == "linear":
        return LinearRegression()
    if family == "polynomial_ridge":
        steps = [
            (
                "design",
                PolynomialFeatures(
                    degree=int(hyperparameters["degree"]), include_bias=False
                ),
            ),
            ("scale", StandardScaler()),
            ("model", Ridge(alpha=float(hyperparameters["alpha"]))),
        ]
        return Pipeline(steps)
    if family == "spline_ridge":
        knots = np.asarray(hyperparameters["knots"], dtype=float).reshape(-1, 1)
        transformer = SplineTransformer(
            n_knots=int(hyperparameters["n_knots"]),
            degree=int(hyperparameters["degree"]),
            knots=knots,
            include_bias=bool(hyperparameters.get("include_bias", False)),
            extrapolation="constant",
        )
        transformer.fit(np.array([[0.0], [1.0]]))
        return Pipeline(
            [
                ("design", transformer),
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=float(hyperparameters["alpha"]))),
            ]
        )
    raise ValueError(f"unknown model family: {family}")


def predict_with(
    spec: dict, train: pd.DataFrame, test: pd.DataFrame, feature: str, target: str
) -> np.ndarray:
    """Fit one model on the frozen cohort and predict the 2024 contests."""
    estimator = build_estimator(spec)
    if estimator is None:
        raw = test[feature].to_numpy(dtype=float)
    else:
        estimator.fit(
            train[[feature]].to_numpy(dtype=float),
            train[target].to_numpy(dtype=float),
        )
        raw = estimator.predict(test[[feature]].to_numpy(dtype=float))
    return np.asarray(raw, dtype=float)


def score(prediction: np.ndarray, actual: np.ndarray) -> dict[str, float]:
    """Score one model. Every number is a percentage point of the share."""
    signed = (np.asarray(prediction, dtype=float) - np.asarray(actual, dtype=float)) * 100
    absolute = np.abs(signed)
    return {
        "mae_points": float(absolute.mean()),
        "rmse_points": float(np.sqrt((signed**2).mean())),
        "p95_abs_error_points": float(np.quantile(absolute, 0.95)),
        "mean_signed_points": float(signed.mean()),
        "median_signed_points": float(np.median(signed)),
    }


def classification_metrics(prediction: np.ndarray, actual: np.ndarray) -> dict[str, float]:
    """Accuracy and Brier score of the two-party vote lead.

    The label is the two-party vote lead, not a certified election winner.
    """
    predicted_lead = (np.asarray(prediction, dtype=float) > 0.5).astype(float)
    actual_lead = (np.asarray(actual, dtype=float) > 0.5).astype(float)
    return {
        "two_party_lead_accuracy": float((predicted_lead == actual_lead).mean()),
        "brier_score": float(((np.asarray(prediction, dtype=float) - actual_lead) ** 2).mean()),
    }


def state_bootstrap_interval(
    delta: np.ndarray, states: np.ndarray, seed: int, repetitions: int
) -> list[float]:
    """Percentile interval of a paired difference, resampled over states."""
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
    return [
        round(float(value), 6)
        for value in np.quantile(totals / counts, [0.025, 0.975])
    ]


def load_frozen_cohort(path: Path) -> pd.DataFrame:
    """Load the frozen 916-record cohort of 2016-2022."""
    raw = pd.read_csv(path, dtype={"state": str, "district": str})
    frame = prepare_elections(raw)
    frame = frame[frame["chamber"].eq("House")].copy()
    if len(frame) != 916:
        raise EvaluationUnavailable(
            f"the frozen cohort has {len(frame)} rows instead of 916"
        )
    return frame


def load_evaluation_year(path: Path) -> pd.DataFrame:
    """Load the normalised 2024 contests."""
    if not path.exists():
        raise EvaluationUnavailable(
            "there is no normalised 2024 file; run scripts/normalize_fec_2024.py "
            "after the publication becomes available"
        )
    raw = pd.read_csv(path, dtype={"state": str, "district": str})
    frame = prepare_elections(raw)
    frame = frame[frame["chamber"].eq("House")].copy()
    if frame.empty:
        raise EvaluationUnavailable("the normalised 2024 file carries no contest")
    if not (frame["year"].astype(int) == 2024).all():
        raise EvaluationUnavailable("the normalised 2024 file carries another year")
    return frame


def evaluate(
    cohort: pd.DataFrame, evaluation: pd.DataFrame, config: dict
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Run the frozen evaluation."""
    plan = build_plan(config)
    feature = plan.feature_column
    target = plan.target_column
    train = cohort[cohort["year"].astype(int).isin(plan.training_years)].copy()
    if len(train) != 916:
        raise EvaluationUnavailable(
            f"the training set has {len(train)} rows instead of 916"
        )
    if (train["year"].astype(int) == plan.evaluation_year).any():
        raise EvaluationUnavailable(
            "the training set must not contain a row of the evaluation year"
        )
    low, high = plan.clip

    rows: list[dict] = []
    frames: list[pd.DataFrame] = []
    for spec in config["models"]:
        name = str(spec["name"])
        prediction = np.clip(
            predict_with(spec, train, evaluation, feature, target), low, high
        )
        actual = evaluation[target].to_numpy(dtype=float)
        rows.append(
            {
                "evaluation_year": plan.evaluation_year,
                "model": name,
                "family": spec["family"],
                "fitted": bool(spec.get("fitted", True)),
                "n_train": int(len(train)),
                "n_test": int(len(evaluation)),
                **score(prediction, actual),
                **classification_metrics(prediction, actual),
            }
        )
        part = evaluation[["year", "state", "district", "election_id"]].copy()
        part["model"] = name
        part["prediction"] = prediction
        part["actual"] = actual
        part["abs_error_points"] = np.abs((prediction - actual) * 100)
        frames.append(part)

    summary = pd.DataFrame(rows)
    predictions = pd.concat(frames, ignore_index=True)

    paired_rows: list[dict] = []
    for reference_name in ("linear", "primary-carryover"):
        reference = predictions[predictions["model"].eq(reference_name)].set_index(
            "election_id"
        )
        for name in plan.models:
            if name == reference_name:
                continue
            other = predictions[predictions["model"].eq(name)].set_index("election_id")
            if set(reference.index) != set(other.index):
                raise AssertionError("the compared models do not share the contests")
            common = reference.index
            delta = (
                other.loc[common, "abs_error_points"].to_numpy()
                - reference.loc[common, "abs_error_points"].to_numpy()
            )
            states = reference.loc[common, "state"].to_numpy()
            paired_rows.append(
                {
                    "evaluation_year": plan.evaluation_year,
                    "model": name,
                    "reference": reference_name,
                    "n": int(len(common)),
                    "mae_reference_points": float(
                        reference.loc[common, "abs_error_points"].mean()
                    ),
                    "mae_model_points": float(
                        other.loc[common, "abs_error_points"].mean()
                    ),
                    "mae_difference_points": float(delta.mean()),
                    "difference_ci95_state_bootstrap": state_bootstrap_interval(
                        delta, states, plan.bootstrap_seed, plan.bootstrap_repetitions
                    ),
                    "districts_improved": int((delta < 0).sum()),
                    "districts_worsened": int((delta > 0).sum()),
                    "interval_status": "exploratory; conditional on a non-random selected set of contests",
                }
            )
    paired = pd.DataFrame(paired_rows)

    per_state = (
        predictions[predictions["model"].eq("linear")]
        .groupby("state")
        .size()
        .rename("n")
        .reset_index()
    )
    meta = {
        "analysis": "frozen-2024-evaluation-v1",
        "protocol_version": plan.protocol_version,
        "protocol_frozen_at": plan.frozen_at,
        "config_path": "configs/frozen-2024-evaluation.json",
        "evaluation_year": plan.evaluation_year,
        "training_years": list(plan.training_years),
        "n_train": int(len(train)),
        "n_test": int(len(evaluation)),
        "models": list(plan.models),
        "metric_unit": config["metrics"]["metric_unit"],
        "label": "the two-party vote lead, NOT a certified election winner",
        "exploratory_bootstrap": True,
        "no_causal_claim": True,
    }
    return summary, predictions, paired, {"meta": meta, "per_state": per_state}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cohort", type=Path, default=REPO / "data" / "processed" / "elections.csv"
    )
    parser.add_argument(
        "--evaluation",
        type=Path,
        default=REPO / "data" / "processed" / "elections_2024.csv",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=REPO / "data" / "processed" / "frozen_2024"
    )
    parser.add_argument(
        "--assert-frozen-config",
        action="store_true",
        help="check that the plan matches the frozen configuration and the note",
    )
    parser.add_argument(
        "--expect-unavailable",
        action="store_true",
        help="exit with zero when the evaluation correctly refuses to run",
    )
    args = parser.parse_args()

    config = load_config()
    if args.assert_frozen_config:
        from frozen_2024_protocol import run_checks

        run_checks()

    try:
        cohort = load_frozen_cohort(args.cohort)
        evaluation = load_evaluation_year(args.evaluation)
    except EvaluationUnavailable as error:
        print(f"The frozen 2024 evaluation stops: {error}", file=sys.stderr)
        print(
            json.dumps(
                {"status": "not-evaluated", "reason": str(error), "values": None},
                ensure_ascii=False,
                indent=2,
            )
        )
        if args.expect_unavailable:
            raise SystemExit(0) from error
        raise SystemExit(2) from error

    summary, predictions, paired, extra = evaluate(cohort, evaluation, config)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_dir / "frozen_2024_summary.csv", index=False)
    paired.to_csv(args.output_dir / "frozen_2024_paired.csv", index=False)
    predictions.to_csv(args.output_dir / "frozen_2024_districts.csv", index=False)
    extra["per_state"].to_csv(args.output_dir / "frozen_2024_per_state.csv", index=False)
    (args.output_dir / "frozen_2024.json").write_text(
        json.dumps(extra["meta"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print()
    print(
        paired[
            [
                "model",
                "reference",
                "n",
                "mae_reference_points",
                "mae_model_points",
                "mae_difference_points",
                "districts_improved",
                "districts_worsened",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:.4f}")
    )
    print("Saved:", args.output_dir / "frozen_2024_summary.csv")


if __name__ == "__main__":
    main()
