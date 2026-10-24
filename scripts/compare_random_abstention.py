"""Compare the abstention rule with random abstention of the same size.

Why this comparison exists
--------------------------
Abstaining always removes errors, so a lower error count after abstention
proves nothing on its own. The question that actually matters is whether the
**Primary two-party margin carries information about which contests are hard**
— that is, whether keeping only the contests the rule accepts leaves fewer
errors than keeping the same *number* of contests chosen at random.

Setup
-----
For one year let

* ``N`` be the size of the frozen evaluation cohort,
* ``E`` be the number of wrong contests under the no-fit majority rule
  (the errors of the t = 0 baseline), and
* ``K`` be the number of contests the rule answers at a given threshold.

If ``K`` contests were chosen **uniformly at random** from the ``N`` contests
and the remaining ``N - K`` abstained, the number of errors left among the
``K`` answers would follow the hypergeometric distribution

    X ~ Hypergeometric(N, E, K)

with expectation ``K * E / N``. The observed error count of the rule is
compared against that reference.

Interpretation limits (stated up front, repeated in the output)
---------------------------------------------------------------
* The random baseline is a **reference point**, not evidence that the abstained
  contests were random in reality.
* ``p_random_at_least_as_good`` is an **exploratory** quantity. With 3 years x
  5 thresholds the comparisons are heavily multiplied, so no significance
  claim is made from it.
* The hypergeometric reference assumes the error count is the only thing that
  distinguishes contests. It does not model any other correlation.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from evaluate_selective_primary import evaluate_grid  # noqa: E402
from fec_analysis.selective import (  # noqa: E402
    SELECTIVE_TEST_YEARS,
    SELECTIVE_THRESHOLDS_PCT,
    load_elections,
)

#: Columns added by this Issue to the 15-condition grid.
RANDOM_BASELINE_COLUMNS = [
    "all_wrong",
    "all_eligible",
    "random_abstention_expected_wrong",
    "random_abstention_sd",
    "random_abstention_p05",
    "random_abstention_p95",
    "error_avoidance_vs_random",
    "p_random_at_least_as_good",
]


def hypergeometric_pmf(population: int, errors: int, draws: int, x: int) -> float:
    """P(X = x) for X ~ Hypergeometric(population, errors, draws).

    Computed with exact integer combinations and converted to float at the end,
    so no new dependency and no floating point cancellation is involved.
    """
    if population <= 0:
        raise ValueError("population must be positive")
    if not 0 <= errors <= population:
        raise ValueError("errors must lie within the population")
    if not 0 <= draws <= population:
        raise ValueError("draws must lie within the population")
    if x < max(0, draws - (population - errors)) or x > min(draws, errors):
        return 0.0
    numerator = math.comb(errors, x) * math.comb(population - errors, draws - x)
    denominator = math.comb(population, draws)
    return numerator / denominator


def hypergeometric_distribution(
    population: int, errors: int, draws: int
) -> dict[int, float]:
    """The full probability mass function of X ~ Hypergeom(N, E, K)."""
    low = max(0, draws - (population - errors))
    high = min(draws, errors)
    return {
        x: hypergeometric_pmf(population, errors, draws, x)
        for x in range(low, high + 1)
    }


def _exact_quantile(distribution: dict[int, float], level: float) -> float:
    """Lower quantile of a discrete distribution (smallest x with CDF >= level)."""
    cumulative = 0.0
    for x in sorted(distribution):
        cumulative += distribution[x]
        if cumulative >= level - 1e-12:
            return float(x)
    return float(max(distribution))


def random_abstention_baseline(
    eligible: int, all_wrong: int, accepted: int
) -> dict[str, float]:
    """Reference values for answering ``accepted`` contests chosen at random.

    Parameters
    ----------
    eligible:
        ``N``, the size of the frozen evaluation cohort.
    all_wrong:
        ``E``, the number of wrong contests in that cohort under the t = 0 rule.
    accepted:
        ``K``, the number of contests the abstention rule answers.
    """
    if eligible <= 0:
        raise ValueError("eligible must be positive")
    if not 0 <= all_wrong <= eligible:
        raise ValueError("all_wrong must lie within the cohort")
    if not 0 <= accepted <= eligible:
        raise ValueError("accepted must lie within the cohort")

    expected = accepted * all_wrong / eligible

    if accepted == 0 or accepted == eligible or eligible == 1:
        # The distribution is degenerate: either nothing is drawn, everything
        # is drawn, or the cohort has a single member.
        variance = 0.0
    else:
        rate = all_wrong / eligible
        variance = (
            accepted
            * rate
            * (1.0 - rate)
            * ((eligible - accepted) / (eligible - 1))
        )
    sd = math.sqrt(variance)

    distribution = hypergeometric_distribution(eligible, all_wrong, accepted)
    p05 = _exact_quantile(distribution, 0.05)
    p95 = _exact_quantile(distribution, 0.95)

    return {
        "all_eligible": eligible,
        "all_wrong": all_wrong,
        "random_abstention_expected_wrong": expected,
        "random_abstention_sd": sd,
        "random_abstention_p05": p05,
        "random_abstention_p95": p95,
        "_distribution": distribution,
    }


def exploratory_p_value(
    observed_wrong: int,
    distribution: dict[int, float],
    expected: float,
) -> float:
    """P(X <= observed) under the random baseline. Exploratory only.

    When the observed count is *better* than the expectation (which is the
    direction the rule claims) this is the probability that a random choice of
    the same size would have been at least as good. When the observation is
    worse than expected, the mirrored tail is reported instead so that the
    value always describes the direction of the deviation.
    """
    if observed_wrong <= expected:
        return sum(p for x, p in distribution.items() if x <= observed_wrong)
    return sum(p for x, p in distribution.items() if x >= observed_wrong)


def compare_grid(
    grid: pd.DataFrame,
    random_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Add the random-abstention reference columns to a 15-condition grid."""
    columns = random_columns or RANDOM_BASELINE_COLUMNS
    rows: list[dict] = []
    for row in grid.to_dict(orient="records"):
        baseline = random_abstention_baseline(
            eligible=int(row["eligible"]),
            all_wrong=int(row["wrong_accepted"]) + int(row["wrong_abstained"]),
            accepted=int(row["accepted"]),
        )
        distribution = baseline.pop("_distribution")
        observed = int(row["wrong_accepted"])
        expected = baseline["random_abstention_expected_wrong"]
        baseline["error_avoidance_vs_random"] = expected - observed
        baseline["p_random_at_least_as_good"] = exploratory_p_value(
            observed, distribution, expected
        )
        merged = {**row, **baseline}
        rows.append({key: merged[key] for key in list(row) + columns})
    return pd.DataFrame(rows)


def verify_against_reference_grid(
    compared: pd.DataFrame, reference: pd.DataFrame
) -> list[str]:
    """Check that the recomputed grid still matches the Issue #80 grid."""
    problems: list[str] = []
    if len(compared) != len(reference):
        return [
            f"row count changed: {len(compared)} != {len(reference)}"
        ]
    keys = ["test_year", "t_pct"]
    merged = compared.merge(reference, on=keys, suffixes=("_new", "_ref"))
    for column in [
        "eligible",
        "accepted",
        "abstained",
        "correct_accepted",
        "wrong_accepted",
        "correct_abstained",
        "wrong_abstained",
    ]:
        new_column = f"{column}_new"
        reference_column = f"{column}_ref"
        if new_column not in merged.columns or reference_column not in merged.columns:
            problems.append(f"{column}: missing from the merged comparison")
            continue
        differing = merged[merged[new_column] != merged[reference_column]]
        if not differing.empty:
            problems.append(
                f"{column} changed in {len(differing)} condition(s): "
                f"{list(differing[keys].itertuples(index=False, name=None))}"
            )
    return problems


def format_table(compared: pd.DataFrame) -> str:
    header = (
        f"{'year':<6}{'t':>4}{'K':>6}{'N':>6}{'E':>4}{'observed':>10}"
        f"{'random E':>10}{'avoidance':>11}{'p(<=obs)':>11}{'correct.abs':>12}"
    )
    lines = [header, "-" * len(header)]
    for row in compared.itertuples(index=False):
        lines.append(
            f"{row.test_year:<6}{row.t_pct:>4}{row.accepted:>6}{row.eligible:>6}"
            f"{row.all_wrong:>4}{row.wrong_accepted:>10}"
            f"{row.random_abstention_expected_wrong:>10.2f}"
            f"{row.error_avoidance_vs_random:>11.2f}"
            f"{row.p_random_at_least_as_good:>11.4f}"
            f"{row.correct_abstained:>12}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare the abstention rule with random abstention of the same size"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/elections.csv"),
    )
    parser.add_argument(
        "--exclusions",
        type=Path,
        default=Path("data/processed/exclusions.csv"),
    )
    parser.add_argument(
        "--reference-grid",
        type=Path,
        default=Path("data/processed/selective-primary-grid.csv"),
        help="Issue #80 grid; used only to confirm the recomputation matches",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("data/processed/selective-primary-random-baseline.csv"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("data/processed/selective-primary-random-baseline.json"),
    )
    parser.add_argument(
        "--test-years", type=int, nargs="+", default=list(SELECTIVE_TEST_YEARS)
    )
    parser.add_argument(
        "--thresholds", type=int, nargs="+", default=list(SELECTIVE_THRESHOLDS_PCT)
    )
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"missing {args.input}; run scripts/normalize_fec.py first")

    elections = load_elections(args.input)
    groups = None
    if args.exclusions.exists():
        from evaluate_selective_primary import voting_house_groups_by_year

        exclusions = pd.read_csv(
            args.exclusions, dtype={"state": str, "district": str}
        )
        groups = voting_house_groups_by_year(elections, exclusions)

    grid = evaluate_grid(
        elections,
        thresholds=tuple(args.thresholds),
        test_years=tuple(args.test_years),
        voting_house_groups=groups,
    )
    compared = compare_grid(grid)
    print(format_table(compared))

    problems: list[str] = []
    if args.reference_grid.exists():
        reference = pd.read_csv(args.reference_grid)
        problems = verify_against_reference_grid(compared, reference)
        if problems:
            print("\nGRID MISMATCH against the Issue #80 output:")
            for problem in problems:
                print(f"  - {problem}")

    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    compared.to_csv(args.csv_output, index=False, na_rep="NA")

    report = {
        "schema_version": 1,
        "scope": "random-abstention reference for the Issue #80 grid",
        "conditions": len(compared),
        "reference_model": (
            "X ~ Hypergeometric(N, E, K): the number of errors left when K of "
            "the N contests are chosen uniformly at random and answered."
        ),
        "results": json.loads(compared.to_json(orient="records")),
        "grid_mismatch_problems": problems,
        "interpretation_limits": [
            "The random baseline is a reference point, not evidence that the "
            "abstained contests were random in reality.",
            "p_random_at_least_as_good is exploratory: 3 years x 5 thresholds "
            "are compared, so no significance claim is made.",
            "The hypergeometric reference models only the error count, not any "
            "other correlation between contests.",
            "Abstentions are never counted as correct predictions.",
        ],
    }
    args.json_output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nSaved: {args.csv_output}")
    print(f"Saved: {args.json_output}")

    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
