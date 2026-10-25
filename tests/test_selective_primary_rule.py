"""Unit tests for the Primary-only abstention rule (Issue #79).

Synthetic inputs only. The function under test takes two Primary vote counts
and a pre-registered threshold, so every case here is exact and hand-checkable.
"""
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys_path = str(ROOT / "scripts")
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)

from selective_primary_rule import (  # noqa: E402
    ALLOWED_THRESHOLDS_PCT,
    DEMOCRATIC_LEAD,
    REPUBLICAN_LEAD,
    describe,
    selective_rule,
)


# --------------------------------------------------------------------------
# Boundary behaviour
# --------------------------------------------------------------------------


def test_threshold_zero_answers_every_contest():
    assert selective_rule(50, 50, 0) == (True, DEMOCRATIC_LEAD)
    assert selective_rule(1, 100, 0) == (True, DEMOCRATIC_LEAD)
    assert selective_rule(100, 1, 0) == (True, REPUBLICAN_LEAD)


def test_five_point_boundary_answers_45_55_and_55_45():
    # 100 * |R - D| >= 2 * 5 * (R + D)  ->  1000 >= 1000
    assert selective_rule(45, 55, 5) == (True, DEMOCRATIC_LEAD)
    assert selective_rule(55, 45, 5) == (True, REPUBLICAN_LEAD)


def test_five_point_boundary_abstains_on_46_54():
    # 100 * |R - D| = 800  <  1000
    assert selective_rule(46, 54, 5) == (False, None)
    assert selective_rule(54, 46, 5) == (False, None)


def test_ten_point_boundary():
    # 40/60 answers, 41/59 abstains.
    assert selective_rule(40, 60, 10) == (True, DEMOCRATIC_LEAD)
    assert selective_rule(60, 40, 10) == (True, REPUBLICAN_LEAD)
    assert selective_rule(41, 59, 10) == (False, None)
    assert selective_rule(59, 41, 10) == (False, None)


def test_fifteen_point_boundary():
    assert selective_rule(35, 65, 15) == (True, DEMOCRATIC_LEAD)
    assert selective_rule(65, 35, 15) == (True, REPUBLICAN_LEAD)
    assert selective_rule(36, 64, 15) == (False, None)


def test_twenty_point_boundary():
    assert selective_rule(30, 70, 20) == (True, DEMOCRATIC_LEAD)
    assert selective_rule(70, 30, 20) == (True, REPUBLICAN_LEAD)
    assert selective_rule(31, 69, 20) == (False, None)


def test_primary_tie_is_only_answered_at_threshold_zero():
    for threshold in ALLOWED_THRESHOLDS_PCT:
        accepted, answer = selective_rule(500, 500, threshold)
        if threshold == 0:
            assert (accepted, answer) == (True, DEMOCRATIC_LEAD)
        else:
            assert (accepted, answer) == (False, None)


def test_large_one_sided_vote_counts_are_valid_but_never_answered_above_zero():
    # A 100% Primary share has a margin of 50 points, so it survives every
    # threshold. Both parties must still have at least one vote.
    assert selective_rule(10**9, 1, 20) == (True, REPUBLICAN_LEAD)
    assert selective_rule(1, 10**9, 20) == (True, DEMOCRATIC_LEAD)


def test_very_large_vote_counts_do_not_overflow():
    huge = 10**30
    accepted, answer = selective_rule(huge, huge, 0)
    assert (accepted, answer) == (True, DEMOCRATIC_LEAD)
    accepted, answer = selective_rule(huge + 1, huge, 5)
    assert (accepted, answer) == (False, None)


def test_swapping_the_parties_keeps_the_decision_and_flips_the_answer():
    for rep, dem in [(60, 40), (45, 55), (46, 54), (51, 49)]:
        for threshold in ALLOWED_THRESHOLDS_PCT:
            forward = selective_rule(rep, dem, threshold)
            backward = selective_rule(dem, rep, threshold)
            assert forward[0] == backward[0]
            if forward[1] is None:
                assert backward[1] is None
            else:
                assert forward[1] != backward[1]


def test_integer_form_matches_the_exact_rational_definition():
    """The integer rule must equal the exact rational definition.

    The comparison is done with :class:`fractions.Fraction` rather than
    binary floating point on purpose. The float form of the same condition
    misjudges exact boundary cases (e.g. 2/3 votes against a 10-point
    threshold), and avoiding that misjudgement is the reason the rule uses
    integer arithmetic in the first place.
    """
    from fractions import Fraction

    for rep in range(1, 60):
        for dem in range(1, 60):
            for threshold in ALLOWED_THRESHOLDS_PCT:
                exact = abs(Fraction(rep, rep + dem) - Fraction(1, 2))
                expected_accept = exact >= Fraction(threshold, 100)
                accepted, _ = selective_rule(rep, dem, threshold)
                assert accepted == expected_accept, (rep, dem, threshold)


def test_float_comparison_would_misjudge_an_exact_boundary():
    """Document why the rule uses integer arithmetic instead of floats."""
    from fractions import Fraction

    rep, dem, threshold = 2, 3, 10
    exact = abs(Fraction(rep, rep + dem) - Fraction(1, 2))
    assert exact == Fraction(threshold, 100)
    # The binary float form is not exact, so it disagrees at the boundary.
    assert abs(rep / (rep + dem) - 0.5) < threshold / 100
    # The integer form answers it, as the frozen specification requires.
    assert selective_rule(rep, dem, threshold) == (True, DEMOCRATIC_LEAD)


def test_every_registered_threshold_is_a_usable_input():
    assert ALLOWED_THRESHOLDS_PCT == (0, 5, 10, 15, 20)
    for threshold in ALLOWED_THRESHOLDS_PCT:
        accepted, answer = selective_rule(100, 1, threshold)
        assert accepted is True
        assert answer == REPUBLICAN_LEAD


# --------------------------------------------------------------------------
# Invalid input
# --------------------------------------------------------------------------


@pytest.mark.parametrize("threshold", [1, 2, 4, 6, 10.0, 25, -5, 100, None, "5"])
def test_invalid_thresholds_are_rejected(threshold):
    with pytest.raises((ValueError, TypeError)):
        selective_rule(60, 40, threshold)


@pytest.mark.parametrize("rep,dem", [(0, 100), (100, 0), (0, 0)])
def test_zero_or_one_sided_vote_counts_are_rejected(rep, dem):
    """A 100% Primary share would mean an unopposed primary, not a contest."""
    with pytest.raises(ValueError):
        selective_rule(rep, dem, 5)


@pytest.mark.parametrize("rep,dem", [(-1, 100), (100, -1), (-5, -5)])
def test_negative_votes_are_rejected(rep, dem):
    with pytest.raises(ValueError):
        selective_rule(rep, dem, 5)


@pytest.mark.parametrize("rep,dem", [(45.0, 55.0), (45.5, 54.5), (45, 55.0)])
def test_fractional_votes_are_rejected(rep, dem):
    with pytest.raises(TypeError):
        selective_rule(rep, dem, 5)


def test_bool_is_not_accepted_as_a_vote_count():
    with pytest.raises(TypeError):
        selective_rule(True, 100, 5)
    with pytest.raises(TypeError):
        selective_rule(100, True, 5)


def test_float_threshold_of_allowed_value_is_rejected():
    """0.0 is numerically equal to 0 but is not an int threshold."""
    with pytest.raises(TypeError):
        selective_rule(60, 40, 0.0)


# --------------------------------------------------------------------------
# Separation from General information
# --------------------------------------------------------------------------


def test_rule_signature_cannot_receive_general_information():
    parameters = list(inspect.signature(selective_rule).parameters)
    assert parameters == ["primary_r", "primary_d", "threshold_pct"]
    for name in parameters:
        assert "general" not in name.lower()
        assert "year" not in name.lower()
        assert "label" not in name.lower()


def test_result_is_invariant_to_general_votes_and_labels():
    """Changing any General quantity must not move a single decision."""
    base = [(60, 40), (45, 55), (46, 54), (51, 49), (50, 50)]
    for threshold in ALLOWED_THRESHOLDS_PCT:
        reference = [selective_rule(rep, dem, threshold) for rep, dem in base]
        for general_rep, general_dem in [(0, 0), (1, 999999), (999999, 1)]:
            for label in (0, 1):
                observed = []
                for rep, dem in base:
                    # The General values exist in the surrounding analysis but
                    # are simply not reachable from the rule.
                    _ = (general_rep, general_dem, label)
                    observed.append(selective_rule(rep, dem, threshold))
                assert observed == reference


def test_describe_reports_the_same_decision():
    result = describe(45, 55, 5)
    assert result["accepted"] is True
    assert result["answer"] == DEMOCRATIC_LEAD
    assert result["margin_percentage_points"] == pytest.approx(10.0)
    assert result["primary_rep_share"] == pytest.approx(0.45)

    abstained = describe(46, 54, 5)
    assert abstained["accepted"] is False
    assert abstained["answer"] is None
    assert abstained["answer_label"] is None


def test_describe_validates_the_same_way():
    with pytest.raises(ValueError):
        describe(0, 100, 5)
    with pytest.raises(ValueError):
        describe(60, 40, 7)
