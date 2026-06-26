import argparse
from pathlib import Path

import pandas as pd

from utils.io_utils import ensure_dir


def safe_read_parquet(path: str) -> pd.DataFrame:
    p = Path(path)
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--report-output", default="reports/insights_summary.md")
    args = parser.parse_args()

    ensure_dir("reports")
    downloads = pd.read_csv(f"{args.processed_dir}/download_log.csv") if Path(f"{args.processed_dir}/download_log.csv").exists() else pd.DataFrame()
    parse_log = pd.read_csv(f"{args.processed_dir}/parse_log.csv") if Path(f"{args.processed_dir}/parse_log.csv").exists() else pd.DataFrame()
    indexes = safe_read_parquet(f"{args.processed_dir}/index_files.parquet")
    plans = safe_read_parquet(f"{args.processed_dir}/plans.parquet")
    refs = safe_read_parquet(f"{args.processed_dir}/referenced_files.parquet")

    lines = ["# UHC TiC Index Files - Insights Summary", ""]

    if not downloads.empty:
        lines += [
            "## 1. Ingestion Summary",
            f"- Manifest rows processed: {len(downloads):,}",
            f"- Download statuses: {downloads['status'].value_counts(dropna=False).to_dict()}",
            f"- Total bytes downloaded: {int(downloads['bytes_written'].fillna(0).sum()):,}",
            "",
        ]

    if not parse_log.empty:
        lines += [
            "## 2. Parse Quality",
            f"- Parse statuses: {parse_log['parse_status'].value_counts(dropna=False).to_dict()}",
            "",
        ]

    if not indexes.empty:
        lines += [
            "## 3. Reporting Entities",
            f"- Parsed index files: {len(indexes):,}",
            "- Reporting entity counts:",
            indexes["reporting_entity_name"].value_counts(dropna=False).head(10).to_markdown(),
            "",
        ]

    if not plans.empty:
        plans_per_index = plans.groupby("index_file_id").size()
        lines += [
            "## 4. Plan Distribution",
            f"- Total plan rows: {len(plans):,}",
            f"- Average plans per parsed index: {plans_per_index.mean():.2f}",
            f"- Median plans per parsed index: {plans_per_index.median():.2f}",
            f"- Max plans in one index: {plans_per_index.max():,}",
            "",
            "### Top plan ID types",
            plans["plan_id_type"].value_counts(dropna=False).head(10).to_markdown(),
            "",
        ]

    if not refs.empty:
        refs_per_index = refs.groupby("index_file_id").size()
        reused = refs.groupby("location_url").agg(
            referenced_count=("location_url", "size"),
            distinct_index_files=("index_file_id", "nunique"),
        ).sort_values("referenced_count", ascending=False).head(10)
        lines += [
            "## 5. Referenced Machine-Readable Files",
            f"- Total referenced file rows: {len(refs):,}",
            f"- Distinct referenced URLs: {refs['location_url'].nunique():,}",
            f"- Average referenced files per parsed index: {refs_per_index.mean():.2f}",
            "",
            "### Referenced file types",
            refs["file_type"].value_counts(dropna=False).to_markdown(),
            "",
            "### Most reused referenced URLs",
            reused.to_markdown(),
            "",
        ]

    lines += [
        "## 6. Production Recommendations",
        "- Schedule the workflow with Airflow or Azure Data Factory.",
        "- Add automated data quality checks for missing fields, malformed URLs, duplicate plans and row-count anomalies.",
        "- Persist raw files in object storage and curated tables in Snowflake.",
        "- Add monitoring, retries, alerting and CI/CD for deployment.",
    ]

    Path(args.report_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"Insights report written to {args.report_output}")


if __name__ == "__main__":
    main()
