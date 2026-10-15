"""Conservative normalizer for 2016/2018/2020/2022 FEC US House results sheets.

Output is a subset: an excluded-contest audit must accompany every dataset.
No imputation of missing primary votes or inferences about special elections.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

REQUIRED = ("STATE ABBREVIATION", "DISTRICT", "FEC ID", "TOTAL VOTES", "PARTY", "PRIMARY VOTES", "GENERAL VOTES")
DEFAULT_EXCLUDE_STATES = frozenset({"AK", "CA", "CT", "LA", "NY", "WA"})
STANDARD_COLUMNS = ["year", "state", "chamber", "district", "primary_rep_votes", "primary_dem_votes", "general_rep_votes", "general_dem_votes", "source_file", "source_sheet", "election_id"]


def numeric_vote(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    txt = str(value).strip().replace(",", "")
    if not re.fullmatch(r"\d+(?:\.0+)?", txt):
        return None
    return int(float(txt))


def district_key(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    txt = str(value).strip()
    if re.fullmatch(r"\d{1,2}(?:\.0+)?", txt):
        return f"{int(float(txt)):02d}"
    return None


def normalize_house(frame: pd.DataFrame, year: int, source_file: str, source_sheet: str, excluded_states: frozenset[str] = DEFAULT_EXCLUDE_STATES, writein_policy: str = 'attribute') -> tuple[pd.DataFrame, pd.DataFrame]:
    if writein_policy not in ("attribute", "ignore"):
        raise ValueError("writein_policy must be attribute or ignore")
    # Year-specific workbooks are human-readable reports, not clean candidate tables.
    source = frame.copy()
    # Verified year-specific aliases (FEC House workbooks for 2016/2018).
    aliases = {"D": "DISTRICT", "FEC ID#": "FEC ID"}
    source.columns = [aliases.get(str(name).strip().upper(), str(name).strip().upper()) for name in source.columns]
    missing = sorted(set(REQUIRED) - set(source.columns))
    if missing:
        raise ValueError(f"Expected House columns missing: {missing}")
    source["_state"] = source["STATE ABBREVIATION"].astype("string").str.strip().str.upper()
    source["_district"] = source["DISTRICT"].map(district_key)
    # Ignore title rows and notes; the district's sub-total rows remain.
    valid = source["_state"].str.fullmatch(r"[A-Z]{2}").fillna(False) & source["_district"].notna()
    source = source[valid].copy()
    source["_party"] = source["PARTY"].astype("string").str.strip().str.upper()
    source["_label"] = source["TOTAL VOTES"].astype("string").str.strip().str.lower()
    source["_id"] = source["FEC ID"].astype("string").str.strip().str.upper()
    source["_candidate"] = source["_id"].str.fullmatch(r"H[A-Z0-9]+", na=False)

    included: list[dict] = []
    excluded: list[dict] = []
    for (state, district), group in source.groupby(["_state", "_district"], sort=True):
        reason = None
        if state in excluded_states:
            reason = "needs-state-election-rule-review"
        if reason is None:
            unresolved = group[
                group["_party"].isin(["R", "D"])
                & ~group["_candidate"]
                & ~group["_label"].isin(["party votes:", "district votes:", "total votes:"])
            ]
            if not unresolved.empty:
                reason = "unclassified-party-row"
        if reason is None:
            specials = [c for c in group.columns if c.startswith("GE RUNOFF ELECTION VOTES") or c.startswith("1ST ROUND RCV VOTES") or c.startswith("2ND ROUND RCV VOTES") or c.startswith("3RD ROUND RCV VOTES")]
            if any(group[c].map(numeric_vote).fillna(0).gt(0).any() for c in specials):
                reason = "runoff-or-ranked-choice"
        votes = {}
        if reason is None:
            for party in ["R", "D"]:
                candidates = group[(group["_candidate"]) & (group["_party"] == party)]
                if candidates.empty:
                    reason = "missing-party-candidates"
                    break
                raw_primaries = candidates["PRIMARY VOTES"].astype("string").str.strip().str.lower()
                if raw_primaries.eq("unopposed").any():
                    reason = "unopposed-primary"
                    break
                party_totals = group[(group["_label"] == "party votes:") & (group["_party"] == party)]
                if len(party_totals) > 1:
                    reason = "duplicate-party-subtotals"
                    break
                known_primary = [numeric_vote(v) for v in candidates["PRIMARY VOTES"]]
                known_primary_sum = sum(v for v in known_primary if v is not None)
                # FEC denotes party-affiliated primary write-ins as W(R)/W(D).
                # Their votes enter the corresponding Party Votes subtotal,
                # but these are NOT votes for a named R/D candidate.
                affiliated = group[group["_party"].eq(f"W({party})")] if writein_policy == "attribute" else group.iloc[:0]
                affiliated_values = [numeric_vote(v) for v in affiliated["PRIMARY VOTES"]]
                if any(pd.notna(v) and n is None for v,n in zip(affiliated["PRIMARY VOTES"],affiliated_values)):
                    reason = "ambiguous-affiliated-writein"
                    break
                affiliated_sum = sum(v for v in affiliated_values if v is not None)
                if len(party_totals) == 1:
                    reported_primary = numeric_vote(party_totals.iloc[0]["PRIMARY VOTES"])
                    if reported_primary is None or reported_primary != known_primary_sum + affiliated_sum:
                        reason = "primary-subtotal-mismatch"
                        break
                    primary_total = reported_primary
                else:
                    # Never infer a party total when FEC has affiliated write-ins
                    # but no source subtotal to reconcile against.
                    if affiliated_sum:
                        reason = "missing-primary-party-subtotal"
                        break
                    primary_total = known_primary_sum
                general_values = [numeric_vote(v) for v in candidates["GENERAL VOTES"]]
                general_total = sum(v for v in general_values if v is not None)
                if primary_total == 0 or general_total == 0:
                    reason = "missing-or-zero-two-party-votes"
                    break
                if any(pd.notna(v) and numeric_vote(v) is None for v in candidates["GENERAL VOTES"]):
                    reason = "invalid-general-vote"
                    break
                votes[party] = (primary_total, general_total)
        if reason:
            excluded.append({"year": year, "state": state, "district": district, "reason": reason})
        else:
            included.append({
                "year": year, "state": state, "chamber": "House", "district": district,
                "primary_rep_votes": votes["R"][0], "primary_dem_votes": votes["D"][0],
                "general_rep_votes": votes["R"][1], "general_dem_votes": votes["D"][1],
                "source_file": source_file, "source_sheet": source_sheet,
                "election_id": f"{year}-House-{state}-{district}",
            })
    return pd.DataFrame(included, columns=STANDARD_COLUMNS), pd.DataFrame(excluded, columns=["year", "state", "district", "reason"])



def exclude_nonstandard_winners(normal: pd.DataFrame, audit: pd.DataFrame, year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Exclude officially unconfirmed/RCV-inconsistent general results.

    The rules inspect official *outcome labels* only for dataset eligibility,
    never as a feature in a model. Keep one audit record per removed district.
    """
    bad = audit[audit["status"] != "agree"]
    if bad.empty:
        return normal.copy(), pd.DataFrame(columns=["year", "state", "district", "reason"])
    existing = set(zip(normal["state"].astype(str), normal["district"].astype(str).str.zfill(2)))
    records = []
    for item in bad.itertuples():
        key=(str(item.state),str(item.district).zfill(2))
        if key not in existing:
            raise AssertionError(f"Official winner discrepancy not in normalized input: {key}")
        records.append({"year":year,"state":key[0],"district":key[1],
                        "reason":f"official-ge-{item.status}"})
    invalid = set((item["state"],item["district"]) for item in records)
    kept = normal[~normal.apply(lambda row:(str(row["state"]),str(row["district"]).zfill(2)) in invalid,axis=1)].copy()
    return kept,pd.DataFrame(records,columns=["year","state","district","reason"])

def load_house_sheet(path: Path) -> tuple[str, pd.DataFrame]:
    with pd.ExcelFile(path) as book:
        matches = [s for s in book.sheet_names if "US House Results by State".lower() in s.lower()]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one House results sheet in {path}: {matches}")
        return matches[0], pd.read_excel(book, sheet_name=matches[0], header=0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize conservatively selected House general/primary contests")
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--years", type=int, nargs="+", default=[2016, 2018, 2020, 2022])
    parser.add_argument("--writein-policy", choices=["attribute", "ignore"], default="attribute",
                        help="attribute: modern policy; ignore: legacy primary subtotal comparison, for historical sensitivity only")
    args = parser.parse_args()
    if not set(args.years).issubset({2016, 2018, 2020, 2022}):
        parser.error("This initial normalizer supports only inspected 2016/2018/2020/2022 xlsx layouts")
    outputs, audits, meta = [], [], []
    for year in args.years:
        path = args.input_dir / f"federalelections{year}.xlsx"
        sheet, df = load_house_sheet(path)
        normal, audit = normalize_house(df, year, path.name, sheet, writein_policy=args.writein_policy)
        # Official 2018 ME-02 RCV outcome and NC-09 uncertified results are
        # not ordinary two-party winner labels. Validate *all* years here.
        from audit_winners import audit as audit_winners
        from source_reconcile import read_house
        official, _ = audit_winners(normal, {year: read_house(path)})
        normal, new_excluded = exclude_nonstandard_winners(normal, official, year)
        audit = pd.concat([audit, new_excluded], ignore_index=True)
        outputs.append(normal)
        audits.append(audit)
        meta.append({"year": year, "source": path.name, "sheet": sheet, "writein_policy": args.writein_policy, "included": len(normal), "excluded": len(audit), "reason_counts": audit["reason"].value_counts().to_dict()})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = pd.concat(outputs, ignore_index=True)
    exclusions = pd.concat(audits, ignore_index=True)
    if output.duplicated(["year", "state", "district"]).any():
        raise ValueError("Duplicate normalized election keys")
    output.to_csv(args.output_dir / "elections.csv", index=False)
    exclusions.to_csv(args.output_dir / "exclusions.csv", index=False)
    (args.output_dir / "normalization-summary.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    print(f"Results saved to {args.output_dir}")


if __name__ == "__main__":
    main()
