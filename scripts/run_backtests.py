"""Chronological out-of-year backtests for normalized FEC House records.

Every test year is evaluated with only older election years as training data.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from analyze import evaluate


def run_backtests(df: pd.DataFrame, test_years: list[int]) -> pd.DataFrame:
    tables = []
    for year in test_years:
        result = evaluate(df, year, "House")
        result.insert(0, "test_year", year)
        tables.append(result)
    return pd.concat(tables, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chronological FEC election model evaluation")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--test-years", nargs="+", type=int, default=[2018, 2020, 2022])
    parser.add_argument("--output", type=Path, default=Path("data/processed/backtest_metrics.csv"))
    args = parser.parse_args()
    df = pd.read_csv(args.input, dtype={"state": str, "district": str})
    if len(set(args.test_years)) != len(args.test_years):
        parser.error("Duplicate test years")
    if not set(args.test_years).issubset(set(df["year"])):
        parser.error("All test years must be present in input")
    scores = run_backtests(df, args.test_years)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(args.output, index=False)
    print(scores.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print("Saved:", args.output)


if __name__ == "__main__":
    main()
