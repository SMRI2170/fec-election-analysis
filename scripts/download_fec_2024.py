"""Retrieve the 2024 FEC publication under the frozen retrieval order (#54).

The frozen plan of [#53](https://github.com/SMRI2170/fec-election-analysis/issues/53)
fixes the order in which the 2024 source may be touched:

1. confirm that the catalogue page exists and record its URL and the date,
2. download the workbook and record the URL, the byte size and the SHA-256,
3. record the sheet names and the column header row **only**,
4. only then parse the vote tables,
5. write the record into ``data/sources/fec2024_publication.json``.

This script performs steps 1 to 3 and 5. It never reads a vote total, so the
plan stays blind to the result even when the publication exists.

If the publication is not available, the script records the reason and stops.
It does not substitute another source and it does not produce a value.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

CATALOGUE_PAGE = (
    "https://www.fec.gov/introduction-campaign-finance/"
    "election-results-and-voting-information/"
)
EDITION_PAGE = (
    "https://www.fec.gov/introduction-campaign-finance/"
    "election-results-and-voting-information/federal-elections-2024/"
)
RECORD_PATH = REPO / "data" / "sources" / "fec2024_publication.json"
USER_AGENT = (
    "FEC-academic-research/0.1 (+https://github.com/SMRI2170/fec-election-analysis)"
)
#: The sheet that carries the House results in every inspected edition.
HOUSE_SHEET_PATTERN = "US House Results by State"


def fetch(url: str, timeout: int = 45) -> tuple[int, bytes]:
    """Fetch a URL and return the status code and the body.

    A network problem is reported as the status ``0`` instead of an
    exception, because the retrieval has to fail closed with a recorded
    reason rather than with a crash.
    """
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, b""
    except URLError:
        return 0, b""
    except Exception:  # pragma: no cover - a transport level failure
        return 0, b""


def find_edition_link(html: str) -> str | None:
    """Return the link of the 2024 edition, if the catalogue lists one."""
    pattern = re.compile(
        r'href="([^"]*federal-elections-2024[^"]*)"', re.IGNORECASE
    )
    for match in pattern.finditer(html):
        link = match.group(1)
        if link.startswith("/"):
            return "https://www.fec.gov" + link
        if link.startswith("https://www.fec.gov"):
            return link
    return None


def find_workbook_link(html: str) -> str | None:
    """Return the link of the Excel workbook of the edition page."""
    pattern = re.compile(
        r'href="([^"]*federalelections2024\.xlsx)"', re.IGNORECASE
    )
    match = pattern.search(html)
    if not match:
        return None
    link = match.group(1)
    if link.startswith("/"):
        return "https://www.fec.gov" + link
    return link


def record_sheet_names(path: Path) -> list[str]:
    """Return the sheet names of the workbook.

    Only the sheet names are read. No cell value of a vote table is touched.
    """
    import pandas as pd

    with pd.ExcelFile(path) as book:
        return list(book.sheet_names)


def locate(edition_page: str = EDITION_PAGE) -> dict:
    """Run the frozen retrieval order and return the record."""
    record: dict = {
        "year": 2024,
        "retrieved_at": date.today().isoformat(),
        "catalogue_page": CATALOGUE_PAGE,
        "edition_page": edition_page,
        "status": "unknown",
        "workbook_url": None,
        "bytes": None,
        "sha256": None,
        "sheet_names": [],
        "house_sheet": None,
        "notes": [],
    }
    status, body = fetch(CATALOGUE_PAGE)
    record["catalogue_page_status"] = status
    if status == 200:
        link = find_edition_link(body.decode("utf-8", "replace"))
        record["catalogue_lists_2024"] = link is not None
        if link:
            record["edition_page"] = link
    else:
        record["catalogue_lists_2024"] = False

    status, body = fetch(record["edition_page"])
    record["edition_page_status"] = status
    if status != 200:
        record["status"] = "not-published"
        record["notes"].append(
            f"the 2024 edition page returned HTTP {status} on "
            f"{record['retrieved_at']}"
        )
        return record

    workbook = find_workbook_link(body.decode("utf-8", "replace"))
    if workbook is None:
        record["status"] = "edition-without-workbook"
        record["notes"].append(
            "the edition page exists but carries no federalelections2024.xlsx link"
        )
        return record
    record["workbook_url"] = workbook
    return record


def download_workbook(record: dict, output_dir: Path, timeout: int = 120) -> dict:
    """Download the workbook and record its byte size and checksum."""
    url = record.get("workbook_url")
    if not url:
        return record
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "federalelections2024.xlsx"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha256()
    size = 0
    with urlopen(request, timeout=timeout) as response, path.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
            output.write(chunk)
    record["bytes"] = size
    record["sha256"] = digest.hexdigest()
    record["local_path"] = str(path)
    record["status"] = "available"
    record["sheet_names"] = record_sheet_names(path)
    house = [s for s in record["sheet_names"] if HOUSE_SHEET_PATTERN.lower() in s.lower()]
    record["house_sheet"] = house[0] if len(house) == 1 else None
    if len(house) != 1:
        record["notes"].append(
            "the workbook does not carry exactly one sheet matching "
            f"{HOUSE_SHEET_PATTERN!r}; the normalisation has to be inspected "
            "before it may run"
        )
        record["status"] = "available-unverified-sheet-layout"
    return record


def write_record(record: dict, path: Path = RECORD_PATH) -> Path:
    """Write the record of the retrieval."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPO / "data" / "raw")
    parser.add_argument("--record", type=Path, default=RECORD_PATH)
    parser.add_argument(
        "--require-source",
        action="store_true",
        help="exit with a non-zero status when the publication is not available",
    )
    args = parser.parse_args()

    record = locate()
    if record["status"] == "not-published" and record.get("workbook_url"):
        record = download_workbook(record, args.output_dir)
    write_record(record, args.record)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    if record["status"] != "available":
        print(
            "The 2024 source is not available. The evaluation stops here and "
            "records the reason; no value is produced.",
            file=sys.stderr,
        )
        if args.require_source:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
