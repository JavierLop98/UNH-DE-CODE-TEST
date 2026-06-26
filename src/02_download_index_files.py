"""
02_download_index_files.py
--------------------------
Downloads index JSON files listed in the manifest produced by step 01.

Features:
- Streaming download to avoid loading large files into memory.
- Automatic retries with exponential backoff (3 attempts).
- Size guard: files exceeding --max-size-mb are skipped.
- Progress bar via tqdm.
- Configurable delay between downloads to respect rate limits.
"""
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.io_utils import ensure_dir

MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


def download_file(
    url: str,
    output_path: Path,
    timeout: int,
    max_size_mb: int,
    retries: int = MAX_RETRIES,
) -> dict:
    """Download a single file with retries and size guard."""
    started_at = datetime.now(timezone.utc).isoformat()
    max_bytes = max_size_mb * 1024 * 1024

    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, stream=True, timeout=timeout, headers={
                "User-Agent": "Mozilla/5.0 UHC-TiC-DataEng/1.0",
                "Accept": "application/json",
            }) as r:
                r.raise_for_status()

                # Check Content-Length before downloading
                content_length = r.headers.get("content-length")
                if content_length and int(content_length) > max_bytes:
                    return {
                        "status": "skipped_too_large",
                        "bytes_written": 0,
                        "content_length": int(content_length),
                        "started_at": started_at,
                        "finished_at": datetime.now(timezone.utc).isoformat(),
                        "error_message": f"Content-Length {int(content_length):,} exceeds {max_size_mb} MB",
                        "attempts": attempt,
                    }

                bytes_written = 0
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if not chunk:
                            continue
                        bytes_written += len(chunk)
                        if bytes_written > max_bytes:
                            f.close()
                            if output_path.exists():
                                output_path.unlink()
                            return {
                                "status": "skipped_too_large",
                                "bytes_written": bytes_written,
                                "content_length": None,
                                "started_at": started_at,
                                "finished_at": datetime.now(timezone.utc).isoformat(),
                                "error_message": f"Streamed bytes exceed {max_size_mb} MB",
                                "attempts": attempt,
                            }
                        f.write(chunk)

            return {
                "status": "downloaded",
                "bytes_written": bytes_written,
                "content_length": content_length,
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error_message": None,
                "attempts": attempt,
            }

        except Exception as exc:
            if attempt < retries:
                wait = BACKOFF_BASE ** attempt
                time.sleep(wait)
            else:
                return {
                    "status": "failed",
                    "bytes_written": 0,
                    "content_length": None,
                    "started_at": started_at,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": str(exc),
                    "attempts": attempt,
                }


def main():
    parser = argparse.ArgumentParser(
        description="Download UHC index files from the manifest."
    )
    parser.add_argument("--manifest", default="data/processed/index_manifest.csv")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-size-mb", type=int, default=512)
    parser.add_argument("--delay", type=float, default=0.1,
                        help="Seconds to wait between downloads")
    parser.add_argument("--log-output", default="data/processed/download_log.csv")
    args = parser.parse_args()

    ensure_dir(args.raw_dir)
    ensure_dir("data/processed")
    manifest = pd.read_csv(args.manifest).head(args.limit)

    logs = []
    progress = tqdm(manifest.iterrows(), total=len(manifest), desc="Downloading",
                    unit="file", ncols=100)

    for _, row in progress:
        file_name = row["file_name"]
        url = row["download_url"]
        output_path = Path(args.raw_dir) / file_name

        progress.set_postfix_str(file_name[:40], refresh=True)

        if output_path.exists():
            result = {
                "status": "already_exists",
                "bytes_written": output_path.stat().st_size,
                "content_length": output_path.stat().st_size,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error_message": None,
                "attempts": 0,
            }
        else:
            result = download_file(url, output_path, args.timeout, args.max_size_mb)
            time.sleep(args.delay)

        logs.append({
            "file_rank": row["file_rank"],
            "file_name": file_name,
            "download_url": url,
            "local_path": str(output_path),
            **result,
        })

    log_df = pd.DataFrame(logs)
    log_df.to_csv(args.log_output, index=False)

    # Summary
    print(f"\nDownload log written to {args.log_output}")
    print(f"Results: {log_df['status'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
