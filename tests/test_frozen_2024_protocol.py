"""Unit tests for the frozen 2024 evaluation plan (#53).

The plan is a pre-registration. These tests check that the frozen document,
the frozen configuration and the frozen source catalogue agree, and that the
guards against a hindsight path are in place.

No test in this file reads a 2024 result, because no 2024 result exists at the
time of the freeze.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from frozen_2024_protocol import (  # noqa: E402
    CONFIG_PATH,
    NOTE_PATH,
    SOURCE_CATALOG_PATH,
    LabelAccessError,
    assert_no_label_access,
    build_plan,
    check_freeze_commit,
    compare_config_and_note,
    extract_note_block,
    frozen_catalogue_years,
    load_config,
    run_checks,
)

#: The model set that is fixed before the 2024 result exists.
EXPECTED_MODELS = (
    "primary-carryover",
    "linear",
    "polynomial2-ridge",
    "cubic-spline-ridge",
)
#: The cohort of the frozen study.
FROZEN_COHORT = {2016: 200, 2018: 241, 2020: 237, 2022: 238}


@pytest.fixture(scope="module")
def config() -> dict:
    return load_config()


def test_the_note_and_the_configuration_are_identical(config: dict) -> None:
    """The research note and the configuration may not drift apart."""
    note = extract_note_block()
    assert compare_config_and_note(config, note) == []


def test_a_changed_configuration_is_detected(config: dict) -> None:
    """The comparison has to notice a difference, not only agree by accident."""
    note = extract_note_block()
    broken = json.loads(json.dumps(note))
    broken["data"]["evaluation_year"] = 2026
    differences = compare_config_and_note(config, broken)
    assert differences
    assert any("evaluation_year" in item for item in differences)


def test_the_plan_uses_only_years_before_the_evaluation(config: dict) -> None:
    plan = build_plan(config)
    assert plan.evaluation_year == 2024
    assert plan.training_years == (2016, 2018, 2020, 2022)
    assert all(year < plan.evaluation_year for year in plan.training_years)
    assert sum(FROZEN_COHORT.values()) == 916


def test_the_plan_refuses_a_training_year_that_is_not_earlier(config: dict) -> None:
    broken = json.loads(json.dumps(config))
    broken["data"]["training_years"] = [2016, 2024]
    with pytest.raises(ValueError):
        build_plan(broken)


def test_the_evaluation_count_is_declared_unknown_in_advance(config: dict) -> None:
    """The plan may not pretend to know a count it cannot know yet."""
    assert "unknown" in str(config["data"]["evaluation_n"]).lower()


def test_the_target_is_a_two_party_lead_and_not_a_certified_winner(config: dict) -> None:
    target = str(config["data"]["target_definition"])
    assert "two-party" in target.lower()
    assert "NOT a certified winner" in target
    assert config["data"]["target_column"] == "general_rep_share"
    assert "general_rep_win" in config["data"]["forbidden_columns_during_tuning"]


def test_the_tuning_phase_refuses_the_target_column(config: dict) -> None:
    with pytest.raises(LabelAccessError):
        assert_no_label_access(["primary_rep_share", "general_rep_share"], "tuning")
    assert_no_label_access(["general_rep_share"], "fit")
    assert_no_label_access(["general_rep_share"], "evaluation")
    with pytest.raises(ValueError):
        assert_no_label_access(["general_rep_share"], "unknown-phase")


def test_the_model_set_is_the_pre_registered_one(config: dict) -> None:
    plan = build_plan(config)
    assert plan.models == EXPECTED_MODELS
    names = [model["name"] for model in config["models"]]
    assert names == list(EXPECTED_MODELS)
    # The carry-over model has no fitted parameter.
    carry = [m for m in config["models"] if m["name"] == "primary-carryover"][0]
    assert carry["fitted"] is False
    assert carry["hyperparameters"] == {}
    # The challengers keep the hyperparameters of the earlier protocol.
    poly = [m for m in config["models"] if m["name"] == "polynomial2-ridge"][0]
    assert poly["hyperparameters"]["degree"] == 2
    assert poly["hyperparameters"]["alpha"] == 1.0
    spline = [m for m in config["models"] if m["name"] == "cubic-spline-ridge"][0]
    assert spline["hyperparameters"]["knots"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert spline["hyperparameters"]["alpha"] == 1.0


def test_no_hyperparameter_search_is_planned(config: dict) -> None:
    assert "none" in str(config["training"]["hyperparameter_search"]).lower()


def test_the_metrics_are_declared_with_their_unit(config: dict) -> None:
    plan = build_plan(config)
    assert "mae_points" in plan.metrics
    assert "mae_difference_against_primary_carryover_points" in plan.metrics
    assert "percentage points" in str(config["metrics"]["metric_unit"]).lower()
    assert plan.bootstrap_unit == "state"
    assert plan.bootstrap_repetitions == 10000
    assert plan.bootstrap_seed == 20261025
    assert "exploratory" in str(config["metrics"]["bootstrap"]["status"]).lower()


def test_the_exclusion_rules_are_fixed_and_blind(config: dict) -> None:
    rules = config["exclusion_rules"]
    assert rules["categories"]
    assert "unopposed" in rules["categories"]
    assert "no category may be added, renamed or removed afterwards" in rules["blind_execution"]
    assert rules["no_zero_filling"] is True or "never" in rules["no_zero_filling"]
    assert "never merged" in rules["no_subtotal_merging"]


def test_the_forbidden_operations_are_listed(config: dict) -> None:
    forbidden = config["forbidden_operations"]
    assert len(forbidden) >= 5
    joined = " ".join(forbidden).lower()
    assert "hyperparameter" in joined
    assert "2024" in joined


def test_the_availability_finding_is_recorded(config: dict) -> None:
    status = config["status"]
    assert status["no_2024_result_viewed"] is True
    assert status["source_published_at_freeze_time"] is False
    assert "404" in status["source_availability_check"]
    assert "unavailable" in status["consequence"].lower()
    assert "no value is produced" in status["consequence"].lower()


def test_the_frozen_source_catalogue_does_not_contain_the_evaluation_year() -> None:
    years = frozen_catalogue_years()
    assert 2024 not in years
    assert years == [2010, 2012, 2014, 2016, 2018, 2020, 2022]
    catalog = json.loads(SOURCE_CATALOG_PATH.read_text(encoding="utf-8"))
    assert all("year" in item for item in catalog["publications"])


def test_a_catalogue_entry_of_the_evaluation_year_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 2024 record may not slip into the frozen 2010-2022 catalogue."""
    import frozen_2024_protocol as module

    catalog = json.loads(SOURCE_CATALOG_PATH.read_text(encoding="utf-8"))
    catalog["publications"].append(
        {
            "year": 2024,
            "format": "xlsx",
            "excel_url": "https://www.fec.gov/documents/1/federalelections2024.xlsx",
        }
    )
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    monkeypatch.setattr(module, "SOURCE_CATALOG_PATH", path)
    with pytest.raises(AssertionError):
        module.run_checks()


def test_the_freeze_commit_is_recorded(config: dict) -> None:
    sha = str(config["freeze_commit_sha"])
    assert sha
    assert sha.upper().startswith("PENDING") or len(sha) == 40


def test_the_checks_of_the_freeze_pass(config: dict) -> None:
    result = run_checks()
    assert result["note_matches_configuration"] is True
    assert result["evaluation_year"] == 2024
    assert result["training_years"] == [2016, 2018, 2020, 2022]
    assert result["source_published_at_freeze_time"] is False
    assert 2024 not in result["frozen_catalogue_years"]


def test_a_missing_freeze_commit_is_refused() -> None:
    with pytest.raises(ValueError):
        check_freeze_commit("0" * 40)


def test_the_note_mentions_the_unknown_count_and_the_no_value_rule(config: dict) -> None:
    text = NOTE_PATH.read_text(encoding="utf-8")
    assert "未確定" in text
    assert "値を作らない" in text
    assert CONFIG_PATH.exists()
