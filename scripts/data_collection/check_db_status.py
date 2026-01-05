#!/usr/bin/env python3
"""Quick script to check database status."""

import sqlite3
import os
import sys

dbs = [".cache/consolidated_historical.db", ".cache/options_historical.db"]

for db_path in dbs:
    print(f"\n{'='*60}")
    print(f"Database: {db_path}")
    print("=" * 60)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables: {tables}")

        if tables:
            table_name = tables[0][0]

            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total = cursor.fetchone()[0]
            print(f"\nTotal records: {total:,}")

            # Check for underlying_price column
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            has_underlying_price = any(col[1] == "underlying_price" for col in columns)

            if has_underlying_price:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE underlying_price IS NOT NULL")
                with_price = cursor.fetchone()[0]

                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE underlying_price IS NULL")
                without_price = cursor.fetchone()[0]

                print(f"With underlying_price: {with_price:,} ({100*with_price/total:.1f}%)")
                print(f"Missing underlying_price: {without_price:,} ({100*without_price/total:.1f}%)")
            else:
                print("No underlying_price column found")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")
