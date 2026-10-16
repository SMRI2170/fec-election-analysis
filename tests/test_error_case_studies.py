import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "build_error_case_studies", ROOT / "scripts" / "build_error_case_studies.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixtures():
    votes = pd.DataFrame([{
        "year": 2022, "state": "AA", "district": "01",
        "primary_rep_votes": 65, "primary_dem_votes": 35,
        "general_rep_votes": 60, "general_dem_votes": 40,
    }])
    errors = pd.DataFrame([{
        "year": 2022, "state": "AA", "district": "01",
        "primary_rep_share": 0.65, "general_rep_share": 0.60,
        "linear_pred_share": 0.67, "abs_linear_error": 0.07,
        "primary_rule_error": False, "logistic_error": False,
    }])
    data = {
        "cases": [{
            "year": 2022, "state": "AA", "district": "01",
            "check": {"candidate_sums_match": True, "district_general_matches": True},
            "candidates": [
                {"party": "R", "name": "Alice", "primary_votes": 35,
                 "general_votes": 60, "footnotes": None},
                {"party": "R", "name": "Bob", "primary_votes": 30,
                 "general_votes": None, "footnotes": None},
                {"party": "D", "name": "Carol", "primary_votes": 35,
                 "general_votes": 40, "footnotes": None},
            ],
        }],
    }
    return errors, votes, data


def test_candidate_composition_is_derived_only_from_original_fec_rows():
    errors, votes, evidence = fixtures()
    result = module.build_cases(errors, votes, evidence)
    assert len(result) == 1
    assert result.iloc[0]["rep_candidate_rows"] == 2
    assert result.iloc[0]["dem_candidate_rows"] == 1
    assert result.iloc[0]["rep_top_named_primary_share"] == pytest.approx(35 / 65)
    assert result.iloc[0]["rep_general_candidate_names"] == "Alice"
    assert result.iloc[0]["reconciled_to_official_fec"]


def test_missing_fec_candidate_source_fails_closed():
    errors, votes, evidence = fixtures()
    with pytest.raises(AssertionError, match="missing original FEC evidence"):
        module.build_cases(errors, votes, {"cases": []})


def test_different_share_from_source_votes_fails_closed():
    errors, votes, evidence = fixtures()
    errors.loc[0, "primary_rep_share"] = 0.70
    with pytest.raises(AssertionError, match="Primary share"):
        module.build_cases(errors, votes, evidence)


def test_failed_original_reconciliation_fails_closed():
    errors, votes, evidence = fixtures()
    evidence["cases"][0]["check"]["candidate_sums_match"] = False
    with pytest.raises(AssertionError, match="reconciliation"):
        module.build_cases(errors, votes, evidence)


def test_invalid_n_not_allowed():
    errors, votes, evidence = fixtures()
    with pytest.raises(ValueError, match="positive"):
        module.build_cases(errors, votes, evidence, top_n=0)
