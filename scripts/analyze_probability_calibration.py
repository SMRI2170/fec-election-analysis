"""Calibration of the Primary-share logistic model (#64).

The selective study (#78-#82) answers *which* contests are hard to predict.
This script answers the complementary question: **when the model outputs a
probability, how often is that probability right?**

For each test year the logistic model is trained on the earlier years only,
with the Primary two-party share as the single feature, and the predicted
probability of a Republican two-party lead is compared with the observed
outcome on the test year. The reported quantities are:

* the Brier score and the log loss (overall accuracy of the probabilities),
* a reliability table: for each probability bin, the number of contests, the
  mean predicted probability and the observed rate,
* the expected and maximum calibration error,
* the gap between the mean predicted probability and the observed base rate.

The observed outcome of the test year is used only to score predictions that
were already fixed; it never enters the model, the bin edges or any
parameter. The majority-vote rule has no probability output and is therefore
not part of this analysis.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fec_analysis.core import prepare_elections

#: Number of fixed-width probability bins for the reliability table.
N_BINS = 10
#: Bins with fewer contests than this are reported but flagged as thin.
THIN_BIN = 5


def fit_predict(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """Fit the Primary-share logistic model and score the test year."""
    if train.empty or test.empty:
        raise ValueError("train/test is empty")
    if train["general_rep_win"].nunique() < 2:
        raise ValueError("training set needs both winner classes")
    model = LogisticRegression(random_state=0, max_iter=1000)
    model.fit(train[["primary_rep_share"]], train["general_rep_win"])
    probability = model.predict_proba(test[["primary_rep_share"]])[
        :, list(model.classes_).index(1)
    ]
    return probability, test["general_rep_win"].to_numpy(dtype=int)


def reliability_table(
    observed: np.ndarray, probability: np.ndarray, n_bins: int = N_BINS
) -> pd.DataFrame:
    """Bin the predicted probabilities and compare them with the outcomes."""
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    index = np.clip(np.digitize(probability, edges[1:-1], right=False), 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = index == b
        count = int(mask.sum())
        if count == 0:
            rows.append(
                {
                    "bin": b,
                    "bin_lower": float(edges[b]),
                    "bin_upper": float(edges[b + 1]),
                    "n": 0,
                    "mean_predicted": np.nan,
                    "observed_rate": np.nan,
                    "error_rate": np.nan,
                    "absolute_gap": np.nan,
                    "thin": False,
                }
            )
            continue
        mean_predicted = float(probability[mask].mean())
        observed_rate = float(observed[mask].mean())
        rows.append(
            {
                "bin": b,
                "bin_lower": float(edges[b]),
                "bin_upper": float(edges[b + 1]),
                "n": count,
                "mean_predicted": mean_predicted,
                "observed_rate": observed_rate,
                "error_rate": 1.0 - observed_rate,
                "absolute_gap": abs(mean_predicted - observed_rate),
                "thin": count < THIN_BIN,
            }
        )
    return pd.DataFrame(rows)


def calibration_metrics(
    observed: np.ndarray, probability: np.ndarray, table: pd.DataFrame
) -> dict[str, float]:
    """Overall and binned calibration error."""
    filled = table[table["n"] > 0]
    weights = filled["n"] / filled["n"].sum()
    ece = float((weights * filled["absolute_gap"]).sum())
    max_gap = float(filled["absolute_gap"].max()) if len(filled) else 0.0
    return {
        "n": int(len(observed)),
        "brier": float(brier_score_loss(observed, probability)),
        "log_loss": float(log_loss(observed, probability, labels=[0, 1])),
        "mean_predicted": float(probability.mean()),
        "observed_base_rate": float(observed.mean()),
        "calibration_in_the_large": float(probability.mean() - observed.mean()),
        "expected_calibration_error": ece,
        "maximum_calibration_error": max_gap,
        "bins_with_data": int(len(filled)),
        "thin_bins": int(filled["thin"].sum()),
    }


def analyze(
    data: pd.DataFrame, test_years: list[int], chamber: str = "House"
) -> tuple[pd.DataFrame, dict]:
    df = prepare_elections(data)
    df = df[df["chamber"] == chamber].copy()
    tables = []
    summary: dict[str, object] = {
        "chamber": chamber,
        "n_bins": N_BINS,
        "thin_bin_threshold": THIN_BIN,
        "feature": "primary_rep_share",
        "general_used_as_predictor": False,
        "new_model_family": False,
        "per_year": [],
    }
    for year in test_years:
        train = df[(df["year"] < year) & (~df["general_tie"])]
        test = df[(df["year"] == year) & (~df["general_tie"])]
        probability, observed = fit_predict(train, test)
        table = reliability_table(observed, probability)
        table.insert(0, "year", year)
        tables.append(table)
        entry = calibration_metrics(observed, probability, table)
        entry["year"] = int(year)
        entry["n_train"] = int(len(train))
        summary["per_year"].append(entry)
    return pd.concat(tables, ignore_index=True), summary


def plot_reliability(table: pd.DataFrame, summary: dict, png_path: Path, svg_path: Path):
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    for year, group in table.groupby("year"):
        filled = group[group["n"] > 0]
        ax.plot(
            filled["mean_predicted"],
            filled["observed_rate"],
            marker="o",
            markersize=3.4,
            linewidth=1.0,
            label=f"{year} (n={int(filled['n'].sum())})",
        )
    ax.plot([0, 1], [0, 1], linestyle="--", linewidth=0.8, color="0.45", label="perfect")
    ax.set_xlabel("Predicted probability of a Republican two-party lead", fontsize=7)
    ax.set_ylabel("Observed rate", fontsize=7)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.tick_params(labelsize=6)
    ax.legend(fontsize=6.2, loc="upper left")
    ax.grid(alpha=0.25, linewidth=0.5)
    fig.tight_layout()
    fig.savefig(png_path, dpi=150, metadata={"Software": "fec-election-analysis"})
    fig.savefig(svg_path, metadata={"Creator": "fec-election-analysis"})
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--test-years", type=int, nargs="+", default=[2018, 2020, 2022])
    parser.add_argument("--chamber", choices=["House", "Senate"], default="House")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/calibration")
    )
    parser.add_argument(
        "--figure-dir", type=Path, default=Path("outputs/figures")
    )
    args = parser.parse_args()

    data = pd.read_csv(args.input, dtype={"state": str, "district": str})
    table, summary = analyze(data, list(args.test_years), args.chamber)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output_dir / "calibration_bins.csv", index=False)
    (args.output_dir / "calibration_metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    png = args.figure_dir / "calibration_reliability.png"
    svg = args.figure_dir / "calibration_reliability.svg"
    plot_reliability(table, summary, png, svg)

    print(
        table[table["n"] > 0][
            ["year", "bin_lower", "bin_upper", "n", "mean_predicted", "observed_rate"]
        ].to_string(index=False, float_format=lambda x: f"{x:.4f}")
    )
    for entry in summary["per_year"]:
        print(
            f"{entry['year']}: Brier {entry['brier']:.4f}, "
            f"mean predicted {entry['mean_predicted']:.4f}, "
            f"observed {entry['observed_base_rate']:.4f}, "
            f"ECE {entry['expected_calibration_error']:.4f}, "
            f"max gap {entry['maximum_calibration_error']:.4f}"
        )
    print("Saved:", args.output_dir / "calibration_bins.csv")
    print("Saved:", args.output_dir / "calibration_metrics.json")
    print("Saved:", png)


if __name__ == "__main__":
    main()
