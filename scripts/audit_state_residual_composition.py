"""Audit how state/year signed residuals are composed (#63).

The state/year analysis (#57) reports a district-weighted signed residual
per test year. That single number hides *which* states carry it, and how
much of it comes from states with too few selected contests to rank. This
script audits that composition from the outputs of ``analyze_state_year.py``
without creating a new state model:

* the selected contests are split into three groups per year --
  ``n>=5`` (rankable), ``1<=n<5`` (selected but too few) and ``n=0``
  (no selected contest at all),
* every group is reported with its state count, its contest count and its
  share of the contests,
* the district-weighted signed residual is decomposed into the contribution
  of each group, and the share of the aggregate bias that comes from the
  small groups is reported,
* the number of rankable states whose residual has the opposite sign to the
  aggregate is reported, because that is the direct evidence of a
  composition effect.

No new prediction model is fitted here and no General vote of the test year
enters any computation except through the residuals produced by #57.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

#: Minimum selected contests per state for a descriptive state comparison.
MIN_N_FOR_STATE_COMPARISONS = 5

GROUPS = ("n_ge_5", "n_1_to_4", "n_0")


def load_metrics(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {
        "year",
        "state",
        "n",
        "linear_mae",
        "linear_signed_pred_minus_actual",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing columns in {path}: {sorted(missing)}")
    frame = frame.copy()
    frame["year"] = frame["year"].astype(int)
    frame["state"] = frame["state"].astype(str)
    frame["n"] = frame["n"].astype(int)
    return frame


def load_coverage(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"population", "year", "state", "selected"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing columns in {path}: {sorted(missing)}")
    frame = frame[frame["population"] == "50-state-voting-House"].copy()
    frame["year"] = frame["year"].astype(int)
    frame["state"] = frame["state"].astype(str)
    frame["selected"] = frame["selected"].astype(int)
    return frame


def classify(n: int) -> str:
    if n >= MIN_N_FOR_STATE_COMPARISONS:
        return "n_ge_5"
    if n >= 1:
        return "n_1_to_4"
    return "n_0"


def compose(metrics: pd.DataFrame, coverage: pd.DataFrame) -> pd.DataFrame:
    """Return one row per test year and group."""
    rows: list[dict[str, object]] = []
    for year in sorted(metrics["year"].unique()):
        year_metrics = metrics[metrics["year"] == year]
        year_coverage = coverage[coverage["year"] == year]
        total_contests = int(year_metrics["n"].sum())
        total_signed = float(
            (year_metrics["n"] * year_metrics["linear_signed_pred_minus_actual"]).sum()
        )
        aggregate_signed = total_signed / total_contests if total_contests else 0.0

        merged = year_coverage.merge(
            year_metrics[["state", "n", "linear_mae", "linear_signed_pred_minus_actual"]],
            on="state",
            how="outer",
        )
        merged["n"] = merged["n"].fillna(0).astype(int)
        merged["linear_signed_pred_minus_actual"] = merged[
            "linear_signed_pred_minus_actual"
        ].fillna(0.0)
        merged["linear_mae"] = merged["linear_mae"].fillna(0.0)
        merged["group"] = merged["n"].map(classify)

        for group in GROUPS:
            part = merged[merged["group"] == group]
            contests = int(part["n"].sum())
            signed = float(
                (part["n"] * part["linear_signed_pred_minus_actual"]).sum()
            )
            rows.append(
                {
                    "year": year,
                    "group": group,
                    "states": int(len(part)),
                    "contests": contests,
                    "contest_share": contests / total_contests if total_contests else 0.0,
                    "group_signed_bias": signed,
                    "share_of_total_signed_bias": (
                        signed / total_signed if total_signed else 0.0
                    ),
                    "mean_state_mae": (
                        float(part["linear_mae"].mean()) if len(part) else 0.0
                    ),
                    "mean_state_signed_residual": (
                        float(part["linear_signed_pred_minus_actual"].mean())
                        if len(part)
                        else 0.0
                    ),
                    "aggregate_signed_residual": aggregate_signed,
                }
            )
    return pd.DataFrame(rows)


def composition_summary(composition: pd.DataFrame, metrics: pd.DataFrame) -> dict:
    """Aggregate the per-group table into per-year findings."""
    findings: list[dict[str, object]] = []
    for year in sorted(composition["year"].unique()):
        year_rows = composition[composition["year"] == year]
        by_group = {row["group"]: row for _, row in year_rows.iterrows()}
        aggregate = float(by_group["n_ge_5"]["aggregate_signed_residual"])
        rankable = metrics[
            (metrics["year"] == year)
            & (metrics["n"] >= MIN_N_FOR_STATE_COMPARISONS)
        ]
        opposite = int(
            (rankable["linear_signed_pred_minus_actual"] * aggregate < 0).sum()
        )
        small = by_group["n_1_to_4"]
        findings.append(
            {
                "year": int(year),
                "aggregate_signed_residual": aggregate,
                "states_rankable": int(by_group["n_ge_5"]["states"]),
                "states_small": int(by_group["n_1_to_4"]["states"]),
                "states_zero": int(by_group["n_0"]["states"]),
                "contests_total": int(year_rows["contests"].sum()),
                "contests_rankable": int(by_group["n_ge_5"]["contests"]),
                "contests_small": int(small["contests"]),
                "share_of_contests_small": float(small["contest_share"]),
                "share_of_signed_bias_small": float(small["share_of_total_signed_bias"]),
                "rankable_states_opposite_to_aggregate": opposite,
                "rankable_states": int(len(rankable)),
            }
        )
    return {
        "min_n_for_state_comparisons": MIN_N_FOR_STATE_COMPARISONS,
        "general_used_as_predictor": False,
        "new_model_fitted": False,
        "per_year": findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--error-metrics",
        type=Path,
        default=Path("data/processed/state_year/state_year_error_metrics.csv"),
    )
    parser.add_argument(
        "--coverage",
        type=Path,
        default=Path("data/processed/state_year/state_year_coverage.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/state_year/state_residual_composition.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("data/processed/state_year/state_residual_composition.json"),
    )
    args = parser.parse_args()

    metrics = load_metrics(args.error_metrics)
    coverage = load_coverage(args.coverage)
    composition = compose(metrics, coverage)
    summary = composition_summary(composition, metrics)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    composition.to_csv(args.output, index=False)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        composition[
            [
                "year",
                "group",
                "states",
                "contests",
                "contest_share",
                "share_of_total_signed_bias",
            ]
        ].to_string(index=False, float_format=lambda x: f"{x:.4f}")
    )
    for entry in summary["per_year"]:
        print(
            f"{entry['year']}: aggregate signed residual "
            f"{entry['aggregate_signed_residual']:+.4f}, "
            f"rankable states {entry['states_rankable']}, "
            f"opposite-sign rankable states {entry['rankable_states_opposite_to_aggregate']}"
            f"/{entry['rankable_states']}, "
            f"contests in n<5 states {entry['contests_small']} "
            f"({entry['share_of_contests_small']:.2%})"
        )
    print("Saved:", args.output)
    print("Saved:", args.summary)


if __name__ == "__main__":
    main()
