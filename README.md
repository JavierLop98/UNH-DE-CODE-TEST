# UHC Transparency in Coverage — Data Engineering Technical Task

## Overview

End-to-end data pipeline that extracts, transforms and analyzes the first 1,000 UHC Transparency in Coverage index files.

> **Task:** Download UHC index files from [https://transparency-in-coverage.uhc.com/](https://transparency-in-coverage.uhc.com/), parse the data, store it locally, and present meaningful insights.

## Architecture

```text
                    UHC Transparency Site
                    (JavaScript SPA + REST API)
                            |
                            v
        +---- 01_discover_index_files.py ----+
        |  GET /api/v1/uhc/blobs/            |
        |  Filter *_index.json (first 1000)  |
        +------------+---------------------- +
                     |
                     v
        data/processed/index_manifest.csv
                     |
                     v
        +---- 02_download_index_files.py ----+
        |  Streaming download + retries      |
        |  Rate-limit delay + size guard     |
        +------------+---------------------- +
                     |
                     v
        data/raw/*.json + data/processed/download_log.csv
                     |
                     v
        +---- 03_parse_index_files.py -------+
        |  Normalize JSON -> 4 Parquet tables|
        |  index_files, entities,            |
        |  plans, referenced_files           |
        +------------+---------------------- +
                     |
                     v
        data/processed/*.parquet
                     |
                     v
        +---- 04_generate_insights.py -------+
        |  Aggregations, distributions,      |
        |  data quality, recommendations     |
        +------------+---------------------- +
                     |
                     v
        reports/insights_summary.md
                     |
                     v
        +---- 05_advanced_insights.py -------+
        |  Charts (matplotlib/seaborn),      |
        |  extended analysis                 |
        +------------+---------------------- +
                     |
                     v
        reports/charts/*.png + reports/extended_insights.md
```

## Data Model

The pipeline produces four normalized tables stored as Parquet:

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `index_files` | One row per parsed JSON file | `index_file_id`, `reporting_entity_name`, `reporting_entity_type`, `version` |
| `reporting_entities` | Entity metadata | `reporting_entity_name`, `reporting_entity_type` |
| `plans` | Plans within each index file | `plan_key`, `plan_name`, `plan_id`, `plan_id_type`, `plan_market_type` |
| `referenced_files` | In-network and allowed-amount file URLs | `referenced_file_key`, `file_type`, `location_url` |

All tables are linked by `index_file_id`. Plans link to referenced files via `plan_key`.

## Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Run the Pipeline

```bash
# Step 1: Discover index files from UHC API (~15 seconds)
python src/01_discover_index_files.py --limit 1000

# Step 2: Download index JSON files (~35 min for 1000 files)
python src/02_download_index_files.py --limit 1000

# Step 3: Parse JSON files into normalized Parquet tables (~1 min)
python src/03_parse_index_files.py

# Step 4: Generate insights report (~30 sec)
python src/04_generate_insights.py

# Step 5: Generate charts and extended analysis (~10 sec)
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

Requires `pip install snowflake-connector-python` (not included in requirements.txt by default).

1. Set environment variables (see `config.example.env`).
2. Run:

```bash
python src/06_load_to_snowflake.py
```

DDL is in [`sql/create_tables.sql`](sql/create_tables.sql). Sample queries in [`sql/insights.sql`](sql/insights.sql).

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **API instead of scraping** | The UHC site is a JavaScript SPA. The `/api/v1/uhc/blobs/` endpoint returns JSON directly, no browser automation needed. |
| **Streaming downloads** | Avoids loading entire files into memory. |
| **Retry with exponential backoff** | UHC API occasionally returns 5xx errors. Three retries with 2/4/8s delays handle this. |
| **Size guard (512 MB)** | Skips unexpectedly large files to protect local disk. |
| **Parquet** | Columnar format, good compression, works with Snowflake/Spark/Pandas. |
| **Separate parse from download** | Failed downloads don't block analysis of successfully downloaded files. |
| **Normalized data model** | Avoids nested structures, enables clean SQL-style joins. |

## Project Structure

```
UNH-DE-CODE-TEST/
├── src/
│   ├── 01_discover_index_files.py   # API-based file discovery
│   ├── 02_download_index_files.py   # Streaming download with retries
│   ├── 03_parse_index_files.py      # JSON -> Parquet normalization
│   ├── 04_generate_insights.py      # Analytics and reporting
│   ├── 05_advanced_insights.py      # Charts and extended analysis
│   ├── 06_load_to_snowflake.py      # Optional Snowflake loader
│   └── utils/
│       ├── __init__.py
│       └── io_utils.py
├── sql/
│   ├── create_tables.sql
│   └── insights.sql
├── data/
│   ├── raw/                         # Downloaded JSON files (git-ignored)
│   └── processed/                   # Parquet + logs (git-ignored)
├── reports/
│   ├── insights_summary.md
│   ├── extended_insights.md
│   └── charts/                      # 11 PNG charts
├── requirements.txt
├── config.example.env
└── README.md
```

## Assumptions

- The task focuses on **index files** (table of contents), not the multi-GB in-network rate files they reference.
- The pipeline handles missing, malformed, or empty files gracefully.
- Parquet files serve as the analytical layer; Snowflake loading is optional.
- The UHC API endpoint is undocumented and may change.
