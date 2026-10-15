"""Audit all primary subtotal mismatches in official FEC House workbooks.

Diagnostics only: never add unexplained votes or alter inclusion criteria.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from source_reconcile import read_house, vote

COLUMNS = ["year","state","district","party","candidate_sum","party_subtotal",
           "delta","abs_delta","candidate_count","idless_row_count",
           "idless_votes","remaining_after_idless","non_numeric_candidate_count",
           "non_numeric_idless_count","source_sheet"]


def inspect(raw: pd.DataFrame, excluded: pd.DataFrame, year: int, sheet: str):
    selection = excluded[(excluded.year == year) & (excluded.reason == "primary-subtotal-mismatch")]
    groups = {(str(s),str(d)):g for (s,d),g in raw.groupby(["_state","_district"])}
    records, evidence = [], []
    for selection_row in selection.itertuples():
        state, district = str(selection_row.state), str(selection_row.district).zfill(2)
        group = groups.get((state,district))
        if group is None:
            raise AssertionError(f"Missing raw district {year}-{state}-{district}")
        case = {"year": year, "state": state, "district": district, "parties": []}
        for party in ("R","D"):
            party_rows = group[group["_party"].eq(party)]
            candidates = party_rows[party_rows["_candidate"]]
            subtotals = party_rows[party_rows["_marker"].eq("party votes:")]
            other = party_rows[~party_rows["_candidate"] &
                               ~party_rows["_marker"].isin(["party votes:","district votes:","total votes:"])]
            candidate_values = [vote(v) for v in candidates["PRIMARY VOTES"]]
            other_values = [vote(v) for v in other["PRIMARY VOTES"]]
            candidate_sum = sum(v for v in candidate_values if v is not None)
            other_sum = sum(v for v in other_values if v is not None)
            subtotal = vote(subtotals.iloc[0]["PRIMARY VOTES"]) if len(subtotals)==1 else None
            delta = subtotal-candidate_sum if subtotal is not None else None
            records.append({
                "year":year,"state":state,"district":district,"party":party,
                "candidate_sum":candidate_sum,"party_subtotal":subtotal,"delta":delta,
                "abs_delta":abs(delta) if delta is not None else None,
                "candidate_count":len(candidates),"idless_row_count":len(other),
                "idless_votes":other_sum,
                "remaining_after_idless":delta-other_sum if delta is not None else None,
                "non_numeric_candidate_count":sum(pd.notna(v) and n is None for v,n in zip(candidates["PRIMARY VOTES"],candidate_values)),
                "non_numeric_idless_count":sum(pd.notna(v) and n is None for v,n in zip(other["PRIMARY VOTES"],other_values)),
                "source_sheet":sheet
            })
            case["parties"].append({
                "party":party, "candidate_sum":candidate_sum,"subtotal":subtotal,
                "delta":delta,"idless_vote_sum":other_sum,
                "candidates":[{
                    "name":str(row.get("CANDIDATE NAME","")),
                    "fec_id":str(row.get("FEC ID","")),
                    "raw_primary":None if pd.isna(row["PRIMARY VOTES"]) else str(row["PRIMARY VOTES"]),
                    "footnote":None if pd.isna(row.get("FOOTNOTES")) else str(row["FOOTNOTES"])[:150]
                } for _,row in candidates.iterrows()],
                "idless_rows":[{
                    "name":str(row.get("CANDIDATE NAME","")),
                    "raw_primary":None if pd.isna(row["PRIMARY VOTES"]) else str(row["PRIMARY VOTES"]),
                    "marker":str(row.get("TOTAL VOTES","")),
                    "footnote":None if pd.isna(row.get("FOOTNOTES")) else str(row["FOOTNOTES"])[:150]
                } for _,row in other.iterrows()]
            })
        evidence.append(case)
    return pd.DataFrame(records,columns=COLUMNS), evidence


def summarize(details:pd.DataFrame,excluded:pd.DataFrame) -> dict:
    affected = details[details["delta"].notna() & details["delta"].ne(0)].copy()
    observed = int(affected[["year","state","district"]].drop_duplicates().shape[0])
    wanted = excluded[excluded.reason == "primary-subtotal-mismatch"]
    expected = len(wanted)
    if observed != expected:
        raise AssertionError(f"Audit disagrees with normalizer: {observed} != {expected}")
    explained = int(affected["remaining_after_idless"].eq(0).sum())
    return {
        "excluded_districts":expected,
        "by_year":{str(k):int(v) for k,v in wanted.groupby("year").size().items()},
        "affected_party_sides":len(affected),
        "idless_rows_explain_delta":explained,
        "remaining_unresolved_party_sides":len(affected)-explained,
        "party_breakdown":{str(k):int(v) for k,v in affected.groupby("party").size().items()},
        "subtotal_greater_than_candidates":int(affected.delta.gt(0).sum()),
        "subtotal_less_than_candidates":int(affected.delta.lt(0).sum()),
        "abs_delta_quantiles":{str(k):float(v) for k,v in affected.abs_delta.quantile([0,.25,.5,.75,.9,1]).items()},
        "inclusion_criteria_modified":False
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,default=Path("data/raw"))
    p.add_argument("--processed-dir",type=Path,default=Path("data/processed"))
    args=p.parse_args()
    excluded=pd.read_csv(args.processed_dir/"exclusions.csv",dtype={"state":str,"district":str})
    data, evidence=[],[]
    for year in sorted(excluded.year.unique()):
        sheet,raw=read_house(args.input_dir/f"federalelections{year}.xlsx")
        details,cases=inspect(raw,excluded,int(year),sheet)
        data.append(details)
        evidence.extend(cases)
    all_data=pd.concat(data,ignore_index=True)
    summary=summarize(all_data,excluded)
    out=args.processed_dir
    all_data.to_csv(out/"primary-subtotal-differences.csv",index=False)
    (out/"primary-subtotal-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    examples=[case for year in sorted(excluded.year.unique()) for case in [x for x in evidence if x["year"]==year][:3]]
    (out/"primary-subtotal-examples.json").write_text(json.dumps(examples,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    for case in examples:
        print("sample",case["year"],case["state"],case["district"],[(p["party"],p["delta"],p["idless_vote_sum"]) for p in case["parties"]])


if __name__=="__main__":
    main()
