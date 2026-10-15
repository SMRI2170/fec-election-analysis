"""Validation and feature engineering for standardized FEC records.

This is NOT a parser for official FEC spreadsheets.
"""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = (
    "year", "state", "chamber", "district",
    "primary_rep_votes", "primary_dem_votes",
    "general_rep_votes", "general_dem_votes",
)
VOTE_COLUMNS = REQUIRED_COLUMNS[4:]


def prepare_elections(df: pd.DataFrame) -> pd.DataFrame:
    """Validate observations and compute TWO-PARTY vote-share leads, not certified winners."""
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if df.empty:
        raise ValueError("Dataset is empty")

    result = df.copy()
    try:
        result["year"] = pd.to_numeric(result["year"], errors="raise")
        if result["year"].isna().any() or (result["year"] % 1 != 0).any():
            raise ValueError("year must be an integer")
        result["year"] = result["year"].astype(int)
        for col in VOTE_COLUMNS:
            result[col] = pd.to_numeric(result[col], errors="raise")
            if result[col].isna().any() or (result[col] < 0).any() or (result[col] % 1 != 0).any():
                raise ValueError(f"{col} must be a nonnegative integer")
            result[col] = result[col].astype("int64")
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid normalized data: {e}") from e

    for col in ("state", "chamber", "district"):
        if result[col].isna().any() or result[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"{col} must be nonempty")
    if not result["chamber"].isin(["House", "Senate"]).all():
        raise ValueError("chamber must be House or Senate")

    keys = ["year", "state", "chamber", "district"]
    if "election_id" in result.columns:
        keys.append("election_id")
    if result.duplicated(subset=keys).any():
        raise ValueError(f"Duplicate election keys found: {keys}")

    p_total = result["primary_rep_votes"] + result["primary_dem_votes"]
    g_total = result["general_rep_votes"] + result["general_dem_votes"]
    if (p_total <= 0).any() or (g_total <= 0).any():
        raise ValueError("Both primary and general two-party vote totals must be positive")
    result["primary_rep_share"] = result["primary_rep_votes"] / p_total
    result["general_rep_share"] = result["general_rep_votes"] / g_total
    # Backwards-compatible field name. It is *not* necessarily the certified winner.
    result["general_two_party_rep_lead"] = (result["general_rep_share"] > 0.5).astype(int)
    result["general_rep_win"] = result["general_two_party_rep_lead"]
    result["general_tie"] = result["general_rep_share"] == 0.5
    return result
