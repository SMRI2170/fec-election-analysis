"""Normalise the 2024 House results under the frozen rules (#54).

The normaliser reuses the **frozen** house normaliser of
``scripts/normalize_fec.py``. No rule is re-derived here: the exclusion
categories, the write-in policy and the subtotal reconciliation are exactly the
ones that produced the 916-record cohort.

The output goes to a **separate** file. The frozen 2016-2022 dataset is never
overwritten, and the frozen source catalogue is never extended.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from normalize_fec import load_house_sheet, normalize_house  # noqa: E402

RECORD_PATH = REPO / "data" / "sources" / "fec2024_publication.json"


class SourceUnavailable(RuntimeError):
    """Raised when the 2024 publication cannot be used."""


def load_record(path: Path = RECORD_PATH) -> dict:
    """Load the retrieval record of the 2024 source."""
    if not path.exists():
        raise SourceUnavailable(
            "there is no retrieval record for the 2024 source; run "
            "scripts/download_fec_2024.py first"
        )
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("status") != "available":
        raise SourceUnavailable(
            "the 2024 source is not available (status: "
            f"{record.get('status')!r}); the notes are {record.get('notes')}"
        )
    return record


def normalize_2024(
    workbook: Path, record: dict, writein_policy: str = "attribute"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normalise the 2024 House contests with the frozen rules."""
    sheet, frame = load_house_sheet(workbook)
    if record.get("house_sheet") and sheet != record["house_sheet"]:
        raise SourceUnavailable(
            f"the workbook now carries the sheet {sheet!r} instead of the "
            f"recorded {record['house_sheet']!r}; the layout has to be inspected"
        )
    normal, audit = normalize_house(
        frame, 2024, workbook.name, sheet, writein_policy=writein_policy
    )
    from audit_winners import audit as audit_winners
    from source_reconcile import read_house

    official, _ = audit_winners(normal, {2024: read_house(workbook)})
    from normalize_fec import exclude_nonstandard_winners

    normal, excluded = exclude_nonstandard_winners(normal, official, 2024)
    audit = pd.concat([audit, excluded], ignore_index=True)
    return normal, audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPO / "data" / "processed")
    parser.add_argument("--record", type=Path, default=RECORD_PATH)
    parser.add_argument(
        "--writein-policy", choices=["attribute", "ignore"], default="attribute"
    )
    parser.add_argument(
        "--expect-unavailable",
        action="store_true",
        help="exit with zero when the normalisation correctly refuses to run",
    )
    args = parser.parse_args()

    try:
        record = load_record(args.record)
    except SourceUnavailable as error:
        print(f"The 2024 normalisation stops: {error}", file=sys.stderr)
        print(json.dumps({"status": "not-normalised", "reason": str(error)}, indent=2))
        if args.expect_unavailable:
            raise SystemExit(0) from error
        raise SystemExit(2) from error

    workbook = Path(record["local_path"])
    normal, audit = normalize_2024(workbook, record, writein_policy=args.writein_policy)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    normal.to_csv(args.output_dir / "elections_2024.csv", index=False)
    audit.to_csv(args.output_dir / "exclusions_2024.csv", index=False)
    summary = {
        "year": 2024,
        "source": record.get("workbook_url"),
        "sha256": record.get("sha256"),
        "sheet": record.get("house_sheet"),
        "writein_policy": args.writein_policy,
        "included": int(len(normal)),
        "excluded": int(len(audit)),
        "reason_counts": audit["reason"].value_counts().to_dict(),
        "note": "the frozen 2016-2022 dataset is not modified by this script",
    }
    (args.output_dir / "normalization-summary-2024.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
