import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "audit_selection_observability", ROOT / "scripts" / "audit_selection_observability.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def raw_fixture():
    rows = [
        ["AA", "01", "HAA01", "R", 55, 60, None],
        ["AA", "01", "HAA02", "D", 45, 40, None],
        ["AA", "01", None, "R", 55, None, "Party Votes:"],
        ["AA", "01", None, "D", 45, None, "Party Votes:"],
        ["BB", "02", "HBB01", "R", "Unopposed", 75, None],
        ["BB", "02", "HBB02", "D", 30, None, None],
        ["BB", "02", None, "R", "Unopposed", None, "Party Votes:"],
        ["BB", "02", None, "D", 30, None, "Party Votes:"],
    ]
    frame = pd.DataFrame(
        rows, columns=[
            "STATE ABBREVIATION", "DISTRICT", "FEC ID", "PARTY",
            "PRIMARY VOTES", "GENERAL VOTES", "TOTAL VOTES",
        ],
    )
    frame["_state"] = frame["STATE ABBREVIATION"]
    frame["_district"] = frame["DISTRICT"]
    frame["_candidate"] = frame["FEC ID"].notna()
    frame["_party"] = frame["PARTY"].astype("string")
    frame["_marker"] = frame["TOTAL VOTES"].astype("string").str.lower()
    return frame


def selections():
    included = pd.DataFrame([{"year": 2022, "state": "AA", "district": "01"}])
    excluded = pd.DataFrame([
        {"year": 2022, "state": "BB", "district": "02", "reason": "unopposed-primary"}
    ])
    return included, excluded


def test_source_coverage_keeps_missing_primary_without_imputation():
    included, excluded = selections()
    rows, aggregates, totals = module.diagnose(included, excluded, {2022: raw_fixture()})
    assert len(rows) == 2
    assert totals["included"] == 1 and totals["excluded"] == 1
    assert totals["missing_votes_imputed"] is False
    selected = rows.loc[rows["included"]].iloc[0]
    unopposed = rows.loc[~rows["included"]].iloc[0]
    assert selected["primary_r_reported_share"] == pytest.approx(0.55)
    assert bool(unopposed["primary_reported_both"]) is False
    assert pd.isna(unopposed["primary_r_reported_share"])
    assert unopposed["r_primary_unopposed_rows"] == 1
    assert len(aggregates) == 2


def test_observed_general_share_is_only_a_diagnostic():
    included, excluded = selections()
    rows, _, totals = module.diagnose(included, excluded, {2022: raw_fixture()})
    assert totals["general_outcomes_are_post_election_diagnostics_not_features"]
    by_state = rows.set_index("state")
    assert by_state.loc["AA", "general_observed_abs_margin"] == pytest.approx(0.2)
    assert by_state.loc["BB", "general_observed_r_share"] == pytest.approx(75 / 105)


def test_missing_general_votes_are_not_treated_as_zero():
    frame = raw_fixture()
    frame.loc[(frame["_state"] == "BB") & (frame["_party"] == "D") &
              frame["_candidate"], "GENERAL VOTES"] = None
    inc, exc = selections()
    rows, _, coverage = module.diagnose(inc, exc, {2022: frame})
    assert coverage["general_two_party_numeric_excluded"] == 0
    assert pd.isna(rows.loc[rows["state"] == "BB", "general_observed_abs_margin"].iloc[0])


def test_unaccounted_or_duplicate_source_groups_fail():
    inc, exc = selections()
    with pytest.raises(AssertionError, match="Unaccounted"):
        module.diagnose(inc.iloc[:0], exc, {2022: raw_fixture()})
    duplicate = pd.concat([exc, exc], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate"):
        module.diagnose(inc, duplicate, {2022: raw_fixture()})
