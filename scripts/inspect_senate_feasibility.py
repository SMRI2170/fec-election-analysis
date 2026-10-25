"""Measure whether a Senate comparison of the Primary/General relation is feasible (#66).

The assignment presents the state, the chamber and the year as examples of
analysis dimensions. This script does **not** build a Senate study. It reads
the official FEC workbooks and measures what a Senate study would have to work
with, so that the decision to keep the study on the House can be justified with
numbers instead of an opinion.

The measurements are:

* how many Senate races each year carries and how many of them have a Primary
  vote for both major parties,
* how often the candidate rows reconcile with the FEC ``Party Votes:`` subtotal
  under the same arithmetic rule the House normalizer uses,
* how many races are unopposed in the Primary,
* which labels identify a race and which total rows mark its end,
* how many two-party General votes a Senate race carries compared with a House
  district.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

#: The years the study covers.
YEARS = (2016, 2018, 2020, 2022)


def vote(value: object) -> int | None:
    """Return the integer vote count of a cell, or ``None`` when it is not one."""
    if pd.isna(value):
        return None
    text = str(value).strip().replace(",", "")
    if not re.fullmatch(r"\d+(?:\.0+)?", text):
        return None
    return int(float(text))


def read_chamber_sheet(path: Path, chamber: str) -> pd.DataFrame:
    """Read the results-by-state sheet of one chamber.

    The Senate sheet uses different labels from the House sheet: the
    ``DISTRICT`` column holds a term label instead of a district number, and
    the race total is written as ``Total State Votes:``. Both are kept as
    published so that the feasibility report can show them.
    """
    with pd.ExcelFile(path) as book:
        if chamber == "House":
            names = [name for name in book.sheet_names if "US House Results by State" in name]
        else:
            names = [name for name in book.sheet_names if "Senate Results by State" in name]
        if len(names) != 1:
            raise ValueError(f"{path.name}: expected one {chamber} sheet, got {names}")
        frame = pd.read_excel(book, sheet_name=names[0])
    aliases = {"D": "DISTRICT", "FEC ID#": "FEC ID"}
    frame.columns = [
        aliases.get(str(column).strip().upper(), str(column).strip().upper())
        for column in frame.columns
    ]
    frame["_state"] = frame["STATE ABBREVIATION"].astype("string").str.strip().str.upper()
    frame["_term_raw"] = frame["DISTRICT"].astype("string")
    frame["_term"] = frame["_term_raw"].str.strip()
    # The House sheet uses the same column for the district number.
    frame["_district"] = frame["_term"]
    frame["_party"] = frame["PARTY"].astype("string").str.strip().str.upper()
    frame["_marker"] = frame["TOTAL VOTES"].astype("string").str.strip().str.lower()
    prefix = "H" if chamber == "House" else "S"
    frame["_candidate"] = (
        frame["FEC ID"].astype("string").str.strip().str.upper().str.fullmatch(
            rf"{prefix}[A-Z0-9]+", na=False
        )
    )
    return frame[frame["_state"].str.fullmatch(r"[A-Z]{2}", na=False)].copy()


def _primary_sum(group: pd.DataFrame, party: str, include_writeins: bool = True) -> int:
    """Sum of the positive Primary votes of one party."""
    candidates = group[(group["_candidate"]) & (group["_party"].eq(party))]
    total = sum(
        int(vote(value))
        for value in candidates["PRIMARY VOTES"]
        if vote(value) is not None and vote(value) > 0
    )
    if include_writeins:
        writeins = group[group["_party"].eq(f"W({party})")]
        total += sum(
            int(vote(value))
            for value in writeins["PRIMARY VOTES"]
            if vote(value) is not None and vote(value) > 0
        )
    return total


def inspect_senate(frame: pd.DataFrame) -> dict:
    """Measure one year of Senate races."""
    races = 0
    both_party_primary = 0
    any_party_primary = 0
    reconciles = 0
    unopposed = 0
    two_party_general_totals: list[int] = []
    for _state, group in frame.groupby("_state"):
        races += 1
        candidates = group[group["_candidate"]]
        primary_re = candidates[candidates["_party"].eq("R")]["PRIMARY VOTES"].map(vote)
        primary_dem = candidates[candidates["_party"].eq("D")]["PRIMARY VOTES"].map(vote)
        if primary_re.notna().any() and primary_dem.notna().any():
            both_party_primary += 1
        if primary_re.notna().any() or primary_dem.notna().any():
            any_party_primary += 1
        matches = True
        for party in ("R", "D"):
            subtotal = group[
                group["_marker"].eq("party votes:") & group["_party"].eq(party)
            ]
            if len(subtotal) == 1:
                reported = vote(subtotal.iloc[0]["PRIMARY VOTES"])
                if reported is not None and reported != _primary_sum(group, party):
                    matches = False
        if matches:
            reconciles += 1
        raw = candidates["PRIMARY VOTES"].astype("string").str.strip().str.lower()
        if raw.eq("unopposed").any():
            unopposed += 1
        general_re = sum(
            int(vote(value))
            for value in candidates[candidates["_party"].eq("R")]["GENERAL VOTES"]
            if vote(value) is not None
        )
        general_dem = sum(
            int(vote(value))
            for value in candidates[candidates["_party"].eq("D")]["GENERAL VOTES"]
            if vote(value) is not None
        )
        if general_re + general_dem > 0:
            two_party_general_totals.append(general_re + general_dem)
    return {
        "races": races,
        "states": int(frame["_state"].nunique()),
        "both_party_primary": both_party_primary,
        "any_party_primary": any_party_primary,
        "subtotal_reconciles": reconciles,
        "unopposed_primary": unopposed,
        "mean_two_party_general_total": (
            float(sum(two_party_general_totals) / len(two_party_general_totals))
            if two_party_general_totals
            else None
        ),
        "term_labels": sorted(
            {value for value in frame["_term"].dropna().unique() if value}
        ),
        # The labels as published: the case and a trailing space differ
        # between the years, so a key filter has to normalize them.
        "term_labels_raw": sorted(
            {value for value in frame["_term_raw"].dropna().unique() if value}
        ),
        "total_row_markers": sorted(
            {value for value in frame["_marker"].dropna().unique() if value != "party votes:"}
        ),
        "unexpired_term_states": sorted(
            frame.loc[
                frame["_term"].astype("string").str.upper().str.contains("UNEXPIRED"), "_state"
            ].unique()
        ),
    }


def inspect_house_scale(frame: pd.DataFrame) -> dict:
    """Measure the two-party General total of the House districts."""
    totals: list[int] = []
    for _key, group in frame.groupby(["_state", "_district"]):
        candidates = group[group["_candidate"]]
        general_re = sum(
            int(vote(value))
            for value in candidates[candidates["_party"].eq("R")]["GENERAL VOTES"]
            if vote(value) is not None
        )
        general_dem = sum(
            int(vote(value))
            for value in candidates[candidates["_party"].eq("D")]["GENERAL VOTES"]
            if vote(value) is not None
        )
        if general_re + general_dem > 0:
            totals.append(general_re + general_dem)
    return {
        "districts": len(totals),
        "mean_two_party_general_total": float(sum(totals) / len(totals)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/chamber_feasibility")
    )
    parser.add_argument("--years", type=int, nargs="+", default=list(YEARS))
    args = parser.parse_args()

    per_year = {}
    house_scale = {}
    for year in args.years:
        path = args.input_dir / f"federalelections{year}.xlsx"
        senate = read_chamber_sheet(path, "Senate")
        house = read_chamber_sheet(path, "House")
        per_year[str(year)] = inspect_senate(senate)
        house_scale[str(year)] = inspect_house_scale(house)

    senate_races = sum(entry["races"] for entry in per_year.values())
    senate_two_party = sum(entry["both_party_primary"] for entry in per_year.values())
    summary = {
        "analysis": "chamber-feasibility-v1",
        "study": "official FEC 2016/2018/2020/2022 workbooks",
        "purpose": "measure what a Senate study would need, not run one",
        "per_year": per_year,
        "house_scale": house_scale,
        "senate_races_total": senate_races,
        "senate_two_party_primary_total": senate_two_party,
        "house_districts_total": sum(
            entry["districts"] for entry in house_scale.values()
        ),
        "mean_scale_ratio_senate_over_house": round(
            sum(entry["mean_two_party_general_total"] for entry in per_year.values())
            / len(per_year)
            / (sum(entry["mean_two_party_general_total"] for entry in house_scale.values())
               / len(house_scale)),
            3,
        ),
        "decision": "keep the study on the House",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "chamber_feasibility.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Saved:", args.output_dir / "chamber_feasibility.json")


if __name__ == "__main__":
    main()
