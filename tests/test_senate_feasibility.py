"""Synthetic unit tests for the chamber feasibility inspection (#66).

Every fixture here is synthetic. The real measurements live in
``docs/chamber-feasibility.md``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_senate_feasibility import (  # noqa: E402
    _primary_sum,
    inspect_house_scale,
    inspect_senate,
    read_chamber_sheet,
    vote,
)


def row(
    party: str,
    primary: object,
    general: object = None,
    fec_id: str | None = None,
    marker: str = "",
    state: str = "AA",
    term: str = "S",
) -> dict:
    return {
        "STATE ABBREVIATION": state,
        "DISTRICT": term,
        "FEC ID": fec_id,
        "PARTY": party,
        "PRIMARY VOTES": primary,
        "GENERAL VOTES": general,
        "TOTAL VOTES": marker,
    }


def senate_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["_state"] = frame["STATE ABBREVIATION"].astype("string").str.strip().str.upper()
    frame["_term_raw"] = frame["DISTRICT"].astype("string")
    frame["_term"] = frame["_term_raw"].str.strip()
    frame["_party"] = frame["PARTY"].astype("string").str.strip().str.upper()
    frame["_marker"] = frame["TOTAL VOTES"].astype("string").str.strip().str.lower()
    frame["_candidate"] = (
        frame["FEC ID"].astype("string").str.strip().str.upper().str.fullmatch(
            r"S[A-Z0-9]+", na=False
        )
    )
    return frame


def test_vote_never_converts_a_marker_into_a_number() -> None:
    assert vote("1,234") == 1234
    assert vote("0") == 0
    assert vote("Unopposed") is None
    assert vote("S") is None
    assert vote(None) is None


def test_the_primary_sum_counts_candidates_and_party_writeins() -> None:
    frame = senate_frame(
        [
            row("R", 60000, fec_id="S8AA01001"),
            row("R", 0, fec_id="S8AA01002"),
            row("R", "Unopposed", fec_id="S8AA01003"),
            row("W(R)", 500),
            row("D", 50000, fec_id="S8AA01004"),
        ]
    )
    # 60000 from the candidate, 500 from the party-attributed write-in.
    assert _primary_sum(frame, "R") == 60500
    assert _primary_sum(frame, "R", include_writeins=False) == 60000
    assert _primary_sum(frame, "D") == 50000


def test_the_inspection_counts_races_and_two_party_primaries() -> None:
    frame = senate_frame(
        [
            row("R", 60000, general=500000, fec_id="S8AA01001"),
            row("D", 50000, general=520000, fec_id="S8AA01004"),
            row("D", 50000, marker="party votes:"),
            row("R", 60000, marker="party votes:"),
            row("R", 40000, general=300000, fec_id="S8BB01001", state="BB"),
            row("D", "Unopposed", fec_id="S8BB01002", state="BB"),
        ]
    )
    result = inspect_senate(frame)
    assert result["races"] == 2
    assert result["both_party_primary"] == 1
    # The second race has a Republican Primary vote but an unopposed
    # Democratic one, so it is counted as "any party has a Primary vote".
    assert result["any_party_primary"] == 2
    assert result["unopposed_primary"] == 1
    assert result["subtotal_reconciles"] == 2


def test_a_mismatching_subtotal_is_reported() -> None:
    frame = senate_frame(
        [
            row("R", 60000, general=500000, fec_id="S8AA01001"),
            row("R", 60001, marker="party votes:"),
            row("D", 50000, general=520000, fec_id="S8AA01004"),
            row("D", 50000, marker="party votes:"),
        ]
    )
    result = inspect_senate(frame)
    assert result["subtotal_reconciles"] == 0


def test_the_primary_reconciliation_does_not_use_the_general_column() -> None:
    frame = senate_frame(
        [
            row("R", 60000, general=500000, fec_id="S8AA01001"),
            row("D", 50000, general=520000, fec_id="S8AA01004"),
            row("D", 50000, marker="party votes:"),
            row("R", 60000, marker="party votes:"),
        ]
    )
    before = inspect_senate(frame)
    changed = frame.copy()
    changed["GENERAL VOTES"] = 1
    after = inspect_senate(changed)
    assert before["subtotal_reconciles"] == after["subtotal_reconciles"]
    assert before["both_party_primary"] == after["both_party_primary"]


def test_the_raw_term_labels_are_kept_next_to_the_normalized_ones() -> None:
    """The published labels differ in case and in a trailing space."""
    frame = senate_frame(
        [
            row("R", 60000, general=500000, fec_id="S8AA01001", term="S "),
            row("D", 50000, general=520000, fec_id="S8AA01004", term="S-Unexpired Term"),
        ]
    )
    result = inspect_senate(frame)
    assert "S " in result["term_labels_raw"]
    assert "S-Unexpired Term" in result["term_labels_raw"]
    assert "S" in result["term_labels"]
    assert result["unexpired_term_states"] == ["AA"]


def test_the_house_scale_is_the_mean_two_party_general_total() -> None:
    frame = pd.DataFrame(
        [
            {"_state": "AA", "_district": "01", "_candidate": True, "_party": "R",
             "GENERAL VOTES": 300000},
            {"_state": "AA", "_district": "01", "_candidate": True, "_party": "D",
             "GENERAL VOTES": 200000},
            {"_state": "AA", "_district": "02", "_candidate": True, "_party": "R",
             "GENERAL VOTES": 100000},
            {"_state": "AA", "_district": "02", "_candidate": True, "_party": "D",
             "GENERAL VOTES": 100000},
        ]
    )
    result = inspect_house_scale(frame)
    assert result["districts"] == 2
    assert result["mean_two_party_general_total"] == pytest.approx((500000 + 200000) / 2)


def test_the_reader_requires_exactly_one_sheet(tmp_path: Path) -> None:
    path = tmp_path / "federalelections2020.xlsx"
    with pytest.raises(Exception):
        read_chamber_sheet(path, "Senate")
