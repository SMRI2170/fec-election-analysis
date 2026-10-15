import importlib.util
from pathlib import Path
import sys
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("audit_selection_bias",ROOT/"scripts"/"audit_selection_bias.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def make_data():
    rows=[]
    for year in (2016,2018,2020,2022):
        for state,r,d in (("AA",70,30),("BB",30,70)):
            rows.append({"year":year,"state":state,"district":"01","chamber":"House",
                         "primary_rep_votes":r,"primary_dem_votes":d,
                         "general_rep_votes":r+5,"general_dem_votes":d-5})
    return pd.DataFrame(rows)

def test_fixed_cohort_uses_identical_2022_observations():
    legacy=make_data()
    new=pd.concat([legacy,pd.DataFrame([{"year":2022,"state":"CC","district":"02",
        "chamber":"House","primary_rep_votes":40,"primary_dem_votes":60,
        "general_rep_votes":35,"general_dem_votes":65}])],ignore_index=True)
    results,summary=mod.compare(legacy,new)
    assert summary["common_test"]==2
    assert summary["legacy_test"]==2 and summary["current_test"]==3
    fixed=results[results["comparison"].str.contains("fixed_current_test")]
    assert set(fixed["n_test"])=={2}

def test_state_counts_only_uses_official_report_groups():
    selected=make_data().iloc[:2]
    excluded=pd.DataFrame([{"year":2022,"state":"CC","district":"01","reason":"unopposed"}])
    counts=mod.state_counts(selected,excluded,"test")
    assert counts["source_groups"].sum()==3
    assert counts["included"].sum()==2
    assert counts["excluded"].sum()==1

def test_duplicate_keys_raise():
    base=make_data()
    with pytest.raises(ValueError,match="Duplicate"):
        mod.keys(pd.concat([base,base.iloc[[0]]]))

def test_overlap_raises():
    base=make_data().iloc[:2]
    with pytest.raises(ValueError,match="overlap"):
        mod.state_counts(base,base[["year","state","district"]].iloc[[0]],"test")

def test_common_district_vote_changes_are_rejected():
    old=make_data()
    current=old.copy()
    current.loc[(current.year==2022)&(current.state=="AA"),"primary_rep_votes"]=200
    with pytest.raises(AssertionError,match="Different normalized primary_rep_votes"):
        mod.compare(old,current,2022)

def test_legacy_cases_not_in_corrected_cohort_are_rejected():
    old=make_data()
    current=old[~((old.year==2022)&(old.state=="AA"))].copy()
    with pytest.raises(AssertionError,match="drops legacy"):
        mod.compare(old,current,2022)
