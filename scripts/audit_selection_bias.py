"""Audit state selection and compare legacy/corrected election subsets on a fixed 2022 test."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from analyze import evaluate

KEY=["year","state","district"]

def keys(df):
    if df.duplicated(KEY).any():
        raise ValueError("Duplicate election keys")
    return set(df[KEY].itertuples(index=False,name=None))

def state_counts(inc,exc,policy):
    used,missing=keys(inc),keys(exc)
    if used & missing:
        raise ValueError("Included and excluded election overlap")
    rows=[]
    for year,state in sorted({(y,s) for y,s,d in used|missing}):
        a=sum((y,s)==(year,state) for y,s,d in used)
        b=sum((y,s)==(year,state) for y,s,d in missing)
        rows.append({"policy":policy,"year":year,"state":state,
                     "included":a,"excluded":b,"source_groups":a+b,
                     "inclusion_rate":a/(a+b)})
    return pd.DataFrame(rows)

def compare(legacy,current,test_year=2022):
    old,new=keys(legacy),keys(current)
    fixed=(old&new)
    fixed={k for k in fixed if k[0]==test_year}
    if not fixed:
        raise ValueError("No common holdout districts")
    common=current[current[KEY].apply(tuple,axis=1).isin(fixed)]
    train_old=legacy[legacy.year<test_year]
    train_new=current[current.year<test_year]
    configurations={
        "legacy_full":legacy,
        "current_full":current,
        "legacy_train_fixed_current_test":pd.concat([train_old,common],ignore_index=True),
        "current_train_fixed_current_test":pd.concat([train_new,common],ignore_index=True),
    }
    outputs=[]
    for label,frame in configurations.items():
        metrics=evaluate(frame,test_year,"House")
        metrics.insert(0,"comparison",label)
        metrics.insert(1,"test_year",test_year)
        outputs.append(metrics)
    summary={"legacy_all":len(legacy),"current_all":len(current),
             "legacy_train":len(train_old),"current_train":len(train_new),
             "legacy_test":sum(k[0]==test_year for k in old),
             "current_test":sum(k[0]==test_year for k in new),
             "common_test":len(fixed),
             "legacy_only_test":sum(k[0]==test_year for k in old-new),
             "current_only_test":sum(k[0]==test_year for k in new-old),
             "fixed_test_observations_identical":True,
             "caution":"Full-cohort scores change training AND test populations. Fixed-test scores isolate training population changes on identical corrected source observations."}
    return pd.concat(outputs,ignore_index=True),summary

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--legacy-dir",type=Path,default=Path("data/processed/legacy"))
    p.add_argument("--current-dir",type=Path,default=Path("data/processed"))
    p.add_argument("--test-year",type=int,default=2022)
    args=p.parse_args()
    def load(path):
        return (pd.read_csv(path/"elections.csv",dtype={"district":str,"state":str}),
                pd.read_csv(path/"exclusions.csv",dtype={"district":str,"state":str}))
    old,old_ex=load(args.legacy_dir)
    new,new_ex=load(args.current_dir)
    source_old=keys(old)|keys(old_ex)
    source_new=keys(new)|keys(new_ex)
    if source_old!=source_new:
        raise AssertionError(f"Official source-group universe changed: {len(source_old)} vs {len(source_new)}")
    scores,summary=compare(old,new,args.test_year)
    summary.update({"source_report_groups":len(source_old),
                    "source_report_groups_are_not_all_us_geographic_districts":True})
    states=pd.concat([state_counts(old,old_ex,"legacy"),state_counts(new,new_ex,"current")])
    reasons=pd.concat([
       old_ex.groupby(["year","state","reason"]).size().rename("n").reset_index().assign(policy="legacy"),
       new_ex.groupby(["year","state","reason"]).size().rename("n").reset_index().assign(policy="current")
    ])
    output=args.current_dir
    scores.to_csv(output/"cohort-comparison.csv",index=False)
    states.to_csv(output/"year-state-selection.csv",index=False)
    reasons.to_csv(output/"state-reason-selection.csv",index=False)
    (output/"cohort-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print(scores[scores.metric.isin(["MAE","accuracy"])].to_string(index=False,float_format=lambda v:f"{v:.5f}"))

if __name__=="__main__":
    main()
