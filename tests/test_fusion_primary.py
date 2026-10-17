"""Synthetic boundary tests for fusion-party evidence (not a new election model)."""
import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("audit_fusion_primary", ROOT / "scripts" / "audit_fusion_primary.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture(party_code="D/IP/WF", include_d_total=True, candidate_id="H0003"):
    entries = [
        ("WI", "07", "H0001", "Regular R", "R", 100, None),
        ("WI", "07", "H0002", "Regular D", "D", 30, None),
        ("WI", "07", candidate_id, "Fusion D", party_code, 40, None),
        ("WI", "07", None, "Scattered", "W(D)", 3, None),
        ("WI", "07", None, None, "R", 100, "Party Votes:"),
    ]
    if include_d_total:
        entries.append(("WI", "07", None, None, "D", 73, "Party Votes:"))
    columns = ["STATE ABBREVIATION", "DISTRICT", "FEC ID", "CANDIDATE NAME",
               "PARTY", "PRIMARY VOTES", "TOTAL VOTES"]
    df = pd.DataFrame(entries, columns=columns)
    df["_state"] = df["STATE ABBREVIATION"].astype("string")
    df["_district"] = df["DISTRICT"].astype("string")
    df["_candidate"] = df["FEC ID"].astype("string").str.fullmatch(r"H[A-Z0-9]+", na=False)
    df["_party"] = df["PARTY"].astype("string").str.upper()
    df["_marker"] = df["TOTAL VOTES"].astype("string").str.lower()
    return df


def get_side(rows, party="D"):
    return next(r for r in rows if r["party"] == party)


def test_fusion_exact_reconciliation_does_not_automatically_admit_district():
    side = get_side(mod.inspect_district(fixture(), 2022, "WI", "07"))
    assert side["remaining_gap"] == 40
    assert side["fusion_candidate_primary"] == 40
    assert side["arithmetic_match"]
    assert not side["safe_to_auto_include"]
    assert not side["independently_verified_state_primary"]
    assert not side["candidate_identity_or_party_ambiguity"]


def test_both_major_party_label_cannot_be_treated_as_unambiguous():
    sides = mod.inspect_district(fixture("R/D"), 2022, "WI", "07")
    assert get_side(sides, "D")["arithmetic_match"]
    assert get_side(sides, "D")["candidate_identity_or_party_ambiguity"]
    assert get_side(sides, "R")["status"] == "balanced"


def test_missing_subtotal_remains_unknown_even_with_fusion_candidate():
    side = get_side(mod.inspect_district(fixture(include_d_total=False), 2022, "WI", "07"))
    assert side["status"] == "missing_party_subtotal"
    assert not side["arithmetic_match"]


def test_repeated_fec_id_in_district_flags_ambiguity():
    side = get_side(mod.inspect_district(fixture(candidate_id="H0002"), 2022, "WI", "07"))
    assert side["arithmetic_match"]
    assert side["candidate_identity_or_party_ambiguity"]


def test_non_major_party_star_is_not_automatically_classified():
    side = get_side(mod.inspect_district(fixture("R*"), 2022, "WI", "07"))
    assert side["status"] == "other_discrepancy"
    assert side["fusion_candidate_count"] == 0


def test_historical_count_assertion_rejects_drift():
    with pytest.raises(AssertionError, match="baseline changed"):
        mod.assert_historical_counts({"excluded_districts": 20, "party_sides": 40,
                                     "counts": {}, "no_automatic_reallocation": True})


def test_one_excluded_district_yields_exactly_two_sides():
    excluded = pd.DataFrame([{"year": 2022, "state": "WI", "district": "07",
                              "reason": "primary-subtotal-mismatch"}])
    report = mod.inspect_all(excluded, {2022: fixture()})
    assert report["party_sides"] == 2
    assert report["counts"]["fusion_arithmetic_match"] == 1
    assert report["no_automatic_reallocation"]


def test_cross_party_writein_can_share_candidate_id_without_entering_d_total_twice():
    df = fixture()
    # A candidate ID may recur on a *different party's* write-in ballot row.
    # It must be preserved in the diagnostic without shifting W(IP) votes to D.
    extra = df.iloc[[2]].copy()
    extra["_party"] = "W(IP)"
    extra["PARTY"] = "W(IP)"
    extra["PRIMARY VOTES"] = 7
    df = pd.concat([df, extra], ignore_index=True)
    side = get_side(mod.inspect_district(df, 2022, "WI", "07"))
    assert side["remaining_gap"] == 40
    assert side["fusion_candidate_primary"] == 40
    assert side["arithmetic_match"]
    evidence = side["candidate_evidence"][0]
    assert evidence["duplicate_fec_id_in_district"]
    assert evidence["multiple_positive_primary_rows_same_id"]
    assert sorted(r["party_code"] for r in evidence["same_id_source_rows"]) == ["D/IP/WF", "W(IP)"]
    assert not side["safe_to_auto_include"]
