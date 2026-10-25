"""State-by-year coverage and out-of-time FEC House diagnostics (Issue #57).

The FEC workbooks are POST-ELECTION publications. State/Year comparisons are
conditional descriptive summaries of a selected cohort, not US-wide estimates.
Never use General-year outcomes as predictors or tune on held-out years.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_error_structure import heldout
from normalize_fec import NONVOTING_DELEGATE_JURISDICTIONS

KEY = ["year", "state", "district"]
FROZEN = {2016: (200, 238), 2018: (241, 197),
          2020: (237, 204), 2022: (238, 201)}
MIN_VISIBLE_N = 5
YEAR_TESTS = (2018, 2020, 2022)
VOTING_STATES = frozenset(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD "
    "MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC "
    "SD TN TX UT VT VA WA WV WI WY".split()
)


def _normalized_keys(df: pd.DataFrame, label: str) -> pd.DataFrame:
    if not set(KEY).issubset(df.columns):
        raise ValueError(f"{label} requires {KEY}")
    data = df.copy()
    data["year"] = pd.to_numeric(data["year"], errors="raise").astype(int)
    data["state"] = data["state"].astype("string").str.strip().str.upper()
    data["district"] = data["district"].astype("string").str.zfill(2)
    if data[KEY].isna().any().any() or data.duplicated(KEY).any():
        raise AssertionError(f"{label}: null/duplicate election keys")
    return data


def summarize_coverage(selected: pd.DataFrame, excluded: pd.DataFrame):
    """Count every source report group; split out non-voting jurisdictions."""
    sel = _normalized_keys(selected, "selected")
    exc = _normalized_keys(excluded, "excluded")
    if not (set(sel.state.dropna()) | set(exc.state.dropna())).issubset(
        VOTING_STATES | NONVOTING_DELEGATE_JURISDICTIONS
    ):
        raise ValueError("Unknown FEC jurisdiction; do not count as a voting state")
    if set(map(tuple,sel[KEY].itertuples(index=False,name=None))) & set(
        map(tuple,exc[KEY].itertuples(index=False,name=None))):
        raise AssertionError("A FEC group is simultaneously included and excluded")
    sel["_included"] = 1
    exc["_included"] = 0
    raw = pd.concat([sel[KEY + ["_included"]],
                     exc[KEY + ["_included"]]], ignore_index=True)
    raw["population"] = np.where(
        raw.state.isin(NONVOTING_DELEGATE_JURISDICTIONS),
        "nonvoting-delegate", "50-state-voting-House")
    if (raw.loc[raw._included.eq(1), "population"] != "50-state-voting-House").any():
        raise AssertionError("Selected nonvoting delegates")
    groups = (raw.groupby(["population","year","state"],as_index=False)
              .agg(report_groups=("_included","size"),selected=("_included","sum")))
    groups["excluded"] = groups.report_groups - groups.selected
    groups["selected_fraction"] = groups.selected / groups.report_groups
    reason = exc.copy()
    if "reason" not in reason:
        raise ValueError("Exclusion reasons are required")
    reason["population"] = np.where(reason.state.isin(NONVOTING_DELEGATE_JURISDICTIONS),
                                    "nonvoting-delegate", "50-state-voting-House")
    reasons = (reason.groupby(["population","year","state","reason"],as_index=False)
               .size().rename(columns={"size":"n_excluded"}))
    checks = reasons.groupby(["population","year","state"])["n_excluded"].sum()
    merged = groups.set_index(["population","year","state"])
    if not (merged["excluded"] == checks.reindex(merged.index,fill_value=0)).all():
        raise AssertionError("State/year exclusions are not fully accounted for")
    return groups.sort_values(["population","year","state"]).reset_index(drop=True), reasons


def summarize_predictions(predictions: pd.DataFrame):
    """Calculate descriptive state-year comparisons from unchanged held-out predictions."""
    if predictions.duplicated(KEY).any():
        raise AssertionError("Duplicate predictions")
    required = {"primary_rep_share","general_rep_share","linear_signed",
                "linear_abs","identity_abs","linear_pred","identity_pred"}
    if not required.issubset(predictions.columns):
        raise ValueError("Missing held-out prediction columns")
    if not set(predictions.year.unique()).issubset(set(YEAR_TESTS)):
        raise ValueError("Unexpected test years")
    if predictions[["linear_abs","identity_abs"]].isna().any().any():
        raise ValueError("Missing prediction errors")
    if predictions.state.isin(NONVOTING_DELEGATE_JURISDICTIONS).any():
        raise AssertionError("Delegates in House predictions")
    data = predictions.copy()
    data["general_minus_primary"] = data.general_rep_share - data.primary_rep_share
    states = (data.groupby(["year","state"],as_index=False).agg(
        n=("district","size"),
        primary_r_share_mean=("primary_rep_share","mean"),
        general_r_share_mean=("general_rep_share","mean"),
        general_minus_primary_mean=("general_minus_primary","mean"),
        linear_mae=("linear_abs","mean"),
        primary_carryover_mae=("identity_abs","mean"),
        linear_signed_pred_minus_actual=("linear_signed","mean"),
    ))
    states["mae_gain_carryover_minus_linear"] = (
        states.primary_carryover_mae - states.linear_mae)
    states["descriptive_n_ge_5"] = states.n >= MIN_VISIBLE_N
    # Do not average percentages by state and then call it a national vote share:
    # this is a district-weighted/selected-state-equal descriptive statistic.
    years = []
    for year, group in data.groupby("year",sort=True):
        by_state = states[states.year.eq(year)]
        visible = by_state[by_state.descriptive_n_ge_5]
        years.append({
            "year":int(year), "n_districts":int(len(group)),
            "selected_states":int(len(by_state)),
            "states_with_n_ge_5":int(len(visible)),
            "states_with_n_lt_5":int((~by_state.descriptive_n_ge_5).sum()),
            "district_weighted_linear_mae":float(group.linear_abs.mean()),
            "equal_selected_state_linear_mae":float(by_state.linear_mae.mean()),
            "equal_selected_state_n_ge_5_linear_mae":(
                float(visible.linear_mae.mean()) if len(visible) else None),
            "district_weighted_signed_pred_minus_actual":float(group.linear_signed.mean()),
            "equal_selected_state_signed_pred_minus_actual":float(
                by_state.linear_signed_pred_minus_actual.mean()),
            "district_weighted_primary_r_share":float(group.primary_rep_share.mean()),
            "district_weighted_general_r_share":float(group.general_rep_share.mean()),
            "equal_selected_state_primary_r_share":float(by_state.primary_r_share_mean.mean()),
            "equal_selected_state_general_r_share":float(by_state.general_r_share_mean.mean()),
            "district_weighted_general_minus_primary":float(group.general_minus_primary.mean()),
            "n_linear_better_than_carryover":int((group.linear_abs < group.identity_abs).sum()),
            "n_linear_worse_than_carryover":int((group.linear_abs > group.identity_abs).sum()),
        })
    return states.sort_values(["year","state"]).reset_index(drop=True), years


def check_frozen(groups: pd.DataFrame, predictions: pd.DataFrame, fit: list[dict]) -> None:
    for year, (included,excluded) in FROZEN.items():
        rows=groups[groups.year.eq(year)]
        if int(rows.selected.sum()) != included or int(rows.excluded.sum()) != excluded:
            raise AssertionError(f"{year} frozen FEC cohort changed")
    if groups.report_groups.sum() != 1756 or groups.selected.sum() != 916:
        raise AssertionError("FEC 1756 / selected 916 frozen cohort changed")
    if set(groups.loc[groups.population.eq("50-state-voting-House"),"state"]) != VOTING_STATES:
        raise AssertionError("FEC expected 50 voting states in report groups")
    for year in YEAR_TESTS:
        x=predictions[predictions.year.eq(year)]
        if len(x)!=FROZEN[year][0]:
            raise AssertionError("Prediction cohort changed")
    for record in fit:
        year=record["test_year"]
        if record["train_max_year"] >= year:
            raise AssertionError("Time leak: training year >= test year")


def charts(coverage: pd.DataFrame, metrics: pd.DataFrame, output: Path) -> None:
    voting=coverage[coverage.population.eq("50-state-voting-House")]
    four_years=voting.groupby("state",as_index=False).agg(
        report_groups=("report_groups","sum"),selected=("selected","sum"))
    four_years["fraction"]=four_years.selected/four_years.report_groups
    fig,ax=plt.subplots(figsize=(9,4.7))
    ax.scatter(four_years.report_groups,four_years.fraction*100,
               s=30+four_years.report_groups*1.5,alpha=.7)
    zeros = sorted(four_years.loc[four_years.selected.eq(0),"state"].tolist())
    fig.text(.06,.015,"No included records: " + ", ".join(zeros),fontsize=7)
    ax.set_xlabel("FEC report groups in 2016–2022 (4 elections)")
    ax.set_ylabel("Included in fixed 916-record cohort (%)")
    ax.set_title("Selection varies by state; observations are not a national sample")
    ax.set_ylim(-4,104);ax.grid(alpha=.2)
    fig.tight_layout(rect=(0,.065,1,1))
    fig.savefig(output/"fig_state_coverage.png",dpi=170)
    fig.savefig(output/"fig_state_coverage.svg")
    plt.close(fig)

    fig,ax=plt.subplots(figsize=(8.5,5))
    for year in YEAR_TESTS:
        sub=metrics[metrics.year.eq(year) & metrics.descriptive_n_ge_5]
        ax.scatter(sub.primary_r_share_mean*100,
                   sub.linear_signed_pred_minus_actual*100,
                   s=20+sub.n*6,alpha=.68,label=f"{year} (states n>=5: {len(sub)})")
    ax.axhline(0,color="black",lw=.9,alpha=.7)
    ax.set(xlabel="Mean Primary R two-party vote share in selected districts (%)",
           ylabel="Mean linear prediction minus actual General R share (pp)",
           title="State/year model bias in sufficiently sampled selected states")
    ax.grid(alpha=.18);ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output/"fig_state_year_bias.png",dpi=170)
    fig.savefig(output/"fig_state_year_bias.svg")
    plt.close(fig)


def run(selected: pd.DataFrame, excluded: pd.DataFrame, assert_baseline=False):
    groups,reasons=summarize_coverage(selected,excluded)
    pred,fit=heldout(selected)
    state_metrics,year_metrics=summarize_predictions(pred)
    if assert_baseline:
        check_frozen(groups,pred,fit)
    annual=groups.groupby(["population","year"],as_index=False).agg(
        report_groups=("report_groups","sum"),
        selected=("selected","sum"),
        excluded=("excluded","sum"))
    annual["selected_fraction"] = annual.selected / annual.report_groups
    full_state=groups[groups.population.eq("50-state-voting-House")]
    overall=full_state.groupby("state",as_index=False).agg(
        report_groups=("report_groups","sum"),selected=("selected","sum"))
    overall["selected_fraction"]=overall.selected/overall.report_groups
    result={
        "description":"Selected-cohort, retrospective, descriptive analysis; not all US House seats",
        "selection_by_year":annual.to_dict(orient="records"),
        "held_out_by_year":year_metrics,
        "four_year_voting_states":int(len(overall)),
        "zero_selected_states":overall.loc[overall.selected.eq(0),"state"].tolist(),
        "selected_total":int(groups.selected.sum()),
        "all_fec_report_groups":int(groups.report_groups.sum()),
        "min_n_for_state_comparisons":MIN_VISIBLE_N,
        "general_used_as_predictor":False,
        "official_winners_inferred_from_two_party_majority":False,
        "interpretation_limits":[
          "FEC primary-vote figures here come from post-election published workbooks",
          "House districts and district boundaries are not assumed comparable across elections",
          "State equal-weight is an average of observed selected states, not national vote weighting",
          "Small-state n<5 groups remain in complete tables but not the state-bias figure",
          "Many states are excluded under conservative primary-election rules",
          "2022 model and cohort previously explored; no prospective causal claim",
        ],
    }
    return groups,reasons,state_metrics, result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("data/processed/elections.csv"))
    p.add_argument("--exclusions",type=Path,default=Path("data/processed/exclusions.csv"))
    p.add_argument("--output-dir",type=Path,default=Path("data/processed/state_year"))
    p.add_argument("--assert-baseline",action="store_true")
    args=p.parse_args()
    selected=pd.read_csv(args.input,dtype={"state":str,"district":str})
    excluded=pd.read_csv(args.exclusions,dtype={"state":str,"district":str})
    cover,reasons,metrics,summary=run(selected,excluded,args.assert_baseline)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    cover.to_csv(args.output_dir/"state_year_coverage.csv",index=False)
    reasons.to_csv(args.output_dir/"state_year_exclusion_reasons.csv",index=False)
    metrics.to_csv(args.output_dir/"state_year_error_metrics.csv",index=False)
    charts(cover,metrics,args.output_dir)
    (args.output_dir/"state_year_summary.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("STATE_YEAR_SUMMARY_START")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print("STATE_YEAR_SUMMARY_END")


if __name__=="__main__":
    main()
