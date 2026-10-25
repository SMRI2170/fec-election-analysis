"""Executable protocol for the non-linear comparison (#61).

The comparison itself is run in [#62](https://github.com/SMRI2170/fec-election-analysis/issues/62).
This module holds the parts that must be fixed **before** any test year is
scored:

* the frozen configuration (``configs/nonlinear-comparison.json``),
* the evaluation plan of a test year (training years, inner validation years,
  models, metrics, clipping, bootstrap settings),
* the guard that keeps the tuning phase away from the target column.

The module deliberately contains **no fitting and no scoring**. The only way to
run the comparison is to build a plan first, and the plan can never contain the
test year in its training or inner validation years.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

#: Location of the frozen configuration, relative to the repository root.
CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "nonlinear-comparison.json"

#: The phases of the protocol. ``tuning`` is the only phase in which a
#: hyperparameter could ever be chosen, and it may not see a label column.
PHASES = ("fit", "tuning", "evaluation")

#: The columns that hold information about the outcome. They may only be read
#: while scoring a finished prediction.
LABEL_COLUMNS = (
    "general_rep_share",
    "general_rep_votes",
    "general_dem_votes",
    "general_two_party_rep_lead",
    "general_rep_win",
    "general_tie",
    "general_rep_share_actual",
    "residual",
)


class LabelAccessError(RuntimeError):
    """Raised when a label column would enter the tuning phase."""


@dataclass(frozen=True)
class EvaluationPlan:
    """Everything one test year is scored with."""

    test_year: int
    train_years: tuple[int, ...]
    inner_validation_years: tuple[int, ...]
    models: tuple[str, ...]
    metrics: tuple[str, ...]
    clip: tuple[float, float]
    bootstrap_seed: int
    bootstrap_repetitions: int
    bootstrap_unit: str
    feature_column: str
    target_column: str
    reference_model: str
    primary_metric: str


def load_config(path: Path | None = None) -> dict:
    """Load and check the frozen configuration."""
    location = Path(path) if path is not None else CONFIG_PATH
    config = json.loads(location.read_text(encoding="utf-8"))
    required = ("data", "models", "evaluation", "hyperparameters")
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"configuration is missing sections: {missing}")
    if not config["models"]:
        raise ValueError("configuration lists no model")
    return config


def model_names(config: dict) -> tuple[str, ...]:
    return tuple(str(model["name"]) for model in config["models"])


def model_spec(config: dict, name: str) -> dict:
    """Return the specification of one model."""
    for model in config["models"]:
        if str(model["name"]) == name:
            return model
    raise KeyError(f"unknown model: {name}")


def build_plan(config: dict, test_year: int) -> EvaluationPlan:
    """Build the evaluation plan of one test year.

    The training years are the cohort years before the test year. The inner
    validation years are read from the configuration and are checked to be
    strictly earlier than the test year, so that a later edit of the
    configuration cannot open a hindsight path.
    """
    evaluation = config["evaluation"]
    hyperparameters = config["hyperparameters"]
    inner = hyperparameters.get("inner_validation_years", {})
    key = str(test_year)
    if key not in inner:
        raise ValueError(f"no inner validation years declared for test year {test_year}")
    inner_years = tuple(sorted(int(year) for year in inner[key]))
    if any(year >= test_year for year in inner_years):
        raise ValueError(
            f"inner validation years {inner_years} are not earlier than {test_year}"
        )
    train_years = _train_years_from_rule(config, test_year)
    if any(year >= test_year for year in train_years):
        raise ValueError("the training rule must only use earlier years")
    clip = tuple(float(value) for value in evaluation["prediction_clip"])
    return EvaluationPlan(
        test_year=int(test_year),
        train_years=train_years,
        inner_validation_years=inner_years,
        models=model_names(config),
        metrics=tuple(str(metric) for metric in evaluation["metrics"]),
        clip=clip,  # type: ignore[arg-type]
        bootstrap_seed=int(evaluation["bootstrap"]["seed"]),
        bootstrap_repetitions=int(evaluation["bootstrap"]["repetitions"]),
        bootstrap_unit=str(evaluation["bootstrap"]["unit"]),
        feature_column=str(config["data"]["feature_column"]),
        target_column=str(config["data"]["target_column"]),
        reference_model=str(evaluation["reference_model"]),
        primary_metric=str(evaluation["primary_metric"]),
    )


def _train_years_from_rule(config: dict, test_year: int) -> tuple[int, ...]:
    """Training years derived from the cohort years declared in the config."""
    cohort_years = config["data"].get("cohort_years")
    if not cohort_years:
        raise ValueError("the configuration does not declare the cohort years")
    return tuple(sorted(int(year) for year in cohort_years if int(year) < test_year))


def fitting_rows(frame: pd.DataFrame, plan: EvaluationPlan) -> pd.DataFrame:
    """Return the rows a model may be fitted on.

    The rows of the test year are never returned, so the target of the test
    year cannot reach the fit.
    """
    train = frame[frame["year"].astype(int).isin(plan.train_years)]
    if train.empty:
        raise ValueError(f"no training rows for test year {plan.test_year}")
    if (train["year"].astype(int) >= plan.test_year).any():
        raise AssertionError("training rows contain the test year")
    return train


def assert_no_label_access(columns, phase: str, forbidden=None) -> None:
    """Refuse a label column in the tuning phase.

    ``columns`` may be a list of names or a pandas object whose columns are
    inspected. The forbidden names default to :data:`LABEL_COLUMNS`; the
    configuration carries the same list and a test keeps both in sync.
    """
    if phase not in PHASES:
        raise ValueError(f"unknown phase: {phase}")
    if phase != "tuning":
        return
    if isinstance(columns, pd.DataFrame):
        names = [str(name) for name in columns.columns]
    else:
        names = [str(name) for name in columns]
    blocked = set(LABEL_COLUMNS if forbidden is None else forbidden)
    offending = sorted(set(names) & blocked)
    if offending:
        raise LabelAccessError(
            "the tuning phase must not see the target column: " + ", ".join(offending)
        )


def clip_predictions(values: np.ndarray, plan: EvaluationPlan) -> np.ndarray:
    """Clip predictions to the interval the protocol declares."""
    low, high = plan.clip
    return np.clip(np.asarray(values, dtype=float), low, high)


def spline_knots(spec: dict) -> np.ndarray:
    """Return the fixed knot positions of a spline model."""
    knots = spec["hyperparameters"]["knots"]
    return np.asarray(knots, dtype=float).reshape(-1, 1)


def design_transformer(spec: dict):
    """Return the design-matrix transformer of a model.

    Only the polynomial and spline families transform the input; the other
    families use the feature directly.
    """
    from sklearn.preprocessing import PolynomialFeatures, SplineTransformer

    family = spec["family"]
    hyperparameters = spec.get("hyperparameters", {})
    if family == "polynomial_ridge":
        return PolynomialFeatures(
            degree=int(hyperparameters["degree"]), include_bias=False
        )
    if family == "spline_ridge":
        knots = spline_knots(spec)
        # The knot positions are fixed in the configuration, so the basis does
        # not depend on the data. scikit-learn expects the knots in a shape
        # that changed between releases, so both shapes are tried.
        for candidate in (knots, knots.reshape(-1)):
            try:
                transformer = SplineTransformer(
                    n_knots=int(hyperparameters["n_knots"]),
                    degree=int(hyperparameters["degree"]),
                    knots=candidate,
                    include_bias=bool(hyperparameters.get("include_bias", False)),
                    extrapolation="constant",
                )
                # scikit-learn checks that the knots span the data range, so
                # the probe sample covers the whole share interval.
                transformer.fit(np.array([[0.0], [1.0]]))
                return transformer
            except ValueError:
                continue
        raise ValueError("the spline knot positions were rejected by scikit-learn")
    return None
