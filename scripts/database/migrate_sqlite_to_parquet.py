import os
import sqlite3
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Configuration
DB_PATH = ".cache/options_historical.db"
PARQUET_ROOT = ".cache/parquet"
CHUNK_SIZE = 100000  # Process in chunks to keep memory low


def migrate_data():
    """
    Migrates data from SQLite to Partitioned Parquet.
    Partitioning: Symbol -> Year -> Quarter (Optional)
    """
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    # Get list of tables (assuming one table per symbol or a master table)
    # Adjust query based on your actual schema
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)

    print(f"Found {len(tables)} tables to migrate...")

    for idx, row in tables.iterrows():
        table_name = row["name"]
        print(f"Processing {table_name}...")

        # Read in chunks to handle large tables without OOM
        query = f"SELECT * FROM {table_name}"

        # Using pandas chunksize for memory efficiency
        for chunk in pd.read_sql(query, conn, chunksize=CHUNK_SIZE):
            # Ensure date column is datetime for partitioning
            if "date" in chunk.columns:
                chunk["date"] = pd.to_datetime(chunk["date"])
                chunk["year"] = chunk["date"].dt.year

            # Convert to PyArrow Table
            table = pa.Table.from_pandas(chunk)

            # Write to partitioned dataset
            # This creates folder structure: .cache/parquet/symbol=SPY/year=2024/part-xxx.parquet
            # If your table name IS the symbol, you can inject it as a column
            if "symbol" not in chunk.columns:
                # Assuming table name is the symbol, e.g., "SPY"
                # If table names are "options_SPY", do string manipulation here
                symbol_val = table_name.replace("options_", "")
                # We don't add the column to data, we use it for directory path

                output_path = Path(PARQUET_ROOT) / f"symbol={symbol_val}"
                output_path.mkdir(parents=True, exist_ok=True)

                # Write partition
                pq.write_to_dataset(
                    table,
                    root_path=PARQUET_ROOT,
                    partition_cols=["year"] if "year" in chunk.columns else None,
                    existing_data_behavior="overwrite_or_ignore",
                )

    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate_data()
