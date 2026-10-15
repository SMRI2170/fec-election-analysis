"""Independent row-level reconciliation against the official FEC House workbook.

Does not alter inclusion criteria. Checks candidate vote sums and district totals.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
import pandas as pd

KEYS = ("year", "state", "district")
VOTE_FIELDS = {
    ("R", "PRIMARY VOTES"): "primary_rep_votes",
    ("D", "PRIMARY VOTES"): "primary_dem_votes",
    ("R", "GENERAL VOTES"): "general_rep_votes",
    ("D", "GENERAL VOTES"): "general_dem_votes",
}

def vote(value: object) -> int | None:
    if pd.isna(value):
        return None
    value = str(value).strip().replace(",", "")
    if not re.fullmatch(r"\d+(?:\.0+)?", value):
        return None
    return int(float(value))

def dist(value: object) -> str | None:
    if pd.isna(value):
        return None
    value = str(value).strip()
    if re.fullmatch(r"\d{1,2}(?:\.0+)?", value):
        return f"{int(float(value)):02d}"
    return None

def read_house(path: Path) -> tuple[str, pd.DataFrame]:
    with pd.ExcelFile(path) as book:
        sheets = [name for name in book.sheet_names if "US House Results by State" in name]
        if len(sheets) != 1:
            raise ValueError(f"{path.name}: expected one House sheet, got {sheets}")
        sheet = sheets[0]
        data = pd.read_excel(book, sheet_name=sheet)
    aliases = {"D": "DISTRICT", "FEC ID#": "FEC ID"}
    data.columns = [aliases.get(str(c).strip().upper(), str(c).strip().upper()) for c in data.columns]
    data["_state"] = data["STATE ABBREVIATION"].astype("string").str.strip().str.upper()
    data["_district"] = data["DISTRICT"].map(dist)
    data["_party"] = data["PARTY"].astype("string").str.strip().str.upper()
    data["_marker"] = data["TOTAL VOTES"].astype("string").str.strip().str.lower()
    data["_candidate"] = data["FEC ID"].astype("string").str.strip().str.upper().str.fullmatch(r"H[A-Z0-9]+", na=False)
    data = data[data["_state"].str.fullmatch(r"[A-Z]{2}", na=False) & data["_district"].notna()].copy()
    return sheet, data

def audit_one(group: pd.DataFrame, expected: pd.Series) -> tuple[dict, list[dict]]:
    details = []
    computed = {}
    for party in ("R", "D"):
        candidates = group[(group["_candidate"]) & (group["_party"] == party)]
        for field in ("PRIMARY VOTES", "GENERAL VOTES"):
            numbers = [vote(v) for v in candidates[field]]
            subtotal = sum(v for v in numbers if v is not None)
            if field == "PRIMARY VOTES":
                # Independent inclusion of all W(R)/W(D) lines.
                # Does not depend on the normalized primary value.
                attributed_writeins = group[group["_party"].eq(f"W({party})")]
                subtotal += sum(vote(v) or 0 for v in attributed_writeins[field])
            computed[VOTE_FIELDS[party, field]] = subtotal
        for _, row in candidates.iterrows():
            details.append({
                "party": party, "fec_id": str(row["FEC ID"]),
                "name": str(row.get("CANDIDATE NAME", "")),
                "primary_votes": vote(row["PRIMARY VOTES"]),
                "general_votes": vote(row["GENERAL VOTES"]),
                "footnotes": None if pd.isna(row.get("FOOTNOTES")) else str(row["FOOTNOTES"])[:160],
            })
    mismatch = [key for key, value in computed.items() if value != int(expected[key])]
    total_rows = group[group["_marker"].eq("district votes:")]
    reported = vote(total_rows.iloc[0]["GENERAL VOTES"]) if len(total_rows) == 1 else None
    # Some valid minor-party / write-in rows have NO FEC candidate ID.
    # The official District Votes total sums all rows carrying a party label,
    # excluding explicit Party Votes / District Votes subtotal rows.
    actual_general_total = sum(
        vote(row["GENERAL VOTES"]) or 0
        for _, row in group.iterrows()
        if pd.notna(row["_party"])
        and str(row["_marker"]) not in {"district votes:", "party votes:", "total votes:"}
    )
    district_matches = None if reported is None else reported == actual_general_total
    return {
        **{name: int(expected[name]) for name in computed},
        "candidate_sums_match": not mismatch,
        "candidate_mismatch_fields": ",".join(mismatch),
        "district_general_total": reported,
        "candidate_plus_scattered_general": actual_general_total,
        "district_general_matches": district_matches,
        "candidate_rows_R_D": len(details),
    }, details

def mismatch_reason_example(group: pd.DataFrame, year: int, state: str, district: str) -> dict:
    out = {"year": year, "state": state, "district": district, "parties": []}
    for party in ("R", "D"):
        candidates = group[group["_candidate"] & group["_party"].eq(party)]
        subtotal = group[group["_marker"].eq("party votes:") & group["_party"].eq(party)]
        out["parties"].append({
            "party": party,
            "candidate_primary_sum": sum(vote(v) or 0 for v in candidates["PRIMARY VOTES"]),
            "subtotal_rows": len(subtotal),
            "reported_primary_subtotal": vote(subtotal.iloc[0]["PRIMARY VOTES"]) if len(subtotal) == 1 else None,
            "primary_non_numeric_count": sum(pd.notna(v) and vote(v) is None for v in candidates["PRIMARY VOTES"]),
            "candidate_names": [str(v) for v in candidates.get("CANDIDATE NAME", pd.Series(dtype=str)).head(6)],
        })
    return out

def reconcile(data: pd.DataFrame, raw_by_year: dict[int, pd.DataFrame],
              errors: pd.DataFrame | None = None, exclusions: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    checkpoints = [("2020", "AL", "01")]
    if errors is not None:
        checkpoints += [(str(v.year), str(v.state), str(v.district).zfill(2)) for v in errors.head(5).itertuples()]
    summary_rows = []
    evidence = {"cases": [], "exclusion_examples": []}
    for year, rows in data.groupby("year"):
        groups = {(str(s), str(d)): g for (s, d), g in raw_by_year[int(year)].groupby(["_state", "_district"])}
        for row in rows.itertuples(index=False):
            group = groups.get((str(row.state), str(row.district).zfill(2)))
            if group is None:
                raise AssertionError(f"Raw district missing: {year} {row.state}-{row.district}")
            check, candidates = audit_one(group, pd.Series(row._asdict()))
            record = {key: getattr(row, key) for key in KEYS} | check
            summary_rows.append(record)
            if (str(year), str(row.state), str(row.district).zfill(2)) in checkpoints:
                evidence["cases"].append({
                    "year": int(year), "state": str(row.state), "district": str(row.district).zfill(2),
                    "check": record, "candidates": candidates,
                })
    if exclusions is not None:
        for year, failures in exclusions[exclusions["reason"] == "primary-subtotal-mismatch"].groupby("year"):
            groups = {(str(s), str(d)): g for (s, d), g in raw_by_year[int(year)].groupby(["_state", "_district"])}
            for row in failures.head(3).itertuples():
                evidence["exclusion_examples"].append(
                    mismatch_reason_example(groups[(row.state, str(row.district).zfill(2))],
                                            int(year), str(row.state), str(row.district).zfill(2))
                )
    results = pd.DataFrame(summary_rows)
    evidence["summary"] = {
        "reconciled_records": len(results),
        "candidate_sum_mismatches": int((~results["candidate_sums_match"]).sum()),
        "district_total_available": int(results["district_general_total"].notna().sum()),
        "district_total_mismatches": int((results["district_general_matches"] == False).sum()),
        "official_source_consistency_is_not_causal_validity": True,
    }
    return results, evidence

def main() -> None:
    parser = argparse.ArgumentParser(description="Audit normalized election rows against original FEC Excel")
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    data = pd.read_csv(args.processed_dir / "elections.csv", dtype={"district": str, "state": str})
    errors = pd.read_csv(args.processed_dir / "errors_2022.csv", dtype={"district": str, "state": str})
    exclusions = pd.read_csv(args.processed_dir / "exclusions.csv", dtype={"district": str, "state": str})
    raw = {int(year): read_house(args.input_dir / f"federalelections{year}.xlsx")[1]
           for year in sorted(data.year.unique())}
    checks, evidence = reconcile(data, raw, errors, exclusions)
    checks.to_csv(args.processed_dir / "source-reconciliation.csv", index=False)
    (args.processed_dir / "case-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(evidence["summary"], indent=2))
    for case in evidence["cases"]:
        check = case["check"]
        print(f"case {case['year']} {case['state']}-{case['district']}: "
              f"candidate votes verified={check['candidate_sums_match']}; "
              f"district subtotal verified={check['district_general_matches']}")
    for item in evidence["exclusion_examples"][:8]:
        print("mismatch-example", json.dumps(item, ensure_ascii=False))
    if evidence["summary"]["candidate_sum_mismatches"]:
        raise AssertionError("Normalized candidate sums conflict with original FEC rows")
    if evidence["summary"]["district_total_mismatches"]:
        raise AssertionError("District General votes do not reconcile with FEC source rows")

if __name__ == "__main__":
    main()
