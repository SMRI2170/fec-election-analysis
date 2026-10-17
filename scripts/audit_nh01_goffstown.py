"""Audit NH-01 2022 official Goffstown municipal Primary and General vote witness.

Municipal report, pdf indices 53/54, independently records ten Republican
Primary candidate rows, seven write-in votes, and two General candidates.
Combines already-audited Alton town General witness, but never promotes a
two-town subset to entire NH Congressional District 1.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from audit_nh01_alton_general import inspect_alton

CANDIDATES = {
    "Karoline Leavitt":660,
    "Mary Maxwell":13,
    "Matt Mowers":564,
    "Russell Prescott":180,
    "Kevin R. Rondeau":19,
    "Gilead R. Towne":8,
    "Tom Alciere":7,
    "Tim Baxter":174,
    "Gail Huff Brown":303,
    "Mark Kilbane":12,
}
GENERAL = {"Karoline Leavitt (R)":3720,"Chris Pappas (D)":3955}
FEC_VALUES = {"primary_rep_votes":75401,"general_rep_votes":142229,"general_dem_votes":167391}


def audit_municipal_votes(source: dict, alton: dict) -> dict:
    if (source.get("year"),source.get("state"),source.get("district"),source.get("municipality")) != (2022,"NH","01","Goffstown"):
        raise AssertionError("Invalid NH-01 town/district/year identity")
    official = source["official_source"]
    if (official["url"] != "https://www.goffstownnh.gov/Archive.aspx?ADID=108" or
        official["primary_pdf_page_index"] != 53 or
        official["general_pdf_page_index"] != 54 or
        official["primary_printed_page"] != 52 or
        official["general_printed_page"] != 53 or
        official["republican_primary_date"] != "2022-09-13" or
        official["general_date"] != "2022-11-08"):
        raise AssertionError("Goffstown town official election report identity has changed")
    scope=source["independent_source_scope"]
    if (not scope["town_only"] or scope["whole_congressional_district_primary_verified"] or
        scope["whole_congressional_district_general_verified"] or
        not scope["do_not_move_cross_party_writein_to_democratic_primary"]):
        raise AssertionError("A town witness must not be promoted to district-wide or cross-party voting")
    prim=source["republican_primary"]
    if prim["named_candidate_votes"]!=CANDIDATES:
        raise AssertionError("Goffstown primary named candidates changed; inspect official town PDF")
    if prim["named_cross_party_writein"] != {"Chris Pappas":5}:
        raise AssertionError("Five Chris Pappas write-ins were on the REPUBLICAN primary ballot")
    if (prim["writeins_under_5_votes_each"],prim["overvotes"],prim["undervotes"])!=(2,4,63):
        raise AssertionError("Town-primary write-in, overvote or undervote row changed")
    ten=sum(CANDIDATES.values())
    total=ten + sum(prim["named_cross_party_writein"].values()) + prim["writeins_under_5_votes_each"]
    if (len(CANDIDATES),ten,total)!=(10,1940,1947):
        raise AssertionError("Republican primary named votes/write-in arithmetic changed")
    if prim["candidate_named_votes_sum"] != ten or prim["counted_valid_republican_primary_votes"] != total:
        raise AssertionError("Goffstown primary published candidate + write-in tally not reconciled")
    general=source["general"]
    if general["party_candidate_votes"]!=GENERAL:
        raise AssertionError("Goffstown General election candidate vote witness changed")
    if (general["other_writein_votes"],general["overvotes"],general["undervotes"])!=(9,1,88):
        raise AssertionError("Goffstown General write-in, overvote or undervote tally changed")
    if source["fec_district_context"]!=FEC_VALUES:
        raise AssertionError("Original FEC NH-01 2022 baseline has drifted")
    alton_result=inspect_alton(alton)
    two_towns={"R":GENERAL["Karoline Leavitt (R)"]+alton_result["town_votes"]["R"],
               "D":GENERAL["Chris Pappas (D)"]+alton_result["town_votes"]["D"]}
    if two_towns!={"R":5656,"D":5179}:
        raise AssertionError("Alton + Goffstown General two-town arithmetic drifted")
    if not (total<FEC_VALUES["primary_rep_votes"] and
            two_towns["R"]<FEC_VALUES["general_rep_votes"] and
            two_towns["D"]<FEC_VALUES["general_dem_votes"]):
        raise AssertionError("Municipal subtotal cannot become district-wide vote witness")
    return {
        "year":2022,"state":"NH","district":"01",
        "official_municipality":"Goffstown",
        "republican_primary":{
            "named_candidates":CANDIDATES,
            "named_candidate_votes":ten,
            "writein_votes_on_republican_ballot":7,
            "town_republican_valid_votes":total,
            "district_republican_primary_independently_verified":False,
        },
        "general":{
            "town_votes":GENERAL,
            "two_town_included":["Alton","Goffstown"],
            "two_town_votes":two_towns,
            "district_general_independently_verified":False
        },
        "official_town_pdf":official["url"],
        "no_causal_inference":True
    }


def compare_fec_csv(audit:dict,path:Path)->None:
    with path.open(newline="",encoding="utf-8") as f:
        rows=[r for r in csv.DictReader(f)
              if r["year"]=="2022" and r["state"]=="NH" and r["district"].zfill(2)=="01"]
    if len(rows)!=1:
        raise AssertionError("Exactly one FEC 2022 NH-01 House row required")
    for field,want in FEC_VALUES.items():
        if int(rows[0][field])!=want:
            raise AssertionError(f"FEC 2022 NH-01 baseline changed: {field}")
    audit["fec_2022_normalized_row_matched"]=True


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--goffstown",type=Path,default=Path("data/sources/nh01_goffstown_2022_primary_general.json"))
    p.add_argument("--alton",type=Path,default=Path("data/sources/nh01_alton_2022_general_partial.json"))
    p.add_argument("--fec",type=Path,default=Path("data/processed/elections.csv"))
    p.add_argument("--output",type=Path,default=Path("data/processed/nh01_goffstown_audit.json"))
    a=p.parse_args()
    audited=audit_municipal_votes(json.loads(a.goffstown.read_text(encoding="utf-8")),
                                   json.loads(a.alton.read_text(encoding="utf-8")))
    compare_fec_csv(audited,a.fec)
    a.output.parent.mkdir(exist_ok=True,parents=True)
    a.output.write_text(json.dumps(audited,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(audited,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
