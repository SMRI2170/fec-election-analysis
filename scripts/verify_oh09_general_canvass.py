"""Independently reconcile 2022 Ohio OH-09 General votes using Ohio's canvass.

Input is an explicit transcription from Lucas County BOE's certified 8-county
congressional canvass, hosted by Defiance County BOE. The original certification
is *not* dynamically downloaded or parsed by CI; official FEC is downloaded.
The 2022 May Primary is outside the scope of this particular source.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

COUNTIES = frozenset({"Defiance", "Erie", "Fulton", "Lucas", "Ottawa",
                      "Sandusky", "Williams", "Wood"})
CANDIDATES = {
    "Marcy Kaptur (D)": ("general_dem_votes", 150655),
    "J.R. Majewski (R)": ("general_rep_votes", 115362),
}


def audit_canvass(source: dict) -> dict:
    if (source.get("year"), source.get("state"), source.get("district"),
            source.get("election")) != (2022, "OH", "09", "general"):
        raise ValueError("Wrong election identity")
    if source.get("date") != "2022-11-08":
        raise ValueError("Wrong official general election date")
    src = source["official_source"]
    if not src["certified_all_counties"].startswith("https://www.boe.ohio.gov/"):
        raise ValueError("Expected official Ohio county BOE source")
    if set(source["counties"]) != COUNTIES:
        raise AssertionError("Certified 8-county universe changed")
    if set(source["officially_certified_district_candidate_totals"]) != set(CANDIDATES):
        raise AssertionError("Unexpected certified candidates")
    if source["verification"]["primary_district_complete"] is not False:
        raise AssertionError("General-only source cannot independently verify Primary")
    if source["verification"]["general_district_complete"] is not True:
        raise AssertionError("This source covers all eight counties in General")
    totals = {}
    for candidate, (fec_key, expected) in CANDIDATES.items():
        values = []
        for county, votes in source["counties"].items():
            if set(votes) != set(CANDIDATES):
                raise AssertionError(f"Candidate missing in {county}")
            value = votes[candidate]
            if type(value) is not int or value < 0:
                raise ValueError(f"Invalid county vote for {county} {candidate}")
            values.append(value)
        county_sum = sum(values)
        published = source["officially_certified_district_candidate_totals"][candidate]
        if published != expected or county_sum != published:
            raise AssertionError(
                f"County vs published official total mismatch: {candidate}: {county_sum} != {published}"
            )
        totals[fec_key] = county_sum
    return {
        "year": 2022, "state": "OH", "district": "09",
        "official_certified_2022_general_totals": totals,
        "all_eight_official_counties_reconciled": True,
        "official_primary_reconciled": False,
        "published_certified_canvass_url": src["certified_all_counties"],
        "causality_established": False,
    }


def compare_fec_csv(report: dict, normalized_csv: Path) -> None:
    with normalized_csv.open(newline="", encoding="utf-8") as f:
        matching = [r for r in csv.DictReader(f) if r["year"] == "2022"
                    and r["state"] == "OH" and r["district"].zfill(2) == "09"]
    if len(matching) != 1:
        raise AssertionError("Expected one FEC normalized 2022 OH-09 row")
    for field, expected in report["official_certified_2022_general_totals"].items():
        if int(matching[0][field]) != expected:
            raise AssertionError(f"Independent Ohio canvass disagrees with FEC {field}")
    report["general_state_vs_fec_match"] = True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/sources/oh09_2022_official_general_canvass.json"))
    parser.add_argument("--elections", type=Path, default=Path("data/processed/elections.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/oh09_2022_general_canvass_audit.json"))
    args = parser.parse_args()
    report = audit_canvass(json.loads(args.source.read_text(encoding="utf-8")))
    compare_fec_csv(report, args.elections)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
