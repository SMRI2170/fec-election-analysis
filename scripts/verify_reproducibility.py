"""Reproduce and validate a compact research manifest from official FEC analysis output.

A baseline is reviewed and committed; this script never overwrites it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

YEARS=(2016,2018,2020,2022)
VOTE_COLS=("primary_rep_votes","primary_dem_votes","general_rep_votes","general_dem_votes")

def build_manifest(input_dir:Path,processed_dir:Path)->dict:
    source=json.loads((input_dir/"download-manifest.json").read_text(encoding="utf-8"))
    if sorted(x["year"] for x in source)!=list(YEARS):
        raise ValueError("Official-source manifest must contain exactly 2016,2018,2020,2022")
    inputs=[]
    for rec in sorted(source,key=lambda r:r["year"]):
        year=int(rec["year"])
        file=input_dir/f"federalelections{year}.xlsx"
        raw=file.read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        if digest!=rec["sha256"]:
            raise AssertionError(f"FEC official source hash disagrees with downloader for {year}")
        inputs.append({"year":year,"url":rec["source_url"],"sha256":digest,"bytes":len(raw),"format":"xlsx"})
    data=pd.read_csv(processed_dir/"elections.csv",dtype={"state":str,"district":str})
    excluded=pd.read_csv(processed_dir/"exclusions.csv",dtype={"state":str,"district":str})
    metrics=pd.read_csv(processed_dir/"backtest_metrics.csv")
    if data.duplicated(["year","state","district"]).any():
        raise AssertionError("Duplicate normalized election")
    if not set(VOTE_COLS).issubset(data):
        raise AssertionError("Normalized data missing vote totals")
    summary=[]
    for year in YEARS:
        selected=data[data.year==year]
        dropped=excluded[excluded.year==year]
        summary.append({"year":year,"included":len(selected),"excluded":len(dropped)})
    values=[]
    for year in (2018,2020,2022):
        for task,model,metric in (("share","linear regression","MAE"),
                                  ("winner","primary-winner rule","accuracy"),
                                  ("winner","logistic regression","accuracy")):
            subset=metrics[(metrics.test_year==year)&(metrics.task==task)&
                           (metrics.model==model)&(metrics.metric==metric)]
            if len(subset)!=1:
                raise AssertionError(f"Missing or duplicate evaluation: {year} {task} {model}")
            row=subset.iloc[0]
            values.append({"year":year,"model":model,"metric":metric,
                           "score":round(float(row.score),8),"n_test":int(row.n_test)})
    return {"schema_version":1,"scope":"FEC 50-state voting U.S. House subset",
            "official_source_files":inputs,"year_counts":summary,
            "total_included":len(data),"total_excluded":len(excluded),
            "out_of_year_metrics":values,
            "note":"Exploratory comparison; excluded contests prevent population-wide generalization."}

def validate(current:dict,expected:dict,atol:float=0.0001)->None:
    if expected["schema_version"]!=current["schema_version"]:
        raise AssertionError("Snapshot schema differs")
    if current["year_counts"]!=expected["year_counts"]:
        raise AssertionError("Year-by-year accepted and excluded counts changed")
    if current["total_included"]!=expected["total_included"]:
        raise AssertionError("Accepted count changed")
    if len(current["out_of_year_metrics"])!=len(expected["out_of_year_metrics"]):
        raise AssertionError("Metric count changed")
    for got,wanted in zip(current["out_of_year_metrics"],expected["out_of_year_metrics"]):
        for key in ("year","model","metric","n_test"):
            if got[key]!=wanted[key]:
                raise AssertionError(f"Changed metric identity: {key} {got} vs {wanted}")
        if abs(got["score"]-wanted["score"])>atol:
            raise AssertionError(f"Metric drift beyond {atol}: {got} vs {wanted}")
    # Once source SHA256 values are reviewed in the committed baseline, they
    # are checked as exact byte-for-byte matches, not rounded comparisons.
    if expected.get("official_source_sha256"):
        hashes={str(x["year"]):x["sha256"] for x in current["official_source_files"]}
        if hashes!=expected["official_source_sha256"]:
            raise AssertionError("FEC source bytes changed: investigate before updating baseline")

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--raw-dir",type=Path,default=Path("data/raw"))
    p.add_argument("--processed-dir",type=Path,default=Path("data/processed"))
    p.add_argument("--baseline",type=Path,default=Path("data/sources/expected_analysis.json"))
    p.add_argument("--output",type=Path,default=Path("data/processed/reproducibility-manifest.json"))
    args=p.parse_args()
    data=build_manifest(args.raw_dir,args.processed_dir)
    expected=json.loads(args.baseline.read_text(encoding="utf-8"))
    validate(data,expected)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"verified":True,"included":data["total_included"],
                      "year_counts":data["year_counts"],
                      "source_sha256":{str(x["year"]):x["sha256"] for x in data["official_source_files"]}},
                     indent=2))
    print("Verified:",args.output)

if __name__=="__main__":
    main()
