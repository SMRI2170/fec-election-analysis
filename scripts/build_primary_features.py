"""Leak-free competitive features from the FEC Primary candidate rows (#59).

The frozen cohort (``data/processed/elections.csv``) carries only the two-party
totals of each election. This script rebuilds the *candidate-level* structure of
the Primary from the official FEC workbooks and turns it into features that a
model may use **before** the General election:

* the number of candidates with a positive numeric Primary vote,
* the sum of those candidate votes,
* the concentration index ``HHI = sum((v_i / sum v)^2)``,
* the top candidate's share of the party total,
* ``log1p`` of the party total.

Every feature is derived from **Primary-side columns only**. The General vote
columns are never read, so a feature cannot contain information about the
outcome it is supposed to predict. ``tests/test_primary_features.py`` verifies
this by mutating the General columns and asserting that the features do not
move.

Deliberate restrictions:

* Party-attributed write-ins (``W(R)`` / ``W(D)``) are **not** candidates. Their
  votes are reported in a separate column, together with the gap between the
  FEC party subtotal and the candidate total.
* Missing, unopposed, convention-endorsed, zero and fusion rows are recorded
  with a cause code and a missing flag. Nothing is filled with zero and nothing
  is taken from the General election.
* The output has exactly one row per cohort contest (916 rows). Contests that
  the cohort excluded are dropped and counted, never silently merged.

Availability caveat: the FEC workbooks are published **after** the election and
the Primary candidate rows are reconstructed from that final publication. The
features are therefore a retrospective reconstruction of what the Primary
looked like, not a record of what was known before the General election.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from source_reconcile import read_house  # noqa: E402

#: The two parties the study models.
MAJOR = ("R", "D")
#: Columns that carry information about the Primary side of the workbook.
#: Everything else is dropped before a feature is computed, so that a General
#: column cannot reach a feature even by accident.
PRIMARY_SIDE_COLUMNS = (
    "_state",
    "_district",
    "_candidate",
    "FEC ID",
    "CANDIDATE NAME",
    "PARTY",
    "PRIMARY VOTES",
    "TOTAL VOTES",
    "FOOTNOTES",
)
#: Markers used by the FEC workbooks for non-numeric vote cells.
NON_NUMERIC_MARKERS = {
    "unopposed": "unopposed-primary",
    "*": "convention-endorsed-no-primary",
    "#": "footnote-no-primary",
    "**": "footnote-no-primary",
}
#: Status priority. The first matching code becomes the cause code of the row.
#: An ambiguous fusion code comes first: the party *does* have candidate rows,
#: they simply cannot be attributed, which is a different fact from having no
#: candidate row at all.
STATUS_PRIORITY = (
    "ambiguous-fusion-party-code",
    "no-candidate-rows",
    "unopposed-primary",
    "non-numeric-primary-votes",
    "zero-primary-total",
    "missing-party-subtotal",
    "subtotal-mismatch",
    "ok",
)


def major_tokens(label: object) -> set[str]:
    """Return the major parties (``R`` / ``D``) named in a party code.

    ``D/IP`` names the Democratic party plus a minor party, so the candidate
    belongs to ``D`` only. ``D/R`` names both major parties, which is
    ambiguous and must not be attributed automatically.
    """
    if pd.isna(label):
        return set()
    raw = str(label).strip().upper()
    if not raw:
        return set()
    return set(re.split(r"[/+, ]+", raw)) & set(MAJOR)


def vote_cell(value: object) -> int | None:
    """Return the integer vote count of a cell, or ``None`` when it is not one.

    ``None`` covers empty cells, the text ``Unopposed`` and the footnote
    markers ``*`` / ``#``. A missing number is never turned into a zero.
    """
    if pd.isna(value):
        return None
    text = str(value).strip().replace(",", "")
    if not re.fullmatch(r"\d+(?:\.0+)?", text):
        return None
    return int(float(text))


def marker_of(value: object) -> str:
    """Return the literal marker text of a non-numeric vote cell."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def primary_side(frame: pd.DataFrame) -> pd.DataFrame:
    """Reduce a workbook sheet to the Primary-side columns.

    The General vote columns are dropped here, once, so that no later step can
    read them.
    """
    keep = [column for column in PRIMARY_SIDE_COLUMNS if column in frame.columns]
    return frame[keep].copy()


def candidate_rows(group: pd.DataFrame) -> pd.DataFrame:
    """Return the candidate rows of a district with their party attribution.

    A candidate may appear on more than one row when the FEC lists additional
    party affiliations (for example ``R`` and ``IP``). The rows are kept so
    that the duplication is visible, and the candidate is identified by its FEC
    ID.
    """
    columns = ["_fec_id", "_tokens", "_votes", "_marker"]
    if "FEC ID" not in group.columns:
        return pd.DataFrame(columns=list(group.columns) + columns)
    rows = group[group["_candidate"]].copy()
    # The helper columns are added even when there is no candidate row, so
    # that every downstream step sees the same shape.
    rows["_fec_id"] = rows["FEC ID"].astype("string").str.strip().str.upper()
    rows["_tokens"] = rows["PARTY"].map(major_tokens)
    rows["_votes"] = rows["PRIMARY VOTES"].map(vote_cell)
    rows["_marker"] = rows["PRIMARY VOTES"].map(marker_of)
    return rows


def _one_vote_per_candidate(rows: pd.DataFrame) -> pd.DataFrame:
    """Keep one row per candidate and per vote value.

    A duplicated candidate row may repeat the same vote count (the same
    candidate listed under two party codes). Keeping the unique pairs makes
    the candidate count and the vote sum independent of how many rows the
    workbook happens to use.
    """
    if rows.empty:
        return rows
    return rows.drop_duplicates(subset=["_fec_id", "_votes"], keep="first")


def party_features(group: pd.DataFrame, party: str) -> dict:
    """Compute the competitive features of one party in one district.

    ``group`` is the whole district block of the workbook sheet: the candidate
    rows *and* the ``Party Votes:`` subtotal rows, which carry no FEC ID and
    would therefore be lost if only the candidate rows were passed in.
    """
    rows = candidate_rows(group)
    # ``.loc`` with a boolean mask keeps the columns even when the mask is
    # empty for every row; ``df[[]]`` would select zero columns instead.
    attributed = rows.loc[[party in tokens for tokens in rows["_tokens"]]]
    ambiguous = attributed.loc[[len(tokens) > 1 for tokens in attributed["_tokens"]]]
    dedicated = attributed.loc[[len(tokens) == 1 for tokens in attributed["_tokens"]]]

    # One vote value per candidate: the count is a count of candidates.
    unique = _one_vote_per_candidate(dedicated)
    positive = unique[unique["_votes"].notna() & (unique["_votes"] > 0)]
    values = [int(v) for v in positive["_votes"]]
    total = sum(values)

    candidates = len(values)
    hhi = sum((v / total) ** 2 for v in values) if total > 0 else None
    top_share = (max(values) / total) if total > 0 and values else None
    log1p = math.log1p(total) if total > 0 else None

    markers = sorted({m for m in dedicated["_marker"] if m and not re.fullmatch(r"\d+(\.0+)?", m.replace(",", ""))})
    unopposed = any(m.lower() == "unopposed" for m in markers)

    # Party-attributed write-ins are reported separately and never counted as
    # candidates.
    writeins = group[
        group["PARTY"].astype("string").str.strip().str.upper().eq(f"W({party})")
    ]
    writein_votes = sum(
        int(vote_cell(value))
        for value in writeins["PRIMARY VOTES"]
        if vote_cell(value) is not None and vote_cell(value) > 0
    )

    subtotal_rows = group_party_subtotal(group, party)
    subtotal = vote_cell(subtotal_rows.iloc[0]["PRIMARY VOTES"]) if len(subtotal_rows) == 1 else None
    gap = None if subtotal is None else subtotal - (total + writein_votes)

    flags = {
        "no-candidate-rows": len(dedicated) == 0,
        "ambiguous-fusion-party-code": len(ambiguous) > 0,
        "unopposed-primary": unopposed,
        "non-numeric-primary-votes": bool(markers) and not unopposed,
        "zero-primary-total": len(dedicated) > 0 and total == 0,
        "missing-party-subtotal": subtotal is None,
        "subtotal-mismatch": gap is not None and gap != 0,
    }
    # The cause code is the first deviation in the documented priority order.
    # ``ok`` is the default when no deviation applies.
    status = next(
        (code for code in STATUS_PRIORITY if code != "ok" and flags[code]), "ok"
    )
    usable = status in ("missing-party-subtotal", "subtotal-mismatch", "ok")

    labels = attributed["PARTY"].astype("string").str.strip().str.upper()
    fusion_rows = int(labels.str.contains(r"[/+]", regex=True).sum())
    star_rows = int(labels.str.endswith("*").sum())

    return {
        "candidates": candidates,
        "candidate_votes": total,
        "hhi": hhi,
        "top_share": top_share,
        "log1p_votes": log1p,
        "writein_votes": writein_votes,
        "party_subtotal": subtotal,
        "subtotal_gap": gap,
        "status": status,
        "missing": 0 if status == "ok" else 1,
        "features_usable": 1 if usable else 0,
        "marker": ";".join(markers),
        "fusion_rows": fusion_rows,
        "ambiguous_rows": int(len(ambiguous)),
        "star_label_rows": star_rows,
    }


def group_party_subtotal(group: pd.DataFrame, party: str) -> pd.DataFrame:
    """Return the FEC ``Party Votes:`` rows of one party."""
    marker = group["TOTAL VOTES"].astype("string").str.strip().str.lower()
    return group[
        marker.eq("party votes:")
        & group["PARTY"].astype("string").str.strip().str.upper().eq(party)
    ]


def contest_features(group: pd.DataFrame) -> dict:
    """Compute every feature of one district from its Primary-side rows."""
    result: dict = {}
    for party in MAJOR:
        for key, value in party_features(group, party).items():
            result[f"{party.lower()}_{key}"] = value
    result["fusion_rows_total"] = result["r_fusion_rows"] + result["d_fusion_rows"]
    result["star_label_rows_total"] = result["r_star_label_rows"] + result["d_star_label_rows"]
    result["features_available"] = int(
        result["r_features_usable"] == 1 and result["d_features_usable"] == 1
    )
    return result


def build_features(
    raw_dir: Path,
    cohort: pd.DataFrame,
    years: list[int],
    excluded: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Build the feature table for every contest of the cohort.

    When ``excluded`` is given, the same features are also computed for the
    districts the cohort dropped. That diagnostic never changes the cohort; it
    only records *why* a dropped district does not reconcile, which is the
    evidence used by the open subtotal audit.
    """
    keys = cohort[["election_id", "year", "state", "district"]].copy()
    keys["district"] = keys["district"].astype("string").str.strip().str.zfill(2)
    wanted = set(keys["election_id"])
    excluded_wanted: dict[str, str] = {}
    if excluded is not None and not excluded.empty:
        for record in excluded.itertuples(index=False):
            district = str(record.district).zfill(2)
            election_id = f"{int(record.year)}-House-{record.state}-{district}"
            excluded_wanted[election_id] = str(record.reason)

    found: dict[str, dict] = {}
    raw_contests = 0
    for year in years:
        path = raw_dir / f"federalelections{year}.xlsx"
        sheet, sheet_frame = read_house(path)
        reduced = primary_side(sheet_frame)
        for (state, district), group in reduced.groupby(["_state", "_district"], sort=True):
            raw_contests += 1
            election_id = f"{year}-House-{state}-{district}"
            if election_id not in wanted and election_id not in excluded_wanted:
                continue
            found[election_id] = contest_features(group)

    rows = []
    missing_rows = []
    for record in keys.itertuples(index=False):
        election_id = record.election_id
        if election_id not in found:
            missing_rows.append(election_id)
            continue
        entry = {"election_id": election_id, "year": int(record.year),
                 "state": record.state, "district": record.district}
        entry.update(found[election_id])
        rows.append(entry)
    frame = pd.DataFrame(rows)
    if missing_rows:
        raise ValueError(
            "cohort contests without raw workbook rows: "
            f"{len(missing_rows)} (first: {missing_rows[:5]})"
        )
    if len(frame) != len(keys) or frame["election_id"].duplicated().any():
        raise ValueError("feature table is not a 1:1 join of the cohort")

    diagnostic_rows = []
    for election_id, reason in sorted(excluded_wanted.items()):
        if election_id not in found:
            continue
        entry = {"election_id": election_id, "exclusion_reason": reason}
        entry.update(found[election_id])
        diagnostic_rows.append(entry)
    diagnostic = pd.DataFrame(diagnostic_rows)

    meta = {
        "years": years,
        "cohort_rows": int(len(keys)),
        "feature_rows": int(len(frame)),
        "raw_contest_groups": int(raw_contests),
        "raw_contests_not_in_cohort": int(raw_contests - len(frame)),
        "source_sheets": {str(year): f"federalelections{year}.xlsx" for year in years},
        "primary_side_columns": list(PRIMARY_SIDE_COLUMNS),
        "general_columns_read": False,
        "features_available_rows": int(frame["features_available"].sum()),
        "status_counts": {
            party: frame[f"{party}_status"].value_counts().to_dict() for party in ("r", "d")
        },
        "excluded_diagnostic_rows": int(len(diagnostic)),
    }
    return frame, diagnostic, meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--cohort", type=Path, default=Path("data/processed/elections.csv")
    )
    parser.add_argument(
        "--exclusions",
        type=Path,
        default=Path("data/processed/exclusions.csv"),
        help="optional exclusion ledger; used for the diagnostic only",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/primary_features")
    )
    parser.add_argument("--years", type=int, nargs="+", default=[2016, 2018, 2020, 2022])
    args = parser.parse_args()

    cohort = pd.read_csv(args.cohort, dtype={"state": str, "district": str})
    excluded = None
    if args.exclusions.exists():
        excluded = pd.read_csv(args.exclusions, dtype={"state": str, "district": str})
    frame, diagnostic, meta = build_features(args.input_dir, cohort, args.years, excluded)

    expected = {2016: 200, 2018: 241, 2020: 237, 2022: 238}
    counts = frame.groupby("year").size().to_dict()
    for year, size in expected.items():
        if int(counts.get(year, 0)) != size:
            raise ValueError(f"cohort size for {year} changed: {counts.get(year)} != {size}")
    if int(frame["election_id"].nunique()) != len(frame):
        raise ValueError("duplicate election ids in the feature table")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output_dir / "primary_features.csv", index=False)
    if not diagnostic.empty:
        diagnostic.to_csv(args.output_dir / "excluded_district_diagnostic.csv", index=False)
    summary = {
        **meta,
        "per_year": {
            str(year): {
                "rows": int(len(part)),
                "features_available": int(part["features_available"].sum()),
                "r_status": part["r_status"].value_counts().to_dict(),
                "d_status": part["d_status"].value_counts().to_dict(),
                "r_subtotal_gap_nonzero": int((part["r_subtotal_gap"].fillna(0) != 0).sum()),
                "d_subtotal_gap_nonzero": int((part["d_subtotal_gap"].fillna(0) != 0).sum()),
            }
            for year, part in frame.groupby("year")
        },
        "excluded_diagnostic": (
            {
                "rows": int(len(diagnostic)),
                "rows_with_both_subtotals": int(
                    (
                        diagnostic["r_party_subtotal"].notna()
                        & diagnostic["d_party_subtotal"].notna()
                    ).sum()
                ),
                "both_parties_reconcile": int(
                    (
                        diagnostic["r_party_subtotal"].notna()
                        & diagnostic["d_party_subtotal"].notna()
                        & (diagnostic["r_subtotal_gap"].fillna(0) == 0)
                        & (diagnostic["d_subtotal_gap"].fillna(0) == 0)
                    ).sum()
                ),
                "by_reason": diagnostic["exclusion_reason"].value_counts().to_dict(),
                "rows_with_nonzero_gap": diagnostic.loc[
                    (diagnostic["r_subtotal_gap"].fillna(0) != 0)
                    | (diagnostic["d_subtotal_gap"].fillna(0) != 0),
                    ["election_id", "exclusion_reason", "r_subtotal_gap", "d_subtotal_gap"],
                ].to_dict(orient="records"),
                "rows_with_missing_subtotal": diagnostic.loc[
                    diagnostic["r_party_subtotal"].isna()
                    | diagnostic["d_party_subtotal"].isna(),
                    ["election_id", "exclusion_reason", "r_status", "d_status"],
                ].to_dict(orient="records"),
            }
            if not diagnostic.empty
            else {}
        ),
    }
    (args.output_dir / "primary_features_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary["per_year"], ensure_ascii=False, indent=2))
    print(json.dumps(summary["excluded_diagnostic"], ensure_ascii=False, indent=2))
    print("Saved:", args.output_dir / "primary_features.csv")
    print("Saved:", args.output_dir / "excluded_district_diagnostic.csv")
    print("Saved:", args.output_dir / "primary_features_summary.json")


if __name__ == "__main__":
    main()
