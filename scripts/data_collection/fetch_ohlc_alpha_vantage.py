#!/usr/bin/env python3
"""Fetch OHLC data from Alpha Vantage and update daily_gex_metrics table.

Usage:
    python fetch_ohlc_alpha_vantage.py --symbol SPY --start-date 2024-01-02 --end-date 2024-12-31

Author: Chat C
Date: 2025-11-22
Purpose: Add OHLC data for Issue #144 Range Expansion calculation
"""

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def load_api_key():
    """Load Alpha Vantage API key from config."""
    config_path = project_root / "config" / "config.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    # Try PREMO key first (1000 calls/min), fallback to free key
    api_key = config.get("ALPHA_VANTAGE_PREMO_KEY") or config.get("ALPHA_VANTAGE_KEY")

    if not api_key:
        raise ValueError("No Alpha Vantage API key found in config")

    return api_key


def fetch_daily_ohlc(symbol, api_key):
    """Fetch daily OHLC data from Alpha Vantage TIME_SERIES_DAILY.

    Returns full history (20+ years if premium key).
    """
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "full",  # Get full history
        "apikey": api_key,
    }

    print(f"Fetching OHLC data for {symbol}...")
    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    if "Error Message" in data:
        raise ValueError(f"API Error: {data['Error Message']}")

    if "Note" in data:
        raise ValueError(f"API Rate Limit: {data['Note']}")

    time_series = data.get("Time Series (Daily)", {})

    if not time_series:
        raise ValueError(f"No time series data returned for {symbol}")

    print(f"  Fetched {len(time_series)} days of OHLC data")

    # Convert to list of records
    records = []
    for date_str, values in time_series.items():
        records.append(
            {
                "date": date_str,
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": int(values["5. volume"]),
            }
        )

    return records


def update_database(symbol, ohlc_records, db_path, start_date=None, end_date=None):
    """Update daily_gex_metrics table with OHLC data.

    Only updates records that already exist in the table (have GEX data).
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Filter records by date range if specified
    if start_date or end_date:
        filtered_records = []
        for record in ohlc_records:
            date = record["date"]
            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue
            filtered_records.append(record)
        ohlc_records = filtered_records

    print(f"\nUpdating database with {len(ohlc_records)} OHLC records...")

    # Check which dates exist in daily_gex_metrics
    cursor.execute(
        """
        SELECT date FROM daily_gex_metrics
        WHERE symbol = ? AND date BETWEEN ? AND ?
    """,
        (symbol, start_date or "1900-01-01", end_date or "2100-12-31"),
    )

    existing_dates = {row[0] for row in cursor.fetchall()}
    print(f"  Found {len(existing_dates)} existing GEX records for {symbol}")

    # Update only existing records
    updated = 0
    skipped = 0

    for record in ohlc_records:
        date = record["date"]

        if date not in existing_dates:
            skipped += 1
            continue

        cursor.execute(
            """
            UPDATE daily_gex_metrics
            SET open = ?, high = ?, low = ?, close = ?, volume = ?
            WHERE symbol = ? AND date = ?
        """,
            (record["open"], record["high"], record["low"], record["close"], record["volume"], symbol, date),
        )

        updated += 1

    conn.commit()
    conn.close()

    print(f"  Updated: {updated} records")
    print(f"  Skipped: {skipped} records (no GEX data for these dates)")

    return updated, skipped


def verify_update(symbol, db_path, sample_date="2024-01-02"):
    """Verify OHLC data was added correctly."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT date, spot_price, open, high, low, close, volume
        FROM daily_gex_metrics
        WHERE symbol = ? AND date = ?
    """,
        (symbol, sample_date),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        print(f"\nVerification (sample: {sample_date}):")
        print(f"  Spot Price: ${row[1]:.2f}")
        print(f"  Open: ${row[2]:.2f}")
        print(f"  High: ${row[3]:.2f}")
        print(f"  Low: ${row[4]:.2f}")
        print(f"  Close: ${row[5]:.2f}")
        print(f"  Volume: {row[6]:,}")

        # Verify close matches spot_price (should be same or very close)
        if abs(row[1] - row[5]) < 0.01:
            print("  ✓ Close price matches spot_price")
        else:
            print(f"  ⚠️ Close ({row[5]:.2f}) differs from spot_price ({row[1]:.2f})")
    else:
        print(f"\n⚠️ No data found for {sample_date}")


def main():
    parser = argparse.ArgumentParser(description="Fetch OHLC data from Alpha Vantage")
    parser.add_argument("--symbol", default="SPY", help="Stock symbol")
    parser.add_argument("--start-date", default="2024-01-02", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2024-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--db-path", default=".cache/consolidated_historical.db", help="Database path")

    args = parser.parse_args()

    db_path = project_root / args.db_path

    print("=" * 80)
    print("OHLC Data Fetcher - Alpha Vantage")
    print("=" * 80)
    print(f"Symbol: {args.symbol}")
    print(f"Date Range: {args.start_date} to {args.end_date}")
    print(f"Database: {db_path}")
    print()

    # Load API key
    api_key = load_api_key()
    print(f"✓ API key loaded (using {'PREMO' if 'PREMO' in str(api_key) else 'FREE'} tier)")

    # Fetch OHLC data
    ohlc_records = fetch_daily_ohlc(args.symbol, api_key)

    # Update database
    updated, skipped = update_database(args.symbol, ohlc_records, db_path, args.start_date, args.end_date)

    # Verify
    verify_update(args.symbol, db_path, args.start_date)

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"✓ OHLC data added to daily_gex_metrics table")
    print(f"✓ {updated} records updated for {args.symbol} ({args.start_date} to {args.end_date})")
    print()


if __name__ == "__main__":
    main()
