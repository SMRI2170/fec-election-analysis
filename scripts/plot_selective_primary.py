"""Render the coverage-risk figure for the abstention study (Issue #82).

The figure shows the trade-off that the study is about: how much of the
eligible area can still be answered, and how wrong the remaining answers are.
Each year contributes one series of five points (one per pre-registered
threshold).

Two reference elements matter for an honest reading:

* the **t = 0** point is the pre-existing Primary-majority rule, and
* each year carries a horizontal reference line at ``E / N``. Under random
  abstention of any size the error rate among the answers stays at the
  baseline rate, so that line is what "abstaining without information" looks
  like. Every thresholded point sits far below it.

A condition with ``accepted == 0`` has no risk to plot. Such a condition is
reported as NA in the accompanying table and is *not* drawn as a point.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, "src")

#: One colour per evaluated year.
YEAR_COLOURS = {2018: "#1f77b4", 2020: "#d62728", 2022: "#2ca02c"}


def build_series(grid: pd.DataFrame) -> dict[int, pd.DataFrame]:
    """Split the grid into one ordered frame per year."""
    series: dict[int, pd.DataFrame] = {}
    for year, group in grid.groupby("test_year"):
        series[int(year)] = group.sort_values("t_pct").reset_index(drop=True)
    return series


def _draw_coverage_risk(
    ax,
    series: dict[int, pd.DataFrame],
    random_baseline: pd.DataFrame | None,
) -> None:
    """Draw the coverage-risk content onto one axis."""
    for year, frame in series.items():
        colour = YEAR_COLOURS.get(year)
        plottable = frame[frame["accepted"] > 0]
        # Conditions with accepted == 0 have no risk and are left out.
        ax.plot(
            plottable["coverage"] * 100.0,
            plottable["selective_risk"] * 100.0,
            marker="o",
            markersize=4.0,
            linewidth=1.3,
            color=colour,
            label=f"{year} (n={int(frame['eligible'].iloc[0])})",
        )
        baseline = frame[frame["t_pct"] == 0]
        if not baseline.empty:
            ax.scatter(
                [float(baseline["coverage"].iloc[0]) * 100.0],
                [float(baseline["selective_risk"].iloc[0]) * 100.0],
                s=62,
                facecolors="none",
                edgecolors=colour,
                linewidths=1.6,
                zorder=5,
            )
        # Conditions that answer nothing are marked instead of plotted.
        for index, row in enumerate(frame[frame["accepted"] == 0].itertuples(index=False)):
            ax.annotate(
                "NA (no answer)",
                xy=(0.0, 0.0),
                xytext=(4, 6 + 8 * index),
                textcoords="offset points",
                fontsize=6,
                color=colour,
            )

    if random_baseline is not None and not random_baseline.empty:
        for year, group in random_baseline.groupby("test_year"):
            reference = group[group["t_pct"] == 0]
            if reference.empty:
                continue
            rate = float(reference["all_wrong"].iloc[0]) / float(
                reference["all_eligible"].iloc[0]
            )
            ax.axhline(
                rate * 100.0,
                color=YEAR_COLOURS.get(int(year), "#666666"),
                linestyle="--",
                linewidth=0.9,
                alpha=0.7,
            )

    first_year = list(series)[0]
    baseline_risk = float(series[first_year]["selective_risk"].iloc[0]) * 100.0
    ax.text(
        0.015,
        0.10,
        "dashed lines: expected risk of\nsame-size random abstention",
        transform=ax.transAxes,
        fontsize=6.2,
        ha="left",
        va="bottom",
        color="#444444",
    )
    ax.annotate(
        "t=0: pre-existing\nmajority rule",
        xy=(100.0, baseline_risk),
        xytext=(-12, 20),
        textcoords="offset points",
        fontsize=6.4,
        ha="right",
        color="#333333",
    )
    ax.set(
        xlabel="Answer rate (coverage) among eligible contests [%]",
        ylabel="Selective risk: wrong among answered [%]",
        xlim=(-3, 103),
        ylim=(-0.6, 13.5),
        title="Abstention on Primary margin: coverage vs. risk",
    )
    ax.grid(alpha=0.2)
    ax.legend(fontsize=7, loc="upper left")


def plot_coverage_risk(
    grid: pd.DataFrame,
    output_dir: Path,
    random_baseline: pd.DataFrame | None = None,
) -> list[Path]:
    """Draw the coverage-risk figure and save it as PNG and SVG."""
    if grid.empty:
        raise ValueError("The grid is empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    series = build_series(grid)

    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    _draw_coverage_risk(ax, series, random_baseline)
    fig.tight_layout()
    png_path = output_dir / "selective_coverage_risk.png"
    fig.savefig(png_path, dpi=150, metadata={"Software": "fec-election-analysis"})
    plt.close(fig)
    paths.append(png_path)

    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    _draw_coverage_risk(ax, series, random_baseline)
    fig.tight_layout()
    svg_path = output_dir / "selective_coverage_risk.svg"
    # The SVG writer accepts a different metadata vocabulary than the PNG one.
    fig.savefig(svg_path, metadata={"Creator": "fec-election-analysis"})
    plt.close(fig)
    paths.append(svg_path)
    return paths


def plot_random_comparison(
    grid: pd.DataFrame, output_dir: Path
) -> list[Path]:
    """Draw observed errors against the same-size random-abstention reference.

    The horizontal axis is the abstention threshold. The solid line is the
    error count the rule actually leaves among the answers; the dashed line is
    what a random choice of the same size would leave on average.
    """
    if grid.empty:
        raise ValueError("The grid is empty")
    if "random_abstention_expected_wrong" not in grid.columns:
        raise ValueError("The random-abstention columns are missing")
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(5.6, 3.9))
    for year, group in grid.groupby("test_year"):
        colour = YEAR_COLOURS.get(int(year), "#666666")
        ordered = group.sort_values("t_pct")
        thresholds = ordered["t_pct"].to_numpy()
        observed = ordered["wrong_accepted"].to_numpy(dtype=float)
        expected = ordered["random_abstention_expected_wrong"].to_numpy(dtype=float)
        ax.plot(
            thresholds,
            expected,
            linestyle="--",
            linewidth=1.3,
            color=colour,
            alpha=0.85,
            label=f"{year}: same-size random abstention",
        )
        ax.plot(
            thresholds,
            observed,
            marker="o",
            markersize=4.0,
            linewidth=1.6,
            color=colour,
            label=f"{year}: observed (Primary margin)",
        )
    ax.set_xticks(sorted(grid["t_pct"].unique()))
    ax.set(
        xlabel="Abstention threshold t [percentage points]",
        ylabel="Wrong among answered contests [count]",
        title="Observed errors vs. same-size random abstention",
    )
    ax.legend(fontsize=6.4, ncol=2, loc="upper center")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    path = output_dir / "selective_random_abstention_comparison.png"
    fig.savefig(path, dpi=150, metadata={"Software": "fec-election-analysis"})
    plt.close(fig)
    return [path]


def describe_figure(grid: pd.DataFrame) -> dict:
    """Machine-readable description of what the figure shows."""
    series = build_series(grid)
    years = []
    for year, frame in series.items():
        years.append(
            {
                "test_year": year,
                "eligible": int(frame["eligible"].iloc[0]),
                "points_plotted": int((frame["accepted"] > 0).sum()),
                "conditions": int(len(frame)),
                "conditions_without_an_answer": int((frame["accepted"] == 0).sum()),
                "coverage_percent": [round(float(v) * 100, 2) for v in frame["coverage"]],
                "selective_risk_percent": [
                    None if pd.isna(v) else round(float(v) * 100, 2)
                    for v in frame["selective_risk"]
                ],
                "t_pct": [int(v) for v in frame["t_pct"]],
                "baseline_condition": "t=0 is the pre-existing Primary-majority rule",
            }
        )
    return {
        "schema_version": 1,
        "x_axis": "coverage = accepted / eligible, in percent",
        "y_axis": "selective_risk = wrong_accepted / accepted, in percent",
        "series": years,
        "total_points_plotted": sum(item["points_plotted"] for item in years),
        "notes": [
            "A condition with accepted == 0 has no risk and is not drawn.",
            "The horizontal dashed line per year is the expected risk of "
            "same-size random abstention, which stays at the baseline rate.",
            "The figure alone does not show correct_abstained; the accompanying "
            "table in docs/selective-coverage-risk.md does.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render the coverage-risk figure for the abstention study"
    )
    parser.add_argument(
        "--grid",
        type=Path,
        default=Path("data/processed/selective-primary-grid.csv"),
    )
    parser.add_argument(
        "--random-baseline",
        type=Path,
        default=Path("data/processed/selective-primary-random-baseline.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/figures"))
    parser.add_argument(
        "--description-output",
        type=Path,
        default=Path("data/processed/selective-figure-description.json"),
    )
    args = parser.parse_args()

    if not args.grid.exists():
        parser.error(f"missing {args.grid}; run scripts/evaluate_selective_primary.py first")
    grid = pd.read_csv(args.grid)
    random_baseline = None
    if args.random_baseline.exists():
        random_baseline = pd.read_csv(args.random_baseline)

    for path in plot_coverage_risk(grid, args.output_dir, random_baseline):
        print(f"Saved {path} ({path.stat().st_size:,} bytes)")
    if random_baseline is not None and not random_baseline.empty:
        for path in plot_random_comparison(random_baseline, args.output_dir):
            print(f"Saved {path} ({path.stat().st_size:,} bytes)")
    else:
        print("Skipped the random-abstention comparison figure (no random baseline)")

    description = describe_figure(grid)
    args.description_output.parent.mkdir(parents=True, exist_ok=True)
    args.description_output.write_text(
        json.dumps(description, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Saved: {args.description_output}")
    print(
        "points plotted:",
        description["total_points_plotted"],
        "of",
        sum(item["conditions"] for item in description["series"]),
        "conditions",
    )


if __name__ == "__main__":
    main()
