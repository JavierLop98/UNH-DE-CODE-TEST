# UHC Transparency In Coverage - Data Engineering Technical Task

This project implements an end-to-end data engineering workflow for the technical task:

> Download the first 1000 UHC Transparency in Coverage index JSON files, ingest and parse the data, store it locally / optionally in Snowflake, and present meaningful insights.

## Goals

- Discover the first 1000 `*_index.json` files published at the UHC Transparency in Coverage website.
- Download index files safely using streaming, retries and metadata logging.
- Parse relevant JSON fields into normalized analytical datasets.
- Store processed outputs as Parquet/CSV locally.
- Optionally load curated tables into Snowflake.
- Generate insight tables that can be discussed during the technical interview.

## Proposed Architecture

```text
UHC Transparency Site
        |
        v
01_discover_index_files.py
        |
        v
data/processed/index_manifest.csv
        |
        v
02_download_index_files.py
        |
        v
data/raw/*.json + data/processed/download_log.csv
        |
        v
03_parse_index_files.py
        |
        v
data/processed/index_files.parquet
 data/processed/reporting_entities.parquet
 data/processed/plans.parquet
 data/processed/referenced_files.parquet
        |
        v
04_generate_insights.py
        |
        v
reports/insights_summary.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Run locally

```bash
python src/01_discover_index_files.py --limit 1000
python src/02_download_index_files.py --limit 1000
python src/03_parse_index_files.py
python src/04_generate_insights.py
```

## Optional: Load to Snowflake

1. Create a Snowflake trial account.
2. Create a database/schema.
3. Set environment variables:

```bash
export SNOWFLAKE_ACCOUNT="<account>"
export SNOWFLAKE_USER="<user>"
export SNOWFLAKE_PASSWORD="<password>"
export SNOWFLAKE_WAREHOUSE="<warehouse>"
export SNOWFLAKE_DATABASE="<database>"
export SNOWFLAKE_SCHEMA="<schema>"
```

4. Run:

```bash
python src/05_load_to_snowflake.py
```

## Design Decisions

- Files are downloaded in streaming mode to avoid loading large JSON files into memory.
- Raw files are retained for auditability and reproducibility.
- Parsing is isolated from download logic so failed downloads do not block analysis of valid files.
- The output model separates index files, reporting entities, plans and referenced files.
- Insights include operational metrics, data quality findings and distribution analysis.

## Interview Walkthrough

Recommended walkthrough structure:

1. Explain the risk of very large JSON files and why streaming download was used.
2. Show the manifest and download log.
3. Walk through parsing logic and normalized model.
4. Show data quality checks and failed/skipped records.
5. Present insights from `reports/insights_summary.md`.
6. Explain how this would be productionized using Airflow/ADF, CI/CD, monitoring and alerts.

## Assumptions

- The task focuses on the UHC index files, not downloading every large machine-readable file referenced by each index.
- Some index files may be unavailable, malformed, duplicated or too large for the local environment.
- Local Parquet files are used as the main reproducible analytical layer; Snowflake loading is optional.
