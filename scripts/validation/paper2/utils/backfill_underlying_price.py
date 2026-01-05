#!/usr/bin/env python3
"""Backfill underlying_price from Alpha Vantage for SPY options data.

Fetches historical stock prices and updates PostgreSQL options_chains_partitioned
table with correct underlying_price values.

Usage:
    python /tmp/backfill_underlying_price.py --symbol SPY --start 2023-01-01 --end 2025-12-31
"""

import argparse
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_api_key():
    """Load Alpha Vantage API key from config"""
    config_path = Path('/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns/config/config.json')
    with open(config_path) as f:
        config = json.load(f)
    # Try premium key first, then regular
    return config.get('ALPHA_VANTAGE_PREMO_KEY') or config.get('ALPHA_VANTAGE_KEY')


def get_missing_dates(conn, symbol: str, start_date: str, end_date: str):
    """Get dates that are missing underlying_price"""
    query = """
        SELECT DISTINCT trading_date
        FROM options_chains_partitioned
        WHERE symbol = %s
          AND trading_date >= %s
          AND trading_date <= %s
          AND (underlying_price IS NULL OR underlying_price = 0)
        ORDER BY trading_date
    """
    with conn.cursor() as cur:
        cur.execute(query, (symbol, start_date, end_date))
        return [row[0].strftime('%Y-%m-%d') for row in cur.fetchall()]


def fetch_daily_prices(api_key: str, symbol: str):
    """Fetch full daily price history from Alpha Vantage"""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "full",  # Get full history
        "apikey": api_key
    }

    logger.info(f"Fetching daily prices for {symbol}...")
    response = requests.get(url, params=params)
    data = response.json()

    if "Time Series (Daily)" not in data:
        logger.error(f"API error: {data.get('Note', data.get('Error Message', 'Unknown error'))}")
        return {}

    prices = {}
    for date, values in data["Time Series (Daily)"].items():
        # Use adjusted close if available, otherwise close
        close_price = float(values.get("5. adjusted close", values.get("4. close", 0)))
        prices[date] = close_price

    logger.info(f"Fetched {len(prices)} daily prices")
    return prices


def update_underlying_prices(conn, symbol: str, date: str, price: float):
    """Update underlying_price for all options on a given date"""
    query = """
        UPDATE options_chains_partitioned
        SET underlying_price = %s
        WHERE symbol = %s
          AND trading_date = %s
          AND (underlying_price IS NULL OR underlying_price = 0)
    """
    with conn.cursor() as cur:
        cur.execute(query, (price, symbol, date))
        updated = cur.rowcount
    return updated


def main():
    parser = argparse.ArgumentParser(description='Backfill underlying_price from Alpha Vantage')
    parser.add_argument('--symbol', default='SPY', help='Symbol to backfill')
    parser.add_argument('--start', default='2023-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default='2025-12-31', help='End date (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')

    args = parser.parse_args()

    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="cregan1",
        database="gex_options"
    )
    conn.autocommit = False

    logger.info(f"Connected to PostgreSQL")

    # Get missing dates
    missing_dates = get_missing_dates(conn, args.symbol, args.start, args.end)
    logger.info(f"Found {len(missing_dates)} dates missing underlying_price")

    if not missing_dates:
        logger.info("No dates need backfilling!")
        return

    # Fetch prices from Alpha Vantage
    api_key = load_api_key()
    if not api_key:
        logger.error("No Alpha Vantage API key found in config")
        return

    prices = fetch_daily_prices(api_key, args.symbol)

    if not prices:
        logger.error("Failed to fetch prices")
        return

    # Update each missing date
    total_updated = 0
    dates_updated = 0
    dates_not_found = []

    for date in missing_dates:
        if date in prices:
            price = prices[date]

            if args.dry_run:
                logger.info(f"[DRY RUN] Would update {date}: ${price:.2f}")
            else:
                updated = update_underlying_prices(conn, args.symbol, date, price)
                total_updated += updated
                dates_updated += 1

                if dates_updated % 50 == 0:
                    conn.commit()
                    logger.info(f"Progress: {dates_updated}/{len(missing_dates)} dates, {total_updated} rows updated")
        else:
            dates_not_found.append(date)

    if not args.dry_run:
        conn.commit()

    logger.info("=" * 70)
    logger.info("BACKFILL COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Dates updated: {dates_updated}")
    logger.info(f"Total rows updated: {total_updated}")

    if dates_not_found:
        logger.warning(f"Dates not found in Alpha Vantage: {len(dates_not_found)}")
        if len(dates_not_found) <= 10:
            for d in dates_not_found:
                logger.warning(f"  - {d}")
        else:
            logger.warning(f"  First 10: {dates_not_found[:10]}")

    conn.close()


if __name__ == '__main__':
    main()
