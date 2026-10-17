"""Synthetic fixture tests for out-of-time error diagnostics (NOT FEC measurements)."""
from pathlib import Path
import sys
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from analyze_error_structure import heldout, analyze, state_interval, LABELS

def fixture():
    records=[]
    for year in (2016,2018,2020,2022):
        for state,i,r,d in (("AL",0,20,80),("AZ",1,45,55),("CA",2,55,45),("CO",3,80,20)):
            records.append({"year":year,"state":state,"district":str(i).zfill(2),"chamber":"House",
                "primary_rep_votes":r,"primary_dem_votes":d,
                "general_rep_votes":r+(year-2016)//2,
                "general_dem_votes":d-(year-2016)//2})
    return pd.DataFrame(records)

def test_time_safe_training():
    pred,fit=heldout(fixture())
    assert [r["train_n"] for r in fit]==[4,8,12]
    assert [r["train_max_year"] for r in fit]==[2016,2018,2020]
    assert [r["test_n"] for r in fit]==[4,4,4]

def test_future_general_results_cannot_affect_model():
    baseline,fit1=heldout(fixture())
    changed=fixture()
    changed.loc[changed.year.eq(2022),"general_rep_votes"]=[5,10,80,95]
    alternate,fit2=heldout(changed)
    assert fit1==fit2
    assert baseline[baseline.year.eq(2022)].linear_pred.tolist()==alternate[alternate.year.eq(2022)].linear_pred.tolist()

def test_fixed_bins_and_subgroup_support():
    pred,fit=heldout(fixture())
    answer=analyze(pred,fit,iterations=100)
    assert answer["no_test_outcome_used_as_predictor"]
    assert answer["fixed_primary_share_bins"]==LABELS
    assert len(answer["years"])==3
    assert all(sum(b["n"] for b in year["fixed_primary_bins"])==4 for year in answer["years"])
    assert all(b["underpowered_under_10"] for b in answer["years"][2]["fixed_primary_bins"])
    assert sum(r["n"] for r in answer["years"][2]["actual_margin_diagnostics"])==4

def test_cluster_bootstrap_is_repeatable():
    x=state_interval(pd.Series([.02,.05,-.03,.04]),pd.Series(["AL","AL","CA","TX"]),123,200)
    assert x==state_interval(pd.Series([.02,.05,-.03,.04]),pd.Series(["AL","AL","CA","TX"]),123,200)
    assert x[0]<=x[1]

def test_single_state_rejected():
    with pytest.raises(ValueError,match="two states"):
        state_interval(pd.Series([.01,.02]),pd.Series(["AL","AL"]),123,100)

def test_synthetic_data_rejected_by_real_fec_cohort_guard():
    pred,fit=heldout(fixture())
    with pytest.raises(AssertionError,match="chronological 916"):
        analyze(pred,fit,iterations=100,assert_baseline=True)

def test_no_fabricated_claims_and_error_statistics():
    pred,fit=heldout(fixture())
    summary=analyze(pred,fit,iterations=100)
    assert summary["no_causal_claim"]
    for y in summary["years"]:
        assert all(v>=0 for v in y["MAE"].values())
        assert 0<=y["top5_share_of_total_absolute_error"]<=1
