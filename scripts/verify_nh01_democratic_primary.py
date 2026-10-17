"""Read-only audit: NH Secretary of State 2022 CD1 Democratic primary.

Manually transcribed official NH SOS PDF Totals row, independently compared
to FEC-normalized 2022 NH-01 Democratic PRIMARY votes. This does not certify
NH-01 Republican primary or General results. CI does not fetch the NH PDF.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

EXPECTED_WRITEINS = {
    "Tom Alciere": 1, "Tim Baxter": 19, "Gail Huff Brown": 42,
    "Mark Kilbane": 0, "Karoline Leavitt": 72, "Mary Maxwell": 2,
    "Matt Mowers": 72, "Russell Prescott": 15, "Kevin Rondeau": 2,
    "Gilead R. Towne": 1,
}

def audit_official_primary(source: dict) -> dict:
    identity = source["election"]
    if (identity["year"],identity["state"],identity["district"],
        identity["stage"],identity["date"]) != (2022,"NH","01","democratic_primary","2022-09-13"):
        raise AssertionError("Official NH-01 primary source identity is not fixed")
    if not source["source"]["official_pdf"].startswith("https://www.sos.nh.gov/"):
        raise ValueError("A NH Secretary of State official source URL is required")
    scope = source["verification_scope"]
    if scope["republican_primary"] or scope["general_election"] or not scope["democratic_primary"]:
        raise AssertionError("Democratic-only PDF cannot verify Republican or General elections")
    official = source["reported_totals"]
    if set(official["write_in_named"]) != set(EXPECTED_WRITEINS):
        raise AssertionError("Official NH write-in candidate set has changed")
    if official["write_in_named"] != EXPECTED_WRITEINS:
        raise AssertionError("Official NH write-in totals changed; verify the PDF before updating")
    pappas = official["Chris Pappas (D)"]
    scattered = official["scattered_write_in"]
    if (type(pappas) is not int or type(scattered) is not int or
         pappas < 0 or scattered < 0):
        raise ValueError("Official votes must be nonnegative integers")
    named = sum(official["write_in_named"].values())
    total = pappas + named + scattered
    if (pappas, named, scattered, total) != (41990, 226, 152, 42368):
        raise AssertionError(f"Expected official NH 2022 D primary 41990+226+152=42368; got {pappas}+{named}+{scattered}={total}")
    if official["all_votes"] != total or source["fec_baseline"]["primary_dem_votes"] != total:
        raise AssertionError("NH official Democratic total differs from recorded baseline")
    return {
        "year":2022,"state":"NH","district":"01","stage":"democratic_primary",
        "official_pappas_primary_votes":pappas,
        "official_named_writeins":named,
        "official_scattered_writeins":scattered,
        "official_democratic_primary_total":total,
        "official_source_pdf":source["source"]["official_pdf"],
        "independent_democratic_primary_reconciled":False,
        "independent_republican_primary_reconciled":False,
        "independent_general_reconciled":False,
    }

def compare_fec_csv(result: dict, elections_path: Path) -> None:
    with elections_path.open(newline="", encoding="utf-8") as f:
        matches = [r for r in csv.DictReader(f)
                   if r["year"]=="2022" and r["state"]=="NH"
                   and r["district"].zfill(2)=="01"]
    if len(matches)!=1:
        raise AssertionError(f"Expected one NH-01 election, got {len(matches)}")
    actual = int(matches[0]["primary_dem_votes"])
    if actual != result["official_democratic_primary_total"]:
        raise AssertionError(f"NH official state D primary vs FEC mismatch: {actual}")
    result["independent_democratic_primary_reconciled"] = True

def main():
    p=argparse.ArgumentParser(description="Independently crosscheck NH-01 Democratic primary (not other races)")
    p.add_argument("--source",type=Path,default=Path("data/sources/nh01_2022_democratic_primary.json"))
    p.add_argument("--elections",type=Path,default=Path("data/processed/elections.csv"))
    p.add_argument("--output",type=Path,default=Path("data/processed/nh01_2022_democratic_primary_audit.json"))
    args=p.parse_args()
    record=json.loads(args.source.read_text(encoding="utf-8"))
    result=audit_official_primary(record)
    compare_fec_csv(result,args.elections)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
