"""Synthetic unit tests for state-by-year analysis. No fixture results are FEC findings."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from analyze_state_year import (summarize_coverage, summarize_predictions,
                                check_frozen, run)
from analyze_error_structure import heldout


def election(year, state, district, primary_r=60, primary_d=40, general_r=53, general_d=47):
    return dict(year=year,state=state,district=district,chamber="House",
                primary_rep_votes=primary_r,primary_dem_votes=primary_d,
                general_rep_votes=general_r,general_dem_votes=general_d)


def sample():
    selected=pd.DataFrame(
        [election(y,s,d,primary_r=(60 if s=="AL" else 40),
                  general_r=(55 if s=="AL" else 45),
                  general_d=(45 if s=="AL" else 55))
         for y in (2016,2018,2020,2022)
         for s,d in (("AL","01"),("TX","02"))])
    excluded=pd.DataFrame(
        [{"year":y,"state":"CA","district":"01",
          "reason":"needs-state-election-rule-review"} for y in (2016,2018,2020,2022)]
       +[{"year":y,"state":"DC","district":"00",
          "reason":"nonvoting-delegate-jurisdiction"} for y in (2016,2018,2020,2022)]
       +[{"year":2018,"state":"AL","district":"02","reason":"unopposed-primary"}])
    return selected,excluded


def test_coverage_has_correct_denominator_and_exclusion_reasons():
    selected,excluded=sample()
    grouped,reasons=summarize_coverage(selected,excluded)
    assert grouped.report_groups.sum()==len(selected)+len(excluded)
    assert grouped.selected.sum()==len(selected)
    assert int(grouped[grouped.population.eq("nonvoting-delegate")].report_groups.sum())==4
    al2018=grouped[(grouped.year==2018)&grouped.state.eq("AL")].iloc[0]
    assert (al2018.report_groups,al2018.selected,al2018.excluded)==(2,1,1)
    assert al2018.selected_fraction==.5
    assert reasons.loc[reasons.reason.eq("unopposed-primary"),"n_excluded"].sum()==1


def test_state_year_weighting_and_sparse_reporting():
    selected,excluded=sample()
    groups,reasons,states,summary=run(selected,excluded)
    assert len(summary["held_out_by_year"])==3
    assert summary["four_year_voting_states"]==3
    assert summary["zero_selected_states"]==["CA"]
    assert len(states)==6  # 2 states x 3 held-out years
    assert (states.n==1).all()
    assert not states.descriptive_n_ge_5.any()
    assert all(y["equal_selected_state_n_ge_5_linear_mae"] is None for y in summary["held_out_by_year"])
    for y in summary["held_out_by_year"]:
        assert y["n_districts"]==2
        assert y["states_with_n_lt_5"]==2
        # Here both selected states have one district; both weighting methods coincide.
        assert abs(y["district_weighted_linear_mae"]-y["equal_selected_state_linear_mae"]) < 1e-10


def test_signed_errors_keep_direction_and_denominator():
    selected,_=sample()
    pred,_=heldout(selected)
    states,years=summarize_predictions(pred)
    for year in (2018,2020,2022):
        by=states[states.year.eq(year)]
        test=pred[pred.year.eq(year)]
        assert len(by)==2
        assert abs(years[(year-2018)//2]["district_weighted_signed_pred_minus_actual"]
                   -test.linear_signed.mean())<1e-12
        assert abs(by.mae_gain_carryover_minus_linear.add(by.linear_mae)
                   .sub(by.primary_carryover_mae)).max()<1e-12


def test_future_labels_cannot_change_predictions_for_test_year():
    selected,_=sample()
    before,_=heldout(selected)
    mutated=selected.copy()
    mutated.loc[mutated.year.eq(2022)&mutated.state.eq("AL"),"general_rep_votes"]=30
    mutated.loc[mutated.year.eq(2022)&mutated.state.eq("AL"),"general_dem_votes"]=70
    after,_=heldout(mutated)
    assert before.loc[before.year.eq(2022),"linear_pred"].tolist()==after.loc[after.year.eq(2022),"linear_pred"].tolist()
    assert before.loc[before.year.eq(2022),"linear_abs"].tolist()!=after.loc[after.year.eq(2022),"linear_abs"].tolist()


def test_duplicate_or_overlap_keys_rejected():
    selected,excluded=sample()
    with pytest.raises(AssertionError,match="duplicate"):
        summarize_coverage(pd.concat([selected,selected.iloc[:1]]),excluded)
    with pytest.raises(AssertionError,match="simultaneously"):
        summarize_coverage(selected,pd.concat([excluded,pd.DataFrame([
            dict(year=2016,state="AL",district="01",reason="wrong")])],ignore_index=True))


def test_nonvoting_delegate_cannot_be_selected():
    selected,excluded=sample()
    broken=selected.copy()
    broken.loc[0,"state"]="DC"
    with pytest.raises(AssertionError,match="delegates"):
        summarize_coverage(broken,excluded)


def test_frozen_916_check_refuses_synthetic_data():
    selected,excluded=sample()
    cover,_=summarize_coverage(selected,excluded)
    predictions,fits=heldout(selected)
    with pytest.raises(AssertionError,match="frozen"):
        check_frozen(cover,predictions,fits)


def test_timewise_metrics_never_use_future_training_data():
    selected,_=sample()
    pred,fits=heldout(selected)
    assert [(f["test_year"],f["train_max_year"]) for f in fits]==[
        (2018,2016),(2020,2018),(2022,2020)]
    assert pred.groupby("year").size().to_dict()=={2018:2,2020:2,2022:2}
