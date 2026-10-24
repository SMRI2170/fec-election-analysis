"""Audit the frozen evaluation cohort of the selective-prediction study.

This script does **not** run any abstention experiment. It fixes and verifies
the cohort that Issues #79-#82 are allowed to score, so that an improvement
claimed later can be attributed to the abstention rule and not to a changed
denominator.

Checks performed
  1. (year, state, district) keys identify exactly one House contest.
  2. Vote columns are non-negative integers with positive two-party totals.
  3. The 916 selected contests sit inside 1,734 voting-House report groups,
     which are themselves inside 1,756 official report groups; the 22
     non-voting delegate jurisdictions are excluded from the 50-state cohort.
  4. The per-year test cohorts are 241 / 237 / 238 contests and the no-fit
     Primary-majority rule reproduces 24 / 24 / 24 errors and
     90.04% / 89.87% / 89.92% accuracy.

Exit status is non-zero when a contract fails, so CI cannot pass silently.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fec_analysis.selective import (  # noqa: E402
    SELECTIVE_TEST_YEARS,
    audit_contracts,
    load_elections,
)


def format_report(report: dict) -> str:
    lines: list[str] = []
    lines.append("== Cohort containment ==")
    containment = report["containment"]
    lines.append(
        f"official report groups      : {containment['report_groups']} "
        f"(non-voting jurisdictions excluded: {containment['nonvoting_groups']})"
    )
    lines.append(
        f"50-state voting House groups : {containment['voting_house_groups']}"
    )
    lines.append(
        f"selected House contests      : {containment['selected_rows']} "
        f"({containment['selection_rate_of_voting_house'] * 100:.2f}% of the "
        f"voting-House groups)"
    )
    lines.append("")
    lines.append("== Per-year classification cohort (General ties removed) ==")
    header = (
        f"{'year':<6}{'house rows':>12}{'ties':>7}{'eligible':>10}"
        f"{'expected':>10}{'wrong':>8}{'exp':>6}{'accuracy':>10}{'exp':>9}"
    )
    lines.append(header)
    for year, entry in report["per_year"].items():
        lines.append(
            f"{year:<6}{entry['house_rows']:>12}{entry['general_ties_removed']:>7}"
            f"{entry['eligible']:>10}{entry['expected_eligible']:>10}"
            f"{entry['baseline_wrong']:>8}{entry['expected_baseline_wrong']:>6}"
            f"{entry['baseline_accuracy'] * 100:>9.2f}%"
            f"{entry['expected_baseline_accuracy'] * 100:>8.2f}%"
        )
    lines.append("")
    lines.append("== Contract checks ==")
    for name, check in report["contract_checks"].items():
        status = "OK " if check["ok"] else "FAIL"
        lines.append(
            f"[{status}] {name:<26} observed={check['observed']} "
            f"expected={check['expected']}"
        )
    lines.append("")
    overall = "PASS" if report["all_contracts_satisfied"] else "FAIL"
    lines.append(f"overall: {overall}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit the selective-prediction evaluation cohort"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/elections.csv"),
        help="normalized election table produced by scripts/normalize_fec.py",
    )
    parser.add_argument(
        "--exclusions",
        type=Path,
        default=Path("data/processed/exclusions.csv"),
        help="exclusion audit produced by scripts/normalize_fec.py",
    )
    parser.add_argument("--output", type=Path, help="write the audit report as JSON")
    parser.add_argument(
        "--test-years",
        type=int,
        nargs="+",
        default=list(SELECTIVE_TEST_YEARS),
        help="test years to audit",
    )
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(
            f"missing {args.input}; run scripts/normalize_fec.py first"
        )
    if not args.exclusions.exists():
        parser.error(
            f"missing {args.exclusions}; run scripts/normalize_fec.py first"
        )

    elections = load_elections(args.input)
    import pandas as pd

    exclusions = pd.read_csv(args.exclusions, dtype={"state": str, "district": str})
    report = audit_contracts(
        elections, exclusions, test_years=tuple(args.test_years)
    )

    print(format_report(report))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Saved: {args.output}")
    if not report["all_contracts_satisfied"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
