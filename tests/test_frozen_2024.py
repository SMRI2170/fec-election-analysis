"""Unit tests for the frozen 2024 evaluation (#54).

Every fixture is synthetic. The real 2024 result does not exist yet: the FEC
has not published the 2024 edition of the Federal Elections compilation. These
tests therefore check two things:

* the pipeline refuses to produce a value when the source is missing, and
* the pipeline computes the frozen metrics correctly on a synthetic stand-in.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

import download_fec_2024 as download  # noqa: E402
import evaluate_frozen_2024 as evaluate_module  # noqa: E402
import normalize_fec_2024 as normalize  # noqa: E402
from evaluate_frozen_2024 import (  # noqa: E402
    EvaluationUnavailable,
    build_estimator,
    classification_metrics,
    load_evaluation_year,
    load_frozen_cohort,
    score,
    state_bootstrap_interval,
)
from fec_analysis.core import prepare_elections  # noqa: E402
from frozen_2024_protocol import load_config  # noqa: E402

COUNTS = {2016: 200, 2018: 241, 2020: 237, 2022: 238}


def synthetic_rows(year: int, count: int) -> list[dict]:
    rows = []
    for index in range(count):
        primary_rep = 1000 + (index * 7) % 900
        primary_dem = 2000 - (index * 5) % 700
        general_rep = int(primary_rep * 0.72) + (index % 11) - 5
        general_dem = int(primary_dem * 0.68) + (index % 13) - 6
        state = f"S{index % 12:02d}"
        district = f"{index // 12 + 1:02d}"
        rows.append(
            {
                "year": year,
                "state": state,
                "chamber": "House",
                "district": district,
                "election_id": f"{year}-House-{state}-{district}",
                "primary_rep_votes": primary_rep,
                "primary_dem_votes": primary_dem,
                "general_rep_votes": max(general_rep, 1),
                "general_dem_votes": max(general_dem, 1),
            }
        )
    return rows


def synthetic_cohort_frame() -> pd.DataFrame:
    rows: list[dict] = []
    for year, count in COUNTS.items():
        rows.extend(synthetic_rows(year, count))
    return prepare_elections(pd.DataFrame(rows))


def synthetic_evaluation_frame() -> pd.DataFrame:
    return prepare_elections(pd.DataFrame(synthetic_rows(2024, 40)))


def test_the_edition_link_is_found_in_the_catalogue() -> None:
    html = (
        '<a href="/introduction-campaign-finance/election-results-and-voting-information/'
        'federal-elections-2024/">2024</a>'
    )
    link = download.find_edition_link(html)
    assert link is not None
    assert link.endswith("/federal-elections-2024/")


def test_the_workbook_link_is_found_in_the_edition_page() -> None:
    html = '<a href="/documents/6901/federalelections2024.xlsx">Excel</a>'
    link = download.find_workbook_link(html)
    assert link == "https://www.fec.gov/documents/6901/federalelections2024.xlsx"


def test_the_retrieval_stops_when_the_edition_page_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing edition page is recorded as a reason, not as a value."""
    monkeypatch.setattr(download, "fetch", lambda url, timeout=45: (404, b""))
    record = download.locate()
    assert record["status"] == "not-published"
    assert record["workbook_url"] is None
    assert record["sha256"] is None
    assert record["notes"]


def test_the_retrieval_stops_when_the_edition_has_no_workbook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch(url: str, timeout: int = 45):
        if "federal-elections-2024" in url:
            return 200, b"<html>no workbook here</html>"
        return 200, b"<html>no edition link</html>"

    monkeypatch.setattr(download, "fetch", fake_fetch)
    record = download.locate()
    assert record["status"] == "edition-without-workbook"
    assert record["workbook_url"] is None


def test_the_normaliser_refuses_without_a_retrieval_record(tmp_path: Path) -> None:
    with pytest.raises(normalize.SourceUnavailable):
        normalize.load_record(tmp_path / "missing.json")
    path = tmp_path / "record.json"
    path.write_text(json.dumps({"status": "not-published"}), encoding="utf-8")
    with pytest.raises(normalize.SourceUnavailable):
        normalize.load_record(path)


def test_the_evaluation_refuses_without_the_normalised_file(tmp_path: Path) -> None:
    with pytest.raises(EvaluationUnavailable):
        load_evaluation_year(tmp_path / "missing.csv")


def test_the_evaluation_refuses_a_cohort_of_the_wrong_size(tmp_path: Path) -> None:
    path = tmp_path / "elections.csv"
    small = pd.DataFrame(synthetic_rows(2016, 10))
    small.to_csv(path, index=False)
    with pytest.raises(EvaluationUnavailable):
        load_frozen_cohort(path)


def test_the_evaluation_refuses_a_file_of_another_year(tmp_path: Path) -> None:
    path = tmp_path / "elections_2024.csv"
    other = pd.DataFrame(synthetic_rows(2020, 10))
    other.to_csv(path, index=False)
    with pytest.raises(EvaluationUnavailable):
        load_evaluation_year(path)


def test_the_models_come_from_the_frozen_configuration() -> None:
    config = load_config()
    assert [model["name"] for model in config["models"]] == [
        "primary-carryover",
        "linear",
        "polynomial2-ridge",
        "cubic-spline-ridge",
    ]
    for spec in config["models"]:
        estimator = build_estimator(spec)
        if spec["family"] == "identity":
            assert estimator is None
        else:
            assert estimator is not None


def test_the_score_is_reported_in_percentage_points() -> None:
    prediction = np.array([0.6, 0.4])
    actual = np.array([0.5, 0.5])
    metrics = score(prediction, actual)
    assert metrics["mae_points"] == pytest.approx(10.0)
    assert metrics["rmse_points"] == pytest.approx(10.0)
    assert metrics["p95_abs_error_points"] == pytest.approx(10.0)


def test_the_classification_label_is_the_two_party_lead() -> None:
    # The prediction 0.6 is a lead, the prediction 0.4 is not.
    metrics = classification_metrics(np.array([0.6, 0.4]), np.array([0.7, 0.3]))
    assert metrics["two_party_lead_accuracy"] == pytest.approx(1.0)
    assert metrics["brier_score"] == pytest.approx((0.4**2 + 0.4**2) / 2)


def test_the_state_bootstrap_is_deterministic() -> None:
    delta = np.array([0.5, -0.25, 0.75, 0.0, -1.0])
    states = np.array(["AA", "AA", "BB", "BB", "CC"])
    first = state_bootstrap_interval(delta, states, seed=7, repetitions=500)
    second = state_bootstrap_interval(delta, states, seed=7, repetitions=500)
    assert first == second
    with pytest.raises(ValueError):
        state_bootstrap_interval(delta, states[:2], seed=7, repetitions=500)


def test_the_pipeline_computes_the_frozen_metrics_on_a_stand_in() -> None:
    """The whole evaluation runs on a synthetic stand-in of the 2024 data."""
    config = load_config()
    cohort = synthetic_cohort_frame()
    evaluation = synthetic_evaluation_frame()
    summary, predictions, paired, extra = evaluate_module.evaluate(
        cohort, evaluation, config
    )
    assert len(summary) == len(config["models"])
    assert int(summary["n_test"].iloc[0]) == 40
    assert int(summary["n_train"].iloc[0]) == 916
    for column in ("mae_points", "rmse_points", "p95_abs_error_points"):
        assert column in summary.columns
    for column in ("two_party_lead_accuracy", "brier_score"):
        assert column in summary.columns
    # The comparison against both references is produced for every other model.
    assert len(paired) == (len(config["models"]) - 1) * 2
    assert set(paired["reference"]) == {"linear", "primary-carryover"}
    assert int(paired["n"].iloc[0]) == 40
    assert len(predictions) == 40 * len(config["models"])
    assert extra["meta"]["label"].startswith("the two-party vote lead")
    assert extra["meta"]["no_causal_claim"] is True


def test_the_training_set_never_reaches_the_evaluation_year() -> None:
    """A cohort that carries 2024 rows must not put them into the fit.

    The contamination is placed in the training material. The evaluation has to
    keep the fit on the 916 rows of 2016-2022, and the reported training size
    has to stay 916.
    """
    config = load_config()
    cohort = synthetic_cohort_frame()
    extra = synthetic_evaluation_frame()[
        [
            "year", "state", "chamber", "district", "election_id",
            "primary_rep_votes", "primary_dem_votes", "general_rep_votes",
            "general_dem_votes",
        ]
    ]
    contaminated = prepare_elections(
        pd.concat([cohort[extra.columns], extra], ignore_index=True)
    )
    assert len(contaminated) == 956
    summary, _, _, _ = evaluate_module.evaluate(
        contaminated, synthetic_evaluation_frame(), config
    )
    assert int(summary["n_train"].iloc[0]) == 916


def test_the_evaluation_never_uses_the_2024_labels_as_features() -> None:
    """Changing the 2024 labels does not change a single prediction."""
    config = load_config()
    cohort = synthetic_cohort_frame()
    evaluation = synthetic_evaluation_frame()
    _, predictions, _, _ = evaluate_module.evaluate(cohort, evaluation, config)

    raw = evaluation[[
        "year", "state", "district", "chamber", "election_id",
        "primary_rep_votes", "primary_dem_votes", "general_rep_votes",
        "general_dem_votes",
    ]].copy()
    raw["general_rep_votes"] = raw["general_rep_votes"].to_numpy()[::-1]
    other = evaluate_module.evaluate(cohort, prepare_elections(raw), config)[1]
    for model in config["models"]:
        left = predictions[predictions["model"].eq(model["name"])].sort_values(
            "election_id"
        )
        right = other[other["model"].eq(model["name"])].sort_values("election_id")
        assert np.allclose(
            left["prediction"].to_numpy(), right["prediction"].to_numpy()
        )
