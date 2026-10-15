"""Identify large 2022 prediction misses without inferring their cause."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fec_analysis.core import prepare_elections


def error_report(raw: pd.DataFrame, test_year: int = 2022) -> pd.DataFrame:
    prepared = prepare_elections(raw)
    df = prepared[prepared["chamber"] == "House"]
    train = df[df["year"] < test_year]
    test = df[df["year"] == test_year].copy()
    if train.empty or test.empty or train["general_rep_win"].nunique() < 2:
        raise ValueError("Time-split or classification class balance is invalid")
    feature = ["primary_rep_share"]
    linear = LinearRegression().fit(train[feature], train["general_rep_share"])
    logistic = LogisticRegression(random_state=0, max_iter=1000).fit(train[feature], train["general_rep_win"])
    test["linear_pred_share"] = linear.predict(test[feature]).clip(0, 1)
    test["abs_linear_error"] = (test["general_rep_share"] - test["linear_pred_share"]).abs()
    test["primary_rule_win"] = (test["primary_rep_share"] > 0.5).astype(int)
    test["logistic_pred_win"] = logistic.predict(test[feature])
    test["primary_rule_error"] = test["primary_rule_win"] != test["general_rep_win"]
    test["logistic_error"] = test["logistic_pred_win"] != test["general_rep_win"]
    columns = [
        "year", "state", "district", "primary_rep_share", "general_rep_share",
        "linear_pred_share", "abs_linear_error", "general_rep_win",
        "primary_rule_win", "logistic_pred_win", "primary_rule_error", "logistic_error",
        "source_file", "source_sheet",
    ]
    return test[columns].sort_values("abs_linear_error", ascending=False).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank out-of-year election prediction errors")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--test-year", type=int, default=2022)
    parser.add_argument("--output", type=Path, default=Path("data/processed/errors_2022.csv"))
    args = parser.parse_args()
    data = pd.read_csv(args.input, dtype={"state": str, "district": str})
    results = error_report(data, args.test_year)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False)
    print("Classification disagreements: primary rule =", int(results["primary_rule_error"].sum()), 
          "; logistic =", int(results["logistic_error"].sum()))
    print("Top 10 linear share errors:")
    print(results[["state", "district", "primary_rep_share", "general_rep_share", "linear_pred_share", "abs_linear_error", "primary_rule_error", "logistic_error"]].head(10).to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("Saved:", args.output)


if __name__ == "__main__":
    main()
