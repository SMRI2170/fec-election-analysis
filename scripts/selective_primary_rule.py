"""Primary-only abstention rule for the selective-prediction study.

This module is deliberately a **pure function with no data access**. It is the
only place where the decision to answer or to abstain is made, and it cannot
see anything except two Primary vote counts and a pre-registered threshold.

Contract
--------
``selective_rule(primary_r, primary_d, threshold_pct) -> (accepted, answer)``

* ``threshold_pct`` is a margin in **percentage points** of the Primary
  two-party share. Only 0, 5, 10, 15 and 20 are allowed.
* The Primary two-party share is ``P = primary_r / (primary_r + primary_d)``;
  the margin is ``abs(P - 0.5)``.
* A contest is answered when ``margin >= threshold_pct / 100``. The
  comparison is performed with **integer arithmetic** so that boundary cases
  never depend on binary floating point:
  ``100 * abs(primary_r - primary_d) >= 2 * threshold_pct * (primary_r + primary_d)``
* When answered, the prediction is the Primary majority: ``1`` if
  ``primary_r > primary_d`` and ``0`` otherwise. A Primary tie is therefore
  predicted as a Democratic lead, matching the pre-existing
  ``primary-winner rule`` in ``scripts/analyze.py``.
* When abstained, the answer is ``None``. An abstention is **not** a correct
  prediction and must never be counted as one.

What this function must never do
--------------------------------
It takes no General vote, no General outcome label, no year and no fitted
parameter. Nothing here may be re-tuned after the results are observed; the
thresholds were fixed in advance by Issue #76.
"""
from __future__ import annotations

import argparse
from typing import Final

#: Pre-registered abstention thresholds, in percentage points.
ALLOWED_THRESHOLDS_PCT: Final[tuple[int, ...]] = (0, 5, 10, 15, 20)

#: Answer value used for a Democratic two-party lead.
DEMOCRATIC_LEAD: Final[int] = 0

#: Answer value used for a Republican two-party lead.
REPUBLICAN_LEAD: Final[int] = 1


def _validate_votes(primary_r: object, primary_d: object) -> tuple[int, int]:
    """Return the two Primary vote counts as plain integers, or raise."""
    for name, value in (("primary_r", primary_r), ("primary_d", primary_d)):
        if isinstance(value, bool):
            raise TypeError(f"{name} must be an integer vote count, not a bool")
        if not isinstance(value, int):
            raise TypeError(f"{name} must be an integer vote count, got {type(value).__name__}")
        if value <= 0:
            raise ValueError(f"{name} must be a positive vote count, got {value}")
    return int(primary_r), int(primary_d)


def _validate_threshold(threshold_pct: object) -> int:
    """Return the threshold as an int, or raise for anything not pre-registered."""
    if isinstance(threshold_pct, bool):
        raise TypeError("threshold_pct must be an int, not a bool")
    if not isinstance(threshold_pct, int):
        raise TypeError(
            f"threshold_pct must be an int, got {type(threshold_pct).__name__}"
        )
    if threshold_pct not in ALLOWED_THRESHOLDS_PCT:
        raise ValueError(
            f"threshold_pct must be one of {ALLOWED_THRESHOLDS_PCT}, got {threshold_pct}"
        )
    return int(threshold_pct)


def selective_rule(
    primary_r: int, primary_d: int, threshold_pct: int
) -> tuple[bool, int | None]:
    """Decide whether to answer a contest from Primary votes alone.

    Parameters
    ----------
    primary_r:
        Republican Primary votes in the contest. Must be a positive integer.
    primary_d:
        Democratic Primary votes in the contest. Must be a positive integer.
    threshold_pct:
        Abstention threshold in percentage points of the Primary two-party
        share. Must be one of 0, 5, 10, 15, 20.

    Returns
    -------
    (accepted, answer)
        ``accepted`` is ``True`` when the contest is answered and ``False``
        when it is abstained. ``answer`` is ``1`` for a predicted Republican
        two-party lead, ``0`` for a predicted Democratic two-party lead, and
        ``None`` when abstained.
    """
    votes_r, votes_d = _validate_votes(primary_r, primary_d)
    threshold = _validate_threshold(threshold_pct)

    # Integer form of margin >= threshold_pct / 100 with margin = |P - 0.5|.
    accepted = 100 * abs(votes_r - votes_d) >= 2 * threshold * (votes_r + votes_d)
    if not accepted:
        return False, None
    if votes_r > votes_d:
        return True, REPUBLICAN_LEAD
    return True, DEMOCRATIC_LEAD


def describe(primary_r: int, primary_d: int, threshold_pct: int) -> dict:
    """Return a human-readable description of one rule decision.

    Useful for the report appendix and for manual spot checks; it performs no
    I/O and reaches no General data.
    """
    votes_r, votes_d = _validate_votes(primary_r, primary_d)
    threshold = _validate_threshold(threshold_pct)
    accepted, answer = selective_rule(votes_r, votes_d, threshold)
    total = votes_r + votes_d
    return {
        "primary_r": votes_r,
        "primary_d": votes_d,
        "threshold_pct": threshold,
        "primary_rep_share": votes_r / total,
        "margin_percentage_points": abs(votes_r - votes_d) / total * 100,
        "accepted": accepted,
        "answer": answer,
        "answer_label": (
            None
            if answer is None
            else ("Republican two-party lead" if answer == REPUBLICAN_LEAD else "Democratic two-party lead")
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply the Primary-only abstention rule to one contest"
    )
    parser.add_argument("--primary-r", type=int, required=True)
    parser.add_argument("--primary-d", type=int, required=True)
    parser.add_argument(
        "--threshold-pct",
        type=int,
        default=5,
        choices=list(ALLOWED_THRESHOLDS_PCT),
        help="abstention threshold in percentage points",
    )
    args = parser.parse_args()
    result = describe(args.primary_r, args.primary_d, args.threshold_pct)
    print(result)


if __name__ == "__main__":
    main()
