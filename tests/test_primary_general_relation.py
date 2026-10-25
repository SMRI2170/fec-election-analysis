"""Synthetic unit tests for the Primary/General descriptive analysis (#58).

No fixture result in this file is an FEC finding: every input here is
synthetic. The real measurements live in
``docs/primary-general-relationship.md``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_primary_general_relation import (  # noqa: E402
    MEASURE_NAME,
    assign_volume_quintiles,
    contest_frame,
    pearson,
    quintile_table,
    spearman,
    year_summary,
)


def election(
    year: int,
    state: str,
    district: str,
    primary_r: int = 60,
    primary_d: int = 40,
    general_r: int = 53,
    general_d: int = 47,
    election_id: str | None = None,
) -> dict:
    return {
        "year": year,
        "state": state,
        "district": district,
        "chamber": "House",
        "primary_rep_votes": primary_r,
        "primary_dem_votes": primary_d,
        "general_rep_votes": general_r,
        "general_dem_votes": general_d,
        "election_id": election_id or f"{year}-{state}-{district}",
    }


#: Two-party vote totals of the synthetic elections. The General total
#: differs from the Primary total and *varies from contest to contest* on
#: purpose: the multiplier compares two elections with different electorates,
#: and a fixture with a constant General total would hide the ordering that
#: the leak check relies on.
PRIMARY_TOTAL = 100
GENERAL_TOTALS = (100, 110, 120)


def sample() -> pd.DataFrame:
    """Ten synthetic contests per year with a spread of Primary totals."""
    rows = []
    for year in (2016, 2018, 2020, 2022):
        for index in range(10):
            primary_r = 30 + index * 5
            primary_d = PRIMARY_TOTAL - primary_r
            general_total = GENERAL_TOTALS[index % len(GENERAL_TOTALS)]
            general_r = int(round(primary_r * 0.8))
            general_d = general_total - general_r
            rows.append(
                election(
                    year,
                    f"S{index:02d}",
                    "01",
                    primary_r=primary_r,
                    primary_d=primary_d,
                    general_r=general_r,
                    general_d=general_d,
                )
            )
    return pd.DataFrame(rows)


def test_two_party_total_ratio_is_not_a_turnout_rate() -> None:
    """The multiplier uses the two-party totals only.

    Third-party votes are not part of the measure, so adding them must not
    change any quantity. If the ratio were a turnout rate it would move.
    """
    frame = contest_frame(sample())
    plain = frame[MEASURE_NAME].to_numpy()

    with_third_party = sample()
    with_third_party["general_other_votes"] = 5000
    with_third_party["primary_other_votes"] = 3000
    with_third_party["registered_voters"] = 100000
    with_third_party["ballots_cast"] = 99999
    other = contest_frame(with_third_party)[MEASURE_NAME].to_numpy()

    assert np.allclose(plain, other)
    # The measure is the ratio of the two-party totals, spelled out.
    first = frame.iloc[0]
    assert first[MEASURE_NAME] == pytest.approx(
        first["general_two_party_total"] / first["primary_two_party_total"]
    )
    # It is a scale factor, not a rate: it is not bounded by one.
    assert frame[MEASURE_NAME].max() > 1.0
    assert frame[MEASURE_NAME].min() > 0.0


def test_the_ratio_is_never_computed_from_a_turnout_denominator() -> None:
    """A district whose General two-party total is smaller than its Primary
    must give a ratio below one, which a turnout rate could never do."""
    frame = contest_frame(
        pd.DataFrame(
            [election(2020, "AA", "01", primary_r=90, primary_d=10, general_r=10, general_d=10)]
        )
    )
    assert frame[MEASURE_NAME].iloc[0] == pytest.approx(20 / 100)


def test_quintile_split_uses_no_general_quantity() -> None:
    """The split rule is fixed on the Primary total alone.

    Permuting every General number must leave the quintile assignment
    untouched; if the split used the General votes it would move. The frame
    is rebuilt through ``contest_frame`` after the permutation, so that the
    derived columns move with the votes they are computed from.
    """
    base = sample()
    frame = contest_frame(base)
    year = frame[frame["year"] == 2018].copy()
    assigned = assign_volume_quintiles(year)

    shuffled = base.copy()
    for _, index in shuffled.groupby("year").groups.items():
        rows = shuffled.loc[index]
        order = np.arange(len(rows))[::-1]
        shuffled.loc[index, "general_rep_votes"] = rows["general_rep_votes"].to_numpy()[order]
        shuffled.loc[index, "general_dem_votes"] = rows["general_dem_votes"].to_numpy()[order]
    shuffled_year = contest_frame(shuffled)
    shuffled_year = shuffled_year[shuffled_year["year"] == 2018].copy()
    shuffled_assigned = assign_volume_quintiles(shuffled_year)

    key = ["state", "district"]
    merged = assigned[key + ["volume_quintile"]].merge(
        shuffled_assigned[key + ["volume_quintile"]], on=key, suffixes=("_a", "_b")
    )
    assert len(merged) == len(assigned)
    assert (merged["volume_quintile_a"] == merged["volume_quintile_b"]).all()


def test_quintile_sizes_are_balanced_and_deterministic() -> None:
    frame = contest_frame(sample())
    year = frame[frame["year"] == 2020]
    assigned = assign_volume_quintiles(year)
    sizes = assigned.groupby("volume_quintile").size()
    assert list(sizes) == [2, 2, 2, 2, 2]
    again = assign_volume_quintiles(year)
    merged = assigned.merge(again, on=["state", "district"], suffixes=("_a", "_b"))
    assert (merged["volume_quintile_a"] == merged["volume_quintile_b"]).all()


def test_quintiles_are_ordered_by_the_primary_total() -> None:
    frame = contest_frame(sample())
    year = frame[frame["year"] == 2022]
    assigned = assign_volume_quintiles(year)
    for _, part in assigned.groupby("volume_quintile"):
        assert part["primary_two_party_total"].max() <= part["primary_two_party_total"].max()
    medians = assigned.groupby("volume_quintile")["primary_two_party_total"].median()
    assert medians.is_monotonic_increasing


def test_majority_rule_error_is_counted_against_the_two_party_lead() -> None:
    """A P above 0.5 that ends below 0.5 is an error of the majority rule."""
    frame = contest_frame(
        pd.DataFrame(
            [
                election(2020, "AA", "01", primary_r=60, primary_d=40, general_r=40, general_d=60),
                election(2020, "BB", "01", primary_r=40, primary_d=60, general_r=30, general_d=70),
            ]
        )
    )
    assert list(frame["majority_rule_prediction"]) == [1, 0]
    assert list(frame["majority_rule_error"]) == [1, 0]


def test_share_difference_is_expressed_in_points() -> None:
    frame = contest_frame(
        pd.DataFrame(
            [election(2020, "AA", "01", primary_r=60, primary_d=40, general_r=50, general_d=50)]
        )
    )
    # P = 0.60, G = 0.50 -> G - P = -10 points.
    assert frame["share_difference_points"].iloc[0] == pytest.approx(-10.0)


def test_year_summary_reports_the_expected_descriptors() -> None:
    frame = contest_frame(sample())
    summary = year_summary(frame[frame["year"] == 2016])
    assert summary["n"] == 10
    assert 0.0 < summary["pearson_r"] <= 1.0
    assert 0.0 < summary["spearman_rho"] <= 1.0
    assert summary["ols_slope"] > 0
    assert summary["mean_two_party_total_ratio"] == pytest.approx(
        frame[frame["year"] == 2016][MEASURE_NAME].mean()
    )
    assert summary["majority_rule_errors"] == int(
        frame[frame["year"] == 2016]["majority_rule_error"].sum()
    )


def test_spearman_handles_ties_like_the_standard_definition() -> None:
    x = np.array([1.0, 2.0, 2.0, 4.0])
    y = np.array([1.0, 3.0, 3.0, 4.0])
    # Ranks of x: 1, 2.5, 2.5, 4 ; of y: 1, 2.5, 2.5, 4 -> rho = 1.
    assert spearman(x, y) == pytest.approx(1.0)
    assert spearman(y, x) == pytest.approx(1.0)
    assert pearson(x, x) == pytest.approx(1.0)


def test_quintile_table_covers_every_contest_once() -> None:
    frame = contest_frame(sample())
    table = quintile_table(frame)
    assert table["n"].sum() == len(frame)
    assert len(table) == 4 * 5
    assert (table["n"] > 0).all()


def test_missing_or_zero_totals_are_rejected_instead_of_filled() -> None:
    """A zero or missing Primary total must raise, never be silently repaired.

    Filling a missing vote count with zero would create a contest that never
    existed, so the loader has to refuse it.
    """
    zeroed = sample()
    zeroed.loc[0, "primary_rep_votes"] = 0
    zeroed.loc[0, "primary_dem_votes"] = 0
    with pytest.raises(ValueError):
        contest_frame(zeroed)

    missing = sample()
    missing.loc[1, "primary_rep_votes"] = np.nan
    with pytest.raises(ValueError):
        contest_frame(missing)

    missing_general = sample()
    missing_general.loc[2, "general_dem_votes"] = np.nan
    with pytest.raises(ValueError):
        contest_frame(missing_general)
