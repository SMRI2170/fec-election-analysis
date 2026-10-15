"""Inspect year-specific FEC CSV/XLSX structure."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect FEC sheet and column structures")
    parser.add_argument("file", type=Path, help="Input .xlsx/.xls/.csv path")
    parser.add_argument("--rows", type=int, default=5)
    args = parser.parse_args()
    if not args.file.is_file():
        parser.error(f"File not found: {args.file}")
    if args.file.suffix.lower() == ".csv":
        df = pd.read_csv(args.file)
        print("CSV shape:", df.shape)
        print("Columns:", df.columns.tolist())
        print(df.head(args.rows).to_string(index=False))
    elif args.file.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        with pd.ExcelFile(args.file) as xls:
            print("Sheets:", xls.sheet_names)
            for name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=name, nrows=args.rows)
                print(f"\n=== {name} ===")
                print("Detected columns:", df.columns.tolist())
                print(df.head(args.rows).to_string(index=False))
                print("Note: headers might not start on row 1; inspect the workbook.")
    else:
        parser.error("Supported formats: .csv, .xlsx, .xlsm, .xls (xls may need xlrd)")


if __name__ == "__main__":
    main()
