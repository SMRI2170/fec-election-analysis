"""Unit tests for the frozen selective-prediction cohort contract.

These tests use **synthetic fixtures only**. The real FEC numbers
(916 / 1,734 / 1,756 and 241 / 237 / 238 with 24 errors each) are verified in
the official-FEC GitHub Actions workflow, not here.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fec_analysis.selective import (  # noqa: E402
    EXPECTED_BASELINE_ACCURACY,
    EXPECTED_BASELINE_ERRORS,
    EXPECTED_COHORT_SIZE,
    SELECTIVE_TEST_YEARS,
    audit_contracts,
    audit_key_uniqueness,
    audit_report_group_containment,
    audit_vote_integrity,
    baseline_scores,
    load_elections,
    majority_prediction,
    select_cohort,
)


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_frame(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal normalized-record frame with the required columns."""
    columns = [
        "year",
        "state",
        "chamber",
        "district",
        "primary_rep_votes",
        "primary_dem_votes",
        "general_rep_votes",
        "general_dem_votes",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    frame["district"] = frame["district"].astype(str)
    return frame


def synthetic_rows() -> list[dict]:
    """Two contests per year: one clear Republican, one clear Democratic."""
    rows: list[dict] = []
    for year in (2016, 2018, 2020, 2022):
        for index, (p_rep, p_dem, g_rep, g_dem) in enumerate(
            [
                (60, 40, 55, 45),
                (30, 70, 25, 75),
            ],
            start=1,
        ):
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
    return rows


# --------------------------------------------------------------------------
# Cohort selection
# --------------------------------------------------------------------------


def test_select_cohort_drops_general_ties():
    rows = synthetic_rows()
    rows.append(
        {
            "year": 2018,
            "state": "AA",
            "chamber": "House",
            "district": "03",
            "primary_rep_votes": 60,
            "primary_dem_votes": 40,
            "general_rep_votes": 50,
            "general_dem_votes": 50,
        }
    )
    cohort = select_cohort(load_elections_from_frame(make_frame(rows)), 2018)
    assert len(cohort) == 2
    assert "03" not in set(cohort["district"])


def test_select_cohort_keeps_other_years_out():
    frame = load_elections_from_frame(make_frame(synthetic_rows()))
    cohort = select_cohort(frame, 2020)
    assert set(cohort["year"]) == {2020}


def test_select_cohort_rejects_an_unprepared_frame():
    with pytest.raises(ValueError, match="prepare_elections"):
        select_cohort(make_frame(synthetic_rows()), 2020)


def test_majority_rule_predicts_democratic_when_primary_is_exactly_tied():
    frame = make_frame(
        [
            {
                "year": 2020,
                "state": "AA",
                "chamber": "House",
                "district": "01",
                "primary_rep_votes": 50,
                "primary_dem_votes": 50,
                "general_rep_votes": 60,
                "general_dem_votes": 40,
            }
        ]
    )
    prepared = load_elections_from_frame(frame)
    cohort = select_cohort(prepared, 2020)
    assert list(majority_prediction(cohort)) == [0]


def load_elections_from_frame(frame: pd.DataFrame) -> pd.DataFrame:
    from fec_analysis.core import prepare_elections

    return prepare_elections(frame)


def test_baseline_scores_count_errors_and_accuracy():
    frame = load_elections_from_frame(make_frame(synthetic_rows()))
    cohort = select_cohort(frame, 2022)
    scores = baseline_scores(cohort)
    assert scores["eligible"] == 2
    assert scores["correct"] == 2
    assert scores["wrong"] == 0
    assert scores["accuracy"] == 1.0


def test_baseline_scores_flag_a_single_error():
    rows = synthetic_rows()
    for row in rows:
        if row["year"] == 2022 and row["district"] == "01":
            row["general_rep_votes"] = 10
            row["general_dem_votes"] = 90
    frame = load_elections_from_frame(make_frame(rows))
    cohort = select_cohort(frame, 2022)
    scores = baseline_scores(cohort)
    assert scores["wrong"] == 1
    assert scores["correct"] == 1
    assert scores["accuracy"] == 0.5


def test_baseline_scores_reject_an_empty_cohort():
    frame = load_elections_from_frame(make_frame(synthetic_rows()))
    with pytest.raises(ValueError):
        baseline_scores(select_cohort(frame, 1999))


# --------------------------------------------------------------------------
# Audits
# --------------------------------------------------------------------------


def test_key_uniqueness_flags_duplicates():
    rows = synthetic_rows()
    rows.append(dict(rows[0]))
    report = audit_key_uniqueness(make_frame(rows))
    assert report["duplicate_keys"] == 1
    assert report["rows"] == len(rows)


def test_vote_integrity_flags_negative_and_fractional_votes():
    rows = synthetic_rows()
    rows[0]["primary_rep_votes"] = -5
    rows[1]["primary_dem_votes"] = 10.5
    report = audit_vote_integrity(make_frame(rows))
    assert report["negative_votes"] == 1
    assert report["fractional_votes"] == 1


def test_vote_integrity_flags_non_positive_two_party_totals():
    rows = synthetic_rows()
    rows[0]["primary_rep_votes"] = 0
    rows[1]["general_dem_votes"] = 0
    report = audit_vote_integrity(make_frame(rows))
    assert report["non_positive_primary"] == 1
    assert report["non_positive_general"] == 1


def test_containment_keeps_the_three_denominators_apart():
    frame = make_frame(synthetic_rows())
    exclusions = pd.DataFrame(
        [
            {"year": 2022, "state": "PR", "district": "01", "reason": "nonvoting-delegate-jurisdiction"},
            {"year": 2022, "state": "BB", "district": "01", "reason": "unopposed-primary"},
        ]
    )
    report = audit_report_group_containment(frame, exclusions)
    assert report["report_groups"] == 10
    assert report["nonvoting_groups"] == 1
    assert report["voting_house_groups"] == 9
    assert report["selected_rows"] == 8
    assert report["nonvoting_jurisdictions_in_cohort"] == []


def test_containment_flags_a_nonvoting_jurisdiction_inside_the_cohort():
    rows = synthetic_rows()
    rows[0]["state"] = "PR"
    frame = make_frame(rows)
    exclusions = pd.DataFrame(
        [{"year": 2022, "state": "PR", "district": "01", "reason": "nonvoting-delegate-jurisdiction"}]
    )
    report = audit_report_group_containment(frame, exclusions)
    assert report["nonvoting_jurisdictions_in_cohort"] == ["PR"]


def test_audit_contracts_reports_failure_when_a_year_moves():
    rows = synthetic_rows()
    frame = load_elections_from_frame(make_frame(rows))
    exclusions = pd.DataFrame(
        columns=["year", "state", "district", "reason"]
    )
    report = audit_contracts(frame, exclusions, test_years=(2018,))
    # The synthetic cohort cannot satisfy the official 241-contest contract.
    assert report["per_year"]["2018"]["eligible_matches"] is False
    assert report["all_contracts_satisfied"] is False


def test_audit_contracts_can_be_satisfied_on_a_synthetic_fixture(monkeypatch):
    """The audit passes when every contract is met, proving it is not a stub."""
    import fec_analysis.selective as selective

    frame = load_elections_from_frame(make_frame(synthetic_rows()))
    exclusions = pd.DataFrame(
        columns=["year", "state", "district", "reason"]
    )
    monkeypatch.setattr(selective, "EXPECTED_COHORT_SIZE", {2018: 2})
    monkeypatch.setattr(selective, "EXPECTED_BASELINE_ERRORS", {2018: 0})
    monkeypatch.setattr(selective, "EXPECTED_BASELINE_ACCURACY", {2018: 1.0})
    monkeypatch.setattr(selective, "EXPECTED_REPORT_GROUPS", 8)
    monkeypatch.setattr(selective, "EXPECTED_NONVOTING_GROUPS", 0)
    monkeypatch.setattr(selective, "EXPECTED_VOTING_HOUSE_GROUPS", 8)
    monkeypatch.setattr(selective, "EXPECTED_SELECTED_ROWS", 8)
    report = selective.audit_contracts(frame, exclusions, test_years=(2018,))
    assert report["all_contracts_satisfied"] is True


# --------------------------------------------------------------------------
# Agreement with the pre-existing evaluation code
# --------------------------------------------------------------------------


def test_baseline_rule_matches_the_existing_analyze_script():
    """The contract must agree with `scripts/analyze.py`'s primary-winner rule."""
    analyze = _load_script("analyze")
    frame = load_elections_from_frame(make_frame(synthetic_rows()))
    scores = analyze.evaluate(frame, 2020, "House")
    rule = scores[
        (scores["model"] == "primary-winner rule") & (scores["metric"] == "accuracy")
    ]
    cohort = select_cohort(frame, 2020)
    ours = baseline_scores(cohort)
    assert float(rule.iloc[0]["score"]) == pytest.approx(ours["accuracy"])
    assert int(rule.iloc[0]["n_test"]) == ours["eligible"]


def test_contract_constants_match_the_frozen_issue_specification():
    assert SELECTIVE_TEST_YEARS == (2018, 2020, 2022)
    assert EXPECTED_COHORT_SIZE == {2018: 241, 2020: 237, 2022: 238}
    assert EXPECTED_BASELINE_ERRORS == {2018: 24, 2020: 24, 2022: 24}
    assert EXPECTED_BASELINE_ACCURACY == {
        2018: 0.9004,
        2020: 0.8987,
        2022: 0.8992,
    }


def test_load_elections_round_trip(tmp_path):
    frame = load_elections_from_frame(make_frame(synthetic_rows()))
    path = tmp_path / "elections.csv"
    frame.to_csv(path, index=False)
    reloaded = load_elections(path)
    assert len(reloaded) == len(frame)
    assert list(reloaded.columns) == list(frame.columns)
