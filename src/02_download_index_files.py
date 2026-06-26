import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from utils.io_utils import ensure_dir


def download_file(url: str, output_path: Path, timeout: int, max_size_mb: int) -> dict:
    started_at = datetime.now(timezone.utc).isoformat()
    status = "downloaded"
    error = None
    bytes_written = 0
    max_bytes = max_size_mb * 1024 * 1024

    try:
        with requests.get(url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            content_length = r.headers.get("content-length")
            if content_length and int(content_length) > max_bytes:
                return {
                    "status": "skipped_too_large",
                    "bytes_written": 0,
                    "content_length": int(content_length),
                    "started_at": started_at,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": f"Content-Length exceeds {max_size_mb} MB",
                }
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        status = "skipped_too_large"
                        error = f"Streamed bytes exceed {max_size_mb} MB"
                        break
                    f.write(chunk)
        if status == "skipped_too_large" and output_path.exists():
            output_path.unlink()
    except Exception as exc:
        status = "failed"
        error = str(exc)

    return {
        "status": status,
        "bytes_written": bytes_written,
        "content_length": None,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "error_message": error,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/processed/index_manifest.csv")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-size-mb", type=int, default=512)
    parser.add_argument("--log-output", default="data/processed/download_log.csv")
    args = parser.parse_args()

    ensure_dir(args.raw_dir)
    ensure_dir("data/processed")
    manifest = pd.read_csv(args.manifest).head(args.limit)

    logs = []
    for _, row in manifest.iterrows():
        file_name = row["file_name"]
        url = row["file_url"]
        output_path = Path(args.raw_dir) / file_name
        if output_path.exists():
            result = {
                "status": "already_exists",
                "bytes_written": output_path.stat().st_size,
                "content_length": output_path.stat().st_size,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error_message": None,
            }
        else:
            result = download_file(url, output_path, args.timeout, args.max_size_mb)
        logs.append({**row.to_dict(), "local_path": str(output_path), **result})
        print(f"{row['file_rank']}: {file_name} -> {result['status']}")

    pd.DataFrame(logs).to_csv(args.log_output, index=False)
    print(f"Download log written to {args.log_output}")


if __name__ == "__main__":
    main()
