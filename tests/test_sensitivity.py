import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_script(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample():
    records = []
    for year in [2016, 2018, 2020, 2022, 2024]:
        for state, rep, dem in [("AA", 16000, 14000), ("BB", 12000, 18000), ("CC", 2000, 3000)]:
            records.append({
                "year": year, "state": state, "chamber": "House", "district": "01",
                "primary_rep_votes": rep, "primary_dem_votes": dem,
                "general_rep_votes": rep + 3000, "general_dem_votes": dem + 1000,
                "source_file": f"fec{year}.xlsx", "source_sheet": "House",
            })
    return pd.DataFrame(records)


def test_sensitivity_reduces_target_population_and_preserves_time_split():
    mod = load_script("run_sensitivity.py")
    metrics = mod.compare_thresholds(sample(), 2022, [0, 5000])
    base = metrics[metrics.min_each_party_primary_votes == 0]
    restricted = metrics[metrics.min_each_party_primary_votes == 5000]
    assert set(base.n_train) == {9}
    assert set(restricted.n_train) == {6}
    assert set(base.n_test) == {3}
    assert set(restricted.n_test) == {2}


def test_sensitivity_rejects_invalid_thresholds():
    with pytest.raises(ValueError, match="Thresholds"):
        load_script("run_sensitivity.py").compare_thresholds(sample(), 2022, [0, -1])


def test_error_report_only_uses_2022_test_rows():
    report = load_script("error_cases.py").error_report(sample(), 2022)
    assert len(report) == 3
    assert set(report.year) == {2022}
    assert report.abs_linear_error.is_monotonic_decreasing
    assert {"primary_rule_error", "logistic_error"} <= set(report.columns)
