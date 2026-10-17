"""Time-safe retrospective cohort audit; data below are synthetic, not FEC findings."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_prediction_time_eligibility import (
    build_ledger, general_outcome_observability, primary_only_compatibility,
)
from normalize_fec import normalize_house


def district(state="AL", district="01", general_r=55, general_d=45, primary_r=70, primary_d=60):
    return [
        [state,district,"H0AL01055","", "R", 50,general_r],
        [state,district,"H0AL01089","", "R", 20,None],
        [state,district,None,"Party Votes:","R",primary_r,None],
        [state,district,"H0AL01097","", "D", 35,general_d],
        [state,district,"H0AL01105","", "D", 25,None],
        [state,district,None,"Party Votes:","D",primary_d,None],
        [state,district,None,"District Votes:",None,None,None],
    ]


def prep(rows):
    df = pd.DataFrame(rows,columns=[
        "STATE ABBREVIATION","DISTRICT","FEC ID","TOTAL VOTES",
        "PARTY","PRIMARY VOTES","GENERAL VOTES"])
    df["_state"]=df["STATE ABBREVIATION"].astype("string").str.strip().str.upper()
    df["_district"]=df["DISTRICT"].astype("string").str.zfill(2)
    df["_party"]=df["PARTY"].astype("string").str.strip().str.upper()
    df["_marker"]=df["TOTAL VOTES"].astype("string").str.strip().str.lower()
    df["_candidate"]=df["FEC ID"].astype("string").str.strip().str.upper().str.fullmatch(r"H[A-Z0-9]+",na=False)
    return df


def fixture():
    base = district()
    missing = district(district="02",general_d=None)
    special = district(district="03")
    ca = district(state="CA",district="01")
    df=prep(base+missing+special+ca)
    good,bad = normalize_house(df,2022,"fec.xlsx","House")
    # Our synthetic official winner audit would flag district 03 as a
    # post-General exception: remove from frozen selection and add its reason.
    good=good[~good.district.eq("03")].copy()
    bad=pd.concat([bad,pd.DataFrame([{"year":2022,"state":"AL","district":"03",
                                      "reason":"official-ge-different_winner"}])],ignore_index=True)
    return df,good,bad


def test_primary_eligibility_ignores_general_vote_values_and_columns():
    df=prep(district())
    assert primary_only_compatibility(df,"AL")["primary_report_compatible"]
    assert primary_only_compatibility(df.drop(columns=["GENERAL VOTES"]),"AL")["primary_report_compatible"]
    df.loc[df["_party"].eq("D") & df["_candidate"],"GENERAL VOTES"]=None
    assert primary_only_compatibility(df,"AL")["primary_report_compatible"]
    assert not general_outcome_observability(df)["post_general_rd_numeric_observable"]


def test_ledger_separates_postgeneral_outcomes_from_primary_compatible():
    raw,kept,excluded=fixture()
    ledger,meta=build_ledger(kept,excluded,{2022:raw})
    assert len(ledger)==4
    assert len(kept)==1
    assert meta["total_fec_report_groups"]==4
    rows=ledger.set_index(["state","district"])
    assert rows.loc[("AL","01"),"final_916_selected"]
    assert rows.loc[("AL","01"),"primary_report_compatible"]
    assert rows.loc[("AL","02"),"primary_report_compatible"]
    assert not rows.loc[("AL","02"),"post_general_rd_numeric_observable"]
    assert rows.loc[("AL","02"),"selection_uses_post_general_information"]
    assert rows.loc[("AL","03"),"primary_report_compatible"]
    assert rows.loc[("AL","03"),"final_exclusion_reason"]=="official-ge-different_winner"
    assert rows.loc[("AL","03"),"selection_uses_post_general_information"]
    assert rows.loc[("CA","01"),"primary_exclusion_reason"]=="needs-state-election-rule-review"
    assert not rows["operational_pre_election_eligibility_proven"].any()
    assert meta["pre_election_snapshot_proven_rows"]==0
    assert meta["years"][0]["retrospective_primary_compatible"]==3
    assert meta["years"][0]["general_rd_not_observed_among_primary_compatible"]==1


def test_unopposed_is_missing_not_zero_or_primary_valid():
    raw=prep(district())
    raw.loc[raw["_party"].eq("D")&raw["_candidate"],"PRIMARY VOTES"]="Unopposed"
    r=primary_only_compatibility(raw,"AL")
    assert r["primary_exclusion_reason"]=="unopposed-primary"
    assert r["primary_r_votes_reconstructed"] is None


def test_writein_reconstruction_uses_primary_only():
    rows=district(primary_r=75)
    rows.append(["AL","01",None,"","W(R)",5,None])
    raw=prep(rows)
    result=primary_only_compatibility(raw,"AL")
    assert result["primary_r_votes_reconstructed"]==75
    assert result["primary_d_votes_reconstructed"]==60
    raw.loc[raw["_party"].eq("W(R)"),"PRIMARY VOTES"]="Unopposed"
    assert primary_only_compatibility(raw,"AL")["primary_exclusion_reason"]=="ambiguous-affiliated-writein"


def test_mismatch_and_missing_party_are_primary_rejections():
    raw=prep(district(primary_d=99))
    assert primary_only_compatibility(raw,"AL")["primary_exclusion_reason"]=="primary-subtotal-mismatch"
    without_r=raw[~raw["_party"].eq("R")]
    assert primary_only_compatibility(without_r,"AL")["primary_exclusion_reason"]=="missing-party-candidates"


def test_raw_and_final_keys_must_match():
    raw,kept,excluded=fixture()
    truncated=excluded[~excluded.district.eq("02")]
    with pytest.raises(AssertionError,match="Unaccounted FEC"):
        build_ledger(kept,truncated,{2022:raw})


def test_frozen_primary_vote_tampering_fails():
    raw,kept,excluded=fixture()
    kept=kept.copy()
    kept.loc[kept.index[0],"primary_rep_votes"]=999
    with pytest.raises(AssertionError,match="Primary reconstruction"):
        build_ledger(kept,excluded,{2022:raw})


def test_selected_general_vote_must_be_observed():
    raw,kept,excluded=fixture()
    selected=kept.copy()
    selected.loc[selected.index[0],"district"]="02"
    excluded=excluded[~excluded.district.eq("02")].copy()
    excluded=pd.concat([excluded,pd.DataFrame([{"year":2022,"state":"AL","district":"01","reason":"unopposed-primary"}])],ignore_index=True)
    with pytest.raises(AssertionError,match="no observed two-party General"):
        build_ledger(selected,excluded,{2022:raw})


def test_general_runoff_and_rcv_columns_do_not_change_primary_diagnostic():
    raw=prep(district())
    raw["GE RUNOFF ELECTION VOTES"]=10
    a=primary_only_compatibility(raw,"AL")
    assert a["primary_report_compatible"]
    assert general_outcome_observability(raw)["general_special_runoff_or_rcv_observed"]


def test_enforce_frozen_916_cannot_pass_synthetic_fixture():
    raw,kept,excluded=fixture()
    with pytest.raises(AssertionError,match="four official FEC election years"):
        build_ledger(kept,excluded,{2022:raw},enforce_baseline=True)
