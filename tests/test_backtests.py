import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_backtests", ROOT / "scripts/run_backtests.py")
import sys
sys.path.insert(0, str(ROOT / "scripts"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def synthetic_elections():
    rows = []
    for year in [2016, 2018, 2020, 2022, 2024]:
        rows += [
            {"year": year, "state": "AA", "chamber": "House", "district": "01",
             "primary_rep_votes": 60, "primary_dem_votes": 40,
             "general_rep_votes": 55, "general_dem_votes": 45},
            {"year": year, "state": "BB", "chamber": "House", "district": "02",
             "primary_rep_votes": 40, "primary_dem_votes": 60,
             "general_rep_votes": 45, "general_dem_votes": 55},
        ]
    return pd.DataFrame(rows)


def test_future_data_not_used_for_training():
    scores = module.run_backtests(synthetic_elections(), [2018, 2020, 2022])
    assert set(scores.test_year) == {2018, 2020, 2022}
    assert set(scores[scores.test_year == 2018].n_train) == {2}
    assert set(scores[scores.test_year == 2020].n_train) == {4}
    assert set(scores[scores.test_year == 2022].n_train) == {6}
    assert (scores.n_test == 2).all()


def test_models_include_naive_baselines():
    scores = module.run_backtests(synthetic_elections(), [2022])
    assert "primary-share identity" in set(scores.model)
    assert "primary-winner rule" in set(scores.model)
    assert "linear regression" in set(scores.model)
    assert "logistic regression" in set(scores.model)
    assert scores.score.between(0, 1).all()
