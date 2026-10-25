"""Synthetic unit tests for the Primary feature ablation (#60).

Every fixture here is synthetic. The real measurements live in
``docs/primary-feature-ablation.md``.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_feature_ablation import (  # noqa: E402
    BASELINE_CHECKS,
    COUNTS,
    MODEL_GROUPS,
    REFERENCE_GROUP,
    TRAIN_YEARS,
    build_pipeline,
    evaluate,
    load_cohort,
    state_interval,
)

NOTE = Path(__file__).resolve().parents[1] / "docs" / "primary-feature-ablation.md"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fec_analysis.core import prepare_elections  # noqa: E402


def synthetic_cohort() -> pd.DataFrame:
    """A synthetic cohort with the sizes of the frozen one."""
    rows = []
    for year, size in COUNTS.items():
        for index in range(size):
            primary = 0.20 + 0.5 * ((index % 40) / 40)
            general = primary * 0.7 + 0.15
            state = f"S{index % 12:02d}"
            district = f"{index // 12 + 1:02d}"
            rows.append(
                {
                    "year": year,
                    "state": state,
                    "district": district,
                    "chamber": "House",
                    "election_id": f"{year}-House-{state}-{district}",
                    "primary_rep_votes": 1000 + index,
                    "primary_dem_votes": 1000 - index // 2,
                    "general_rep_votes": 1500 + index,
                    "general_dem_votes": 1500 - index // 3,
                }
            )
    return prepare_elections(pd.DataFrame(rows))


def synthetic_features(elections: pd.DataFrame, unusable: tuple[str, ...] = ()) -> pd.DataFrame:
    """A feature table with one row per contest."""
    rows = []
    for record in elections.itertuples(index=False):
        usable = record.election_id not in unusable
        rows.append(
            {
                "election_id": record.election_id,
                "r_candidates": 2 if usable else 1,
                "d_candidates": 3 if usable else 1,
                "r_hhi": 0.5 if usable else np.nan,
                "d_hhi": 0.4 if usable else np.nan,
                "r_log1p_votes": 10.0 if usable else np.nan,
                "d_log1p_votes": 10.5 if usable else np.nan,
                "r_features_usable": 1 if usable else 0,
                "d_features_usable": 1 if usable else 0,
            }
        )
    return pd.DataFrame(rows)


def test_the_model_groups_are_predeclared_and_symmetric() -> None:
    assert list(MODEL_GROUPS) == [
        "p_only",
        "p_candidates",
        "p_concentration",
        "p_log_volume",
        "p_all",
    ]
    assert REFERENCE_GROUP == "p_only"
    for name, columns in MODEL_GROUPS.items():
        assert "primary_rep_share" in columns
        for party in ("r", "d"):
            party_columns = [c for c in columns if c.startswith(f"{party}_")]
            # The Republican and the Democratic features are always used
            # together, so no group depends on a single party.
            assert len(party_columns) == len(
                [c for c in columns if c.startswith(("r_", "d_"))]
            ) / 2
            for column in party_columns:
                assert not column.startswith(f"{party}_candidates") or (
                    f"{'d' if party == 'r' else 'r'}_candidates" in columns
                )
        if name != "p_only":
            assert len(columns) > 1


def test_the_pipeline_matches_a_plain_linear_regression() -> None:
    """Scaling does not change the predictions of a linear model, so the
    P-only group stays equal to the frozen baseline."""
    rng = np.random.default_rng(3)
    x = rng.random((200, 1)) * 0.6 + 0.2
    y = 0.7 * x[:, 0] + 0.15 + rng.normal(0, 0.01, 200)
    pipeline = build_pipeline()
    pipeline.fit(x, y)
    plain = LinearRegression().fit(x, y)
    probe = np.array([[0.3], [0.55]])
    assert np.allclose(pipeline.predict(probe), plain.predict(probe))


def test_the_imputation_uses_the_training_years_only() -> None:
    frame = synthetic_cohort()
    features = synthetic_features(frame, unusable=("2016-House-S00-01",))
    joined = load_cohort(frame, features)
    train = joined[joined["year"].isin((2016,))]
    test = joined[joined["year"].eq(2018)]
    pipeline = build_pipeline()
    columns = list(MODEL_GROUPS["p_concentration"])
    pipeline.fit(train[columns], train["general_rep_share"])
    imputed = pipeline.named_steps["impute"].statistics_
    expected = train[columns].median(numeric_only=True).to_numpy()
    assert np.allclose(np.sort(imputed), np.sort(expected))


def test_the_test_year_labels_do_not_change_the_predictions() -> None:
    frame = synthetic_cohort()
    features = synthetic_features(frame)
    joined = load_cohort(frame, features)
    summary, districts, _ = evaluate(joined)
    shuffled = joined.copy()
    mask = shuffled["year"].eq(2020)
    order = np.arange(int(mask.sum()))[::-1]
    shuffled.loc[mask, "general_rep_votes"] = (
        shuffled.loc[mask, "general_rep_votes"].to_numpy()[order]
    )
    shuffled.loc[mask, "general_dem_votes"] = (
        shuffled.loc[mask, "general_dem_votes"].to_numpy()[order]
    )
    shuffled = prepare_elections(
        shuffled[["year", "state", "district", "chamber", "election_id",
                  "primary_rep_votes", "primary_dem_votes", "general_rep_votes",
                  "general_dem_votes"]]
    )
    other, _, _ = evaluate(load_cohort(shuffled, features))
    reference = summary[summary["model"].eq("p_only")].set_index("test_year")
    other_reference = other[other["model"].eq("p_only")].set_index("test_year")
    for year in reference.index:
        assert reference.loc[year, "n"] == other_reference.loc[year, "n"]


def test_every_group_is_scored_on_the_same_number_of_contests() -> None:
    frame = synthetic_cohort()
    features = synthetic_features(frame)
    summary, districts, meta = evaluate(load_cohort(frame, features))
    for year, part in summary.groupby("test_year"):
        assert part["n"].nunique() == 1
        assert int(part["n"].iloc[0]) == COUNTS[int(year)]
    for year in TRAIN_YEARS:
        entry = [row for row in meta["paired"] if row["test_year"] == year]
        assert len(entry) == len(MODEL_GROUPS) - 1
        for row in entry:
            assert row["n"] == COUNTS[year]


def test_the_unusable_features_are_masked() -> None:
    frame = synthetic_cohort()
    target = frame["election_id"].iloc[0]
    features = synthetic_features(frame, unusable=(target,))
    joined = load_cohort(frame, features)
    row = joined[joined["election_id"].eq(target)].iloc[0]
    assert pd.isna(row["r_hhi"])
    assert pd.isna(row["d_hhi"])
    assert pd.isna(row["r_candidates"])
    assert pd.notna(row["primary_rep_share"])


def test_the_training_years_are_always_earlier_than_the_test_year() -> None:
    for year, training_years in TRAIN_YEARS.items():
        assert all(training < year for training in training_years)
    assert TRAIN_YEARS[2018] == (2016,)
    assert TRAIN_YEARS[2020] == (2016, 2018)
    assert TRAIN_YEARS[2022] == (2016, 2018, 2020)


def test_the_state_interval_is_deterministic() -> None:
    delta = np.array([0.1, -0.2, 0.3, 0.0])
    states = np.array(["AA", "AA", "BB", "BB"])
    first = state_interval(delta, states, seed=11, repetitions=200)
    second = state_interval(delta, states, seed=11, repetitions=200)
    assert first == second
    with pytest.raises(ValueError):
        state_interval(delta, states[:2], seed=11, repetitions=200)


def test_the_evaluation_is_deterministic() -> None:
    frame = synthetic_cohort()
    features = synthetic_features(frame)
    joined = load_cohort(frame, features)
    first = evaluate(joined)
    second = evaluate(joined)
    pd.testing.assert_frame_equal(first[0], second[0])
    pd.testing.assert_frame_equal(first[1], second[1])


def test_the_note_records_the_frozen_baseline_of_the_reference_group() -> None:
    """The reference row of the note has to carry the frozen MAE values.

    The note is written by hand, so a transcription slip in the baseline row
    would silently contradict the frozen benchmark. The check parses the note
    instead of trusting it.
    """
    text = NOTE.read_text(encoding="utf-8")
    for year, expected in BASELINE_CHECKS.items():
        pattern = re.compile(
            r"^\| " + str(year) + r" \| `" + REFERENCE_GROUP + r"`（基準） \| "
            r"\d+ \| ([0-9.]+) \|",
            re.M,
        )
        match = pattern.search(text)
        assert match is not None, f"the reference row of {year} is missing"
        assert abs(float(match.group(1)) / 100 - expected["mae"]) <= 0.0001


def test_the_note_declares_every_predeclared_group() -> None:
    text = NOTE.read_text(encoding="utf-8")
    for name in MODEL_GROUPS:
        assert f"`{name}`" in text, f"the group {name} is not declared in the note"
    # Every group is evaluated on the same contests, so the note lists the
    # same number of rows per year as the design has groups.
    for year in TRAIN_YEARS:
        rows = re.findall(r"^\| " + str(year) + r" \| `p_\w+`", text, re.M)
        assert len(rows) >= len(MODEL_GROUPS)
