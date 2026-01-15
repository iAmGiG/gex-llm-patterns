"""
Database Rebuild Script - Fix GEX Corruption Issue

Rebuilds the consolidated_historical.db database with fresh GEX calculations
using the current GEXCalculator (post-Issue #80 enhancements).

Root Cause:
- Database was populated Oct 2, 2025 with OLD GEX calculation
- GEXCalculator updated Oct 9, 2025 (Issue #80)
- Database has stale values with 1000-4500x magnitude errors

This script:
1. Backs up existing corrupted database
2. Uses HistoricalGEXDatabaseBuilder with current GEXCalculator
3. Validates results match fresh calculations
4. Reports rebuild progress and quality metrics

Usage:
    python scripts/database/rebuild_gex_database.py --start-date 2024-01-01 --end-date 2024-12-31 --symbol SPY
"""

import argparse
import os
import logging
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from gex_db_infrastructure.cache.options_db_manager import SQLiteOptionsManager
from gex_db_infrastructure.cache.postgresql_options_manager import PostgreSQLOptionsManager
from gex_db_infrastructure.data_sources.historical_gex_builder import HistoricalGEXDatabaseBuilder
from gex_db_infrastructure.gex.gex_calculator import GEXCalculator
from src.utils.date_utils import date_range_trading_days

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def backup_database(db_path: Path) -> Path:
    """Create timestamped backup of existing database.

    Args:
        db_path: Path to database file

    Returns:
        Path to backup file
    """
    if not db_path.exists():
        logger.warning(f"No existing database to backup at {db_path}")
        return None

    # Create backup with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    backup_path = backup_dir / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"

    logger.info(f"Backing up database...")
    logger.info(f"  Source: {db_path}")
    logger.info(f"  Backup: {backup_path}")

    shutil.copy2(db_path, backup_path)

    # Verify backup
    if backup_path.exists():
        original_size = db_path.stat().st_size
        backup_size = backup_path.stat().st_size
        if original_size == backup_size:
            logger.info(f"✅ Backup successful ({backup_size / 1024 / 1024:.1f} MB)")
            return backup_path
        else:
            logger.error("❌ Backup size mismatch!")
            return None
    else:
        logger.error("❌ Backup failed!")
        return None


def validate_rebuild(db_path: Path, options_db: SQLiteOptionsManager, sample_dates: list) -> dict:
    """Validate rebuilt database against fresh calculations.

    Issue #180: Now uses SQLiteOptionsManager directly.

    Args:
        db_path: Path to rebuilt database
        options_db: SQLiteOptionsManager for fresh calculations
        sample_dates: List of dates to validate

    Returns:
        Validation report dict
    """
    logger.info(f"\nValidating rebuilt database ({len(sample_dates)} samples)...")

    conn = sqlite3.connect(db_path)
    gex_calc = GEXCalculator()

    validation_results = []

    for date in sample_dates:
        # Get database value
        cursor = conn.execute(
            "SELECT total_gex, spot_price FROM daily_gex_metrics WHERE date = ? AND symbol = 'SPY'", (date,)
        )
        row = cursor.fetchone()

        if not row:
            validation_results.append({"date": date, "status": "MISSING", "db_gex": None, "fresh_gex": None})
            continue

        db_gex = row[0]
        spot_price = row[1]

        # Issue #180: Get fresh calculation from SQLite
        options_data = options_db.get_options_chain("SPY", date)
        if options_data is None or options_data.empty:
            validation_results.append({"date": date, "status": "NO_OPTIONS_DATA", "db_gex": db_gex, "fresh_gex": None})
            continue

        try:
            fresh_calc = gex_calc.calculate_gex_profile(options_data, spot_price)
            fresh_gex = fresh_calc.get("net_gex", 0)

            # Check match (within 1%)
            if abs(fresh_gex) > 0:
                ratio = abs((db_gex - fresh_gex) / fresh_gex)
                match = ratio < 0.01  # Within 1%
            else:
                match = abs(db_gex) < 1e6  # Both near zero

            validation_results.append(
                {
                    "date": date,
                    "status": "MATCH" if match else "MISMATCH",
                    "db_gex": db_gex,
                    "fresh_gex": fresh_gex,
                    "ratio": ratio if "ratio" in locals() else None,
                }
            )

        except Exception as e:
            logger.error(f"Validation error for {date}: {e}")
            validation_results.append({"date": date, "status": "ERROR", "db_gex": db_gex, "error": str(e)})

    conn.close()

    # Calculate stats
    matches = sum(1 for r in validation_results if r["status"] == "MATCH")
    total = len(validation_results)

    report = {
        "total_validated": total,
        "matches": matches,
        "match_rate": (matches / total * 100) if total > 0 else 0,
        "results": validation_results,
    }

    logger.info(f"  Validation: {matches}/{total} matches ({report['match_rate']:.1f}%)")

    return report


def rebuild_database(db_path: Path, start_date: str, end_date: str, symbol: str = "SPY", force: bool = False):
    """Rebuild database with fresh GEX calculations.

    Args:
        db_path: Path to database file
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        symbol: Trading symbol
        force: Force rebuild without confirmation
    """
    logger.info("=" * 80)
    logger.info("DATABASE REBUILD - FIX GEX CORRUPTION")
    logger.info("=" * 80)

    # Backup existing database
    if db_path.exists():
        if not force:
            response = input(f"\n⚠️  This will rebuild {db_path}. Continue? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Rebuild cancelled.")
                return

        backup_path = backup_database(db_path)
        if not backup_path:
            logger.error("Backup failed! Aborting rebuild.")
            return

        # Remove old database
        db_path.unlink()
        logger.info(f"Removed old database")

    # Initialize builder with current GEXCalculator (use PostgreSQL by default)
    logger.info(f"\nInitializing builder with current GEXCalculator...")
    options_db = PostgreSQLOptionsManager()
    builder = HistoricalGEXDatabaseBuilder(database_path=str(db_path), options_db_manager=options_db)

    # Get trading days in range
    trading_days = date_range_trading_days(start_date, end_date)
    logger.info(f"\nRebuilding {len(trading_days)} trading days ({start_date} to {end_date})")

    # Build database
    logger.info(f"\nStarting rebuild...")
    try:
        builder.build_gex_database(symbols=[symbol], start_date=start_date, end_date=end_date)
        logger.info(f"Rebuild complete!")

    except Exception as e:
        logger.error(f"Rebuild failed: {e}")
        raise

    # Validate rebuild (Issue #180: use SQLiteOptionsManager)
    sample_dates = trading_days[:: max(1, len(trading_days) // 20)]  # Sample ~20 dates
    validation = validate_rebuild(db_path, options_db, sample_dates)

    if validation["match_rate"] >= 95:
        logger.info(f"\n✅ REBUILD SUCCESSFUL - {validation['match_rate']:.1f}% validation match")
    else:
        logger.warning(f"\n⚠️  REBUILD COMPLETED WITH WARNINGS - {validation['match_rate']:.1f}% validation match")

    # Show database stats
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM daily_gex_metrics WHERE symbol = ?", (symbol,))
    row_count = cursor.fetchone()[0]
    conn.close()

    logger.info(f"\nDatabase Statistics:")
    logger.info(f"  Path: {db_path}")
    logger.info(f"  Size: {db_path.stat().st_size / 1024 / 1024:.1f} MB")
    logger.info(f"  Rows: {row_count}")
    logger.info(f"  Symbol: {symbol}")
    logger.info(f"  Date Range: {start_date} to {end_date}")

    logger.info("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Rebuild GEX database with fresh calculations")
    parser.add_argument("--start-date", type=str, default="2024-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default="2024-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--symbol", type=str, default="SPY", help="Trading symbol (default: SPY)")
    parser.add_argument("--database", type=str, default=".cache/consolidated_historical.db", help="Database path")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    db_path = Path(args.database)

    rebuild_database(
        db_path=db_path, start_date=args.start_date, end_date=args.end_date, symbol=args.symbol, force=args.force
    )


if __name__ == "__main__":
    main()
