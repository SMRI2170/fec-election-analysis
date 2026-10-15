"""Inspect unmodified workbook layout; do not assume the first row is a header.

Produces an inspection inventory, not normalized election observations.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def inspect(path: Path, max_sheets: int = 8, rows: int = 6) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    if max_sheets < 1 or rows < 1:
        raise ValueError("max_sheets and rows must be >= 1")
    with pd.ExcelFile(path) as book:
        sheets = []
        for name in book.sheet_names[:max_sheets]:
            frame = pd.read_excel(book, sheet_name=name, header=None, nrows=rows, dtype=object)
            preview = [
                [None if pd.isna(v) else str(v)[:120] for v in row]
                for row in frame.itertuples(index=False, name=None)
            ]
            sheets.append({"name": name, "preview_rows": preview})
        return {
            "file": path.name,
            "sheet_count": len(book.sheet_names),
            "sheet_names": book.sheet_names,
            "inspected_sheets": sheets,
            "preview_only": True,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect initial FEC workbook rows and sheet names")
    parser.add_argument("file", type=Path)
    parser.add_argument("--max-sheets", type=int, default=8)
    parser.add_argument("--rows", type=int, default=6)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = inspect(args.file, args.max_sheets, args.rows)
    encoded = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
