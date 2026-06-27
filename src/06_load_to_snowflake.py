"""
06_load_to_snowflake.py
OPTIONAL step - loads the processed Parquet files into Snowflake tables.

Requires: pip install "snowflake-connector-python[pandas]" python-dotenv
"""
import os
from pathlib import Path

import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from dotenv import load_dotenv

# mapping of Snowflake table name -> local parquet file path
TABLES = {
    "INDEX_FILES": "data/processed/index_files.parquet",
    "REPORTING_ENTITIES": "data/processed/reporting_entities.parquet",
    "PLANS": "data/processed/plans.parquet",
    "REFERENCED_FILES": "data/processed/referenced_files.parquet",
}


def get_connection():
    """Connect to Snowflake using credentials from env vars."""
    load_dotenv()  # Load variables from .env file automatically
    
    # We connect WITHOUT database/schema/warehouse first so it doesn't fail
    # if they haven't been created yet.
    kwargs = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "role": os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
    }

    # Support Single Sign-On (Google/Microsoft) via browser
    if os.environ.get("SNOWFLAKE_AUTHENTICATOR") == "externalbrowser":
        kwargs["authenticator"] = "externalbrowser"
    else:
        kwargs["password"] = os.environ.get("SNOWFLAKE_PASSWORD")

    return snowflake.connector.connect(**kwargs)


def bootstrap_environment(conn):
    """Ensure the database, warehouse and schema exist."""
    load_dotenv()
    db = os.environ.get("SNOWFLAKE_DATABASE", "UHC_TIC")
    schema = os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC")
    wh = os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    
    print(f"Ensuring Warehouse '{wh}', Database '{db}', and Schema '{schema}' exist...")
    cursor = conn.cursor()
    try:
        # Create resources if they don't exist
        cursor.execute(f"CREATE WAREHOUSE IF NOT EXISTS {wh} WAREHOUSE_SIZE = 'X-SMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db};")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {db}.{schema};")
        
        # Use the resources for the current session
        cursor.execute(f"USE WAREHOUSE {wh};")
        cursor.execute(f"USE DATABASE {db};")
        cursor.execute(f"USE SCHEMA {schema};")
    finally:
        cursor.close()


def main():
    print("Connecting to Snowflake...")
    conn = get_connection()
    try:
        bootstrap_environment(conn)
        
        for table_name, path in TABLES.items():
            p = Path(path)
            if not p.exists():
                print(f"Skipping {table_name}; missing {path}")
                continue

            print(f"Loading {path} into Snowflake table {table_name}...")
            df = pd.read_parquet(p)

            # Snowflake expects uppercase column names
            df.columns = [c.upper() for c in df.columns]

            # write_pandas handles staging and COPY INTO for us
            success, nchunks, nrows, _ = write_pandas(
                conn, df, table_name, auto_create_table=True, overwrite=True
            )
            print(f"  -> success={success}, chunks={nchunks}, rows={nrows}")
            
    except Exception as e:
        print(f"Error loading to Snowflake: {e}")
    finally:
        conn.close()
        print("Snowflake connection closed.")


if __name__ == "__main__":
    main()
