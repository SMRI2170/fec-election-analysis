import importlib.util
from pathlib import Path
import json
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("verify_reproducibility",ROOT/"scripts"/"verify_reproducibility.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fixture():
    return {"schema_version":1,"year_counts":[{"year":2022,"included":2,"excluded":1}],
            "total_included":2,"official_source_files":[{"year":2022,"sha256":"a"*64}],
            "out_of_year_metrics":[{"year":2022,"model":"linear regression","metric":"MAE","score":0.05,"n_test":2}]}

def test_identical_snapshot_accepted():
    current=fixture()
    expected={k:v for k,v in current.items() if k!="official_source_files"}
    m.validate(current,expected)

def test_accuracy_drift_is_rejected():
    current=fixture()
    expected={k:v for k,v in current.items() if k!="official_source_files"}
    expected["out_of_year_metrics"]=[{**expected["out_of_year_metrics"][0],"score":0.07}]
    with pytest.raises(AssertionError,match="Metric drift"):
        m.validate(current,expected)

def test_cohort_change_is_rejected():
    current=fixture()
    expected={k:v for k,v in current.items() if k!="official_source_files"}
    expected["year_counts"][0]["included"]=3
    with pytest.raises(AssertionError,match="counts changed"):
        m.validate(current,expected)

def test_source_hash_change_is_rejected():
    current=fixture()
    expected={k:v for k,v in current.items() if k!="official_source_files"}
    expected["official_source_sha256"]={"2022":"b"*64}
    with pytest.raises(AssertionError,match="source bytes changed"):
        m.validate(current,expected)
