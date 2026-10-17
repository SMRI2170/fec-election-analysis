"""Protect NH-01 town-level evidence from being promoted to full verification."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("alton",ROOT/"scripts"/"audit_nh01_alton_general.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def source():
    return json.loads((ROOT/"data/sources/nh01_alton_2022_general_partial.json").read_text(encoding="utf-8"))

def test_both_independent_sources_agree_but_not_a_district_sum():
    r=mod.inspect_alton(source())
    assert r["town_votes"]=={"R":1936,"D":1224}
    assert r["independent_town_corrobated"]
    assert r["whole_district_independently_verified"] is False
    assert r["official_document_not_reparsed_by_ci"] is True

def test_madison_cannot_be_substituted_for_alton():
    s=source()
    s["municipality"]="Madison"
    with pytest.raises(AssertionError,match="Only official 2022 Alton"):
        mod.inspect_alton(s)

def test_press_must_match_the_state_indexed_row():
    s=source()
    s["contemporaneous_correspondence"]["votes_in_alton"]["Chris Pappas (D)"]=1225
    with pytest.raises(AssertionError,match="local reporting"):
        mod.inspect_alton(s)

def test_unaudited_full_pdf_claim_rejected():
    s=source()
    s["official_state_document"]["full_document_programmatically_verified"]=True
    with pytest.raises(AssertionError,match="full state PDF"):
        mod.inspect_alton(s)

def test_promoting_town_data_to_district_complete_fails():
    s=source()
    s["verification"]["whole_nh01_general_district_reconciled"]=True
    with pytest.raises(AssertionError,match="cannot be labelled"):
        mod.inspect_alton(s)

def test_fec_baseline_drift_rejected(tmp_path):
    p=tmp_path/"elections.csv"
    p.write_text("year,state,district,general_rep_votes,general_dem_votes\n2022,NH,01,142229,167392\n",encoding="utf-8")
    with pytest.raises(AssertionError,match="baseline differs"):
        mod.compare_fec_csv(mod.inspect_alton(source()),p)
