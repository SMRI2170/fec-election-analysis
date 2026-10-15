"""Recreate compact report figures from normalized real-source FEC observations.

Figures must be generated from actual normalized data. Example/toy data
cannot be presented as evidence. The output stays untracked under outputs/.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fec_analysis.core import prepare_elections


def render_figures(
    source: pd.DataFrame,
    backtests: pd.DataFrame,
    output_dir: Path,
    test_year: int = 2022,
) -> list[Path]:
    df = prepare_elections(source)
    df = df[df["chamber"] == "House"].copy()
    train = df[df["year"] < test_year]
    test = df[df["year"] == test_year]
    if train.empty or test.empty:
        raise ValueError("Both prior-year training data and test-year data are required")
    model = LinearRegression().fit(train[["primary_rep_share"]], train["general_rep_share"])
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    # Figure 1: a year-out sample only, not population-wide US results.
    fig, ax = plt.subplots(figsize=(5.3, 4.0))
    ax.scatter(test["primary_rep_share"], test["general_rep_share"], s=16, alpha=0.62,
               label=f"{test_year} House races (n={len(test)})")
    x = np.linspace(0, 1, 100)
    ax.plot(x, x, linestyle=":", linewidth=1.2, label="Same two-party share (y=x)")
    ax.plot(x, model.predict(pd.DataFrame({"primary_rep_share": x})).clip(0, 1),
            linewidth=1.5, label="Linear prediction (prior years)")
    ax.set(xlabel="Primary Republican share (two-party)",
           ylabel="General Republican share (two-party)",
           xlim=(-0.02, 1.02), ylim=(-0.02, 1.02),
           title=f"Primary and general shares: {test_year}")
    ax.grid(alpha=0.2)
    ax.legend(loc="best", fontsize=7)
    fig.tight_layout()
    path = output_dir / f"primary_vs_general_{test_year}.png"
    fig.savefig(path, dpi=150, metadata={"Software": "fec-election-analysis"})
    plt.close(fig)
    paths.append(path)

    # Figure 2: share MAE (lower is better), for independent chronological tests.
    data = backtests[(backtests["task"] == "share") & (backtests["metric"] == "MAE")].copy()
    models = ["mean-share baseline", "primary-share identity", "linear regression"]
    years = sorted(data["test_year"].unique())
    if len(years) == 0:
        raise ValueError("No chronological share-MAE measurements")
    values = []
    for year in years:
        per_year = data[data["test_year"] == year].set_index("model")["score"]
        if not set(models).issubset(per_year.index):
            raise ValueError(f"Missing share models for {year}")
        values.append([float(per_year.at[m]) for m in models])
    values_np = np.asarray(values)
    positions = np.arange(len(years))
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    width = 0.25
    for index, name in enumerate(models):
        ax.bar(positions + (index - 1) * width, values_np[:, index], width,
               label=name)
    ax.set_xticks(positions, [str(y) for y in years])
    ax.set(xlabel="Test year (trained on earlier years only)",
           ylabel="Mean absolute error", title="Year-out general vote share prediction")
    ax.legend(fontsize=7)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    path = output_dir / "chronological_share_mae.png"
    fig.savefig(path, dpi=150, metadata={"Software": "fec-election-analysis"})
    plt.close(fig)
    paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate report figures from official-source normalized data")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--test-year", type=int, default=2022)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/figures"))
    args = parser.parse_args()
    for path in render_figures(
        pd.read_csv(args.input, dtype={"state": str, "district": str}),
        pd.read_csv(args.metrics),
        args.output_dir,
        args.test_year,
    ):
        print(f"Saved {path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
