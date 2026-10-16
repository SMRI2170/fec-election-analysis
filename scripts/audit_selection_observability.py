"""Diagnose observability and vote margins of excluded FEC House report groups.

Use only observed FEC workbook data. Missing or 'Unopposed' cells are never
imputed, and General outcomes are used for retrospective diagnostics only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from source_reconcile import read_house, vote


KEY = ["year", "state", "district"]
PARTIES = ("R", "D")


def describe_group(group: pd.DataFrame, year: int, state: str, district: str) -> dict:
    result: dict = {"year": year, "state": state, "district": district}
    source_primaries: dict[str, int | None] = {}
    source_general: dict[str, int | None] = {}

    for party in PARTIES:
        rows = group[group["_party"].eq(party)]
        candidates = rows[rows["_candidate"]]
        primary_subtotals = rows[rows["_marker"].eq("party votes:")]
        if len(primary_subtotals) == 1:
            source_primaries[party] = vote(primary_subtotals.iloc[0]["PRIMARY VOTES"])
        else:
            source_primaries[party] = None

        general_values = [vote(x) for x in candidates["GENERAL VOTES"]]
        # A blank indicates no reported votes for that candidate, not a zero
        # observed count. Keep the missing count and use numeric rows only.
        numerical = [v for v in general_values if v is not None]
        source_general[party] = sum(numerical) if numerical else None
        result[f"{party.lower()}_candidate_rows"] = len(candidates)
        result[f"{party.lower()}_general_numeric_rows"] = len(numerical)
        result[f"{party.lower()}_general_missing_or_text_rows"] = len(candidates) - len(numerical)
        result[f"{party.lower()}_primary_unopposed_rows"] = int(
            candidates["PRIMARY VOTES"].astype("string").str.strip().str.lower().eq("unopposed").sum()
        )
        result[f"{party.lower()}_primary_party_subtotal_available"] = source_primaries[party] is not None

    r_primary, d_primary = source_primaries["R"], source_primaries["D"]
    result["primary_r_subtotal"] = r_primary
    result["primary_d_subtotal"] = d_primary
    result["primary_reported_both"] = (
        r_primary is not None and d_primary is not None and r_primary + d_primary > 0
    )
    result["primary_r_reported_share"] = (
        r_primary / (r_primary + d_primary) if result["primary_reported_both"] else None
    )
    r_general, d_general = source_general["R"], source_general["D"]
    result["general_r_observed_candidate_votes"] = r_general
    result["general_d_observed_candidate_votes"] = d_general
    result["general_both_observed"] = (
        r_general is not None and d_general is not None and r_general + d_general > 0
    )
    result["general_observed_r_share"] = (
        r_general / (r_general + d_general) if result["general_both_observed"] else None
    )
    result["general_observed_abs_margin"] = (
        abs(result["general_observed_r_share"] - 0.5) * 2
        if result["general_both_observed"] else None
    )
    return result


def diagnose(
    included: pd.DataFrame,
    excluded: pd.DataFrame,
    raw_by_year: dict[int, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    included_keys = set(included[KEY].itertuples(index=False, name=None))
    excluded_map = {
        (int(row.year), str(row.state), str(row.district).zfill(2)): str(row.reason)
        for row in excluded.itertuples(index=False)
    }
    if len(excluded_map) != len(excluded):
        raise ValueError("Duplicate exclusion keys")
    if included_keys & set(excluded_map):
        raise ValueError("A district is simultaneously selected and excluded")

    records = []
    for year, workbook in sorted(raw_by_year.items()):
        for (state, district), group in workbook.groupby(["_state", "_district"]):
            key = (year, str(state), str(district).zfill(2))
            if key not in included_keys and key not in excluded_map:
                raise AssertionError(f"Unaccounted source election: {key}")
            row = describe_group(group, *key)
            row["included"] = key in included_keys
            row["exclusion_reason"] = excluded_map.get(key, "")
            records.append(row)
    frame = pd.DataFrame(records)
    if len(frame) != len(included_keys) + len(excluded_map):
        raise AssertionError("Report groups must be one-to-one with selected + excluded")

    grouped = []
    for (year, status, reason), part in frame.groupby(
        ["year", "included", "exclusion_reason"], dropna=False
    ):
        observable_primary = part["primary_reported_both"]
        observable_general = part["general_both_observed"]
        margin = part.loc[observable_general, "general_observed_abs_margin"].dropna()
        grouped.append({
            "year": year,
            "included": bool(status),
            "exclusion_reason": reason or "included",
            "groups": len(part),
            "both_primary_subtotals_available": int(observable_primary.sum()),
            "both_general_parties_observed": int(observable_general.sum()),
            "median_observed_general_abs_margin": (
                float(margin.median()) if len(margin) else None
            ),
            "observed_general_close_within_10pp": (
                int((margin <= 0.10).sum()) if len(margin) else None
            ),
        })
    summary = pd.DataFrame(grouped)
    coverage = {
        "total_report_groups": len(frame),
        "included": int(frame["included"].sum()),
        "excluded": int((~frame["included"]).sum()),
        "source_primary_both_covered_selected": int(
            (frame["included"] & frame["primary_reported_both"]).sum()
        ),
        "source_primary_both_covered_excluded": int(
            (~frame["included"] & frame["primary_reported_both"]).sum()
        ),
        "general_two_party_numeric_selected": int(
            (frame["included"] & frame["general_both_observed"]).sum()
        ),
        "general_two_party_numeric_excluded": int(
            (~frame["included"] & frame["general_both_observed"]).sum()
        ),
        "missing_votes_imputed": False,
        "general_outcomes_are_post_election_diagnostics_not_features": True,
        "general_margin_uses_only_reported_numeric_R_D_candidate_rows": True,
        "report_groups_are_not_a_US_national_probability_sample": True,
    }
    # Compare competitiveness only where the original workbook contains
    # observed numeric R and D General candidate votes. This is NOT an
    # estimate for excluded groups lacking comparable candidate vote cells.
    for name, selected in (("selected", True), ("excluded", False)):
        comparable = frame[frame["included"].eq(selected) & frame["general_both_observed"]]
        margins = comparable["general_observed_abs_margin"].dropna()
        coverage[f"{name}_general_margin_comparable_n"] = len(margins)
        coverage[f"{name}_general_median_abs_margin"] = (
            float(margins.median()) if len(margins) else None
        )
        coverage[f"{name}_general_margin_within_10pp_n"] = (
            int((margins <= 0.10).sum()) if len(margins) else 0
        )
    return frame, summary, coverage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrospective selection diagnostics from actual FEC workbook cells"
    )
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()

    included = pd.read_csv(
        args.processed_dir / "elections.csv", dtype={"state": str, "district": str}
    )
    excluded = pd.read_csv(
        args.processed_dir / "exclusions.csv", dtype={"state": str, "district": str}
    )
    sources = {
        int(year): read_house(args.input_dir / f"federalelections{year}.xlsx")[1]
        for year in sorted(included.year.unique())
    }
    observations, by_reason, summary = diagnose(included, excluded, sources)
    observations.sort_values(KEY).to_csv(
        args.processed_dir / "selection-observability.csv", index=False
    )
    by_reason.sort_values(["year", "included", "exclusion_reason"]).to_csv(
        args.processed_dir / "selection-observability-summary.csv", index=False
    )
    (args.processed_dir / "selection-observability-meta.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    print(by_reason.to_string(index=False))
    print("No imputation; General margins are outcome diagnostics, never predictors.")


if __name__ == "__main__":
    main()
