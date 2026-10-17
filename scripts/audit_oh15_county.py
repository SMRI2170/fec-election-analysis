"""Check Clark County's official OH-15 vote record against FEC district totals.

A county is only one part of a congressional district. Never upgrade the
independent verification status to district_complete from this partial source.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FIELD_MAP = {
    "primary_rep_votes": ("primary", "Mike Carey (R)"),
    "primary_dem_votes": ("primary", "Gary Josephson (D)"),
    "general_rep_votes": ("general", "Mike Carey (R)"),
    "general_dem_votes": ("general", "Gary Josephson (D)"),
}


def audit_county(source: dict) -> dict:
    if (source.get("year"), source.get("state"), source.get("district"), source.get("county")) != (2022, "OH", "15", "Clark"):
        raise ValueError("Incorrect independent OH-15 source identity")
    if source.get("verification_level") != "county_only_not_district_complete":
        raise AssertionError("County data must not be labeled as full district verification")
    if source["official_sources"]["primary_date"] != "2022-05-03" or source["official_sources"]["general_date"] != "2022-11-08":
        raise ValueError("Election dates changed")
    if not all(str(source["official_sources"][k]).startswith("https://liveresults.boe.ohio.gov/")
               for k in ("primary", "general")):
        raise ValueError("Evidence must reference county Board of Elections official results")
    expected = source["district_fec_comparison_values"]
    actual_fields = set(FIELD_MAP)
    if set(expected) != actual_fields:
        raise AssertionError("All four FEC comparison fields must be supplied")
    observation = {}
    for field, (stage, candidate) in FIELD_MAP.items():
        value = source["county_votes"][stage][candidate]
        upper = expected[field]
        if type(value) is not int or type(upper) is not int or value < 0 or upper <= 0:
            raise ValueError("Votes must be nonnegative integers")
        if value >= upper:
            raise AssertionError(f"Clark county cannot equal/exceed OH-15 entire district: {field}")
        observation[field] = {
            "clark_county_votes": value,
            "fec_district_votes": upper,
            "unverified_remainder": upper - value,
            "clark_share_of_fec_district": round(value / upper, 6),
        }
    if source["county_votes"]["primary"] != {"Mike Carey (R)": 3398, "Gary Josephson (D)": 365}:
        raise AssertionError("Official Clark County primary source snapshot changed")
    if source["county_votes"]["general"] != {"Mike Carey (R)": 15671, "Gary Josephson (D)": 5407}:
        raise AssertionError("Official Clark County general source snapshot changed")
    return {
        "state": "OH", "district": "15", "year": 2022,
        "county": "Clark", "verification_level": "county_only_not_district_complete",
        "official_county_votes_mathematically_consistent_with_fec": True,
        "complete_district_reconciliation_verified": False,
        "comparisons": observation,
    }


def compare_fec_csv(summary: dict, elections_csv: Path) -> None:
    with elections_csv.open(newline="", encoding="utf-8") as fp:
        matches = [row for row in csv.DictReader(fp) if row["year"] == "2022"
                   and row["state"] == "OH" and row["district"].zfill(2) == "15"]
    if len(matches) != 1:
        raise AssertionError("Expected exactly one 2022 OH-15 voting House row")
    record = matches[0]
    for name, comparison in summary["comparisons"].items():
        if int(record[name]) != comparison["fec_district_votes"]:
            raise AssertionError(f"FEC normalized votes changed: {name}")
    summary["fec_baseline_reproduced"] = True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/sources/oh15_clark_2022_official_votes.json"))
    parser.add_argument("--elections", type=Path, default=Path("data/processed/elections.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/oh15_clark_county_fec_audit.json"))
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    summary = audit_county(source)
    compare_fec_csv(summary, args.elections)
    summary["sources"] = source["official_sources"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
