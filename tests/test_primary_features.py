"""Synthetic unit tests for the Primary candidate features (#59).

Every fixture in this file is synthetic. The real measurements live in
``docs/primary-feature-schema.md`` and are produced by reading the official FEC
workbooks.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_primary_features import (  # noqa: E402
    STATUS_PRIORITY,
    contest_features,
    major_tokens,
    primary_side,
    vote_cell,
)


def row(
    party: str,
    primary: object,
    fec_id: str | None = None,
    marker: str = "",
    general: object = None,
    district: str = "01",
) -> dict:
    """One row of a workbook sheet."""
    return {
        "_state": "AA",
        "_district": district,
        "_candidate": fec_id is not None,
        "FEC ID": fec_id,
        "CANDIDATE NAME": f"Candidate {fec_id}" if fec_id else None,
        "PARTY": party,
        "PRIMARY VOTES": primary,
        "TOTAL VOTES": marker,
        "FOOTNOTES": None,
        "GENERAL VOTES": general,
    }


def sheet(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def features(rows: list[dict]) -> dict:
    return contest_features(sheet(rows))


def test_major_tokens_separates_major_from_minor_parties() -> None:
    assert major_tokens("R") == {"R"}
    assert major_tokens("D") == {"D"}
    assert major_tokens("D/IP") == {"D"}
    assert major_tokens("R/TRP") == {"R"}
    assert major_tokens("W(D)") == set()
    assert major_tokens("W(R)") == set()
    assert major_tokens("LIB") == set()
    # A label that names both major parties cannot be attributed automatically.
    assert major_tokens("D/R") == {"D", "R"}
    # The star suffix is a footnote marker, not a party code.
    assert major_tokens("R*") == set()


def test_vote_cell_never_turns_a_marker_into_a_number() -> None:
    assert vote_cell("1,234") == 1234
    assert vote_cell("0") == 0
    assert vote_cell("Unopposed") is None
    assert vote_cell("*") is None
    assert vote_cell(None) is None
    assert vote_cell(float("nan")) is None


def test_features_are_computed_from_the_candidate_rows() -> None:
    result = features(
        [
            row("R", 60000, "H1AA01001"),
            row("R", 40000, "H1AA01002"),
            row("D", 50000, "H1AA01003"),
            row("D", 30000, "H1AA01004"),
            row("D", 80000, None, marker="party votes:"),
            row("R", 100000, None, marker="party votes:"),
        ]
    )
    assert result["r_candidates"] == 2
    assert result["r_candidate_votes"] == 100000
    assert result["r_hhi"] == pytest.approx((0.6**2 + 0.4**2))
    assert result["r_top_share"] == pytest.approx(0.6)
    assert result["r_log1p_votes"] == pytest.approx(math.log1p(100000))
    assert result["d_candidates"] == 2
    assert result["d_hhi"] == pytest.approx((0.625**2 + 0.375**2))
    assert result["r_status"] == "ok"
    assert result["d_status"] == "ok"
    assert result["features_available"] == 1


def test_general_votes_cannot_reach_a_feature() -> None:
    """The features must not move when the General column changes."""
    base = [
        row("R", 60000, "H1AA01001", general=55000),
        row("D", 50000, "H1AA01003", general=52000),
        row("D", 100000, None, marker="party votes:"),
        row("R", 60000, None, marker="party votes:"),
    ]
    changed = [dict(item) for item in base]
    for item in changed:
        item["GENERAL VOTES"] = 1 if item["GENERAL VOTES"] is None else 999999
    plain = features(base)
    other = features(changed)
    assert plain == other
    # The reduction drops the General column before anything is computed.
    assert "GENERAL VOTES" not in primary_side(sheet(base)).columns


def test_party_attributed_writeins_are_not_candidates() -> None:
    result = features(
        [
            row("R", 60000, "H1AA01001"),
            row("W(R)", 500, None),
            row("D", 50000, "H1AA01003"),
            row("D", 50500, None, marker="party votes:"),
            row("R", 60500, None, marker="party votes:"),
        ]
    )
    assert result["r_candidates"] == 1
    assert result["r_candidate_votes"] == 60000
    assert result["r_writein_votes"] == 500
    # The write-in is not part of the candidate total, and the difference to
    # the party subtotal is reported in its own column.
    assert result["r_subtotal_gap"] == 0
    assert result["r_status"] == "ok"


def test_a_candidate_listed_twice_is_counted_once() -> None:
    result = features(
        [
            row("R", 60000, "H1AA01001"),
            row("IP", None, "H1AA01001"),
            row("D", 50000, "H1AA01003"),
            row("D", 50000, None, marker="party votes:"),
            row("R", 60000, None, marker="party votes:"),
        ]
    )
    assert result["r_candidates"] == 1
    assert result["r_candidate_votes"] == 60000
    assert result["r_hhi"] == pytest.approx(1.0)


def test_fusion_code_is_attributed_to_its_major_party() -> None:
    result = features(
        [
            row("D/IP", 70000, "H1AA01001"),
            row("D", 30000, "H1AA01002"),
            row("R", 50000, "H1AA01003"),
            row("D", 100000, None, marker="party votes:"),
            row("R", 50000, None, marker="party votes:"),
        ]
    )
    assert result["d_candidates"] == 2
    assert result["d_candidate_votes"] == 100000
    assert result["d_hhi"] == pytest.approx((0.7**2 + 0.3**2))
    assert result["d_fusion_rows"] == 1
    assert result["d_status"] == "ok"


def test_ambiguous_fusion_code_is_flagged_and_not_attributed() -> None:
    result = features(
        [
            row("D/R", 70000, "H1AA01001"),
            row("R", 50000, "H1AA01003"),
            row("R", 50000, None, marker="party votes:"),
        ]
    )
    assert result["d_status"] == "ambiguous-fusion-party-code"
    assert result["d_missing"] == 1
    assert result["d_features_usable"] == 0
    assert result["d_ambiguous_rows"] == 1


def test_unopposed_primary_is_reported_and_not_filled() -> None:
    result = features(
        [
            row("R", "Unopposed", "H1AA01001"),
            row("D", 50000, "H1AA01003"),
            row("D", 50000, None, marker="party votes:"),
        ]
    )
    assert result["r_status"] == "unopposed-primary"
    assert result["r_missing"] == 1
    assert result["r_candidates"] == 0
    assert result["r_candidate_votes"] == 0
    assert result["r_marker"] == "Unopposed"


def test_non_numeric_primary_marker_is_reported() -> None:
    result = features(
        [
            row("R", "*", "H1AA01001"),
            row("R", 40000, "H1AA01002"),
            row("D", 50000, "H1AA01003"),
            row("D", 50000, None, marker="party votes:"),
            row("R", 40000, None, marker="party votes:"),
        ]
    )
    assert result["r_status"] == "non-numeric-primary-votes"
    assert result["r_missing"] == 1
    assert result["r_features_usable"] == 0
    assert result["r_candidates"] == 1


def test_zero_total_is_reported_and_not_filled() -> None:
    result = features(
        [
            row("R", 0, "H1AA01001"),
            row("D", 50000, "H1AA01003"),
            row("D", 50000, None, marker="party votes:"),
        ]
    )
    assert result["r_status"] == "zero-primary-total"
    assert result["r_candidate_votes"] == 0
    assert result["r_hhi"] is None


def test_missing_party_subtotal_is_reported_but_the_candidate_features_stay() -> None:
    result = features(
        [
            row("R", 60000, "H1AA01001"),
            row("D", 50000, "H1AA01003"),
            row("D", 50000, None, marker="party votes:"),
        ]
    )
    assert result["r_status"] == "missing-party-subtotal"
    assert result["r_missing"] == 1
    assert result["r_features_usable"] == 1
    assert result["r_candidates"] == 1
    assert result["r_subtotal_gap"] is None


def test_subtotal_mismatch_is_reported_with_the_gap() -> None:
    result = features(
        [
            row("R", 60000, "H1AA01001"),
            row("R", 60500, None, marker="party votes:"),
            row("D", 50000, "H1AA01003"),
            row("D", 50000, None, marker="party votes:"),
        ]
    )
    assert result["r_status"] == "subtotal-mismatch"
    assert result["r_subtotal_gap"] == 500
    assert result["r_features_usable"] == 1


def test_zero_vote_candidates_are_not_counted() -> None:
    result = features(
        [
            row("R", 60000, "H1AA01001"),
            row("R", 0, "H1AA01002"),
            row("D", 50000, "H1AA01003"),
            row("D", 50000, None, marker="party votes:"),
            row("R", 60000, None, marker="party votes:"),
        ]
    )
    assert result["r_candidates"] == 1
    assert result["r_candidate_votes"] == 60000


def test_status_priority_is_documented_and_ordered() -> None:
    assert STATUS_PRIORITY[0] == "ambiguous-fusion-party-code"
    assert STATUS_PRIORITY[1] == "no-candidate-rows"
    assert STATUS_PRIORITY[-1] == "ok"
    assert len(set(STATUS_PRIORITY)) == len(STATUS_PRIORITY)


def test_the_feature_table_is_a_one_to_one_join_of_the_cohort(tmp_path: Path) -> None:
    """A cohort contest without a workbook row is an error, not a dropped row."""
    cohort = pd.DataFrame(
        [
            {"election_id": "2016-House-AA-01", "year": 2016, "state": "AA", "district": "01"},
            {"election_id": "2016-House-BB-01", "year": 2016, "state": "BB", "district": "01"},
        ]
    )
    raw = tmp_path / "raw"
    raw.mkdir()
    # The workbook is replaced by a frame so that the unit test does not need
    # a spreadsheet writer.
    import build_primary_features as module

    def fake_read_house(path: Path):
        frame = sheet(
            [
                row("R", 60000, "H1AA01001"),
                row("D", 50000, "H1AA01003"),
                row("D", 50000, None, marker="party votes:"),
                row("R", 60000, None, marker="party votes:"),
            ]
        )
        frame["_state"] = "AA"
        frame["_district"] = "01"
        return "2016 US House Results by State", frame

    original = module.read_house
    module.read_house = fake_read_house
    try:
        # Only the contests that exist in the workbook are joined.
        complete = cohort.iloc[[0]]
        frame, diagnostic, meta = module.build_features(raw, complete, [2016])
        assert list(frame["election_id"]) == ["2016-House-AA-01"]
        assert meta["cohort_rows"] == 1
        assert meta["feature_rows"] == 1
        assert frame["features_available"].iloc[0] == 1
        # A cohort contest without a workbook row must fail loudly.
        with pytest.raises(ValueError):
            module.build_features(raw, cohort, [2016])
    finally:
        module.read_house = original
