import importlib.util
from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("audit_residual_parties",ROOT/"scripts"/"audit_residual_parties.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def fixture():
    rows=[
      ["OR","01","H0OR01","R Candidate","R",100,None, None],
      ["OR","01","H0OR02","D Candidate","D",30,None, None],
      ["OR","01","H0OR03","Fusion Candidate","D/IP/WF",40,None, "Fusion nomination"],
      ["OR","01",None,None,"R",100,"Party Votes:",None],
      ["OR","01",None,None,"D",70,"Party Votes:",None],
    ]
    df=pd.DataFrame(rows,columns=["STATE ABBREVIATION","DISTRICT","FEC ID","CANDIDATE NAME","PARTY","PRIMARY VOTES","TOTAL VOTES","FOOTNOTES"])
    df["_party"]=df["PARTY"].astype("string").str.upper()
    df["_candidate"]=df["FEC ID"].notna()
    df["_marker"]=df["TOTAL VOTES"].astype("string").str.lower()
    df["_state"]="OR"
    df["_district"]="01"
    return df

def test_split_party_candidate_is_only_diagnostic():
    records,evidence=mod.examine(fixture(),2022,"OR","01")
    d=next(x for x in records if x["party"]=="D")
    assert d["candidate_votes"]==30
    assert d["remaining_gap"]==40
    assert d["multiparty_candidate_vote_sum"]==40
    assert d["status"]=="possible_multiparty_candidate_match"
    assert len(evidence)==1
    assert evidence[0]["party_code"]=="D/IP/WF"
    assert "NOT automatically" in evidence[0]["note"]

def test_no_source_party_subtotal_is_unknown():
    df=fixture()
    df=df[~((df["PARTY"]=="D") & (df["TOTAL VOTES"]=="Party Votes:"))]
    results,_=mod.examine(df,2022,"OR","01")
    d=next(x for x in results if x["party"]=="D")
    assert d["status"]=="no_single_party_subtotal"

def test_all_excluded_cases_receive_both_party_records():
    df=fixture()
    excluded=pd.DataFrame([{"year":2022,"state":"OR","district":"01","reason":"primary-subtotal-mismatch"}])
    records,candidates,summary=mod.run(excluded,{2022:df})
    assert len(records)==2 and summary["remaining_excluded_districts"]==1
    assert summary["candidate_party_code_potential_matches"]==1
    assert summary["no_automatic_reallocation"]
