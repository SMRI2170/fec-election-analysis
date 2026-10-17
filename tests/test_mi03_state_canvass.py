"""Regression guards for independently published MI-03 2022 canvass totals."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("mi03_canvass", ROOT / "scripts" / "verify_mi03_state_canvass.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture():
    return json.loads((ROOT / "data/sources/mi03_2022_state_canvass.json").read_text())


def test_independent_source_county_sums_equal_official_statewide_totals():
    summary = mod.verify_canvass(fixture())
    assert summary["fec_two_party_fields"] == {
        "primary_rep_votes": 104576,
        "primary_dem_votes": 59661,
        "general_rep_votes": 142229,
        "general_dem_votes": 185989,
    }
    assert summary["general_all_candidates"] == 338988
    assert summary["verified_causal_explanation"] is False


def test_transcription_error_caught():
    data = fixture()
    data["primary"]["John Gibbs (R)"]["Kent"] += 1
    with pytest.raises(AssertionError, match="State manual vs counties mismatch"):
        mod.verify_canvass(data)


def test_unknown_county_caught():
    data = fixture()
    data["county_order"] = ["Kent", "Muskegon", "Wayne"]
    with pytest.raises(ValueError, match="county list"):
        mod.verify_canvass(data)


def test_missing_fec_row_never_passes(tmp_path):
    f = tmp_path / "elections.csv"
    f.write_text("year,state,district,primary_rep_votes,primary_dem_votes,general_rep_votes,general_dem_votes\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="exactly one"):
        mod.compare_fec_csv(mod.verify_canvass(fixture()), f)


def test_fec_difference_raises(tmp_path):
    f = tmp_path / "elections.csv"
    f.write_text("year,state,district,primary_rep_votes,primary_dem_votes,general_rep_votes,general_dem_votes\n2022,MI,03,104577,59661,142229,185989\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="State vs FEC discrepancy"):
        mod.compare_fec_csv(mod.verify_canvass(fixture()), f)
