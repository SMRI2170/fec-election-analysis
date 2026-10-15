import importlib.util
from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("audit_winners",ROOT/"scripts"/"audit_winners.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def raw(winner_party="R",multiple=False):
    rows=[
        ["AZ","03","H0AZ123","R","R person",90,"W" if winner_party=="R" else ""],
        ["AZ","03","H0AZ999","D","D person",80,"W" if winner_party=="D" or multiple else ""],
        ["AZ","03","H0AZ333","IND","I person",5,"W" if winner_party=="IND" else ""],
    ]
    df=pd.DataFrame(rows,columns=["STATE ABBREVIATION","DISTRICT","FEC ID","PARTY","CANDIDATE NAME","GENERAL VOTES","GE WINNER INDICATOR"])
    df["TOTAL VOTES"]=None
    df["_state"]=df["STATE ABBREVIATION"]
    df["_district"]=df["DISTRICT"]
    df["_party"]=df["PARTY"].astype("string")
    df["_marker"]=df["TOTAL VOTES"].astype("string")
    df["_candidate"]=True
    return df


def candidate_row():
    return pd.Series({"state":"AZ","district":"03","general_rep_votes":90,"general_dem_votes":80})


def test_official_and_two_party_winner_agree():
    result=mod.audit_one(raw(),candidate_row(),2022,"House")
    assert result["status"]=="agree"
    assert result["official_winner_party"]=="R"


def test_official_candidate_can_disagree_with_two_party_lead():
    result=mod.audit_one(raw("D"),candidate_row(),2022,"House")
    assert result["status"]=="different_winner"


def test_third_party_winner_is_not_republican_lead():
    result=mod.audit_one(raw("IND"),candidate_row(),2022,"House")
    assert result["status"]=="third_party_official_winner"


def test_multiple_official_winners_are_not_silently_resolved():
    result=mod.audit_one(raw("R",multiple=True),candidate_row(),2022,"House")
    assert result["status"]=="multiple_official_flags"


def test_no_official_flag_is_unknown():
    df=raw()
    df["GE WINNER INDICATOR"]=None
    assert mod.audit_one(df,candidate_row(),2022,"House")["status"]=="no_official_flag"
