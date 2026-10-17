"""Explain out-of-time FEC prediction errors without outcome leakage or causal claims."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from fec_analysis.core import prepare_elections

BINS=[0,.35,.45,.55,.65,1.0000000001]
LABELS=["[0%,35%)","[35%,45%)","[45%,55%)","[55%,65%)","[65%,100%]"]
COUNTS={2016:200,2018:241,2020:237,2022:238}

def state_interval(delta,states,seed,repetitions=4000):
    """Cluster bootstrap over states; diagnostic interval, not an unbiased national CI."""
    if len(delta)!=len(states) or not len(delta) or repetitions<100:
        raise ValueError("paired records and at least 100 draws required")
    part=pd.DataFrame({"state":states.astype(str).to_numpy(),"d":np.asarray(delta,dtype=float)})
    if not np.isfinite(part.d.to_numpy()).all():
        raise ValueError("Invalid error values")
    grouped=part.groupby("state",sort=True).d.agg(["sum","count"])
    if len(grouped)<2:
        raise ValueError("At least two states required")
    rng=np.random.default_rng(seed)
    draws=rng.integers(0,len(grouped),size=(repetitions,len(grouped)))
    result=grouped["sum"].to_numpy()[draws].sum(axis=1)/grouped["count"].to_numpy()[draws].sum(axis=1)
    return [round(float(x),6) for x in np.quantile(result,[.025,.975])]

def heldout(raw,years=(2018,2020,2022)):
    data=prepare_elections(raw)
    data=data[data.chamber.eq("House")]
    records=[];fits=[]
    for year in years:
        training=data[data.year.lt(year)]
        test=data[data.year.eq(year)].copy()
        if len(training)==0 or len(test)==0 or training.year.ge(year).any():
            raise AssertionError("Train/test dates overlap or empty")
        x="primary_rep_share";y="general_rep_share"
        linear=LinearRegression().fit(training[[x]],training[y])
        constant=DummyRegressor(strategy="mean").fit(training[[x]],training[y])
        test["linear_pred"]=linear.predict(test[[x]]).clip(0,1)
        test["identity_pred"]=test[x]
        test["mean_pred"]=constant.predict(test[[x]]).clip(0,1)
        test["linear_signed"]=test["linear_pred"]-test[y]
        for name in ("linear","identity","mean"):
            test[name+"_abs"]=(test[name+"_pred"]-test[y]).abs()
        test["share_bin"]=pd.cut(test[x],BINS,labels=LABELS,include_lowest=True,right=False)
        test["actual_margin_pp"]=(test[y]-.5).abs()*200
        if test["share_bin"].isna().any():
            raise AssertionError("Predeclared bins fail to cover all primary shares")
        test["primary_majority"]=(test[x]>.5).astype(int)
        test["general_majority"]=(test[y]>.5).astype(int)
        records.append(test)
        fits.append({"test_year":year,"train_n":len(training),"test_n":len(test),
            "train_max_year":int(training.year.max()),
            "linear_intercept":round(float(linear.intercept_),6),
            "linear_slope":round(float(linear.coef_[0]),6)})
    return pd.concat(records,ignore_index=True),fits

def analyze(pred,fits,iterations=4000,assert_baseline=False):
    if assert_baseline:
        if sum(COUNTS.values())!=916:
            raise AssertionError("Frozen original cohort changed")
        for fit in fits:
            year=fit["test_year"]
            if fit["train_n"]!=sum(v for y,v in COUNTS.items() if y<year) or fit["test_n"]!=COUNTS[year]:
                raise AssertionError("Fixed chronological 916 voting-House cohort changed")
    answer={
        "analysis":"retrospective-error-structure-v1",
        "study":"official FEC 2016/2018/2020/2022, 916 selected US voting House records",
        "no_test_outcome_used_as_predictor":True,"no_causal_claim":True,
        "fixed_primary_share_bins":LABELS,
        "state_bootstrap":{"iterations":iterations,"seed_rule":"20261017 + test_year",
            "warning":"Exploratory; conditional on nonrandom selected districts and states. Not a future guarantee."},
        "fit":fits,"years":[]}
    for year,t in pred.groupby("year",sort=True):
        metrics={
          "year":int(year),"n":len(t),"states":int(t.state.nunique()),
          "MAE":{name:round(float(t[name+"_abs"].mean()),6) for name in ("mean","identity","linear")},
          "linear_RMSE":round(float(np.sqrt((t.linear_signed**2).mean())),6),
          "linear_mean_signed_pred_minus_actual":round(float(t.linear_signed.mean()),6),
          "linear_over_predictions":int((t.linear_signed>0).sum()),
          "linear_under_predictions":int((t.linear_signed<0).sum()),
          "abs_linear_error_quantiles":{str(q):round(float(t.linear_abs.quantile(q)),6) for q in (.5,.9,.95,.99)},
          "top5_share_of_total_absolute_error":round(float(t.linear_abs.nlargest(5).sum()/t.linear_abs.sum()),6),
          "relative_baseline_gains":{},"fixed_primary_bins":[],"actual_margin_diagnostics":[]}
        for base in ("identity","mean"):
            delta=t[base+"_abs"]-t.linear_abs
            metrics["relative_baseline_gains"][base]={
              "MAE_difference_baseline_minus_linear":round(float(delta.mean()),6),
              "relative_MAE_reduction":round(float(delta.mean()/t[base+"_abs"].mean()),6),
              "linear_better_districts":int((delta>1e-12).sum()),
              "linear_worse_districts":int((delta< -1e-12).sum()),
              "state_bootstrap_95pct_interval":state_interval(delta,t.state,20261017+int(year),iterations)}
        for label in LABELS:
            group=t[t.share_bin.astype(str).eq(label)]
            if group.empty: continue
            metrics["fixed_primary_bins"].append({
                "bin":label,"n":len(group),"underpowered_under_10":bool(len(group)<10),
                "linear_MAE":round(float(group.linear_abs.mean()),6),
                "identity_MAE":round(float(group.identity_abs.mean()),6),
                "signed_bias_pred_minus_actual":round(float(group.linear_signed.mean()),6),
                "primary_general_majority_disagree":int((group.primary_majority!=group.general_majority).sum()),
                "observed_general_share_mean":round(float(group.general_rep_share.mean()),6)})
        for name,mask in (("actual_general_margin_lt_10pp",t.actual_margin_pp<10),
                          ("actual_general_margin_ge_10pp",t.actual_margin_pp>=10)):
            group=t[mask]
            metrics["actual_margin_diagnostics"].append({
                "name":name,"n":len(group),
                "linear_MAE":round(float(group.linear_abs.mean()),6) if len(group) else None,
                "outcome_based_lookahead_NOT_available_for_prediction":True})
        answer["years"].append(metrics)
    return answer

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("data/processed/elections.csv"))
    p.add_argument("--output-dir",type=Path,default=Path("data/processed"))
    p.add_argument("--iterations",type=int,default=4000)
    p.add_argument("--assert-baseline",action="store_true")
    a=p.parse_args()
    raw=pd.read_csv(a.input,dtype={"state":str,"district":str})
    predictions,fits=heldout(raw)
    result=analyze(predictions,fits,a.iterations,a.assert_baseline)
    a.output_dir.mkdir(parents=True,exist_ok=True)
    (a.output_dir/"error-structure-summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    cols=["year","state","district","primary_rep_share","general_rep_share","linear_pred","identity_pred","mean_pred","linear_signed","linear_abs","identity_abs","mean_abs","share_bin","actual_margin_pp"]
    predictions[cols].to_csv(a.output_dir/"error-structure-districts.csv",index=False)
    print("ANALYSIS_SUMMARY_JSON_START")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print("ANALYSIS_SUMMARY_JSON_END")

if __name__=="__main__":
    main()
