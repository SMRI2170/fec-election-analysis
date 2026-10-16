"""Reproducible candidate-composition diagnostics for the 2022 largest forecast errors.

Source is the independently reconciled FEC candidate rows written by
source_reconcile.py. Never infer causal factors from these retrospective data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

KEY = ["year", "state", "district"]


def build_cases(
    errors: pd.DataFrame,
    elections: pd.DataFrame,
    evidence: dict,
    top_n: int = 5,
) -> pd.DataFrame:
    if top_n < 1:
        raise ValueError("top_n must be positive")
    if errors.duplicated(KEY).any() or elections.duplicated(KEY).any():
        raise ValueError("Duplicate election identity")
    cases = {
        (int(x["year"]), str(x["state"]), str(x["district"]).zfill(2)): x
        for x in evidence["cases"]
    }
    entries = []
    ordered = errors.sort_values("abs_linear_error", ascending=False)
    for rank, row in enumerate(ordered.head(top_n).itertuples(index=False), start=1):
        key = (int(row.year), str(row.state), str(row.district).zfill(2))
        matched = elections[
            (elections["year"] == key[0])
            & (elections["state"] == key[1])
            & (elections["district"].str.zfill(2) == key[2])
        ]
        if len(matched) != 1 or key not in cases:
            raise AssertionError(f"Top error missing original FEC evidence: {key}")
        source = cases[key]
        check = source["check"]
        if not (check["candidate_sums_match"] and check["district_general_matches"]):
            raise AssertionError(f"FEC vote reconciliation failed: {key}")
        values = matched.iloc[0]
        record = {
            "rank": rank, "year": key[0], "state": key[1], "district": key[2],
            "primary_rep_votes": int(values["primary_rep_votes"]),
            "primary_dem_votes": int(values["primary_dem_votes"]),
            "general_rep_votes": int(values["general_rep_votes"]),
            "general_dem_votes": int(values["general_dem_votes"]),
            "primary_rep_share": float(row.primary_rep_share),
            "general_rep_share": float(row.general_rep_share),
            "linear_pred_share": float(row.linear_pred_share),
            "abs_linear_error": float(row.abs_linear_error),
            "primary_rule_error": bool(row.primary_rule_error),
            "logistic_error": bool(row.logistic_error),
            "reconciled_to_official_fec": True,
        }
        for party, prefix in [("R", "rep"), ("D", "dem")]:
            cand = [x for x in source["candidates"] if x["party"] == party]
            numeric_primaries = [
                int(x["primary_votes"]) for x in cand if x["primary_votes"] is not None
            ]
            nonzero_candidates = sum(v > 0 for v in numeric_primaries)
            record[f"{prefix}_candidate_rows"] = len(cand)
            record[f"{prefix}_primary_positive_candidates"] = nonzero_candidates
            named_total = sum(numeric_primaries)
            record[f"{prefix}_named_primary_votes"] = named_total
            record[f"{prefix}_top_named_primary_share"] = (
                max(numeric_primaries) / named_total if named_total else None
            )
            general_candidates = [
                x["name"] for x in cand if x["general_votes"] is not None
                and int(x["general_votes"]) > 0
            ]
            record[f"{prefix}_general_candidate_names"] = " | ".join(general_candidates)
            record[f"{prefix}_footnote_present"] = any(x["footnotes"] for x in cand)

        expected_p = record["primary_rep_votes"] / (
            record["primary_rep_votes"] + record["primary_dem_votes"]
        )
        expected_g = record["general_rep_votes"] / (
            record["general_rep_votes"] + record["general_dem_votes"]
        )
        if abs(expected_p - record["primary_rep_share"]) > 1e-8:
            raise AssertionError(f"Primary share differs from normalized votes: {key}")
        if abs(expected_g - record["general_rep_share"]) > 1e-8:
            raise AssertionError(f"General share differs from normalized votes: {key}")
        entries.append(record)
    return pd.DataFrame(entries)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit top forecast misses against FEC candidate rows")
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args()
    p = args.processed_dir
    errors = pd.read_csv(p / "errors_2022.csv", dtype={"district": str, "state": str})
    votes = pd.read_csv(p / "elections.csv", dtype={"district": str, "state": str})
    evidence = json.loads((p / "case-evidence.json").read_text(encoding="utf-8"))
    result = build_cases(errors, votes, evidence, top_n=args.top_n)
    result.to_csv(p / "2022-top-error-cases.csv", index=False)
    columns = [
        "rank", "state", "district", "abs_linear_error",
        "rep_candidate_rows", "dem_candidate_rows",
        "rep_top_named_primary_share", "dem_top_named_primary_share",
        "primary_rule_error",
    ]
    print(result[columns].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"Saved {p / '2022-top-error-cases.csv'}; no causal inference made.")


if __name__ == "__main__":
    main()
