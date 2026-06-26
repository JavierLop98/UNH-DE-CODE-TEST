import os
from pathlib import Path

import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

TABLES = {
    "INDEX_FILES": "data/processed/index_files.parquet",
    "REPORTING_ENTITIES": "data/processed/reporting_entities.parquet",
    "PLANS": "data/processed/plans.parquet",
    "REFERENCED_FILES": "data/processed/referenced_files.parquet",
}


def get_connection():
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
            df.columns = [c.upper() for c in df.columns]
            success, nchunks, nrows, _ = write_pandas(conn, df, table_name, auto_create_table=True, overwrite=True)
            print(f"{table_name}: success={success}, chunks={nchunks}, rows={nrows}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
