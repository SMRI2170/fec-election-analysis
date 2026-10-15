import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("normalize_fec", ROOT / "scripts" / "normalize_fec.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample_house():
    rows = [
        ["AL", "01", "H0AL01055", "", "R", 50, 55],
        ["AL", "01", "H0AL01089", "", "R", 20, None],
        ["AL", "01", None, "Party Votes:", "R", 70, None],
        ["AL", "01", "H0AL01097", "", "D", 35, 45],
        ["AL", "01", "H0AL01105", "", "D", 25, None],
        ["AL", "01", None, "Party Votes:", "D", 60, None],
        ["AL", "01", None, "District Votes:", None, 130, 100],
    ]
    return pd.DataFrame(rows, columns=["STATE ABBREVIATION", "DISTRICT", "FEC ID", "TOTAL VOTES", "PARTY", "PRIMARY VOTES", "GENERAL VOTES"])


def test_party_subtotals_not_double_counted():
    good, bad = mod.normalize_house(sample_house(), 2020, "fec.xlsx", "House")
    assert len(good) == 1 and bad.empty
    row = good.iloc[0]
    assert row["primary_rep_votes"] == 70 and row["primary_dem_votes"] == 60
    assert row["general_rep_votes"] == 55 and row["general_dem_votes"] == 45


def test_unopposed_does_not_become_zero():
    df = sample_house()
    df["PRIMARY VOTES"] = df["PRIMARY VOTES"].astype(object)
    df.loc[0, "PRIMARY VOTES"] = "Unopposed"
    good, bad = mod.normalize_house(df, 2022, "fec.xlsx", "House")
    assert good.empty and bad.iloc[0]["reason"] == "unopposed-primary"


def test_bad_party_subtotal_excludes_contest():
    df = sample_house()
    df.loc[2, "PRIMARY VOTES"] = 999
    good, bad = mod.normalize_house(df, 2020, "fec.xlsx", "House")
    assert good.empty and bad.iloc[0]["reason"] == "primary-subtotal-mismatch"


def test_top_two_state_excluded():
    df = sample_house()
    df["STATE ABBREVIATION"] = "CA"
    good, bad = mod.normalize_house(df, 2022, "fec.xlsx", "House")
    assert good.empty and bad.iloc[0]["reason"] == "needs-state-election-rule-review"


def test_missing_party_rejected():
    df = sample_house()
    df = df[df["PARTY"] != "D"].copy()
    good, bad = mod.normalize_house(df, 2022, "fec.xlsx", "House")
    assert good.empty and bad.iloc[0]["reason"] == "missing-party-candidates"


def test_invalid_headers_fail():
    with pytest.raises(ValueError, match="missing"):
        mod.normalize_house(pd.DataFrame({"OTHER": [1]}), 2020, "fec.xlsx", "House")

def test_2016_verified_district_and_fec_id_aliases():
    df = sample_house().rename(columns={"DISTRICT": "D", "FEC ID": "FEC ID#"})
    good, bad = mod.normalize_house(df, 2016, "fec2016.xlsx", "2016 US House Results by State")
    assert len(good) == 1 and bad.empty
    assert good.iloc[0]["district"] == "01"


def test_2018_verified_fec_id_alias():
    df = sample_house().rename(columns={"FEC ID": "FEC ID#"})
    good, bad = mod.normalize_house(df, 2018, "fec2018.xlsx", "2018 US House Results by State")
    assert len(good) == 1 and bad.empty
    assert good.iloc[0]["primary_rep_votes"] == 70

def test_uncertified_and_rcv_winners_are_separated():
    df = pd.DataFrame([
      {"year":2018,"state":"ME","district":"02","chamber":"House"},
      {"year":2018,"state":"NC","district":"09","chamber":"House"},
      {"year":2018,"state":"AL","district":"01","chamber":"House"},
    ])
    official = pd.DataFrame([
      {"state":"ME","district":"02","status":"different_winner"},
      {"state":"NC","district":"09","status":"no_official_flag"},
      {"state":"AL","district":"01","status":"agree"},
    ])
    kept, removed=mod.exclude_nonstandard_winners(df,official,2018)
    assert len(kept)==1 and kept.iloc[0]["state"]=="AL"
    assert set(removed["reason"])=={"official-ge-different_winner","official-ge-no_official_flag"}


def test_valid_winners_remain_unchanged():
    df = pd.DataFrame([{"state":"AL","district":"01","year":2020}])
    flags=pd.DataFrame([{"state":"AL","district":"01","status":"agree"}])
    kept,removed=mod.exclude_nonstandard_winners(df,flags,2020)
    assert len(kept)==1 and removed.empty


def test_affiliated_writein_votes_are_included_only_when_subtotal_matches():
    df=sample_house()
    df.loc[df["TOTAL VOTES"].eq("Party Votes:") & df["PARTY"].eq("R"),"PRIMARY VOTES"]=75
    df.loc[len(df)] = ["AL","01",None,None,"W(R)",5,None]
    good,bad=mod.normalize_house(df,2022,"fec.xlsx","House")
    assert len(good)==1 and bad.empty
    assert good.iloc[0]["primary_rep_votes"]==75
    assert good.iloc[0]["primary_dem_votes"]==60


def test_incorrect_affiliated_writein_subtotal_still_excluded():
    df=sample_house()
    df.loc[df["TOTAL VOTES"].eq("Party Votes:") & df["PARTY"].eq("R"),"PRIMARY VOTES"]=80
    df.loc[len(df)] = ["AL","01",None,None,"W(R)",5,None]
    good,bad=mod.normalize_house(df,2022,"fec.xlsx","House")
    assert good.empty and bad.iloc[0]["reason"]=="primary-subtotal-mismatch"


def test_affiliated_writein_without_party_total_is_not_guessed():
    df=sample_house()
    df=df[~(df["TOTAL VOTES"].eq("Party Votes:") & df["PARTY"].eq("R"))].copy()
    df.loc[len(df)] = ["AL","01",None,None,"W(R)",5,None]
    good,bad=mod.normalize_house(df,2022,"fec.xlsx","House")
    assert good.empty and bad.iloc[0]["reason"]=="missing-primary-party-subtotal"
