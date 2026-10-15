import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

def load(filename):
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

audit = load("source_reconcile.py")
stats = load("paired_accuracy.py")

def example():
    fields = ["STATE ABBREVIATION","DISTRICT","FEC ID","CANDIDATE NAME","TOTAL VOTES","PARTY","PRIMARY VOTES","GENERAL VOTES"]
    rows = [
        ["AA","01","H0AA00001","Republican","","R",70,55],
        ["AA","01","H0AA00002","Democrat","","D",60,45],
        ["AA","01",None,None,"Party Votes:","R",70,None],
        ["AA","01",None,None,"Party Votes:","D",60,None],
        ["AA","01",None,None,"District Votes:",None,130,105],
        ["AA","01",None,"Third","Scattered","W",None,5],
    ]
    raw = pd.DataFrame(rows, columns=fields)
    raw["_candidate"] = raw["FEC ID"].notna()
    raw["_party"] = raw["PARTY"].astype("string").str.strip().str.upper()
    raw["_marker"] = raw["TOTAL VOTES"].astype("string").str.strip().str.lower()
    raw["_state"] = raw["STATE ABBREVIATION"]
    raw["_district"] = raw["DISTRICT"]
    normalized = pd.DataFrame([{
        "year":2022,"state":"AA","district":"01","primary_rep_votes":70,
        "primary_dem_votes":60,"general_rep_votes":55,"general_dem_votes":45,
    }])
    return raw, normalized

def test_district_and_candidate_reconciliation():
    raw, normalized = example()
    _, result = audit.reconcile(normalized, {2022: raw})
    assert result["summary"]["candidate_sum_mismatches"] == 0
    assert result["summary"]["district_total_mismatches"] == 0
    assert result["summary"]["district_total_available"] == 1

def test_detect_source_discrepancy():
    raw, normalized = example()
    normalized.loc[0, "primary_rep_votes"] = 999
    _, result = audit.reconcile(normalized, {2022: raw})
    assert result["summary"]["candidate_sum_mismatches"] == 1

def test_paired_accuracy_uncertainty():
    df = pd.DataFrame({"primary_rule_error":[0,0,0,1,1], "logistic_error":[1,1,1,0,1]})
    result = stats.compare_predictions(df, repetitions=300, seed=3)
    assert (result["rule_only_wrong"], result["logistic_only_wrong"], result["both_wrong"]) == (1,3,1)
    assert result["mcnemar_exact_two_sided_p"] == pytest.approx(0.625)
    assert result["accuracy_difference_rule_minus_logistic"] == pytest.approx(0.4)

def test_paired_test_all_agree():
    df = pd.DataFrame({"primary_rule_error":[0,1], "logistic_error":[0,1]})
    assert stats.compare_predictions(df, repetitions=100)["mcnemar_exact_two_sided_p"] == 1.0

def test_reject_nonbinary_errors():
    df = pd.DataFrame({"primary_rule_error":[0,2], "logistic_error":[0,1]})
    with pytest.raises(ValueError, match="binary"):
        stats.compare_predictions(df)

def test_reconcile_pandas_missing_marker_values():
    raw, normalized = example()
    raw.loc[0, "_marker"] = pd.NA
    raw.loc[1, "_marker"] = pd.NA
    _, result = audit.reconcile(normalized, {2022: raw})
    assert result["summary"]["candidate_sum_mismatches"] == 0
    assert result["summary"]["district_total_mismatches"] == 0
