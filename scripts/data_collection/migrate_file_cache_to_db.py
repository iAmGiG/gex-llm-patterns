#!/usr/bin/env python3
"""
Migrate File Cache to Database - Issue #147

Backfills raw_options_chain table from existing file cache.

Usage:
    python scripts/data_collection/migrate_file_cache_to_db.py --symbol SPY --dry-run
    python scripts/data_collection/migrate_file_cache_to_db.py --symbol SPY
"""

import sys
import sqlite3
import argparse
import logging
from pathlib import Path
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cache.unified_cache import UnifiedCacheManager
from src.data_sources.historical_gex_builder import HistoricalGEXDatabaseBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_file_cache_to_database(
    symbol: str = 'SPY',
    cache_dir: Path = None,
    db_path: Path = None,
    dry_run: bool = False
):
    """
    Migrate all file cache data to database.

    Args:
        symbol: Stock symbol to migrate
        cache_dir: File cache root directory (default: .cache/gex_data)
        db_path: Database path (default: .cache/consolidated_historical.db)
        dry_run: If True, report only (no database writes)
    """
    # Setup paths
    if cache_dir is None:
        cache_dir = Path('.cache/gex_data')
    if db_path is None:
        db_path = Path('.cache/consolidated_historical.db')

    # Initialize managers
    cache = UnifiedCacheManager()
    builder = HistoricalGEXDatabaseBuilder(database_path=str(db_path))

    # Scan file cache for all trading days
    symbol_cache = cache_dir / symbol

    if not symbol_cache.exists():
        logger.error(f"Cache directory not found: {symbol_cache}")
        return

    # Get all date directories
    date_dirs = sorted([d for d in symbol_cache.iterdir() if d.is_dir()])

    logger.info(f"Found {len(date_dirs)} trading days in file cache")

    if dry_run:
        logger.info("DRY RUN MODE - No database writes will occur")

    # Migration stats
    success_count = 0
    skip_count = 0
    error_count = 0
    total_options = 0

    with sqlite3.connect(str(db_path)) as conn:
        for date_dir in tqdm(date_dirs, desc="Migrating"):
            trading_date = date_dir.name  # YYYY-MM-DD

            # Check if already migrated
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM raw_options_chain WHERE symbol = ? AND date = ?',
                (symbol, trading_date)
            )
            existing_count = cursor.fetchone()[0]

            if existing_count > 0:
                logger.debug(f"Skipping {trading_date} ({existing_count} options already in DB)")
                skip_count += 1
                continue

            # Load raw options from file cache
            try:
                # Get options data from cache
                options_df = cache.get_options_data(symbol, trading_date)

                if options_df is None or options_df.empty:
                    logger.warning(f"Empty options data for {trading_date}")
                    error_count += 1
                    continue

                # Get underlying price from GEX summary (if available)
                gex_summary = cache.gex_cache.get_gex_summary(symbol, trading_date)

                if gex_summary and 'spot_price' in gex_summary:
                    underlying_price = gex_summary['spot_price']
                elif gex_summary and 'underlying_price' in gex_summary:
                    underlying_price = gex_summary['underlying_price']
                elif 'underlying_price' in options_df.columns and not options_df['underlying_price'].isna().all():
                    # Try to get from options_df if available
                    underlying_price = options_df['underlying_price'].iloc[0]
                else:
                    logger.warning(f"No underlying price found for {trading_date}, skipping")
                    error_count += 1
                    continue

                # Store to database
                if not dry_run:
                    rows_inserted = builder.store_raw_options_chain(
                        conn=conn,
                        symbol=symbol,
                        date=trading_date,
                        options_df=options_df,
                        underlying_price=underlying_price
                    )
                    conn.commit()
                    total_options += rows_inserted
                    logger.info(f"Migrated {rows_inserted} options for {trading_date}")
                else:
                    logger.info(f"[DRY RUN] Would migrate {len(options_df)} options for {trading_date} (spot: ${underlying_price:.2f})")

                success_count += 1

            except Exception as e:
                logger.error(f"Error migrating {trading_date}: {e}")
                error_count += 1
                if not dry_run:
                    conn.rollback()
                continue

    # Report summary
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    print(f"Total days found:      {len(date_dirs)}")
    print(f"Successfully migrated: {success_count}")
    print(f"Already in database:   {skip_count}")
    print(f"Errors:                {error_count}")
    if not dry_run:
        print(f"Total options stored:  {total_options:,}")
    print("="*60)

    if dry_run:
        print("\nDRY RUN COMPLETE - No data was written to database")
        print(f"Run without --dry-run to perform actual migration")
    else:
        print(f"\nMigration complete! Database size:")
        import os
        db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"  {db_path}: {db_size_mb:.1f} MB")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Migrate file cache to database (Issue #147)')
    parser.add_argument('--symbol', default='SPY', help='Symbol to migrate')
    parser.add_argument('--cache-dir', type=Path, help='Cache directory')
    parser.add_argument('--db-path', type=Path, help='Database path')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report only, no database writes')

    args = parser.parse_args()

    migrate_file_cache_to_database(
        symbol=args.symbol,
        cache_dir=args.cache_dir,
        db_path=args.db_path,
        dry_run=args.dry_run
    )
