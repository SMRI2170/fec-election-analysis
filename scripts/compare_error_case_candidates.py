"""Exploratory comparison: 2022 top-five forecast misses vs other test districts.

The top five are selected AFTER observing the holdout prediction errors.
Differences in candidate counts or primary competitiveness are descriptive,
NOT pre-specified tests and NOT evidence of causes. No training changes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from source_reconcile import read_house, vote

KEY = ("year", "state", "district")
EXPECTED_TOP_FIVE = (("RI", "02"), ("OH", "15"), ("OH", "09"),
                     ("MI", "03"), ("NH", "01"))


def candidate_features(errors: pd.DataFrame, raw_2022: pd.DataFrame, n_top: int = 5) -> pd.DataFrame:
    if n_top < 1 or n_top >= len(errors):
        raise ValueError("Comparison requires nonempty selected and reference groups")
    for field in ("year", "state", "district", "abs_linear_error"):
        if field not in errors:
            raise ValueError(f"Missing required error_report field: {field}")
    if not (errors["year"] == 2022).all():
        raise ValueError("The full reference and top group must be the 2022 holdout")
    ordered = errors.sort_values(["abs_linear_error", "state", "district"],
                                 ascending=[False, True, True], kind="stable").reset_index(drop=True)
    if ordered.duplicated(["year", "state", "district"]).any():
        raise AssertionError("Repeated 2022 test district in error report")
    groups = {(str(s), str(d)): df for (s,d),df in
              raw_2022.groupby(["_state", "_district"])}
    records = []
    for rank, row in enumerate(ordered.itertuples(index=False), start=1):
        state, district = str(row.state), str(row.district).zfill(2)
        source = groups.get((state,district))
        if source is None:
            raise AssertionError(f"Original FEC 2022 district missing: {state}-{district}")
        result = {
            "year":2022,"state":state,"district":district,"error_rank":rank,
            "group":"top5_selected_posthoc" if rank <= n_top else "other_2022_test",
            "abs_linear_error":float(row.abs_linear_error),
            "primary_rep_share":float(row.primary_rep_share),
            "general_rep_share":float(row.general_rep_share),
            "primary_rule_error":bool(row.primary_rule_error),
            "logistic_error":bool(row.logistic_error),
        }
        for party, prefix in (("R","rep"), ("D","dem")):
            candidates = source[source["_candidate"] & source["_party"].eq(party)]
            valid = [vote(v) for v in candidates["PRIMARY VOTES"]]
            numeric = [v for v in valid if v is not None and v > 0]
            result[f"{prefix}_primary_candidate_rows"] = len(candidates)
            result[f"{prefix}_positive_primary_candidates"] = len(numeric)
            result[f"{prefix}_contested_primary"] = len(numeric) >= 2
            result[f"{prefix}_top_named_primary_share"] = (
                max(numeric)/sum(numeric) if numeric else None
            )
        result["either_party_contested_primary"] = (
            result["rep_contested_primary"] or result["dem_contested_primary"])
        records.append(result)
    return pd.DataFrame(records)


def summarize(features: pd.DataFrame, expected_test_rows: int | None = None) -> dict:
    if expected_test_rows is not None and len(features) != expected_test_rows:
        raise AssertionError("The fixed 2022 test cohort changed")
    a = features[features["group"] == "top5_selected_posthoc"]
    b = features[features["group"] == "other_2022_test"]
    if len(a) != 5 or b.empty:
        raise AssertionError("Expected five selected errors and a nonempty reference group")
    if expected_test_rows is not None:
        labels = tuple((row.state, row.district) for row in a.itertuples())
        if labels != EXPECTED_TOP_FIVE:
            raise AssertionError(f"Top-five FEC record identity changed: {labels}")
    outcome = {
        "study_year":2022,
        "selection":"retrospective top five by absolute linear prediction error",
        "other_group":"remaining 2022 holdout districts",
        "posthoc_selection_warning":True,
        "causal_effect_claimed":False,
        "p_value_reported":False,
        "candidate_counts_meaning":"FEC explicitly party-coded candidate rows with numeric positive Primary votes, not number of unique candidates across all parties",
        "groups":{},
    }
    for name, group in (("top5_selected_posthoc",a),("other_2022_test",b)):
        outcome["groups"][name] = {
            "districts":len(group),
            "median_abs_linear_error":round(float(group["abs_linear_error"].median()),6),
            "mean_abs_linear_error":round(float(group["abs_linear_error"].mean()),6),
            "mean_positive_rep_primary_candidates":round(float(group["rep_positive_primary_candidates"].mean()),6),
            "mean_positive_dem_primary_candidates":round(float(group["dem_positive_primary_candidates"].mean()),6),
            "either_party_contested_districts":int(group["either_party_contested_primary"].sum()),
            "either_party_contested_fraction":round(float(group["either_party_contested_primary"].mean()),6),
            "primary_majority_rule_misses":int(group["primary_rule_error"].sum()),
        }
    return outcome


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--errors",type=Path,default=Path("data/processed/errors_2022.csv"))
    p.add_argument("--fec-2022",type=Path,default=Path("data/raw/federalelections2022.xlsx"))
    p.add_argument("--processed-dir",type=Path,default=Path("data/processed"))
    p.add_argument("--assert-baseline",action="store_true")
    args=p.parse_args()
    errors=pd.read_csv(args.errors,dtype={"district":str,"state":str})
    _,raw=read_house(args.fec_2022)
    features=candidate_features(errors,raw)
    results=summarize(features,expected_test_rows=238 if args.assert_baseline else None)
    args.processed_dir.mkdir(parents=True,exist_ok=True)
    (args.processed_dir/"error-case-feature-comparison.csv").write_text(
        features.to_csv(index=False),encoding="utf-8")
    (args.processed_dir/"error-case-feature-summary.json").write_text(
        json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
