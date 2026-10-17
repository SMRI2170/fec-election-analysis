"""Regression tests for the read-only 2020 WI primary boundary audit."""
import importlib.util
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("audit_wi_2020", ROOT / "scripts" / "audit_wi_2020_writeins.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def raw_fixture(wi02_writein_district="02"):
    rows = [
        ("WI", "01", "Bryan Steil", "H001", "R", 40273, "", ""),
        ("WI", "01", "", "", "R", 40404, "Party Votes:", ""),
        ("WI", wi02_writein_district, "Scattered", "", "W(R)", 131, "", ""),
        ("WI", "02", "Theron", "H002", "R", 18812, "", ""),
        ("WI", "02", "Scattered", "", "W(R)", 50, "", ""),
        ("WI", "02", "", "", "R", 18862, "Party Votes:", ""),
    ]
    cols = ["STATE ABBREVIATION", "DISTRICT", "CANDIDATE NAME", "FEC ID", "PARTY", "PRIMARY VOTES", "TOTAL VOTES", "FOOTNOTES"]
    df = pd.DataFrame(rows, columns=cols)
    df["_state"] = df["STATE ABBREVIATION"]
    df["_district"] = df["DISTRICT"]
    df["_party"] = df["PARTY"].astype("string")
    df["_marker"] = df["TOTAL VOTES"].astype("string").str.lower()
    df["_candidate"] = df["FEC ID"].astype("string").str.fullmatch(r"H[A-Z0-9]+", na=False)
    return df


def test_mislabelled_writein_is_flagged_as_hypothesis_but_not_corrected():
    report = mod.audit(raw_fixture())
    districts = {r["district"]: r for r in report["districts"]}
    assert districts["01"]["remaining_gap"] == 131
    assert districts["02"]["remaining_gap"] == -131
    assert report["opposite_gap_with_matching_wi02_writein"] is True
    assert report["automatic_reallocation"] is False
    assert districts["02"]["writein_primary_rows"][0]["primary_votes"] == 131


def test_valid_assignment_has_no_gap_or_boundary_suspicion():
    report = mod.audit(raw_fixture(wi02_writein_district="01"))
    assert all(r["remaining_gap"] == 0 for r in report["districts"])
    assert report["opposite_gap_with_matching_wi02_writein"] is False


def test_missing_source_subtotal_is_an_error():
    df = raw_fixture()
    df = df.drop(index=1)
    import pytest
    with pytest.raises(ValueError, match="subtotal"):
        mod.audit(df)
