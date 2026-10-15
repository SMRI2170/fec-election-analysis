"""Audit whether the *two-party Republican vote lead* agrees with FEC's GE winner indicator.

Do not use official winner information as a training feature.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from source_reconcile import read_house, vote


def audit_one(group: pd.DataFrame, expected: pd.Series, year: int, sheet: str) -> dict:
    if "GE WINNER INDICATOR" not in group.columns:
        raise ValueError(f"{year}: missing official GE WINNER INDICATOR")
    # FEC marker W is an indicator COLUMN, not the W write-in PARTY code.
    flags = group["GE WINNER INDICATOR"].astype("string").str.strip().str.upper().eq("W").fillna(False)
    flagged = group[flags].copy()
    flagged = flagged[flagged["GENERAL VOTES"].map(vote).fillna(0).gt(0)]
    winners = [
        {
            "fec_id": None if pd.isna(row["FEC ID"]) else str(row["FEC ID"]),
            "party": None if pd.isna(row["_party"]) else str(row["_party"]),
            "candidate_name": None if pd.isna(row.get("CANDIDATE NAME")) else str(row["CANDIDATE NAME"]),
            "general_votes": vote(row["GENERAL VOTES"]),
            "footnotes": None if pd.isna(row.get("FOOTNOTES")) else str(row["FOOTNOTES"])[:140],
        }
        for _, row in flagged.iterrows()
    ]
    winner_party = winners[0]["party"] if len(winners) == 1 else None
    r, d = int(expected["general_rep_votes"]), int(expected["general_dem_votes"])
    two_party_label = "R" if r > d else "D" if d > r else "TIE"
    agrees = bool(winner_party == two_party_label) if winner_party in ("R", "D") and two_party_label != "TIE" else None
    all_general = group[group["GENERAL VOTES"].map(vote).fillna(0).gt(0) &
                        ~group["_marker"].isin(["party votes:", "district votes:", "total votes:"])]
    non_winner_higher = None
    if len(winners) == 1:
        non_winner_higher = any((vote(v) or 0) > winners[0]["general_votes"] for v in all_general["GENERAL VOTES"])
    status = (
        "two_party_tie" if two_party_label == "TIE" else
        "no_official_flag" if not winners else
        "multiple_official_flags" if len(winners) > 1 else
        "third_party_official_winner" if winner_party not in ("R","D") else
        "different_winner" if not agrees else
        "agree"
    )
    return {
        "year":year, "state":str(expected["state"]), "district":str(expected["district"]).zfill(2),
        "two_party_leader":two_party_label, "two_party_r_votes":r, "two_party_d_votes":d,
        "official_winner_party":winner_party, "official_winner_count":len(winners),
        "agrees":agrees, "status":status, "official_winner_candidates":winners,
        "official_winner_below_other_candidate":non_winner_higher,
        "source_sheet":sheet,
    }


def audit(normalized:pd.DataFrame, sources:dict[int,tuple[str,pd.DataFrame]]) -> tuple[pd.DataFrame,dict]:
    seen=[]
    for year,df in normalized.groupby("year"):
        sheet, raw = sources[int(year)]
        groups = {(str(s),str(d)):g for (s,d),g in raw.groupby(["_state","_district"])}
        for _,row in df.iterrows():
            state,district=str(row["state"]),str(row["district"]).zfill(2)
            if (state,district) not in groups:
                raise AssertionError(f"Missing official FEC source {year}-{state}-{district}")
            seen.append(audit_one(groups[(state,district)],row,int(year),sheet))
    table=pd.DataFrame([{key:v for key,v in row.items() if key!="official_winner_candidates"} for row in seen])
    summary={
        "n":len(table),
        "by_year_status":{str(year):{str(k):int(v) for k,v in part["status"].value_counts().items()}
                          for year,part in table.groupby("year")},
        "status_counts":{str(k):int(v) for k,v in table["status"].value_counts().items()},
        "official_winner_not_highest_vote_rows":int(table["official_winner_below_other_candidate"].eq(True).sum()),
        "label_means_two_party_vote_leader_not_necessarily_official_winner": True,
    }
    return table,{"summary":summary,"cases":[row for row in seen if row["status"]!="agree"]}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,default=Path("data/raw"))
    p.add_argument("--processed-dir",type=Path,default=Path("data/processed"))
    args=p.parse_args()
    df=pd.read_csv(args.processed_dir/"elections.csv",dtype={"state":str,"district":str})
    sources={int(year):read_house(args.input_dir/f"federalelections{year}.xlsx") for year in sorted(df.year.unique())}
    rows,evidence=audit(df,sources)
    rows.to_csv(args.processed_dir/"winner-label-audit.csv",index=False)
    (args.processed_dir/"winner-label-summary.json").write_text(json.dumps(evidence["summary"],indent=2)+"\n",encoding="utf-8")
    (args.processed_dir/"winner-label-exceptions.json").write_text(json.dumps(evidence["cases"],indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(evidence["summary"],indent=2))
    for row in evidence["cases"][:15]:
        print("winner-exception",row["year"],row["state"],row["district"],row["status"],
              row["two_party_leader"],row["official_winner_party"],row["official_winner_candidates"][:2])


if __name__ == "__main__":
    main()
