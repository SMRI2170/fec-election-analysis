"""Ablate the Primary candidate features on the same out-of-year evaluation (#60).

The frozen cohort carries a single explanatory variable: the Republican
two-party share of the Primary. Issue [#59](https://github.com/SMRI2170/fec-election-analysis/issues/59)
rebuilt the candidate-level structure of the Primary from the official FEC
workbooks. This script asks which of those features carry information beyond
the share itself.

Five pre-declared model groups are compared **on the same evaluation
districts**, with the same pipeline and the same metrics:

| group | columns |
| --- | --- |
| `p_only` | the Primary two-party share (the frozen baseline) |
| `p_candidates` | share + the candidate counts of both parties |
| `p_concentration` | share + the concentration index of both parties |
| `p_log_volume` | share + the log volume of both parties |
| `p_all` | all of the above |

The Republican and the Democratic features are always used **symmetrically**.
The groups were declared before the comparison was run; no group is added
after seeing a result, and a group that does not help is reported as well.

Every pipeline (imputation, scaling, regression) is fitted on the training
years only. The 2022 results were already inspected during the exploratory
work, so the outcome here is **exploratory** and not a predictive claim.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fec_analysis.core import prepare_elections  # noqa: E402

#: The frozen cohort, unchanged by this script.
COUNTS = {2016: 200, 2018: 241, 2020: 237, 2022: 238}
#: The evaluation years and their training years.
TRAIN_YEARS = {2018: (2016,), 2020: (2016, 2018), 2022: (2016, 2018, 2020)}
#: The reference group of the comparison.
REFERENCE_GROUP = "p_only"
#: The pre-declared model groups. The Republican and the Democratic features
#: are always used together, so that the comparison never depends on a single
#: party.
MODEL_GROUPS: dict[str, tuple[str, ...]] = {
    "p_only": ("primary_rep_share",),
    "p_candidates": (
        "primary_rep_share",
        "r_candidates",
        "d_candidates",
    ),
    "p_concentration": (
        "primary_rep_share",
        "r_hhi",
        "d_hhi",
    ),
    "p_log_volume": (
        "primary_rep_share",
        "r_log1p_votes",
        "d_log1p_votes",
    ),
    "p_all": (
        "primary_rep_share",
        "r_candidates",
        "d_candidates",
        "r_hhi",
        "d_hhi",
        "r_log1p_votes",
        "d_log1p_votes",
    ),
}
#: The frozen baseline values of the P-only model, reproduced by this script.
BASELINE_CHECKS = {
    2018: {"mae": 0.0442},
    2020: {"mae": 0.0549},
    2022: {"mae": 0.0502},
}


def build_pipeline() -> Pipeline:
    """The pipeline of every group.

    The imputation and the scaling are inside the pipeline, so that they are
    fitted on the training years only. The scaling does not change the
    predictions of a linear model, which keeps the P-only group equal to the
    frozen baseline.
    """
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", LinearRegression()),
        ]
    )


def state_interval(
    delta: np.ndarray, states: np.ndarray, seed: int, repetitions: int = 4000
) -> list[float]:
    """Cluster bootstrap over states; a diagnostic interval, not a national CI."""
    if len(delta) != len(states) or len(delta) == 0 or repetitions < 100:
        raise ValueError("paired records and at least 100 draws are required")
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


def load_cohort(elections: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Join the frozen cohort with the candidate features, one row per contest."""
    frame = prepare_elections(elections)
    frame = frame[frame["chamber"].eq("House")].copy()
    if len(frame) != sum(COUNTS.values()):
        raise AssertionError("the frozen 916-record cohort changed")
    # The Primary share comes from the cohort itself; the feature table adds
    # the candidate-level columns.
    feature_columns = sorted(
        {
            column
            for group in MODEL_GROUPS.values()
            for column in group
            if column != "primary_rep_share"
        }
    )
    keys = features[["election_id"] + feature_columns].copy()
    # A feature that the schema marks as unusable is not used: for example the
    # candidate count of a party whose primary was unopposed is a lower bound,
    # and the concentration index of a party without a candidate is undefined.
    # The values are masked so that the pipeline imputes them from the
    # training years instead.
    for party in ("r", "d"):
        usable = features[f"{party}_features_usable"].fillna(0).astype(int).eq(1)
        masked = ~usable
        for column in feature_columns:
            if column.startswith(f"{party}_"):
                keys.loc[masked, column] = np.nan
    merged = frame.merge(keys, on="election_id", how="left", validate="one_to_one")
    if len(merged) != len(frame):
        raise AssertionError("the feature join changed the number of rows")
    return merged


def evaluate(frame: pd.DataFrame, seed: int = 20261025) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Score every model group on every evaluation year."""
    rows: list[dict] = []
    predictions: list[pd.DataFrame] = []
    fits: list[dict] = []
    for year, training_years in TRAIN_YEARS.items():
        train = frame[frame["year"].isin(training_years)].copy()
        test = frame[frame["year"].eq(year)].copy()
        if train.empty or test.empty:
            raise ValueError(f"empty train or test set for {year}")
        if train["year"].max() >= year:
            raise AssertionError("the training set reaches into the test year")
        if len(test) != COUNTS[year]:
            raise AssertionError(f"the {year} test set does not match the cohort")
        for name, columns in MODEL_GROUPS.items():
            pipeline = build_pipeline()
            pipeline.fit(train[list(columns)], train["general_rep_share"])
            prediction = np.clip(
                pipeline.predict(test[list(columns)]), 0.0, 1.0
            )
            signed = prediction - test["general_rep_share"].to_numpy(dtype=float)
            part = test[["year", "state", "district", "election_id"]].copy()
            part["model"] = name
            part["prediction"] = prediction
            part["signed"] = signed
            part["abs_error"] = np.abs(signed)
            predictions.append(part)
            rows.append(
                {
                    "test_year": int(year),
                    "model": name,
                    "n": int(len(test)),
                    "train_n": int(len(train)),
                    "train_years": list(training_years),
                    "features": list(columns),
                    "mae": float(np.abs(signed).mean()),
                    "rmse": float(np.sqrt((signed**2).mean())),
                    "mean_signed": float(signed.mean()),
                    "imputed_rows_in_test": int(
                        test[list(columns)].isna().any(axis=1).sum()
                    ),
                }
            )
            fits.append(
                {
                    "test_year": int(year),
                    "model": name,
                    "train_n": int(len(train)),
                    "test_n": int(len(test)),
                    "train_max_year": int(train["year"].max()),
                }
            )
    summary = pd.DataFrame(rows)
    districts = pd.concat(predictions, ignore_index=True)

    # The paired comparison against the reference group, on the same districts.
    paired_rows = []
    for year in TRAIN_YEARS:
        reference = districts[
            districts["year"].eq(year) & districts["model"].eq(REFERENCE_GROUP)
        ].set_index("election_id")
        for name in MODEL_GROUPS:
            if name == REFERENCE_GROUP:
                continue
            other = districts[
                districts["year"].eq(year) & districts["model"].eq(name)
            ].set_index("election_id")
            if set(reference.index) != set(other.index):
                raise AssertionError("the compared models do not share the districts")
            common = reference.index
            delta = (
                other.loc[common, "abs_error"].to_numpy()
                - reference.loc[common, "abs_error"].to_numpy()
            )
            states = reference.loc[common, "state"].to_numpy()
            paired_rows.append(
                {
                    "test_year": int(year),
                    "model": name,
                    "reference": REFERENCE_GROUP,
                    "n": int(len(common)),
                    "mae_reference": float(reference.loc[common, "abs_error"].mean()),
                    "mae_model": float(other.loc[common, "abs_error"].mean()),
                    "mae_difference": float(delta.mean()),
                    "mae_difference_ci95_state_bootstrap": state_interval(
                        delta, states, seed=seed + year
                    ),
                    "districts_improved": int((delta < 0).sum()),
                    "districts_worsened": int((delta > 0).sum()),
                    "districts_unchanged": int((delta == 0).sum()),
                }
            )
    paired = pd.DataFrame(paired_rows)

    meta = {
        "analysis": "primary-feature-ablation-v1",
        "study": "official FEC 2016/2018/2020/2022, 916 selected House voting records",
        "model_groups": {name: list(columns) for name, columns in MODEL_GROUPS.items()},
        "reference_group": REFERENCE_GROUP,
        "pipeline": "SimpleImputer(median) -> StandardScaler -> LinearRegression, fitted on the training years only",
        "symmetry_rule": "the Republican and the Democratic features are always used together",
        "prediction_clip": [0.0, 1.0],
        "metrics": ["MAE", "RMSE", "mean signed residual", "improved and worsened districts"],
        "no_causal_claim": True,
        "exploratory": (
            "the 2022 results were already inspected during the exploratory work; "
            "the best group of 2022 is not a predictive result and the final "
            "evaluation candidate is still to be fixed in #53"
        ),
        "fits": fits,
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
    parser.add_argument("--elections", type=Path, default=Path("data/processed/elections.csv"))
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("data/processed/primary_features/primary_features.csv"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/feature_ablation")
    )
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument(
        "--assert-baseline",
        action="store_true",
        help="check that the P-only group reproduces the frozen baseline",
    )
    args = parser.parse_args()

    elections = pd.read_csv(args.elections, dtype={"state": str, "district": str})
    features = pd.read_csv(args.features, dtype={"state": str, "district": str})
    frame = load_cohort(elections, features)
    summary, districts, meta = evaluate(frame, seed=args.seed)

    if args.assert_baseline:
        for year, expected in BASELINE_CHECKS.items():
            row = summary[
                summary["test_year"].eq(year) & summary["model"].eq(REFERENCE_GROUP)
            ]
            if row.empty:
                raise AssertionError(f"the reference row for {year} is missing")
            mae = float(row["mae"].iloc[0])
            if abs(mae - expected["mae"]) > 0.0001:
                raise AssertionError(
                    f"the {year} P-only MAE changed: {mae:.4f} != {expected['mae']:.4f}"
                )
        # Every group is scored on the same number of contests.
        for year, part in summary.groupby("test_year"):
            if part["n"].nunique() != 1:
                raise AssertionError(f"the groups of {year} do not share the same n")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_dir / "feature_ablation.csv", index=False)
    meta["paired_frame"].to_csv(args.output_dir / "feature_ablation_paired.csv", index=False)
    districts.to_csv(args.output_dir / "feature_ablation_districts.csv", index=False)
    payload = {key: value for key, value in meta.items() if key != "paired_frame"}
    (args.output_dir / "feature_ablation.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print()
    print(
        meta["paired_frame"][
            [
                "test_year",
                "model",
                "n",
                "mae_reference",
                "mae_model",
                "mae_difference",
                "districts_improved",
                "districts_worsened",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:.4f}")
    )
    print("Saved:", args.output_dir / "feature_ablation.csv")


if __name__ == "__main__":
    main()
