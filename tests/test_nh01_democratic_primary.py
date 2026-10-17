import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("nh01_primary",ROOT/"scripts"/"verify_nh01_democratic_primary.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def original():
    return json.loads((ROOT/"data/sources/nh01_2022_democratic_primary.json").read_text(encoding="utf-8"))

def test_official_nh_democratic_primary_totals():
    r=m.audit_official_primary(original())
    assert r["official_pappas_primary_votes"]==41990
    assert r["official_named_writeins"]==226
    assert r["official_scattered_writeins"]==152
    assert r["official_democratic_primary_total"]==42368
    assert r["independent_democratic_primary_reconciled"] is False
    assert r["independent_republican_primary_reconciled"] is False
    assert r["independent_general_reconciled"] is False

def test_named_writein_changes_fail():
    x=original()
    x["reported_totals"]["write_in_named"]["Karoline Leavitt"]+=1
    with pytest.raises(AssertionError,match="write-in totals"):
        m.audit_official_primary(x)

def test_scattered_writein_changes_fail():
    x=original()
    x["reported_totals"]["scattered_write_in"]+=1
    with pytest.raises(AssertionError,match="Expected official NH"):
        m.audit_official_primary(x)

def test_cannot_upgrade_general_or_r_primary_flag():
    x=original()
    x["verification_scope"]["republican_primary"]=True
    with pytest.raises(AssertionError,match="Democratic-only"):
        m.audit_official_primary(x)

def test_bad_fec_row_fails(tmp_path):
    x=m.audit_official_primary(original())
    path=tmp_path/"elections.csv"
    path.write_text("year,state,district,primary_dem_votes\n2022,NH,01,42367\n",encoding="utf-8")
    with pytest.raises(AssertionError,match="NH official state D primary vs FEC mismatch"):
        m.compare_fec_csv(x,path)

def test_good_fec_row_marks_democratic_only(tmp_path):
    x=m.audit_official_primary(original())
    path=tmp_path/"elections.csv"
    path.write_text("year,state,district,primary_dem_votes\n2022,NH,01,42368\n",encoding="utf-8")
    m.compare_fec_csv(x,path)
    assert x["independent_democratic_primary_reconciled"] is True
    assert not x["independent_general_reconciled"]
