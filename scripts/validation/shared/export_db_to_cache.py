#!/usr/bin/env python3
"""Export GEX from database to cache parquet files.

The Sequential GEX validation requires cache parquet files, but we have
2020 data only in the database. This script bridges that gap.

Issue: #111 (Test 4)
"""

import logging
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd

from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Export database GEX to cache parquet files."""

    logger.info("Exporting 2020 GEX from database to cache parquet files...")

    # Connect to database
    db_path = ".cache/consolidated_historical.db"
    conn = sqlite3.connect(db_path)

    # Get all 2020 dates
    query = """
        SELECT
            date,
            symbol,
            spot_price,
            total_gex,
            net_call_gex,
            net_put_gex,
            options_count
        FROM daily_gex_metrics
        WHERE date BETWEEN '2020-01-01' AND '2020-12-31'
        ORDER BY date
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    logger.info(f"Found {len(df)} days of 2020 data in database")

    # Initialize cache manager
    cache = UnifiedCacheManager()

    # Export each day to cache parquet
    success_count = 0
    fail_count = 0

    for idx, row in df.iterrows():
        trade_date = row["date"]

        try:
            # Create GEX summary dict in expected format
            gex_summary = {
                "date": trade_date,
                "symbol": row["symbol"],
                "total_gex": float(row["total_gex"]),
                "net_call_gex": float(row["net_call_gex"]),
                "net_put_gex": float(row["net_put_gex"]),
                "spot_price": float(row["spot_price"]),
                "options_count": int(row["options_count"]),
                "source": "database_export",
            }

            # Save to cache using GEXCacheManager format
            cache_file = Path(f".cache/gex_summary_{trade_date}.parquet")
            summary_df = pd.DataFrame([gex_summary])
            summary_df.to_parquet(cache_file, engine="pyarrow")

            success_count += 1

            if success_count % 50 == 0:
                logger.info(f"Exported {success_count} days...")

        except Exception as e:
            logger.error(f"Failed to export {trade_date}: {e}")
            fail_count += 1

    logger.info(f"\nExport complete!")
    logger.info(f"  Success: {success_count} days")
    logger.info(f"  Failed: {fail_count} days")
    logger.info(f"  Cache files created in: .cache/gex_summary_2020-*.parquet")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
