"""
06_load_to_snowflake.py
OPTIONAL step - loads the processed Parquet files into Snowflake tables.

Requires: pip install snowflake-connector-python
Also requires these environment variables to be set:
  SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
  SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA
"""
import os
from pathlib import Path

import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

# mapping of Snowflake table name -> local parquet file path
TABLES = {
    "INDEX_FILES": "data/processed/index_files.parquet",
    "REPORTING_ENTITIES": "data/processed/reporting_entities.parquet",
    "PLANS": "data/processed/plans.parquet",
    "REFERENCED_FILES": "data/processed/referenced_files.parquet",
}


def get_connection():
    """Connect to Snowflake using credentials from env vars."""
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )


def main():
    conn = get_connection()
    try:
        for table_name, path in TABLES.items():
            p = Path(path)
            if not p.exists():
                print(f"Skipping {table_name}; missing {path}")
                continue

            df = pd.read_parquet(p)

            # Snowflake expects uppercase column names
            df.columns = [c.upper() for c in df.columns]

            # write_pandas handles staging and COPY INTO for us
            success, nchunks, nrows, _ = write_pandas(
                conn, df, table_name, auto_create_table=True, overwrite=True
            )
            print(f"{table_name}: success={success}, chunks={nchunks}, rows={nrows}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
