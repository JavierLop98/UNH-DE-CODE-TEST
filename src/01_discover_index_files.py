import argparse
from datetime import datetime, timezone
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from utils.io_utils import ensure_dir

DEFAULT_URL = "https://transparency-in-coverage.uhc.com/"


def discover_index_files(base_url: str, limit: int) -> pd.DataFrame:
    response = requests.get(base_url, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        candidate = href or text
        if "_index.json" in candidate:
            file_url = urljoin(base_url, href)
            file_name = file_url.rstrip("/").split("/")[-1]
            links.append({"file_name": file_name, "file_url": file_url})

    # Fallback for simple text/table pages where URLs appear as text rather than anchors
    if not links:
        for token in response.text.split():
            if "_index.json" in token:
                cleaned = token.strip('"\',<>')
                file_url = urljoin(base_url, cleaned)
                file_name = file_url.rstrip("/").split("/")[-1]
                links.append({"file_name": file_name, "file_url": file_url})

    seen = set()
    deduped = []
    for item in links:
        if item["file_url"] not in seen:
            seen.add(item["file_url"])
            deduped.append(item)

    rows = []
    discovered_at = datetime.now(timezone.utc).isoformat()
    for rank, item in enumerate(deduped[:limit], start=1):
        rows.append({
            "file_rank": rank,
            "file_name": item["file_name"],
            "file_url": item["file_url"],
            "discovered_at": discovered_at,
            "status": "pending",
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--output", default="data/processed/index_manifest.csv")
    args = parser.parse_args()

    ensure_dir("data/processed")
    manifest = discover_index_files(args.url, args.limit)
    manifest.to_csv(args.output, index=False)
    print(f"Discovered {len(manifest)} index files. Manifest written to {args.output}")


if __name__ == "__main__":
    main()
