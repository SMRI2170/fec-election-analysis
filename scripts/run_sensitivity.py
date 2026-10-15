"""Compare how excluding contests with small party primary totals changes evaluation.

Threshold comparisons have different target populations; never equate higher
accuracy with general superiority without accounting for sample selection.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
from analyze import evaluate


def compare_thresholds(df: pd.DataFrame, test_year: int, thresholds: list[int]) -> pd.DataFrame:
    if not thresholds or any(x < 0 for x in thresholds) or len(set(thresholds)) != len(thresholds):
        raise ValueError("Thresholds must be unique nonnegative integers")
    outputs = []
    for threshold in thresholds:
        eligible = df[
            (df["primary_rep_votes"] >= threshold) &
            (df["primary_dem_votes"] >= threshold)
        ]
        metrics = evaluate(eligible, test_year)
        metrics.insert(0, "min_each_party_primary_votes", threshold)
        outputs.append(metrics)
    return pd.concat(outputs, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sensitivity of time-split FEC metrics to sample thresholds")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--test-year", type=int, default=2022)
    parser.add_argument("--thresholds", type=int, nargs="+", default=[0, 1000, 5000, 10000])
    parser.add_argument("--output", type=Path, default=Path("data/processed/sensitivity_metrics.csv"))
    args = parser.parse_args()
    df = pd.read_csv(args.input, dtype={"state": str, "district": str})
    scores = compare_thresholds(df, args.test_year, args.thresholds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(args.output, index=False)
    print(scores.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("Saved:", args.output)


if __name__ == "__main__":
    main()
