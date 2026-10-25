"""The frozen evaluation plan for the 2024 out-of-year test (#53).

This module holds everything that has to be fixed **before** the 2024 result
can be seen:

* the frozen configuration (``configs/frozen-2024-evaluation.json``),
* the machine-readable copy of the same configuration that is embedded in the
  research note, so that the note and the configuration cannot drift apart,
* the checks that the freeze commit and the frozen source catalogue are still
  intact.

The module contains **no fitting and no scoring of the 2024 data**. The actual
evaluation is [#54](https://github.com/SMRI2170/fec-election-analysis/issues/54)
and runs from this configuration only.

The 2024 source was **not published** when this plan was frozen. That is the
strongest possible form of pre-registration: the plan cannot have been
influenced by the result, because the result did not exist yet.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO / "configs" / "frozen-2024-evaluation.json"
NOTE_PATH = REPO / "docs" / "2024-frozen-evaluation-protocol.md"
SOURCE_CATALOG_PATH = REPO / "data" / "sources" / "fec_publications.json"

#: The heading of the machine-readable block inside the research note.
BLOCK_HEADING = "固定設定（機械可読）"

#: The phases of the protocol. ``tuning`` is the only phase in which a
#: hyperparameter could ever be chosen, and it may not see a label column.
PHASES = ("fit", "tuning", "evaluation")


class LabelAccessError(RuntimeError):
    """Raised when a label column would enter the tuning phase."""


@dataclass(frozen=True)
class FrozenPlan:
    """Everything the 2024 evaluation is executed with."""

    protocol_version: str
    frozen_at: str
    training_years: tuple[int, ...]
    evaluation_year: int
    models: tuple[str, ...]
    feature_column: str
    target_column: str
    clip: tuple[float, float]
    metrics: tuple[str, ...]
    bootstrap_seed: int
    bootstrap_repetitions: int
    bootstrap_unit: str
    freeze_commit_sha: str


def load_config(path: Path | None = None) -> dict:
    """Load and check the frozen configuration."""
    location = Path(path) if path is not None else CONFIG_PATH
    config = json.loads(location.read_text(encoding="utf-8"))
    required = ("data", "models", "training", "metrics", "reporting_rules")
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"the configuration is missing sections: {missing}")
    if not config["models"]:
        raise ValueError("the configuration lists no model")
    return config


def extract_note_block(note_path: Path | None = None) -> dict:
    """Read the machine-readable block of the research note.

    The note carries a copy of the configuration in a fenced JSON block. The
    copy exists so that a reader of the note alone sees the frozen rules, and
    the check exists so that the note and the configuration cannot drift apart
    silently.
    """
    location = Path(note_path) if note_path is not None else NOTE_PATH
    text = location.read_text(encoding="utf-8")
    if BLOCK_HEADING not in text:
        raise ValueError("the research note has no machine-readable block")
    after = text.split(BLOCK_HEADING, 1)[1]
    match = re.search(r"```json\s*(\{.*?\})\s*```", after, re.S)
    if not match:
        raise ValueError("the machine-readable block of the note is not valid JSON")
    return json.loads(match.group(1))


def compare_config_and_note(config: dict, note: dict) -> list[str]:
    """Return the differences between the configuration and the note."""
    differences: list[str] = []

    def compare(left: object, right: object, path: str) -> None:
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                if key not in left:
                    differences.append(f"{path}.{key}: only in the note")
                elif key not in right:
                    differences.append(f"{path}.{key}: only in the configuration")
                else:
                    compare(left[key], right[key], f"{path}.{key}")
        elif isinstance(left, list) and isinstance(right, list):
            if len(left) != len(right):
                differences.append(f"{path}: {len(left)} entries vs {len(right)}")
            else:
                for index, (a, b) in enumerate(zip(left, right)):
                    compare(a, b, f"{path}[{index}]")
        elif left != right:
            differences.append(f"{path}: {left!r} vs {right!r}")

    compare(config, note, "config")
    return differences


def build_plan(config: dict) -> FrozenPlan:
    """Build the plan of the 2024 evaluation.

    The training years are the cohort years before 2024. The check refuses a
    year that is not earlier, so that a later edit cannot open a hindsight
    path.
    """
    data = config["data"]
    training = tuple(sorted(int(year) for year in data["training_years"]))
    evaluation_year = int(data["evaluation_year"])
    if any(year >= evaluation_year for year in training):
        raise ValueError("the training years must be earlier than the evaluation year")
    clip = tuple(float(value) for value in config["training"]["prediction_clip"])
    metrics = tuple(
        str(metric) for metric in config["metrics"]["primary"] + config["metrics"]["secondary"]
    )
    bootstrap = config["metrics"]["bootstrap"]
    return FrozenPlan(
        protocol_version=str(config["protocol_version"]),
        frozen_at=str(config["frozen_at"]),
        training_years=training,
        evaluation_year=evaluation_year,
        models=tuple(str(model["name"]) for model in config["models"]),
        feature_column=str(data["feature_column"]),
        target_column=str(data["target_column"]),
        clip=clip,  # type: ignore[arg-type]
        metrics=metrics,
        bootstrap_seed=int(bootstrap["seed"]),
        bootstrap_repetitions=int(bootstrap["repetitions"]),
        bootstrap_unit=str(bootstrap["unit"]),
        freeze_commit_sha=str(config["freeze_commit_sha"]),
    )


def assert_no_label_access(columns, phase: str, forbidden=None) -> None:
    """Refuse a label column in the tuning phase.

    The forbidden names default to the list of the configuration. The fit and
    the evaluation phase may read the target, the tuning phase may not.
    """
    if phase not in PHASES:
        raise ValueError(f"unknown phase: {phase}")
    if phase != "tuning":
        return
    if forbidden is None:
        forbidden = load_config()["data"]["forbidden_columns_during_tuning"]
    names = [str(name) for name in columns]
    offending = sorted(set(names) & set(forbidden))
    if offending:
        raise LabelAccessError(
            "the tuning phase must not see the target column: " + ", ".join(offending)
        )


def frozen_catalogue_years(path: Path | None = None) -> list[int]:
    """The years of the frozen 2010-2022 source catalogue."""
    location = Path(path) if path is not None else SOURCE_CATALOG_PATH
    catalog = json.loads(location.read_text(encoding="utf-8"))
    return sorted(int(item["year"]) for item in catalog["publications"])


def check_freeze_commit(sha: str, repo: Path | None = None) -> str:
    """Check that the recorded freeze commit exists and is an ancestor.

    The freeze commit is the commit that introduced the frozen configuration.
    It has to be part of the history, otherwise the note points at nothing.
    """
    if not sha or sha.upper().startswith("PENDING"):
        return "PENDING"
    location = Path(repo) if repo is not None else REPO
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        cwd=location,
        capture_output=True,
    )
    if exists.returncode != 0:
        raise ValueError(f"the freeze commit {sha} is not in the repository")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "HEAD"],
        cwd=location,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        raise ValueError(f"the freeze commit {sha} is not an ancestor of HEAD")
    return sha


def run_checks() -> dict:
    """Run every check of the freeze and return the result."""
    config = load_config()
    note = extract_note_block()
    differences = compare_config_and_note(config, note)
    if differences:
        raise AssertionError(
            "the research note and the frozen configuration differ: "
            + "; ".join(differences)
        )
    plan = build_plan(config)
    sha = check_freeze_commit(plan.freeze_commit_sha)
    years = frozen_catalogue_years()
    if plan.evaluation_year in years:
        raise AssertionError(
            "the frozen 2010-2022 source catalogue must not contain the "
            f"evaluation year {plan.evaluation_year}; the 2024 record belongs "
            "to a separate catalogue file"
        )
    return {
        "protocol_version": plan.protocol_version,
        "frozen_at": plan.frozen_at,
        "freeze_commit_sha": sha,
        "evaluation_year": plan.evaluation_year,
        "training_years": list(plan.training_years),
        "models": list(plan.models),
        "metrics": list(plan.metrics),
        "bootstrap": {
            "seed": plan.bootstrap_seed,
            "repetitions": plan.bootstrap_repetitions,
            "unit": plan.bootstrap_unit,
        },
        "source_published_at_freeze_time": config["status"][
            "source_published_at_freeze_time"
        ],
        "frozen_catalogue_years": years,
        "note_matches_configuration": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="check that the note, the configuration and the freeze commit agree",
    )
    args = parser.parse_args()
    if not args.check:
        parser.error("nothing to do; pass --check")
    result = run_checks()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("The frozen 2024 evaluation plan is consistent.")


if __name__ == "__main__":
    main()
