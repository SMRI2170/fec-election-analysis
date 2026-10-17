"""Exploratory-only study of 2022 top-five errors against reference districts."""
import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("compare_cases",ROOT/"scripts"/"compare_error_case_candidates.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def fixtures():
    rows=[]
    raw=[]
    for i in range(7):
        district=f"{i+1:02d}"
        rows.append({"year":2022,"state":"AA","district":district,
                     "abs_linear_error":1-i/10,
                     "primary_rep_share":.6,"general_rep_share":.4,
                     "primary_rule_error":True,"logistic_error":True})
        for party, primary_votes in (("R",10),("D",20)):
            raw.append({"_state":"AA","_district":district,
                        "_candidate":True,"_party":party,"PRIMARY VOTES":primary_votes})
        if i in (0,1):
            raw.append({"_state":"AA","_district":district,
                        "_candidate":True,"_party":"R","PRIMARY VOTES":5})
        if i==2:
            raw.append({"_state":"AA","_district":district,
                        "_candidate":False,"_party":"W(R)","PRIMARY VOTES":5})
    return pd.DataFrame(rows),pd.DataFrame(raw)

def test_selection_uses_only_top_five_and_233_style_other_group():
    errors,raw=fixtures()
    out=mod.candidate_features(errors,raw)
    assert len(out)==7
    assert out.iloc[0]["rep_positive_primary_candidates"]==2
    assert out.iloc[1]["rep_contested_primary"]
    assert not out.iloc[2]["rep_contested_primary"] # A W(R) is not a named R candidate.
    assert out.iloc[4]["group"]=="top5_selected_posthoc"
    assert out.iloc[5]["group"]=="other_2022_test"
    s=mod.summarize(out)
    assert s["groups"]["top5_selected_posthoc"]["districts"]==5
    assert s["groups"]["other_2022_test"]["districts"]==2
    assert s["posthoc_selection_warning"] is True
    assert s["causal_effect_claimed"] is False and s["p_value_reported"] is False

def test_reject_invalid_holdout():
    errors,raw=fixtures()
    errors.loc[0,"year"]=2020
    with pytest.raises(ValueError,match="2022 holdout"):
        mod.candidate_features(errors,raw)

def test_reject_missing_raw_district():
    errors,raw=fixtures()
    raw=raw[raw["_district"]!="07"]
    with pytest.raises(AssertionError,match="Original FEC 2022 district missing"):
        mod.candidate_features(errors,raw)

def test_reject_test_cohort_drift():
    errors,raw=fixtures()
    with pytest.raises(AssertionError,match="fixed 2022"):
        mod.summarize(mod.candidate_features(errors,raw),expected_test_rows=238)

def test_no_fake_significance():
    errors,raw=fixtures()
    result=mod.summarize(mod.candidate_features(errors,raw))
    assert "p_value" not in result
    assert result["p_value_reported"] is False
