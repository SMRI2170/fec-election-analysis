"""Descriptive relation between the Primary and the General election (#58).

The selective study (#78-#82) asks *which* contests are hard to predict, and
#63/#64 ask how the errors and the probability output behave. This script
answers the complementary descriptive question of the assignment: **how do the
Primary and the General election relate beyond the two-party share?**

Three families of quantities are computed on the frozen 916-contest cohort:

1. **Scale.** For every contest the two-party vote totals of both elections
   (``R+D``) and their ratio are computed. The ratio is a *two-party vote
   total multiplier*: the General election involves a different electorate,
   different rules and a different number of contests, so it is **not** a
   turnout rate and it does not contain third-party votes. It is named
   accordingly and never called a participation rate.

2. **Shape.** The Primary two-party share ``P`` and the General two-party
   share ``G`` are related per year: Pearson's r, Spearman's rho, the OLS
   slope and intercept of ``G`` on ``P``, and the mean absolute difference
   ``G - P`` in points. The per-year fit is descriptive; it is never used to
   predict a later year, and nothing is re-tuned on 2022.

3. **Pre-declared split.** The adopted contests of a year are split into
   quintiles of the **Primary two-party vote total**. That quantity is
   available before the General election and is fixed by the split rule, not
   by any outcome, so the split is declared before the General numbers are
   looked at. Within a quintile the mean vote-total multiplier, the mean
   ``G - P`` and the majority-rule error rate are reported as an *exploratory*
   comparison.

No causal reading is made: the Primary and the General election differ in
electorate, in rules (runoff, fusion, uncontested races) and in the fact that
the source workbooks are published after the election. Nothing in this script
estimates an effect; it describes the relation on the frozen cohort.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fec_analysis.core import prepare_elections

#: Number of pre-declared quintiles of the Primary two-party vote total.
N_QUINTILES = 5
#: The two-party vote-total multiplier is a scale comparison between two
#: elections. It is *not* a turnout rate: it excludes third-party votes and
#: the electorate plays no role. This constant is carried in the output so
#: that the naming cannot be silently changed downstream.
MEASURE_NAME = "two_party_total_ratio"
MEASURE_DEFINITION = (
    "(general_rep_votes + general_dem_votes) / (primary_rep_votes + primary_dem_votes)"
)
NOT_A_TURNOUT_NOTE = (
    "two-party vote total multiplier; not a turnout or participation rate "
    "(third-party votes and the electorate are not part of the measure)"
)


def contest_frame(data: pd.DataFrame, chamber: str = "House") -> pd.DataFrame:
    """Add the descriptive quantities to the frozen cohort."""
    df = prepare_elections(data)
    df = df[df["chamber"] == chamber].copy()
    df["primary_two_party_total"] = df["primary_rep_votes"] + df["primary_dem_votes"]
    df["general_two_party_total"] = df["general_rep_votes"] + df["general_dem_votes"]
    df[MEASURE_NAME] = df["general_two_party_total"] / df["primary_two_party_total"]
    df["two_party_total_difference"] = (
        df["general_two_party_total"] - df["primary_two_party_total"]
    )
    df["share_difference_points"] = (df["general_rep_share"] - df["primary_rep_share"]) * 100
    df["abs_share_difference_points"] = df["share_difference_points"].abs()
    # The majority rule predicts a Republican lead when P > 0.5. It is the
    # rule the report uses, so the error rate per quintile is measured with
    # it. The *label* is the two-party lead of the General election, never a
    # certified winner.
    df["majority_rule_prediction"] = (df["primary_rep_share"] > 0.5).astype(int)
    df["majority_rule_error"] = (
        df["majority_rule_prediction"] != df["general_two_party_rep_lead"]
    ).astype(int)
    return df


def _ranks(values: np.ndarray) -> np.ndarray:
    """Average ranks, so that ties are handled like a standard Spearman rho."""
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(1, len(values) + 1, dtype=float)
    # Average the ranks of tied values.
    sorted_values = values[order]
    start = 0
    for index in range(1, len(values) + 1):
        if index == len(values) or sorted_values[index] != sorted_values[start]:
            if index - start > 1:
                ranks[order[start:index]] = ranks[order[start:index]].mean()
            start = index
    return ranks


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson's correlation coefficient."""
    if len(x) < 2:
        return float("nan")
    dx = x - x.mean()
    dy = y - y.mean()
    denominator = float(np.sqrt((dx * dx).sum() * (dy * dy).sum()))
    if denominator == 0:
        return float("nan")
    return float((dx * dy).sum() / denominator)


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman's rank correlation coefficient."""
    if len(x) < 2:
        return float("nan")
    return pearson(_ranks(x), _ranks(y))


def year_summary(group: pd.DataFrame) -> dict[str, float]:
    """Descriptive relation between the Primary and the General share."""
    primary = group["primary_rep_share"].to_numpy(dtype=float)
    general = group["general_rep_share"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(primary, general, 1)
    ratio = group[MEASURE_NAME].to_numpy(dtype=float)
    return {
        "n": int(len(group)),
        "pearson_r": pearson(primary, general),
        "spearman_rho": spearman(primary, general),
        "ols_slope": float(slope),
        "ols_intercept": float(intercept),
        "mean_share_difference_points": float(group["share_difference_points"].mean()),
        "mean_abs_share_difference_points": float(group["abs_share_difference_points"].mean()),
        "mean_two_party_total_ratio": float(ratio.mean()),
        "median_two_party_total_ratio": float(np.median(ratio)),
        "q25_two_party_total_ratio": float(np.quantile(ratio, 0.25)),
        "q75_two_party_total_ratio": float(np.quantile(ratio, 0.75)),
        "min_two_party_total_ratio": float(ratio.min()),
        "max_two_party_total_ratio": float(ratio.max()),
        "mean_primary_two_party_total": float(group["primary_two_party_total"].mean()),
        "mean_general_two_party_total": float(group["general_two_party_total"].mean()),
        "mean_two_party_total_difference": float(
            group["two_party_total_difference"].mean()
        ),
        "majority_rule_errors": int(group["majority_rule_error"].sum()),
        "majority_rule_error_rate": float(group["majority_rule_error"].mean()),
    }


def assign_volume_quintiles(
    group: pd.DataFrame, n_quintiles: int = N_QUINTILES
) -> pd.DataFrame:
    """Split a year into quintiles of the **Primary** two-party vote total.

    The split rule is fixed before any General quantity is read: the edges
    come from the quintiles of the Primary two-party total of the adopted
    contests of that year. Ties are broken by the election id so that the
    assignment is deterministic and reproducible.
    """
    if len(group) < n_quintiles:
        raise ValueError("not enough contests to split into quintiles")
    ordered = group.sort_values(
        ["primary_two_party_total", "election_id"], kind="mergesort"
    )
    # ``qcut`` on the already sorted frame is not used: duplicate totals
    # would raise. The rank position decides the bin, so every contest gets
    # exactly one bin and the bin sizes differ by at most one.
    positions = np.arange(len(ordered))
    bins = np.minimum((positions * n_quintiles) // len(ordered), n_quintiles - 1)
    result = ordered.copy()
    result["volume_quintile"] = bins + 1
    return result


def quintile_table(frame: pd.DataFrame, n_quintiles: int = N_QUINTILES) -> pd.DataFrame:
    """Descriptive comparison of the General outcome across the quintiles."""
    rows = []
    for year, group in frame.groupby("year"):
        assigned = assign_volume_quintiles(group, n_quintiles)
        for quintile, part in assigned.groupby("volume_quintile"):
            ratio = part[MEASURE_NAME].to_numpy(dtype=float)
            rows.append(
                {
                    "year": int(year),
                    "volume_quintile": int(quintile),
                    "n": int(len(part)),
                    "mean_primary_two_party_total": float(
                        part["primary_two_party_total"].mean()
                    ),
                    "mean_general_two_party_total": float(
                        part["general_two_party_total"].mean()
                    ),
                    "mean_two_party_total_ratio": float(ratio.mean()),
                    "median_two_party_total_ratio": float(np.median(ratio)),
                    "mean_share_difference_points": float(
                        part["share_difference_points"].mean()
                    ),
                    "mean_abs_share_difference_points": float(
                        part["abs_share_difference_points"].mean()
                    ),
                    "majority_rule_errors": int(part["majority_rule_error"].sum()),
                    "majority_rule_error_rate": float(part["majority_rule_error"].mean()),
                }
            )
    return pd.DataFrame(rows)


def analyze(data: pd.DataFrame, chamber: str = "House") -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return the per-year summary, the quintile table and the run metadata."""
    frame = contest_frame(data, chamber)
    per_year = []
    for year, group in frame.groupby("year"):
        entry = year_summary(group)
        entry["year"] = int(year)
        per_year.append(entry)
    summary_frame = pd.DataFrame(per_year).sort_values("year")
    quintiles = quintile_table(frame)
    meta = {
        "chamber": chamber,
        "measure": MEASURE_NAME,
        "measure_definition": MEASURE_DEFINITION,
        "measure_is_not": NOT_A_TURNOUT_NOTE,
        "n_quintiles": N_QUINTILES,
        "quintile_rule": (
            "quintiles of the Primary two-party vote total of the adopted "
            "contests of each year; the rule uses no General quantity"
        ),
        "general_used_as_predictor": False,
        "causal_claim": False,
        "n_contests": int(len(frame)),
        "per_year": summary_frame.to_dict(orient="records"),
    }
    return summary_frame, quintiles, meta


def plot_relation(
    frame: pd.DataFrame,
    summary: pd.DataFrame,
    png_path: Path,
    svg_path: Path,
) -> None:
    """Scatter of the Primary against the General share, and the scale ratio."""
    # The figure is drawn at the width it is printed at (5.6 in = 14.2 cm),
    # so that the in-figure text stays near 7 pt in the manuscript.
    fig, (left, right) = plt.subplots(1, 2, figsize=(5.6, 2.9))
    for year, group in frame.groupby("year"):
        left.scatter(
            group["primary_rep_share"],
            group["general_rep_share"],
            s=9,
            alpha=0.65,
            linewidths=0,
            label=f"{year} (n={len(group)})",
        )
    left.plot([0, 1], [0, 1], linestyle="--", linewidth=0.8, color="0.45")
    for _, row in summary.iterrows():
        slope = row["ols_slope"]
        intercept = row["ols_intercept"]
        x = np.linspace(0, 1, 10)
        left.plot(x, slope * x + intercept, linewidth=0.9, alpha=0.85)
    left.set_xlabel("Primary two-party share (R)", fontsize=7)
    left.set_ylabel("General two-party share (R)", fontsize=7)
    left.set_xlim(0, 1)
    left.set_ylim(0, 1)
    left.tick_params(labelsize=6)
    left.legend(fontsize=6, loc="upper left", ncol=2)
    left.grid(alpha=0.25, linewidth=0.5)

    years = sorted(frame["year"].unique())
    data = [frame.loc[frame["year"] == year, MEASURE_NAME].to_numpy() for year in years]
    # ``labels`` was renamed to ``tick_labels`` in matplotlib 3.9 and removed
    # in 3.11; the requirement range allows both, so the call is adapted.
    try:
        parts = right.boxplot(
            data, tick_labels=[str(year) for year in years], widths=0.55
        )
    except TypeError:  # pragma: no cover - matplotlib < 3.9
        parts = right.boxplot(data, labels=[str(year) for year in years], widths=0.55)
    for element in ("whiskers", "caps", "medians"):
        for item in parts[element]:
            item.set_linewidth(0.7)
    for item in parts["boxes"]:
        item.set_linewidth(0.7)
    right.axhline(1.0, linestyle="--", linewidth=0.8, color="0.45")
    right.set_ylabel("Two-party vote total multiplier (G / P)", fontsize=7)
    right.set_xlabel("Year", fontsize=7)
    right.tick_params(labelsize=6)
    right.grid(alpha=0.25, linewidth=0.5, axis="y")

    fig.tight_layout()
    fig.savefig(png_path, dpi=150, metadata={"Software": "fec-election-analysis"})
    fig.savefig(svg_path, metadata={"Creator": "fec-election-analysis"})
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--chamber", choices=["House", "Senate"], default="House")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/primary_general")
    )
    parser.add_argument(
        "--figure-dir", type=Path, default=Path("outputs/figures")
    )
    args = parser.parse_args()

    data = pd.read_csv(args.input, dtype={"state": str, "district": str})
    summary, quintiles, meta = analyze(data, args.chamber)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_dir / "primary_general_summary.csv", index=False)
    quintiles.to_csv(args.output_dir / "volume_quintiles.csv", index=False)
    (args.output_dir / "primary_general_summary.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    png = args.figure_dir / "primary_general_relation.png"
    svg = args.figure_dir / "primary_general_relation.svg"
    frame = contest_frame(data, args.chamber)
    plot_relation(frame, summary, png, svg)

    print(
        summary[
            [
                "year",
                "n",
                "pearson_r",
                "spearman_rho",
                "ols_slope",
                "mean_share_difference_points",
                "mean_two_party_total_ratio",
                "majority_rule_errors",
            ]
        ].to_string(index=False, float_format=lambda x: f"{x:.4f}")
    )
    print()
    print(
        quintiles[
            [
                "year",
                "volume_quintile",
                "n",
                "mean_two_party_total_ratio",
                "mean_share_difference_points",
                "majority_rule_errors",
            ]
        ].to_string(index=False, float_format=lambda x: f"{x:.4f}")
    )
    print("Saved:", args.output_dir / "primary_general_summary.csv")
    print("Saved:", args.output_dir / "volume_quintiles.csv")
    print("Saved:", args.output_dir / "primary_general_summary.json")
    print("Saved:", png)


if __name__ == "__main__":
    main()
