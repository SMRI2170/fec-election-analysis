"""OH-09 2022 Ohio independent county-primary audit: Defiance + Erie + Ottawa.

Ottawa County publishes an *amended* official canvass dated June 8, 2022.
This script computes candidate-level sums for three of eight counties and
compares the partial R/D totals to a separately fetched FEC district baseline.
It cannot establish the district-wide primary subtotal or any causal effect.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from audit_oh09_two_county_primary import verify_two_counties, FEC_FIELDS, EIGHT_COUNTIES

OTT_CANDIDATES={
    "Republican":{"Beth Deck":208,"Theresa Gavarone":1639,"J.R. Majewski":2027,"Craig S. Riedel":1383},
    "Democratic":{"Marcy Kaptur":2138},
}
OTT_TOTALS={"Republican":5257,"Democratic":2138}
THREE_CANDIDATES={
    "Republican":{"Beth Deck":868,"Theresa Gavarone":4174,"J.R. Majewski":5852,"Craig S. Riedel":6065},
    "Democratic":{"Marcy Kaptur":6659},
}
THREE_TOTALS={"Republican":16959,"Democratic":6659}
CERTIFIED_COUNTIES=("Defiance","Erie","Ottawa")

def verify_three_counties(defiance:dict,erie:dict,ottawa:dict)->dict:
    two=verify_two_counties(defiance,erie)
    if (ottawa.get("year"),ottawa.get("state"),ottawa.get("district"),ottawa.get("county"),
        ottawa.get("stage"),ottawa.get("election_date"))!=(2022,"OH","09","Ottawa","primary","2022-05-03"):
        raise AssertionError("Ottawa source election identity differs from 2022 OH09 Primary")
    source=ottawa["official_source"]
    if (source["official_pdf"]!="https://boe.ottawa.oh.gov/wp-content/uploads/2022/06/Amended-Official-Summary.pdf"
        or source["report_timestamp"]!="2022-06-08 15:54"
        or source["democratic_pdf_page_index"]!=2 or source["republican_pdf_page_index"]!=7):
        raise AssertionError("Ottawa source, amended date or PDF page locator changed")
    scope=ottawa["scope"]
    if not scope["amended_official_county_primary"] or not scope["county_subset_only"] or scope["eight_county_district_complete"] or scope["causality_established"]:
        raise AssertionError("Three counties must not be labelled as complete OH09 district")
    if ottawa["candidates"]!=OTT_CANDIDATES:
        raise AssertionError("Official Ottawa candidate transcription differs from pinned amended canvass")
    if ottawa["published_party_totals"]!=OTT_TOTALS:
        raise AssertionError("Official Ottawa party subtotals changed")
    for party in ("Republican","Democratic"):
        if sum(ottawa["candidates"][party].values())!=OTT_TOTALS[party]:
            raise AssertionError(f"Ottawa {party} subtotal and candidate votes are inconsistent")
        counts=ottawa["vote_issues"][party]
        if (counts["overvotes"]+counts["undervotes"]+OTT_TOTALS[party]) != counts["contest_totals"]:
            raise AssertionError(f"Ottawa {party} overvotes/undervotes must be kept separate")
    combined={}
    for party in ("Republican","Democratic"):
        combined[party]={name:two["candidates_two_county_sum"][party][name]+ottawa["candidates"][party][name]
                         for name in OTT_CANDIDATES[party]}
        if combined[party]!=THREE_CANDIDATES[party]:
            raise AssertionError(f"Three-county {party} candidate totals drifted")
        if sum(combined[party].values())!=THREE_TOTALS[party]:
            raise AssertionError(f"Three-county {party} subtotal drifted")
        if THREE_TOTALS[party]>=FEC_FIELDS[party][1]:
            raise AssertionError("Three county votes cannot equal the entire OH09 district")
    if max(OTT_CANDIDATES["Republican"],key=OTT_CANDIDATES["Republican"].get)!="J.R. Majewski":
        raise AssertionError("Ottawa local Republican Primary winner unexpectedly changed")
    missing=sorted(EIGHT_COUNTIES-set(CERTIFIED_COUNTIES))
    if len(missing)!=5:
        raise AssertionError("Five counties should still require independent primary verification")
    return {
        "study_year":2022,"state":"OH","district":"09","stage":"primary",
        "certified_counties":list(CERTIFIED_COUNTIES),
        "remaining_unverified_counties":missing,
        "three_county_candidate_totals":combined,
        "three_county_primary_party_totals":THREE_TOTALS,
        "fec_district_primary_context":{"R":FEC_FIELDS["Republican"][1],"D":FEC_FIELDS["Democratic"][1]},
        "three_county_counties_covered":3,
        "district_counties_total":8,
        "full_district_primary_independently_reconciled":False,
        "proof_is_noncausal":True,
        "official_sources":{
          "Defiance":two["official_sources"]["Defiance"],
          "Erie":two["official_sources"]["Erie"],
          "Ottawa":source["official_pdf"]
        },
        "ottawa_version":"Amended Official Results dated 2022-06-08",
        "official_pdf_not_parsed_in_ci":True
    }


def compare_fec_csv(result:dict, csv_path:Path)->None:
    with csv_path.open(newline="",encoding="utf-8") as f:
        records=[row for row in csv.DictReader(f)
            if row["year"]=="2022" and row["state"]=="OH" and row["district"].zfill(2)=="09"]
    if len(records)!=1:
        raise AssertionError("Expected exactly one official FEC OH09 2022 normalized row")
    for party,(field,expected) in FEC_FIELDS.items():
        if int(records[0][field])!=expected:
            raise AssertionError(f"2022 FEC baseline changed: {field}")
        if result["three_county_primary_party_totals"][party]>=expected:
            raise AssertionError("Ohio three-county subtotal cannot equal FEC district")
    result["official_fec_2022_baseline_reproduced"]=True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--defiance",type=Path,default=Path("data/sources/oh09_defiance_2022_primary.json"))
    p.add_argument("--erie",type=Path,default=Path("data/sources/oh09_erie_2022_primary.json"))
    p.add_argument("--ottawa",type=Path,default=Path("data/sources/oh09_ottawa_2022_amended_primary.json"))
    p.add_argument("--elections",type=Path,default=Path("data/processed/elections.csv"))
    p.add_argument("--output",type=Path,default=Path("data/processed/oh09_three_county_primary_audit.json"))
    args=p.parse_args()
    read=lambda path:json.loads(path.read_text(encoding="utf-8"))
    result=verify_three_counties(read(args.defiance),read(args.erie),read(args.ottawa))
    compare_fec_csv(result,args.elections)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
