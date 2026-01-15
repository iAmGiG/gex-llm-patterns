#!/usr/bin/env python
"""Backfill underlying prices for existing options data.

This script efficiently backfills underlying_price for all existing options
records that have NULL values. It uses a single API call per symbol to fetch
all historical prices, then performs bulk SQL updates.

Usage:
    python scripts/data_collection/backfill_underlying_prices.py
    python scripts/data_collection/backfill_underlying_prices.py --symbols TQQQ SQQQ
    python scripts/data_collection/backfill_underlying_prices.py --dry-run
"""

import argparse
import os
import logging
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd

from gex_db_infrastructure.data_sources.alpha_vantage_gex import AlphaVantageGEXClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_symbols_needing_backfill(db_path: str) -> list:
    """Get list of symbols with NULL underlying_price."""
    conn = sqlite3.connect(db_path)
    query = """
    SELECT DISTINCT symbol
    FROM options_chains
    WHERE underlying_price IS NULL
    ORDER BY symbol
    """
    result = pd.read_sql_query(query, conn)
    conn.close()
    return result["symbol"].tolist()


def get_dates_needing_backfill(db_path: str, symbol: str) -> list:
    """Get list of trading dates with NULL underlying_price for a symbol."""
    conn = sqlite3.connect(db_path)
    query = """
    SELECT DISTINCT trading_date
    FROM options_chains
    WHERE symbol = ? AND underlying_price IS NULL
    ORDER BY trading_date
    """
    result = pd.read_sql_query(query, conn, params=(symbol,))
    conn.close()
    return result["trading_date"].tolist()


def fetch_all_prices_for_symbol(client: AlphaVantageGEXClient, symbol: str) -> dict:
    """Fetch all historical prices for a symbol in one API call.

    Returns:
        Dict mapping date string (YYYY-MM-DD) to close price
    """
    logger.info(f"Fetching full price history for {symbol}...")

    # Get full history (20+ years)
    df = client.fetch_underlying_data(symbol, "2019-01-01", "2025-12-31")

    if df is None or df.empty:
        logger.warning(f"No price data returned for {symbol}")
        return {}

    # Convert to dict: date -> close price
    prices = {}
    for idx, row in df.iterrows():
        if hasattr(idx, "strftime"):
            date_str = idx.strftime("%Y-%m-%d")
        else:
            date_str = str(idx)[:10]
        prices[date_str] = float(row["close"])

    logger.info(f"Got {len(prices)} price points for {symbol}")
    return prices


def backfill_symbol(db_path: str, symbol: str, prices: dict, dry_run: bool = False) -> int:
    """Backfill underlying_price for all records of a symbol.

    Args:
        db_path: Path to SQLite database
        symbol: Stock symbol
        prices: Dict mapping date to close price
        dry_run: If True, don't actually update

    Returns:
        Number of dates updated
    """
    dates_needing_update = get_dates_needing_backfill(db_path, symbol)

    if not dates_needing_update:
        logger.info(f"{symbol}: No dates need backfill")
        return 0

    logger.info(f"{symbol}: {len(dates_needing_update)} dates need backfill")

    if dry_run:
        matched = sum(1 for d in dates_needing_update if d in prices)
        logger.info(f"{symbol}: [DRY RUN] Would update {matched}/{len(dates_needing_update)} dates")
        return matched

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    updated_count = 0
    missing_prices = []

    for date in dates_needing_update:
        if date in prices:
            price = prices[date]
            cursor.execute(
                """
                UPDATE options_chains
                SET underlying_price = ?
                WHERE symbol = ? AND trading_date = ?
                """,
                (price, symbol, date),
            )
            updated_count += 1

            if updated_count % 100 == 0:
                conn.commit()
                logger.info(f"{symbol}: Updated {updated_count}/{len(dates_needing_update)} dates...")
        else:
            missing_prices.append(date)

    conn.commit()
    conn.close()

    if missing_prices:
        logger.warning(f"{symbol}: Could not find prices for {len(missing_prices)} dates")
        if len(missing_prices) <= 10:
            logger.warning(f"  Missing dates: {missing_prices}")

    logger.info(f"{symbol}: Successfully backfilled {updated_count} dates")
    return updated_count


def main():
    parser = argparse.ArgumentParser(description="Backfill underlying prices for options data")
    parser.add_argument("--db", default=".cache/options_historical.db", help="Database path")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to backfill (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without changing data")
    args = parser.parse_args()

    db_path = args.db

    # Check database exists
    if not Path(db_path).exists():
        logger.error(f"Database not found: {db_path}")
        return 1

    # Get symbols to process
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = get_symbols_needing_backfill(db_path)

    if not symbols:
        logger.info("No symbols need backfill!")
        return 0

    logger.info(f"Symbols to backfill: {symbols}")

    # Initialize API client
    client = AlphaVantageGEXClient()

    total_updated = 0

    for i, symbol in enumerate(symbols, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {symbol} ({i}/{len(symbols)})")
        logger.info(f"{'='*60}")

        # Fetch all prices for this symbol (one API call)
        prices = fetch_all_prices_for_symbol(client, symbol)

        if not prices:
            logger.warning(f"Skipping {symbol} - no price data")
            continue

        # Backfill all dates for this symbol
        updated = backfill_symbol(db_path, symbol, prices, dry_run=args.dry_run)
        total_updated += updated

        # Rate limit between symbols
        if i < len(symbols):
            logger.info("Waiting 2s before next symbol...")
            time.sleep(2)

    logger.info(f"\n{'='*60}")
    logger.info(f"BACKFILL COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total dates updated: {total_updated}")

    # Show verification stats
    conn = sqlite3.connect(db_path)
    query = """
    SELECT
        COUNT(*) as total_records,
        COUNT(underlying_price) as with_price,
        COUNT(*) - COUNT(underlying_price) as missing_price
    FROM options_chains
    """
    stats = pd.read_sql_query(query, conn)
    conn.close()

    logger.info(f"\nDatabase stats:")
    logger.info(f"  Total records: {stats['total_records'].iloc[0]:,}")
    logger.info(f"  With underlying_price: {stats['with_price'].iloc[0]:,}")
    logger.info(f"  Missing underlying_price: {stats['missing_price'].iloc[0]:,}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
