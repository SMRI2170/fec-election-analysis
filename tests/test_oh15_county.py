"""Regression guards against overstating a partial Ohio county crosscheck."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("oh15_county", ROOT / "scripts" / "audit_oh15_county.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture():
    return json.loads((ROOT / "data/sources/oh15_clark_2022_official_votes.json").read_text(encoding="utf-8"))


def test_clark_official_primary_and_general_values_are_less_than_district():
    r = mod.audit_county(fixture())
    assert r["complete_district_reconciliation_verified"] is False
    assert r["verification_level"] == "county_only_not_district_complete"
    assert {k: v["clark_county_votes"] for k, v in r["comparisons"].items()} == {
        "primary_rep_votes": 3398,
        "primary_dem_votes": 365,
        "general_rep_votes": 15671,
        "general_dem_votes": 5407,
    }


def test_cannot_mark_county_results_as_statewide_verification():
    data = fixture()
    data["verification_level"] = "district_complete"
    with pytest.raises(AssertionError, match="County data"):
        mod.audit_county(data)


def test_snapshot_changes_need_explicit_review():
    data = fixture()
    data["county_votes"]["general"]["Mike Carey (R)"] += 1
    with pytest.raises(AssertionError, match="source snapshot"):
        mod.audit_county(data)


def test_greater_than_district_votes_is_rejected():
    data = fixture()
    data["county_votes"]["primary"]["Mike Carey (R)"] = 50000
    with pytest.raises(AssertionError, match="cannot equal/exceed"):
        mod.audit_county(data)


def test_fec_baseline_drift_is_rejected(tmp_path):
    report = mod.audit_county(fixture())
    path = tmp_path / "elections.csv"
    path.write_text(
        "year,state,district,primary_rep_votes,primary_dem_votes,general_rep_votes,general_dem_votes\n"
        "2022,OH,15,48938,9047,143113,108139\n", encoding="utf-8"
    )
    with pytest.raises(AssertionError, match="FEC normalized votes changed"):
        mod.compare_fec_csv(report, path)
