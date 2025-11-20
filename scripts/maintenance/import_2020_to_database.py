#!/usr/bin/env python3
"""
Import 2020 File Cache to Database (Background Task)

Purpose:
    Import 2020 GEX data from file cache into database for redundancy.
    Treats file cache as temporary (Redis-like) and database as permanent storage.

Background:
    - 2020 data exists in file cache (.cache/gex_data/SPY/2020-*/)
    - Database only has 2024 data (252 days)
    - Phase 4 currently works via file cache fallback
    - This import provides redundancy and consistency

Usage:
    python scripts/maintenance/import_2020_to_database.py [--dry-run]

Architecture:
    File Cache (Redis analogy):
        - Temporary, fast access
        - Can be regenerated from API
        - Used as fallback when database empty

    Database (Storage analogy):
        - Permanent, single source of truth
        - Indexed for fast queries
        - Preferred data source

Related: Phase 4 validation, Issue #89
"""

import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def import_2020_to_database(dry_run: bool = False):
    """
    Import 2020 file cache data into database.

    Args:
        dry_run: If True, print actions without executing
    """
    cache_dir = PROJECT_ROOT / '.cache' / 'gex_data' / 'SPY'
    db_path = PROJECT_ROOT / '.cache' / 'gex_database.db'

    # Get all 2020 dates
    all_2020_dates = sorted([
        d.name for d in cache_dir.iterdir()
        if d.is_dir() and d.name.startswith('2020')
    ])

    logger.info(f"╔{'═' * 58}╗")
    logger.info(f"║{' 2020 File Cache → Database Import ':^58}║")
    logger.info(f"╚{'═' * 58}╝")
    logger.info(f"\nFound {len(all_2020_dates)} days in file cache")
    logger.info(f"Date range: {all_2020_dates[0]} to {all_2020_dates[-1]}")

    if dry_run:
        logger.info(f"\n⚠️  DRY RUN MODE - No changes will be made")

    # Check database
    if not db_path.exists():
        logger.error(f"\n❌ Database not found: {db_path}")
        return

    # Process each date
    imported = 0
    skipped = 0
    errors = []

    logger.info(f"\nProcessing...")

    with sqlite3.connect(db_path) as conn:
        for i, date in enumerate(all_2020_dates):
            gex_file = cache_dir / date / 'gex_summary.json'

            if not gex_file.exists():
                skipped += 1
                errors.append(f"{date}: Missing gex_summary.json")
                continue

            try:
                # Load file cache data
                with open(gex_file) as f:
                    data = json.load(f)

                # Extract fields
                symbol = data.get('symbol', 'SPY')
                spot_price = data.get('spot_price', 0)
                total_gex = data.get('total_gex', 0)
                net_gex = data.get('net_gex', total_gex)
                call_gex = data.get('call_gex', 0)
                put_gex = data.get('put_gex', 0)

                # Database expects net_call_gex and net_put_gex
                net_call_gex = call_gex
                net_put_gex = put_gex

                # Insert into database
                if not dry_run:
                    conn.execute("""
                        INSERT OR REPLACE INTO daily_gex_metrics
                        (symbol, date, spot_price, total_gex, net_call_gex, net_put_gex,
                         gamma_flip_point, flip_ratio, gex_regime, data_quality_score,
                         options_count, validation_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol, date, spot_price, total_gex, net_call_gex, net_put_gex,
                        None, None, None, 100, 0, 'imported_from_cache'
                    ))

                imported += 1

                # Progress
                if (i + 1) % 50 == 0:
                    logger.info(f"  Progress: {i + 1}/{len(all_2020_dates)} days...")

            except Exception as e:
                skipped += 1
                errors.append(f"{date}: {str(e)}")

        if not dry_run:
            conn.commit()

    # Summary
    logger.info(f"\n{'═' * 60}")
    logger.info(f"Import Summary")
    logger.info(f"{'═' * 60}")
    logger.info(f"Total dates: {len(all_2020_dates)}")
    logger.info(f"Imported: {imported}")
    logger.info(f"Skipped: {skipped}")
    logger.info(f"Errors: {len(errors)}")

    if errors:
        logger.info(f"\n❌ Errors:")
        for error in errors[:10]:  # Show first 10
            logger.info(f"  - {error}")
        if len(errors) > 10:
            logger.info(f"  ... and {len(errors) - 10} more")

    if not dry_run and imported > 0:
        logger.info(f"\n✅ Imported {imported} days to database")
        logger.info(f"\nVerify with:")
        logger.info(f"  sqlite3 .cache/gex_database.db \"SELECT COUNT(*) FROM daily_gex_metrics WHERE date LIKE '2020%';\"")
    elif dry_run:
        logger.info(f"\n✅ Dry run complete - would import {imported} days")
        logger.info(f"\nRun without --dry-run to execute import")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Import 2020 file cache to database')
    parser.add_argument('--dry-run', action='store_true', help='Show actions without executing')
    args = parser.parse_args()

    import_2020_to_database(dry_run=args.dry_run)
