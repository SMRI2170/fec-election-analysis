"""Certified eight-county Ohio congressional General election crosscheck."""
import importlib.util
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("oh09_general", ROOT / "scripts" / "verify_oh09_general_canvass.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture():
    return json.loads((ROOT / "data/sources/oh09_2022_official_general_canvass.json").read_text(encoding="utf-8"))


def test_certified_eight_county_candidate_sums_exactly_match():
    report = mod.audit_canvass(fixture())
    assert report["official_certified_2022_general_totals"] == {
        "general_rep_votes": 115362, "general_dem_votes": 150655}
    assert report["all_eight_official_counties_reconciled"] is True
    assert report["official_primary_reconciled"] is False


def test_changed_official_county_votes_must_fail():
    data = fixture()
    data["counties"]["Defiance"]["Marcy Kaptur (D)"] += 1
    with pytest.raises(AssertionError, match="County vs published official total"):
        mod.audit_canvass(data)


def test_missing_county_must_fail():
    data = fixture()
    del data["counties"]["Wood"]
    with pytest.raises(AssertionError, match="8-county"):
        mod.audit_canvass(data)


def test_invalid_primary_certification_claim_must_fail():
    data = fixture()
    data["verification"]["primary_district_complete"] = True
    with pytest.raises(AssertionError, match="General-only"):
        mod.audit_canvass(data)


def test_reject_fec_mismatch(tmp_path):
    path = tmp_path / "elections.csv"
    path.write_text(
        "year,state,district,general_rep_votes,general_dem_votes\n"
        "2022,OH,09,115362,150656\n", encoding="utf-8")
    report = mod.audit_canvass(fixture())
    with pytest.raises(AssertionError, match="Independent Ohio canvass"):
        mod.compare_fec_csv(report, path)
