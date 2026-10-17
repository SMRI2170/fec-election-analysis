"""Inspect 2020 Wisconsin House primary party subtotals around districts 01/02.

This is a read-only audit. A matching gap is *not* permission to rewrite votes,
change candidate district IDs, or expand the study sample.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from source_reconcile import read_house, vote

FIELDS = ("STATE ABBREVIATION", "DISTRICT", "CANDIDATE NAME",
          "FEC ID", "PARTY", "PRIMARY VOTES", "TOTAL VOTES", "FOOTNOTES")
DISTRICTS = ("01", "02")


def source_rows(frame: pd.DataFrame, district: str) -> list[dict]:
    rows = frame[(frame["_state"] == "WI") & (frame["_district"] == district)]
    result = []
    for index, row in rows.iterrows():
        entry = {"excel_row_approx": int(index) + 2}
        for field in FIELDS:
            value = row.get(field)
            entry[field] = None if pd.isna(value) else str(value)
        result.append(entry)
    return result


def summarize_party(frame: pd.DataFrame, district: str, party: str = "R") -> dict:
    group = frame[(frame["_state"] == "WI") & (frame["_district"] == district)]
    if group.empty:
        raise ValueError(f"No WI-{district} raw rows")
    candidate = group[group["_candidate"] & group["_party"].eq(party)]
    writeins = group[group["_party"].eq(f"W({party})")]
    totals = group[group["_marker"].eq("party votes:") & group["_party"].eq(party)]
    if len(totals) != 1:
        raise ValueError(f"WI-{district}: expected exactly one {party} subtotal")
    subtotal = vote(totals.iloc[0]["PRIMARY VOTES"])
    if subtotal is None:
        raise ValueError(f"WI-{district}: missing numeric {party} subtotal")
    candidate_votes = sum(vote(v) or 0 for v in candidate["PRIMARY VOTES"])
    writein_votes = sum(vote(v) or 0 for v in writeins["PRIMARY VOTES"])
    return {
        "district": district,
        "party": party,
        "candidate_votes": candidate_votes,
        "affiliated_writein_votes": writein_votes,
        "official_party_subtotal": subtotal,
        "remaining_gap": subtotal - candidate_votes - writein_votes,
        "writein_primary_rows": [
            {"excel_row_approx": int(idx) + 2,
             "party_code": str(row["PARTY"]),
             "primary_votes": vote(row["PRIMARY VOTES"])}
            for idx, row in writeins.iterrows()
        ],
        "source_rows": source_rows(frame, district),
    }


def audit(frame: pd.DataFrame) -> dict:
    results = [summarize_party(frame, district) for district in DISTRICTS]
    by_district = {entry["district"]: entry for entry in results}
    gap1, gap2 = by_district["01"]["remaining_gap"], by_district["02"]["remaining_gap"]
    # This is only a diagnostic hint; the FEC PDF/official state canvass
    # must independently confirm attribution before any change to normalization.
    candidate_transfer = (
        gap1 > 0 and gap1 == -gap2 and any(
            row["primary_votes"] == gap1
            for row in by_district["02"]["writein_primary_rows"]
        )
    )
    return {
        "year": 2020,
        "state": "WI",
        "party": "R",
        "districts": results,
        "opposite_gap_with_matching_wi02_writein": candidate_transfer,
        "automatic_reallocation": False,
        "note": "Diagnostic only. Excel row numbers assume the first worksheet row is the column header.",
    }


def verify_observed_2020_boundary(report: dict) -> None:
    """Fail CI if the evidence recorded in the research note no longer holds."""
    results = {record["district"]: record for record in report["districts"]}
    expect = {
        "01": (40273, 0, 40404, 131),
        "02": (18812, 181, 18862, -131),
    }
    for district, expected in expect.items():
        item = results[district]
        actual = (item["candidate_votes"], item["affiliated_writein_votes"],
                  item["official_party_subtotal"], item["remaining_gap"])
        if actual != expected:
            raise AssertionError(f"WI-{district} official primary evidence changed: {actual}")
    suspicious = [row for row in results["02"]["writein_primary_rows"]
                  if row["excel_row_approx"] == 3941
                  and row["party_code"] == "W(R)" and row["primary_votes"] == 131]
    if not suspicious or not report["opposite_gap_with_matching_wi02_writein"]:
        raise AssertionError("Expected out-of-order WI-02 W(R) 131 source row not found")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, default=Path("data/raw/federalelections2020.xlsx"))
    parser.add_argument("--expected", type=Path, default=Path("data/sources/expected_analysis.json"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/wi-2020-primary-boundary-audit.json"))
    parser.add_argument("--require-known-snapshot", action="store_true")
    args = parser.parse_args()
    wanted = json.loads(args.expected.read_text(encoding="utf-8"))["official_source_sha256"]["2020"]
    actual = hashlib.sha256(args.workbook.read_bytes()).hexdigest()
    if actual != wanted:
        raise AssertionError("2020 official workbook SHA-256 changed; do not draw conclusions")
    sheet, frame = read_house(args.workbook)
    report = audit(frame)
    report["source_sheet"] = sheet
    report["source_sha256"] = actual
    if args.require_known_snapshot:
        verify_observed_2020_boundary(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
