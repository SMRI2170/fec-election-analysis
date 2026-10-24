"""Unit tests for the abstention evaluation grid (Issue #80).

Synthetic fixtures only. The official numbers (241 / 237 / 238 contests with
24 baseline errors, and the 15-row grid itself) are verified in the
official-FEC GitHub Actions workflow.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
for extra in (str(ROOT / "scripts"), str(ROOT / "src")):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from fec_analysis.core import prepare_elections  # noqa: E402
from fec_analysis.selective import (  # noqa: E402
    EXPECTED_BASELINE_ACCURACY,
    EXPECTED_BASELINE_ERRORS,
    EXPECTED_COHORT_SIZE,
    SELECTIVE_TEST_YEARS,
    SELECTIVE_THRESHOLDS_PCT,
    select_cohort,
)
from selective_primary_rule import selective_rule  # noqa: E402


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evaluator = _load_script("evaluate_selective_primary")


def make_cohort(
    specs: list[tuple[int, int, int, int]], year: int = 2022
) -> pd.DataFrame:
    """Build a prepared cohort from (primary_r, primary_d, general_r, general_d)."""
    rows = []
    for index, (p_rep, p_dem, g_rep, g_dem) in enumerate(specs, start=1):
        rows.append(
            {
                "year": year,
                "state": "AA",
                "chamber": "House",
                "district": f"{index:02d}",
                "primary_rep_votes": p_rep,
                "primary_dem_votes": p_dem,
                "general_rep_votes": g_rep,
                "general_dem_votes": g_dem,
            }
        )
    return prepare_elections(pd.DataFrame(rows))


#: Two clear Republican contests, two clear Democratic ones and one razor-thin
#: contest that the majority rule gets wrong.
FIXTURE = [
    (70, 30, 65, 35),
    (60, 40, 55, 45),
    (30, 70, 35, 65),
    (40, 60, 45, 55),
    (51, 49, 40, 60),
]


# --------------------------------------------------------------------------
# Condition-level accounting
# --------------------------------------------------------------------------


def test_conservation_laws_hold_for_every_threshold():
    cohort = make_cohort(FIXTURE)
    for threshold in SELECTIVE_THRESHOLDS_PCT:
        row = evaluator.evaluate_condition(cohort, threshold)
        assert row["accepted"] + row["abstained"] == row["eligible"]
        assert row["correct_accepted"] + row["wrong_accepted"] == row["accepted"]
        assert row["correct_abstained"] + row["wrong_abstained"] == row["abstained"]
        assert row["wrong_accepted"] <= row["accepted"]
        assert row["coverage"] == pytest.approx(row["accepted"] / row["eligible"])


def test_threshold_zero_answers_everything():
    cohort = make_cohort(FIXTURE)
    row = evaluator.evaluate_condition(cohort, 0)
    assert row["accepted"] == len(FIXTURE)
    assert row["abstained"] == 0
    assert row["correct_abstained"] == 0
    assert row["wrong_abstained"] == 0


def test_threshold_zero_counts_the_razor_thin_contest_as_an_error():
    cohort = make_cohort(FIXTURE)
    row = evaluator.evaluate_condition(cohort, 0)
    # Only the 51/49 -> 40/60 contest flips.
    assert row["wrong_accepted"] == 1
    assert row["correct_accepted"] == len(FIXTURE) - 1


def test_abstention_removes_the_razor_thin_contest():
    cohort = make_cohort(FIXTURE)
    row = evaluator.evaluate_condition(cohort, 5)
    assert row["abstained"] == 1
    assert row["wrong_accepted"] == 0
    # The abandoned contest is the razor-thin one that the majority rule got
    # wrong (51/49 in the primary, 40/60 in the general), so abstaining
    # removed an error rather than a correct answer.
    assert row["wrong_abstained"] == 1
    assert row["correct_abstained"] == 0


def test_abstentions_are_never_credited_as_correct_answers():
    cohort = make_cohort(FIXTURE)
    for threshold in SELECTIVE_THRESHOLDS_PCT:
        row = evaluator.evaluate_condition(cohort, threshold)
        # The number of credited answers never exceeds what was answered.
        assert row["correct_accepted"] <= row["accepted"]
        assert row["correct_accepted"] + row["correct_abstained"] <= row["eligible"]


def test_wrong_per_eligible_does_not_credit_abstentions():
    cohort = make_cohort(FIXTURE)
    for threshold in SELECTIVE_THRESHOLDS_PCT:
        row = evaluator.evaluate_condition(cohort, threshold)
        assert row["wrong_per_eligible"] == pytest.approx(
            row["wrong_accepted"] / row["eligible"]
        )


def test_risk_and_accuracy_are_nan_when_nothing_is_answered():
    # Every contest sits inside the 20-point band, so nothing is answered.
    cohort = make_cohort([(51, 49, 60, 40), (49, 51, 40, 60)])
    row = evaluator.evaluate_condition(cohort, 20)
    assert row["accepted"] == 0
    assert row["abstained"] == 2
    assert pd.isna(row["selective_risk"])
    assert pd.isna(row["conditional_accuracy"])
    assert row["coverage"] == 0.0


def test_evaluate_condition_rejects_an_empty_cohort():
    cohort = make_cohort(FIXTURE)
    empty = cohort.iloc[0:0]
    with pytest.raises(ValueError):
        evaluator.evaluate_condition(empty, 5)


# --------------------------------------------------------------------------
# Invariance to future information
# --------------------------------------------------------------------------


def test_abstention_decision_is_invariant_to_general_votes():
    """Changing every General vote must not move a single accept/abstain call."""
    original = make_cohort(FIXTURE)
    scrambled = original.copy()
    scrambled["general_rep_votes"] = [1, 2, 3, 4, 5]
    scrambled["general_dem_votes"] = [900, 800, 700, 600, 500]

    for threshold in SELECTIVE_THRESHOLDS_PCT:
        before = evaluator.evaluate_condition(original, threshold)
        after = evaluator.evaluate_condition(scrambled, threshold)
        assert before["accepted"] == after["accepted"]
        assert before["abstained"] == after["abstained"]
        assert before["correct_abstained"] + before["wrong_abstained"] == (
            after["correct_abstained"] + after["wrong_abstained"]
        )


def test_decision_matches_the_pure_rule_row_by_row():
    cohort = make_cohort(FIXTURE)
    for threshold in SELECTIVE_THRESHOLDS_PCT:
        expected = sum(
            selective_rule(int(r.primary_rep_votes), int(r.primary_dem_votes), threshold)[0]
            for r in cohort.itertuples(index=False)
        )
        assert evaluator.evaluate_condition(cohort, threshold)["accepted"] == expected


# --------------------------------------------------------------------------
# Grid-level checks
# --------------------------------------------------------------------------


def test_grid_has_one_row_per_year_and_threshold():
    frame = make_cohort(FIXTURE, year=2018)
    grid = evaluator.evaluate_grid(frame, test_years=(2018,))
    assert len(grid) == len(SELECTIVE_THRESHOLDS_PCT)
    assert sorted(grid["t_pct"]) == sorted(SELECTIVE_THRESHOLDS_PCT)


def test_accepted_never_grows_with_the_threshold():
    frame = make_cohort(FIXTURE, year=2018)
    grid = evaluator.evaluate_grid(frame, test_years=(2018,))
    accepted = grid.sort_values("t_pct")["accepted"].tolist()
    for previous, current in zip(accepted, accepted[1:]):
        assert current <= previous


def test_monotonicity_check_detects_a_broken_grid():
    frame = make_cohort(FIXTURE, year=2018)
    grid = evaluator.evaluate_grid(frame, test_years=(2018,))
    broken = grid.copy()
    accepted_at_zero = int(broken.loc[broken["t_pct"] == 0, "accepted"].iloc[0])
    broken.loc[broken["t_pct"] == 10, "accepted"] = accepted_at_zero + 1
    assert evaluator.check_monotonicity(broken)


def test_monotonicity_check_detects_a_missing_accepted_count():
    frame = make_cohort(FIXTURE, year=2018)
    grid = evaluator.evaluate_grid(frame, test_years=(2018,))
    broken = grid.copy()
    broken.loc[broken["t_pct"] == 10, "accepted"] = float("nan")
    assert evaluator.check_monotonicity(broken)


def test_baseline_check_detects_a_wrong_baseline():
    frame = make_cohort(FIXTURE, year=2018)
    grid = evaluator.evaluate_grid(frame, test_years=(2018,))
    broken = grid.copy()
    broken.loc[broken["t_pct"] == 0, "wrong_accepted"] = 99
    assert evaluator.check_baseline(broken)


def test_baseline_check_passes_on_the_official_expectations():
    """The checker accepts a grid whose t=0 row matches the frozen contract."""
    rows = []
    for year in SELECTIVE_TEST_YEARS:
        n = EXPECTED_COHORT_SIZE[year]
        wrong = EXPECTED_BASELINE_ERRORS[year]
        rows.append(
            {
                "test_year": year,
                "t_pct": 0,
                "eligible": n,
                "accepted": n,
                "abstained": 0,
                "coverage": 1.0,
                "correct_accepted": n - wrong,
                "wrong_accepted": wrong,
                "selective_risk": wrong / n,
                "conditional_accuracy": (n - wrong) / n,
                "correct_abstained": 0,
                "wrong_abstained": 0,
                "wrong_per_eligible": wrong / n,
                "voting_house_groups": None,
                "accepted_over_voting_house_groups": float("nan"),
            }
        )
    grid = pd.DataFrame(rows)
    assert evaluator.check_baseline(grid) == []


# --------------------------------------------------------------------------
# Cohort contract inheritance
# --------------------------------------------------------------------------


def test_general_ties_are_excluded_from_the_cohort():
    rows = list(FIXTURE) + [(60, 40, 50, 50)]
    cohort = select_cohort(make_cohort(rows), 2022)
    assert len(cohort) == len(FIXTURE)
    assert "general_tie" not in cohort.columns or not cohort["general_tie"].any()


def test_voting_house_group_counts_drop_nonvoting_jurisdictions():
    elections = pd.DataFrame(
        [
            {"year": 2022, "state": "AA", "district": "01"},
            {"year": 2022, "state": "AA", "district": "02"},
        ]
    )
    exclusions = pd.DataFrame(
        [
            {"year": 2022, "state": "PR", "district": "01", "reason": "nonvoting-delegate-jurisdiction"},
            {"year": 2022, "state": "AA", "district": "09", "reason": "unopposed-primary"},
        ]
    )
    counts = evaluator.voting_house_groups_by_year(elections, exclusions)
    # selected (2) + excluded (2) - non-voting (1)
    assert counts == {2022: 3}


def test_voting_house_groups_never_fall_below_the_accepted_count():
    """The selection denominator must stay larger than any accepted count."""
    frame = make_cohort(FIXTURE, year=2022)
    elections = prepare_elections(
        pd.concat(
            [
                frame,
                prepare_elections(
                    pd.DataFrame(
                        [
                            {
                                "year": 2022,
                                "state": "BB",
                                "chamber": "House",
                                "district": "01",
                                "primary_rep_votes": 60,
                                "primary_dem_votes": 40,
                                "general_rep_votes": 55,
                                "general_dem_votes": 45,
                            }
                        ]
                    )
                ),
            ],
            ignore_index=True,
        )
    )
    exclusions = pd.DataFrame(
        [
            {"year": 2022, "state": "PR", "district": "01", "reason": "nonvoting-delegate-jurisdiction"},
        ]
    )
    groups = evaluator.voting_house_groups_by_year(elections, exclusions)
    grid = evaluator.evaluate_grid(
        frame, test_years=(2022,), voting_house_groups=groups
    )
    for row in grid.itertuples(index=False):
        assert row.accepted <= row.voting_house_groups
        assert row.accepted_over_voting_house_groups <= 1.0
