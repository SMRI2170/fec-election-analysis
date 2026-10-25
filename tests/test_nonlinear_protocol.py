"""Tests for the frozen non-linear comparison protocol (#61).

These tests do not score any model. They check that the configuration is
readable, that every model is scored under identical conditions, and that the
evaluation year cannot enter the tuning phase.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from nonlinear_protocol import (  # noqa: E402
    CONFIG_PATH,
    LABEL_COLUMNS,
    EvaluationPlan,
    LabelAccessError,
    assert_no_label_access,
    build_plan,
    clip_predictions,
    design_transformer,
    fitting_rows,
    load_config,
    model_names,
    model_spec,
)


def synthetic_frame() -> pd.DataFrame:
    """One row per contest of a synthetic cohort."""
    rows = []
    for year, size in ((2016, 5), (2018, 6), (2020, 7), (2022, 8)):
        for index in range(size):
            rows.append(
                {
                    "year": year,
                    "state": f"S{index:02d}",
                    "district": "01",
                    "primary_rep_share": 0.2 + 0.05 * index,
                    "general_rep_share": 0.25 + 0.05 * index,
                }
            )
    return pd.DataFrame(rows)


def test_the_frozen_configuration_is_readable() -> None:
    config = load_config()
    assert config["issue"] == "#61"
    assert config["data"]["feature_column"] == "primary_rep_share"
    assert config["data"]["target_column"] == "general_rep_share"
    assert config["evaluation"]["test_years"] == [2018, 2020, 2022]
    assert config["evaluation"]["prediction_clip"] == [0.0, 1.0]
    assert config["evaluation"]["bootstrap"]["repetitions"] == 10000
    assert config["evaluation"]["bootstrap"]["seed"] == 20261025
    assert config["evaluation"]["bootstrap"]["unit"] == "state"


def test_the_comparison_covers_the_required_model_families() -> None:
    config = load_config()
    families = {str(model["family"]) for model in config["models"]}
    assert families == {"constant", "identity", "linear", "polynomial_ridge", "spline_ridge"}
    names = model_names(config)
    assert len(names) == len(set(names))
    for name in names:
        assert model_spec(config, name)["name"] == name


def test_every_model_is_scored_under_identical_conditions() -> None:
    """One plan describes the whole comparison, so no model can get its own
    evaluation years, metrics or clipping."""
    config = load_config()
    for year in config["evaluation"]["test_years"]:
        plan = build_plan(config, year)
        assert len(plan.models) == len(config["models"])
        assert plan.metrics == tuple(config["evaluation"]["metrics"])
        assert plan.clip == (0.0, 1.0)
        assert plan.feature_column == config["data"]["feature_column"]
        assert plan.target_column == config["data"]["target_column"]
        assert plan.reference_model in plan.models


def test_the_training_years_are_always_earlier_than_the_test_year() -> None:
    config = load_config()
    for year in config["evaluation"]["test_years"]:
        plan = build_plan(config, year)
        assert plan.train_years == tuple(y for y in config["data"]["cohort_years"] if y < year)
        assert all(train < year for train in plan.train_years)
        assert all(inner < year for inner in plan.inner_validation_years)


def test_2018_has_no_inner_validation_and_says_so() -> None:
    """Only 2016 precedes 2018, so no inner split may be invented."""
    config = load_config()
    plan = build_plan(config, 2018)
    assert plan.train_years == (2016,)
    assert plan.inner_validation_years == ()
    assert "2018" in config["hyperparameters"]["inner_validation_years"]
    assert "not called out-of-year validation" in config["hyperparameters"]["note_for_2018"]


def test_the_fitting_rows_never_contain_the_test_year() -> None:
    frame = synthetic_frame()
    config = load_config()
    for year in config["evaluation"]["test_years"]:
        plan = build_plan(config, year)
        train = fitting_rows(frame, plan)
        assert set(train["year"]) == set(plan.train_years)
        assert (train["year"] < year).all()


def test_the_tuning_phase_refuses_the_target_column() -> None:
    assert_no_label_access(["primary_rep_share"], phase="tuning")
    with pytest.raises(LabelAccessError):
        assert_no_label_access(["primary_rep_share", "general_rep_share"], phase="tuning")
    with pytest.raises(LabelAccessError):
        assert_no_label_access(pd.DataFrame({"general_rep_votes": [1]}), phase="tuning")
    # The evaluation phase may read the target; that is what it scores.
    assert_no_label_access(["general_rep_share"], phase="evaluation")
    assert_no_label_access(["general_rep_share"], phase="fit")


def test_the_configuration_and_the_module_block_the_same_columns() -> None:
    config = load_config()
    declared = set(config["data"]["forbidden_columns_during_tuning"])
    assert declared == set(LABEL_COLUMNS)


def test_the_configuration_holds_no_tuning_entry() -> None:
    """No key may hold a value that was chosen with the test year in view."""
    config = load_config()
    forbidden_words = ("tuned", "selected", "search", "grid", "candidates", "best", "chosen")

    def walk(node, path=""):
        if isinstance(node, dict):
            for key, value in node.items():
                assert not any(word in str(key).lower() for word in forbidden_words), (
                    f"configuration key {path}/{key} looks like a tuning entry"
                )
                walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(config)


def test_the_hyperparameters_are_fixed_constants() -> None:
    config = load_config()
    assert config["hyperparameters"]["selection"].startswith("fixed constants")
    for model in config["models"]:
        hyperparameters = model.get("hyperparameters", {})
        for key, value in hyperparameters.items():
            assert not isinstance(value, (list, dict)) or key == "knots"
    # The ridge penalty is the same for both penalised models.
    polynomial = model_spec(config, "polynomial2-ridge")["hyperparameters"]
    spline = model_spec(config, "cubic-spline-ridge")["hyperparameters"]
    assert polynomial["alpha"] == spline["alpha"] == 1.0
    assert polynomial["standardize"] is True and spline["standardize"] is True


def test_the_spline_knots_are_fixed_positions() -> None:
    config = load_config()
    spec = model_spec(config, "cubic-spline-ridge")
    assert spec["hyperparameters"]["knots"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert spec["hyperparameters"]["degree"] == 3
    assert spec["hyperparameters"]["n_knots"] == 5


def test_predictions_are_clipped_to_the_declared_interval() -> None:
    config = load_config()
    plan = build_plan(config, 2022)
    clipped = clip_predictions([-0.2, 0.5, 1.4], plan)
    assert list(clipped) == [0.0, 0.5, 1.0]


def test_the_design_transformer_is_deterministic_for_the_fixed_knots() -> None:
    """The spline basis must not depend on the data it is fitted to."""
    import numpy as np

    config = load_config()
    spec = model_spec(config, "cubic-spline-ridge")
    transformer = design_transformer(spec)
    assert transformer is not None
    first = transformer.fit_transform(np.array([[0.1], [0.4], [0.9]]))
    other = design_transformer(spec)
    second = other.fit_transform(np.array([[0.2], [0.5], [0.8]]))
    # The same input gives the same basis regardless of the fitted sample.
    assert np.allclose(
        transformer.transform(np.array([[0.1], [0.4], [0.9]])), first
    )
    assert second.shape == first.shape


def test_the_linear_family_has_no_design_transformer() -> None:
    config = load_config()
    assert design_transformer(model_spec(config, "linear")) is None
    assert design_transformer(model_spec(config, "constant-mean")) is None
    assert design_transformer(model_spec(config, "primary-carryover")) is None


def test_the_plan_is_frozen() -> None:
    """The plan is a value object; it cannot be edited after the fact."""
    config = load_config()
    plan = build_plan(config, 2020)
    assert isinstance(plan, EvaluationPlan)
    with pytest.raises(Exception):
        plan.test_year = 2022  # type: ignore[misc]


def test_the_configuration_file_is_committed_as_json() -> None:
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert raw["protocol_version"]
    assert raw["frozen_at"]
    assert raw["reporting_rules"]
