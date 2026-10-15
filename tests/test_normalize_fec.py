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
