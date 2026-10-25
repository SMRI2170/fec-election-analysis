"""Unit tests for the random-abstention comparison (Issue #81).

Synthetic fixtures only. The official 15-condition comparison is produced by
the official-FEC GitHub Actions workflow.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
for extra in (str(ROOT / "scripts"), str(ROOT / "src")):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from fec_analysis.core import prepare_elections  # noqa: E402
from evaluate_selective_primary import evaluate_grid  # noqa: E402


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


comparator = _load_script("compare_random_abstention")


def make_cohort(specs: list[tuple[int, int, int, int]], year: int = 2022):
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


#: Two clear Republicans, two clear Democrats and one contest that is razor thin
#: in the primary and wrong in the general.
FIXTURE = [
    (70, 30, 65, 35),
    (60, 40, 55, 45),
    (30, 70, 35, 65),
    (40, 60, 45, 55),
    (51, 49, 40, 60),
]


# --------------------------------------------------------------------------
# Hypergeometric reference
# --------------------------------------------------------------------------


def test_hypergeometric_pmf_sums_to_one():
    distribution = comparator.hypergeometric_distribution(241, 24, 199)
    assert sum(distribution.values()) == pytest.approx(1.0)


def test_hypergeometric_pmf_matches_the_closed_form():
    population, errors, draws = 20, 7, 9
    distribution = comparator.hypergeometric_distribution(population, errors, draws)
    for x, probability in distribution.items():
        expected = (
            math.comb(errors, x)
            * math.comb(population - errors, draws - x)
            / math.comb(population, draws)
        )
        assert probability == pytest.approx(expected)


def test_hypergeometric_pmf_is_zero_outside_the_support():
    # With N=20, E=7 and K=15 the support is x in [2, 7].
    assert comparator.hypergeometric_pmf(20, 7, 15, 1) == 0.0
    assert comparator.hypergeometric_pmf(20, 7, 15, 8) == 0.0
    assert comparator.hypergeometric_pmf(20, 7, 15, 7) > 0.0


def test_hypergeometric_pmf_rejects_impossible_parameters():
    with pytest.raises(ValueError):
        comparator.hypergeometric_pmf(10, 20, 5, 1)
    with pytest.raises(ValueError):
        comparator.hypergeometric_pmf(10, 5, 20, 1)
    with pytest.raises(ValueError):
        comparator.hypergeometric_pmf(0, 0, 0, 0)


# --------------------------------------------------------------------------
# Baseline values and edge cases
# --------------------------------------------------------------------------


def test_expected_error_count_is_k_times_e_over_n():
    baseline = comparator.random_abstention_baseline(241, 24, 199)
    assert baseline["random_abstention_expected_wrong"] == pytest.approx(
        199 * 24 / 241
    )


def test_accepting_everything_equals_the_observed_error_count():
    """At t = 0 the rule answers everything, so expected == observed."""
    cohort = make_cohort(FIXTURE)
    grid = evaluate_grid(cohort, test_years=(2022,))
    compared = comparator.compare_grid(grid)
    zero = compared[compared["t_pct"] == 0].iloc[0]
    assert zero["accepted"] == zero["all_eligible"]
    assert zero["random_abstention_expected_wrong"] == pytest.approx(
        float(zero["wrong_accepted"])
    )
    assert zero["error_avoidance_vs_random"] == pytest.approx(0.0)
    assert zero["p_random_at_least_as_good"] == pytest.approx(1.0)


def test_accepting_nothing_is_a_degenerate_baseline():
    baseline = comparator.random_abstention_baseline(241, 24, 0)
    assert baseline["random_abstention_expected_wrong"] == 0.0
    assert baseline["random_abstention_sd"] == 0.0


def test_accepting_everything_is_a_degenerate_baseline():
    baseline = comparator.random_abstention_baseline(241, 24, 241)
    assert baseline["random_abstention_expected_wrong"] == pytest.approx(24.0)
    assert baseline["random_abstention_sd"] == 0.0
    distribution = comparator.hypergeometric_distribution(241, 24, 241)
    assert set(distribution) == {24}


def test_all_correct_cohort():
    baseline = comparator.random_abstention_baseline(10, 0, 4)
    assert baseline["random_abstention_expected_wrong"] == 0.0
    assert comparator.hypergeometric_distribution(10, 0, 4) == {0: 1.0}


def test_all_wrong_cohort():
    baseline = comparator.random_abstention_baseline(10, 10, 4)
    assert baseline["random_abstention_expected_wrong"] == pytest.approx(4.0)
    assert comparator.hypergeometric_distribution(10, 10, 4) == {4: 1.0}


def test_single_contest_cohort_does_not_divide_by_zero():
    baseline = comparator.random_abstention_baseline(1, 1, 1)
    assert baseline["random_abstention_sd"] == 0.0


def test_invalid_parameters_are_rejected():
    with pytest.raises(ValueError):
        comparator.random_abstention_baseline(0, 0, 0)
    with pytest.raises(ValueError):
        comparator.random_abstention_baseline(10, 20, 5)
    with pytest.raises(ValueError):
        comparator.random_abstention_baseline(10, 5, 20)


def test_expected_value_is_not_rounded_away():
    """The expectation is a float; the columns must keep full precision."""
    baseline = comparator.random_abstention_baseline(237, 24, 149)
    assert baseline["random_abstention_expected_wrong"] == 149 * 24 / 237
    assert baseline["random_abstention_expected_wrong"] != round(
        baseline["random_abstention_expected_wrong"], 0
    )


# --------------------------------------------------------------------------
# Exploratory p-value
# --------------------------------------------------------------------------


def test_p_value_is_one_when_the_observation_sits_at_the_expectation():
    """Accepting everything leaves the error count unchanged, so p = 1."""
    distribution = comparator.hypergeometric_distribution(241, 24, 241)
    expected = 241 * 24 / 241
    value = comparator.exploratory_p_value(24, distribution, expected)
    assert value == pytest.approx(1.0)


def test_p_value_is_small_when_the_observation_is_better_than_expected():
    distribution = comparator.hypergeometric_distribution(241, 24, 95)
    expected = 95 * 24 / 241
    value = comparator.exploratory_p_value(0, distribution, expected)
    assert value < 0.01


def test_p_value_uses_the_mirrored_tail_when_the_observation_is_worse():
    """An observation above the expectation is scored in the upper tail."""
    distribution = comparator.hypergeometric_distribution(20, 5, 10)
    expected = 10 * 5 / 20
    good = comparator.exploratory_p_value(0, distribution, expected)
    bad = comparator.exploratory_p_value(5, distribution, expected)
    assert good < 0.05
    # Observing the maximum possible error count is at least as extreme in the
    # wrong direction, so the mirrored tail is a small but non-zero value.
    assert 0.0 < bad < 0.5


# --------------------------------------------------------------------------
# Grid integration
# --------------------------------------------------------------------------


def test_comparison_keeps_every_issue_80_column_unchanged():
    cohort = make_cohort(FIXTURE)
    grid = evaluate_grid(cohort, test_years=(2022,))
    compared = comparator.compare_grid(grid)
    for column in grid.columns:
        assert column in compared.columns
        for original, new in zip(grid[column], compared[column]):
            if pd.isna(original) and pd.isna(new):
                continue
            assert original == new or original == pytest.approx(new)


def test_accepted_count_changes_with_the_threshold():
    cohort = make_cohort(FIXTURE)
    grid = evaluate_grid(cohort, test_years=(2022,))
    compared = comparator.compare_grid(grid)
    accepted = compared.sort_values("t_pct")["accepted"].tolist()
    assert accepted[0] == len(FIXTURE)
    for previous, current in zip(accepted, accepted[1:]):
        assert current <= previous


def test_reference_grid_check_passes_for_an_unchanged_grid():
    cohort = make_cohort(FIXTURE)
    grid = evaluate_grid(cohort, test_years=(2022,))
    compared = comparator.compare_grid(grid)
    assert comparator.verify_against_reference_grid(compared, grid) == []


def test_reference_grid_check_detects_a_changed_aggregate():
    cohort = make_cohort(FIXTURE)
    grid = evaluate_grid(cohort, test_years=(2022,))
    compared = comparator.compare_grid(grid)
    broken = grid.copy()
    broken.loc[broken["t_pct"] == 0, "wrong_accepted"] = 99
    problems = comparator.verify_against_reference_grid(compared, broken)
    assert any("wrong_accepted" in problem for problem in problems)


def test_reference_grid_check_detects_a_changed_row_count():
    cohort = make_cohort(FIXTURE)
    grid = evaluate_grid(cohort, test_years=(2022,))
    compared = comparator.compare_grid(grid)
    problems = comparator.verify_against_reference_grid(compared, grid.iloc[:-1])
    assert problems
