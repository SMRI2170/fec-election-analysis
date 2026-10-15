import importlib.util
from pathlib import Path
import sys
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("audit_primary_subtotals",ROOT/"scripts"/"audit_primary_subtotals.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture(idless=False):
    rows=[
        ["AZ","03","H1AZ01","First",None,"R",30],
        ["AZ","03","H1AZ02","Second",None,"R",40],
        ["AZ","03",None,None,"Party Votes:","R",75],
        ["AZ","03","H1AZ03","Third",None,"D",55],
        ["AZ","03",None,None,"Party Votes:","D",55],
    ]
    if idless:
        rows.append(["AZ","03",None,"Scattered",None,"R",5])
    frame=pd.DataFrame(rows,columns=["STATE ABBREVIATION","DISTRICT","FEC ID","CANDIDATE NAME","TOTAL VOTES","PARTY","PRIMARY VOTES"])
    frame["_state"]=frame["STATE ABBREVIATION"]
    frame["_district"]=frame["DISTRICT"]
    frame["_party"]=frame["PARTY"].astype("string")
    frame["_marker"]=frame["TOTAL VOTES"].astype("string").str.lower()
    frame["_candidate"]=frame["FEC ID"].notna()
    excluded=pd.DataFrame([{"year":2020,"state":"AZ","district":"03","reason":"primary-subtotal-mismatch"}])
    return frame,excluded


def test_residual_is_audited_without_imputation():
    frame,excluded=fixture()
    rows,cases=mod.inspect(frame,excluded,2020,"House")
    r=rows[rows.party=="R"].iloc[0]
    assert (r.candidate_sum,r.party_subtotal,r.delta)==(70,75,5)
    assert len(cases)==1
    assert mod.summarize(rows,excluded)["remaining_unresolved_party_sides"]==1


def test_idless_votes_explain_not_automatically_reclassify():
    frame,excluded=fixture(True)
    rows,_=mod.inspect(frame,excluded,2020,"House")
    summary=mod.summarize(rows,excluded)
    assert summary["idless_rows_explain_delta"]==1
    assert summary["inclusion_criteria_modified"] is False


def test_discrepancy_count_fails_closed():
    frame,excluded=fixture()
    rows,_=mod.inspect(frame,excluded,2020,"House")
    rows.loc[rows.party=="R","delta"]=0
    with pytest.raises(AssertionError,match="disagrees"):
        mod.summarize(rows,excluded)
