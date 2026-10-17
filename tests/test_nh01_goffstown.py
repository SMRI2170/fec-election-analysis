"""Certified NH-01 town Republican-primary and General independent-source regression."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("nh_goffstown",ROOT/"scripts"/"audit_nh01_goffstown.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture():
    return (json.loads((ROOT/"data/sources/nh01_goffstown_2022_primary_general.json").read_text(encoding="utf-8")),
            json.loads((ROOT/"data/sources/nh01_alton_2022_general_partial.json").read_text(encoding="utf-8")))

def test_town_primary_and_two_town_general_are_not_falsely_full_district():
    s,a=fixture()
    r=mod.audit_municipal_votes(s,a)
    assert r["republican_primary"]["named_candidate_votes"]==1940
    assert r["republican_primary"]["writein_votes_on_republican_ballot"]==7
    assert r["republican_primary"]["town_republican_valid_votes"]==1947
    assert r["republican_primary"]["district_republican_primary_independently_verified"] is False
    assert r["general"]["two_town_votes"]=={"R":5656,"D":5179}
    assert not r["general"]["district_general_independently_verified"]

def test_cross_party_writein_remains_republican_ballot_vote():
    s,a=fixture()
    s["independent_source_scope"]["do_not_move_cross_party_writein_to_democratic_primary"]=False
    with pytest.raises(AssertionError,match="cross-party voting"):
        mod.audit_municipal_votes(s,a)

def test_candidate_transcription_error_caught():
    s,a=fixture()
    s["republican_primary"]["named_candidate_votes"]["Karoline Leavitt"]+=1
    with pytest.raises(AssertionError,match="primary named candidates"):
        mod.audit_municipal_votes(s,a)

def test_undervotes_do_not_enter_party_subtotal():
    s,a=fixture()
    s["republican_primary"]["counted_valid_republican_primary_votes"]=2010
    with pytest.raises(AssertionError,match="tally not reconciled"):
        mod.audit_municipal_votes(s,a)

def test_municipal_general_row_change_caught():
    s,a=fixture()
    s["general"]["party_candidate_votes"]["Chris Pappas (D)"]+=1
    with pytest.raises(AssertionError,match="General election candidate"):
        mod.audit_municipal_votes(s,a)

def test_official_report_source_page_is_pinned():
    s,a=fixture()
    s["official_source"]["primary_pdf_page_index"]=54
    with pytest.raises(AssertionError,match="official election report identity"):
        mod.audit_municipal_votes(s,a)

def test_fec_drift_rejected(tmp_path):
    s,a=fixture()
    result=mod.audit_municipal_votes(s,a)
    p=tmp_path/"elections.csv"
    p.write_text("year,state,district,primary_rep_votes,general_rep_votes,general_dem_votes\n2022,NH,01,75402,142229,167391\n",encoding="utf-8")
    with pytest.raises(AssertionError,match="FEC 2022 NH-01 baseline changed"):
        mod.compare_fec_csv(result,p)
