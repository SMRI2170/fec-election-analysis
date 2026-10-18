"""Compose publication figures from already-validated FEC analyses (Issue #67).

Never fabricate missing state/year figures: the state analysis remains in PR #73
until reviewed and merged. This script checks all supported numerical claims
against the pinned FEC cohort before building manuscript-ready charts/tables.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

YEARS = (2018, 2020, 2022)
SOURCE_TYPES = {"verified_main", "verified_ci_unmerged_pr", "partially_verified_main"}


def check_evidence_registry(registry: dict, frozen: dict) -> None:
    if registry.get("schema_version") != 1:
        raise AssertionError("Unknown report evidence schema")
    if registry.get("official_xlsx_sha256") != frozen.get("official_source_sha256"):
        raise AssertionError("Official FEC workbook SHA-256 differs from pinned baseline")
    cohort = registry.get("frozen_cohort", {})
    if cohort.get("selected") != frozen["total_included"]:
        raise AssertionError("916 fixed report cohort changed")
    pinned_counts = {str(item["year"]): item["included"] for item in frozen["year_counts"]}
    if cohort.get("selected_by_year") != pinned_counts:
        raise AssertionError("Yearly FEC sample selection disagrees with frozen baseline")
    evidence = registry.get("evidence", [])
    ids = [entry.get("id") for entry in evidence]
    if len(ids) != len(set(ids)) or not ids:
        raise AssertionError("Missing/duplicate evidence identifiers")
    for entry in evidence:
        required = ("rq", "status", "unit", "n", "script_paths", "source_docs", "ci", "important_limit")
        if not all(entry.get(k) for k in required):
            raise AssertionError(f"Evidence {entry.get('id')} lacks provenance or limitations")
        if entry["status"] not in SOURCE_TYPES:
            raise AssertionError(f"Unrecognized or overstated evidence status: {entry['status']}")
        if entry["n"] <= 0:
            raise AssertionError("Evidence count must be positive")
        if entry["status"] == "verified_ci_unmerged_pr" and not entry.get("pr"):
            raise AssertionError("Unmerged experimental results need a PR link")
    for figure in registry.get("report_figure_budget", []):
        if not set(figure["evidence_ids"]).issubset(set(ids)):
            raise AssertionError("A proposed figure lacks an evidence source")
    rqs = {x.get("rq") for x in evidence}
    if not {"RQ1", "RQ2", "RQ3"}.issubset(rqs):
        raise AssertionError("RQ1/RQ2/RQ3 must have evidence")


def yearly_mae_rows(error_summary: dict, frozen: dict) -> pd.DataFrame:
    years = error_summary.get("years", [])
    seen = [int(x["year"]) for x in years]
    if sorted(seen) != list(YEARS) or len(seen) != 3:
        raise AssertionError("Yearly error structure 2018/2020/2022 required, no extra years")
    fixed = {x["year"]: x for x in frozen["out_of_year_metrics"]
             if x["model"] == "linear regression" and x["metric"] == "MAE"}
    rows=[]
    for r in sorted(years, key=lambda x:x["year"]):
        y=int(r["year"])
        n=int(r["n"])
        if n != int(fixed[y]["n_test"]):
            raise AssertionError(f"{y} held-out sample size differs from official reference")
        carry=float(r["MAE"]["identity"])
        linear=float(r["MAE"]["linear"])
        constant=float(r["MAE"]["mean"])
        if abs(linear-float(fixed[y]["score"])) > 0.00012:
            raise AssertionError(f"{y} calculated MAE differs from pinned baseline")
        if any(not 0<=v<=1 for v in (carry,linear,constant)):
            raise AssertionError("Invalid MAE fraction")
        rows.append(dict(test_year=y,n_test=n,constant_mae=constant,
                         primary_carryover_mae=carry,linear_mae=linear,
                         linear_gain_pp=(carry-linear)*100))
    return pd.DataFrame(rows)


def validated_state_year_rows(summary: dict, frozen: dict) -> pd.DataFrame:
    if summary.get("all_fec_report_groups") != 1756 or summary.get("selected_total") != 916:
        raise AssertionError("State/year analysis differs from official FEC source group or cohort")
    if sorted(x["year"] for x in summary.get("held_out_by_year", [])) != list(YEARS):
        raise AssertionError("State/year analysis must include held-out years")
    rows=[]
    for item in summary["held_out_by_year"]:
        y=int(item["year"])
        n=int(item["n_districts"])
        expected = next(x["included"] for x in frozen["year_counts"] if x["year"]==y)
        if n!=expected:
            raise AssertionError("State-year test n does not equal frozen cohort")
        if int(item["selected_states"]) < int(item["states_with_n_ge_5"]):
            raise AssertionError("n>=5 states cannot exceed selected states")
        if int(item["states_with_n_ge_5"])+int(item["states_with_n_lt_5"])!=int(item["selected_states"]):
            raise AssertionError("Small-state counts do not add up")
        rows.append(dict(test_year=y,n_test=n,
                         n_states=int(item["selected_states"]),
                         n_states_ge_5=int(item["states_with_n_ge_5"]),
                         district_weighted_mae_pp=float(item["district_weighted_linear_mae"])*100,
                         selected_state_equal_mae_pp=float(item["equal_selected_state_linear_mae"])*100,
                         signed_bias_pp=float(item["district_weighted_signed_pred_minus_actual"])*100,
                         general_minus_primary_pp=float(item["district_weighted_general_minus_primary"])*100))
    return pd.DataFrame(rows).sort_values("test_year")


def render_mae_plot(table: pd.DataFrame, dest: Path) -> None:
    fig,ax=plt.subplots(figsize=(7.2,4.3))
    x=range(len(table))
    ax.plot(x,table.primary_carryover_mae*100,marker="o",lw=1.8,
            label="Primary share carried over")
    ax.plot(x,table.linear_mae*100,marker="s",lw=1.8,
            label="Chronological linear regression")
    ax.set_xticks(list(x),[str(y) for y in table.test_year])
    ax.set_ylabel("General R two-party share MAE (percentage points)")
    ax.set_xlabel("Held-out general election year")
    ax.set_title("One-feature regression vs an untrained baseline")
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=8)
    ax.grid(alpha=.2)
    fig.tight_layout()
    for ext in (".png",".svg"):
        fig.savefig(dest/f"report_f1_yearly_mae{ext}",dpi=170)
    plt.close(fig)


def run(registry: dict, frozen: dict, error_summary: dict,
        output_dir: Path, state_summary: dict|None = None,
        state_figure: Path|None = None) -> dict:
    check_evidence_registry(registry,frozen)
    output_dir.mkdir(parents=True,exist_ok=True)
    table=yearly_mae_rows(error_summary,frozen)
    table.to_csv(output_dir/"report_t1_yearly_mae.csv",index=False)
    render_mae_plot(table,output_dir)
    result={"source":"FEC official workbook SHA256 and previously validated error-structure JSON",
            "cohort_selected":916,"yearly_n":table.n_test.tolist(),
            "report_f1_status":"generated_from_validated_fec_error_summary",
            "state_year_status":"not_supplied_unmerged_dependency",
            "prediction_time_operationally_verified":False}
    if state_summary is not None:
        state=validated_state_year_rows(state_summary,frozen)
        state.to_csv(output_dir/"report_t2_state_year_weights.csv",index=False)
        result["state_year_status"]="validated_FEC_CI_PR73_source"
        result["state_year_rows"]=len(state)
        if state_figure is not None:
            if not state_figure.exists() or state_figure.suffix.lower()!=".svg":
                raise FileNotFoundError("State coverage SVG from PR #73 is unavailable")
            shutil.copyfile(state_figure,output_dir/"report_f2_state_coverage.svg")
            result["report_f2_status"]="copied_from_state_year_pipeline"
    elif state_figure is not None:
        raise ValueError("Cannot reuse state figure without its state/year summary JSON")
    (output_dir/"report_figure_manifest.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--registry",type=Path,default=Path("data/sources/report_evidence.json"))
    p.add_argument("--pinned",type=Path,default=Path("data/sources/expected_analysis.json"))
    p.add_argument("--error-summary",type=Path,default=Path("data/processed/error-structure-summary.json"))
    p.add_argument("--state-summary",type=Path,default=None)
    p.add_argument("--state-figure",type=Path,default=None)
    p.add_argument("--output-dir",type=Path,default=Path("data/processed/report_figures"))
    a=p.parse_args()
    load=lambda path:json.loads(path.read_text(encoding="utf-8"))
    result=run(load(a.registry),load(a.pinned),load(a.error_summary),a.output_dir,
               state_summary=load(a.state_summary) if a.state_summary else None,
               state_figure=a.state_figure)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
