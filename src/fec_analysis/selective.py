"""Frozen evaluation contract for the selective-prediction study (Issue #76).

This module is the single source of truth for the *cohort* that the
abstention experiments are allowed to score. It owns

* the fixed test-year cohorts and their baseline (no-fit majority rule) scores,
* the containment relation between the official FEC report groups and the
  916 selected House contests, and
* the audit that proves both are reproducible from the official workbooks.

Rules that every downstream Issue (#79-#82) inherits:

* The abstention decision may read **Primary votes only**. General votes are
  read exclusively to score a prediction that has already been fixed, never to
  decide whether to answer.
* ``P == 0.5`` is predicted as a Democratic lead. This matches the
  pre-existing ``primary-winner rule`` in ``scripts/analyze.py`` and is not
  changed by this study.
* General two-party ties are removed from the classification denominator,
  matching ``test_clf = test[~general_tie]`` in ``scripts/analyze.py``.
* The label ``general_rep_win`` is a **two-party lead**, not the certified
  election winner. The two are not interchangeable.

Nothing in this module fits a model, and nothing in it reads a threshold or a
threshold-adjusted result from the evaluated year.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from fec_analysis.core import prepare_elections

# --------------------------------------------------------------------------
# Frozen contract
# --------------------------------------------------------------------------

#: Test years evaluated by the selective-prediction study.
SELECTIVE_TEST_YEARS: tuple[int, ...] = (2018, 2020, 2022)

#: Abstention thresholds, in percentage points of the Primary two-party share.
SELECTIVE_THRESHOLDS_PCT: tuple[int, ...] = (0, 5, 10, 15, 20)

#: Size of the fixed per-year classification cohort (General ties removed).
EXPECTED_COHORT_SIZE: dict[int, int] = {2018: 241, 2020: 237, 2022: 238}

#: Baseline (t=0) error count of the no-fit Primary-majority rule.
EXPECTED_BASELINE_ERRORS: dict[int, int] = {2018: 24, 2020: 24, 2022: 24}

#: Baseline (t=0) accuracy of the no-fit Primary-majority rule (4 decimals).
EXPECTED_BASELINE_ACCURACY: dict[int, float] = {
    2018: 0.9004,
    2020: 0.8987,
    2022: 0.8992,
}

#: Containment of the selected cohort inside the official FEC report groups.
EXPECTED_REPORT_GROUPS: int = 1756
EXPECTED_NONVOTING_GROUPS: int = 22
EXPECTED_VOTING_HOUSE_GROUPS: int = 1734
EXPECTED_SELECTED_ROWS: int = 916

#: Non-voting delegate jurisdictions; never part of the 50-state House cohort.
NONVOTING_JURISDICTIONS: frozenset[str] = frozenset(
    {"AS", "DC", "GU", "MP", "PR", "VI"}
)

#: Keys that identify one House contest inside one year.
COHORT_KEYS: tuple[str, ...] = ("year", "state", "district")


# --------------------------------------------------------------------------
# Loading and cohort selection
# --------------------------------------------------------------------------


def load_elections(path: Path | str) -> pd.DataFrame:
    """Load the normalized FEC cohort and apply the shared validation rules.

    ``prepare_elections`` rejects negative or fractional votes, empty keys and
    duplicate election keys, so a successful load already guarantees the
    per-record preconditions the selective study relies on.
    """
    raw = pd.read_csv(path, dtype={"state": str, "district": str})
    return prepare_elections(raw)


def select_cohort(df: pd.DataFrame, test_year: int) -> pd.DataFrame:
    """Return the fixed classification cohort of ``test_year``.

    The cohort is every House contest of that year **minus** the contests
    whose General two-party vote is exactly tied, matching the denominator
    used by the pre-existing backtests.
    """
    if "general_tie" not in df.columns:
        raise ValueError(
            "select_cohort() expects a frame prepared by prepare_elections() "
            "(missing 'general_tie'); call fec_analysis.core.prepare_elections first"
        )
    cohort = df[(df["year"] == test_year) & (df["chamber"] == "House")]
    cohort = cohort[~cohort["general_tie"]]
    return cohort.reset_index(drop=True)


def majority_prediction(cohort: pd.DataFrame) -> pd.Series:
    """The no-fit Primary-majority rule: ``P > 0.5`` predicts R, otherwise D.

    This is the pre-existing ``primary-winner rule`` from ``scripts/analyze.py``
    and is the reference against which every abstention threshold is compared.
    """
    return (cohort["primary_rep_share"] > 0.5).astype(int)


def baseline_scores(cohort: pd.DataFrame) -> dict[str, Any]:
    """Error count and accuracy of the no-fit majority rule on one cohort."""
    if cohort.empty:
        raise ValueError("Cohort is empty")
    predicted = majority_prediction(cohort)
    wrong = int((predicted != cohort["general_rep_win"]).sum())
    n = len(cohort)
    correct = n - wrong
    return {
        "eligible": n,
        "correct": correct,
        "wrong": wrong,
        "accuracy": correct / n,
    }


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------


def audit_key_uniqueness(df: pd.DataFrame) -> dict[str, Any]:
    """Check that every (year, state, district) key identifies one contest."""
    duplicated = df[df.duplicated(subset=list(COHORT_KEYS), keep=False)]
    return {
        "rows": int(len(df)),
        "distinct_keys": int(len(df.drop_duplicates(subset=list(COHORT_KEYS)))),
        "duplicate_keys": int(
            duplicated.groupby(list(COHORT_KEYS), dropna=False).ngroups
        ),
    }


def audit_vote_integrity(df: pd.DataFrame) -> dict[str, Any]:
    """Check the vote preconditions the abstention rule depends on."""
    vote_columns = (
        "primary_rep_votes",
        "primary_dem_votes",
        "general_rep_votes",
        "general_dem_votes",
    )
    non_positive_primary = int(
        ((df["primary_rep_votes"] <= 0) | (df["primary_dem_votes"] <= 0)).sum()
    )
    non_positive_general = int(
        ((df["general_rep_votes"] <= 0) | (df["general_dem_votes"] <= 0)).sum()
    )
    negative = int((df[list(vote_columns)] < 0).sum().sum())
    fractional = int((df[list(vote_columns)] % 1 != 0).sum().sum())
    return {
        "non_positive_primary": non_positive_primary,
        "non_positive_general": non_positive_general,
        "negative_votes": negative,
        "fractional_votes": fractional,
    }


def audit_report_group_containment(
    df: pd.DataFrame, exclusions: pd.DataFrame
) -> dict[str, Any]:
    """Relate the 916 selected contests to the 1,756 official report groups.

    The three denominators used by this study are kept apart on purpose:

    * 1,756  -- every House report group in the four official workbooks,
    * 1,734  -- those minus the 22 non-voting delegate jurisdictions,
    *   916  -- the contests the conservative normalizer can actually score.
    """
    included = len(df)
    excluded = len(exclusions)
    nonvoting = int(
        (exclusions["reason"] == "nonvoting-delegate-jurisdiction").sum()
    )
    voting_house_groups = included + excluded - nonvoting
    nonvoting_in_cohort = sorted(
        set(df["state"].astype(str)) & NONVOTING_JURISDICTIONS
    )
    return {
        "report_groups": included + excluded,
        "selected_rows": included,
        "excluded_rows": excluded,
        "nonvoting_groups": nonvoting,
        "voting_house_groups": voting_house_groups,
        "selection_rate_of_voting_house": (
            included / voting_house_groups if voting_house_groups else float("nan")
        ),
        "nonvoting_jurisdictions_in_cohort": nonvoting_in_cohort,
    }


def audit_contracts(
    df: pd.DataFrame,
    exclusions: pd.DataFrame,
    test_years: tuple[int, ...] = SELECTIVE_TEST_YEARS,
) -> dict[str, Any]:
    """Run every cohort check and return a machine-readable audit report.

    The report is deliberately verbose: each expectation is paired with the
    observed value so a reviewer can see *which* contract failed rather than
    only that something failed.
    """
    keys = audit_key_uniqueness(df)
    votes = audit_vote_integrity(df)
    containment = audit_report_group_containment(df, exclusions)

    per_year: dict[str, Any] = {}
    for year in test_years:
        cohort = select_cohort(df, year)
        scores = baseline_scores(cohort)
        ties = int(
            (
                df[(df["year"] == year) & (df["chamber"] == "House")]["general_tie"]
            ).sum()
        )
        per_year[str(year)] = {
            "house_rows": int(
                len(df[(df["year"] == year) & (df["chamber"] == "House")])
            ),
            "general_ties_removed": ties,
            "eligible": scores["eligible"],
            "expected_eligible": EXPECTED_COHORT_SIZE.get(year),
            "eligible_matches": scores["eligible"]
            == EXPECTED_COHORT_SIZE.get(year),
            "baseline_wrong": scores["wrong"],
            "expected_baseline_wrong": EXPECTED_BASELINE_ERRORS.get(year),
            "baseline_wrong_matches": scores["wrong"]
            == EXPECTED_BASELINE_ERRORS.get(year),
            "baseline_accuracy": round(scores["accuracy"], 4),
            "expected_baseline_accuracy": EXPECTED_BASELINE_ACCURACY.get(year),
            "baseline_accuracy_matches": round(scores["accuracy"], 4)
            == EXPECTED_BASELINE_ACCURACY.get(year),
        }

    expectations = {
        "report_groups": (
            containment["report_groups"],
            EXPECTED_REPORT_GROUPS,
        ),
        "nonvoting_groups": (
            containment["nonvoting_groups"],
            EXPECTED_NONVOTING_GROUPS,
        ),
        "voting_house_groups": (
            containment["voting_house_groups"],
            EXPECTED_VOTING_HOUSE_GROUPS,
        ),
        "selected_rows": (containment["selected_rows"], EXPECTED_SELECTED_ROWS),
        "duplicate_keys": (keys["duplicate_keys"], 0),
        "negative_votes": (votes["negative_votes"], 0),
        "fractional_votes": (votes["fractional_votes"], 0),
        "non_positive_primary": (votes["non_positive_primary"], 0),
        "non_positive_general": (votes["non_positive_general"], 0),
        "nonvoting_in_cohort": (
            len(containment["nonvoting_jurisdictions_in_cohort"]),
            0,
        ),
    }
    contract_checks = {
        name: {"observed": observed, "expected": expected, "ok": observed == expected}
        for name, (observed, expected) in expectations.items()
    }

    per_year_ok = all(
        entry["eligible_matches"]
        and entry["baseline_wrong_matches"]
        and entry["baseline_accuracy_matches"]
        for entry in per_year.values()
    )
    all_ok = all(item["ok"] for item in contract_checks.values()) and per_year_ok

    return {
        "all_contracts_satisfied": all_ok,
        "key_uniqueness": keys,
        "vote_integrity": votes,
        "containment": containment,
        "per_year": per_year,
        "contract_checks": contract_checks,
        "notes": {
            "label_definition": (
                "general_rep_win is a two-party General vote lead, not the "
                "certified election winner."
            ),
            "tie_handling": (
                "General two-party ties are removed from the classification "
                "denominator, matching scripts/analyze.py."
            ),
            "prediction_time": (
                "General votes are used only to score a frozen prediction; the "
                "abstention decision sees Primary votes only."
            ),
        },
    }
