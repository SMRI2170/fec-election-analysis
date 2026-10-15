import pandas as pd
import pytest

from fec_analysis.core import prepare_elections


def sample():
    return pd.DataFrame([{
        "year": 2020, "state": "AA", "chamber": "House", "district": "1",
        "primary_rep_votes": 60, "primary_dem_votes": 40,
        "general_rep_votes": 55, "general_dem_votes": 45,
    }])


def test_share_and_winner():
    result = prepare_elections(sample())
    assert result.loc[0, "primary_rep_share"] == pytest.approx(0.6)
    assert result.loc[0, "general_rep_share"] == pytest.approx(0.55)
    assert result.loc[0, "general_rep_win"] == 1


def test_duplicate_keys_rejected():
    row = sample()
    with pytest.raises(ValueError, match="Duplicate"):
        prepare_elections(pd.concat([row, row], ignore_index=True))


def test_negative_votes_rejected():
    df = sample()
    df.loc[0, "primary_dem_votes"] = -1
    with pytest.raises(ValueError, match="nonnegative"):
        prepare_elections(df)


def test_zero_totals_rejected():
    df = sample()
    df.loc[0, ["primary_rep_votes", "primary_dem_votes"]] = 0
    with pytest.raises(ValueError, match="positive"):
        prepare_elections(df)
