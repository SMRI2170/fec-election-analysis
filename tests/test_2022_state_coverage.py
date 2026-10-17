"""Fail-closed verification levels for 2022 top five cases."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("validate_sources",ROOT/"scripts"/"validate_2022_state_coverage.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def fixture():
    return json.loads((ROOT/"data/sources/2022_state_evidence_coverage.json").read_text(encoding="utf-8"))

def test_complete_matrix_has_only_two_whole_cases():
    got=mod.validate_ledger(fixture(),ROOT)
    assert got["district_verified_party_stages"]==11
    assert got["partial_subdistrict_party_stages"]==6
    assert got["not_verified_party_stages"]==3
    assert got["whole_cases_verified_primary_and_general"]==2
    assert got["source_discovery_is_not_verification"] is True

def test_found_nh_sos_document_is_not_independent_vote_comparison():
    d=fixture()
    d["cases"]["NH-01"]["general"]["R"]["level"]="district_verified"
    with pytest.raises(AssertionError,match="Independent district votes"):
        mod.validate_ledger(d,ROOT)

def test_oh15_clark_only_may_not_become_entire_district():
    d=fixture()
    d["cases"]["OH-15"]["general"]["D"]["level"]="district_verified"
    with pytest.raises(AssertionError,match="Independent district votes"):
        mod.validate_ledger(d,ROOT)

def test_nh01_democratic_primary_does_not_verify_republican_primary():
    d=fixture()
    d["cases"]["NH-01"]["primary"]["R"]["votes"]=75401
    with pytest.raises(AssertionError,match="Unverified source may not carry"):
        mod.validate_ledger(d,ROOT)

def test_unverified_missing_source_does_not_allow_false_completion():
    d=fixture()
    d["cases"]["OH-09"]["primary"]["R"]["level"]="district_verified"
    d["cases"]["OH-09"]["primary"]["R"]["votes"]=61090
    d["cases"]["OH-09"]["primary"]["R"]["evidence"]="data/sources/not_a_real_file.json"
    d["cases"]["OH-09"]["primary"]["R"]["source_url"]="https://example.org"
    with pytest.raises(AssertionError,match="Evidence file missing"):
        mod.validate_ledger(d,ROOT)

def test_unexpected_party_or_scope_rejected():
    d=fixture()
    d["cases"]["MI-03"]["general"]["other"]={"level":"not_verified","votes":None,"evidence":None,"source_url":None}
    with pytest.raises(AssertionError,match="Missing R/D party"):
        mod.validate_ledger(d,ROOT)

def test_stale_fec_normalization_rejected(tmp_path):
    d=fixture()
    path=tmp_path/"elections.csv"
    path.write_text(
       "year,state,district,primary_rep_votes,primary_dem_votes,general_rep_votes,general_dem_votes\n"
       "2022,NH,01,75401,42368,142230,167391\n",encoding="utf-8")
    with pytest.raises(AssertionError,match="Missing FEC baseline"):
        mod.validate_ledger(d,ROOT,path)
