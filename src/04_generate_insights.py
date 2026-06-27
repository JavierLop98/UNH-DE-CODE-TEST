"""
04_generate_insights.py
Reads the parsed Parquet tables and generates a Markdown insights report
covering ingestion stats, parse quality, entity analysis, plan distribution,
referenced files, data quality, and production recommendations.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

# make local utils importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.io_utils import ensure_dir


def safe_read_parquet(path: str) -> pd.DataFrame:
    """Return the parquet file as a DataFrame, or empty if it doesn't exist."""
    p = Path(path)
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(
        description="Generate an insights summary from parsed UHC TiC data."
    )
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--report-output", default="reports/insights_summary.md")
    args = parser.parse_args()

    ensure_dir("reports")

    # Load all the processed data we need
    dl_log_path = f"{args.processed_dir}/download_log.csv"
    parse_log_path = f"{args.processed_dir}/parse_log.csv"
    downloads = pd.read_csv(dl_log_path) if Path(dl_log_path).exists() else pd.DataFrame()
    parse_log = pd.read_csv(parse_log_path) if Path(parse_log_path).exists() else pd.DataFrame()
    indexes = safe_read_parquet(f"{args.processed_dir}/index_files.parquet")
    plans = safe_read_parquet(f"{args.processed_dir}/plans.parquet")
    refs = safe_read_parquet(f"{args.processed_dir}/referenced_files.parquet")

    lines = [
        "# UHC Transparency in Coverage — Insights Summary",
        "",
        f"> Generated at: {pd.Timestamp.now(tz='UTC').isoformat()}",
        "",
    ]

    # -- Section 1: Ingestion Summary --
    if not downloads.empty:
        status_counts = downloads["status"].value_counts(dropna=False)
        total_bytes = int(downloads["bytes_written"].fillna(0).sum())
        lines += [
            "## 1. Ingestion Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Manifest rows processed | {len(downloads):,} |",
            f"| Total bytes downloaded | {total_bytes:,} ({total_bytes / 1024 / 1024:.1f} MB) |",
            "",
            "**Download status breakdown:**",
            "",
            status_counts.to_markdown(),
            "",
        ]

    # -- Section 2: Parse Quality --
    if not parse_log.empty:
        parse_counts = parse_log["parse_status"].value_counts(dropna=False)
        lines += [
            "## 2. Parse Quality",
            "",
            parse_counts.to_markdown(),
            "",
        ]
        failed = parse_log[parse_log["parse_status"] == "failed"]
        if not failed.empty:
            lines += [
                "### Failed parse samples",
                "",
                failed.head(10).to_markdown(index=False),
                "",
            ]

    # -- Section 3: Reporting Entities --
    if not indexes.empty:
        entity_type_counts = indexes["reporting_entity_type"].value_counts(dropna=False)
        top_entities = indexes["reporting_entity_name"].value_counts(dropna=False).head(15)
        lines += [
            "## 3. Reporting Entities",
            "",
            f"- **Parsed index files:** {len(indexes):,}",
            f"- **Distinct entity names:** {indexes['reporting_entity_name'].nunique():,}",
            "",
            "### Entity type distribution",
            "",
            entity_type_counts.to_markdown(),
            "",
            "### Top 15 reporting entities (by index file count)",
            "",
            top_entities.to_markdown(),
            "",
        ]

    # -- Section 4: Plan Distribution --
    if not plans.empty:
        plans_per_index = plans.groupby("index_file_id").size()
        market_type = plans["plan_market_type"].value_counts(dropna=False)
        id_type = plans["plan_id_type"].value_counts(dropna=False)
        lines += [
            "## 4. Plan Distribution",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total plan rows | {len(plans):,} |",
            f"| Distinct plan names | {plans['plan_name'].nunique():,} |",
            f"| Mean plans per index | {plans_per_index.mean():.2f} |",
            f"| Median plans per index | {plans_per_index.median():.2f} |",
            f"| Max plans in one index | {plans_per_index.max():,} |",
            "",
            "### Plan market type distribution",
            "",
            market_type.to_markdown(),
            "",
            "### Plan ID type distribution",
            "",
            id_type.to_markdown(),
            "",
        ]

    # -- Section 5: Referenced Files --
    if not refs.empty:
        refs_per_index = refs.groupby("index_file_id").size()
        file_type_counts = refs["file_type"].value_counts(dropna=False)

        # find the most reused URLs across index files
        reused = (
            refs.groupby("location_url")
            .agg(
                reference_count=("location_url", "size"),
                distinct_index_files=("index_file_id", "nunique"),
            )
            .sort_values("reference_count", ascending=False)
            .head(15)
        )

        lines += [
            "## 5. Referenced Machine-Readable Files",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total referenced file rows | {len(refs):,} |",
            f"| Distinct referenced URLs | {refs['location_url'].nunique():,} |",
            f"| Mean refs per index | {refs_per_index.mean():.2f} |",
            "",
            "### File type split",
            "",
            file_type_counts.to_markdown(),
            "",
            "### Top 15 most reused referenced URLs",
            "",
            reused.to_markdown(),
            "",
        ]

    # -- Section 6: Data Quality Findings --
    quality_items = []
    if not indexes.empty:
        null_entity = indexes["reporting_entity_name"].isna().sum()
        null_version = indexes["version"].isna().sum()
        if null_entity:
            quality_items.append(f"- {null_entity:,} index files have **null reporting_entity_name**.")
        if null_version:
            quality_items.append(f"- {null_version:,} index files have **null version**.")
    if not plans.empty:
        null_plan_name = plans["plan_name"].isna().sum()
        null_plan_id = plans["plan_id"].isna().sum()
        if null_plan_name:
            quality_items.append(f"- {null_plan_name:,} plans have **null plan_name**.")
        if null_plan_id:
            quality_items.append(f"- {null_plan_id:,} plans have **null plan_id**.")
    if not refs.empty:
        null_url = refs["location_url"].isna().sum()
        if null_url:
            quality_items.append(f"- {null_url:,} referenced files have **null location_url**.")

    if quality_items:
        lines += ["## 6. Data Quality Findings", ""] + quality_items + [""]
    else:
        lines += ["## 6. Data Quality Findings", "", "No data quality issues detected.", ""]

    # -- Section 7: Production Recommendations --
    lines += [
        "## 7. Production Recommendations",
        "",
        "- **Orchestration:** Schedule the pipeline with Apache Airflow or Azure Data Factory.",
        "- **Storage:** Persist raw JSON in cloud object storage (S3/ADLS); curated Parquet in Snowflake.",
        "- **Data Quality:** Add automated checks for missing fields, malformed URLs, duplicate plans, and row-count anomalies.",
        "- **Incremental Loads:** Track `last_updated_on` to avoid re-downloading unchanged files.",
        "- **Monitoring:** Set up alerts on download failures, parse errors, and volume anomalies.",
        "- **CI/CD:** Version-control DDL, Python scripts, and dbt models. Deploy via GitHub Actions.",
        "- **Security:** Rotate Snowflake credentials via secrets manager; encrypt data at rest.",
        "",
    ]

    report_text = "\n".join(lines)
    Path(args.report_output).write_text(report_text, encoding="utf-8")
    print(f"Insights report written to {args.report_output}")
    print(f"Report length: {len(report_text):,} characters")


if __name__ == "__main__":
    main()
