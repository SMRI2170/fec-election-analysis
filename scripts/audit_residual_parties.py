"""Inspect the remaining primary subtotal mismatches without assigning ambiguous party votes.

Diagnostic output only: multi-party codes indicate a possible connection, not
proof that all votes should be credited to any one party in a model.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
import pandas as pd
from source_reconcile import read_house, vote

PARTIES=("R","D")
KEY=("year","state","district")


def party_tokens(label: object) -> list[str]:
    if pd.isna(label):
        return []
    value=str(label).strip().upper()
    if "/" not in value and "+" not in value:
        return []
    return re.split(r"[/+,\s]+", value)


def examine(group: pd.DataFrame, year: int, state: str, district: str) -> tuple[list[dict],list[dict]]:
    records=[]
    evidence=[]
    for party in PARTIES:
        direct=group[group["_candidate"] & group["_party"].eq(party)]
        total=group[group["_marker"].eq("party votes:") & group["_party"].eq(party)]
        affiliated=group[group["_party"].eq(f"W({party})")]
        count=sum(vote(x) or 0 for x in direct["PRIMARY VOTES"])
        writein=sum(vote(x) or 0 for x in affiliated["PRIMARY VOTES"])
        reported=vote(total.iloc[0]["PRIMARY VOTES"]) if len(total)==1 else None
        gap=(reported-count-writein) if reported is not None else None
        candidate_rows=group[group["_candidate"] & ~group["_party"].isin(["R","D"])]
        multiparty=candidate_rows[candidate_rows["_party"].map(lambda x:party in party_tokens(x))]
        alternate_votes=[vote(v) for v in multiparty["PRIMARY VOTES"]]
        alternate_sum=sum(v for v in alternate_votes if v is not None)
        status=("no_single_party_subtotal" if reported is None else
                "balanced" if gap==0 else
                "possible_multiparty_candidate_match" if alternate_sum>0 and gap==alternate_sum else
                "no_multiparty_candidate_match")
        records.append({
            "year":year,"state":state,"district":district,"party":party,
            "candidate_votes":count,"affiliated_writein_votes":writein,
            "source_party_subtotal":reported,"remaining_gap":gap,
            "multiparty_candidate_vote_sum":alternate_sum,
            "multiparty_candidate_row_count":len(multiparty),
            "status":status,
        })
        for _,row in multiparty.iterrows():
            evidence.append({
                "year":year,"state":state,"district":district,"party_to_investigate":party,
                "party_code":str(row["PARTY"]),"candidate_name":str(row.get("CANDIDATE NAME","")),
                "fec_id":str(row.get("FEC ID","")),
                "primary_votes":None if pd.isna(row["PRIMARY VOTES"]) else str(row["PRIMARY VOTES"]),
                "general_votes":None if pd.isna(row.get("GENERAL VOTES")) else str(row.get("GENERAL VOTES")),
                "footnote":None if pd.isna(row.get("FOOTNOTES")) else str(row.get("FOOTNOTES"))[:300],
                "note":"Potential split-party row, NOT automatically allocated to R or D."
            })
    return records,evidence


def run(excluded:pd.DataFrame, source_by_year:dict[int,pd.DataFrame]) -> tuple[pd.DataFrame,pd.DataFrame,dict]:
    leftover=excluded[excluded["reason"]=="primary-subtotal-mismatch"]
    all_results=[]
    all_evidence=[]
    for year,year_rows in leftover.groupby("year"):
        source=source_by_year[int(year)]
        indexed={(str(st),str(d)):g for (st,d),g in source.groupby(["_state","_district"])}
        for entry in year_rows.itertuples(index=False):
            state,district=str(entry.state),str(entry.district).zfill(2)
            if (state,district) not in indexed:
                raise AssertionError(f"Missing district {year} {state}-{district}")
            rows,evidence=examine(indexed[(state,district)],int(year),state,district)
            all_results.extend(rows)
            all_evidence.extend(evidence)
    results=pd.DataFrame(all_results)
    sources=pd.DataFrame(all_evidence)
    if len(results)!=2*len(leftover):
        raise AssertionError("Each excluded district needs R and D records")
    summary={
        "remaining_excluded_districts":len(leftover),
        "party_sides_examined":len(results),
        "nonzero_remaining_gap":int(results.remaining_gap.fillna(0).ne(0).sum()),
        "candidate_party_code_potential_matches":int(results.status.eq("possible_multiparty_candidate_match").sum()),
        "no_party_subtotal":int(results.status.eq("no_single_party_subtotal").sum()),
        "not_explained_by_multiparty_candidate_code":int(results.status.eq("no_multiparty_candidate_match").sum()),
        "source_candidate_rows_with_split_party_labels":len(sources),
        "year_breakdown":{str(k):int(v) for k,v in leftover.groupby("year").size().items()},
        "no_automatic_reallocation":True,
    }
    return results,sources,summary


def main():
    p=argparse.ArgumentParser(description="Find possible split-party rows behind unclassified primary subtotal differences")
    p.add_argument("--input-dir",type=Path,default=Path("data/raw"))
    p.add_argument("--processed-dir",type=Path,default=Path("data/processed"))
    args=p.parse_args()
    excluded=pd.read_csv(args.processed_dir/"exclusions.csv",dtype={"district":str,"state":str})
    sources={int(y):read_house(args.input_dir/f"federalelections{y}.xlsx")[1]
             for y in sorted(excluded.year.unique())}
    results,candidates,summary=run(excluded,sources)
    results.to_csv(args.processed_dir/"residual-party-discrepancies.csv",index=False)
    candidates.to_csv(args.processed_dir/"residual-multiparty-candidates.csv",index=False)
    (args.processed_dir/"residual-party-summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    print(results[results.status!="balanced"].to_string(index=False))

if __name__=="__main__":
    main()
