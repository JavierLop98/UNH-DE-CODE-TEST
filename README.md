# UHC Transparency in Coverage — Data Engineering Technical Task

## Overview

End-to-end data engineering pipeline that extracts, transforms and analyzes the first 1,000 UHC Transparency in Coverage index JSON files.

> **Task:** Download UHC index files from [https://transparency-in-coverage.uhc.com/](https://transparency-in-coverage.uhc.com/), parse the data, store it locally, and present meaningful insights.

## Architecture

```text
                    UHC Transparency Site
                    (JavaScript SPA + REST API)
                            │
                            ▼
        ┌──── 01_discover_index_files.py ────┐
        │  GET /api/v1/uhc/blobs/            │
        │  Filter *_index.json (first 1000)  │
        └────────────┬───────────────────────┘
                     │
                     ▼
        data/processed/index_manifest.csv
                     │
                     ▼
        ┌──── 02_download_index_files.py ────┐
        │  Streaming download + retries      │
        │  Rate-limit delay + size guard     │
        └────────────┬───────────────────────┘
                     │
                     ▼
        data/raw/*.json + data/processed/download_log.csv
                     │
                     ▼
        ┌──── 03_parse_index_files.py ───────┐
        │  Normalize JSON → 4 Parquet tables │
        │  index_files, entities,            │
        │  plans, referenced_files           │
        └────────────┬───────────────────────┘
                     │
                     ▼
        data/processed/*.parquet
                     │
                     ▼
        ┌──── 04_generate_insights.py ───────┐
        │  Aggregations, distributions,      │
        │  data quality, recommendations     │
        └────────────┬───────────────────────┘
                     │
                     ▼
        reports/insights_summary.md
```

## Data Model

The pipeline produces four normalized analytical tables:

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `index_files` | One row per parsed JSON file | `index_file_id`, `reporting_entity_name`, `reporting_entity_type`, `version` |
| `reporting_entities` | Entity metadata (denormalized for convenience) | `reporting_entity_name`, `reporting_entity_type` |
| `plans` | Plans within each index file's reporting structure | `plan_key`, `plan_name`, `plan_id`, `plan_id_type`, `plan_market_type` |
| `referenced_files` | In-network and allowed-amount file URLs | `referenced_file_key`, `file_type`, `location_url` |

All tables are linked by `index_file_id`. Plans link to referenced files via `plan_key`.

## Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Run the Pipeline

```bash
# Step 1: Discover index files from UHC API (finds ~86k+ blobs, filters first 1000 index files)
python src/01_discover_index_files.py --limit 1000

# Step 2: Download index JSON files with retries and progress bar
python src/02_download_index_files.py --limit 1000

# Step 3: Parse JSON files into normalized Parquet tables
python src/03_parse_index_files.py

# Step 4: Generate Markdown insights report
python src/04_generate_insights.py

# Step 5: Generate charts and advanced insights
python src/05_advanced_insights.py
```

### Command-Line Options

| Script | Flag | Default | Description |
|--------|------|---------|-------------|
| `01` | `--limit` | 1000 | Max index files to discover |
| `01` | `--timeout` | 120 | HTTP timeout for API call |
| `02` | `--limit` | 1000 | Max files to download |
| `02` | `--delay` | 0.1 | Seconds between downloads |
| `02` | `--max-size-mb` | 512 | Skip files larger than this |
| `02` | `--timeout` | 60 | Per-file download timeout |

## Optional: Load to Snowflake

1. Create a Snowflake trial account.
2. Set environment variables:

```bash
export SNOWFLAKE_ACCOUNT="<account>"
export SNOWFLAKE_USER="<user>"
export SNOWFLAKE_PASSWORD="<password>"
export SNOWFLAKE_WAREHOUSE="<warehouse>"
export SNOWFLAKE_DATABASE="<database>"
export SNOWFLAKE_SCHEMA="<schema>"
```

3. Run:

```bash
python src/06_load_to_snowflake.py
```

DDL for explicit table creation is in [`sql/create_tables.sql`](sql/create_tables.sql).
Sample insight queries are in [`sql/insights.sql`](sql/insights.sql).

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **API instead of scraping** | The UHC site is a JavaScript SPA. The `/api/v1/uhc/blobs/` endpoint returns structured JSON directly, eliminating the need for browser automation. |
| **Streaming downloads** | Index files can vary in size. Streaming avoids loading entire files into memory. |
| **Retry with exponential backoff** | The UHC API occasionally returns 5xx errors. Three retries with 2/4/8 second delays handle transient failures. |
| **Size guard** | Files exceeding 512 MB are skipped to protect local storage. |
| **Parquet output** | Columnar format enables efficient analytical queries and integrates well with Snowflake, Spark, and Pandas. |
| **Separated parse from download** | Failed downloads don't block analysis. Files can be re-downloaded without re-parsing. |
| **Normalized data model** | Separating indexes → plans → referenced files avoids deeply nested structures and enables clean joins. |

## Project Structure

```
UNH-DE-CODE-TEST/
├── src/
│   ├── 01_discover_index_files.py   # API-based file discovery
│   ├── 02_download_index_files.py   # Streaming download with retries
│   ├── 03_parse_index_files.py      # JSON → Parquet normalization
│   ├── 04_generate_insights.py      # Analytics and reporting
│   ├── 05_advanced_insights.py      # Charts and deep analysis
│   ├── 06_load_to_snowflake.py      # Optional Snowflake loader
│   └── utils/
│       ├── __init__.py
│       └── io_utils.py              # File I/O helpers
├── sql/
│   ├── create_tables.sql            # Snowflake DDL
│   └── insights.sql                 # Analytical queries
├── data/
│   ├── raw/                         # Downloaded JSON files (git-ignored)
│   └── processed/                   # Parquet tables, manifests, logs (git-ignored)
├── reports/
│   └── insights_summary.md          # Generated insights (git-ignored)
├── notebooks/                       # Jupyter notebooks (optional)
├── requirements.txt
├── config.example.env
├── .gitignore
└── README.md
```

## Interview Walkthrough Guide

1. **Problem Understanding:** Explain the CMS Transparency in Coverage mandate and why UHC publishes these files.
2. **Data Access Challenge:** The site is a JavaScript SPA — demonstrate how you discovered and used the API endpoint.
3. **Pipeline Design:** Walk through the four-step architecture (discover → download → parse → insights).
4. **Resilience:** Show retry logic, size guards, download logging, and idempotent re-runs.
5. **Data Model:** Explain the normalized Parquet schema and how tables relate.
6. **Insights:** Present findings from `reports/insights_summary.md`.
7. **Production Path:** Discuss Airflow/ADF scheduling, Snowflake integration, CI/CD, monitoring, and data quality.

## Assumptions

- The task focuses on UHC **index files** (table of contents), not downloading the multi-gigabyte in-network rate files they reference.
- Some index files may be unavailable, malformed, or empty; the pipeline handles these gracefully.
- Local Parquet files serve as the analytical layer; Snowflake loading is optional.
- The UHC API endpoint is undocumented and may change without notice.
