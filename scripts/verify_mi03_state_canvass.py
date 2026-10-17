"""Validate Michigan legislature's published MI-03 2022 county canvass.

Read-only independent-source evidence: compare a source-transcribed county table
with published statewide totals and the FEC-normalized two-party election record.
Do not infer effects of incumbency, campaign strategy, or primary competition.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

PARTIES = {
    "primary_rep_votes": ("primary", ("John Gibbs (R)", "Peter Meijer (R)")),
    "primary_dem_votes": ("primary", ("Hillary Scholten (D)",)),
    "general_rep_votes": ("general", ("John Gibbs (R)",)),
    "general_dem_votes": ("general", ("Hillary Scholten (D)",)),
}


def verify_canvass(canvass: dict) -> dict:
    if (canvass.get("year"), canvass.get("state"), canvass.get("district")) != (2022, "MI", "03"):
        raise ValueError("Wrong year/state/district for this independent source")
    counties = canvass["county_order"]
    if sorted(counties) != ["Kent", "Muskegon", "Ottawa"] or len(set(counties)) != 3:
        raise ValueError("MI-03 official county list changed")
    totals = {}
    for election in ("primary", "general"):
        votes = canvass[election]
        checks = canvass["official_statewide_checks"][election]
        if set(votes) != set(checks):
            raise AssertionError(f"{election} candidate lists do not match publication totals")
        for candidate, by_county in votes.items():
            if set(by_county) != set(counties):
                raise AssertionError(f"{election} {candidate}: unexpected county set")
            if any(type(v) is not int or v < 0 for v in by_county.values()):
                raise ValueError("County votes must be nonnegative integers")
            summed = sum(by_county.values())
            if summed != checks[candidate]:
                raise AssertionError(f"State manual vs counties mismatch: {election}, {candidate}, {summed} != {checks[candidate]}")
            totals[f"{election}:{candidate}"] = summed
    if sum(canvass["official_statewide_checks"]["general"].values()) != canvass["official_statewide_checks"]["general_all_candidates"]:
        raise AssertionError("General statewide sum of all four named candidates changed")
    fec_fields = {
        field: sum(totals[f"{stage}:{candidate}"] for candidate in candidates)
        for field, (stage, candidates) in PARTIES.items()
    }
    return {"year": 2022, "state": "MI", "district": "03",
            "official_counties": counties,
            "published_statewide_values_match_county_sums": True,
            "general_all_candidates": canvass["official_statewide_checks"]["general_all_candidates"],
            "fec_two_party_fields": fec_fields,
            "comparison_type": "source-transcribed official MI manual vs independent FEC normalization",
            "verified_causal_explanation": False}


def compare_fec_csv(summary: dict, elections_path: Path) -> None:
    with elections_path.open(newline="", encoding="utf-8") as fp:
        matches = [row for row in csv.DictReader(fp) if row["year"] == "2022"
                   and row["state"] == "MI" and row["district"].zfill(2) == "03"]
    if len(matches) != 1:
        raise AssertionError(f"Expected exactly one 2022 MI-03 normalized election, found {len(matches)}")
    matched = matches[0]
    for field, expected in summary["fec_two_party_fields"].items():
        actual = int(matched[field])
        if actual != expected:
            raise AssertionError(f"State vs FEC discrepancy: {field}, {actual} != {expected}")
    summary["independent_state_to_fec_match"] = True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/sources/mi03_2022_state_canvass.json"))
    parser.add_argument("--elections", type=Path, default=Path("data/processed/elections.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/mi03_state_fec_audit.json"))
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    report = verify_canvass(source)
    compare_fec_csv(report, args.elections)
    report["official_state_manual"] = source["source"]["official_state_manual"]
    report["county_primary"] = source["source"]["county_primary"]
    report["county_general"] = source["source"]["county_general"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
