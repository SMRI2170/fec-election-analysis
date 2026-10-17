"""Audit pre-General compatible Primary records vs post-General label availability.

IMPORTANT: This is a RETROSPECTIVE reconstruction from FEC's final election
workbook, not a dated pre-election release. No row is proven to have been
available before the General election. Do not claim operational forecast
performance from this sample. The frozen selected 916 records are unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from normalize_fec import DEFAULT_EXCLUDE_STATES, NONVOTING_DELEGATE_JURISDICTIONS
from source_reconcile import read_house, vote

KEY = ("year", "state", "district")
YEARS = (2016, 2018, 2020, 2022)
EXPECTED_YEAR_GROUPS = {2016: 438, 2018: 438, 2020: 441, 2022: 439}
EXPECTED_SELECTED = {2016: 200, 2018: 241, 2020: 237, 2022: 238}
# Independently reproduced from official FEC post-election source by CI #55.
EXPECTED_PRIMARY_COMPATIBLE = {2016: 200, 2018: 243, 2020: 237, 2022: 239}
EXPECTED_POST_GENERAL_REMOVED = {2016: 0, 2018: 2, 2020: 0, 2022: 1}
SUBTOTAL_LABELS = frozenset({"party votes:", "district votes:", "total votes:"})


def primary_only_compatibility(group: pd.DataFrame, state: str) -> dict:
    """Reproduce applicable Primary subtests; never touch any General columns."""
    result = {
        "primary_report_compatible": False, "primary_exclusion_reason": None,
        "primary_r_votes_reconstructed": None, "primary_d_votes_reconstructed": None,
    }
    if state in NONVOTING_DELEGATE_JURISDICTIONS:
        reason = "nonvoting-delegate-jurisdiction"
    elif state in DEFAULT_EXCLUDE_STATES:
        reason = "needs-state-election-rule-review"
    else:
        reason = None
    if reason is None:
        unresolved = group[
            group["_party"].isin(["R", "D"]) &
            ~group["_candidate"] &
            ~group["_marker"].isin(SUBTOTAL_LABELS)
        ]
        if not unresolved.empty:
            reason = "unclassified-party-row"
    totals = {}
    if reason is None:
        for party in ("R", "D"):
            candidates = group[group["_candidate"] & group["_party"].eq(party)]
            if candidates.empty:
                reason = "missing-party-candidates"
                break
            raw_primaries = candidates["PRIMARY VOTES"].astype("string").str.strip().str.lower()
            if raw_primaries.eq("unopposed").any():
                reason = "unopposed-primary"
                break
            summary = group[group["_marker"].eq("party votes:") & group["_party"].eq(party)]
            if len(summary) > 1:
                reason = "duplicate-party-subtotals"
                break
            named_primary = sum(vote(v) or 0 for v in candidates["PRIMARY VOTES"])
            affiliated = group[group["_party"].eq(f"W({party})")]
            affiliated_numeric = [vote(v) for v in affiliated["PRIMARY VOTES"]]
            if any(pd.notna(v) and n is None for v, n in
                   zip(affiliated["PRIMARY VOTES"], affiliated_numeric)):
                reason = "ambiguous-affiliated-writein"
                break
            writein = sum(v or 0 for v in affiliated_numeric)
            if len(summary) == 1:
                party_total = vote(summary.iloc[0]["PRIMARY VOTES"])
                if party_total is None or party_total != named_primary + writein:
                    reason = "primary-subtotal-mismatch"
                    break
            else:
                if writein:
                    reason = "missing-primary-party-subtotal"
                    break
                party_total = named_primary
            if party_total == 0:
                reason = "missing-or-zero-primary-votes"
                break
            totals[party] = party_total
    result["primary_exclusion_reason"] = reason
    result["primary_report_compatible"] = reason is None
    if reason is None:
        result["primary_r_votes_reconstructed"] = int(totals["R"])
        result["primary_d_votes_reconstructed"] = int(totals["D"])
    return result


def general_outcome_observability(group: pd.DataFrame) -> dict:
    """Diagnostic only: General columns are NOT used in Primary eligibility."""
    totals = {}
    non_numeric = {}
    for party in ("R", "D"):
        candidates = group[group["_candidate"] & group["_party"].eq(party)]
        numeric_values = [vote(v) for v in candidates["GENERAL VOTES"]]
        totals[party] = sum(n or 0 for n in numeric_values)
        non_numeric[party] = sum(
            pd.notna(v) and n is None for v, n in
            zip(candidates["GENERAL VOTES"], numeric_values)
        )
    special_columns = [
        col for col in group.columns
        if col.startswith(("GE RUNOFF ELECTION VOTES", "1ST ROUND RCV VOTES",
                           "2ND ROUND RCV VOTES", "3RD ROUND RCV VOTES"))
    ]
    special = any(
        any((vote(v) or 0) > 0 for v in group[column])
        for column in special_columns
    )
    return {
        "post_general_rd_numeric_observable": bool(
            totals["R"] > 0 and totals["D"] > 0 and
            non_numeric["R"] == 0 and non_numeric["D"] == 0),
        "general_r_observed_candidate_votes": int(totals["R"]),
        "general_d_observed_candidate_votes": int(totals["D"]),
        "general_r_non_numeric_candidate_rows": int(non_numeric["R"]),
        "general_d_non_numeric_candidate_rows": int(non_numeric["D"]),
        "general_special_runoff_or_rcv_observed": bool(special),
    }


def _index(df: pd.DataFrame, name: str) -> dict[tuple[int, str, str], dict]:
    if not set(KEY).issubset(df.columns):
        raise AssertionError(f"{name} missing year/state/district")
    result = {}
    for row in df.to_dict(orient="records"):
        k = (int(row["year"]), str(row["state"]), str(row["district"]).zfill(2))
        if k in result:
            raise AssertionError(f"{name} repeated key {k}")
        result[k] = row
    return result


def build_ledger(included: pd.DataFrame, excluded: pd.DataFrame,
                 raw_by_year: dict[int, pd.DataFrame],
                 enforce_baseline: bool = False) -> tuple[pd.DataFrame, dict]:
    """One-to-one audit of raw FEC report groups against frozen final selection."""
    kept = _index(included, "frozen selected")
    dropped = _index(excluded, "frozen excluded")
    if set(kept) & set(dropped):
        raise AssertionError("FEC record both selected and excluded")
    if set(raw_by_year) != set(YEARS) and enforce_baseline:
        raise AssertionError("Must inspect four official FEC election years")
    rows = []
    for year, raw in sorted(raw_by_year.items()):
        for (state, district), group in raw.groupby(["_state", "_district"], sort=True):
            k = (int(year), str(state), str(district).zfill(2))
            if k not in kept and k not in dropped:
                raise AssertionError(f"Unaccounted FEC report group {k}")
            if k in kept and k in dropped:
                raise AssertionError(f"Overlapping final disposition {k}")
            primary = primary_only_compatibility(group, k[1])
            outcome = general_outcome_observability(group)
            selected = k in kept
            reason = "" if selected else str(dropped[k]["reason"])
            if selected and not primary["primary_report_compatible"]:
                raise AssertionError(f"Selected FEC row fails Primary-only conditions {k}")
            if selected and not outcome["post_general_rd_numeric_observable"]:
                raise AssertionError(f"Selected FEC row has no observed two-party General label {k}")
            if selected and outcome["general_special_runoff_or_rcv_observed"]:
                raise AssertionError(f"Selected FEC row has special General election {k}")
            if selected:
                for party, name in (("R", "rep"), ("D", "dem")):
                    val = primary[f"primary_{party.lower()}_votes_reconstructed"]
                    if val != int(kept[k][f"primary_{name}_votes"]):
                        raise AssertionError(f"FEC Primary reconstruction differs from frozen row {k}")
                    if outcome[f"general_{party.lower()}_observed_candidate_votes"] != int(kept[k][f"general_{name}_votes"]):
                        raise AssertionError(f"FEC General candidate vote total differs from frozen row {k}")
            rows.append({
                "year": k[0], "state": k[1], "district": k[2],
                # This is not true pre-election data: final FEC report rows.
                "fec_workbook_is_postelection_publication": True,
                "primary_snapshot_timestamp_verified": False,
                "operational_pre_election_eligibility_proven": False,
                **primary, **outcome,
                "final_916_selected": bool(selected),
                "final_exclusion_reason": reason,
                "post_general_label_and_primary_compatible": bool(
                    primary["primary_report_compatible"] and
                    outcome["post_general_rd_numeric_observable"]),
                "selection_uses_post_general_information": bool(
                    primary["primary_report_compatible"] and
                    (not outcome["post_general_rd_numeric_observable"] or
                     outcome["general_special_runoff_or_rcv_observed"] or
                     reason.startswith("official-ge-"))),
            })
    table = pd.DataFrame(rows).sort_values(list(KEY)).reset_index(drop=True)
    if len(table) != len(kept) + len(dropped):
        raise AssertionError("Raw groups do not match final dispositions")
    if table.duplicated(list(KEY)).any():
        raise AssertionError("FEC raw election key duplicated")
    if int(table.final_916_selected.sum()) != len(kept):
        raise AssertionError("Final selected row count disagrees with baseline")
    years = []
    for year, part in table.groupby("year"):
        compat = part[part.primary_report_compatible]
        years.append({
            "year": int(year), "raw_fec_groups": int(len(part)),
            "retrospective_primary_compatible": int(len(compat)),
            "primary_conditions_failed": int((~part.primary_report_compatible).sum()),
            "general_rd_numeric_observed_among_primary_compatible":
                int(compat.post_general_rd_numeric_observable.sum()),
            "general_rd_not_observed_among_primary_compatible":
                int((~compat.post_general_rd_numeric_observable).sum()),
            "post_general_rd_observed_but_not_final_selected":
                int((compat.post_general_rd_numeric_observable & ~compat.final_916_selected).sum()),
            "final_selected": int(part.final_916_selected.sum()),
            "final_excluded": int((~part.final_916_selected).sum()),
            "selection_depends_on_postgeneral_information_count":
                int(part.selection_uses_post_general_information.sum()),
        })
    summary = {
        "schema_version": 1,
        "source": "2026-10-17 reconstruction from final FEC federal election House workbooks",
        "primary_report_compatible_is_not_verified_pre_election_availability": True,
        "pre_election_snapshot_proven_rows": 0,
        "general_outcomes_never_used_to_determine_primary_compatibility": True,
        "legacy_916_cohort_unchanged": True,
        "post_general_observed_is_not_equivalent_to_certified_winner": True,
        "frozen_cohort_records": int(len(kept)),
        "total_fec_report_groups": int(len(table)),
        "years": years,
        "excluded_reason_counts": {
            str(reason): int(n)
            for reason, n in sorted(table.loc[~table.final_916_selected, "final_exclusion_reason"]
                                    .value_counts().items())
        },
        "primary_compatibility_exclusion_counts": {
            str(reason): int(n)
            for reason, n in sorted(table.loc[~table.primary_report_compatible, "primary_exclusion_reason"]
                                    .value_counts().items())
        },
        "limitations": [
            "FEC final workbook has no validated Primary-stage publication timestamp",
            "Primary rule compatibility is retrospectively reconstructed, not actual operational forecasting eligibility",
            "General two-party candidate vote observability is known only after the General election",
            "Missing General R/D votes are NOT imputed; no predictive performance assigned to unlabelled groups",
            "State-specific primary systems and special elections remain outside the frozen sample",
            "Prior 2018/2020/2022 testing and eligibility revisions are exploratory, not prospectively preregistered",
        ],
    }
    if enforce_baseline:
        if {item["year"]: item["raw_fec_groups"] for item in years} != EXPECTED_YEAR_GROUPS:
            raise AssertionError("FEC original report-group population changed")
        if {item["year"]: item["final_selected"] for item in years} != EXPECTED_SELECTED:
            raise AssertionError("916 frozen selected cohort changed")
        if {item["year"]: item["retrospective_primary_compatible"] for item in years} != EXPECTED_PRIMARY_COMPATIBLE:
            raise AssertionError("Official FEC Primary-only eligible counts changed")
        if {item["year"]: item["post_general_rd_observed_but_not_final_selected"] for item in years} != EXPECTED_POST_GENERAL_REMOVED:
            raise AssertionError("Post-General exclusion count changed")
        if any(item["general_rd_not_observed_among_primary_compatible"] for item in years):
            raise AssertionError("Unexpected missing General two-party label among Primary compatible")
        if len(table) != 1756 or len(kept) != 916 or len(dropped) != 840:
            raise AssertionError("Original FEC / frozen selection totals changed")
    return table, summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    p.add_argument("--assert-baseline", action="store_true")
    args = p.parse_args()
    included = pd.read_csv(args.processed_dir / "elections.csv", dtype={"state": str, "district": str})
    excluded = pd.read_csv(args.processed_dir / "exclusions.csv", dtype={"state": str, "district": str})
    raw = {year: read_house(args.input_dir / f"federalelections{year}.xlsx")[1] for year in YEARS}
    table, summary = build_ledger(included, excluded, raw, args.assert_baseline)
    args.processed_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.processed_dir / "prediction-time-cohort.csv", index=False)
    (args.processed_dir / "prediction-time-cohort-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PREDICTION_TIME_AUDIT_START")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("PREDICTION_TIME_AUDIT_END")


if __name__ == "__main__":
    main()
