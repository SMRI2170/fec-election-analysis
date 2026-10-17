"""Audit fusion-party primary candidates against FEC party subtotals.

Read-only: this script never modifies normalize_fec.py, study membership, or the
published 916-record baseline. Arithmetic agreement does NOT establish that
fusion-party candidate votes should be assigned to a major-party prediction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

from source_reconcile import read_house, vote

MAJOR = frozenset({"R", "D"})
YEAR_SET = (2016, 2018, 2020, 2022)


def major_tokens(label: object) -> set[str]:
    if pd.isna(label):
        return set()
    raw = str(label).strip().upper()
    # Do not infer the meaning of a star suffix (R*), write-in prefixes
    # (W(D)/W), or standalone party names; examine fusion codes only.
    if "/" not in raw and "+" not in raw:
        return set()
    return set(re.split(r"[/+, ]+", raw)) & MAJOR


def inspect_district(group: pd.DataFrame, year: int, state: str, district: str) -> list[dict]:
    candidates = group[group["_candidate"]]
    ids = [str(x).strip().upper() for x in candidates["FEC ID"] if pd.notna(x)]
    duplicate_ids = {identity for identity, n in Counter(ids).items() if n > 1}
    id_occurrences: dict[str, list[dict]] = {}
    for idx, row in candidates.iterrows():
        fid = str(row["FEC ID"]).strip().upper()
        id_occurrences.setdefault(fid, []).append({
            "excel_row_approx": int(idx) + 2,
            "party_code": str(row["_party"]),
            "primary_votes": vote(row["PRIMARY VOTES"]),
            "general_votes": vote(row.get("GENERAL VOTES")),
        })
    result = []
    for party in ("R", "D"):
        direct = candidates[candidates["_party"].eq(party)]
        attributed = group[group["_party"].eq(f"W({party})")]
        totals = group[group["_marker"].eq("party votes:") & group["_party"].eq(party)]
        base = sum(vote(v) or 0 for v in direct["PRIMARY VOTES"])
        writein = sum(vote(v) or 0 for v in attributed["PRIMARY VOTES"])
        reported = vote(totals.iloc[0]["PRIMARY VOTES"]) if len(totals) == 1 else None
        gap = None if reported is None else reported - base - writein
        evidence = []
        for idx, row in candidates.iterrows():
            tokens = major_tokens(row["_party"])
            if party not in tokens:
                continue
            fid = str(row["FEC ID"]).strip().upper()
            raw_votes = row["PRIMARY VOTES"]
            evidence.append({
                "excel_row_approx": int(idx) + 2,
                "fec_id": fid,
                "candidate_name": None if pd.isna(row.get("CANDIDATE NAME")) else str(row["CANDIDATE NAME"]),
                "party_code": str(row["_party"]),
                "primary_votes": vote(raw_votes),
                "primary_numeric": vote(raw_votes) is not None,
                "major_party_tokens": sorted(tokens),
                "both_major_parties": len(tokens) > 1,
                "duplicate_fec_id_in_district": fid in duplicate_ids,
                "same_id_source_rows": id_occurrences[fid] if fid in duplicate_ids else [],
                "multiple_positive_primary_rows_same_id": sum(
                    (other["primary_votes"] or 0) > 0 for other in id_occurrences[fid]
                ) > 1,
            })
        candidate_total = sum(e["primary_votes"] or 0 for e in evidence)
        exact = (
            gap is not None and gap > 0 and candidate_total == gap and
            len(evidence) > 0
        )
        ambiguous = any(e["both_major_parties"] or e["duplicate_fec_id_in_district"]
                        or not e["primary_numeric"] for e in evidence)
        status = ("missing_party_subtotal" if reported is None
                  else "balanced" if gap == 0
                  else "fusion_arithmetic_match" if exact
                  else "other_discrepancy")
        result.append({
            "year": year, "state": state, "district": district, "party": party,
            "direct_candidate_primary": base,
            "attributed_writein_primary": writein,
            "source_party_subtotal": reported,
            "remaining_gap": gap,
            "fusion_candidate_primary": candidate_total,
            "fusion_candidate_count": len(evidence),
            "arithmetic_match": exact,
            "candidate_identity_or_party_ambiguity": ambiguous,
            "status": status,
            # These are observations, not permission to change the sample.
            "independently_verified_state_primary": False,
            "safe_to_auto_include": False,
            "candidate_evidence": evidence,
        })
    return result


def inspect_all(excluded: pd.DataFrame, raw: dict[int, pd.DataFrame]) -> dict:
    unbalanced = excluded[excluded["reason"].eq("primary-subtotal-mismatch")]
    if unbalanced.duplicated(["year", "state", "district"]).any():
        raise AssertionError("Duplicate district exclusion key")
    out = []
    for year, yr in unbalanced.groupby("year"):
        if int(year) not in raw:
            raise ValueError(f"Missing source workbook for {year}")
        grouped = {(str(state), str(district)): group for
                   (state, district), group in raw[int(year)].groupby(["_state", "_district"])}
        for row in yr.itertuples(index=False):
            state, district = str(row.state), str(row.district).zfill(2)
            group = grouped.get((state, district))
            if group is None:
                raise AssertionError(f"Source group missing: {year} {state}-{district}")
            out.extend(inspect_district(group, int(year), state, district))
    by = Counter(r["status"] for r in out)
    if len(out) != 2 * len(unbalanced):
        raise AssertionError("Each excluded district must have exactly R and D audit records")
    return {
        "scope": "current exclusion rows marked primary-subtotal-mismatch",
        "excluded_districts": len(unbalanced),
        "party_sides": len(out),
        "counts": {name: int(by[name]) for name in
                   ("balanced", "fusion_arithmetic_match", "other_discrepancy",
                    "missing_party_subtotal")},
        "fusion_matches_with_identity_ambiguity": sum(
            r["arithmetic_match"] and r["candidate_identity_or_party_ambiguity"] for r in out),
        "fusion_matches_with_repeated_fec_id": sum(
            r["arithmetic_match"] and any(e["duplicate_fec_id_in_district"]
                                           for e in r["candidate_evidence"]) for r in out),
        "fusion_matches_with_multiple_primary_rows_same_id": sum(
            r["arithmetic_match"] and any(e["multiple_positive_primary_rows_same_id"]
                                           for e in r["candidate_evidence"]) for r in out),
        "no_automatic_reallocation": True,
        "sides": out,
    }


def assert_historical_counts(report: dict) -> None:
    expected = {
        "excluded_districts": 21,
        "party_sides": 42,
        "counts": {
            "balanced": 16,
            "fusion_arithmetic_match": 18,
            "other_discrepancy": 5,
            "missing_party_subtotal": 3,
        },
    }
    for field, wanted in expected.items():
        if report[field] != wanted:
            raise AssertionError(f"2026-10-16 baseline changed: {field}: {report[field]} != {wanted}")
    if report["no_automatic_reallocation"] is not True:
        raise AssertionError("Audit must not modify eligibility")


def verify_official_hashes(raw_dir: Path, expected: Path) -> dict[int, str]:
    pinned = json.loads(expected.read_text(encoding="utf-8"))["official_source_sha256"]
    checksums = {}
    for year in YEAR_SET:
        path = raw_dir / f"federalelections{year}.xlsx"
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        if checksum != pinned[str(year)]:
            raise AssertionError(f"FEC {year} input differs from recorded official SHA-256")
        checksums[year] = checksum
    return checksums


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit FEC fusion-party primary vote evidence without data changes")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--expected", type=Path, default=Path("data/sources/expected_analysis.json"))
    parser.add_argument("--assert-baseline", action="store_true")
    args = parser.parse_args()
    sha = verify_official_hashes(args.raw_dir, args.expected)
    excluded = pd.read_csv(args.processed_dir / "exclusions.csv", dtype={"state": str, "district": str})
    source = {year: read_house(args.raw_dir / f"federalelections{year}.xlsx")[1] for year in YEAR_SET}
    report = inspect_all(excluded, source)
    if args.assert_baseline:
        assert_historical_counts(report)
    report["official_source_sha256"] = {str(year): value for year, value in sha.items()}
    args.processed_dir.mkdir(parents=True, exist_ok=True)
    output = args.processed_dir / "fusion-primary-evidence.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "excluded_districts": report["excluded_districts"],
        "party_sides": report["party_sides"],
        "counts": report["counts"],
        "fusion_matches_with_identity_ambiguity": report["fusion_matches_with_identity_ambiguity"],
        "fusion_matches_with_repeated_fec_id": report["fusion_matches_with_repeated_fec_id"],
        "fusion_matches_with_multiple_primary_rows_same_id": report["fusion_matches_with_multiple_primary_rows_same_id"],
        "repeated_fec_id_details": [
            {"district": f'{r["year"]}-{r["state"]}-{r["district"]}', "party": r["party"],
             "candidate_rows": [
                 {"id": e["fec_id"], "source_rows": e["same_id_source_rows"]}
                 for e in r["candidate_evidence"] if e["duplicate_fec_id_in_district"]
             ]}
            for r in report["sides"] if r["arithmetic_match"] and any(
                e["duplicate_fec_id_in_district"] for e in r["candidate_evidence"])
        ],
        "fusion_match_details": [
            {"district": f'{r["year"]}-{r["state"]}-{r["district"]}', "party": r["party"],
             "gap": r["remaining_gap"],
             "candidates": [{"fec_id": e["fec_id"], "party_code": e["party_code"],
                             "primary_votes": e["primary_votes"]}
                            for e in r["candidate_evidence"]]}
            for r in report["sides"] if r["arithmetic_match"]
        ],
        "no_automatic_reallocation": report["no_automatic_reallocation"],
        "evidence": str(output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
