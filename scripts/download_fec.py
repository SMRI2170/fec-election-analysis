"""Download FEC Federal Elections workbooks using official per-year URLs.

This never writes into tracked source directories by default. Offline tests use
synthetic byte streams; a real FEC network download must be separately verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

CATALOG = Path(__file__).resolve().parents[1] / "data/sources/fec_publications.json"
OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


def load_sources(catalog: Path = CATALOG) -> dict[int, dict]:
    records = json.loads(catalog.read_text(encoding="utf-8"))["publications"]
    sources = {int(item["year"]): item for item in records}
    if len(sources) != len(records):
        raise ValueError("Duplicate years in FEC source catalog")
    for year, item in sources.items():
        expected_suffix = "." + item["format"]
        url = item["excel_url"]
        if not url.startswith("https://www.fec.gov/documents/") or not url.endswith(expected_suffix):
            raise ValueError(f"Unexpected FEC URL for {year}: {url}")
    return sources


def check_signature(data: bytes, extension: str) -> None:
    if extension == "xlsx" and not data.startswith(ZIP_SIGNATURES):
        raise ValueError("Invalid xlsx signature (possible error/HTML response)")
    if extension == "xls" and not data.startswith(OLE_SIGNATURE):
        raise ValueError("Invalid xls signature (possible error/HTML response)")


def download_one(year: int, source: dict, out_dir: Path, timeout: int = 45) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"federalelections{year}.{source['format']}"
    request = Request(source["excel_url"], headers={"User-Agent": "FEC-academic-research/0.1 (+https://github.com/SMRI2170/fec-election-analysis)"})
    tmp_path = path.with_suffix(path.suffix + ".part")
    digest = hashlib.sha256()
    size = 0
    try:
        with urlopen(request, timeout=timeout) as response, tmp_path.open("wb") as output:
            prefix = b""
            while chunk := response.read(1024 * 1024):
                if not prefix:
                    prefix = chunk[:8]
                    check_signature(prefix, source["format"])
                digest.update(chunk)
                size += len(chunk)
                output.write(chunk)
        if size == 0:
            raise ValueError(f"Empty response for year {year}")
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return {"year": year, "source_url": source["excel_url"], "path": str(path), "bytes": size, "sha256": digest.hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download official FEC Federal Elections workbooks")
    parser.add_argument("--years", type=int, nargs="+", default=[2020, 2022])
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()
    sources = load_sources()
    unknown = sorted(set(args.years) - set(sources))
    if unknown:
        parser.error(f"Unsupported years: {unknown}; available: {sorted(sources)}")
    results = [download_one(year, sources[year], args.output_dir, args.timeout) for year in args.years]
    manifest = args.output_dir / "download-manifest.json"
    manifest.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
