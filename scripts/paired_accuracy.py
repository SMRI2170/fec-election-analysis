"""Paired exact McNemar test and bootstrap uncertainty on identical elections."""
from __future__ import annotations
import argparse
import json
from math import comb
from pathlib import Path
import numpy as np
import pandas as pd

def compare_predictions(df: pd.DataFrame, repetitions: int = 10000, seed: int = 20261015) -> dict:
    for name in ("primary_rule_error", "logistic_error"):
        if name not in df:
            raise ValueError(f"Missing {name}")
        if df[name].isna().any():
            raise ValueError(f"{name} contains missing values")
        if not df[name].isin([0, 1, True, False]).all():
            raise ValueError(f"{name} must be binary")
    a = df["primary_rule_error"].astype(bool).to_numpy()
    b = df["logistic_error"].astype(bool).to_numpy()
    if len(a) == 0 or repetitions < 1:
        raise ValueError("Empty data or nonpositive bootstrap count")
    b_only_wrong = int((~a & b).sum())
    a_only_wrong = int((a & ~b).sum())
    n = b_only_wrong + a_only_wrong
    tail = sum(comb(n, i) for i in range(min(b_only_wrong, a_only_wrong) + 1))
    exact_p = min(1.0, 2.0 * tail / 2 ** n) if n else 1.0
    accuracy_delta = (~a).astype(float) - (~b).astype(float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(df), size=(repetitions, len(df)))
    low, high = np.quantile(accuracy_delta[indices].mean(axis=1), [0.025, 0.975])
    # Sensitivity: resample STATES (not individual districts) to account for
    # potential within-state dependence in the exploratory uncertainty range.
    state_ci = None
    if "state" in df.columns and not df["state"].isna().any():
        state_summaries = pd.DataFrame({
            "state": df["state"].astype(str).to_numpy(), "delta": accuracy_delta
        }).groupby("state")["delta"].agg(["sum", "count"])
        if len(state_summaries) >= 2:
            draw = rng.integers(0, len(state_summaries), size=(repetitions, len(state_summaries)))
            totals = state_summaries["sum"].to_numpy()[draw].sum(axis=1)
            weights = state_summaries["count"].to_numpy()[draw].sum(axis=1)
            state_ci = [float(v) for v in np.quantile(totals / weights, [0.025, 0.975])]
    return {
        "n": len(df),
        "rule_errors": int(a.sum()),
        "logistic_errors": int(b.sum()),
        "both_wrong": int((a & b).sum()),
        "rule_only_wrong": a_only_wrong,
        "logistic_only_wrong": b_only_wrong,
        "accuracy_rule": float((~a).mean()),
        "accuracy_logistic": float((~b).mean()),
        "accuracy_difference_rule_minus_logistic": float(accuracy_delta.mean()),
        "bootstrap_paired_95pct_interval": [float(low), float(high)],
        "mcnemar_exact_two_sided_p": float(exact_p),
        "state_cluster_bootstrap_95pct_interval": state_ci,
        "bootstrap_iterations": repetitions,
        "seed": seed,
        "exploratory": True,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Paired accuracy and uncertainty")
    parser.add_argument("--input", type=Path, default=Path("data/processed/errors_2022.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/paired-accuracy.json"))
    args = parser.parse_args()
    result = compare_predictions(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
