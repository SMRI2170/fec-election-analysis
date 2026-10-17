"""Ohio 2022 OH-09 amended official Ottawa county source regression."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("oh09_ottawa",ROOT/"scripts"/"audit_oh09_three_county_primary.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def fixture():
    paths=("oh09_defiance_2022_primary.json","oh09_erie_2022_primary.json","oh09_ottawa_2022_amended_primary.json")
    return tuple(json.loads((ROOT/"data/sources"/p).read_text(encoding="utf-8")) for p in paths)

def test_ottawa_amended_official_candidate_totals_and_5_remaining():
    report=mod.verify_three_counties(*fixture())
    assert report["three_county_primary_party_totals"]=={"Republican":16959,"Democratic":6659}
    assert report["three_county_candidate_totals"]["Republican"]=={
        "Beth Deck":868,"Theresa Gavarone":4174,"J.R. Majewski":5852,"Craig S. Riedel":6065}
    assert report["three_county_counties_covered"]==3
    assert report["remaining_unverified_counties"]==["Fulton","Lucas","Sandusky","Williams","Wood"]
    assert report["full_district_primary_independently_reconciled"] is False

def test_do_not_swap_amended_pdf_for_unverified_original():
    a,b,c=fixture()
    c["official_source"]["report_timestamp"]="2022-05-25 15:54"
    with pytest.raises(AssertionError,match="amended date"):
        mod.verify_three_counties(a,b,c)

def test_one_candidate_changed_is_rejected():
    a,b,c=fixture()
    c["candidates"]["Republican"]["Beth Deck"]+=1
    with pytest.raises(AssertionError,match="Ottawa candidate transcription"):
        mod.verify_three_counties(a,b,c)

def test_democratic_vote_change_is_rejected():
    a,b,c=fixture()
    c["candidates"]["Democratic"]["Marcy Kaptur"]+=1
    with pytest.raises(AssertionError,match="Ottawa candidate transcription"):
        mod.verify_three_counties(a,b,c)

def test_undervotes_do_not_count_as_candidate_votes():
    a,b,c=fixture()
    c["vote_issues"]["Republican"]["undervotes"]+=1
    with pytest.raises(AssertionError,match="overvotes/undervotes"):
        mod.verify_three_counties(a,b,c)

def test_cannot_pretend_three_counties_are_whole_district():
    a,b,c=fixture()
    c["scope"]["eight_county_district_complete"]=True
    with pytest.raises(AssertionError,match="must not be labelled"):
        mod.verify_three_counties(a,b,c)

def test_fec_baseline_drift_fails(tmp_path):
    r=mod.verify_three_counties(*fixture())
    p=tmp_path/"elections.csv"
    p.write_text("year,state,district,primary_rep_votes,primary_dem_votes\n2022,OH,09,61090,32967\n",encoding="utf-8")
    with pytest.raises(AssertionError,match="FEC baseline changed"):
        mod.compare_fec_csv(r,p)

def test_correct_fec_baseline_still_does_not_certify_all_counties(tmp_path):
    r=mod.verify_three_counties(*fixture())
    p=tmp_path/"elections.csv"
    p.write_text("year,state,district,primary_rep_votes,primary_dem_votes\n2022,OH,09,61090,32968\n",encoding="utf-8")
    mod.compare_fec_csv(r,p)
    assert r["official_fec_2022_baseline_reproduced"]
    assert r["full_district_primary_independently_reconciled"] is False
