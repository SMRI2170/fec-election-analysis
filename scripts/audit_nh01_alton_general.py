"""Read-only NH-01 General partial source witness for the town of Alton.

Matches New Hampshire Secretary of State indexed CD-1 PDF Alton row with
contemporaneous regional reporting. Does not claim all-district verification,
and CI does not download/reparse the NH official PDF.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

VOTES = {"Karoline Leavitt (R)":1936,"Chris Pappas (D)":1224}
FEC_EXPECT = {"general_rep_votes":142229,"general_dem_votes":167391}

def inspect_alton(source:dict)->dict:
    if (source.get("year"),source.get("state"),source.get("district"),
        source.get("stage"),source.get("municipality")) != (2022,"NH","01","general","Alton"):
        raise AssertionError("Only official 2022 Alton town General votes within NH-01 may be used")
    state=source["official_state_document"]
    press=source["contemporaneous_correspondence"]
    if (state["municipality"]!="Alton" or
        not state["url"].startswith("https://www.sos.nh.gov/") or
        not press["url"].startswith("https://")):
        raise AssertionError("Expected official NH state reference and independent Alton reference")
    if state["full_document_programmatically_verified"] is not False:
        raise AssertionError("Do not claim the full state PDF was parsed")
    verification=source["verification"]
    if (verification["whole_nh01_general_district_reconciled"] is not False or
        verification["missing_remainder_unverified"] is not True or
        verification["alton_subdistrict_row_corrobated"] is not True):
        raise AssertionError("Alton town result cannot be labelled district-complete")
    votes=source["recorded_party_candidate_votes"]
    if set(votes)!=set(VOTES) or set(press["votes_in_alton"])!=set(VOTES):
        raise AssertionError("Unexpected town candidates in corroboration")
    for name, expected in VOTES.items():
        if type(votes[name]) is not int or votes[name]!=expected:
            raise AssertionError(f"Official Alton town source witness changed: {name}")
        if press["votes_in_alton"][name]!=expected:
            raise AssertionError(f"Alton local reporting and NH official indexed row diverged: {name}")
    if verification["2022_nh01_general_rep_fec_baseline"]!=FEC_EXPECT["general_rep_votes"] or verification["2022_nh01_general_dem_fec_baseline"]!=FEC_EXPECT["general_dem_votes"]:
        raise AssertionError("NH01 FEC baseline context changed")
    if not (votes["Karoline Leavitt (R)"]<FEC_EXPECT["general_rep_votes"] and
            votes["Chris Pappas (D)"]<FEC_EXPECT["general_dem_votes"]):
        raise AssertionError("Town votes cannot equal whole NH-01 district votes")
    return {
        "year":2022,"state":"NH","district":"01","stage":"general",
        "town":"Alton",
        "town_votes":{"R":1936,"D":1224},
        "independent_town_corrobated":True,
        "whole_district_independently_verified":False,
        "official_document_not_reparsed_by_ci":True,
        "state_indexed_pdf_url":state["url"],
        "news_pdf_url":press["url"],
    }

def compare_fec_csv(report:dict,path:Path)->None:
    with path.open(encoding="utf-8",newline="") as fp:
        rows=[r for r in csv.DictReader(fp) if r["year"]=="2022" and
              r["state"]=="NH" and r["district"].zfill(2)=="01"]
    if len(rows)!=1:
        raise AssertionError("Expected one 2022 NH-01 normalized FEC row")
    for field, expected in FEC_EXPECT.items():
        if int(rows[0][field])!=expected:
            raise AssertionError(f"NH-01 FEC baseline differs: {field}")
    report["fec_2022_baseline_reproduced"]=True

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=Path("data/sources/nh01_alton_2022_general_partial.json"))
    parser.add_argument("--elections",type=Path,default=Path("data/processed/elections.csv"))
    parser.add_argument("--output",type=Path,default=Path("data/processed/nh01_alton_2022_general_partial_audit.json"))
    args=parser.parse_args()
    result=inspect_alton(json.loads(args.source.read_text(encoding="utf-8")))
    compare_fec_csv(result,args.elections)
    args.output.parent.mkdir(exist_ok=True,parents=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
