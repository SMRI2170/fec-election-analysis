"""Defiance Ohio 2022 certified Primary is a one-county witness, not full OH09."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("defiance",ROOT/"scripts"/"audit_oh09_defiance_primary.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def source():
    return json.loads((ROOT/"data/sources/oh09_defiance_2022_primary.json").read_text(encoding="utf-8"))

def test_official_county_4_republican_candidates_and_one_democrat():
    audit=mod.verify_official_county(source())
    assert audit["official_county_party_totals"]=={"Republican":4854,"Democratic":1133}
    assert audit["county_republican_winner"]=="Craig S. Riedel"
    assert audit["district_fec_republican_winner_context"]=="J.R. Majewski"
    assert audit["full_district_primary_independently_verified"] is False

def test_a_changed_candidate_count_fails():
    changed=source()
    changed["official_county_candidate_votes"]["Republican"]["Craig S. Riedel"]+=1
    with pytest.raises(AssertionError,match="candidate witness changed"):
        mod.verify_official_county(changed)

def test_a_changed_democrat_count_fails():
    changed=source()
    changed["official_county_candidate_votes"]["Democratic"]["Marcy Kaptur"]+=1
    with pytest.raises(AssertionError,match="candidate witness changed"):
        mod.verify_official_county(changed)

def test_false_full_district_claim_fails():
    changed=source()
    changed["observation"]["primary_full_district_independently_verified"]=True
    with pytest.raises(AssertionError,match="single county"):
        mod.verify_official_county(changed)

def test_misreading_local_winner_as_district_winner_fails():
    changed=source()
    changed["observation"]["district_republican_primary_winner"]="Craig S. Riedel"
    with pytest.raises(AssertionError,match="Do not infer"):
        mod.verify_official_county(changed)

def test_fec_mismatch_is_rejected(tmp_path):
    file=tmp_path/"elections.csv"
    file.write_text("year,state,district,primary_rep_votes,primary_dem_votes\n2022,OH,09,61089,32968\n",encoding="utf-8")
    with pytest.raises(AssertionError,match="district baseline changed"):
        mod.compare_fec_csv(mod.verify_official_county(source()),file)

def test_correct_fec_row_is_not_interpreted_as_state_canvass(tmp_path):
    file=tmp_path/"elections.csv"
    file.write_text("year,state,district,primary_rep_votes,primary_dem_votes\n2022,OH,09,61090,32968\n",encoding="utf-8")
    output=mod.verify_official_county(source())
    mod.compare_fec_csv(output,file)
    assert output["fec_baseline_matched_without_promoting_county_to_district"]
    assert not output["full_district_primary_independently_verified"]
