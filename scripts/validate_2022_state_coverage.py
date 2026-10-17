"""Fail-closed independent 2022 state vote evidence coverage validator.

Prevents a located source or single county subset from being silently promoted
to district-wide source verification. Does not alter the published FEC cohort.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path

DISTRICTS = ("RI-02", "OH-15", "OH-09", "MI-03", "NH-01")
LEVELS = frozenset({"district_verified", "partial_subdistrict", "not_verified"})
STAGES = ("primary", "general")
PARTIES = ("R", "D")
FIELDS = {
    ("primary","R"):"primary_rep_votes",
    ("primary","D"):"primary_dem_votes",
    ("general","R"):"general_rep_votes",
    ("general","D"):"general_dem_votes",
}
WITNESS = {
    "RI-02": {"primary":{"R":12113,"D":56102},"general":{"R":93969,"D":101432}},
    "OH-15": {"primary":{"R":48938,"D":9047},"general":{"R":143112,"D":108139}},
    "OH-09": {"primary":{"R":61090,"D":32968},"general":{"R":115362,"D":150655}},
    "MI-03": {"primary":{"R":104576,"D":59661},"general":{"R":142229,"D":185989}},
    "NH-01": {"primary":{"R":75401,"D":42368},"general":{"R":142229,"D":167391}},
}


def validate_ledger(ledger: dict, root: Path, fec_2022_csv: Path | None = None) -> dict:
    if ledger.get("study_year") != 2022 or ledger.get("schema_version") != 1:
        raise AssertionError("Evidence ledger year/schema changed")
    if set(ledger["cases"]) != set(DISTRICTS):
        raise AssertionError("Exactly the fixed top five 2022 error districts must be listed")
    guard = ledger["safeguards"]
    if (guard["baseline_total_study_records"] != 916 or
        guard["holdout_2022_records"] != 238 or
        not guard["do_not_treat_document_discovery_as_reconciliation"] or
        not guard["municipality_must_be_in_2022_congressional_district"]):
        raise AssertionError("The study baseline or independent-source safeguards changed")
    counts = Counter()
    for district in DISTRICTS:
        if set(ledger["cases"][district]) != set(STAGES):
            raise AssertionError(f"Missing primary/general stage: {district}")
        for stage in STAGES:
            parties = ledger["cases"][district][stage]
            if set(parties) != set(PARTIES):
                raise AssertionError(f"Missing R/D party at {district} {stage}")
            for party in PARTIES:
                entry = parties[party]
                level = entry["level"]
                votes = entry["votes"]
                if level not in LEVELS:
                    raise AssertionError(f"Invalid independent verification level at {district}")
                if level == "not_verified":
                    if votes is not None or entry["evidence"] is not None or entry["source_url"] is not None:
                        raise AssertionError("Unverified source may not carry independently confirmed votes")
                else:
                    if type(votes) is not int or votes < 0:
                        raise AssertionError("Verified or partial votes must be nonnegative integers")
                    if not entry["source_url"] or not entry["source_url"].startswith("https://"):
                        raise AssertionError("Verified source needs its official URL")
                    evidence = entry["evidence"]
                    if not evidence or not (root / evidence).is_file():
                        raise AssertionError(f"Evidence file missing: {evidence}")
                    expected = WITNESS[district][stage][party]
                    if level == "district_verified" and votes != expected:
                        raise AssertionError(f"Independent district votes differ from FEC witness: {district} {stage} {party}")
                    if level == "partial_subdistrict" and votes >= expected:
                        raise AssertionError("Subdistrict votes cannot meet or exceed full-district votes")
                    # The OH-09 Primary remains a partial three-county witness.
                    # Its R/D subtotal and each individual official source must
                    # be retained before this stage may be called independently
                    # verified at any higher level.
                    if district == "OH-09" and stage == "primary" and level == "partial_subdistrict":
                        pinned = {"R": 16959, "D": 6659}[party]
                        if votes != pinned or entry.get("included_counties") != ["Defiance", "Erie", "Ottawa"]:
                            raise AssertionError("OH-09 three-county Primary witness changed; check official results")
                        expected_sources = [
                            ("Defiance", "data/sources/oh09_defiance_2022_primary.json"),
                            ("Erie", "data/sources/oh09_erie_2022_primary.json"),
                        ]
                        present = entry.get("additional_county_sources", [])
                        if [(x.get("county"), x.get("evidence")) for x in present] != expected_sources:
                            raise AssertionError("OH-09 source must preserve Defiance and Erie county evidence")
                        if entry["evidence"] != "data/sources/oh09_ottawa_2022_amended_primary.json":
                            raise AssertionError("OH-09 amended Ottawa evidence must remain the third county")
                        sources = [root / x["evidence"] for x in present] + [root / entry["evidence"]]
                        if not all(p.is_file() for p in sources):
                            raise AssertionError("One of the three certified OH-09 source files is missing")
                        raw = [json.loads(p.read_text(encoding="utf-8")) for p in sources]
                        county_totals = (
                            raw[0]["official_county_subtotals"],
                            raw[1]["official_county_party_totals"],
                            raw[2]["published_party_totals"],
                        )
                        for idx, row in enumerate(county_totals):
                            expected_party_votes = (row["Republican"] if party == "R" else row["Democratic"])
                            expected_county_sum = sum((
                                raw[0]["official_county_candidate_votes"],
                                raw[1]["primary_candidates"],
                                raw[2]["candidates"],
                            )[idx]["Republican" if party == "R" else "Democratic"].values())
                            if expected_party_votes != expected_county_sum:
                                raise AssertionError("OH-09 county candidate votes and published party sum diverged")
                        three_sum = sum(row["Republican" if party == "R" else "Democratic"] for row in county_totals)
                        if three_sum != pinned:
                            raise AssertionError("OH-09 independent three-county evidence does not sum to the ledger")
                    if district == "NH-01" and level == "partial_subdistrict":
                        goffstown_path = "data/sources/nh01_goffstown_2022_primary_general.json"
                        if entry["evidence"] != goffstown_path:
                            raise AssertionError("NH-01 partial evidence must link to the Goffstown official town witness")
                        goffstown = json.loads((root / goffstown_path).read_text(encoding="utf-8"))
                        if stage == "primary":
                            if party != "R" or votes != 1947 or entry.get("included_municipalities") != ["Goffstown"]:
                                raise AssertionError("NH-01 Republican Primary remains only a Goffstown town partial witness")
                            prim = goffstown["republican_primary"]
                            named = sum(prim["named_candidate_votes"].values())
                            valid = named + sum(prim["named_cross_party_writein"].values()) + prim["writeins_under_5_votes_each"]
                            if named != 1940 or valid != votes or prim["named_cross_party_writein"] != {"Chris Pappas": 5}:
                                raise AssertionError("NH-01 GOP town primary candidate/write-in source does not reconcile")
                        else:
                            want = {"R": 5656, "D": 5179}[party]
                            if votes != want or entry.get("included_municipalities") != ["Alton", "Goffstown"]:
                                raise AssertionError("NH-01 general remains only a two-town partial witness")
                            alton_source = entry.get("additional_town_source", {})
                            alton_path = "data/sources/nh01_alton_2022_general_partial.json"
                            if alton_source.get("evidence") != alton_path or not (root / alton_path).is_file():
                                raise AssertionError("NH-01 Alton town component source is missing")
                            alton = json.loads((root / alton_path).read_text(encoding="utf-8"))
                            name = {"R": "Karoline Leavitt (R)", "D": "Chris Pappas (D)"}[party]
                            alton_vote = alton["recorded_party_candidate_votes"][name]
                            goffstown_vote = goffstown["general"]["party_candidate_votes"][name]
                            if (alton_vote + goffstown_vote != votes or
                                alton_vote != {"R":1936,"D":1224}[party] or
                                goffstown_vote != {"R":3720,"D":3955}[party]):
                                raise AssertionError("NH-01 Alton + Goffstown primary-source witness sums changed")
                counts[level] += 1
    if sum(counts.values()) != 20:
        raise AssertionError("Expected five cases x two elections x two parties = 20 cells")
    if fec_2022_csv is not None:
        with fec_2022_csv.open(newline="", encoding="utf-8") as stream:
            rows = {(r["state"],str(r["district"]).zfill(2)):r for r in csv.DictReader(stream)
                    if r["year"] == "2022"}
        for district in DISTRICTS:
            state, num = district.split("-")
            r = rows.get((state,num))
            if r is None:
                raise AssertionError(f"Missing FEC baseline record for {district}")
            for (stage,party),field in FIELDS.items():
                if int(r[field]) != WITNESS[district][stage][party]:
                    raise AssertionError(f"Baseline FEC source changed: {district} {field}")
    known = {(r["district"],r["stage"]) for r in ledger["source_discovery_only"]}
    if len(known) != len(ledger["source_discovery_only"]):
        raise AssertionError("Duplicate pending state-source discovery record")
    for found in ledger["source_discovery_only"]:
        if found["district"] not in DISTRICTS or not found["source_url"].startswith("https://"):
            raise AssertionError("Invalid source discovery reference")
        if "status" not in found or "transcribed" not in found["status"] and "not_inspected" not in found["status"]:
            raise AssertionError("Document discovery must be explicitly marked as unverified")
    full_both_stages = sum(all(
        ledger["cases"][district][stage][party]["level"]=="district_verified"
        for stage in STAGES for party in PARTIES
    ) for district in DISTRICTS)
    return {
        "parties_x_stages":20,
        "district_verified_party_stages":counts["district_verified"],
        "partial_subdistrict_party_stages":counts["partial_subdistrict"],
        "not_verified_party_stages":counts["not_verified"],
        "whole_cases_verified_primary_and_general":full_both_stages,
        "districts_total":5,
        "source_discovery_is_not_verification":True,
        "frozen_study_records":916,
        "frozen_holdout_2022":238,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--ledger",type=Path,default=Path("data/sources/2022_state_evidence_coverage.json"))
    p.add_argument("--fec-2022-csv",type=Path,default=None)
    p.add_argument("--output",type=Path,default=Path("data/processed/2022_state_evidence_coverage_summary.json"))
    args=p.parse_args()
    ledger=json.loads(args.ledger.read_text(encoding="utf-8"))
    report=validate_ledger(ledger,Path("."),args.fec_2022_csv)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
