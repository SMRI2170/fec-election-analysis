"""Baseline evaluation of verified normalized election data.

Real FEC data are not included in this repository.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, mean_absolute_error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fec_analysis.core import prepare_elections


def evaluate(data: pd.DataFrame, test_year: int, chamber: str = "House") -> pd.DataFrame:
    df = prepare_elections(data)
    df = df[df["chamber"] == chamber].copy()
    if df.empty:
        raise ValueError(f"No rows for {chamber}")
    train = df[df["year"] < test_year]
    test = df[df["year"] == test_year]
    if train.empty or test.empty:
        raise ValueError("Train/test is empty: check available years and test year")
    Xtrain = train[["primary_rep_share"]]
    Xtest = test[["primary_rep_share"]]

    results: list[dict[str, object]] = []
    for name, model in [
        ("mean-share baseline", DummyRegressor(strategy="mean")),
        ("linear regression", LinearRegression()),
    ]:
        model.fit(Xtrain, train["general_rep_share"])
        predicted = model.predict(Xtest).clip(0, 1)
        results.append({"task": "share", "model": name, "metric": "MAE", "score": mean_absolute_error(test["general_rep_share"], predicted), "n_train": len(train), "n_test": len(test)})

    train_clf = train[~train["general_tie"]]
    test_clf = test[~test["general_tie"]]
    if train_clf.empty or test_clf.empty:
        raise ValueError("Non-tied classification train/test is empty")
    if train_clf["general_rep_win"].nunique() < 2:
        raise ValueError("Training set needs both winner classes")
    for name, model in [
        ("majority-class baseline", DummyClassifier(strategy="prior")),
        ("logistic regression", LogisticRegression(random_state=0, max_iter=1000)),
    ]:
        model.fit(train_clf[["primary_rep_share"]], train_clf["general_rep_win"])
        predicted = model.predict(test_clf[["primary_rep_share"]])
        prob = model.predict_proba(test_clf[["primary_rep_share"]])[:, list(model.classes_).index(1)]
        results.append({"task": "winner", "model": name, "metric": "accuracy", "score": accuracy_score(test_clf["general_rep_win"], predicted), "n_train": len(train_clf), "n_test": len(test_clf)})
        results.append({"task": "winner", "model": name, "metric": "Brier", "score": brier_score_loss(test_clf["general_rep_win"], prob), "n_train": len(train_clf), "n_test": len(test_clf)})
    return pd.DataFrame(results)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate primary/general relationships")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--test-year", type=int, default=2022)
    parser.add_argument("--chamber", choices=["House", "Senate"], default="House")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    scores = evaluate(pd.read_csv(args.input, dtype={"state": str, "district": str}), args.test_year, args.chamber)
    print(scores.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        scores.to_csv(args.output, index=False)
        print("Saved:", args.output)


if __name__ == "__main__":
    main()
