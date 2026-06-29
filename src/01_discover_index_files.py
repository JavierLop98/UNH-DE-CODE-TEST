"""Discovers UHC Transparency in Coverage index files via the public API."""
import argparse
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # so we can import from utils/

from utils.io_utils import ensure_dir

API_URL = "https://transparency-in-coverage.uhc.com/api/v1/uhc/blobs/"


def fetch_blob_list(api_url: str, timeout: int = 120) -> list[dict]:
    """Call the UHC blobs API and return blob metadata."""
    print(f"Fetching blob list from {api_url} ...")
    response = requests.get(api_url, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    # the API wraps everything under a "blobs" key
    blobs = data.get("blobs", [])
    print(f"  -> received {len(blobs):,} blobs from API")
    return blobs


def filter_index_files(blobs: list[dict], limit: int) -> pd.DataFrame:
    """Keep only *_index.json blobs and return as a DataFrame."""
    rows = []
    discovered_at = datetime.now(timezone.utc).isoformat()
    rank = 0

    for blob in blobs:
        name = blob.get("name", "")
        if not name.endswith("_index.json"):
            continue
        rank += 1
        rows.append({
            "file_rank": rank,
            "file_name": name,
            "download_url": blob.get("downloadUrl", ""),
            "file_size_bytes": blob.get("size"),
            "discovered_at": discovered_at,
            "status": "pending",
        })
        if rank >= limit:
            break

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Discover UHC TiC index files via the blobs API."
    )
    parser.add_argument("--api-url", default=API_URL,
                        help="UHC blobs API endpoint")
    parser.add_argument("--limit", type=int, default=1000,
                        help="Maximum number of index files to include")
    parser.add_argument("--output", default="data/processed/index_manifest.csv",
                        help="Path for the output manifest CSV")
    parser.add_argument("--timeout", type=int, default=120,
                        help="HTTP request timeout in seconds")
    args = parser.parse_args()

    ensure_dir("data/processed")

    blobs = fetch_blob_list(args.api_url, args.timeout)
    manifest = filter_index_files(blobs, args.limit)

    manifest.to_csv(args.output, index=False)
    print(f"\nDiscovered {len(manifest):,} index files.")
    print(f"Manifest written to {args.output}")


if __name__ == "__main__":
    main()
