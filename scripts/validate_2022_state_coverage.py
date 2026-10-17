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
