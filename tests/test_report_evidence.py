"""Only synthetic data in unit fixtures. This is not a source of FEC measurements."""
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_report_figures import (
    check_evidence_registry, yearly_mae_rows, validated_state_year_rows, run
)

def baseline():
    pinned=json.loads((ROOT/"data/sources/expected_analysis.json").read_text())
    sources=json.loads((ROOT/"data/sources/report_evidence.json").read_text())
    return pinned,sources


def synthetic_error_summary():
    # Test-fixture values chosen to match the published checksum baseline.
    # This function NEVER downloads or measures actual FEC results.
    return {"years":[
        {"year":2018,"n":241,"MAE":{"identity":.062852,"linear":.044157,"mean":.132673}},
        {"year":2020,"n":237,"MAE":{"identity":.078389,"linear":.054936,"mean":.139806}},
        {"year":2022,"n":238,"MAE":{"identity":.075042,"linear":.050168,"mean":.140875}},
    ]}


def synthetic_state_summary():
    return {
      "all_fec_report_groups":1756,
      "selected_total":916,
      "held_out_by_year":[
        {"year":2018,"n_districts":241,"selected_states":37,
         "states_with_n_ge_5":16,"states_with_n_lt_5":21,
         "district_weighted_linear_mae":.044157,
         "equal_selected_state_linear_mae":.049405,
         "district_weighted_signed_pred_minus_actual":.0077,
         "district_weighted_general_minus_primary":-.00282},
        {"year":2020,"n_districts":237,"selected_states":37,
         "states_with_n_ge_5":16,"states_with_n_lt_5":21,
         "district_weighted_linear_mae":.054936,
         "equal_selected_state_linear_mae":.054932,
         "district_weighted_signed_pred_minus_actual":-.04575,
         "district_weighted_general_minus_primary":.06139},
        {"year":2022,"n_districts":238,"selected_states":36,
         "states_with_n_ge_5":17,"states_with_n_lt_5":19,
         "district_weighted_linear_mae":.050168,
         "equal_selected_state_linear_mae":.052653,
         "district_weighted_signed_pred_minus_actual":.02998,
         "district_weighted_general_minus_primary":-.02255},
      ],
    }


def test_registry_maps_all_3_questions_and_sources():
    pinned,reg=baseline()
    check_evidence_registry(reg,pinned)
    assert {entry["rq"] for entry in reg["evidence"]}>={"RQ1","RQ2","RQ3"}
    assert sum(entry["status"]=="verified_ci_unmerged_pr" for entry in reg["evidence"])==1


def test_fec_original_sha_cannot_be_changed_silently():
    frozen,registry=baseline()
    registry["official_xlsx_sha256"]["2022"]="0"*64
    with pytest.raises(AssertionError,match="SHA-256"):
        check_evidence_registry(registry,frozen)


def test_figure_with_no_source_rejected():
    frozen,registry=baseline()
    registry["report_figure_budget"][0]["evidence_ids"]=["EV-NONE"]
    with pytest.raises(AssertionError,match="lacks an evidence"):
        check_evidence_registry(registry,frozen)


def test_incomplete_evidence_provenance_rejected():
    frozen,registry=baseline()
    del registry["evidence"][0]["ci"]
    with pytest.raises(AssertionError,match="lacks provenance"):
        check_evidence_registry(registry,frozen)


def test_frozen_yearly_2018_2020_2022_crosscheck():
    frozen,_=baseline()
    df=yearly_mae_rows(synthetic_error_summary(),frozen)
    assert list(df.n_test)==[241,237,238]
    assert (df.linear_gain_pp>0).all()
    bad=synthetic_error_summary()
    bad["years"][2]["MAE"]["linear"]+=.005
    with pytest.raises(AssertionError,match="pinned baseline"):
        yearly_mae_rows(bad,frozen)


def test_no_future_or_unexpected_years_accepted():
    frozen,_=baseline()
    bad=synthetic_error_summary()
    bad["years"].append({"year":2024,"n":200,"MAE":{"identity":.1,"linear":.02,"mean":.15}})
    with pytest.raises(AssertionError,match="no extra years"):
        yearly_mae_rows(bad,frozen)


def test_state_year_rejects_relabelled_sample():
    frozen,_=baseline()
    state=synthetic_state_summary()
    state["held_out_by_year"][2]["n_districts"]=921
    with pytest.raises(AssertionError,match="test n"):
        validated_state_year_rows(state,frozen)


def test_builds_only_verified_mae_without_unmerged_state_data(tmp_path):
    frozen,registry=baseline()
    result=run(registry,frozen,synthetic_error_summary(),tmp_path)
    assert result["state_year_status"]=="not_supplied_unmerged_dependency"
    assert (tmp_path/"report_f1_yearly_mae.png").exists()
    assert (tmp_path/"report_f1_yearly_mae.svg").exists()
    assert (tmp_path/"report_t1_yearly_mae.csv").exists()
    assert not (tmp_path/"report_t2_state_year_weights.csv").exists()


def test_state_tables_require_validated_state_figure_source(tmp_path):
    frozen,registry=baseline()
    figure=tmp_path/"source.svg"
    figure.write_text("<svg></svg>")
    result=run(registry,frozen,synthetic_error_summary(),tmp_path/"out",
               state_summary=synthetic_state_summary(),state_figure=figure)
    assert result["state_year_status"]=="validated_FEC_CI_PR73_source"
    assert (tmp_path/"out"/"report_t2_state_year_weights.csv").exists()
    assert (tmp_path/"out"/"report_f2_state_coverage.svg").exists()


def test_state_figure_without_state_summary_rejected(tmp_path):
    frozen,registry=baseline()
    with pytest.raises(ValueError,match="without its state"):
        run(registry,frozen,synthetic_error_summary(),tmp_path,
            state_figure=tmp_path/"foo.svg")
