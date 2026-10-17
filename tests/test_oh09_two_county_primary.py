"""Two independently certified county-level OH-09 2022 Primary sources."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("two_counties",ROOT/"scripts"/"audit_oh09_two_county_primary.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def load(name):
    return json.loads((ROOT/"data/sources"/name).read_text(encoding="utf-8"))

def fixtures():
    return load("oh09_defiance_2022_primary.json"),load("oh09_erie_2022_primary.json")

def test_two_counties_sum_and_different_local_primary_winners():
    result=mod.verify_two_counties(*fixtures())
    assert result["official_two_county_party_sums"]=={"Republican":11702,"Democratic":4521}
    assert result["candidates_two_county_sum"]["Republican"]=={
        "Beth Deck":660,"Theresa Gavarone":2535,"J.R. Majewski":3825,"Craig S. Riedel":4682}
    assert result["defiance_republican_primary_winner"]=="Craig S. Riedel"
    assert result["erie_republican_primary_winner"]=="J.R. Majewski"
    assert len(result["other_district_counties_without_independent_primary_vote_reconciliation"])==6
    assert not result["independently_verified_whole_district_primary"]

def test_erie_candidate_transcription_change_rejected():
    first,second=fixtures()
    second["primary_candidates"]["Republican"]["Beth Deck"]+=1
    with pytest.raises(AssertionError,match="Erie official candidate vote witness"):
        mod.verify_two_counties(first,second)

def test_erie_wrong_source_page_rejected():
    first,second=fixtures()
    second["official_source"]["republican_printed_page"]=25
    with pytest.raises(AssertionError,match="page or source identity"):
        mod.verify_two_counties(first,second)

def test_cannot_claim_complete_primary_with_two_counties():
    first,second=fixtures()
    second["no_district_wide_independent_primary_claim"]=False
    with pytest.raises(AssertionError,match="Two counties cannot"):
        mod.verify_two_counties(first,second)

def test_bad_fec_reference_rejected(tmp_path):
    result=mod.verify_two_counties(*fixtures())
    file=tmp_path/"elections.csv"
    file.write_text("year,state,district,primary_rep_votes,primary_dem_votes\n2022,OH,09,61090,32967\n",encoding="utf-8")
    with pytest.raises(AssertionError,match="FEC baseline changed"):
        mod.compare_fec_csv(result,file)
