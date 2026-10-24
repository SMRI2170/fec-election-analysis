"""Evaluate the Primary-only abstention rule over the frozen cohort.

This is the measurement script for Issue #80. It scores the rule of
``scripts/selective_primary_rule.py`` on the cohorts frozen by Issue #78 and
writes the full 3 years x 5 thresholds grid.

What the script does
--------------------
For every (test year, threshold) pair it reports, among the contests that
were **answered**:

* how many were answered (coverage),
* how many of those were wrong (selective risk), and
* how many correct answers were **given up** by abstaining.

What the script deliberately does not do
----------------------------------------
* It never re-tunes a threshold. The thresholds are fixed in advance by
  Issue #76 and are simply swept here.
* It never lets a General quantity influence an abstention decision. General
  votes are read only to score a decision that has already been made.
* It never removes a contest because its outcome is inconvenient. General
  two-party ties are removed by the frozen cohort contract of Issue #78, and
  nothing else is dropped.
* It never counts an abstention as a correct prediction.

Denominators
------------
Three different denominators appear in this study and they are kept apart:

============================  ==========================================
``eligible``                  the frozen per-year classification cohort
                              (241 / 237 / 238) used for coverage and risk
``voting_house_groups``       the 50-state voting House report groups of
                              that year in the official FEC workbooks
                              (the *selection* denominator)
``report_groups``             all House report groups of that year,
                              including non-voting jurisdictions
============================  ==========================================

Coverage of the *selection* stage (916 of 1,734 overall) and coverage of the
*answering* stage (accepted / eligible) are different questions and are
reported in different columns.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from fec_analysis.selective import (  # noqa: E402
    EXPECTED_BASELINE_ACCURACY,
    EXPECTED_BASELINE_ERRORS,
    EXPECTED_COHORT_SIZE,
    SELECTIVE_TEST_YEARS,
    SELECTIVE_THRESHOLDS_PCT,
    load_elections,
    select_cohort,
)
from selective_primary_rule import selective_rule  # noqa: E402

#: Columns of the machine-readable 15-row grid.
RESULT_COLUMNS = [
    "test_year",
    "t_pct",
    "eligible",
    "accepted",
    "abstained",
    "coverage",
    "correct_accepted",
    "wrong_accepted",
    "selective_risk",
    "conditional_accuracy",
    "correct_abstained",
    "wrong_abstained",
    "wrong_per_eligible",
    "voting_house_groups",
    "accepted_over_voting_house_groups",
]


def _majority_answer(primary_r: int, primary_d: int) -> int:
    """The no-fit Primary-majority answer: 1 for R, 0 otherwise."""
    return 1 if primary_r > primary_d else 0


def evaluate_condition(
    cohort: pd.DataFrame,
    threshold_pct: int,
    voting_house_groups: int | None = None,
) -> dict:
    """Score one (year, threshold) condition of the abstention rule.

    ``cohort`` must already be the frozen evaluation cohort of one year.
    """
    if cohort.empty:
        raise ValueError("Cohort is empty")

    accepted = 0
    correct_accepted = 0
    wrong_accepted = 0
    correct_abstained = 0
    wrong_abstained = 0

    for row in cohort.itertuples(index=False):
        primary_r = int(row.primary_rep_votes)
        primary_d = int(row.primary_dem_votes)
        is_answered, answer = selective_rule(primary_r, primary_d, threshold_pct)
        # The answer the rule would have given without abstaining. Used only
        # to score the opportunity that abstaining gives up.
        majority = _majority_answer(primary_r, primary_d)
        is_correct = majority == int(row.general_rep_win)
        if is_answered:
            accepted += 1
            # `answer` and `majority` agree whenever the contest is answered.
            assert answer == majority
            if is_correct:
                correct_accepted += 1
            else:
                wrong_accepted += 1
        else:
            if is_correct:
                correct_abstained += 1
            else:
                wrong_abstained += 1

    eligible = len(cohort)
    abstained = eligible - accepted
    assert accepted + abstained == eligible
    assert correct_accepted + wrong_accepted == accepted
    assert correct_abstained + wrong_abstained == abstained
    assert wrong_accepted <= accepted

    if accepted:
        selective_risk = wrong_accepted / accepted
        conditional_accuracy = 1.0 - selective_risk
    else:
        selective_risk = float("nan")
        conditional_accuracy = float("nan")

    row = {
        "t_pct": threshold_pct,
        "eligible": eligible,
        "accepted": accepted,
        "abstained": abstained,
        "coverage": accepted / eligible,
        "correct_accepted": correct_accepted,
        "wrong_accepted": wrong_accepted,
        "selective_risk": selective_risk,
        "conditional_accuracy": conditional_accuracy,
        "correct_abstained": correct_abstained,
        "wrong_abstained": wrong_abstained,
        "wrong_per_eligible": wrong_accepted / eligible,
    }
    if voting_house_groups:
        row["voting_house_groups"] = voting_house_groups
        row["accepted_over_voting_house_groups"] = accepted / voting_house_groups
    else:
        row["voting_house_groups"] = None
        row["accepted_over_voting_house_groups"] = float("nan")
    return row


def evaluate_grid(
    elections: pd.DataFrame,
    thresholds: tuple[int, ...] = SELECTIVE_THRESHOLDS_PCT,
    test_years: tuple[int, ...] = SELECTIVE_TEST_YEARS,
    voting_house_groups: dict[int, int] | None = None,
) -> pd.DataFrame:
    """Score the full year x threshold grid, one row per condition."""
    rows: list[dict] = []
    for year in test_years:
        cohort = select_cohort(elections, year)
        groups = None if voting_house_groups is None else voting_house_groups.get(year)
        for threshold in thresholds:
            result = evaluate_condition(cohort, threshold, groups)
            result["test_year"] = year
            rows.append(result)
    frame = pd.DataFrame(rows)
    return frame[["test_year"] + RESULT_COLUMNS[1:]]


def voting_house_groups_by_year(
    elections: pd.DataFrame, exclusions: pd.DataFrame
) -> dict[int, int]:
    """50-state voting House report groups per year.

    The denominator of the *selection* stage is every House report group of
    the year except the non-voting delegate jurisdictions:

        voting_house_groups = selected + excluded - nonvoting

    The non-voting delegate jurisdictions are removed because they are not
    50-state House contests and must not enter the nationwide denominator.
    """
    counts: dict[int, int] = {}
    for year, group in exclusions.groupby("year"):
        nonvoting = int(
            (group["reason"] == "nonvoting-delegate-jurisdiction").sum()
        )
        selected = int((elections["year"] == int(year)).sum())
        counts[int(year)] = selected + len(group) - nonvoting
    return counts


def check_baseline(grid: pd.DataFrame) -> list[str]:
    """Verify that t=0 reproduces the frozen baseline of Issue #78."""
    problems: list[str] = []
    zero = grid[grid["t_pct"] == 0]
    for year in SELECTIVE_TEST_YEARS:
        row = zero[zero["test_year"] == year]
        if len(row) != 1:
            problems.append(f"{year}: expected exactly one t=0 row, found {len(row)}")
            continue
        values = row.iloc[0]
        if int(values["eligible"]) != EXPECTED_COHORT_SIZE[year]:
            problems.append(
                f"{year}: eligible {int(values['eligible'])} != {EXPECTED_COHORT_SIZE[year]}"
            )
        if int(values["wrong_accepted"]) != EXPECTED_BASELINE_ERRORS[year]:
            problems.append(
                f"{year}: t=0 errors {int(values['wrong_accepted'])} != {EXPECTED_BASELINE_ERRORS[year]}"
            )
        expected_accuracy = EXPECTED_BASELINE_ACCURACY[year]
        observed = round(float(values["conditional_accuracy"]), 4)
        if observed != expected_accuracy:
            problems.append(
                f"{year}: t=0 accuracy {observed} != {expected_accuracy}"
            )
        if int(values["abstained"]) != 0:
            problems.append(f"{year}: t=0 must not abstain, got {int(values['abstained'])}")
    return problems


def check_monotonicity(grid: pd.DataFrame) -> list[str]:
    """Accepted must never grow with the threshold.

    Accuracy is deliberately **not** required to improve: a threshold that
    concentrates on hard contests can make things worse.
    """
    problems: list[str] = []
    for year, group in grid.groupby("test_year"):
        ordered = group.sort_values("t_pct")
        accepted = ordered["accepted"].tolist()
        for threshold, value in zip(ordered["t_pct"], accepted):
            if pd.isna(value):
                problems.append(f"{year}: accepted is missing at t={threshold}")
        for previous, current in zip(accepted, accepted[1:]):
            if pd.isna(previous) or pd.isna(current):
                continue
            if current > previous:
                problems.append(
                    f"{year}: accepted grew from {previous} to {current} as the threshold rose"
                )
    return problems


def build_report(
    grid: pd.DataFrame,
    elections: pd.DataFrame,
    exclusions: pd.DataFrame | None = None,
) -> dict:
    """Assemble the machine-readable report around the 15-row grid."""
    from fec_analysis.selective import audit_report_group_containment

    report: dict = {
        "schema_version": 1,
        "scope": "FEC 50-state voting U.S. House, frozen Issue #78 cohort",
        "thresholds_pct": list(SELECTIVE_THRESHOLDS_PCT),
        "test_years": list(SELECTIVE_TEST_YEARS),
        "conditions": len(grid),
        "results": json.loads(grid.to_json(orient="records")),
        "baseline_check": {
            "problems": check_baseline(grid),
            "ok": not check_baseline(grid),
        },
        "monotonicity_check": {
            "problems": check_monotonicity(grid),
            "ok": not check_monotonicity(grid),
        },
        "definitions": {
            "coverage": "accepted / eligible (answering stage)",
            "selective_risk": "wrong_accepted / accepted; NaN when accepted == 0",
            "conditional_accuracy": "1 - selective_risk; NaN when accepted == 0",
            "wrong_per_eligible": "wrong_accepted / eligible (abstentions are not credited)",
            "correct_abstained": "contests that were abstained although the majority rule would have been right",
            "wrong_abstained": "contests that were abstained and would have been wrong",
        },
        "notes": {
            "label": "general_rep_win is a two-party General lead, not the certified winner.",
            "thresholds": "Pre-registered in Issue #76 before measurement; not tuned afterwards.",
            "general_use": "General votes are used only to score frozen decisions.",
            "exploratory": (
                "The 2022 error structure was already inspected before this design "
                "was fixed, so every threshold result is exploratory."
            ),
        },
    }
    if exclusions is not None:
        containment = audit_report_group_containment(elections, exclusions)
        report["selection_coverage"] = {
            "report_groups": containment["report_groups"],
            "nonvoting_groups": containment["nonvoting_groups"],
            "voting_house_groups": containment["voting_house_groups"],
            "selected_rows": containment["selected_rows"],
            "selection_rate_of_voting_house": containment[
                "selection_rate_of_voting_house"
            ],
            "note": (
                "Selection coverage (916 / 1,734) and answering coverage "
                "(accepted / eligible) use different denominators."
            ),
        }
    return report


def format_table(grid: pd.DataFrame) -> str:
    """Render the grid as a fixed-width table for the console."""
    header = (
        f"{'year':<6}{'t':>4}{'eligible':>10}{'accepted':>10}{'abstained':>11}"
        f"{'coverage':>10}{'wrong':>7}{'risk':>9}{'cond.acc':>10}"
        f"{'corr.abs':>10}{'wrong.abs':>11}{'wrong/elig':>12}"
    )
    lines = [header, "-" * len(header)]
    for row in grid.itertuples(index=False):
        risk = "NA" if pd.isna(row.selective_risk) else f"{row.selective_risk * 100:.2f}%"
        accuracy = (
            "NA"
            if pd.isna(row.conditional_accuracy)
            else f"{row.conditional_accuracy * 100:.2f}%"
        )
        lines.append(
            f"{row.test_year:<6}{row.t_pct:>4}{row.eligible:>10}{row.accepted:>10}"
            f"{row.abstained:>11}{row.coverage * 100:>9.2f}%{row.wrong_accepted:>7}"
            f"{risk:>9}{accuracy:>10}{row.correct_abstained:>10}"
            f"{row.wrong_abstained:>11}{row.wrong_per_eligible * 100:>11.2f}%"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the Primary-only abstention rule over the frozen cohort"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/elections.csv"),
        help="normalized election table from scripts/normalize_fec.py",
    )
    parser.add_argument(
        "--exclusions",
        type=Path,
        default=Path("data/processed/exclusions.csv"),
        help="exclusion audit from scripts/normalize_fec.py",
    )
    parser.add_argument("--csv-output", type=Path, default=Path("data/processed/selective-primary-grid.csv"))
    parser.add_argument("--json-output", type=Path, default=Path("data/processed/selective-primary-grid.json"))
    parser.add_argument(
        "--test-years",
        type=int,
        nargs="+",
        default=list(SELECTIVE_TEST_YEARS),
    )
    parser.add_argument(
        "--thresholds",
        type=int,
        nargs="+",
        default=list(SELECTIVE_THRESHOLDS_PCT),
    )
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"missing {args.input}; run scripts/normalize_fec.py first")

    elections = load_elections(args.input)
    exclusions = None
    groups = None
    if args.exclusions.exists():
        exclusions = pd.read_csv(args.exclusions, dtype={"state": str, "district": str})
        groups = voting_house_groups_by_year(elections, exclusions)

    grid = evaluate_grid(
        elections,
        thresholds=tuple(args.thresholds),
        test_years=tuple(args.test_years),
        voting_house_groups=groups,
    )
    print(format_table(grid))

    problems = check_baseline(grid) + check_monotonicity(grid)
    if problems:
        print("\nCONTRACT PROBLEMS:")
        for problem in problems:
            print(f"  - {problem}")

    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    grid.to_csv(args.csv_output, index=False, na_rep="NA")
    report = build_report(grid, elections, exclusions)
    args.json_output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nSaved: {args.csv_output}")
    print(f"Saved: {args.json_output}")

    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
