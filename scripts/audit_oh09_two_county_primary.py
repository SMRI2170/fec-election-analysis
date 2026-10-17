"""Crosscheck two separately certified Ohio OH09 2022 Primary county canvasses.

Defiance and Erie each publish county-specific candidate votes. Their sum is
still only TWO of the eight counties in the congressional district. Neither
document independently certifies the whole OH09 primary.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from audit_oh09_defiance_primary import verify_official_county, FEC_FIELDS, CANDIDATES

ERIE_EXPECTED={
 "Republican":{"Beth Deck":434,"Theresa Gavarone":1987,"J.R. Majewski":2510,"Craig S. Riedel":1917},
 "Democratic":{"Marcy Kaptur":3388},
}
ERIE_TOTAL={"Republican":6848,"Democratic":3388}
EIGHT_COUNTIES={"Defiance","Erie","Fulton","Lucas","Ottawa","Sandusky","Williams","Wood"}

def verify_two_counties(defiance:dict,erie:dict)->dict:
    first=verify_official_county(defiance)
    identity=erie["election"]
    if (identity["year"],identity["state"],identity["district"],identity["stage"],identity["county"],identity["date"])!=(2022,"OH","09","primary","Erie","2022-05-03"):
        raise AssertionError("Unexpected county or stage in certified Erie canvass")
    source=erie["official_source"]
    if (source["official_certified_pdf"]!="https://www.boe.ohio.gov/erie/c/elecres/20220503results.pdf"
        or source["precincts_reported"]!=62 or source["democratic_printed_page"]!=5 or source["republican_printed_page"]!=26):
        raise AssertionError("Erie official canvass page or source identity changed")
    if not erie["no_district_wide_independent_primary_claim"]:
        raise AssertionError("Two counties cannot verify an eight-county district")
    if erie["primary_candidates"]!=ERIE_EXPECTED:
        raise AssertionError("Erie official candidate vote witness changed")
    totals={}
    candidates={}
    for party in ("Republican","Democratic"):
        erie_total=sum(erie["primary_candidates"][party].values())
        if erie_total!=ERIE_TOTAL[party] or erie_total!=erie["official_county_party_totals"][party]:
            raise AssertionError(f"Erie certified {party} subtotal mismatch")
        candidates[party]={name:erie["primary_candidates"][party][name]+defiance["official_county_candidate_votes"][party][name]
                           for name in erie["primary_candidates"][party]}
        county_sum=erie_total+first["official_county_party_totals"][party]
        if county_sum>=FEC_FIELDS[party][1]:
            raise AssertionError("Two-county candidate votes exceed full district FEC votes")
        totals[party]=county_sum
    erie_winner=max(ERIE_EXPECTED["Republican"],key=ERIE_EXPECTED["Republican"].get)
    if erie["county_republican_winner"]!=erie_winner or erie_winner!="J.R. Majewski":
        raise AssertionError("Erie candidate winner differs from certified source")
    if first["county_republican_winner"]!="Craig S. Riedel":
        raise AssertionError("Defiance candidate winner unexpectedly changed")
    if totals!={"Republican":11702,"Democratic":4521}:
        raise AssertionError("Pinned 2-county primary R/D witness changed")
    if set(["Defiance","Erie"])!=set(["Defiance","Erie"]) & EIGHT_COUNTIES:
        raise AssertionError("Primary counties must be in 2022 OH09")
    return {
        "district":"2022-OH-09",
        "stage":"primary",
        "certified_counties":["Defiance","Erie"],
        "other_district_counties_without_independent_primary_vote_reconciliation":
            sorted(EIGHT_COUNTIES-{"Defiance","Erie"}),
        "candidates_two_county_sum":candidates,
        "official_two_county_party_sums":totals,
        "defiance_republican_primary_winner":"Craig S. Riedel",
        "erie_republican_primary_winner":"J.R. Majewski",
        "congressional_district_republican_primary_winner":"J.R. Majewski",
        "independently_verified_whole_district_primary":False,
        "county_sources_are_separately_certified":True,
        "causal_effect_established":False,
        "official_sources":{
            "Defiance":defiance["source"]["official_certified_canvass"],
            "Erie":source["official_certified_pdf"]
        }
    }

def compare_fec_csv(result:dict,path:Path)->None:
    with path.open(newline="",encoding="utf-8") as fp:
        records=[r for r in csv.DictReader(fp) if r["year"]=="2022"
                 and r["state"]=="OH" and r["district"].zfill(2)=="09"]
    if len(records)!=1:
        raise AssertionError("Missing/duplicate FEC OH09 2022 normalized row")
    for party,(field,expected) in FEC_FIELDS.items():
        if int(records[0][field])!=expected:
            raise AssertionError(f"Official FEC baseline changed: {field}")
        if result["official_two_county_party_sums"][party]>=expected:
            raise AssertionError("Two-county votes cannot be promoted to district total")
    result["fec_2022_baseline_matched"]=True

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--defiance",type=Path,default=Path("data/sources/oh09_defiance_2022_primary.json"))
    p.add_argument("--erie",type=Path,default=Path("data/sources/oh09_erie_2022_primary.json"))
    p.add_argument("--elections",type=Path,default=Path("data/processed/elections.csv"))
    p.add_argument("--output",type=Path,default=Path("data/processed/oh09_two_county_primary_audit.json"))
    args=p.parse_args()
    defiance=json.loads(args.defiance.read_text(encoding="utf-8"))
    erie=json.loads(args.erie.read_text(encoding="utf-8"))
    result=verify_two_counties(defiance,erie)
    compare_fec_csv(result,args.elections)
    args.output.parent.mkdir(exist_ok=True,parents=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
