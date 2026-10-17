"""Audit the certified Defiance County portion of Ohio OH-09 2022 primary.

The one-county canvass is independent of FEC. Its county-only totals must not
be promoted to complete congressional-district reconciliation or causal proof.
The Ohio source PDF is manually transcribed; the official FEC XLSX is fetched
and normalized by CI.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

CANDIDATES = {
    "Republican":{"Beth Deck":226,"Theresa Gavarone":548,"J.R. Majewski":1315,"Craig S. Riedel":2765},
    "Democratic":{"Marcy Kaptur":1133},
}
COUNTY_TOTALS={"Republican":4854,"Democratic":1133}
FEC_FIELDS={"Republican":("primary_rep_votes",61090),"Democratic":("primary_dem_votes",32968)}

def verify_official_county(source:dict)->dict:
    e=source["election"]
    if (e["year"],e["state"],e["district"],e["stage"],e["date"],e["county"]) != (2022,"OH","09","primary","2022-05-03","Defiance"):
        raise AssertionError("Incorrect primary election scope: expected OH-09 Defiance 2022")
    s=source["source"]
    if (s["official_certified_canvass"] != "https://www.boe.ohio.gov/defiance/c/elecres/20220503results.pdf"
        or s["certification_date"] != "2022-05-24"):
        raise AssertionError("Official certified May 2022 Ohio source identity changed")
    obs=source["observation"]
    if not obs["county_partial_only"] or obs["primary_full_district_independently_verified"] or obs["not_causal_evidence"] is not True:
        raise AssertionError("A single county is not the full OH-09 district")
    if source["district_fec_baseline_2022"] != {field:total for field,total in FEC_FIELDS.values()}:
        raise AssertionError("FEC district baselines are pinned to the 2022 FEC cohort")
    if set(source["official_county_candidate_votes"])!=set(CANDIDATES):
        raise AssertionError("Both local primary parties must be recorded")
    party_totals={}
    for party,candidates in CANDIDATES.items():
        actual=source["official_county_candidate_votes"][party]
        if actual != candidates:
            raise AssertionError(f"Certified {party} candidate witness changed; verify source PDF")
        if any(type(v) is not int or v<0 for v in actual.values()):
            raise AssertionError("Official candidate votes must be nonnegative integers")
        summation=sum(actual.values())
        if summation != COUNTY_TOTALS[party] or summation != source["official_county_subtotals"][party]:
            raise AssertionError(f"Certified {party} subtotal does not equal county candidate sum")
        if summation >= FEC_FIELDS[party][1]:
            raise AssertionError("County-only totals must be smaller than district totals")
        party_totals[party]=summation
    winner=max(source["official_county_candidate_votes"]["Republican"],key=source["official_county_candidate_votes"]["Republican"].get)
    if (winner != "Craig S. Riedel" or obs["county_republican_primary_winner"]!=winner
        or obs["district_republican_primary_winner"]!="J.R. Majewski"
        or obs["winner_differs_because_of_geographic_scope"] is not True):
        raise AssertionError("Do not infer congressional district winner from one county")
    return {
        "identity":"2022-OH-09-Defiance-Primary",
        "official_county_party_totals":party_totals,
        "county_republican_candidate_votes":CANDIDATES["Republican"],
        "county_republican_winner":winner,
        "district_fec_republican_winner_context":"J.R. Majewski",
        "county_partial_only":True,
        "full_district_primary_independently_verified":False,
        "causal_explanation_established":False,
        "official_county_canvass_url":s["official_certified_canvass"],
    }

def compare_fec_csv(report:dict,path:Path)->None:
    with path.open(encoding="utf-8",newline="") as fp:
        rows=[r for r in csv.DictReader(fp)
              if r["year"]=="2022" and r["state"]=="OH" and str(r["district"]).zfill(2)=="09"]
    if len(rows)!=1:
        raise AssertionError("Expected exactly one 2022 OH-09 normalized district row")
    for party,(field,expected) in FEC_FIELDS.items():
        actual=int(rows[0][field])
        if actual != expected:
            raise AssertionError(f"Official FEC district baseline changed for {party}: {actual} != {expected}")
        if report["official_county_party_totals"][party]>=actual:
            raise AssertionError("A county must not be promoted to the district")
    report["fec_baseline_matched_without_promoting_county_to_district"]=True

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=Path("data/sources/oh09_defiance_2022_primary.json"))
    p.add_argument("--elections",type=Path,default=Path("data/processed/elections.csv"))
    p.add_argument("--output",type=Path,default=Path("data/processed/oh09_defiance_primary_audit.json"))
    args=p.parse_args()
    report=verify_official_county(json.loads(args.source.read_text(encoding="utf-8")))
    compare_fec_csv(report,args.elections)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
